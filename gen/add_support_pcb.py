"""KiCad python: PCB side of the support parts (review items 04/05/09).

* U1 moved 2.5 mm toward the bottom edge so the USB-C mouth sits outside the board
* C1..C24 (100 nF, back side, under each LED), C25 (10 uF bulk), R1 (100 ohm series on the first DIN)
* new net DIN_FIRST (R1.2 / U2.4); old copper removed (re-routed by route_board.py)
"""
import pcbnew as pcb, json, math
R = r'D:\Document\Research\software\pcb\dna-accesories'
P = R + r'\dna-accesories.kicad_pcb'
LIBD = r'C:\Program Files\KiCad\9.0\share\kicad\footprints'
b = pcb.LoadBoard(P)
V = lambda x, y: pcb.VECTOR2I(round(x * 1e6), round(y * 1e6))
mm = pcb.ToMM
uu = json.load(open(R + r'\gen\_part_uuids.json'))
fps = {f.GetReference(): f for f in b.GetFootprints()}
assert 'C1' not in fps, 'already applied'
for t in list(b.GetTracks()):
    b.Delete(t)

u1 = fps['U1']
u1.SetPosition(V(100, 134.5))

nets = b.GetNetsByName()
if 'DIN_FIRST' not in nets:
    n = pcb.NETINFO_ITEM(b, 'DIN_FIRST'); b.Add(n)
nets = b.GetNetsByName()
fps['U2'].FindPadByNumber('4').SetNet(nets['DIN_FIRST'])


def add(ref, lib, name, x, y, layer_back, want):
    """want: callable(pad1_xy, centre) -> True when pad 1 is on the wanted side"""
    f = pcb.FootprintLoad(LIBD + '\\' + lib + '.pretty', name)
    f.SetFPID(pcb.LIB_ID(lib, name)); f.SetReference(ref); f.SetValue(uu_val[ref])
    b.Add(f)
    if layer_back:
        f.SetPosition(V(x, y)); f.Flip(V(x, y), False)
    else:
        f.SetPosition(V(x, y))
    best = None
    for ang in range(0, 360, 45):
        f.SetOrientationDegrees(ang)
        p1 = f.FindPadByNumber('1').GetPosition()
        if want(mm(p1.x) - x, mm(p1.y) - y):
            best = ang; break
    assert best is not None, ref
    f.SetOrientationDegrees(best)
    f.SetPath(pcb.KIID_PATH('/' + uu[ref]))
    f.Reference().SetVisible(False); f.Value().SetVisible(False)
    for item in list(f.GraphicalItems()):
        if item.GetLayer() in (pcb.F_SilkS, pcb.B_SilkS):
            f.Delete(item)
    return f


uu_val = {('C%d' % i): '100nF' for i in range(1, 25)}
uu_val['C25'] = '10uF'; uu_val['R1'] = '100'
leds = ['U%d' % i for i in range(2, 26)]
for k, ref in enumerate(leds):
    led = fps[ref]; x, y = mm(led.GetX()), mm(led.GetY())
    left = x < 100
    # pad 1 (POWER) must sit toward the LED's VDD corner: NE for the left LED, SW for the right LED
    want = (lambda dx, dy: dx > 0.2 and dy < -0.2) if left else (lambda dx, dy: dx < -0.2 and dy > 0.2)
    c = add('C%d' % (k + 1), 'Capacitor_SMD', 'C_0402_1005Metric', x, y, True, want)
    c.FindPadByNumber('1').SetNet(nets['POWER']); c.FindPadByNumber('2').SetNet(nets['GND'])
c = add('C25', 'Capacitor_SMD', 'C_0805_2012Metric', 108.0, 121.4, True, lambda dx, dy: dx < -0.2)
c.FindPadByNumber('1').SetNet(nets['POWER']); c.FindPadByNumber('2').SetNet(nets['GND'])
r = add('R1', 'Resistor_SMD', 'R_0402_1005Metric', 92.0, 121.4, True, lambda dx, dy: dx < -0.2)
r.FindPadByNumber('1').SetNet(nets['CODON_START']); r.FindPadByNumber('2').SetNet(nets['DIN_FIRST'])
b.Save(P)
print('footprints', len(list(b.GetFootprints())))
