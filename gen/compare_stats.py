"""Measure the previous board (design/pre-compact-20261102) and the current one for gen/make_comparison.py.
Run with KiCad's Python:  python gen/compare_stats.py <out.json>   (Shapely from gen/_deps/py311)"""
import sys,json,math
from pathlib import Path
R=Path(__file__).resolve().parents[1].as_posix()+'/'
sys.path.insert(0,R+'gen/_deps/py311')
import pcbnew as pcb
from shapely.geometry import Polygon
out={}
for name,pcbp,geo in (('old',R+'design/pre-compact-20261102/dna-accesories.kicad_pcb',R+'design/pre-compact-20261102/dna-geometry.json'),('new',R+'dna-accesories.kicad_pcb',R+'design/dna-geometry.json')):
    b=pcb.LoadBoard(pcbp);mm=pcb.ToMM
    tr=[t for t in b.GetTracks() if t.Type()==pcb.PCB_TRACE_T];vias=[t for t in b.GetTracks() if t.Type()==pcb.PCB_VIA_T]
    g=json.load(open(geo));poly=Polygon(g['outer'],g['holes'])
    x0,y0,x1,y1=g['bounds']
    out[name]=dict(w=x1-x0,h=y1-y0,area=poly.area,bbox_area=(x1-x0)*(y1-y0),perimeter=poly.length,
        tracks=len(tr),track_len=sum(mm(t.GetLength()) for t in tr),vias=len(vias),footprints=len(list(b.GetFootprints())),
        cutouts=len(g['holes']),bounds=g['bounds'],pair_distance=g['pair_distance_mm'],pair_pitch=g.get('pair_pitch_mm',6.5),
        rail_width=g['rail_width'],rung_width=g['rung_width'],
        silk_f=sum(1 for d in b.GetDrawings() if d.GetLayer()==pcb.F_SilkS),silk_b=sum(1 for d in b.GetDrawings() if d.GetLayer()==pcb.B_SilkS),
        letters=sum(1 for d in b.GetDrawings() if d.GetClass()=='PCB_TEXT' and d.GetText() in ('A','T','G','C') and d.GetLayer() in (pcb.F_SilkS,pcb.B_SilkS)))
json.dump(out,open(sys.argv[1],'w'),indent=1)
for k,v in out.items():print(k,{a:(round(c,2) if isinstance(c,float) else c) for a,c in v.items() if a!='bounds'})
