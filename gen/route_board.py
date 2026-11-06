"""Stage 2 (plain python + numpy/scipy/PIL): grid router for the DNA board.
Reads gen/_board.json, writes gen/_routes.json (tracks, vias).  Clearance-aware A* on two copper layers."""
import json, heapq, math, sys, collections, re
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw
RES = 0.05
import os
CL = float(os.environ.get('CL','0.2')); EDGE = float(os.environ.get('EDGE','0.6')); VIA_D = float(os.environ.get('VIAD','0.5')); VIA_COST = 40
WIDTH = {'sig': float(os.environ.get('WS','0.2')), 'pwr': float(os.environ.get('WP','0.3')), 'hi': float(os.environ.get('WH','0.4'))}   # hi: boost input and switch node (up to ~0.8 A)
d = json.load(open('gen/_board.json'))
_xs=[v for a, b in d['edge'] for v in (a[0], b[0])]; _ys=[v for a, b in d['edge'] for v in (a[1], b[1])]
OX = math.floor(min(_xs)) - 1.0; OY = math.floor(min(_ys)) - 1.0
W = int((math.ceil(max(_xs)) + 1.0 - OX) / RES); H = int((math.ceil(max(_ys)) + 1.0 - OY) / RES)


def cell(x, y):
    return int(round((x - OX) / RES)), int(round((y - OY) / RES))


def mmxy(cx, cy):
    return OX + cx * RES, OY + cy * RES


# ---- board outline raster
adj = collections.defaultdict(list)
key = lambda p: (round(p[0], 3), round(p[1], 3))
for a, b in d['edge']:
    adj[key(a)].append(key(b)); adj[key(b)].append(key(a))
loops = []; seen = set()
for s in list(adj):
    if s in seen:
        continue
    loop = [s]; seen.add(s); cur = s; prev = None
    while True:
        nx = [n for n in adj[cur] if n != prev and n not in seen]
        if not nx:
            break
        prev = cur; cur = nx[0]; seen.add(cur); loop.append(cur)
    loops.append(loop)


def area(l):
    return abs(sum(l[i][0] * l[(i + 1) % len(l)][1] - l[(i + 1) % len(l)][0] * l[i][1] for i in range(len(l)))) / 2


loops.sort(key=lambda l: -area(l))
img = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(img)
px = lambda l: [((x - OX) / RES, (y - OY) / RES) for x, y in l]
dr.polygon(px(loops[0]), fill=1)
for l in loops[1:]:
    dr.polygon(px(l), fill=0)
board = np.array(img, bool)
print('loops', len(loops), 'board cells', board.sum(), file=sys.stderr)
edt_board = ndimage.distance_transform_edt(board) * RES

# ---- copper ownership
NETID = {}; own = [np.full((H, W), -1, np.int16) for _ in range(2)]  # 0=F 1=B
padcells = np.zeros((H, W), bool)


def nid(n):
    if n not in NETID:
        NETID[n] = len(NETID)
    return NETID[n]


def box_slice(box):
    x0, y0, x1, y1 = box; cx0, cy0 = cell(x0, y0); cx1, cy1 = cell(x1, y1)
    return slice(cy0, cy1 + 1), slice(cx0, cx1 + 1)


pads = d['pads']
for p in pads:
    ok = bool(p['net']) and not p['net'].startswith('unconnected')
    n = p['net'] if ok else '@' + p['ref'] + p['num']
    p['nid'] = nid(n); p['routed'] = ok
    bx = p['box']; inf = 0.15 if p['ref'] in ('U1', 'J1') else 0.04
    sl = box_slice([bx[0] - inf, bx[1] - inf, bx[2] + inf, bx[3] + inf])
    for L, k in ((0, 'F'), (1, 'B')):
        if p[k]:
            own[L][sl] = p['nid']; padcells[sl] = True
via_block = np.zeros((H, W), bool)
# rule areas of the footprints (XIAO: no copper / vias around its test pads): tracks and vias keep out
for k in d.get('keepouts', []):
    for L in k['layers']:
        if k['tracks']:
            own[L][box_slice(k['box'])] = 9999
    if k['vias']:
        via_block[box_slice([k['box'][0] - VIA_D / 2, k['box'][1] - VIA_D / 2, k['box'][2] + VIA_D / 2, k['box'][3] + VIA_D / 2])] = True


def disk_offsets(r):
    n = int(math.ceil(r / RES)); ys, xs = np.mgrid[-n:n + 1, -n:n + 1]
    m = (xs ** 2 + ys ** 2) * RES ** 2 <= r * r + 1e-9
    return ys[m], xs[m]


def paint(arr, pts, r, v):
    oy, ox = disk_offsets(r)
    for cx, cy in pts:
        yy = oy + cy; xx = ox + cx
        ok = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
        arr[yy[ok], xx[ok]] = v


