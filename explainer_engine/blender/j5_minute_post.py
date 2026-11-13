import sys, glob, math, numpy as np, cv2
sys.argv=[sys.argv[0]]+sys.argv[1:]
import build as B
from PIL import Image
W,H=B.W,B.H; rng=B.rng
def fog_tex():
    a=rng.normal(0,1,(24,96)).astype(np.float32); a=cv2.resize(a,(1536,300),interpolation=cv2.INTER_CUBIC); a=cv2.GaussianBlur(a,(0,0),18); a=(a-a.min())/(a.max()-a.min()); return a
FOG=fog_tex()
def fog(a,i,alpha=0.22,ytop=0.45):
    off=int(i*1.6)%FOG.shape[1]; tex=np.roll(FOG,-off,axis=1)[:, :1920] if FOG.shape[1]>=1920 else np.tile(FOG,(1,2))[:,:1920]
    tex=cv2.resize(tex,(W,H//2)); full=np.zeros((H,W),np.float32); full[int(H*ytop):int(H*ytop)+H//2]=tex[:H-int(H*ytop)] if int(H*ytop)+H//2>H else tex
    return a*(1-alpha*full[...,None])+alpha*full[...,None]*np.array([170,172,180])
EM=[(rng.uniform(0.47,0.56),rng.uniform(0,3.0),rng.uniform(110,230),rng.uniform(-40,40)) for _ in range(70)]
def embers(a,i,fire=(0.52,0.74)):
    t=i/24; layer=np.zeros((H,W),np.float32)
    for x0,ph,sp,dr in EM:
        age=(t+ph)%3.0; y=fire[1]*H-age*sp; x=x0*W+dr*age+8*math.sin(age*4+ph*5)
        if 0<=x<W-2 and 0<=y<H-2: cv2.circle(layer,(int(x),int(y)),2,float(max(0,1-age/3.0)),-1)
    layer=cv2.GaussianBlur(layer,(0,0),1.2)
    return np.clip(a+layer[...,None]*np.array([255,150,60])*0.9,0,255)
def post(name,d,fns=()):
    fs=sorted(glob.glob(f"{d}/f*.png")); p=B.Pipe(name)
    for i,f in enumerate(fs):
        a=np.asarray(Image.open(f).convert("RGB"),np.float32)
        for fn in fns: a=fn(a,i)
        a=a+rng.normal(0,2.0,a.shape); p.w(B.vignette(a))
    p.close(); print("post",name,len(fs),flush=True)
def post_video(name,src,fns=()):
    cap=cv2.VideoCapture(src); p=B.Pipe(name); i=0
    while True:
        ok,fr=cap.read()
        if not ok: break
        a=cv2.cvtColor(fr,cv2.COLOR_BGR2RGB).astype(np.float32)
        for fn in fns: a=fn(a,i)
        p.w(a); i+=1
    p.close(); print("postv",name,i,flush=True)
def m2():
    fs=sorted(glob.glob("tx_M1/f*.png"))[:72]; p=B.Pipe("M2v2")
    for i,f in enumerate(fs):
        img=Image.open(f).convert("RGB"); t=B.ease(i/(len(fs)-1)); z=2.4+0.3*t
        a=np.asarray(B.view(img,0.07+0.02*t,0.70,z),np.float32); a=B.rain(a,i); a=a+rng.normal(0,2,a.shape); p.w(B.vignette(a))
    p.close(); print("M2v2",flush=True)
if __name__=="__main__":
    w=sys.argv[1:]
    J={"K1":lambda:post("K1v2","dd_K1"),"K2":lambda:post("K2v2","dd_K2"),
       "M1":lambda:post("M1v2","dd_M1",[lambda a,i:B.rain(a,i)]),
       "T1":lambda:post("T1v2","dd_T1",[embers]),"T6":lambda:post("T6v2","dd_T6"),"B1":lambda:post("B1v2","dd_B1"),
       "D5":lambda:post("D5v2","dd_D5",[lambda a,i:fog(a,i,0.28)]),"M2":m2,
       "W":lambda:post_video("Wv2","out/Wraw.mp4",[lambda a,i:fog(a,i,0.25,0.4)])}
    for k in (w or J): J[k]()
