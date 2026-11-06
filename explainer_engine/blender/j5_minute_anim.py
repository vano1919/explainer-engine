"""Animated textures (free, Python): local motion on a picture, driven by colour and depth masks; frame i of a picture -> texture frame for the Blender relief camera."""
import sys, os, numpy as np, cv2, math
from PIL import Image
R="in/route_test_2026-11/assets/"
def load(p): return cv2.cvtColor(cv2.imread(R+p),cv2.COLOR_BGR2RGB)
def hsv(img): return cv2.cvtColor(img,cv2.COLOR_RGB2HSV_FULL).astype(np.float32)
def soft(m,s=7): return cv2.GaussianBlur(m.astype(np.float32),(0,0),s)
def remap(img,dx,dy):
    h,w=img.shape[:2]; gx,gy=np.meshgrid(np.arange(w,dtype=np.float32),np.arange(h,dtype=np.float32))
    return cv2.remap(img,gx+dx.astype(np.float32),gy+dy.astype(np.float32),cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
def hue_mask(img,h0,h1,smin=0.25,vmin=0.12):
    H=hsv(img); h=H[...,0]*360/255; s=H[...,1]/255; v=H[...,2]/255
    return ((h>=h0)&(h<=h1)&(s>=smin)&(v>=vmin)).astype(np.float32)
def make(name,pic,depthname,sec,fx,fps=24):
    img=load(pic); h,w=img.shape[:2]; d=np.asarray(Image.open(f"depth/{depthname}.png").convert("L").resize((w,h)),np.float32)/255
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32); out=f"tx_{name}"; os.makedirs(out,exist_ok=True); n=int(sec*fps)
    pre=fx(img,d,xx,yy,h,w)
    for i in range(n):
        t=i/fps; dx,dy,post=pre(t,i)
        fr=remap(img,dx,dy)
        if post is not None: fr=post(fr)
        cv2.imwrite(f"{out}/f{i:04d}.png",cv2.cvtColor(fr,cv2.COLOR_RGB2BGR))
    print("tex",name,n,flush=True)
# ---- per picture effects: each returns f(t,i)->(dx,dy,postfn)
def fx_march(img,d,xx,yy,h,w):
    sold=soft(hue_mask(img,150,215,0.2,0.1),4)*(yy>h*0.28)
    flag=soft(hue_mask(img,340,360,0.5,0.3)+hue_mask(img,0,18,0.5,0.3),3)*(yy<h*0.32)*(xx>w*0.5)
    def f(t,i):
        ph=2*math.pi*2.0*t-8.0*d                        # a bob that travels down the column: each soldier a beat later
        dy=-3.2*np.sin(ph)*sold*(0.4+d)
        dx=1.5*np.sin(ph+0.7)*sold+ 6*np.sin(2*math.pi*0.9*t+xx*0.03)*flag
        dy=dy+3*np.sin(2*math.pi*0.9*t+xx*0.04)*flag
        return dx,dy,None
    return f
def fx_water(img,d,xx,yy,h,w):
    water=soft(hue_mask(img,190,250,0.2,0.1)+hue_mask(img,10,40,0.6,0.5)*(yy>h*0.4)*(xx<w*0.45),6)*(yy>h*0.36)
    smoke=soft((np.asarray(cv2.cvtColor(img,cv2.COLOR_RGB2GRAY),np.float32)>150)*(yy<h*0.4)*(hsv(img)[...,1]<60),5)
    crowd=soft(hue_mask(img,0,30,0.3,0.15),8)*(xx>w*0.65)*(yy>h*0.35)
    def f(t,i):
        dx=3.0*np.sin(2*math.pi*0.7*t+yy*0.045+xx*0.01)*water+4*np.sin(2*math.pi*0.45*t-yy*0.05)*smoke
        dy=1.2*np.sin(2*math.pi*0.9*t+xx*0.03)*water-3.0*np.abs(np.sin(2*math.pi*1.3*t+xx*0.06))*crowd*(0.3+d)
        return dx,dy,None
    return f
