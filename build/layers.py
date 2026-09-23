"""Split the source illustration into animation layers.

Outputs (build/layers/):
  bg.png            the scene with the raised arm, chopsticks, jeon and eyes removed and the gaps rebuilt
  arm.png           sleeve + cuff + glove, rotated about the elbow by the SVG
  jeon.png          the held jeon with the chopstick painted out
  eye*/dot*.png     glowing eyes and blush dots as soft-edged sprites
  meta.json         bounding box (x0, y0, x1, y1) of every sprite in source pixels
"""
import json
from pathlib import Path
import numpy as np, cv2
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'layers'
src = cv2.cvtColor(np.array(Image.open(ROOT.parent / 'source' / 'chuseok.webp').convert('RGB')), cv2.COLOR_RGB2BGR)
H, W = src.shape[:2]

def poly_mask(pts, scale=4):
    m = np.zeros((H*scale, W*scale), np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.float32).__mul__(scale).astype(np.int32)], 255, cv2.LINE_AA)
    return cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA)

def line_mask(p0, p1, w):
    m = np.zeros((H*4, W*4), np.uint8)
    cv2.line(m, tuple(int(v*4) for v in p0), tuple(int(v*4) for v in p1), 255, int(w*4), cv2.LINE_AA)
    return cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA)

# ---- arm (sleeve + cuff + glove) ----
ARM = [(280,660),(283,643),(300,625),(325,612),(350,598),(372,592),(386,578),(400,556),(420,548),
       (450,548),(465,556),(476,575),(479,595),(475,618),(465,637),(455,648),(456,670),(456,705),
       (440,716),(415,728),(385,740),(350,750),(320,753),(295,747),(280,725)]
arm = poly_mask(ARM)

# ---- chopsticks ----
STICK_U = ((352,580.5),(578,527))
STICK_L = ((356,601),(534,548))
sticks = np.maximum(line_mask(*STICK_U, 8), line_mask(*STICK_L, 8))

# ---- jeon (colour segmentation inside its bbox) ----
bx0,by0,bx1,by1 = 505,486,630,600
hsv = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)
roi = hsv[by0:by1, bx0:bx1]
h,s,v = roi[...,0].astype(int), roi[...,1].astype(int), roi[...,2].astype(int)
yel = ((h>=8)&(h<=35)&(s>135)&(v>110)).astype(np.uint8)*255
yel = cv2.morphologyEx(yel, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9)))
n, lab, stats, _ = cv2.connectedComponentsWithStats(yel)
big = 1+np.argmax(stats[1:,cv2.CC_STAT_AREA])
yel = (lab==big).astype(np.uint8)*255
# fill holes
ff = cv2.copyMakeBorder(yel,1,1,1,1,cv2.BORDER_CONSTANT,value=0); cv2.floodFill(ff, None, (0,0), 255); yel = yel | cv2.bitwise_not(ff[1:-1,1:-1])
jeon = np.zeros((H,W),np.uint8); jeon[by0:by1,bx0:bx1] = yel

# ================= background reconstruction =================
def dil(m, r):
    return cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*r+1,2*r+1)))
def feather_comp(base, fill, region, grow=2, blur=1.6):
    a = cv2.GaussianBlur(dil(region,grow).astype(np.float32)/255, (0,0), blur)[...,None]
    return (base*(1-a) + fill*a).astype(np.uint8)
yy, xx = np.mgrid[0:H, 0:W]

