import math, subprocess, sys
import numpy as np
from PIL import Image
W,H,FPS,DUR=1920,1080,30,28.0
STILL=len(sys.argv)>1 and sys.argv[1]=="still"
def crop(n):
    im=Image.open(n+"_keyed.png"); bb=im.getchannel("A").point(lambda v:255 if v>40 else 0).getbbox(); return im.crop(bb)
RAW={k:crop(k) for k in ["sci_nansen","sci_franklin","sci_einstein","pose_nansen_drill","pose_nansen_proud","pose_franklin_blow","pose_einstein_lens","pose_einstein_amazed"]}
fire=crop("fire_clean")
BASE_H=330/RAW["sci_nansen"].height
_cache={}
def spr(k,mult):
    key=(k,round(mult,2))
    if key not in _cache:
        im=RAW[k]; s=BASE_H*mult; _cache[key]=im.resize((max(1,round(im.width*s)),max(1,round(im.height*s))),Image.LANCZOS)
    return _cache[key]
def fire_spr(mult):
    key=("fire",round(mult,2))
    if key not in _cache:
        s=BASE_H*0.55*mult; _cache[key]=fire.resize((round(fire.width*s),round(fire.height*s)),Image.LANCZOS)
    return _cache[key]
BG={n:np.asarray(Image.open(f"bg_{n}.png").convert("RGB").resize((W,H),Image.LANCZOS),dtype=np.float32)/255 for n in "bcdef"}
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
def ease(x): x=min(max(x,0),1); return x*x*(3-2*x)
def back(x):
    x=min(max(x,0),1); c=1.70158; return 1+(c+1)*(x-1)**3+c*(x-1)**2
# shots: (start,end,bg,ground,anchor_x,zoom0,zoom1,actor mult)
SHOTS=[(0,5.4,"b",880,620,1.0,1.05),(5.4,8.7,"c",900,900,1.0,1.08),(8.7,13.4,"d",900,760,1.0,1.08),
       (13.4,18.6,"e",920,700,1.0,1.08),(18.6,25.3,"b",880,640,1.12,1.18),(25.3,28.01,"f",890,760,1.0,1.06)]
T_SPARK=23.4
def bgframe(name,G,A,cam):
    x0=A-A/cam; y0=G-G/cam
    return np.asarray(Image.fromarray((BG[name]*255).astype(np.uint8)).transform((W,H),Image.AFFINE,(1/cam,0,x0,0,1/cam,y0),resample=Image.BICUBIC),dtype=np.float32)/255
def glow(fr,cx,cy,r,col,amt):
    g=np.exp(-(((xx-cx)**2+(yy-cy)**2)/(r*r)))[...,None]; return fr+g*np.array(col,np.float32)*amt
def shadow(fr,cx,G,w,a=0.35):
    sh=np.exp(-(((xx-cx)/w)**2+((yy-G-4)/(w*0.11))**2))[...,None]*a; return fr*(1-sh)
def put(base,im,cx,G,sx=1.0,sy=1.0,rot=0.0):
    if sx!=1 or sy!=1: im=im.resize((max(1,round(im.width*sx)),max(1,round(im.height*sy))),Image.BILINEAR)
    if rot: im=im.rotate(rot,resample=Image.BILINEAR,expand=True,center=(im.width/2,im.height))
    base.alpha_composite(im,(int(cx-im.width/2),int(G-im.height)))
def pop(t,t0,d=0.35,a=0.10):
    if t0<=t<t0+d: u=(t-t0)/d; return 1-a*(1-u),1+a*(1-u)
    return 1.0,1.0
def smoke(fr,x0,y0,t,sc):
    for i in range(14):
        ph=((t*0.8+i/14)%1.0); sx=x0+math.sin(i*2.3+t*2)*14*sc+ph*10*sc; sy=y0-ph*260*sc; r=(10+ph*34)*sc*1.3; a=0.30*(1-ph)
        ya,yb,xa,xb=int(max(0,sy-r)),int(min(H,sy+r)),int(max(0,sx-r)),int(min(W,sx+r))
        if yb>ya and xb>xa:
            gy,gx=np.mgrid[ya:yb,xa:xb]; m=np.exp(-(((gx-sx)**2+(gy-sy)**2)/(r*r*0.5)))[...,None]*a
            fr[ya:yb,xa:xb]=fr[ya:yb,xa:xb]*(1-m)+np.array([.88,.88,.88],np.float32)*m
    return fr
