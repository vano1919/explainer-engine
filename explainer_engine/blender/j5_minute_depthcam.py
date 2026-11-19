"""Depth-displaced 2.5D camera (Blender, Workbench texture): a picture and its depth map become a relief mesh; the camera moves over it.
usage: python depthcam.py IMAGE DEPTH OUTDIR SECONDS x0 x1 y0 y1 dolly0 dolly1 [relief] [fps]"""
import sys, math, numpy as np, bpy
from PIL import Image, ImageFilter
img,dep,out,sec=sys.argv[1:5]; sec=float(sec); x0,x1,y0,y1,d0,d1=map(float,sys.argv[5:11]); relief=float(sys.argv[11]) if len(sys.argv)>11 else 0.9
fps=24; n=int(float(sec)*fps); 
import os,glob
TEX=sorted(glob.glob(img+"/f*.png")) if os.path.isdir(img) else None
im=Image.open(TEX[0] if TEX else img); aspect=im.width/im.height
dp=Image.open(dep).convert("L").filter(ImageFilter.GaussianBlur(3)); D=np.asarray(dp,np.float32)/255
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene; sc.render.engine="BLENDER_WORKBENCH"; sc.render.resolution_x=1920; sc.render.resolution_y=1080
sc.render.image_settings.file_format="PNG"; sc.render.fps=fps
sh=sc.display.shading; sh.light="FLAT"; sh.color_type="TEXTURE"; sh.show_shadows=False; sh.show_cavity=False
sc.view_settings.view_transform="Standard"; sc.display_settings.display_device="sRGB"
sc.render.filter_size=1.0
sc.display.render_aa="8"
GX,GY=320,int(320/aspect)
xs=np.linspace(-aspect/2,aspect/2,GX+1); ys=np.linspace(0.5,-0.5,GY+1)
Dg=np.asarray(dp.resize((GX+1,GY+1),Image.BILINEAR),np.float32)/255
verts=[(xs[i],-relief*(Dg[j,i]-0.5)*0.0+0.0,ys[j]) for j in range(GY+1) for i in range(GX+1)]
# camera looks along +y; depth: near (white, Dg high) closer to camera => smaller y
verts=[(xs[i],(1.0-Dg[j,i])*relief,ys[j]) for j in range(GY+1) for i in range(GX+1)]
faces=[(j*(GX+1)+i,j*(GX+1)+i+1,(j+1)*(GX+1)+i+1,(j+1)*(GX+1)+i) for j in range(GY) for i in range(GX)]
me=bpy.data.meshes.new("relief"); me.from_pydata(verts,[],faces); me.update()
uv=me.uv_layers.new(name="uv")
for poly in me.polygons:
    for li,vi in zip(poly.loop_indices,poly.vertices):
        uv.data[li].uv=((vi%(GX+1))/GX,1-(vi//(GX+1))/GY)
ob=bpy.data.objects.new("relief",me); sc.collection.objects.link(ob)
mat=bpy.data.materials.new("m"); mat.use_nodes=True; nt=mat.node_tree
tx=nt.nodes.new("ShaderNodeTexImage"); tx.image=bpy.data.images.load(TEX[0] if TEX else img); tx.interpolation="Cubic"
bsdf=nt.nodes["Principled BSDF"]; nt.links.new(tx.outputs["Color"],bsdf.inputs["Base Color"]); ob.data.materials.append(mat)
cam=bpy.data.cameras.new("c"); cam.sensor_fit="VERTICAL"; cam.sensor_height=24; Lfar=1.2+relief; cam.lens=24*Lfar/1.15; cam.clip_start=0.01; cam.clip_end=50
co=bpy.data.objects.new("cam",cam); sc.collection.objects.link(co); sc.camera=co
base=-1.2   # plane centre ~ at y=relief/2; camera at y=base from origin so that it fills the frame
os_=out; 
import os; os.makedirs(out,exist_ok=True)
for i in range(n):
    t=i/max(n-1,1); t=t*t*(3-2*t)
    co.location=(x0+(x1-x0)*t, base+d0+(d1-d0)*t, y0+(y1-y0)*t); co.rotation_euler=(math.pi/2,0,0)
    if TEX:
        old=tx.image; tx.image=bpy.data.images.load(TEX[min(i,len(TEX)-1)]); bpy.data.images.remove(old)
    sc.render.filepath=f"{out}/f{i:04d}.png"; bpy.ops.render.render(write_still=True)
print("rendered",n)
