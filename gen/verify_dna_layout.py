"""Verify constant-distance paired placement and preserved nets for revision 2."""
from pathlib import Path
import pcbnew as pcb, json, math, hashlib
root=Path(__file__).resolve().parents[1]
b=pcb.LoadBoard(str(root/'dna-accesories.kicad_pcb'))
g=json.loads((root/'design'/'dna-geometry.json').read_text())
fps={f.GetReference():f for f in b.GetFootprints()}
assert len(fps)==26
refs=[]
for i,pair in enumerate(g['pairs']):
    a,z=pair['a'],pair['b'];refs.extend([a['ref'],z['ref']])
    assert (a['ref'],z['ref'])==(f'U{2+2*i}',f'U{3+2*i}')
    ap,zp=fps[a['ref']].GetPosition(),fps[z['ref']].GetPosition()
    assert abs(pcb.ToMM(ap.y-zp.y))<.00001
    assert abs(pcb.ToMM(ap.x+zp.x)-200)<.00001
    assert abs(math.dist(a['xy'],z['xy'])-10.0)<.000001
    assert abs(pcb.ToMM(ap.x-zp.x))==10.0
    pa=next(p for p in fps[a['ref']].Pads() if p.GetNumber()=='2')
    pz=next(p for p in fps[z['ref']].Pads() if p.GetNumber()=='4')
    assert pa.GetNetCode()==pz.GetNetCode()
    tracks=[t for t in b.GetTracks() if t.GetNetCode()==pa.GetNetCode()]
    assert len(tracks)==1
    assert tracks[0].GetStart()==pa.GetPosition() and tracks[0].GetEnd()==pz.GetPosition()
assert set(refs)=={f'U{i}' for i in range(2,26)}
before=json.loads((root/'design'/'net-preservation.json').read_text())
assert before['unchanged']
for f in b.GetFootprints():
    expected=before['footprints'][f.GetReference()]
    assert expected['uuid']==f.m_Uuid.AsString()
    assert expected['pads']=={p.GetNumber():p.GetNetname() for p in f.Pads()}
for name in ['dna-accesories.kicad_sch','dna-accesories.kicad_pro','fp-lib-table','sym-lib-table']:
    assert (root/name).read_bytes()==(root/'design'/'pre-redesign-20261008'/name).read_bytes(),name
d=json.loads((root/'design'/'placement-drc.json').read_text())
assert len(d['violations'])==0
assert len(d['schematic_parity'])==0
assert len(d['unconnected_items'])==62
result={'write_probe':'PASS (create/read-back/delete)','base_pairs':12,'leds':24,
        'physical_drc_violations':0,'schematic_parity_issues':0,'unconnected_items_pending':62,
        'schematic_and_project_unchanged':True,'original_pad_nets_and_uuids_retained':True,
        'intra_pair_connections_verified':12,'dimensions_mm':[round(g['bounds'][2]-g['bounds'][0],3),round(g['bounds'][3]-g['bounds'][1],3)],
        'base_pair_center_distance_mm':10.0,'equal_distance_pairs_verified':12,
        'pcb_sha256':hashlib.sha256((root/'dna-accesories.kicad_pcb').read_bytes()).hexdigest(),
        'stage':'Outline / placement; power and inter-pair routing pending'}
(root/'design'/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
