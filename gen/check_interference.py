"""3D interference check of the exported KiCad assembly (needs cadquery-ocp; run with that Python).

Exports the board with all 26 STEP models via kicad-cli, then tests every component pair and every
component against the board body with boolean intersections. A USB-C plug overmold envelope
(USB Type-C spec maximum 12.35 x 6.5 mm, an assumption) is tested at the receptacle mouth.
"""
import sys, json, subprocess, itertools, tempfile, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'gen'))
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from asm import parts
K=r'C:\Program Files\KiCad\9.0\bin\kicad-cli.exe'
out=Path(tempfile.mkdtemp())/'board.step'
subprocess.run([K,'pcb','export','step','--force','-o',str(out),str(ROOT/'dna-accesories.kicad_pcb')],check=True,capture_output=True)
items=parts(str(out))
comps={n:s for n,s in items if n and not n.startswith('=>')}
board=next(s for n,s in items if n and n.startswith('=>'))
def bb(s):
    b=Bnd_Box();BRepBndLib.Add_s(s,b);return b
def vol(s):
    p=GProp_GProps();BRepGProp.VolumeProperties_s(s,p);return abs(p.Mass())
def overlap(a,b):
    if bb(a).IsOut(bb(b)):return 0.0
    c=BRepAlgoAPI_Common(a,b)
    return vol(c.Shape()) if c.IsDone() else float('nan')
result={'components':len(comps),'pairs_tested':0,'component_collisions':[],'board_collisions':[],'bboxes':{}}
names=sorted(comps)
for a,b_ in itertools.combinations(names,2):
    if bb(comps[a]).IsOut(bb(comps[b_])):continue
    result['pairs_tested']+=1
    v=overlap(comps[a],comps[b_])
    if v>1e-4:result['component_collisions'].append([a,b_,round(v,4)])
for n in names:
    v=overlap(comps[n],board)
    if v>1e-4:result['board_collisions'].append([n,round(v,4)])
for n in ('U1','J1'):
    x0,y0,z0,x1,y1,z1=bb(comps[n]).Get();result['bboxes'][n]={'x':[round(x0,3),round(x1,3)],'board_y':[round(-y1,3),round(-y0,3)],'z':[round(z0,3),round(z1,3)]}
# USB-C plug overmold at the receptacle mouth (board y = 144.0 for U1 at y=132, rotation 0, back side).
x0,y0,z0,x1,y1,z1=bb(comps['U1']).Get()
result['usb_plug']={}
mouth_y=y0   # most negative STEP y = largest board y = the USB mouth
zc=-(0.076+2.36)                  # receptacle centre: module underside z=-0.076 minus 2.36 mm height of its centre
xc=(x0+x1)/2
plug=BRepPrimAPI_MakeBox(gp_Pnt(xc-12.35/2,mouth_y-8,zc-6.5/2),gp_Pnt(xc+12.35/2,mouth_y,zc+6.5/2)).Shape()
v=overlap(plug,board)
result['usb_plug']={'mouth_board_y':round(-mouth_y,3),'overmold_mm':[12.35,6.5],'overlap_with_board_mm3':round(v,3),'overlap_height_mm':round(zc+6.5/2,3)}
(ROOT/'design'/'interference-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
