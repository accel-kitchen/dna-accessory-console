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
def nets_of(*pads):
    return {pad(r, n).GetNetname() for r, n in pads}
exp_power = {(u, '2') for u in leds} | {(f'C{i}', '1') for i in list(range(1, 26)) + [27, 29]} | {('D1', '1'), ('D2', '1'), ('R2', '1')}
exp_gnd = {(u, '3') for u in leds} | {(f'C{i}', '2') for i in range(1, 30)} | {('U1', 'GND'), ('U1', 'BAT_N'), ('J1', '2'), ('U26', '2'), ('Q1', '2'), ('R3', '2'), ('R5', '2')}
got = lambda name: {(f.GetReference(), str(p.GetNumber())) for f in fps.values() for p in f.Pads() if p.GetNetname() == name}
chain.append((f'POWER pads = {len(exp_power)}: 24 LED VDD + C1-C25, C27, C29 + D1.K, D2.K, R2.1 (U1 is not on it)', got('POWER') == exp_power))
chain.append((f'GND pads = {len(exp_gnd)}: 24 LED + C1-C29 + U1 GND/BAT-, J1.2, U26, Q1.S, R3, R5', got('GND') == exp_gnd))
chain.append(('VUSB = U1.VUSB, D2.A, Q1.G, R5.1', got('VUSB') == {('U1', 'VUSB'), ('D2', '2'), ('Q1', '1'), ('R5', '1')}))
chain.append(('VBAT = J1.1, U1.BAT+, U26.IN, L1.1, R4.1, C26.1, C28.1', got('VBAT') == {('J1', '1'), ('U1', 'BAT_P'), ('U26', '5'), ('L1', '1'), ('R4', '1'), ('C26', '1'), ('C28', '1')}))
chain.append(('SW = U26.SW, L1.2, D1.A', got('SW') == {('U26', '1'), ('L1', '2'), ('D1', '2')}))
chain.append(('BOOST_EN = U26.EN, Q1.D, R4.2', got('BOOST_EN') == {('U26', '4'), ('Q1', '3'), ('R4', '2')}))
chain.append(('FB = U26.FB, R2.2, R3.1', got('FB') == {('U26', '3'), ('R2', '2'), ('R3', '1')}))
def ohm(v):
    v = v.strip().lower().replace('k', 'e3').replace('m', 'e6')
    return float(v)
