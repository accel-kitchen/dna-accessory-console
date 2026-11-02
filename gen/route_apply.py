"""Stage 3 (KiCad python): write gen/_routes.json into the PCB as tracks and vias."""
import pcbnew as pcb, json, sys
from pathlib import Path
R=str(Path(__file__).resolve().parents[1])
b=pcb.LoadBoard(R+r'\dna-accesories.kicad_pcb');r=json.load(open(R+r'\gen\_routes.json'))
for t in list(b.GetTracks()):b.Delete(t)
nets=b.GetNetsByName()
for f in b.GetFootprints():
    q=f.GetFPID()
    if str(q.GetLibNickname())=='' and f.GetReference()[0] in 'CR':
        f.SetFPID(pcb.LIB_ID('Capacitor_SMD' if f.GetReference()[0]=='C' else 'Resistor_SMD',str(q.GetLibItemName())))
V=lambda xy:pcb.VECTOR2I(round(xy[0]*1e6),round(xy[1]*1e6))
import math
vias=r['vias']
def snap(net,pt):
    best=None
    for v in vias:
        if v['net']==net:
            dd=math.dist(v['xy'],pt)
            if dd<0.25 and (best is None or dd<best[0]):best=(dd,v['xy'])
    return tuple(best[1]) if best else pt
for t in r['tracks']:
    if len(t['pts'])>1:
        t['pts'][0]=snap(t['net'],tuple(t['pts'][0]));t['pts'][-1]=snap(t['net'],tuple(t['pts'][-1]))
def layers_at(v):
    ls=set()
    for t in r['tracks']:
        if t['net']!=v['net']:continue
        for e in (t['pts'][0],t['pts'][-1]):
            if math.dist(e,v['xy'])<0.02:ls.add(t['layer'])
    return ls
keep=[v for v in vias if len(layers_at(v))==2]
print('vias kept',len(keep),'of',len(vias))
r['vias']=keep
n=0
for t in r['tracks']:
    for a,z in zip(t['pts'],t['pts'][1:]):
        if V(a)==V(z):continue
        s=pcb.PCB_TRACK(b);s.SetStart(V(a));s.SetEnd(V(z));s.SetWidth(pcb.FromMM(t['w']));s.SetLayer(pcb.F_Cu if t['layer']==0 else pcb.B_Cu);s.SetNet(nets[t['net']]);b.Add(s);n+=1
for v in r['vias']:
    x=pcb.PCB_VIA(b);x.SetPosition(V(v['xy']));x.SetViaType(pcb.VIATYPE_THROUGH);x.SetWidth(pcb.FromMM(0.56));x.SetDrill(pcb.FromMM(0.3));x.SetLayerPair(pcb.F_Cu,pcb.B_Cu);x.SetNet(nets[v['net']]);b.Add(x)
b.Save(R+r'\dna-accesories.kicad_pcb');print(n,len(r['vias']))
