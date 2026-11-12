import numpy as np, subprocess, sys, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
R="/tmp/claude-0/minute/in/route_test_2026-11/assets/"; W,H,FPS=1920,1080,24
rng=np.random.default_rng(7)
def load(p): return Image.open(R+p).convert("RGB")
def ease(t): return t*t*(3-2*t)
def view(img,cx,cy,zoom,out=(W,H)):
    """crop window of size (iw/zoom) centred (cx,cy in 0..1) from img, resized to out"""
    iw,ih=img.size; ar=out[0]/out[1]
    ch=ih/zoom; cw=ch*ar
    if cw>iw: cw=iw; ch=cw/ar
    x0=min(max(cx*iw-cw/2,0),iw-cw); y0=min(max(cy*ih-ch/2,0),ih-ch)
    return img.resize(out,Image.LANCZOS,box=(x0,y0,x0+cw,y0+ch))
def rain(frame,i,density=1.0,alpha=0.35):
    a=np.zeros((H,W),np.float32)
    n=int(900*density); r=np.random.default_rng(100+i)
    xs=r.integers(0,W,n); ys=r.integers(0,H,n); L=r.integers(30,70,n)
    for x,y,l in zip(xs,ys,L):
        for k in range(l):
            yy=y+k; xx=x-k//4
            if 0<=yy<H and 0<=xx<W: a[yy,xx]=1
    a=np.array(Image.fromarray((a*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)),np.float32)/255
    return np.clip(frame+ (a[...,None]*alpha*255*np.array([0.8,0.85,1.0])),0,255)
def vignette(f,s=0.25):
    y,x=np.mgrid[0:H,0:W]; d=np.sqrt(((x-W/2)/(W/2))**2+((y-H/2)/(H/2))**2)
    return f*(1-s*np.clip(d-0.5,0,1)[...,None])
class Pipe:
    def __init__(s,name):
        s.p=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-c:v","libx264","-preset","veryfast","-crf","16","-pix_fmt","yuv420p",f"/tmp/claude-0/minute/out/{name}.mp4"],stdin=subprocess.PIPE)
    def w(s,a): s.p.stdin.write(np.clip(a,0,255).astype(np.uint8).tobytes())
    def close(s): s.p.stdin.close(); s.p.wait()
def kb(name,img,sec,z0,z1,c0,c1,rainy=False,grain=True):
    n=int(sec*FPS); p=Pipe(name)
    for i in range(n):
        t=ease(i/max(n-1,1)); z=z0+(z1-z0)*t; cx=c0[0]+(c1[0]-c0[0])*t; cy=c0[1]+(c1[1]-c0[1])*t
        f=np.asarray(view(img,cx,cy,z),np.float32)
        if rainy: f=rain(f,i)
        if grain: f=f+rng.normal(0,2.2,f.shape)
        p.w(vignette(f))
    p.close()
def parallax(name,img,sec,bands,drift=60,zoom=1.12,flicker=None):
    """3 depth layers by vertical bands (far top, mid, near bottom) with feathered masks; the camera tracks sideways, the near layer moves more"""
    n=int(sec*FPS); big=img.resize((int(W*zoom*1.25),int(H*zoom*1.25)),Image.LANCZOS); bw,bh=big.size
    arr=np.asarray(big,np.float32); y=np.arange(H)[:,None]
    m_far=np.clip((bands[0]-y/H)/0.08+0.5,0,1); m_near=np.clip((y/H-bands[1])/0.08+0.5,0,1); m_mid=1-m_far-m_near+0*m_far
    m_mid=np.clip(m_mid,0,1)
    p=Pipe(name)
    for i in range(n):
        t=ease(i/max(n-1,1)); out=np.zeros((H,W,3),np.float32)
        for m,spd in ((m_far,0.4),(m_mid,1.0),(m_near,1.9)):
            ox=int((bw-W)/2+(t-0.5)*drift*spd*2); oy=int((bh-H)/2)
            out+=arr[oy:oy+H,ox:ox+W]*m[...,None]
        if flicker:
            fx,fy,r=flicker; yy,xx=np.mgrid[0:H,0:W]; g=np.exp(-(((xx-fx)**2+(yy-fy)**2)/(2*r*r)))
            k=1+0.10*math.sin(i*0.9)+0.06*math.sin(i*2.3+1)+0.04*rng.normal()
            out=out*(1+(k-1)*g[...,None]*1.5)
        out=out+rng.normal(0,2.0,out.shape); p.w(vignette(out))
    p.close()
def cutout(img,thresh=28):
    a=np.asarray(img,np.int16); bg=a[5:20,5:20].reshape(-1,3).mean(0)
    d=np.abs(a-bg).sum(2); m=(d>thresh).astype(np.uint8)*255
    m=Image.fromarray(m).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    rgba=img.convert("RGBA"); rgba.putalpha(m); return rgba.crop(rgba.getbbox())
