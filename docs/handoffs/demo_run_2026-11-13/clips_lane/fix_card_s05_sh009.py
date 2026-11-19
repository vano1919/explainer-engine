"""FL-312 (audit round 4): the portrait card in S05_SH009 shows a moustached man; the story says Friedrich's wife and daughter
(S05_SH010 shows the card with a woman). Free local fix, no model call: the woman of S05_SH010's card (same card, same sepia
style) is fitted into the card of S05_SH009 inside the card's own paper border, the glove stays in front.
Usage: python fix_card_s05_sh009.py <S05_SH009 picture> <S05_SH010 picture> <out png>"""
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

b = Image.open(sys.argv[1]).convert("RGB")
a = Image.open(sys.argv[2]).convert("RGB")
src = a.crop((1300, 665, 1490, 890))                       # the woman, head and shoulders (190x225)
x0, y0, x1, y1 = 1475, 962, 1698, 1244
tw, th = x1 - x0, y1 - y0
src = src.resize((tw, th), Image.LANCZOS)
old = np.asarray(b.crop((x0, y0, x1, y1)).convert("L"), np.float32)
new = np.asarray(src.convert("L"), np.float32)
# match the grey level and contrast of the old portrait, then give it the old card's sepia
new = (new - new.mean()) / (new.std() + 1e-6) * old.std() + old.mean()
new = np.clip(new, 0, 255)
tone = np.asarray(b.crop((x0, y0, x1, y1)), np.float32)
light = tone[old > np.percentile(old, 40)]                              # the card's own paper and sepia (one hue, no ghost of the old face)
hue = np.median(light, axis=0) / max(float(np.median(light)), 1.0)
rgb = np.clip(new[..., None] * hue[None, None, :], 0, 255).astype(np.uint8)
# mask: the card's inner area minus the glove in front of its lower right corner
m = Image.new("L", b.size, 0)
d = ImageDraw.Draw(m)
d.polygon([(1500, 990), (1658, 968), (1691, 1110), (1700, 1240), (1522, 1240)], fill=255)
d.polygon([(1700, 1116), (1662, 1122), (1626, 1140), (1606, 1165), (1596, 1190), (1599, 1215), (1592, 1246), (1710, 1246)], fill=0)
m = m.filter(ImageFilter.GaussianBlur(3))
canvas = b.copy()
patch = Image.new("RGB", b.size)
patch.paste(Image.fromarray(rgb), (x0, y0))
canvas = Image.composite(patch, canvas, m)
canvas.save(sys.argv[3])
print(sys.argv[3])
