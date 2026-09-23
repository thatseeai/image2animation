"""Assemble the animated SVG from the layers produced by layers.py."""
import base64, io, json, math, random
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
L = str(ROOT / 'layers') + '/'
meta = json.load(open(L + 'meta.json'))
OUT = ROOT.parent / 'chuseok-robot.svg'
T = 8.0                                   # loop length (s)
PIV = (300, 705)                          # elbow pivot of the arm
JC = (572, 542)                           # jeon centre
GRIP = (430, 585)                         # where the lower chopstick pivots in the hand

def b64(path, quality=90, lossless=False):
    im = Image.open(path); buf = io.BytesIO()
    im.save(buf, 'WEBP', quality=quality, method=6, lossless=lossless)
    return 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode()

def img(name, **kw):
    x0, y0, x1, y1 = meta[name]
    extra = ''.join(f' {k.replace("_","-")}="{v}"' for k, v in kw.items())
    return f'<image href="{b64(L+name+".png", 92)}" x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}"{extra}/>'

# ---------- keyframe helpers ----------
EASE = {'io': '0.42 0 0.58 1', 'o': '0.16 1 0.3 1', 'i': '0.55 0 1 0.45', 'l': '0 0 1 1', 'h': '0 0 1 1',
        's': '0.3 0 0.2 1'}
def fmt(v):
    if isinstance(v, (tuple, list)): return ' '.join(fmt(x) for x in v)
    return f'{v:.4g}' if isinstance(v, float) else str(v)
def kf(frames):
    """frames: [(t, value, ease_into_this_frame)] -> (values, keyTimes, keySplines)"""
    if frames[0][0] > 0: frames = [(0.0, frames[0][1], 'h')] + frames
    if frames[-1][0] < T: frames = frames + [(T, frames[-1][1], 'h')]
    vals = ';'.join(fmt(v) for _, v, _ in frames)
    kt = ';'.join(f'{t/T:.5f}' for t, _, _ in frames)
    ks = ';'.join(EASE[e] for _, _, e in frames[1:])
    return vals, kt, ks
def at(kind, frames, attr='transform', extra=''):
    v, kt, ks = kf(frames)
    head = f'<animateTransform attributeName="transform" type="{kind}"' if attr == 'transform' else f'<animate attributeName="{attr}"'
    return (f'{head} dur="{T}s" repeatCount="indefinite" values="{v}" keyTimes="{kt}" '
            f'calcMode="spline" keySplines="{ks}"{extra}/>')
def disc(attr, frames):
    """discrete steps: [(t, value)] value holds from t until the next t"""
    if frames[0][0] > 0: frames = [(0.0, frames[-1][1])] + frames
    v = ';'.join(fmt(x) for _, x in frames); kt = ';'.join(f'{t/T:.5f}' for t, _ in frames)
    return f'<animate attributeName="{attr}" dur="{T}s" repeatCount="indefinite" calcMode="discrete" values="{v}" keyTimes="{kt}"/>'

# ---------- timeline ----------
CHOMPS = [0.38, 1.46, 2.56]
ARM = [(0.00, 0, 'h'), (0.22, 0, 'h'), (0.38, -3.2, 'i'), (0.62, 0, 'o'),
       (1.30, 0, 'h'), (1.46, -3.2, 'i'), (1.70, 0, 'o'),
       (2.40, 0, 'h'), (2.56, -3.6, 'i'), (2.82, 0, 'o'),
       (3.70, 0, 'h'), (4.62, 40, 'io'), (4.78, 41.5, 'io'), (4.95, 39.5, 'o'),
       (6.10, -1.2, 'io'), (6.40, 0, 'io'), (8.00, 0, 'h')]
arm_anim = at('rotate', [(t, (a, *PIV), e) for t, a, e in ARM])
counter  = at('rotate', [(t, float(-a), e) for t, a, e in ARM])
squash   = at('scale', [(0, (1, 1), 'h'), (3.70, (1, 1), 'h'), (4.62, (1, 0.52), 'io'), (4.95, (1, 0.56), 'o'),
                        (6.10, (1, 1), 'io')])
jeon_vis = (
    '<animate attributeName="opacity" dur="8s" repeatCount="indefinite" '
    f'values="1;1;0;0;1;1" keyTimes="0;{2.56/T:.5f};{2.565/T:.5f};{4.74/T:.5f};{4.90/T:.5f};1"/>')