def draw(t):
    for (a,b,bg,G,A,z0,z1) in SHOTS:
        if a<=t<b: break
    u=(t-a)/(b-a); cam=z0+(z1-z0)*ease(u)
    fr=bgframe(bg,G,A,cam)
    fire_k=0.0
    # per-shot staging
    if bg=="b" and a==0:   # A: three stand
        acts=[("sci_einstein",290,1.0),("sci_nansen",520,1.0),("sci_franklin",1020,1.0)]
        ex=[("sci_einstein",290,1,0),("sci_nansen",520,1,0),("sci_franklin",1020,1,0)]
        m=1.0
    elif a==5.4:
        m=1.35
    elif a==8.7: m=1.35
    elif a==13.4: m=1.35
    elif a==18.6: m=1.0
    else: m=1.0
    cx_of=lambda x: A+(x-A)*cam   # follows zoom anchor
    sc=cam
    names=[]
    fr=fr*np.clip(1-0.10*(((xx-W/2)/(W/2))**2+((yy-H/2)/(H/2))**2),0.85,1)[...,None]
    base_list=[]  # (sprite_key, x, mult, sx, sy, rot)
    jitter=0
    if a==0:
        for k,x in (("sci_einstein",290),("sci_nansen",520),("sci_franklin",1020)):
            base_list.append((k,cx_of(x),m*cam,1,1+0.012*math.sin(t*2.1+x),0))
    elif a==5.4:
        sx_,sy_=pop(t,5.4)
        wob=math.sin(t*38)*3*(1 if t>5.9 else 0)
        base_list.append(("pose_nansen_drill",cx_of(900)+wob,m*cam,sx_,sy_,math.sin(t*38)*0.6))
    elif a==8.7:
        sx_,sy_=pop(t,8.7)
        base_list.append(("pose_franklin_blow",cx_of(760),m*cam,sx_,sy_*(1+0.015*math.sin(t*2.6)),0))
    elif a==13.4:
        sx_,sy_=pop(t,13.4)
        base_list.append(("pose_einstein_lens",cx_of(700),m*cam,sx_,sy_,0))
    elif a==18.6:
        drill=(t<T_SPARK+0.2)
        wob=math.sin(t*38)*3 if drill and (int((t-18.6)*0.9)%3!=2) else 0
        base_list.append(("pose_einstein_lens",cx_of(290),cam,1,1+0.01*math.sin(t*2),0))
        base_list.append(("pose_nansen_drill",cx_of(520)+wob,cam,1,1,math.sin(t*38)*0.6 if wob else 0))
        base_list.append(("pose_franklin_blow",cx_of(1020),cam,1,1+0.015*math.sin(t*2.6)+(0.03*math.sin((t-T_SPARK)*7) if t>T_SPARK+1.2 else 0),0))
    else:
        jump=lambda t0: abs(math.sin((t-t0)*5.0))*16*max(0,1-(t-t0)/2.0) if t>t0 else 0
        base_list.append(("pose_einstein_amazed",cx_of(470),cam,1,1,0,jump(25.8)))
        base_list.append(("pose_nansen_proud",cx_of(600),cam,1,1,0,jump(25.6)))
        base_list.append(("sci_franklin",cx_of(1050),cam,1,1,0,jump(26.0)))
    for it in base_list:
        fr=shadow(fr,it[1],G,spr(it[0],it[2]).width*0.45)
    img=Image.fromarray((np.clip(fr,0,1)*255+0.5).astype(np.uint8)).convert("RGBA")
    for it in base_list:
        k,x,mm,sx_,sy_,rot=it[:6]; lift=it[6] if len(it)>6 else 0
        put(img,spr(k,mm),x,G-lift,sx_,sy_,rot)
    fr=np.asarray(img.convert("RGB"),dtype=np.float32)/255
    # effects
    def feet(i): return base_list[i][1]
    if a==5.4 and t>5.8:
        fr=smoke(fr,feet(0)+95*BASE_H*(1/BASE_H)*0.0+ spr("pose_nansen_drill",m*cam).width*0.30,G-30*m*cam,t,m*cam*0.9)
    if a==8.7 and t>9.0:
        s_=spr("pose_franklin_blow",m*cam); gx=feet(0)-s_.width*0.30; gy=G-s_.height*0.38
        g=min(1,(t-9.0)/3); fr=glow(fr,gx,gy,45*m*cam,(1.0,.55,.15),0.5*g*(0.8+0.2*math.sin(t*20)))
        for i in range(8):
            ph=((t*0.9+i/8)%1.0); fr=glow(fr,gx+math.sin(i*3+t)*20*m,gy-ph*80*m,4*m,(1,.8,.5),0.5*(1-ph)*g)
    if a==13.4 and t>13.7:
        s_=spr("pose_einstein_lens",m*cam); lx=feet(0)-s_.width*0.33; ly=G-s_.height*0.78
        pul=0.7+0.3*math.sin(t*6)
        fr=glow(fr,lx,ly,60*m*cam,(1,.95,.7),0.8*pul)
        tx,ty=lx+300*m*cam,G-8
        for j in range(50):
            q=j/49; fr=glow(fr,lx+(tx-lx)*q,ly+(ty-ly)*q,4+6*q,(1,.9,.5),0.06+0.10*q)
        fr=glow(fr,tx,ty,10+14*math.sin(t*9)**2,(1,.85,.4),0.9*ease((t-13.7)/3))
    if a==18.6:
        s1=spr("pose_einstein_lens",cam); lx=feet(0)-s1.width*0.33; ly=G-s1.height*0.78
        fr=glow(fr,lx,ly,40*cam,(1,.95,.7),0.7*(0.7+0.3*math.sin(t*6)))
        s3=spr("pose_franklin_blow",cam); emx=feet(2)-s3.width*0.30; emy=G-s3.height*0.38
        s2=spr("pose_nansen_drill",cam)
        if t<T_SPARK+0.2: fr=smoke(fr,feet(1)+s2.width*0.30,G-30*cam,t,cam*0.8)
        if t>=T_SPARK:
            g=min(1,(t-T_SPARK)/1.6); fr=glow(fr,emx,emy,45*cam*(1+g),(1.0,.55,.15),0.6*g*(0.8+0.2*math.sin(t*20)))
        if T_SPARK-0.6<t<T_SPARK+0.1:
            q=(t-(T_SPARK-0.6))/0.7; sx0=feet(1)+s2.width*0.3; sy0=G-40*cam
            fr=glow(fr,sx0+(emx-sx0)*q,sy0+(emy-sy0)*q-math.sin(q*math.pi)*110*cam,9,(1,.85,.45),1.3)
    if a==25.3:
        u=(t-25.3)/0.6; sc_=back(u) if u<1 else 1.0; sc_=max(sc_,0.01)
        fx=cx_of(800); fl=1+0.025*math.sin(t*17)+0.02*math.sin(t*29)
        img=Image.fromarray((np.clip(fr,0,1)*255+0.5).astype(np.uint8)).convert("RGBA")
        put(img,fire_spr(cam*1.2),fx,G+8,sc_,sc_*fl)
        fr=np.asarray(img.convert("RGB"),dtype=np.float32)/255
        k2=ease((t-25.3)/0.8)
        fr=glow(fr,fx,G-60,300,(1.0,.55,.22),0.26*k2*(0.9+0.1*math.sin(t*13)))
        for i in range(34):
            ph=((t-25.3)*0.55+i/34)%1.0; ex_=fx+math.sin(i*5.1+t*2)*35+(i%7-3)*ph*12; ey_=G-90-ph*330
            fr=glow(fr,ex_,ey_,3+((i*7)%3),(1,.7,.3),0.9*(1-ph))
    fr=np.clip(fr,0,1)
    # crossfade into next shot (last 0.2 s handled by blending with next)
    return fr
def frame(t):
    f=draw(t)
    for (a,b,*_) in SHOTS:
        if 0<a<=t<a+0.2:   # soft cut-in from previous shot
            p=draw(a-0.001); q=(t-a)/0.2; f=p*(1-q)+f*q
    return f
if STILL:
    ts=[3,7,11,16,21,24.5,26.5,27.7]
    for t in ts: Image.fromarray((frame(t)*255+0.5).astype(np.uint8)).save(f"s2_{t}.png")
    s=Image.new("RGB",(960*2,540*4))
    for i,t in enumerate(ts): s.paste(Image.open(f"s2_{t}.png").resize((960,540)),((i%2)*960,(i//2)*540))
    s.save("s2_sheet.png"); sys.exit()
ff=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-c:v","libx264","-crf","17","-pix_fmt","yuv420p","fire_scene_silent.mp4"],stdin=subprocess.PIPE)
for i in range(int(DUR*FPS)): ff.stdin.write((frame(i/FPS)*255+0.5).astype(np.uint8).tobytes())
ff.stdin.close(); ff.wait(); print("done")
