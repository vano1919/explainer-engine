import numpy as np, wave
SR=48000; T=60.0; n=int(SR*T); r=np.random.default_rng(5); t=np.arange(n)/SR
def env(t0,t1,fi=1.0,fo=1.0,g=1.0):
    e=((t>=t0)&(t<t1)).astype(float); return np.minimum(np.minimum(e,np.clip((t-t0)/fi,0,1)),np.clip((t1-t)/fo,0,1))*g
def lp(x,a):
    from scipy.signal import lfilter
    return lfilter([a],[1,-(1-a)],x)
def hp(x,a): return x-lp(x,a)
white=r.normal(0,1,n)
def clang(bed,t0,t1,k,amp=0.05):
    for q in np.sort(r.uniform(t0,t1,k)):
        i=int(q*SR); L=int(SR*0.4); tt=np.arange(L)/SR; f=r.uniform(1400,3400); m=min(L,n-i)
        bed[i:i+m]+=(np.sin(2*np.pi*f*tt)+0.5*np.sin(2*np.pi*f*2.41*tt))[:m]*np.exp(-tt*13)[:m]*amp
def thump(bed,t0,t1,step,f=55,amp=0.12):
    for q in np.arange(t0,t1,step):
        i=int(q*SR); L=int(SR*0.4); tt=np.arange(L)/SR; m=min(L,n-i); bed[i:i+m]+=np.sin(2*np.pi*f*tt)[:m]*np.exp(-tt*9)[:m]*amp
# courtyard day: murmur + clashes
murmur=lp(white,0.03)*1.2*(1+0.3*np.sin(t*0.9))*env(0,13,0.5,1.5,0.10); clang(murmur,5.2,9.8,9,0.07); clang(murmur,0.5,4.8,2,0.02)
# map: paper/low
paper=hp(lp(white,0.2),0.01)*0.15*env(10,13.4,0.4,0.5,0.06)
# rain 13-24
rain=hp(white,0.25)*0.5*(1+0.15*np.sin(t*1.7))*env(13,24.5,0.5,2.0,0.22)
# fire 19-41.5
fire=np.zeros(n)
for k in r.integers(int(19*SR),int(41.5*SR),240):
    L=int(SR*r.uniform(0.002,0.01)); m=min(L,n-k); fire[k:k+m]+=r.normal(0,1,m)*r.uniform(0.2,0.8)
fire=(hp(fire,0.3)*0.5+lp(r.normal(0,1,n),0.01)*0.8)*env(19,42,1.0,1.5,0.12)
# ford battle 41.5-47.5
bat=lp(white,0.08)*1.3*env(41.5,48,1.0,2.0,0.22); clang(bat,42,47,26,0.05); thump(bat,41.8,47,0.8)
# dawn wind 45-58
wind=lp(white,0.015)*3.0*(1+0.3*np.sin(t*0.6))*env(45,58,2.0,3.0,0.12)
# footsteps in mud 49-56.5
steps=np.zeros(n)
for q in np.arange(49.3,56.4,0.56):
    i=int(q*SR); L=int(SR*0.18); tt=np.arange(L)/SR; m=min(L,n-i); steps[i:i+m]+=lp(r.normal(0,1,L),0.05)[:m]*np.exp(-tt*22)[:m]*0.35
drone=(np.sin(2*np.pi*55*t)+0.5*np.sin(2*np.pi*82.5*t))*0.02*env(0,60,3,4,1)
amb=np.clip(murmur+paper+rain+fire+bat+wind+steps+drone,-0.9,0.9)
w=wave.open('out/amb2.wav','wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((amb*32767).astype('<i2').tobytes()); w.close(); print("ok")