nets = collections.defaultdict(list)
for p in pads:
    if p['routed']:
        nets[p['net']].append(p)
nets = {k: v for k, v in nets.items() if len(v) > 1}


STUBS = []
def make_stubs():
    rvv = VIA_D / 2
    for name in list(nets):
        newlist = []
        for p in nets[name]:
            if not re.match(r'U([2-9]|1\d|2[0-5])$', p['ref']):          # stubs and vias only for the 24 LEDs
                newlist.append(p); continue
            cxm = round((p['box'][0] + p['box'][2]) / 2, 3); cym = (p['box'][1] + p['box'][3]) / 2
            ref = [q for q in pads if q['ref'] == p['ref']]
            lx = sum(q['x'] for q in ref) / 4; ly = sum(q['y'] for q in ref) / 4
            sx = 1 if p['x'] > lx else -1; sy = 1 if p['y'] > ly else -1
            placed = None
            for dist in (0.8, 0.9, 1.0, 1.2):
                for (ax, ay) in ((sx, sy), (-sx, sy), (sx, -sy), (-sx, -sy)):
                    vx, vy = p['x'] + ax * dist, p['y'] + ay * dist
                    c = cell(vx, vy)
                    if edt_board[c[1], c[0]] >= EDGE + rvv + 0.05 and not via_block[c[1], c[0]] and not padcells[c[1]-6:c[1]+7, c[0]-6:c[0]+7].any():
                        placed = (vx, vy); break
                if placed: break
            assert placed, (p['ref'], p['num'])
            c = cell(*placed); N = p['nid']
            # stub on F.Cu pad -> via
            a = cell(p['x'], p['y'])
            n = max(abs(c[0] - a[0]), abs(c[1] - a[1]))
            pts = [(round(a[0] + (c[0] - a[0]) * k / n), round(a[1] + (c[1] - a[1]) * k / n)) for k in range(n + 1)]
            paint(own[0], pts, WIDTH[klass(name)] / 2, N)
            for L in (0, 1):
                paint(own[L], [c], rvv + 0.04, N)
            paint(via_block, [c], VIA_D, True)
            STUBS.append(dict(net=name, w=WIDTH[klass(name)], pts=[(p['x'], p['y']), placed], pin=[p['ref'], p['num']], via=placed))
            v = dict(ref=p['ref'], num=p['num'], net=name, x=placed[0], y=placed[1], nid=N, F=True, B=True, routed=True,
                     box=[placed[0] - .1, placed[1] - .1, placed[0] + .1, placed[1] + .1])
            newlist.append(v)
        nets[name] = newlist


def klass(n):
    if n in ('VBAT', 'SW', 'BAT_RAW'):
        return 'hi'
    return 'pwr' if n in ('POWER', 'GND', 'VUSB') else 'sig'


def layers_of(p):
    return [L for L, k in ((0, 'F'), (1, 'B')) if p[k]]


NB = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]


def astar(pin, start, allowed, via_ok, target, h):
    pq = []; G = {}; par = {}; goal = None
    for L in layers_of(pin):
        st = (L, start[1], start[0]); G[st] = 0.0
        heapq.heappush(pq, (h[start[1], start[0]], 0.0, st))
    while pq:
        f, g, st = heapq.heappop(pq)
        if G.get(st, 1e18) < g - 1e-9:
            continue
        L, y, x = st
        if target[L][y, x]:
            goal = st; break
        al = allowed[L]
        for dx, dy in NB:
            nx, ny = x + dx, y + dy
            if nx < 0 or ny < 0 or nx >= W or ny >= H or not al[ny, nx]:
                continue
            if dx and dy:
                if not (al[y, nx] and al[ny, x]):
                    continue
                c = 1.4142
            else:
                c = 1.0
            ns = (L, ny, nx); ng = g + c
            if ng < G.get(ns, 1e18):
                G[ns] = ng; par[ns] = st; heapq.heappush(pq, (ng + h[ny, nx], ng, ns))
        L2 = 1 - L
        if allowed[L2][y, x] and via_ok[y, x]:
            ns = (L2, y, x); ng = g + VIA_COST
            if ng < G.get(ns, 1e18):
                G[ns] = ng; par[ns] = st; heapq.heappush(pq, (ng + h[y, x], ng, ns))
    if goal is None:
        return None
    seq = [goal]
    while seq[-1] in par:
        seq.append(par[seq[-1]])
    seq.reverse()
    runs = []; vl = []; cur = []; curL = seq[0][0]
    for L, y, x in seq:
        if L != curL:
            vl.append(cur[-1]); runs.append((curL, cur)); cur = [cur[-1]]; curL = L
        cur.append((x, y))
    runs.append((curL, cur))
    return runs, vl