# --- 1. eyes & blush dots -> separate glow layers, erased from the screen
# every bright blob on the screen is assigned to the nearest seed, so each sprite owns only its own glow
SEEDS = {'eyeL': (487,472), 'eyeR': (637,436), 'dotL': (443,520), 'dotR': (689,466)}
WINS  = {'eyeL': (435,435,540,510), 'eyeR': (585,400,690,475), 'dotL': (425,505,462,535), 'dotR': (668,450,710,482)}
gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
scr = np.zeros((H,W),np.uint8); scr[395:545, 405:725] = 255
core = ((gray > 110) & (scr > 0) & (jeon == 0) & (sticks < 10)).astype(np.uint8)*255
n, lab, stats, cent = cv2.connectedComponentsWithStats(core)
own = {k: np.zeros((H,W),np.uint8) for k in SEEDS}
for i in range(1, n):
    x, y, w, h, area = stats[i]
    k = min(SEEDS, key=lambda k: np.hypot(*(cent[i] - SEEDS[k])))
    # keep only blobs lying wholly inside that sprite's window (drops specks and the white shell)
    wx0, wy0, wx1, wy1 = WINS[k]
    if area < 4 or x < wx0 or y < wy0 or x + w > wx1 or y + h > wy1: continue
    own[k][lab == i] = 255
glow = {k: dil(m, 14) for k, m in own.items()}
eyes_glow = np.maximum.reduce(list(glow.values()))
bg0 = cv2.inpaint(src, eyes_glow, 12, cv2.INPAINT_TELEA)
bg0 = feather_comp(src, bg0, eyes_glow, 1, 1.5)

# --- 2. holes
hole_j = np.maximum(dil(jeon, 8), dil(sticks, 4))
hole_a = dil(arm, 4)
hole = np.maximum(hole_j, hole_a)
known = (hole==0)
work = bg0.copy().astype(np.float32)
setm = np.zeros((H,W),bool)
to8 = lambda m: m.astype(np.uint8)*255
def curve(pts):
    xs, ys = zip(*pts); return np.interp(xx, xs, ys)
# bottom edge of the face screen, and the bottom (chin) of the white head shell
E = curve([(380,505),(400,527),(404,530),(408,538),(412,544),(416,548),(420,552),(430,557),(445,560),(470,560),(520,556),(560,551),(600,545),(616,542),(632,537),(644,533),(656,530),(680,520),(700,510),(720,500)])
C = curve([(322,556),(335,578),(345,588),(365,597),(400,601),(440,598),(480,590),(540,578),(600,570),(640,565),(660,562),(700,560)])
wE = np.clip(yy - E + 0.5, 0, 1)[...,None]   # 0 above screen edge, 1 below (anti-aliased)
wC = np.clip(yy - C + 0.5, 0, 1)[...,None]

# --- 3. body behind the arm (below the chin): reflect the right half about the body axis
def reflector(P, d):
    P = np.array(P, float); d = np.array(d, float); d /= np.linalg.norm(d)
    def f(x, y):
        dot = (x-P[0])*d[0] + (y-P[1])*d[1]
        return 2*(P[0]+dot*d[0]) - x, 2*(P[1]+dot*d[1]) - y
    return f
sx, sy = reflector((546,592), (0.0,1.0))(xx, yy)
sx = np.clip(sx.round().astype(int),0,W-1); sy = np.clip(sy.round().astype(int),0,H-1)
torso = src[sy, sx].astype(np.float32)
Mt = (hole>0) & (xx>=286) & (xx<=548) & (yy>=C-1) & (yy<=712) & known[sy, sx]
# soft shadow cast by the head onto the body
shade = 1 - 0.28*np.clip(1 - (yy - C)/10, 0, 1)*(yy>=C)
torso *= shade[...,None]

# --- screen (dark) and head shell (white) each inpainted only from their own colour
win = (xx>=326)&(xx<=680)&(yy>=470)&(yy<=615)
B = (hole>0) & win
def nc_fill(img, known_m, sigmas=(2,4,8,16,32,64)):
    """normalised-convolution fill: every pixel takes the finest-scale average of known pixels around it"""
    img = img.astype(np.float32); k = known_m.astype(np.float32)
    out = img.copy(); done = known_m.copy()
    for sg in sigmas:
        den = cv2.GaussianBlur(k, (0,0), sg)
        num = cv2.GaussianBlur(img*k[...,None], (0,0), sg)
        ok = (den > 0.02) & ~done
        out[ok] = num[ok] / den[ok][:,None]
        done |= ok
    return out
