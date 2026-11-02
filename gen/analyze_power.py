"""KiCad python: DC resistance / voltage drop of the POWER and GND copper at full-white load.

Builds a resistor network from the real tracks and vias (1 oz copper, 0.49 mOhm/sq, via ~ 1.6 mm barrel, ~1 mOhm),
injects 15.35 mA per LED (3 x 5 mA + 0.35 mA, review item 04) at each LED VDD pad and returns it at the XIAO pad.
"""
import pcbnew as pcb, json, math
import numpy as np
R = r'D:\Document\Research\software\pcb\dna-accesories'
b = pcb.LoadBoard(R + r'\dna-accesories.kicad_pcb'); mm = pcb.ToMM
RHO = 0.49e-3   # ohm per square, 35 um copper
I_LED = 0.01535
out = {}
for net, src_ref, src_pad in (('POWER', 'U1', 'VUSB'), ('GND', 'U1', 'GND')):
    segs = []
    for t in b.GetTracks():
        if t.GetNetname() != net: continue
        if t.GetClass() == 'PCB_VIA':
            continue
        segs.append((mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y), mm(t.GetWidth()), t.GetLayer()))
    vias = [(mm(t.GetPosition().x), mm(t.GetPosition().y)) for t in b.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetname() == net]
    nodes = {}; coords = []
    def node(x, y, L):
        for i, (cx, cy, cl) in enumerate(coords):
            if cl == L and abs(cx - x) < 0.1 and abs(cy - y) < 0.1: return i
        coords.append((x, y, L)); nodes[(len(coords) - 1,)] = len(coords) - 1; return len(coords) - 1
    # collect points to split segments at T junctions
    pts = {0: [], 1: []}
    for s in segs:
        L = 0 if s[5] == pcb.F_Cu else 1
        pts[L] += [(s[0], s[1]), (s[2], s[3])]
    for v_ in vias:
        pts[0].append(v_); pts[1].append(v_)
    edges = []
    for s in segs:
        L = 0 if s[5] == pcb.F_Cu else 1
        a = np.array(s[:2]); z = np.array(s[2:4]); d = z - a; ln = np.linalg.norm(d)
        cut = [0.0, 1.0]
        for p in pts[L]:
            q = np.array(p)
            if ln < 1e-9: break
            t = float(np.dot(q - a, d) / ln ** 2)
            if 0.001 < t < 0.999 and np.linalg.norm(a + t * d - q) < 0.2: cut.append(t)
        cut = sorted(set(cut))
        for t0, t1 in zip(cut, cut[1:]):
            p0 = a + d * t0; p1 = a + d * t1
            r = RHO * (ln * (t1 - t0)) / s[4]
            edges.append((node(*p0, L), node(*p1, L), max(r, 1e-6)))
    # pads & vias join layers at same xy
    for (x, y) in vias:
        for L in (0, 1):
            pass
        edges.append((node(x, y, 0), node(x, y, 1), 1e-3))
    # pads: join to nearest node within 0.3 mm on the pad layer
    def near(x, y, L):
        best = None
        for i, (kx, ky, kl) in enumerate(coords):
            if kl != L: continue
            dd = math.hypot(kx - x, ky - y)
            if best is None or dd < best[0]: best = (dd, i)
        return best
    sinks = []; source = None
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() != net: continue
            L = 0 if p.IsOnLayer(pcb.F_Cu) else 1
            bb = p.GetBoundingBox(); x0, y0, x1, y1 = mm(bb.GetLeft()) - .05, mm(bb.GetTop()) - .05, mm(bb.GetRight()) + .05, mm(bb.GetBottom()) + .05
            inside = [i for i, (kx, ky, kl) in enumerate(coords) if kl == L and x0 <= kx <= x1 and y0 <= ky <= y1]
            if not inside:
                cx_, cy_ = (x0 + x1) / 2, (y0 + y1) / 2
                c = sorted((math.hypot(kx - cx_, ky - cy_), i) for i, (kx, ky, kl) in enumerate(coords) if kl == L)
                if not c or c[0][0] > 2.5: print('pad without copper', f.GetReference(), p.GetNumber()); continue
                inside = [c[0][1]]
            for i in inside[1:]: edges.append((inside[0], i, 1e-6))
            ref = f.GetReference()
            if ref == src_ref and p.GetNumber() == src_pad: source = inside[0]
            elif ref.startswith('U') and ref != 'U1': sinks.append((ref, inside[0]))
    N = len(nodes); G = np.zeros((N, N))
    for i, j, r in edges:
        if i == j: continue
        g = 1.0 / r; G[i, i] += g; G[j, j] += g; G[i, j] -= g; G[j, i] -= g
    # connected component of source
    comp = {source}; stack = [source]
    adj = {}
    for i, j, r in edges: adj.setdefault(i, []).append(j); adj.setdefault(j, []).append(i)
    while stack:
        u = stack.pop()
        for v in adj.get(u, []):
            if v not in comp: comp.add(v); stack.append(v)
    print(net,'nodes',N,'comp',len(comp),'sinks',len(sinks),'edges',len(edges),'source',source, coords[source] if source is not None else None)
    idx = sorted(comp); pos = {n: k for k, n in enumerate(idx)}
    Gc = G[np.ix_(idx, idx)]
    cur = np.zeros(len(idx)); found = []
    for ref, n in sinks:
        if n in comp:
            cur[pos[n]] -= I_LED; found.append(ref)
    cur[pos[source]] += I_LED * len(found)
    keep = [k for k in range(len(idx)) if idx[k] != source]
    v = np.zeros(len(idx))
    v[keep] = np.linalg.solve(Gc[np.ix_(keep, keep)], cur[keep])
    drops = {ref: float(v[pos[n]]) for ref, n in sinks if n in comp}
    # drop shown as magnitude (source at 0 V reference; sinks pull current out for POWER and return for GND)
    out[net] = dict(leds_reached=len(found), max_drop_mV=round(1000 * max(abs(x) for x in drops.values()), 1),
                    worst=max(drops, key=lambda k: abs(drops[k])), track_mm=round(sum(math.hypot(s[0]-s[2], s[1]-s[3]) for s in segs), 1),
                    vias=len(vias))
print(json.dumps(out, indent=1))
json.dump(out, open(R + r'\design\power-drop.json', 'w'), indent=1)
