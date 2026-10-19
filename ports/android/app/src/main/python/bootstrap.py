import os,sys

def open_game(directory,data,native):
    os.environ['LIBUNICORN_PATH']=native
    sys.path.insert(0,directory)
    from session import Session
    return Session(data)

def prepare(directory,data,native,activity=None):
    os.environ['LIBUNICORN_PATH']=native
    os.environ['XENZIA_AUDIO_LIBRARY']=os.path.join(native,'libxenzia_audio.so')
    if directory not in sys.path:sys.path.insert(0,directory)
    from asset_store import ensure_assets
    if ensure_assets(data):return True
    from auto_assets import obtain
    def progress(message,percent):
        if activity is not None:activity.onPreparationProgress(message,percent)
    return obtain(data,progress)

def import_original(source,data):
    from asset_store import import_assets
    return import_assets(source,data)

def audio_file(name):
    from asset_store import resource
    return str(resource('audio/'+name+'.wav'))

def self_test(directory):
    from test_portable import run
    import json
    return json.dumps(run(directory))