pinch = at('rotate', [(0, (0, *GRIP), 'h'), (2.56, (0, *GRIP), 'h'), (2.66, (-1.8, *GRIP), 'o'),
                      (4.10, (-1.8, *GRIP), 'h'), (4.55, (3.0, *GRIP), 'io'), (4.80, (0, *GRIP), 'i')])

# bite marks (jeon-local coordinates), appear at each chomp and reset while the jeon is hidden
BITES = [[(572, 489, 16), (591, 494, 14), (555, 497, 11)],
         [(560, 512, 21), (590, 514, 23), (613, 528, 14), (539, 522, 12)]]
bite_svg = ''
for i, circles in enumerate(BITES):
    for cx, cy, r in circles:
        bite_svg += f'<circle cx="{cx}" cy="{cy}" r="0" fill="#000">{disc("r", [(0, 0), (CHOMPS[i], r), (4.0, 0)])}</circle>'

# chopsticks as tapered wood sticks
def stick(p0, p1, w0, w1, dark, light):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0; n = math.hypot(dx, dy); nx, ny = -dy / n, dx / n
    pts = [(x0 + nx*w0/2, y0 + ny*w0/2), (x1 + nx*w1/2, y1 + ny*w1/2), (x1 - nx*w1/2, y1 - ny*w1/2), (x0 - nx*w0/2, y0 - ny*w0/2)]
    poly = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    hl = f'M{x0+nx*w0*0.18:.1f},{y0+ny*w0*0.18:.1f} L{x1+nx*w1*0.15:.1f},{y1+ny*w1*0.15:.1f}'
    return (f'<polygon points="{poly}" fill="{dark}" stroke="#3b1d0b" stroke-width="0.8" stroke-linejoin="round"/>'
            f'<path d="{hl}" stroke="{light}" stroke-width="{w1*0.35:.2f}" stroke-linecap="round" opacity="0.85"/>')
STICK_U = stick((346, 582), (578, 527), 7.0, 4.2, '#7a4019', '#c98a4e')
STICK_L = stick((350, 603), (572, 537), 7.0, 4.2, '#6a3514', '#b8783f')

# crumbs flying off at every chomp
random.seed(7)
crumbs = ''
for tc in CHOMPS:
    for k in range(6):
        x = 570 + random.uniform(-14, 18); y = 486 + random.uniform(-6, 8)
        dx = random.uniform(-38, 40); dy = random.uniform(55, 120); r = random.uniform(1.8, 3.4)
        t0, t1 = tc + 0.01, tc + random.uniform(0.55, 0.8)
        col = random.choice(['#f2b640', '#e39a2c', '#f7cd62', '#c9742a'])
        mv = at('translate', [(0, (0, 0), 'h'), (t0, (0, 0), 'h'), (t1, (dx, dy), 'i'), (t1 + 0.01, (0, 0), 'h')])
        op = ('<animate attributeName="opacity" dur="8s" repeatCount="indefinite" '
              f'values="0;0;1;1;0;0" keyTimes="0;{t0/T:.5f};{(t0+0.02)/T:.5f};{(t1-0.2)/T:.5f};{t1/T:.5f};1"/>')
        crumbs += f'<g opacity="0">{op}<g>{mv}<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{col}"/></g></g>'

# eyes: chewing bounce, glance down at the plate, eager bounce while bringing the jeon up
eye_frames = [(0, (0, 0), 'h')]
for w0, w1 in [(0.62, 1.30), (1.70, 2.40), (2.82, 3.70)]:
    t = w0
    while t + 0.3 <= w1 + 0.01:
        eye_frames += [(t + 0.15, (0, -3.5), 'io'), (t + 0.30, (0, 0), 'io')]; t += 0.30
eye_frames += [(4.25, (-5, 7), 'io'), (4.95, (-5, 7), 'h'), (5.70, (0, 0), 'io'),
               (6.55, (0, -4), 'o'), (6.80, (0, 0), 'io'), (7.05, (0, -4), 'o'), (7.30, (0, 0), 'io')]
eye_anim = at('translate', eye_frames)

# mouth (glowing, drawn on the face screen, behind the jeon)
def vis(windows, fade=0.04):
    fr = [(0, 0.0, 'h')]
    for a, b in windows:
        fr += [(max(a, 0.0001), 0.0, 'h'), (a + fade, 1.0, 'l'), (b - fade, 1.0, 'h'), (b, 0.0, 'l')]
    return at('', fr, attr='opacity')
