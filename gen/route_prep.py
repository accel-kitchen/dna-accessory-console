"""Stage 1 (KiCad python): swap LED pad 1/2 nets (datasheet pinout), drop old tracks, dump board data for the router."""
import pcbnew as pcb, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=str(ROOT/'dna-accesories.kicad_pcb')
b=pcb.LoadBoard(P);mm=pcb.ToMM
if '--swap' in sys.argv:
    for f in b.GetFootprints():
        if f.GetFPIDAsString().startswith('footprint:SMD4_XL'):
            p1=f.FindPadByNumber('1');p2=f.FindPadByNumber('2')
            n1,n2=p1.GetNet(),p2.GetNet();p1.SetNet(n2);p2.SetNet(n1)
    for t in list(b.GetTracks()):b.Delete(t)
    b.Save(P)
segs=[];
for d in b.GetDrawings():
    if d.GetLayer()==pcb.Edge_Cuts:
        s,e=d.GetStart(),d.GetEnd();segs.append([[mm(s.x),mm(s.y)],[mm(e.x),mm(e.y)]])
pads=[]
for f in b.GetFootprints():
    for p in f.Pads():
        r=p.GetBoundingBox()
        pads.append(dict(ref=f.GetReference(),num=p.GetNumber(),net=p.GetNetname(),x=mm(p.GetX()),y=mm(p.GetY()),
            box=[mm(r.GetLeft()),mm(r.GetTop()),mm(r.GetRight()),mm(r.GetBottom())],
            F=p.IsOnLayer(pcb.F_Cu),B=p.IsOnLayer(pcb.B_Cu),drill=mm(p.GetDrillSizeX()),shape=int(p.GetShape())))
json.dump(dict(edge=segs,pads=pads),open(str(ROOT/'gen'/'_board.json'),'w'))
print(len(segs),len(pads))
