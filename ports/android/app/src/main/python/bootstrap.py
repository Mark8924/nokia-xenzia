import os,sys

def open_game(directory,data,native):
    os.environ['LIBUNICORN_PATH']=native
    sys.path.insert(0,directory)
    from session import Session
    return Session(data)

def self_test(directory):
    from test_portable import run
    import json
    return json.dumps(run(directory))
