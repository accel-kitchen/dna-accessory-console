"""Dump placement / pad / outline data from the PCB for the Seeed Fusion assembly package.
Run with KiCad's Python:  python gen/dump_assembly_data.py <shapely_path> <out.json>"""
import json, sys
import pcbnew
sys.path.insert(0, sys.argv[1])
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely import affinity

MM = 1e6
b = pcbnew.LoadBoard('dna-accesories.kicad_pcb')

so = pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(so)
outline = []
for i in range(so.OutlineCount()):
    o = so.Outline(i)
    ext = [(o.CPoint(k).x / MM, o.CPoint(k).y / MM) for k in range(o.PointCount())]
    holes = [[(so.Hole(i, h).CPoint(k).x / MM, so.Hole(i, h).CPoint(k).y / MM) for k in range(so.Hole(i, h).PointCount())]
             for h in range(so.HoleCount(i))]
    outline.append({'ext': ext, 'holes': holes})
board_poly = unary_union([Polygon(o['ext'], o['holes']) for o in outline])
edge = board_poly.boundary  # outer edge + cut-out edges

parts = []
for f in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    side = 'bottom' if f.GetLayer() == pcbnew.B_Cu else 'top'
    layer = f.GetLayer()
    pads = []
    for p in f.Pads():
        sz = p.GetSize(layer)
        pads.append({'num': p.GetNumber(), 'x': p.GetX() / MM, 'y': p.GetY() / MM, 'w': sz.x / MM, 'h': sz.y / MM,
                     'rot': p.GetOrientationDegrees(), 'shape': int(p.GetShape(layer)), 'net': p.GetNetname(),
                     'th': p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)})
    crt = f.GetCourtyard(layer)
    court = None
    if crt.OutlineCount():
        o = crt.Outline(0)
        court = [(o.CPoint(k).x / MM, o.CPoint(k).y / MM) for k in range(o.PointCount())]
    bb = f.GetBoundingBox(False)
    parts.append({'ref': f.GetReference(), 'value': f.GetValue(), 'fp': f.GetFPIDAsString().split(':')[-1], 'side': side,
                  'x': f.GetX() / MM, 'y': f.GetY() / MM, 'rot': f.GetOrientationDegrees(), 'pads': pads, 'court': court,
                  'bbox': [bb.GetLeft() / MM, bb.GetTop() / MM, bb.GetRight() / MM, bb.GetBottom() / MM]})

# --- spacing checks (Seeed Fusion PCBA spec: chip-chip >= 1 mm, chip-connector >= 5 mm) -------------
def shape(p):
    if p['court']:
        return Polygon(p['court'])
    return box(*p['bbox'])

def pad_union(p):
    polys = []
    for d in p['pads']:
        r = box(d['x'] - d['w'] / 2, d['y'] - d['h'] / 2, d['x'] + d['w'] / 2, d['y'] + d['h'] / 2)
        polys.append(affinity.rotate(r, -d['rot'], origin=(d['x'], d['y'])) if d['rot'] % 180 else r)
    return unary_union(polys)

checks = {}
for side in ('top', 'bottom'):
    ps = [p for p in parts if p['side'] == side]
    best = None
    for i, a in enumerate(ps):
        for c in ps[i + 1:]:
            d = shape(a).distance(shape(c))
            if best is None or d < best[0]:
                best = (d, a['ref'], c['ref'])
    checks[side + '_min_courtyard_gap'] = best
    pad_best = None
    for i, a in enumerate(ps):
        for c in ps[i + 1:]:
            d = pad_union(a).distance(pad_union(c))
            if pad_best is None or d < pad_best[0]:
                pad_best = (d, a['ref'], c['ref'])
    checks[side + '_min_pad_gap'] = pad_best
# distance from parts (courtyard / pads) to the board edge or cut-out edge
edge_d = sorted(((shape(p).distance(edge), p['ref']) for p in parts))[:6]
edge_pad = sorted(((pad_union(p).distance(edge), p['ref']) for p in parts))[:6]
checks['edge_courtyard_nearest'] = edge_d
checks['edge_pad_nearest'] = edge_pad
# front/back overlap: parts on opposite sides whose courtyards overlap (info only)
opp = []
for a in [p for p in parts if p['side'] == 'top']:
    for c in [p for p in parts if p['side'] == 'bottom']:
        if shape(a).intersects(shape(c)):
            opp.append((a['ref'], c['ref']))
checks['opposite_side_overlaps'] = len(opp)
checks['opposite_side_overlap_pairs_sample'] = opp[:6]
bx = board_poly.bounds
json.dump({'outline': outline, 'bounds': bx, 'parts': parts, 'checks': checks}, open(sys.argv[2], 'w'), default=float)
print(json.dumps(checks, default=float, indent=1))
