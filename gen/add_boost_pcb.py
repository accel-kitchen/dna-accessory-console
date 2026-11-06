"""PCB part of the battery power path (KiCad Python).

  "C:\\Program Files\\KiCad\\9.0\\python.exe" gen/add_boost_pcb.py <source.kicad_pcb> <out.kicad_pcb>

* nets: U1.BAT+ moves from Net-(U1-BAT+) to VBAT, J1.1 to BAT_RAW (the battery side of the rev 7 power switch Q2/R6/SW1),
  new nets VUSB / SW / FB / BOOST_EN / PWR_G; U1.VUSB moves from POWER to VUSB
* the 16 parts of gen/add_boost_sch.py are added on the front at the positions of gen/_boost_place.json, linked to the schematic symbols
Placement is stored, so the result is reproducible; gen/rebuild_dna_board.py then starts from <out.kicad_pcb>.
"""
import sys, json, importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'gen' / '_deps' / 'py311'))
import pcbnew as pcb

spec = importlib.util.spec_from_file_location('add_boost_sch', ROOT / 'gen' / 'add_boost_sch.py')
sch = importlib.util.module_from_spec(spec); spec.loader.exec_module(sch)
LIBD = r'C:\Program Files\KiCad\9.0\share\kicad\footprints'
V = lambda x, y: pcb.VECTOR2I(round(x * 1e6), round(y * 1e6))

src, dst = sys.argv[1], sys.argv[2]
b = pcb.LoadBoard(src)
place = json.loads((ROOT / 'gen' / '_boost_place.json').read_text(encoding='utf-8'))
uuids = json.loads((ROOT / 'gen' / '_boost_uuids.json').read_text(encoding='utf-8'))
fps = {f.GetReference(): f for f in b.GetFootprints()}
assert 'U26' not in fps, 'already applied'

# ---- nets
nets = b.GetNetsByName()
for name in ('VBAT', 'VUSB', 'SW', 'FB', 'BOOST_EN', 'BAT_RAW', 'PWR_G'):         # (renaming Net-(U1-BAT+) leaves a stale name map, so the pads move to a new net)
    b.Add(pcb.NETINFO_ITEM(b, name))
nets = b.GetNetsByName()
assert fps['U1'].FindPadByNumber('VUSB').GetNetname() == 'POWER'
fps['U1'].FindPadByNumber('VUSB').SetNet(nets['VUSB'])
for ref, num, net in (('J1', '1', 'BAT_RAW'), ('U1', 'BAT_P', 'VBAT')):
    pd = fps[ref].FindPadByNumber(num)
    assert pd.GetNetname() == 'Net-(U1-BAT+)', (ref, num, pd.GetNetname())
    pd.SetNet(nets[net])

for ref, num in (('J1', '2'), ('U1', 'BAT_N')):             # battery return = GND (see add_boost_sch.py)
    pd = fps[ref].FindPadByNumber(num)
    assert pd.GetNetname() == 'Net-(U1-BAT-)', (ref, num, pd.GetNetname())
    pd.SetNet(nets['GND'])

# ---- parts
for ref, libsym, value, fp, _xy, pin_nets in sch.PARTS:
    lib, name = fp.split(':')
    f = pcb.FootprintLoad(LIBD + '/' + lib + '.pretty', name)
    f.SetFPID(pcb.LIB_ID(lib, name)); f.SetReference(ref); f.SetValue(value)
    b.Add(f)
    x, y, rot = place[ref]
    f.SetPosition(V(x, y)); f.SetOrientationDegrees(rot)
    f.SetPath(pcb.KIID_PATH('/' + uuids[ref]))
    f.Reference().SetVisible(False); f.Value().SetVisible(False)
    for item in list(f.GraphicalItems()):
        if item.GetLayer() in (pcb.F_SilkS, pcb.B_SilkS):
            f.Delete(item)
    for num, net in pin_nets.items():
        p = f.FindPadByNumber(num)
        assert p is not None, (ref, num)
        p.SetNet(nets[net])
# pad 6 of the SOT-23-6 is not connected: the schematic names that net, so the board must too
nets = b.GetNetsByName()
b.Add(pcb.NETINFO_ITEM(b, 'unconnected-(U26-NC-Pad6)'))
b.GetFootprints()  # (refresh)
nets = b.GetNetsByName()
[f for f in b.GetFootprints() if f.GetReference() == 'U26'][0].FindPadByNumber('6').SetNet(nets['unconnected-(U26-NC-Pad6)'])
b.Save(dst)
print('footprints', len(list(b.GetFootprints())), '->', dst)