vout = 0.6 * (1 + ohm(fps['R2'].GetValue()) / ohm(fps['R3'].GetValue()))
chain.append((f'feedback divider R2 {fps["R2"].GetValue()} / R3 {fps["R3"].GetValue()}: output = 0.6 V x (1 + R2/R3) = {vout:.2f} V', abs(vout - 5.0) < 0.05))
chain.append(('every footprint value matches the schematic part (U26 MT3608B, L1 10uH, D1/D2 1N5819HW, Q1 2N7002)', fps['U26'].GetValue() == 'MT3608B' and fps['L1'].GetValue() == '10uH' and fps['D1'].GetValue() == fps['D2'].GetValue() == '1N5819HW' and fps['Q1'].GetValue() == '2N7002'))
chain.append(('battery return: J1.2 and U1.BAT- are on GND (BAT- is the XIAO GND)', got('GND') >= {('J1', '2'), ('U1', 'BAT_N')}))
chain.append(('U1 is not connected to POWER (LED power only through D1 / D2)', all(p.GetNetname() != 'POWER' for p in fps['U1'].Pads())))
out['boost_vout_nominal'] = vout
vlo = 0.588 * (1 + 0.99 * ohm(fps['R2'].GetValue()) / (1.01 * ohm(fps['R3'].GetValue()))); vhi = 0.612 * (1 + 1.01 * ohm(fps['R2'].GetValue()) / (0.99 * ohm(fps['R3'].GetValue())))
out['boost_vout_range'] = [vlo, vhi]
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
LAST_BRANCH = {}


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
    cur = (lambda x: current[x]) if isinstance(current, dict) else (lambda x: current)
    for s in sinks:
        Iv[pad_nodes[s][0]] -= cur(s)
    Iv[src] += sum(cur(s) for s in sinks)
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
    # largest branch current and the width of that copper (resistance = 0.49 mOhm/sq x length / width)
    Vfull = np.zeros(n)
    for i, k in idx.items():
        Vfull[i] = V[k]
    worst = (0.0, None)
    for a, c, r, ln in edges:
        if a in comp and c in comp and ln > 0.05:
            cur_ = abs(Vfull[a] - Vfull[c]) / r
            if cur_ > worst[0]:
                worst = (cur_, RHO_SQ * ln / r)
    global LAST_BRANCH
    LAST_BRANCH = {'I_max_A': worst[0], 'width_mm': worst[1]}
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
IIN = {'3.7 V cell': 0.58, '3.0 V cell': 0.73}          # input current of the boost at 368 mA / 5 V, 85 % efficiency
for label, I in (('15.35 mA per LED (datasheet typ., all white; 368 mA total)', 0.01535), ('30 mA per LED (2x margin; 737 mA total)', 0.030)):
    case = {'I_led_mA': I * 1e3, 'I_total_mA': I * 24e3}
    for mode, psrc, gsrc in (('battery', ('D1', '1'), ('U26', '2')), ('usb', ('D2', '1'), ('U1', 'GND'))):
        dp, _, _ = solve('POWER', psrc, [(u, '2') for u in leds], I)
        dg, _, _ = solve('GND', gsrc, [(u, '3') for u in leds], I)
        loss = {u: ((dp[(u, '2')] or 0) + (dg[(u, '3')] or 0)) for u in leds}
        w = max(loss, key=loss.get)
        case[mode] = {'power_drop_max_mV': max(v for v in dp.values() if v is not None) * 1e3, 'gnd_rise_max_mV': max(v for v in dg.values() if v is not None) * 1e3,
                      'worst_led': w, 'vdd_loss_worst_mV': loss[w] * 1e3, 'per_led_drop_mV': {u: round(v * 1e3, 2) for u, v in loss.items()},
                      'all_connected': all(v is not None for v in dp.values()) and all(v is not None for v in dg.values())}
    power[label] = case
# battery side of the boost: J1 -> L1 / U26 (input current), and the GND return U26 -> J1.2
bat = {}
for label, I in IIN.items():
    dv, _, _ = solve('VBAT', ('J1', '1'), [('L1', '1')], I)
    dgr, _, _ = solve('GND', ('J1', '2'), [('U26', '2')], I)
    bat[label] = {'I_in_A': I, 'vbat_path_mV': dv[('L1', '1')] * 1e3, 'gnd_return_mV': dgr[('U26', '2')] * 1e3}
branch = {}
solve('POWER', ('D1', '1'), [(u, '2') for u in leds], 0.01535); branch['POWER trunk, all white (battery mode)'] = dict(LAST_BRANCH)
solve('GND', ('U26', '2'), [(u, '3') for u in leds], 0.01535); branch['GND, LED return, all white'] = dict(LAST_BRANCH)
solve('VBAT', ('J1', '1'), [('L1', '1')], 0.73); branch['VBAT, battery to inductor, 3.0 V cell'] = dict(LAST_BRANCH)
solve('GND', ('J1', '2'), [('U26', '2')], 0.73); branch['GND, boost input return to the battery, 3.0 V cell'] = dict(LAST_BRANCH)
out['branch_currents'] = branch
out['battery_path'] = bat
out['power'] = power
# thinnest POWER / GND copper
w_min = {}
for net in ('POWER', 'GND', 'VBAT', 'SW', 'VUSB', 'BOOST_EN', 'FB'):
    ws = [mm(t.GetWidth()) for t in b.GetTracks() if t.GetNetname() == net and t.Type() != pcb.PCB_VIA_T]
    w_min[net] = {'min_w': min(ws), 'max_w': max(ws), 'segments': len(ws), 'length_mm': sum(mm(t.GetLength()) for t in b.GetTracks() if t.GetNetname() == net and t.Type() != pcb.PCB_VIA_T)}
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
print(json.dumps({k: out[k] for k in ('battery_path', 'boost_vout_range', 'decoupling', 'trunk_widths', 'ampacity_A_10K', 'centroid')}, indent=1, default=str)[:3500])
print([x for x in out['netlist_walk'] if not x['ok']])
