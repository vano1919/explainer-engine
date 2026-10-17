import sys, wave, subprocess, numpy as np
sys.path.insert(0,"/home/user/explainer-engine")
from explainer_engine.audio.sfx_library import read_wav
L="/home/user/explainer-engine/assets/audio/library/"
SR=48000; DUR=28.0
def load(rel):
    r=read_wav(L+rel); x=np.asarray(r[0] if isinstance(r,tuple) else r,dtype=np.float32)
    sr=r[1] if isinstance(r,tuple) and len(r)>1 else SR
    return x,sr
def tomono48(x,sr):
    if x.ndim>1: x=x.mean(axis=1)
    if sr!=SR: x=np.interp(np.arange(0,len(x)*SR/sr),np.arange(len(x))*SR/sr,x).astype(np.float32)
    return x
mix=np.zeros(int(DUR*SR),np.float32)
def put(x,t,db=0.0):
    i=int(t*SR); x=x*10**(db/20); n=min(len(x),len(mix)-i)
    if n>0: mix[i:i+n]+=x[:n]
def sfx(rel,t,db=0.0):
    x,sr=load(rel); put(tomono48(x,sr),t,db)
# narration
w=wave.open("narr.wav"); nar=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768
nar=tomono48(nar,w.getframerate()); nar=nar/np.abs(nar).max()*0.7; put(nar,0.0,0)
# music
m,sr=load("music/clockwork_loop__v1.wav"); m=tomono48(m,sr)[:int(DUR*SR)]
f=np.ones(len(m),np.float32); f[:SR]=np.linspace(0,1,SR); f[-3*SR:]=np.linspace(1,0,3*SR); put(m*f,0,-24)
# events (times match scene.py)
sfx("foley/swish__v1.wav" if False else "foley/cloth_rustle__v1.wav",5.4,-8)
sfx("foley/cloth_rustle__v2.wav",8.7,-8)
sfx("foley/pop_in__v1.wav",13.4,-8)
sfx("foley/glow_ping__v1.wav",13.8,-14)
sfx("foley/glow_ping__v1.wav",23.2,-8)
sfx("foley/pop_in__v1.wav",25.3,-5)
sfx("foley/seam_shimmer__v1.wav",25.35,-12)
sfx("vocal/gasp_inhale__v1.wav",25.35,-8)
sfx("vocal/effort_hup__v1.wav",25.6,-12)
sfx("vocal/laugh_warm__v1.wav",26.4,-14)
s,sr=load("foley/pencil_scribble__v1.wav"); s=tomono48(s,sr)
for a,b in ((5.9,12.2),(18.8,23.2)):
    t=a
    while t<b: put(s*np.hanning(len(s))**0.5,t,-18); t+=len(s)/SR*0.7
# fire crackle
rng=np.random.default_rng(2); cr=np.zeros(len(mix),np.float32)
n=int(rng.integers(60,80))
for t in np.sort(rng.uniform(25.4,27.9,60)):
    k=int(0.012*SR); env=np.exp(-np.arange(k)/ (k/5)); c=rng.standard_normal(k)*env*rng.uniform(0.2,0.9)
    i=int(t*SR); cr[i:i+k]+=c.astype(np.float32)
k=int(1.0*SR); 
put(cr,0,-14); 
bed=rng.standard_normal(len(mix)).astype(np.float32); bed=np.convolve(bed,np.ones(40)/40,mode="same")
gate=np.clip((np.arange(len(mix))/SR-25.3)/0.8,0,1); put(bed*gate*0.6,0,-24)
pk=np.abs(mix).max(); print("peak",pk)
mix=mix/pk*0.7079  # -3 dBFS
w=wave.open("mix.wav","wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix*32767).astype(np.int16).tobytes()); w.close()
