"""Independent checks of the routed board for review.html (KiCad Python).

  "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" gen/review_checks.py gen/_runs/review_checks.json

* netlist walk on the board itself (data chain, LED pad functions, bypass capacitors, pad counts)
* DC resistance / voltage drop of POWER and GND from the real tracks and vias (own resistor network)
* decoupling loop length LED pad -> its capacitor pad along the copper
* chain-hole webs, ear / USB-C plug clearance, copper near the XIAO antenna end, centroid file vs board
"""
import sys, json, math, collections, csv
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'gen' / '_deps' / 'py311'))
import numpy as np
import pcbnew as pcb
from shapely.geometry import Polygon, Point, LineString, box

mm = pcb.ToMM
b = pcb.LoadBoard(str(ROOT / 'dna-accesories.kicad_pcb'))
fps = {f.GetReference(): f for f in b.GetFootprints()}
def pad(ref, num):
    return fps[ref].FindPadByNumber(str(num))
out = {}

# ------------------------------------------------------------------ netlist walk
leds = [f'U{i}' for i in range(2, 26)]
chain = []
ok = True
first = pad('U2', 4).GetNetname()
chain.append(('R1.2 -> U2.DIN', pad('R1', 2).GetNetname() == first == 'DIN_FIRST'))
chain.append(('U1.D6 -> R1.1', pad('U1', '6').GetNetname() == pad('R1', 1).GetNetname() == 'CODON_START'))
hops = []
for a, c in zip(leds, leds[1:]):
    n = pad(a, 1).GetNetname()
    hops.append(n == pad(c, 4).GetNetname() and n.startswith(('Net-', 'CODON')))
chain.append(('U(n).DOUT -> U(n+1).DIN, 23 hops', all(hops)))
chain.append(('U25.DOUT unconnected (CODON_END)', pad('U25', 1).GetNetname() == 'CODON_END'))
chain.append(('every LED pad 2 = POWER, pad 3 = GND', all(pad(u, 2).GetNetname() == 'POWER' and pad(u, 3).GetNetname() == 'GND' for u in leds)))
caps = [f'C{i}' for i in range(1, 25)]
chain.append(('C(n-1) POWER/GND under U(n), same centre, back side',
              all(pad(f'C{i - 1}', 1).GetNetname() == 'POWER' and pad(f'C{i - 1}', 2).GetNetname() == 'GND'
                  and fps[f'C{i - 1}'].GetPosition() == fps[f'U{i}'].GetPosition()
                  and fps[f'C{i - 1}'].GetLayer() == pcb.B_Cu and fps[f'U{i}'].GetLayer() == pcb.F_Cu for i in range(2, 26))))
cnt = collections.Counter(p.GetNetname() for f in fps.values() for p in f.Pads())
chain.append(('POWER pad count = 50 (24 LED + 25 C + U1.VUSB)', cnt['POWER'] == 50))
chain.append(('GND pad count = 50', cnt['GND'] == 50))
chain.append(('U1.VUSB on POWER, U1.GND on GND', pad('U1', 'VUSB').GetNetname() == 'POWER' and pad('U1', 'GND').GetNetname() == 'GND'))
chain.append(('J1.1 / J1.2 -> U1.BAT_P / BAT_N', pad('J1', 1).GetNetname() == pad('U1', 'BAT_P').GetNetname() and pad('J1', 2).GetNetname() == pad('U1', 'BAT_N').GetNetname()))
chain.append(('POWER net has no battery connection (only U1.VUSB)', all(p.GetNetname() != 'POWER' or (f.GetReference()[0] in 'CU') for f in fps.values() for p in f.Pads())))
out['netlist_walk'] = [{'check': k, 'ok': bool(v)} for k, v in chain]

# ------------------------------------------------------------------ copper resistor network
RHO_SQ = 0.49e-3            # ohm per square, 35 um copper
R_VIA = 1.1e-3              # ohm, 0.3 mm drill, 25 um plating, 1.6 mm barrel
def key(p):
    return (int(p.x), int(p.y))
