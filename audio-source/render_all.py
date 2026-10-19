from pathlib import Path
import struct,json,subprocess,hashlib,sys,array
root=Path(__file__).resolve().parents[1];code=(root/'assets/snake-code.bin').read_bytes()
manifest={};names={120:'Fret Noise / CRASH',12:'Marimba / VIBAs4',55:'Orchestra Hit / ORCHC5D'}
for i in range(7):
 program,note,duration,repeat=struct.unpack_from('>4h',code,0xdd70-0x8000+i*8)
 command=(note,0,program,repeat,0,duration,100,100)
 key=','.join(map(str,command));filename=f'effect-{min(i,4)}.s16le'
 if key not in manifest:
  target=root/'assets/audio'/filename
  subprocess.run([sys.argv[1],str(root/'assets/audio/nokia-rh93.sf2'),str(program),str(note),str(duration),'100','100',str(target)],check=True)
  raw=target.read_bytes();samples=array.array('h');samples.frombytes(raw)
  # Trim trailing digital silence, retain at least the requested note duration.
  last=len(samples)-1
  while last>round(22050*duration/1000) and abs(samples[last])<8:last-=1
  samples=samples[:min(len(samples),last+int(22050*.01))]
  target.write_bytes(samples.tobytes());raw=target.read_bytes()
  manifest[key]={'file':filename,'program':program,'note':note,'note_off_ms':duration,'instrument':names[program],'frames':len(samples),'sha256':hashlib.sha256(raw).hexdigest()}
  print(i,names[program],'note',note,'held',duration,'ms','total',round(len(samples)/22.05),'ms','peak',max(map(abs,samples)))
(root/'assets/audio/effects.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
