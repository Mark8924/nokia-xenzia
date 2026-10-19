package local.snake.xenzia;

import android.app.*;
import android.os.*;
import android.graphics.*;
import android.media.*;
import android.view.*;
import android.widget.*;
import com.chaquo.python.*;
import com.chaquo.python.android.AndroidPlatform;
import org.json.*;
import java.io.*;
import java.nio.ByteBuffer;
import java.util.*;
import java.util.zip.*;

public class MainActivity extends Activity {
    private HandlerThread thread;
    private Handler worker;
    private final Handler ui=new Handler(Looper.getMainLooper());
    private PyObject game;
    private volatile boolean active=false,ready=false,failed=false,introVisible=false;
    private volatile boolean destroyed=false,preparing=false;
    private GameView screen;
    private LinearLayout root,pad;
    private SoundPool sound;
    private final Map<String,Integer> tones=new HashMap<>();
    private int stream=0;
    private JSONObject options=new JSONObject();
    private Bitmap lastFrame;
    private float density;
    private File engineDirectory;
    private LinearLayout preparationPanel;
    private TextView preparationLabel;
    private ProgressBar preparationProgress;
    private Button retryPreparation;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);density=getResources().getDisplayMetrics().density;
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        root=new LinearLayout(this);root.setOrientation(1);root.setBackgroundColor(Color.rgb(213,217,219));
        root.setOnApplyWindowInsetsListener((view,insets)->{
            if(Build.VERSION.SDK_INT>=30){android.graphics.Insets i=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());view.setPadding(i.left,i.top,i.right,i.bottom);}
            else view.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            return insets;
        });
        LinearLayout bar=new LinearLayout(this);bar.setGravity(Gravity.CENTER_VERTICAL);bar.setPadding(dp(16),dp(4),dp(8),dp(4));
        TextView title=new TextView(this);title.setText("S N A K E   X E N Z I A");title.setTextColor(Color.rgb(30,36,39));title.setTextSize(16);title.setTypeface(null,Typeface.BOLD);
        bar.addView(title,new LinearLayout.LayoutParams(0,dp(48),1));title.setGravity(Gravity.CENTER_VERTICAL);
        Button settings=new Button(this);settings.setText("设置 ⋮");settings.setOnClickListener(v->showSettings());bar.addView(settings);
        root.addView(bar,new LinearLayout.LayoutParams(-1,-2));
        preparationPanel=new LinearLayout(this);preparationPanel.setOrientation(1);preparationPanel.setPadding(dp(20),dp(14),dp(20),dp(14));
        preparationLabel=new TextView(this);preparationLabel.setText("正在准备游戏… / Preparing game…");preparationLabel.setTextColor(Color.rgb(30,36,39));
        preparationProgress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);preparationProgress.setMax(100);
        retryPreparation=new Button(this);retryPreparation.setText("重试 / Retry");retryPreparation.setVisibility(View.GONE);retryPreparation.setOnClickListener(v->prepareEngine());
        preparationPanel.addView(preparationLabel);preparationPanel.addView(preparationProgress,new LinearLayout.LayoutParams(-1,dp(20)));preparationPanel.addView(retryPreparation);
        root.addView(preparationPanel,new LinearLayout.LayoutParams(-1,-2));
        screen=new GameView();root.addView(screen,new LinearLayout.LayoutParams(-1,0,1));
        LinearLayout soft=new LinearLayout(this);soft.setPadding(dp(10),0,dp(10),0);
        soft.addView(button("选择 / 暂停", "select"),new LinearLayout.LayoutParams(0,dp(54),1));
        soft.addView(button("返回", "back"),new LinearLayout.LayoutParams(0,dp(54),1));root.addView(soft);
        pad=new LinearLayout(this);pad.setOrientation(1);pad.setGravity(Gravity.CENTER);
        for(int row=0;row<3;row++) {
            LinearLayout line=new LinearLayout(this);line.setGravity(Gravity.CENTER);
            for(int col=0;col<3;col++) {
                String label=null,key=null;
                if(row==0&&col==1){label="↑  2";key="up";}
                if(row==1&&col==0){label="←  4";key="left";}
                if(row==1&&col==2){label="→  6";key="right";}
                if(row==2&&col==1){label="↓  8";key="down";}
                View v=key==null?new View(this):button(label,key);
                line.addView(v,new LinearLayout.LayoutParams(dp(96),dp(50)));
            }
            pad.addView(line);
        }
        root.addView(pad);setContentView(root);screen.requestFocus();root.requestApplyInsets();
        sound=new SoundPool.Builder().setMaxStreams(1).setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_GAME).setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build()).build();
        setVolumeControlStream(AudioManager.STREAM_MUSIC);
        thread=new HandlerThread("NokiaEngine");thread.start();worker=new Handler(thread.getLooper());
        prepareEngine();
    }

    public void onPreparationProgress(String message,int percent) {
        ui.post(()->{if(!destroyed){preparationLabel.setText(message);preparationProgress.setProgress(percent);}});
    }

    private void prepareEngine() {
        if(ready||preparing||destroyed)return;
        preparing=true;
        preparationPanel.setVisibility(View.VISIBLE);retryPreparation.setVisibility(View.GONE);preparationLabel.setText("正在准备游戏… / Preparing game…");
        worker.post(()->{try {
            engineDirectory=unpack();
            if(!Python.isStarted())Python.start(new AndroidPlatform(this));
            boolean available=Python.getInstance().getModule("bootstrap").callAttr("prepare",engineDirectory.getAbsolutePath(),new File(getFilesDir(),"save").getAbsolutePath(),getApplicationInfo().nativeLibraryDir,MainActivity.this).toBoolean();
            if(!available)throw new IOException("Game preparation did not complete");
            if(destroyed)return;
            ui.post(()->preparationPanel.setVisibility(View.GONE));
            startEngine();
        } catch(Throwable error){
            android.util.Log.e("XenziaPreparation","Unable to prepare game",error);
            ui.post(()->{if(!destroyed){preparationPanel.setVisibility(View.VISIBLE);preparationLabel.setText("准备失败，请检查网络后重试。\nPreparation failed. Check your connection and retry.");retryPreparation.setVisibility(View.VISIBLE);}});
        } finally {preparing=false;} });
    }

    private void startEngine() throws Exception {
            game=Python.getInstance().getModule("bootstrap").callAttr("open_game",engineDirectory.getAbsolutePath(),new File(getFilesDir(),"save").getAbsolutePath(),getApplicationInfo().nativeLibraryDir);
            options=new JSONObject(game.callAttr("settings").toString());
            for(int i=0;i<5;i++){String name="effect-"+i;String path=Python.getInstance().getModule("bootstrap").callAttr("audio_file",name).toString();tones.put(name,sound.load(path,1));}
            game.callAttr("set_audio_sink",MainActivity.this);
            ready=true;publish();ui.post(()->pad.setVisibility(options.optBoolean("controls_visible",true)?View.VISIBLE:View.GONE));
            if((getApplicationInfo().flags&android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE)!=0&&getIntent().getBooleanExtra("self_test",false)) {
                String result=Python.getInstance().getModule("bootstrap").callAttr("self_test",new File(getFilesDir(),"qa").getAbsolutePath()).toString();
                try(FileWriter out=new FileWriter(new File(getFilesDir(),"android-test.json"))){out.write(result);}
                android.util.Log.i("XenziaQA",result);
            }
            if(active)worker.post(tick);
    }

    private int dp(float value){return Math.round(value*density);}
    private File unpack() throws Exception {
        String hash;
        try(InputStream input=getAssets().open("game.sha256")){ByteArrayOutputStream output=new ByteArrayOutputStream();byte[] data=new byte[256];int n;while((n=input.read(data))!=-1)output.write(data,0,n);hash=output.toString("UTF-8").trim();}
        File engine=new File(getFilesDir(),"engine-"+hash.substring(0,16));File marker=new File(engine,"ready-v1");
        if(!marker.exists()) {
            engine.mkdirs();String prefix=engine.getCanonicalPath()+File.separator;
            try(ZipInputStream zip=new ZipInputStream(getAssets().open("game.zip"))) {
                ZipEntry entry;byte[] buffer=new byte[16384];
                while((entry=zip.getNextEntry())!=null) {
                    File file=new File(engine,entry.getName());
                    if(!file.getCanonicalPath().startsWith(prefix))throw new IOException("Unsafe asset path");
                    if(entry.isDirectory())file.mkdirs();
                    else {file.getParentFile().mkdirs();try(FileOutputStream out=new FileOutputStream(file)){int n;while((n=zip.read(buffer))!=-1)out.write(buffer,0,n);}}
                }
            }
            marker.createNewFile();
        }
        return engine;
    }

    private Button button(String label,String key) {
        Button button=new Button(this);button.setText(label);button.setTextSize(15);button.setFocusable(false);button.setAllCaps(false);
        button.setOnTouchListener((view,event)->{if(event.getActionMasked()==MotionEvent.ACTION_DOWN){send(key);view.setPressed(true);return true;}if(event.getActionMasked()==MotionEvent.ACTION_UP||event.getActionMasked()==MotionEvent.ACTION_CANCEL){view.setPressed(false);return true;}return true;});
        button.setOnClickListener(v->send(key));return button;
    }

    private final Runnable tick=new Runnable(){@Override public void run(){if(!ready||!active||failed)return;try{game.callAttr("tick");publish();worker.postDelayed(this,game.callAttr("delay").toInt());}catch(Throwable error){error(error);}}};
    public void playEffect(String effect) {
        Integer tone=tones.get(effect);
        if(tone!=null){if(stream!=0)sound.stop(stream);stream=sound.play(tone,1,1,1,0,1);}
    }
    private void publish() throws Exception {
        introVisible=game.callAttr("is_intro").toBoolean();
        byte[] rgba=game.callAttr("pixels").toJava(byte[].class);
        Bitmap frame=Bitmap.createBitmap(96,65,Bitmap.Config.ARGB_8888);frame.copyPixelsFromBuffer(ByteBuffer.wrap(rgba));
        JSONArray effects=new JSONArray(game.callAttr("take_audio").toString());
        for(int i=0;i<effects.length();i++){Integer tone=tones.get(effects.getString(i));if(tone!=null){if(stream!=0)sound.stop(stream);stream=sound.play(tone,1,1,1,0,1);}}
        ui.post(()->{lastFrame=frame;screen.invalidate();});
    }
    private void send(String key) {
        if(!ready||failed)return;
        worker.post(()->{try {
            boolean wasMenu=game.callAttr("is_menu").toBoolean();game.callAttr("key",key);publish();
            if(wasMenu&&!game.callAttr("is_menu").toBoolean()){worker.removeCallbacks(tick);if(active)worker.postDelayed(tick,game.callAttr("delay").toInt());}
        }catch(Throwable error){error(error);}});
    }
    private void tap(float x,float y){if(!ready||failed)return;worker.post(()->{try{boolean was=game.callAttr("is_menu").toBoolean();game.callAttr("tap",x,y);publish();if(was&&!game.callAttr("is_menu").toBoolean()){worker.removeCallbacks(tick);if(active)worker.postDelayed(tick,game.callAttr("delay").toInt());}}catch(Throwable error){error(error);}});}
    private void setOption(String key,Object value){if(!ready||failed)return;worker.post(()->{try{game.callAttr("configure",key,value);options=new JSONObject(game.callAttr("settings").toString());if(options.optBoolean("muted")&&stream!=0)sound.stop(stream);publish();ui.post(()->pad.setVisibility(options.optBoolean("controls_visible",true)?View.VISIBLE:View.GONE));}catch(Throwable error){error(error);}});}
    private void showSettings() {
        if(!ready)return;
        LinearLayout box=new LinearLayout(this);box.setOrientation(1);box.setPadding(dp(20),dp(8),dp(20),dp(8));
        for(String key:new String[]{"muted","controls_visible","play_intro"}) {
            CheckBox check=new CheckBox(this);check.setText(key.equals("muted")?"静音 / Mute":key.equals("controls_visible")?"显示屏幕方向键 / Direction pad":"启动时播放开场动画 / Opening animation");check.setChecked(options.optBoolean(key));check.setOnCheckedChangeListener((b,value)->setOption(key,value));box.addView(check);
        }
        TextView caption=new TextView(this);caption.setText("配色 / Colour");box.addView(caption);
        Spinner colors=new Spinner(this);colors.setAdapter(new ArrayAdapter<String>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"跟随原版 / Original","白底黑色 / Light","黑底白色 / Dark"}));
        String current=options.optString("color_mode","original");colors.setSelection(current.equals("dark")?2:current.equals("light")?1:0);
        colors.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener(){public void onNothingSelected(AdapterView<?> p){}public void onItemSelected(AdapterView<?> p,View v,int position,long id){setOption("color_mode",new String[]{"original","light","dark"}[position]);}});box.addView(colors);
        TextView help=new TextView(this);help.setText("\n方向键 / WASD / 2 4 6 8 转向\nEnter / 5 选择；Esc 返回\n支持在游戏画面上滑动转向。\n菜单中 Level 调整速度，Game type 选择玩法。\n自动保存，关闭后通过 Continue 继续。\n开场动画的开启在下次启动时生效。");box.addView(help);
        new AlertDialog.Builder(this).setTitle("Snake Xenzia").setView(box).setPositiveButton("完成 / Done",null).show();
    }

    private void error(Throwable error) {
        android.util.Log.e("SnakeXenzia","Game error",error);failed=true;worker.removeCallbacks(tick);
        try(PrintWriter out=new PrintWriter(new FileWriter(new File(getFilesDir(),"game.log"),true))){error.printStackTrace(out);}catch(IOException ignored){}
        ui.post(()->new AlertDialog.Builder(this).setTitle("运行错误 / Game error").setMessage(error.toString()+"\n已保留之前的自动存档。").setPositiveButton("关闭",(d,w)->finish()).show());
    }
    @Override public void onResume(){super.onResume();active=true;if(worker!=null&&ready){worker.removeCallbacks(tick);worker.post(tick);sound.autoResume();}}
    @Override public void onPause(){active=false;super.onPause();if(worker!=null){worker.removeCallbacks(tick);worker.post(()->{if(ready&&!failed)try{game.callAttr("pause");}catch(Throwable error){android.util.Log.e("SnakeXenzia","Save error",error);}sound.autoPause();});}}
    @Override public void onDestroy(){destroyed=true;if(worker!=null)worker.post(()->{if(ready&&!failed)try{game.callAttr("close");}catch(Throwable ignored){}sound.release();thread.quitSafely();});super.onDestroy();}
    @Override public void onBackPressed(){if(!ready)finish();else send("back");}
    @Override public boolean onKeyDown(int code,KeyEvent event) {
        String key=null;
        switch(code){case KeyEvent.KEYCODE_DPAD_UP:case KeyEvent.KEYCODE_W:case KeyEvent.KEYCODE_2:key="up";break;case KeyEvent.KEYCODE_DPAD_DOWN:case KeyEvent.KEYCODE_S:case KeyEvent.KEYCODE_8:key="down";break;case KeyEvent.KEYCODE_DPAD_LEFT:case KeyEvent.KEYCODE_A:case KeyEvent.KEYCODE_4:key="left";break;case KeyEvent.KEYCODE_DPAD_RIGHT:case KeyEvent.KEYCODE_D:case KeyEvent.KEYCODE_6:key="right";break;case KeyEvent.KEYCODE_ENTER:case KeyEvent.KEYCODE_SPACE:case KeyEvent.KEYCODE_5:key="select";break;case KeyEvent.KEYCODE_ESCAPE:case KeyEvent.KEYCODE_P:key="back";break;}
        if(key!=null){send(key);return true;}return super.onKeyDown(code,event);
    }

    class GameView extends View {
        Paint paint=new Paint();RectF dest=new RectF();float x0,y0;boolean dragged,introAtDown;
        GameView(){super(MainActivity.this);setFocusable(true);setFocusableInTouchMode(true);paint.setFilterBitmap(false);}
        @Override protected void onDraw(Canvas canvas){super.onDraw(canvas);if(lastFrame==null)return;float scale=Math.max(1,(float)Math.floor(Math.min((getWidth()-dp(24))/96f,(getHeight()-dp(24))/65f)));float width=scale*96,height=scale*65;dest.set((getWidth()-width)/2,(getHeight()-height)/2,(getWidth()+width)/2,(getHeight()+height)/2);paint.setColor(Color.rgb(42,47,51));canvas.drawRect(dest.left-dp(3),dest.top-dp(3),dest.right+dp(3),dest.bottom+dp(3),paint);canvas.drawBitmap(lastFrame,null,dest,paint);}
        @Override public boolean onTouchEvent(android.view.MotionEvent e){
            if(e.getActionMasked()==MotionEvent.ACTION_DOWN){x0=e.getX();y0=e.getY();dragged=false;introAtDown=introVisible;return true;}
            if(e.getActionMasked()==MotionEvent.ACTION_MOVE&&!dragged){float dx=e.getX()-x0,dy=e.getY()-y0;if(Math.max(Math.abs(dx),Math.abs(dy))>dp(24)){send(Math.abs(dx)>Math.abs(dy)?dx>0?"right":"left":dy>0?"down":"up");dragged=true;}return true;}
            if(e.getActionMasked()==MotionEvent.ACTION_UP){if(!dragged){if(introAtDown){worker.post(()->{try{game.callAttr("skip_intro");publish();}catch(Throwable error){error(error);}});}else tap((x0-dest.left)*96/dest.width(),(y0-dest.top)*65/dest.height());}performClick();return true;}return true;
        }
        @Override public boolean performClick(){super.performClick();return true;}
    }
}