def build(net):
    nodes = {}; edges = []     # edges: (a, b, R, length_mm)
    def nid(layer, p):
        k = (layer, int(p[0]), int(p[1]))
        return nodes.setdefault(k, len(nodes))
    segs = []
    for t in b.GetTracks():
        if t.GetNetname() != net: continue
        if t.Type() == pcb.PCB_VIA_T: continue
        L = 0 if t.GetLayer() == pcb.F_Cu else 1
        segs.append((L, (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y), mm(t.GetWidth())))
    vias = [(t.GetPosition().x, t.GetPosition().y) for t in b.GetTracks() if t.Type() == pcb.PCB_VIA_T and t.GetNetname() == net]
    pads = [(f.GetReference(), p.GetNumber(), (p.GetPosition().x, p.GetPosition().y), p.IsOnLayer(pcb.F_Cu), p.IsOnLayer(pcb.B_Cu))
            for f in fps.values() for p in f.Pads() if p.GetNetname() == net]
    pts = {0: [], 1: []}
    TOL_END, TOL_VIA = 60000, 300000            # nm: a track end sits on another track within 0.06 mm; a via annulus (r 0.28) overlaps a track within 0.3 mm
    for L, a, z, w in segs: pts[L] += [(a, TOL_END), (z, TOL_END)]
    for v in vias: pts[0].append((v, TOL_VIA)); pts[1].append((v, TOL_VIA))
    for r, n, pos, F, B in pads:
        if F: pts[0].append((pos, TOL_END))
        if B: pts[1].append((pos, TOL_END))
    for L, a, z, w in segs:
        A = np.array(a, float); Z = np.array(z, float); D = Z - A; ln = np.linalg.norm(D)
        cuts = [0.0, 1.0]
        for q, tol in pts[L]:
            Q = np.array(q, float)
            if ln < 1: continue
            t_ = float(np.dot(Q - A, D) / ln ** 2)
            if 0 < t_ < 1 and np.linalg.norm(A + t_ * D - Q) < tol:
                cuts.append(t_)
        cuts = sorted(set(cuts))
        for t0, t1 in zip(cuts, cuts[1:]):
            p0 = A + D * t0; p1 = A + D * t1
            seg_len = mm(int(ln)) * (t1 - t0)
            if t1 - t0 < 1e-9: continue
            # a T-joint point that is not exactly on the line still connects: snap it to the node of the touching end point
            n0 = nid(L, p0) if t0 == 0.0 else nid(L, p0)
            n1 = nid(L, p1)
            edges.append((n0, n1, RHO_SQ * seg_len / w, seg_len))
    for v in vias:
        edges.append((nid(0, v), nid(1, v), R_VIA, 1.6))
    pad_nodes = {}
    boxes = {(f.GetReference(), str(p.GetNumber())): p.GetBoundingBox() for f in fps.values() for p in f.Pads() if p.GetNetname() == net}
    ends = [(L, e) for L, a, z, w in segs for e in (a, z)]
    ends += [(L, v) for v in vias for L in (0, 1)]            # a via inside pad copper joins that pad
    M = 250000                                  # 0.25 mm: a track end or via next to the pad edge overlaps the pad with its own half width / annulus
    for r, n, pos, F, B in pads:
        bx = boxes[(r, str(n))]
        for L, on in ((0, F), (1, B)):
            if on:
                pn = nid(L, pos)
                if (r, str(n)) in pad_nodes:
                    edges.append((pad_nodes[(r, str(n))][0], pn, 1e-4, 0.0))      # a pad on both layers is one conductor
                pad_nodes.setdefault((r, str(n)), []).append(pn)
                # the router ends tracks anywhere on the pad copper, not only at its centre
                for L2, e in ends:
                    if L2 == L and bx.GetLeft() - M <= e[0] <= bx.GetRight() + M and bx.GetTop() - M <= e[1] <= bx.GetBottom() + M:
                        edges.append((pn, nid(L, e), 1e-4, 0.0))
    # T-joint end points: join any node to the nearest segment node within 0.06 mm on the same layer
    via_ids = {nid(L, v) for v in vias for L in (0, 1)}
    byL = collections.defaultdict(list)
    for (L, x, y), i in nodes.items(): byL[L].append((x, y, i))
    for L, lst in byL.items():
        arr = np.array([(x, y) for x, y, _ in lst], float)
        for idx, (x, y, i) in enumerate(lst):
            d = np.hypot(arr[:, 0] - x, arr[:, 1] - y)
            for j in np.where((d > 0) & (d < TOL_VIA))[0]:
                jj = lst[j][2]
                if jj != i and (d[j] < TOL_END or i in via_ids or jj in via_ids): edges.append((i, jj, 1e-6, 0.0))
    return nodes, edges, pad_nodes
