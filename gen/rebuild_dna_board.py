"""Rebuild PCB outline, placement and silkscreen using installed KiCad 9 pcbnew Python.

Preserves footprint UUIDs, pad numbers, nets, and schematic links.
Revision 5 starts from the routed revision-4 board (design/pre-compact-20261102): it re-places the
LEDs and their back-side bypass capacitors on the compact helix, redraws outline and silkscreen
(no base letters on the helix, chain holes in the collar corners) and drops all copper, which
gen/route_prep.py -> route_board.py -> route_apply.py then routes again.
Needs Shapely: set DNA_DEPS to a folder that contains it (KiCad's Python has none).
"""
from pathlib import Path
import os, sys
if os.environ.get('DNA_DEPS'):sys.path.insert(0,os.environ['DNA_DEPS'])
import pcbnew as pcb, json, math, csv
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep
ROOT=Path(__file__).resolve().parents[1]
g=json.loads((ROOT/'design'/'dna-geometry.json').read_text())
SOURCE=ROOT/'design'/'pre-compact-20261102'/'dna-accesories.kicad_pcb'
b=pcb.LoadBoard(str(SOURCE))
def point(xy):return pcb.VECTOR2I(round(xy[0]*1e6),round(xy[1]*1e6))
def mm(p):return [pcb.ToMM(p.x),pcb.ToMM(p.y)]
before={f.GetReference():{'uuid':f.m_Uuid.AsString(),'pads':{p.GetNumber():p.GetNetname() for p in f.Pads()}} for f in b.GetFootprints()}
for item in list(b.GetTracks())+list(b.Zones())+list(b.GetDrawings()):b.Delete(item)

# ---------------------------------------------------------------- drawing primitives
SIDES={'F':pcb.F_SilkS,'B':pcb.B_SilkS}
def line(a,z,layer,width=0.05):
    s=pcb.PCB_SHAPE(b);s.SetShape(pcb.SHAPE_T_SEGMENT);s.SetStart(point(a));s.SetEnd(point(z));s.SetLayer(layer);s.SetWidth(pcb.FromMM(width));b.Add(s);return s
def circle(c,r,layer,width=.12):
    s=pcb.PCB_SHAPE(b);s.SetShape(pcb.SHAPE_T_CIRCLE);s.SetCenter(point(c));s.SetEnd(point((c[0]+r,c[1])));s.SetLayer(layer);s.SetWidth(pcb.FromMM(width));s.SetFilled(False);b.Add(s);return s
def outline(points):
    # Individual closed segments make every cut-out unambiguous to KiCad.
    for i,a in enumerate(points):line(a,points[(i+1)%len(points)],pcb.Edge_Cuts)
outline(g['outer'])
for hole in g['holes']:outline(hole)
fps={f.GetReference():f for f in b.GetFootprints()}
def position(f,xy,deg):f.SetOrientationDegrees(deg);f.SetPosition(point(xy))
def text(value,xy,size=0.8,layer=pcb.F_SilkS,angle=0,thick=.12):
    t=pcb.PCB_TEXT(b);t.SetText(value);t.SetPosition(point(xy));t.SetLayer(layer);t.SetTextSize(point((size,size)));t.SetTextThickness(pcb.FromMM(thick));t.SetTextAngle(pcb.EDA_ANGLE(angle,pcb.DEGREES_T));
    if layer in (pcb.B_SilkS,pcb.B_Fab):t.SetMirrored(True)
    b.Add(t);return t
def text_box(t):
    """Inked area of a text item: KiCad's bounding box includes line-spacing room above and below the glyphs."""
    r=t.GetBoundingBox();cx=pcb.ToMM(r.GetCenter().x);cy=pcb.ToMM(r.GetCenter().y)
    half_w=pcb.ToMM(r.GetWidth())/2*.94;half_h=pcb.ToMM(t.GetTextSize().y)*.5+pcb.ToMM(t.GetTextThickness())/2+.02
    return box(cx-half_w,cy-half_h,cx+half_w,cy+half_h)
