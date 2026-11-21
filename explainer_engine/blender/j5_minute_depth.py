import torch, numpy as np
from transformers import pipeline
from PIL import Image
pipe=pipeline("depth-estimation",model="depth-anything/Depth-Anything-V2-Small-hf",device=-1)
R="in/route_test_2026-11/assets/"
for n in ["A/A1_tent","A/A3_field","D2/D1_ford_90","D2/D2_duel_90","D2/D4_rain_90","D2/D5_after_90","D2/D6_eyes_90"]:
    im=Image.open(R+n+".png").convert("RGB"); d=pipe(im)["depth"]; d=np.asarray(d,np.float32); d=(d-d.min())/(d.max()-d.min()+1e-6)
    Image.fromarray((d*255).astype(np.uint8)).save("depth/"+n.split("/")[1]+".png"); print(n,d.shape,flush=True)