open_w = [(0.0, 0.40), (1.28, 1.48), (2.38, 2.58), (7.62, 8.0)]
chew_w = [(0.40, 1.30), (1.48, 2.40), (2.58, 3.72)]
smile_w = [(3.70, 7.64)]
def open_vis():
    # starts the loop already open (continues from 7.62s) -> first window has no fade-in
    fr = [(0, 1.0, 'h'), (0.36, 1.0, 'h'), (0.40, 0.0, 'l'),
          (1.28, 0.0, 'h'), (1.32, 1.0, 'l'), (1.44, 1.0, 'h'), (1.48, 0.0, 'l'),
          (2.38, 0.0, 'h'), (2.42, 1.0, 'l'), (2.54, 1.0, 'h'), (2.58, 0.0, 'l'),
          (7.62, 0.0, 'h'), (7.70, 1.0, 'l'), (8.0, 1.0, 'h')]
    return at('', fr, attr='opacity')
open_scale = at('scale', [(0, (1, 0.8), 'h'), (0.30, (1, 1), 'o'), (0.38, (1, 0.15), 'i'),
                          (1.28, (1, 0.3), 'h'), (1.40, (1, 1), 'o'), (1.46, (1, 0.15), 'i'),
                          (2.38, (1, 0.3), 'h'), (2.50, (1, 1.1), 'o'), (2.56, (1, 0.15), 'i'),
                          (7.62, (1, 0.3), 'h'), (8.0, (1, 0.8), 'o')])
chew_frames = [(0, (1, 1), 'h')]
for a, b in chew_w:
    t = a
    while t + 0.3 <= b + 0.01:
        chew_frames += [(t + 0.15, (1.12, 0.45), 'io'), (t + 0.30, (1, 1), 'io')]; t += 0.30
chew_scale = at('scale', chew_frames)

glow = '#d9f1ff'
MOUTH = f'''
<g transform="translate(573 501) rotate(-13)" filter="url(#glow)">
  <g opacity="1">{open_vis()}<g>{open_scale}
    <path d="M-16,-5 Q0,-8 16,-5 Q14,13 0,14 Q-14,13 -16,-5 Z" fill="#070b22" stroke="{glow}" stroke-width="2.6" stroke-linejoin="round"/>
    <ellipse cx="0" cy="8" rx="7" ry="3.4" fill="#ff86b0" opacity="0.85"/></g></g>
  <g opacity="0">{vis(chew_w)}<g>{chew_scale}
    <path d="M-12,-1 Q-6,6 0,0 Q6,6 12,-1" fill="none" stroke="{glow}" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/></g></g>
  <g opacity="0">{vis(smile_w)}
    <path d="M-12,-3 Q0,9 12,-3" fill="none" stroke="{glow}" stroke-width="2.8" stroke-linecap="round"/></g>
</g>'''

# ---------- ambient touches ----------
LEAF = ('M0,-30 L6,-16 L14,-23 L12,-8 L27,-13 L21,-2 L31,4 L16,8 L21,19 L6,14 L2,26 L-2,26 L-6,14 '
        'L-21,19 L-16,8 L-31,4 L-21,-2 L-27,-13 L-12,-8 L-14,-23 L-6,-16 Z')
VEINS = 'M0,24 L0,-24 M0,6 L22,-9 M0,6 L-22,-9 M0,14 L15,16 M0,14 L-15,16'
leaves = ''
random.seed(3)
for i, (x, dur, beg, sc, g) in enumerate([(90, 13, 0, 0.85, 0), (250, 16, -6, 0.65, 1), (1180, 14, -3, 0.75, 0),
                                           (1420, 17, -10, 0.95, 1), (1330, 12, -8, 0.6, 0), (40, 15, -12, 0.7, 1)]):
    sway = random.uniform(40, 80)
    path = (f'M{x},-60 C{x+sway},200 {x-sway},420 {x+sway*0.6},620 S{x-sway*0.4},900 {x+sway*0.3},1090')
    spin = random.choice([1, -1]) * 360
    flip = f'{random.uniform(1.6, 2.6):.1f}s'
    leaves += (f'<g opacity="0.95"><animateMotion dur="{dur}s" begin="{beg}s" repeatCount="indefinite" path="{path}"/>'
               f'<g><animateTransform attributeName="transform" type="rotate" values="0;{spin}" dur="{dur*0.6:.1f}s" begin="{beg}s" repeatCount="indefinite"/>'
               f'<g><animateTransform attributeName="transform" type="scale" values="{sc} {sc};{sc*0.25:.2f} {sc};{sc} {sc}" dur="{flip}" repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1" keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>'
               f'<path d="M0,24 L0,40" stroke="#8a3a12" stroke-width="2.4" stroke-linecap="round"/>'
               f'<path d="{LEAF}" fill="url(#leaf{g})" stroke="#9c3510" stroke-width="1" stroke-linejoin="round"/>'
               f'<path d="{VEINS}" fill="none" stroke="#b5461a" stroke-width="1.2" opacity="0.6"/>'
               f'</g></g></g>')