for ref,c in g['control'].items():position(fps[ref],c['xy'],c['orientation'])
for pair in g['pairs']:
    for strand in ('a','b'):
        v=pair[strand];f=fps[v['ref']];deg=0 if v['xy'][0]<100 else 180
        assert abs((f.GetOrientationDegrees()-deg+180)%360-180)<1e-6,('LED side changed',v['ref'])
        position(f,tuple(v['xy']),deg)
        # C(n-1) is the 100 nF bypass capacitor on the back of U(n); same centre, orientation kept.
        fps['C'+str(int(v['ref'][1:])-1)].SetPosition(f.GetPosition())

# ---------------------------------------------------------------- silk planning (Shapely clearance checks)
board_poly=Polygon(g['outer'],g['holes'])
FREE=board_poly.buffer(-.45)               # silk keeps >=0.45 mm from every board edge / cut-out
START=g['helix_start_y'];PP=g['pair_pitch_mm'];END=START+12*PP;PD=g['pair_distance_mm'];RAIL=g['rail_width']
reserved={'F':[],'B':[]}                   # silk or mask openings that new silk must not touch
for f in b.GetFootprints():
    for p in f.Pads():
        r=p.GetBoundingBox();pad=box(pcb.ToMM(r.GetLeft()),pcb.ToMM(r.GetTop()),pcb.ToMM(r.GetRight()),pcb.ToMM(r.GetBottom())).buffer(.3)
        if p.IsOnLayer(pcb.F_Cu):reserved['F'].append(pad)
        if p.IsOnLayer(pcb.B_Cu):reserved['B'].append(pad)
def fits(side,geom,margin=.12):
    if not FREE.contains(geom):return False
    return all(geom.distance(r)>=margin for r in reserved[side])
def reserve(side,geom):reserved[side].append(geom)
def put_text(side,value,xy,size=.8,thick=.12,must=True,free=None):
    t=text(value,xy,size,SIDES[side],thick=thick);bb=text_box(t)
    if must:assert (free or FREE).contains(bb) and all(bb.distance(r)>=.05 for r in reserved[side]),f'silk text collides: {value!r} {bb.bounds}'
    reserve(side,bb.buffer(.1));return t
def put_line(side,a,z,width=.12):
    line(a,z,SIDES[side],width);reserve(side,LineString([a,z]).buffer(width/2))

SEQ='ATGGCATCGTAA'                          # 4 codons: ATG (start) GCA TCG TAA (stop)
PAIR={'A':'T','T':'A','G':'C','C':'G'}
CODON_NAMES=['START','CODON 2','CODON 3','STOP']
def pair_marks(side):
    """Hydrogen bonds, LED outlines and pair numbers for one side of the board (no base letters:
    the colour of every LED is chosen at run time)."""
    for i,pair in enumerate(g['pairs']):
        y=pair['a']['xy'][1]
        base=SEQ[i];bonds=2 if base in 'AT' else 3
        # LED body outline (top / bottom bars only, outside the pad mask envelope); LEDs are on the front only.
        for led in (pair['a'],pair['b']):
            x=led['xy'][0]
            for off in (-.95,.95):
                if side=='F':put_line(side,(x-.94,y+off),(x+.94,y+off))
                else:reserve(side,LineString([(x-.94,y+off),(x+.94,y+off)]).buffer(.06))
        # Hydrogen bonds: two dashed bars for A-T, three for G-C, one dash either side of the pair number.
        offs=(-.35,.35) if bonds==2 else (-.5,0,.5)
        for off in offs:
            for x0,x1 in ((-1.75,-1.05),(1.05,1.75)):put_line(side,(100+x0,y+off),(100+x1,y+off))
        put_text(side,f'{i+1:02}',(100,y),.8)

crossings=[START+(math.pi/2+k*math.pi-math.pi/12)*6*PP/(2*math.pi) for k in range(5)]
crossings=[y for y in crossings if START<=y<=END]