def net_allowed(N, w, slack=0.0):
    out = []
    for L in (0, 1):
        other = (own[L] != -1) & (own[L] != N)
        e = ndimage.distance_transform_edt(~other) * RES
        out.append(((e > w / 2 + CL - slack) & (edt_board >= EDGE + w / 2 - slack)) | (own[L] == N))
    return out


def route_net(name, pins):
    w = WIDTH[klass(name)]; N = pins[0]['nid']
    allowed = net_allowed(N, w)
    rv = VIA_D / 2
    via_ok = np.ones((H, W), bool)
    for L in (0, 1):
        other = (own[L] != -1) & (own[L] != N)
        via_ok &= ndimage.distance_transform_edt(~other) * RES > rv + CL
    via_ok &= (edt_board >= EDGE + rv) & ~padcells & ~via_block
    target = [np.zeros((H, W), bool) for _ in range(2)]
    order = sorted(pins, key=lambda p: 0 if p['ref'] == 'U1' else 1)
    seed = order[0]
    for L in layers_of(seed):
        target[L][box_slice(seed['box'])] = True
    rest = order[1:]; ok_all = True; added = []
    while rest:
        h = ndimage.distance_transform_edt(~(target[0] | target[1]))
        rest.sort(key=lambda p: h[cell(p['x'], p['y'])[1], cell(p['x'], p['y'])[0]])
        p = rest.pop(0)
        res = astar(p, cell(p['x'], p['y']), allowed, via_ok, target, h)
        if res is None:
            print('FAIL', name, p['ref'], p['num'], file=sys.stderr); ok_all = False; continue
        runs, vl = res
        runs = [(L, simplify(L, pts, allowed)) for L, pts in runs]
        for L, pts in runs:
            dense = []
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                n = max(abs(x1 - x0), abs(y1 - y0), 1)
                dense += [(round(x0 + (x1 - x0) * k / n), round(y0 + (y1 - y0) * k / n)) for k in range(n + 1)]
            if len(pts) == 1:
                dense = list(pts)
            paint(own[L], dense, w / 2, N)
            for cx, cy in dense:
                target[L][cy, cx] = True
        for cx, cy in vl:
            for L in (0, 1):
                paint(own[L], [(cx, cy)], rv + 0.04, N); target[L][cy, cx] = True
            paint(via_block, [(cx, cy)], VIA_D, True)
        added.append((runs, vl, p))
        for L in (0, 1):
            allowed[L] |= (own[L] == N)
    return added, ok_all


def simplify(L, pts, allowed):
    out = [pts[0]]; i = 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1:
            (x0, y0), (x1, y1) = pts[i], pts[j]; n = max(abs(x1 - x0), abs(y1 - y0)) * 2
            if all(allowed[L][round(y0 + (y1 - y0) * k / n), round(x0 + (x1 - x0) * k / n)] for k in range(1, n)):
                break
            j -= 1
        out.append(pts[j]); i = j
    return out


if __name__ == '__main__':
    def span(ps):
        return max(p['y'] for p in ps) - min(p['y'] for p in ps)
    names = [n for n in nets if n not in ('POWER', 'GND', 'VBAT', 'SW', 'BAT_RAW')]
    names.sort(key=lambda n: (span(nets[n]) > 8, span(nets[n])))
    make_stubs()
    names = ['BAT_RAW', 'VBAT', 'SW', 'POWER', 'GND'] + [n for n in names]
    if os.environ.get('SEED'):
        import random; random.seed(int(os.environ['SEED'])); random.shuffle(names)
    prio = [n for n in os.environ.get('PRIO', '').split('|') if n in names]
    names = prio + [n for n in names if n not in prio]
    out = {'tracks': [], 'vias': [], 'failed': []}
    for st in STUBS:
        out['tracks'].append(dict(net=st['net'], layer=0, w=st['w'], pts=st['pts'], pin=st['pin']))
        out['vias'].append(dict(net=st['net'], xy=st['via']))
    for name in names:
        w0 = WIDTH[klass(name)]
        added, ok = route_net(name, nets[name])
        for runs, vl, p in added:
            for k, (L, pts) in enumerate(runs):
                mp = [mmxy(*c) for c in pts]
                if k == 0:
                    mp = [(p['x'], p['y'])] + mp[1:] if len(mp) > 1 else [(p['x'], p['y'])]
                out['tracks'].append(dict(net=name, layer=L, w=w0, pts=mp, pin=[p['ref'], p['num']]))
            for c in vl:
                out['vias'].append(dict(net=name, xy=mmxy(*c)))
        if not ok:
            out['failed'].append(name)
        print(name, 'ok' if ok else 'FAILED', file=sys.stderr)
    json.dump(out, open(os.environ.get('OUT', 'gen/_routes.json'), 'w'))
