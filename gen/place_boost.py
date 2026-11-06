"""Place the 13 battery-power parts on the front of the collar (simulated annealing, fixed seeds).

Plain python (no dependencies).  Writes gen/_boost_place.json: {ref: [x, y, rotation_deg]}.
Courtyards are axis-aligned rectangles (rotations are multiples of 90 degrees), so overlap tests are exact and fast.
Cost: pad-to-pad distances of the critical loops (boost switch node, input / output capacitors, feedback divider) weighted
high, the other connections weighted low, plus penalties for overlap (0.4 mm between courtyards), leaving the collar band
or touching J1.  Usage: python gen/place_boost.py [restarts] [seed]
"""
import json, math, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

# courtyard (w, h) and pad offsets at rotation 0, from the KiCad footprints
FP = {
    'sot236': ((4.19, 3.49), {'1': (-1.137, -0.95), '2': (-1.137, 0.0), '3': (-1.137, 0.95), '4': (1.137, 0.95), '5': (1.137, 0.0), '6': (1.137, -0.95)}),
    'ind':    ((5.15, 4.59), {'1': (-1.525, 0), '2': (1.525, 0)}),
    'sod123': ((4.79, 2.39), {'1': (-1.65, 0), '2': (1.65, 0)}),
    'sot23':  ((3.95, 3.49), {'1': (-0.938, -0.95), '2': (-0.938, 0.95), '3': (0.938, 0)}),
    'c0805':  ((3.49, 2.05), {'1': (-0.95, 0), '2': (0.95, 0)}),
    'r0402':  ((1.95, 1.03), {'1': (-0.51, 0), '2': (0.51, 0)}),
}
PARTS = {'U26': 'sot236', 'L1': 'ind', 'D1': 'sod123', 'D2': 'sod123', 'Q1': 'sot23',
         'C26': 'c0805', 'C28': 'c0805', 'C27': 'c0805', 'C29': 'c0805',
         'R2': 'r0402', 'R3': 'r0402', 'R4': 'r0402', 'R5': 'r0402'}
# (weight, [(ref, pad) or (x, y) anchor]) : every net is a star around its first pin
NETS = [
    (10, [('U26', '1'), ('L1', '2'), ('D1', '2')]),                                  # SW node
    (6, [('U26', '5'), ('L1', '1'), ('C26', '1'), ('C28', '1')]),                    # VBAT at the IC: input capacitors, inductor
    (6, [('D1', '1'), ('C27', '1'), ('C29', '1')]),                                  # boost output
    (4, [('U26', '2'), ('C26', '2'), ('C28', '2'), ('C27', '2'), ('C29', '2')]),     # ground of the switching loop
    (6, [('U26', '3'), ('R2', '2'), ('R3', '1')]),                                   # FB node
    (2, [('R2', '1'), ('D1', '1')]),
    (1, [('R3', '2'), ('U26', '2')]),
    (2, [('U26', '4'), ('R4', '2'), ('Q1', '3')]),                                   # EN
    (1, [('R4', '1'), ('U26', '5')]),
    (1.5, [('D2', '2'), ('Q1', '1'), ('R5', '1'), (108.5, 142.12)]),                 # VUSB near the XIAO VUSB pad
    (1, [('D2', '1'), ('D1', '1')]),
    (1, [('Q1', '2'), ('R5', '2'), (108.5, 139.58)]),                                # GND near the XIAO GND pad
    (1.5, [('L1', '1'), (99.0, 142.25), (95.5, 134.8)]),                             # battery: J1.1 and XIAO BAT+
    (0.7, [('D1', '1'), (100.0, 127.0)]),                                            # POWER leaves towards the helix
]
BAND = (89.5, 127.9, 110.5, 145.4)           # x0, y0, x1, y1 allowed for courtyards
J1 = (94.9, 136.6, 105.1, 146.4)             # J1 courtyard + margin
GAP = 0.45


def rect(ref, x, y, rot):
    w, h = FP[PARTS[ref]][0]
    if rot in (90, 270):
        w, h = h, w
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def overlap(a, b, grow=0.0):
    dx = min(a[2], b[2]) - max(a[0], b[0]) + grow
    dy = min(a[3], b[3]) - max(a[1], b[1]) + grow
    return dx * dy if dx > 0 and dy > 0 else 0.0


