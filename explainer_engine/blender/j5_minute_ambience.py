import numpy as np, wave
SR=48000; T=60.0; n=int(SR*T); r=np.random.default_rng(3)
def env(t0,t1,f_in=1.0,f_out=1.0,g=1.0):
    t=np.arange(n)/SR; e=np.zeros(n); m=(t>=t0)&(t<t1); e[m]=1
    e=np.minimum(e,np.clip((t-t0)/f_in,0,1)); e=np.minimum(e,np.clip((t1-t)/f_out,0,1)); return e*g
def lp(x,a): 
    y=np.zeros_like(x); acc=0.0
    for i in range(len(x)): acc+=a*(x[i]-acc); y[i]=acc
    return y
def hp(x,a): return x-lp(x,a)
white=r.normal(0,1,n)
rain=hp(white,0.25)*0.5; rain=rain*(1+0.15*np.sin(np.arange(n)/SR*1.7))
rainbed=rain*env(0,24,0.5,2.5,0.22)
# fire crackle: random ticks + low rumble
fire=np.zeros(n); ticks=r.integers(int(18*SR),int(43*SR),260)
for k in ticks: L=int(SR*r.uniform(0.002,0.01)); fire[k:k+L]+=r.normal(0,1,min(L,n-k))*r.uniform(0.2,0.8)
fire=hp(fire,0.3)*0.5+lp(r.normal(0,1,n),0.01)*0.8
firebed=fire*env(18.5,43,1.0,2.0,0.12)
# battle: noise swell + metal clicks + low thumps
bat=lp(white,0.08)*1.3*env(42,52.5,1.5,1.5,0.22)
for k in np.sort(r.uniform(42.5,52,34)):
    i=int(k*SR); L=int(SR*0.35); t=np.arange(L)/SR; f=r.uniform(1400,3200)
    n_=min(L,n-i); bat[i:i+n_]+=(np.sin(2*np.pi*f*t)+0.5*np.sin(2*np.pi*f*2.41*t))[:n_]*np.exp(-t*14)[:n_]*0.05
for k in np.arange(42.5,52,0.8):
    i=int(k*SR); L=int(SR*0.4); t=np.arange(L)/SR; n_=min(L,n-i); bat[i:i+n_]+=np.sin(2*np.pi*55*t)[:n_]*np.exp(-t*9)[:n_]*0.12
# dawn wind
wind=lp(white,0.015)*3.0*(1+0.3*np.sin(np.arange(n)/SR*0.6))*env(50.5,60,2.0,3.0,0.12)
# low drone under the whole film for glue
t=np.arange(n)/SR; drone=(np.sin(2*np.pi*55*t)+0.5*np.sin(2*np.pi*82.5*t))*0.025*env(0,60,3,4,1)
amb=rainbed+firebed+bat+wind+drone
amb=np.clip(amb,-0.9,0.9)
w=wave.open('out/amb.wav','wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((amb*32767).astype('<i2').tobytes()); w.close()