def solve(net, source, sinks, current):
    """DC solution: `source` node is held at 0 V and every sink draws `current` through it. Returns per-sink drop (V)."""
    nodes, edges, pad_nodes = build(net)
    n = len(nodes)
    G = np.zeros((n, n))
    for a, c, r, _ in edges:
        g = 1.0 / max(r, 1e-6)
        G[a, a] += g; G[c, c] += g; G[a, c] -= g; G[c, a] -= g
    src = pad_nodes[source][0]
    Iv = np.zeros(n)
    for s in sinks:
        Iv[pad_nodes[s][0]] -= current
    Iv[src] += current * len(sinks)
    keep = [i for i in range(n) if i != src]
    # connected component of the source only
    comp = {src}; adj = collections.defaultdict(list)
    for a, c, r, _ in edges: adj[a].append(c); adj[c].append(a)
    stack = [src]
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if v not in comp: comp.add(v); stack.append(v)
    import os
    if os.environ.get('RC_DEBUG'):
        sk = [pad_nodes[x][0] for x in sinks]
        print(net, 'nodes', n, 'edges', len(edges), 'component', len(comp), 'sinks in comp', sum(1 for x in sk if x in comp), 'src', src)
    keep = [i for i in comp if i != src]
    idx = {i: k for k, i in enumerate(keep)}
    Gr = G[np.ix_(keep, keep)]
    V = np.linalg.solve(Gr, Iv[keep])
    drops = {}
    for s in sinks:
        node = pad_nodes[s][0]
        drops[s] = float(-V[idx[node]]) if node in idx else None       # sinks sit below the source: report the drop as positive
    return drops, len(comp), n
def path_len(net, a, c):
    nodes, edges, pad_nodes = build(net)
    import heapq
    adj = collections.defaultdict(list)
    for x, y, r, ln in edges: adj[x].append((y, ln)); adj[y].append((x, ln))
    src = pad_nodes[a][0]; dst = set(pad_nodes[c])
    dist = {src: 0.0}; pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if u in dst: return d
        if d > dist.get(u, 1e18): continue
        for v, ln in adj[u]:
            nd = d + ln
            if nd < dist.get(v, 1e18): dist[v] = nd; heapq.heappush(pq, (nd, v))
    return None

power = {}
for label, I in (('15.35 mA per LED (datasheet typ., all white; 368 mA total)', 0.01535), ('30 mA per LED (2x margin; 737 mA total)', 0.030)):
    dp, comp_p, n_p = solve('POWER', ('U1', 'VUSB'), [(u, '2') for u in leds], I)
    dg, comp_g, n_g = solve('GND', ('U1', 'GND'), [(u, '3') for u in leds], I)
    worst = max(leds, key=lambda u: (dp[(u, '2')] or 0) + (dg[(u, '3')] or 0))
    power[label] = {'I_led_mA': I * 1e3, 'I_total_mA': I * 24e3,
                    'power_drop_max_mV': max(v for v in dp.values() if v is not None) * 1e3,
                    'gnd_rise_max_mV': max(v for v in dg.values() if v is not None) * 1e3,
                    'worst_led': worst,
                    'vdd_loss_worst_mV': ((dp[(worst, '2')] or 0) + (dg[(worst, '3')] or 0)) * 1e3,
                    'per_led_drop_mV': {u: round(((dp[(u, '2')] or 0) + (dg[(u, '3')] or 0)) * 1e3, 2) for u in leds},
                    'all_connected': all(v is not None for v in dp.values()) and all(v is not None for v in dg.values())}
out['power'] = power
# thinnest POWER / GND copper
w_min = {}
for net in ('POWER', 'GND'):
    ws = [mm(t.GetWidth()) for t in b.GetTracks() if t.GetNetname() == net and t.Type() != pcb.PCB_VIA_T]
    w_min[net] = {'min_w': min(ws), 'max_w': max(ws), 'segments': len(ws)}
