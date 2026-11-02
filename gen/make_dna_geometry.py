"""Generate a single connected DNA silhouette and twelve base-pair positions.

Requires shapely>=2.2.0. This is a decorative projection, not a molecular scale model.
Revision 5: compact helix (all sizes are parameters), no hanging cap at the tip; the chain holes
are two 2.0 mm holes in the lower corners of the controller collar.

Parameters can be given as environment variables for experiments (DNA_D, DNA_P, DNA_A, DNA_RAIL,
DNA_RUNG, DNA_OUT); the defaults are the committed design.
"""
import sys, json, math, os
from pathlib import Path
if '--dependency-path' in sys.argv:
    sys.path.insert(0, sys.argv[sys.argv.index('--dependency-path')+1])
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
def env(name,default):return float(os.environ.get(name,default))
CX=100.0
PAIR_DISTANCE=env('DNA_D',6.0)        # LED centre to LED centre inside one base pair
PAIR_PITCH=env('DNA_P',5.2)           # axial distance between base pairs
AMPLITUDE=env('DNA_A',7.5)            # backbone swing around the axis
RAIL_WIDTH=env('DNA_RAIL',4.0)
RUNG_WIDTH=env('DNA_RUNG',4.0)
PAIRS=12
LENGTH=PAIRS*PAIR_PITCH               # one extra pitch below the last pair, as in revision 4
END=118.0                             # the helix hands over to the collar here
START=END-LENGTH
PITCH=6*PAIR_PITCH                    # 6 pairs per turn = 2 turns / 12 pairs
PHASE=math.pi/12
OUT=Path(os.environ.get('DNA_OUT',ROOT/'design'/'dna-geometry.json'))
def strand(y,side):
    return CX+side*AMPLITUDE*math.cos(2*math.pi*(y-START)/PITCH+PHASE),y
samples=[START+LENGTH*i/520 for i in range(521)]
rails=[[strand(y,side) for y in samples] for side in (1,-1)]
pieces=[LineString(rail).buffer(RAIL_WIDTH/2,quad_segs=12) for rail in rails]
pairs=[]
for i in range(PAIRS):
    y=START+i*PAIR_PITCH
    rail_a=strand(y,1); rail_b=strand(y,-1)
    direction=1 if rail_a[0]>CX else -1
    # Bases occupy a constant-width central pair; their stalks reach the curved backbones.
    a=(CX+direction*PAIR_DISTANCE/2,y)
    b=(CX-direction*PAIR_DISTANCE/2,y)
    pairs.append({'pair':i+1,'codon_group':i//3+1,'a':{'ref':f'U{2+2*i}','xy':a},'b':{'ref':f'U{3+2*i}','xy':b}})
    rung_min=min(a[0],b[0],rail_a[0],rail_b[0])
    rung_max=max(a[0],b[0],rail_a[0],rail_b[0])
    pieces.append(LineString([(rung_min,y),(rung_max,y)]).buffer(RUNG_WIDTH/2,cap_style='round',quad_segs=12))

# Broad lower collar supports the module and battery connector; merge both backbones.
collar=box(CX-14.5,117.5,CX+14.5,146.0)
collar=collar.buffer(-2.0,quad_segs=16).buffer(2.0,quad_segs=16)
pieces.append(collar)
for side in (1,-1):pieces.append(LineString([strand(START+LENGTH,side),(CX+side*9,121.0)]).buffer(RAIL_WIDTH/2,quad_segs=12))
board=unary_union(pieces).buffer(0).simplify(0.025,preserve_topology=True)
assert board.geom_type=='Polygon',board.geom_type
assert board.is_valid
# Chain holes sit in the lower collar corners, concentric with the 2 mm corner radius (1.0 mm ring).
HOLE_D=2.0
hanging_holes=[(CX-12.5,144.0),(CX+12.5,144.0)]
# Eliminate tiny triangular slivers and round internal slots for a 1.2 mm router.
clean_holes=[]
for ring in board.interiors:
    rounded=Polygon(ring).buffer(-.6,quad_segs=12).buffer(.6,quad_segs=12)
    if not rounded.is_empty and rounded.area>2:clean_holes.append(rounded)
for c in hanging_holes:clean_holes.append(Point(*c).buffer(HOLE_D/2,quad_segs=32))
board=Polygon(board.exterior).difference(unary_union(clean_holes)).simplify(.015,preserve_topology=True)
assert board.geom_type=='Polygon' and board.is_valid
result={'design':f'DNA helix / constant {PAIR_DISTANCE:g} mm base pairs / layout revision 5','units':'mm',
        'outer':list(board.exterior.coords)[:-1],'holes':[list(r.coords)[:-1] for r in board.interiors],
        'rails':rails,'pairs':pairs,'bounds':board.bounds,'rail_width':RAIL_WIDTH,
        'rung_width':RUNG_WIDTH,'pair_distance_mm':PAIR_DISTANCE,'pair_pitch_mm':PAIR_PITCH,
        'amplitude_mm':AMPLITUDE,'helix_start_y':START,
        'hanging_holes':[{'center':c,'diameter':HOLE_D} for c in hanging_holes],
        'control':{'U1':{'xy':(100,134.5),'orientation':0,'layer':'B.Cu'},'J1':{'xy':(100,140),'orientation':0,'layer':'F.Cu'}},
        'notes':['The outline is one connected FR4 shape with internal cut-outs.',
                 '12 pairs = 24 LEDs, U2/U3 through U24/U25.',
                 f'Every base pair has exactly {PAIR_DISTANCE:g} mm LED center-to-center spacing.',
                 'Two decorative turns; axial spacing is stylized.',
                 'Chain holes: two 2.0 mm holes in the lower collar corners (USB-C side).',
                 'Original schematic nets and LED symbol mapping are retained.']}
OUT.write_text(json.dumps(result,indent=2),encoding='utf-8')
print('Outline bounds:',tuple(round(x,3) for x in board.bounds),'cut-outs:',len(board.interiors))
print('Size:',round(board.bounds[2]-board.bounds[0],2),'x',round(board.bounds[3]-board.bounds[1],2),'mm')
print('Helix part:',round(END-START,1),'mm; width',round(2*AMPLITUDE+RAIL_WIDTH,1),'mm')
print('LED spacing per pair:',sorted({round(math.dist(p['a']['xy'],p['b']['xy']),2) for p in pairs}))
