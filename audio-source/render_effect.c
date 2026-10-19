#define TSF_IMPLEMENTATION
#include "tsf.h"
#include <stdint.h>
int main(int argc, char **argv) {
 if (argc != 8) return 2;
 tsf *font=tsf_load_filename(argv[1]); if (!font) return 3;
 int program=atoi(argv[2]),note=atoi(argv[3]),ms=atoi(argv[4]);
 float velocity=atof(argv[5])/127.0f,volume=atof(argv[6])/100.0f;
 tsf_set_output(font,TSF_MONO,22050,0.0f);tsf_set_volume(font,volume);
 int preset=tsf_get_presetindex(font,0,program);if(preset<0)return 4;
 tsf_note_on(font,preset,note,velocity);
 FILE *out=fopen(argv[7],"wb");if(!out)return 5;
 short block[256];int remaining=(22050*ms+500)/1000;
 while(remaining>0){int n=remaining>256?256:remaining;tsf_render_short(font,block,n,0);fwrite(block,2,n,out);remaining-=n;}
 tsf_note_off(font,preset,note);
 // Preserve the sample's release instead of cutting the effect off at note-off.
 for(int n=0;n<22050*5;n+=256){
  tsf_render_short(font,block,256,0);fwrite(block,2,256,out);
  if(!tsf_active_voice_count(font))break;
 }
 fclose(out);tsf_close(font);return 0;
}