def fx_duel(img,d,xx,yy,h,w):
    ring=soft(((yy<h*0.62)&((xx<w*0.33)|(xx>w*0.66))).astype(np.float32),25)
    G=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY).astype(np.float32); c=(G*(1-0)).copy(); c[:int(h*0.15)]=0; c[int(h*0.65):]=0; c[:,:int(w*0.3)]=0; c[:,int(w*0.75):]=0
    py,px=np.unravel_index(np.argmax(cv2.GaussianBlur(c,(0,0),6)),c.shape)
    def f(t,i):
        dy=-2.0*np.abs(np.sin(2*math.pi*1.2*t+xx*0.05))*ring; dx=1.2*np.sin(2*math.pi*0.8*t+yy*0.03)*ring
        def post(fr):
            k=max(0,math.sin(2*math.pi*2.2*t))**8      # blades clash about twice a second
            if k>0.02:
                g=np.exp(-(((xx-px)**2+(yy-py)**2)/(2*(22+30*k)**2)))
                fr=np.clip(fr.astype(np.float32)+g[...,None]*k*np.array([255,230,150])*1.0,0,255).astype(np.uint8)
            return fr
        return dx,dy,post
    return f
def fx_camp(img,d,xx,yy,h,w):
    ban=soft(hue_mask(img,0,30,0.45,0.3)*(yy<h*0.5),3)
    fire=np.exp(-(((xx-w*0.50)**2+(yy-h*0.70)**2)/(2*60**2))) if False else None
    H=hsv(img); br=(H[...,2]>215)&(H[...,1]>140)&(H[...,0]*360/255<60)&(yy>h*0.45)
    ys,xs=np.nonzero(br); fx0,fy0=(xs.mean(),ys.mean()) if len(xs) else (w*0.5,h*0.7)
    flame=soft(br.astype(np.float32),3)
    def f(t,i):
        dx=5*np.sin(2*math.pi*0.8*t+xx*0.03)*ban+ 3.0*np.sin(2*math.pi*3.1*t+yy*0.2)*flame
        dy=2*np.sin(2*math.pi*0.8*t+xx*0.04)*ban-4.0*np.abs(np.sin(2*math.pi*2.3*t+xx*0.1))*flame
        def post(fr):
            g=np.exp(-(((xx-fx0)**2+(yy-fy0)**2)/(2*(w*0.12)**2)))
            k=1+0.12*math.sin(i*0.9)+0.07*math.sin(i*2.3+1)
            return np.clip(fr.astype(np.float32)*(1+(k-1)*g[...,None]*1.6),0,255).astype(np.uint8)
        return dx,dy,post
    return f
def fx_dawn(img,d,xx,yy,h,w):
    cloak=soft((yy>h*0.3)&(d>0.55),6)
    def f(t,i):
        dx=2.5*np.sin(2*math.pi*0.25*t+yy*0.02)*(yy<h*0.55)*(d<0.5)
        dy=0.8*np.sin(2*math.pi*0.3*t+xx*0.03)*cloak
        return dx,dy,None
    return f
def fx_eyes(img,d,xx,yy,h,w):
    flame=soft(hue_mask(img,10,50,0.5,0.55)*(xx<w*0.25),3)
    def f(t,i):
        dx=4*np.sin(2*math.pi*3.4*t+yy*0.15)*flame; dy=-5*np.abs(np.sin(2*math.pi*2.1*t))*flame
        s=1+0.004*math.sin(2*math.pi*0.35*t)                  # breathing
        return dx+(xx-w/2)*(1-s),dy+(yy-h/2)*(1-s),(lambda fr:np.clip(fr.astype(np.float32)*(1+0.03*math.sin(i*1.3)),0,255).astype(np.uint8))
    return f
def fx_court(img,d,xx,yy,h,w):
    ban=soft(hue_mask(img,0,20,0.4,0.3)+hue_mask(img,100,150,0.3,0.3),3)*(yy<h*0.5)
    def f(t,i): return 5*np.sin(2*math.pi*0.8*t+xx*0.03)*ban,2*np.sin(2*math.pi*0.8*t+xx*0.04)*ban,None
    return f
JOBS={"K1":("A/A2_courtyard.png","A2_courtyard",5.0,fx_court),"K2":("D2/D2_duel_90.png","D2_duel_90",5.0,fx_duel),
 "M1":("D2/D4_rain_90.png","D4_rain_90",4.0,fx_march),"T1":("A/A1_tent.png","A1_tent",4.0,fx_camp),
 "T6":("D2/D6_eyes_90.png","D6_eyes_90",5.0,fx_eyes),"B1":("D2/D1_ford_90.png","D1_ford_90",5.0,fx_water),
 "D5":("D2/D5_after_90.png","D5_after_90",4.0,fx_dawn)}
if __name__=="__main__":
    for k in (sys.argv[1:] or JOBS):
        p,dn,s,fx=JOBS[k]; make(k,p,dn,s,fx)
