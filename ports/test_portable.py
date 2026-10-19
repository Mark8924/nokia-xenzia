"""Run on each packaged interpreter, using only isolated game data."""
import contextlib,hashlib,io,json
from pathlib import Path
from session import Session
from qa_play import original_state,route
from test_frame_budget import main as maximum_snake
from asset_store import resource


def components(image):
    points={(x,y) for y in range(65) for x in range(96) if max(image.getpixel((x,y)))<240};parts=0
    while points:
        todo=[points.pop()];size=0
        while todo:
            x,y=todo.pop();size+=1
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    point=x+dx,y+dy
                    if point in points:points.remove(point);todo.append(point)
        if size>=3:parts+=1
    return parts


def run(directory):
    data=Path(directory);data.mkdir(parents=True,exist_ok=True)
    # Tests may be rerun; use a fresh nested directory, not a user's save.
    import tempfile
    with tempfile.TemporaryDirectory(dir=data) as scratch:
        game=Session(scratch)
        assert game.is_menu() and game.runtime.menu_labels()[0]=='New game'
        game.runtime.random.seed(265);game.tap(15,19)
        assert not game.is_menu()
        r=game.runtime
        target_score=3*r.word(r.state+4)
        for step in range(150):
            field,s,f,head,food,body=original_state(r);path=route(head,food,body);assert path
            game.key(path[0])
            for _ in range(4):game.tick()
            if r.word(r.state+8)>=target_score:break
        score=r.word(r.state+8);assert score==target_score
        progress=original_state(r)[3:]
        game.configure('color_mode','dark');game.configure('controls_visible',False);game.configure('play_intro',True)
        assert len(game.pixels())==96*65*4
        game.close();loaded=Session(scratch)
        assert loaded.options['color_mode']=='dark' and not loaded.options['controls_visible']
        assert loaded.intro is not None and loaded.runtime.word(loaded.runtime.state+8)==score
        frames=set()
        for _ in range(100):
            if loaded.intro is None:break
            assert components(loaded.intro.image)<=1
            frames.add(loaded.intro.image.tobytes());loaded.tick()
        assert loaded.intro is None and len(frames)>10
        assert original_state(loaded.runtime)[3:]==progress
        loaded.close()
    manifest=json.loads(resource('audio/effects.json').read_text())
    for effect in manifest.values():
        pcm=resource('audio/'+effect['file']).read_bytes()
        assert hashlib.sha256(pcm).hexdigest()==effect['sha256']
        assert resource('audio/'+Path(effect['file']).stem+'.wav').read_bytes()[:4]==b'RIFF'
    with contextlib.redirect_stdout(io.StringIO()):maximum_snake()
    from test_transitions import check_campaign
    transition=check_campaign()
    result={'native_gameplay':True,'three_foods_score':score,'save_resume':True,'intro_no_flicker':True,'intro_unique_frames':len(frames),'options_persist':True,'original_audio_assets':True,'maximum_100_segment_render_cases':12,'finite_guest_guard':True}
    result['campaign_transition']=transition
    (data/'portable-test.json').write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    import sys
    print(json.dumps(run(sys.argv[1]),indent=2))