steam = ''
for i, (x, beg) in enumerate([(955, 0), (995, -1.4), (1030, -2.7)]):
    d = f'M{x},800 c-14,-18 14,-34 0,-52 c-12,-16 12,-30 2,-46'
    steam += (f'<path d="{d}" fill="none" stroke="#fff" stroke-width="9" stroke-linecap="round" filter="url(#steamBlur)" opacity="0">'
              f'<animate attributeName="opacity" values="0;0.45;0" dur="4.2s" begin="{beg}s" repeatCount="indefinite"/>'
              f'<animateTransform attributeName="transform" type="translate" values="0 10;0 -55" dur="4.2s" begin="{beg}s" repeatCount="indefinite"/></path>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1536 1024" width="1536" height="1024">
<title>즐거운 명절 보내세요 — 부침개 먹는 로봇</title>
<defs>
  <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="2.2" result="b1"/>
    <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="b2"/>
    <feColorMatrix in="b2" type="matrix" values="0 0 0 0 0.25  0 0 0 0 0.6  0 0 0 0 1  0 0 0 1.4 0" result="blue"/>
    <feMerge><feMergeNode in="blue"/><feMergeNode in="b1"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="steamBlur" x="-100%" y="-50%" width="300%" height="200%"><feGaussianBlur stdDeviation="5"/></filter>
  <linearGradient id="leaf0" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffc23d"/><stop offset="1" stop-color="#ee6a1c"/></linearGradient>
  <linearGradient id="leaf1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff8a2a"/><stop offset="1" stop-color="#c8341a"/></linearGradient>
  <radialGradient id="warm"><stop offset="0" stop-color="#ffd27a" stop-opacity="0.9"/><stop offset="1" stop-color="#ffb347" stop-opacity="0"/></radialGradient>
  <radialGradient id="moon"><stop offset="0.55" stop-color="#fff3c4" stop-opacity="0.6"/><stop offset="1" stop-color="#ffe7a0" stop-opacity="0"/></radialGradient>
  <mask id="bite" maskUnits="userSpaceOnUse" x="495" y="470" width="150" height="140">
    <rect x="495" y="470" width="150" height="140" fill="#fff"/>{bite_svg}
  </mask>
</defs>
<image href="{b64(L+'bg.png', 90)}" x="0" y="0" width="1536" height="1024"/>
<ellipse cx="1305" cy="147" rx="150" ry="150" fill="url(#moon)" style="mix-blend-mode:screen" opacity="0.25">
  <animate attributeName="opacity" values="0.18;0.38;0.18" dur="6s" repeatCount="indefinite"/></ellipse>
<ellipse cx="212" cy="258" rx="85" ry="100" fill="url(#warm)" style="mix-blend-mode:screen" opacity="0.2">
  <animate attributeName="opacity" values="0.14;0.3;0.2;0.34;0.16;0.26;0.14" dur="3.3s" repeatCount="indefinite"/></ellipse>
{steam}
<g>{eye_anim}{img('eyeL')}{img('eyeR')}</g>
{img('dotL')}{img('dotR')}
{MOUTH}
<g id="arm">{arm_anim}
  <g>{pinch}{STICK_L}</g>
  <g transform="translate({JC[0]} {JC[1]})"><g>{counter}<g>{squash}
    <g transform="translate({-JC[0]} {-JC[1]})" mask="url(#bite)">{jeon_vis}{img('jeon')}</g>
  </g></g></g>
  {STICK_U}
  {img('arm')}
</g>
{crumbs}
{leaves}
</svg>'''
OUT.write_text(svg)
print(OUT, f'{len(svg)/1024:.0f} KB')