def rail_point(side_index,y):
    rail=g['rails'][side_index];i=round((y-rail[0][1])/(rail[-1][1]-rail[0][1])*(len(rail)-1))
    return rail[i]
def pentagon(c,r):
    pts=[(c[0]+r*math.cos(math.radians(-90+72*k)),c[1]+r*math.sin(math.radians(-90+72*k))) for k in range(5)]
    return pts
def beads(side):
    """Deoxyribose pentagon at each base attachment, phosphate ring between: the sugar-phosphate backbone."""
    placed=[]
    for si in (0,1):
        ys=[p['a']['xy'][1] for p in g['pairs']]                # sugars at the base-pair rows
        specs=[(y,'sugar') for y in ys]+[(y+PP/2,'phosphate') for y in ys]
        for y,kind in specs:
            if y>END-3.1 or any(abs(y-c)<1.95 for c in crossings):continue
            c=rail_point(si,y);r=.78 if kind=='sugar' else .55
            shape=Polygon(pentagon(c,r)) if kind=='sugar' else Point(c).buffer(r)
            if not fits(side,shape.buffer(.12),.1):continue
            if any(shape.distance(o)<.4 for o in placed):continue
            placed.append(shape)
            if kind=='sugar':
                pts=pentagon(c,r)
                for a,z in zip(pts,pts[1:]+pts[:1]):line(a,z,SIDES[side],.12)
            else:circle(c,r,SIDES[side],.12)
    for s in placed:reserve(side,s.buffer(.22))
    return placed
def ribbons(side):
    """Double ribbon along both backbones; the strand that passes behind breaks at each crossing.
    Fragments shorter than 1.2 mm (squeezed between letters, numbers and beads) are dropped."""
    block=prep(unary_union(reserved[side]))
    for si,rail in enumerate(g['rails']):
        for offset in (-.36,.36):
            run=[]
            def flush():
                if run and sum(math.dist(a,z) for a,z in run)>=1.2:
                    for a,z in run:line(a,z,SIDES[side],.15)
                run.clear()
            for a,z in zip(rail,rail[1:]):
                y=(a[1]+z[1])/2
                behind=any(abs(y-c)<1.65*RAIL/4.8 and (k%2==si)==(side=='F') for k,c in enumerate(crossings))
                aa=(a[0]+offset,a[1]);zz=(z[0]+offset,z[1]);seg=LineString([aa,zz])
                if not behind and FREE.contains(seg) and not block.intersects(seg.buffer(.075+.06)):run.append((aa,zz))
                else:flush()
            flush()

table=[]
for pair in g['pairs']:
    row=[]
    for strand in ('a','b'):
        v=pair[strand];f=fps[v['ref']];x,y=v['xy'];deg=0 if x<100 else 180
        # References move off the LED pads to the outer backbone edge.
        f.Reference().SetVisible(False)
        f.Value().SetVisible(False)
        for item in list(f.GraphicalItems()):
            if item.GetLayer()==pcb.F_SilkS:f.Delete(item)
        text(v['ref'],(x,y+1.4),.8,pcb.F_Fab)
        row.append(f)
        table.append({'pair':pair['pair'],'group':pair['codon_group'],'strand':strand.upper(),
                      'base':SEQ[pair['pair']-1] if strand=='a' else PAIR[SEQ[pair['pair']-1]],
                      'reference':v['ref'],'x_mm':round(x,5),'y_mm':round(y,5),'rotation_deg':deg,
                      'DIN':next(p.GetNetname() for p in f.Pads() if p.GetNumber()=='4'),
                      'DOUT':next(p.GetNetname() for p in f.Pads() if p.GetNumber()=='1')})   # revision 4: DOUT is pad 1
for f in (fps['U1'],fps['J1']):
    f.Reference().SetVisible(False);f.Value().SetVisible(False)
for item in list(fps['U1'].GraphicalItems()):
    if item.GetLayer() in (pcb.F_SilkS,pcb.B_SilkS):fps['U1'].Delete(item)

