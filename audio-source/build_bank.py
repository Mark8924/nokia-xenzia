"""Keep the SF2 region/envelope layout; replace the three game voices with the
actual signed 8-bit PCM extracted from RH-93's embedded DLS sound bank."""
from pathlib import Path
import struct,sys
root=Path(__file__).resolve().parents[1]
def chunks(data,start=0):
 data=bytes(data)
 while start+8<=len(data):
  tag=data[start:start+4];n=struct.unpack_from('<I',data,start+4)[0]
  yield tag,start+8,data[start+8:start+8+n]
  start+=8+n+(n&1)
reference=bytearray(Path(sys.argv[1]).read_bytes())
for tag,pos,payload in chunks(reference,12):
 if tag==b'LIST' and payload[:4]==b'pdta':tables={t:x for t,_,x in chunks(payload,4)}
 if tag==b'LIST' and payload[:4]==b'sdta':
  for t,p,x in chunks(payload,4):
   if t==b'smpl':sample_offset=pos+p
original=(root/'assets/audio/original-rh93.dls').read_bytes()
for tag,_,payload in chunks(original,12):
 if tag==b'LIST' and payload[:4]==b'wvpl':waves=[{t:x for t,_,x in chunks(w,4)}[b'data'] for _,_,w in chunks(payload,4)]
for sfindex,dlsindex in [(1,1),(19,23),(31,32)]:
 name,start,end,*_=struct.unpack_from('<20sIIIIIBbHH',tables[b'shdr'],sfindex*46)
 pcm=waves[dlsindex][:end-start]
 assert len(pcm)==end-start
 # Nokia's bank uses signed 8-bit sample values; the SF2 reference confirms the
 # polarity/centering. WAV-style unsigned conversion would introduce DC offset.
 converted=b''.join(struct.pack('<h',(x if x<128 else x-256)*256) for x in pcm)
 reference[sample_offset+start*2:sample_offset+end*2]=converted
 print('Original PCM:',name.split(b'\0')[0].decode(),len(pcm),'frames')
(root/'assets/audio/nokia-rh93.sf2').write_bytes(reference)