def pad_xy(ref, pad, x, y, rot):
    px, py = FP[PARTS[ref]][1][pad]
    a = math.radians(rot); c, s = round(math.cos(a)), round(math.sin(a))
    return (x + px * c - py * s, y + px * s + py * c)


def part_cost(r, st, rects):
    g = rects[r]
    c = 0.0
    if g[0] < BAND[0]: c += 300 * (BAND[0] - g[0] + .1)
    if g[1] < BAND[1]: c += 300 * (BAND[1] - g[1] + .1)
    if g[2] > BAND[2]: c += 300 * (g[2] - BAND[2] + .1)
    if g[3] > BAND[3]: c += 300 * (g[3] - BAND[3] + .1)
    return c + 400 * overlap(g, J1)


def net_cost(st):
    c = 0.0
    for w, pins in NETS:
        pts = [pad_xy(p[0], p[1], *st[p[0]]) if isinstance(p[0], str) else p for p in pins]
        c += w * sum(math.dist(pts[0], q) for q in pts[1:])
    # the switch node and the input loop must stay small
    sw = [pad_xy('U26', '1', *st['U26']), pad_xy('L1', '2', *st['L1']), pad_xy('D1', '2', *st['D1'])]
    c += 80 * max(0.0, max(math.dist(a, b) for a in sw for b in sw) - 5.0)
    return c


def total(st):
    rects = {r: rect(r, *st[r]) for r in st}
    refs = list(st)
    c = net_cost(st) + sum(part_cost(r, st, rects) for r in refs)
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            c += 700 * overlap(rects[a], rects[b], GAP)
    return c


def anneal(seed):
    rnd = random.Random(seed)
    refs = list(PARTS)
    st = {r: [rnd.uniform(91, 109), rnd.uniform(129, 144), rnd.choice([0, 90, 180, 270])] for r in refs}
    cur = total(st); T = 20.0; best = (cur, {k: list(v) for k, v in st.items()})
    for it in range(120000):
        r = rnd.choice(refs); old = list(st[r])
        if rnd.random() < 0.8:
            sig = 0.9 * T / 20 + 0.08
            st[r][0] += rnd.gauss(0, sig); st[r][1] += rnd.gauss(0, sig)
        else:
            st[r][2] = (st[r][2] + 90 * rnd.choice([1, 2, 3])) % 360
        new = total(st)
        if new < cur or rnd.random() < math.exp((cur - new) / max(T, 1e-3)):
            cur = new
            if cur < best[0]:
                best = (cur, {k: list(v) for k, v in st.items()})
        else:
            st[r] = old
        T = max(0.02, T * 0.99995)
    return best


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    seed0 = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    results = []
    for k in range(n):
        cst, st = anneal(seed0 + k)
        results.append((cst, st)); print('run', k, round(cst, 1), flush=True)
    cst, st = min(results, key=lambda t: t[0])
    snap = {r: [round(x / 0.05) * 0.05, round(y / 0.05) * 0.05, rot] for r, (x, y, rot) in st.items()}
    rects = {r: rect(r, *snap[r]) for r in snap}
    ov = [(a, b) for i, a in enumerate(snap) for b in list(snap)[i + 1:] if overlap(rects[a], rects[b], 0.2) > 0]
    print('RESULT seed', seed0, 'best', round(cst, 1), 'snapped cost', round(total(snap), 1), 'overlaps(0.2 mm):', ov)
    sw = [pad_xy('U26', '1', *snap['U26']), pad_xy('L1', '2', *snap['L1']), pad_xy('D1', '2', *snap['D1'])]
    print('switch node pad spread mm:', round(max(math.dist(a, b) for a in sw for b in sw), 2))
    (ROOT / 'gen' / ('_boost_place_%d.json' % seed0)).write_text(json.dumps({r: [round(v[0], 2), round(v[1], 2), v[2]] for r, v in snap.items()}, indent=1), encoding='utf-8')
    for r, v in snap.items():
        print(r, [round(x, 2) for x in v])


if __name__ == '__main__':
    main()
