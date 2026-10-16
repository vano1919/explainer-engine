import sys, concurrent.futures as cf, time
sys.path.insert(0, ".")
from gen import gen
REF = "../a_idle.png"
BASE = ("Painted storybook illustration, same art style, line quality and palette as the reference image (the reference is only a STYLE guide; "
 "do not copy its character). A friendly CARICATURE of the historical scientist {who}: head about 1.6x oversized, exaggerated but kind and instantly "
 "recognisable features from well-known historical portraits (hair, face shape, moustache, clothing of their era), expressive. Full body, standing, "
 "{act}. Adult, dignified-comic, not childish. One figure only, feet visible, no text, no letters, no logo. Flat solid pure green #00FF00 background, "
 "no shadow on the background, no green on the figure.")
S = {
 "newton": ("Isaac Newton", "long curly wig, 17th-century coat, holding a prism in one hand and looking at it intensely, an apple tucked under the other arm"),
 "einstein": ("Albert Einstein", "wild white hair, bushy moustache, rumpled cardigan, no socks, scribbling an equation in the air with a chalk stick, dreamy smile"),
 "curie": ("Marie Curie", "dark hair tied back, plain dark long dress with apron, holding a glass flask glowing faintly, focused determined look"),
 "darwin": ("Charles Darwin", "huge white beard, bald forehead, dark frock coat, kneeling slightly with a magnifying lens examining a small beetle in his palm"),
 "tesla": ("Nikola Tesla", "tall thin, sharp moustache, slicked dark hair, long dark coat, holding a glowing bulb without wires in one hand, sparks around the other hand"),
 "archimedes": ("Archimedes", "ancient Greek, curly beard, simple tunic, sandals, drawing a circle in the sand with a stick, holding a lever"),
 "franklin": ("Benjamin Franklin", "long thin grey hair, round spectacles, 18th-century brown coat and breeches, holding a kite string, clever grin"),
 "nansen": ("Fridtjof Nansen", "Norwegian polar explorer, strong jaw, fur-trimmed hooded parka, snow goggles pushed up, carrying a coil of rope and an ice axe"),
}
def job(k):
    who, act = S[k]
    return gen("sci_"+k, BASE.format(who=who, act=act), [REF], aspect="3:4")
with cf.ThreadPoolExecutor(3) as ex:
    list(ex.map(job, S))