dark  = nc_fill(bg0, known & (yy < E-1.5))
white = nc_fill(bg0, known & (yy > E+1.5) & (yy < C-1.5) & (gray > 150) & (xx > 318))
face = dark*(1-wE) + white*wE
Mf = B & (yy < C+1)
work[Mf] = face[Mf]; setm |= Mf
Mt &= ~Mf | (yy >= C)
blend = (face*(1-wC) + torso*wC)
work[Mt] = np.where(Mf[Mt][:,None], blend[Mt], torso[Mt]); setm |= Mt
SHOULDER = [(352,600),(338,606),(322,616),(308,630),(297,648),(291,670),(290,700),(300,730),(560,730),(560,560),(352,560)]
inS = poly_mask(SHOULDER) > 127
sat = hsv[...,1]
fwin = (xx>=240)&(xx<=400)&(yy>=540)&(yy<=770)
fol = cv2.inpaint(bg0, to8(fwin & ~(known & (sat > 70))), 9, cv2.INPAINT_TELEA).astype(np.float32)
Mo = (hole>0) & ~inS & ~Mf & (xx < 360) & (yy > 560)
wS = cv2.GaussianBlur(inS.astype(np.float32), (0,0), 1.2)[...,None]
work[Mo] = fol[Mo]
edge = (hole>0) & Mt & ~Mf
work[edge] = (work*wS + fol*(1-wS))[edge]
setm |= Mo
work = np.clip(work,0,255).astype(np.uint8)

# --- 4. whatever is left: Telea
rest = ((hole>0) & ~setm).astype(np.uint8)*255
work = cv2.inpaint(work, rest, 7, cv2.INPAINT_TELEA)
bg = feather_comp(bg0, work, hole, 2, 1.6)

# ================= foreground layers =================
def rgba_crop(img, alpha, box):
    x0,y0,x1,y1 = box
    rgb = cv2.cvtColor(img[y0:y1,x0:x1], cv2.COLOR_BGR2RGB)
    return Image.fromarray(np.dstack([rgb, alpha[y0:y1,x0:x1]]).astype(np.uint8), 'RGBA')
layers = {}
# arm: sleeve + cuff + glove
ARM_BOX = (270,540,490,760)
layers['arm'] = (rgba_crop(src, arm, ARM_BOX), ARM_BOX)
# jeon: remove the upper chopstick that lies across it, keep only jeon pixels
J_BOX = (505,486,630,600)
jt = cv2.erode(jeon, np.ones((2,2),np.uint8))
jt = cv2.GaussianBlur(jt, (0,0), 0.6)
jsrc = cv2.inpaint(src, to8((sticks>10) | ((jeon==0) & win)), 4, cv2.INPAINT_TELEA)
layers['jeon'] = (rgba_crop(jsrc, jt, J_BOX), J_BOX)
# eyes + blush dots: soft-edged glow sprites (box padded so the alpha reaches 0 inside it)
for k, g in glow.items():
    soft = cv2.GaussianBlur(g, (0,0), 3)
    img_k = feather_comp(bg0, src, g, 0, 1.0)            # only this sprite's own glow, others erased
    ys, xs = np.nonzero(soft > 2)
    box = (int(xs.min())-2, int(ys.min())-2, int(xs.max())+3, int(ys.max())+3)
    layers[k] = (rgba_crop(img_k, soft, box), box)
OUT.mkdir(exist_ok=True)
meta = {}
for k,(im,box) in layers.items():
    im.save(OUT / f'{k}.png'); meta[k] = box
Image.fromarray(cv2.cvtColor(bg, cv2.COLOR_BGR2RGB)).save(OUT / 'bg.png')
(OUT / 'meta.json').write_text(json.dumps(meta))
print('layers ->', OUT)