def card_shot(name,plate,card,sec,card_h,cx,base,walk=False,cam=(1.0,1.08),dark=1.0,scroll=0,pan_blur=False):
    n=int(sec*FPS); pl=plate.resize((int(plate.width*H/plate.height*1.3),int(H*1.3)),Image.LANCZOS)
    c=card.resize((int(card.width*card_h/card.height),card_h),Image.LANCZOS); p=Pipe(name)
    pa=np.asarray(pl,np.float32)*dark
    for i in range(n):
        t=ease(i/max(n-1,1)); z=cam[0]+(cam[1]-cam[0])*t
        ox=int((pl.width-W)/2+scroll*(t-0.5)*2)
        bg=Image.fromarray(np.clip(pa[int(H*0.15):int(H*0.15)+H,max(ox,0):max(ox,0)+W],0,255).astype(np.uint8))
        bob=int(8*abs(math.sin(i*0.33))) if walk else int(3*math.sin(i*0.12))
        sway=math.sin(i*0.17)*(1.5 if walk else 0.4)
        cc=c.rotate(sway,expand=True,resample=Image.BICUBIC)
        sh=Image.new("RGBA",bg.size,(0,0,0,0)); ds=ImageDraw.Draw(sh)
        ds.ellipse((cx-cc.width*0.35,base-14,cx+cc.width*0.35,base+14),fill=(0,0,0,110)); sh=sh.filter(ImageFilter.GaussianBlur(10))
        bg=bg.convert("RGBA"); bg.alpha_composite(sh); bg.alpha_composite(cc,(int(cx-cc.width/2),int(base-cc.height-bob)))
        f=np.asarray(bg.convert("RGB"),np.float32)
        if z!=1: f=np.asarray(Image.fromarray(f.astype(np.uint8)).resize((W,H),Image.LANCZOS,box=(W*(1-1/z)/2,H*(1-1/z)/2,W-W*(1-1/z)/2,H-H*(1-1/z)/2)),np.float32)
        p.w(vignette(f+rng.normal(0,2,f.shape)))
    p.close()
def font(sz,bold=False):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"):
        try: return ImageFont.truetype(f,sz)
        except Exception: pass
    return ImageFont.load_default()
def map_shot(name,sec):
    n=int(sec*FPS); p=Pipe(name)
    base=Image.new("RGB",(W,H),(214,190,146)); noise=rng.normal(0,9,(H,W,1)); b=np.clip(np.asarray(base,np.float32)+noise,0,255)
    pts=[(240,820),(520,640),(760,760),(1060,520),(1340,600),(1640,330)]
    d=Image.fromarray(b.astype(np.uint8)); dr=ImageDraw.Draw(d)
    for k in range(40):
        x=rng.integers(0,W); y=rng.integers(0,H); dr.polygon([(x,y),(x+60,y+90),(x+120,y)],outline=(120,95,60))
    dr.text((90,70),"THE ROAD TO THE FORD",font=font(54),fill=(70,45,25))
    base=d.copy(); n_pts=len(pts)
    for i in range(n):
        t=ease(i/(n-1)); im=base.copy(); dr=ImageDraw.Draw(im)
        seg=t*(n_pts-1); k=int(seg); fr=seg-k
        for a in range(min(k,n_pts-1)): dr.line([pts[a],pts[a+1]],fill=(150,30,25),width=9)
        if k<n_pts-1:
            x=pts[k][0]+(pts[k+1][0]-pts[k][0])*fr; y=pts[k][1]+(pts[k+1][1]-pts[k][1])*fr
            dr.line([pts[k],(x,y)],fill=(150,30,25),width=9); dr.ellipse((x-14,y-14,x+14,y+14),fill=(150,30,25))
        for q in pts: dr.ellipse((q[0]-8,q[1]-8,q[0]+8,q[1]+8),outline=(70,45,25),width=4)
        a=np.asarray(im,np.float32); p.w(vignette(a+rng.normal(0,2,a.shape),0.3))
    p.close()
def title_shot(name,sec):
    n=int(sec*FPS); p=Pipe(name); im=Image.new("RGB",(W,H),(12,10,14)); dr=ImageDraw.Draw(im)
    for txt,y,sz in (("THE COMMANDER'S LAST NIGHT",470,70),("a J5 test minute",600,34)):
        w=dr.textlength(txt,font=font(sz)); dr.text(((W-w)/2,y),txt,font=font(sz),fill=(222,200,160))
    a=np.asarray(im,np.float32)
    for i in range(n): p.w(a)
    p.close()
if __name__=="__main__":
    which=sys.argv[1:]
    D4=load("D2/D4_rain_90.png"); A1=load("A/A1_tent.png"); A3=load("A/A3_field.png"); D1=load("D2/D1_ford_90.png"); D2=load("D2/D2_duel_90.png"); D5=load("D2/D5_after_90.png"); D6=load("D2/D6_eyes_90.png")
    H1=cutout(load("B/B_H1_back.png")); H3=cutout(load("B/B_H3_front.png"))
    jobs={
     "M0_map":lambda:map_shot("M0_map",3.0),
     "M1":lambda:kb("M1",D4,5.0,1.0,1.08,(0.5,0.5),(0.45,0.52),rainy=True),
     "M2":lambda:kb("M2",D4,4.0,3.2,3.6,(0.07,0.72),(0.09,0.70),rainy=True),
     "M3":lambda:card_shot("M3",A3,H1,7.5,820,860,1010,walk=True,cam=(1.0,1.1),dark=0.85,scroll=-160),
     "T1":lambda:parallax("T1",A1,5.0,(0.38,0.62),drift=70,flicker=(1000,730,170)),
     "T5":lambda:card_shot("T5",A1.filter(ImageFilter.GaussianBlur(8)),H3,2.0,860,960,1040,cam=(1.0,1.07),dark=0.55),
     "T6":lambda:kb("T6",D6,5.0,1.0,1.12,(0.5,0.5),(0.46,0.46)),
     "B1":lambda:parallax("B1",D1,5.0,(0.30,0.62),drift=80,zoom=1.15),
     "B2":lambda:kb("B2",D2,5.0,1.0,1.12,(0.5,0.5),(0.52,0.48)),
     "A1_after":lambda:kb("A1_after",D5,5.0,1.1,1.0,(0.5,0.5),(0.5,0.5)),
     "A2":lambda:title_shot("A2",4.5),
    }
    for k in (which or jobs): jobs[k](); print("done",k,flush=True)