# The intra-pair copper tracks are silk-neutral (silk only collides with mask openings, i.e. pads).
for side in ('F','B'):
    # End tags and the hanging-hole ring first, so beads / ribbons route around them.
    rx=g['rails'][0][0][0]-100                               # backbone x offset at the helix ends
    for tag,xy in (("5'",(100+rx,START-.2)),("3'",(100-rx,START-.2)),("3'",(100+rx,END-1.0)),("5'",(100-rx,END-1.0))):put_text(side,tag,xy,.8,must=False)
    for hole in g['hanging_holes']:reserve(side,Point(*hole['center']).buffer(hole['diameter']/2+.6))
    pair_marks(side)
    beads(side)
    ribbons(side)

# Front collar: title, the encoded sequence, legend and polarity of the battery connector.
put_text('F','DNA / 12 BASE PAIRS',(100,119.8),1.0)
put_text('F',f'REV 5  -  {PD:g} mm / PAIR',(100,122.4),.8)
put_text('F',"5'-"+' '.join(SEQ[k:k+3] for k in range(0,12,3))+"-3'",(100,125.8),1.0,.15)
put_text('F',"3'-"+' '.join(''.join(PAIR[c] for c in SEQ[k:k+3]) for k in range(0,12,3))+"-5'",(100,128.0),1.0,.15)
put_text('F','START',(94.8,130.4),.8);put_text('F','STOP',(105.2,130.4),.8)
put_text('F','A=T 2 BONDS  G-C 3 BONDS',(100,132.5),.8)
put_text('F','2 TURNS / 12 BASE PAIRS',(100,134.6),.8)
put_text('F','WATSON CRICK FRANKLIN 1953',(100,136.6),.8)
put_text('F','+',(93.0,141.5),1.1);put_text('F','-',(107.0,141.5),1.1)
# Back collar: orientation marks for the XIAO and the USB-C mouth.
put_text('B','DNA / 12 BASE PAIRS',(100,119.6),.9)
put_text('B','USB-C',(100,144.85),.8,must=False)
b.GetDesignSettings().SetAuxOrigin(point((100,146)))
after={f.GetReference():{'uuid':f.m_Uuid.AsString(),'pads':{p.GetNumber():p.GetNetname() for p in f.Pads()}} for f in b.GetFootprints()}
assert before==after,'Schematic UUID / net mapping changed'
pcb.SaveBoard(str(ROOT/'dna-accesories.kicad_pcb'),b)
silk=[]
for item in b.GetDrawings():
    if item.GetLayer()!=pcb.F_SilkS:continue
    if isinstance(item,pcb.PCB_TEXT):
        silk.append({'type':'text','text':item.GetText(),'xy':mm(item.GetPosition()),'size':pcb.ToMM(item.GetTextSize().y)})
    elif item.GetShape()==pcb.SHAPE_T_CIRCLE:
        silk.append({'type':'circle','c':mm(item.GetCenter()),'r':pcb.ToMM(item.GetRadius()),'width':pcb.ToMM(item.GetWidth())})
    else:
        silk.append({'type':'line','a':mm(item.GetStart()),'b':mm(item.GetEnd()),'width':pcb.ToMM(item.GetWidth())})
(ROOT/'design'/'front-silkscreen.json').write_text(json.dumps(silk,indent=2),encoding='utf-8')
with (ROOT/'design'/'base-pairs.csv').open('w',encoding='utf-8-sig',newline='') as file:
    writer=csv.DictWriter(file,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
(ROOT/'design'/'net-preservation.json').write_text(json.dumps({'unchanged':before==after,'footprints':after},indent=2),encoding='utf-8')
print('Saved redesigned main board:',ROOT/'dna-accesories.kicad_pcb')
print('Pairs:',len(g['pairs']),'original footprints:',len(fps),'intra-pair tracks:',len(list(b.GetTracks())))
print('Silk items front/back:',sum(1 for d in b.GetDrawings() if d.GetLayer()==pcb.F_SilkS),sum(1 for d in b.GetDrawings() if d.GetLayer()==pcb.B_SilkS))