out['trunk_widths'] = w_min
# IPC-2221 external-layer ampacity for the thinnest POWER track (35 um, 10 K rise)
w = w_min['POWER']['min_w'] / 0.0254; a_mil2 = w * 1.378
out['ampacity_A_10K'] = 0.048 * (10 ** 0.44) * (a_mil2 ** 0.725)

# decoupling loop: copper path LED VDD pad -> bypass capacitor pad 1 (and GND)
loops = {}
for i in range(2, 26):
    pv = path_len('POWER', (f'U{i}', '2'), (f'C{i - 1}', '1'))
    pg = path_len('GND', (f'U{i}', '3'), (f'C{i - 1}', '2'))
    loops[f'U{i}'] = (pv, pg)
out['decoupling'] = {'max_power_path_mm': max(v[0] for v in loops.values()), 'max_gnd_path_mm': max(v[1] for v in loops.values()),
                     'mean_power_path_mm': float(np.mean([v[0] for v in loops.values()])), 'mean_gnd_path_mm': float(np.mean([v[1] for v in loops.values()])),
                     'worst': max(loops, key=lambda u: loops[u][0] + loops[u][1])}

# ------------------------------------------------------------------ mechanics from the outline
geo = json.loads((ROOT / 'design' / 'dna-geometry.json').read_text(encoding='utf-8'))
board = Polygon(geo['outer'], geo['holes'])
ext = Polygon(geo['outer'])
webs = {}
for hdef in geo['hanging_holes']:
    c = Point(*hdef['center']); r = hdef['diameter'] / 2
    webs[f"hole at x={hdef['center'][0]:.0f}"] = {'min_web_mm': ext.exterior.distance(c) - r, 'diameter': hdef['diameter']}
out['chain_hole_webs'] = webs
out['ear'] = {'inner_gap_mm': 16.0, 'bounds_y': [146.0, geo['bounds'][3]], 'width_mm': 4.0}
u1 = fps['U1']; bb = u1.GetBoundingBox(False)
out['u1_bbox'] = [mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())]
out['plug_clearance_each_side_mm'] = (16.0 - 12.35) / 2

# copper in the zone around the XIAO end that faces the helix (BLE antenna side)
zone = box(90, 121.0, 110, 129.0)
zone_cu = {'F': 0.0, 'B': 0.0}; zone_items = collections.Counter()
for t in b.GetTracks():
    if t.Type() == pcb.PCB_VIA_T: continue
    ls = LineString([(mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y))])
    inter = ls.intersection(zone).length
    if inter > 0:
        zone_cu['F' if t.GetLayer() == pcb.F_Cu else 'B'] += inter
        zone_items[t.GetNetname()] += 1
out['antenna_zone'] = {'zone_mm': [90, 121.0, 110, 129.0], 'track_length_mm': zone_cu, 'nets': dict(zone_items)}

# ------------------------------------------------------------------ fusion files vs board
cent = list(csv.DictReader((ROOT / 'fusion' / 'centroid.csv').open(encoding='utf-8-sig', newline='')))
keys = {k.lower(): k for k in cent[0]}
rk = keys.get('designator') or keys.get('ref') or list(cent[0])[0]
xk, yk, sk = 'Mid X', 'Mid Y', 'Layer'
bad = []
for r in cent:
    f = fps[r[rk]]
    dx = abs(float(r[xk]) - mm(f.GetX())); dy = abs(-float(r[yk]) - mm(f.GetY()))      # KiCad .pos files use Y up
    side_ok = (r[sk].lower() == 'bottom') == (f.GetLayer() == pcb.B_Cu)
    if dx > 0.01 or dy > 0.01 or not side_ok: bad.append((r[rk], round(dx, 3), round(dy, 3), side_ok))
out['centroid'] = {'rows': len(cent), 'mismatch': bad[:5], 'columns': list(cent[0])}
out['footprints'] = len(fps)
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding='utf-8')
print(json.dumps({k: out[k] for k in ('power', 'decoupling', 'chain_hole_webs', 'antenna_zone', 'centroid', 'trunk_widths', 'ampacity_A_10K', 'plug_clearance_each_side_mm')}, indent=1, default=str)[:6000])
print([x for x in out['netlist_walk'] if not x['ok']])
