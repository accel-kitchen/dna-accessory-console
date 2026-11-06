"""Schematic part of the battery power path (plain python, text edit of the .kicad_sch).

LED power used to be U1.VUSB only.  Now:  battery -> MT3608B boost (5.0 V) -> POWER,  USB -> D2 -> POWER,
and the boost is switched off by Q1 while USB is present (EN pulled low), so USB wins and the cell is not drained.

  VBAT (J1.1 / U1.BAT+) --L1--> SW --D1--> POWER      U26 MT3608B: IN=VBAT EN=BOOST_EN SW FB GND
  POWER --R2--> FB --R3--> GND                          5.0 V = 0.6 V x (1 + 110k / 15k)   (datasheet Fig.1 values)
  U1.VUSB (net VUSB) --D2--> POWER                      Q1 (2N7002): G=VUSB, S=GND, D=BOOST_EN;  R4 BOOST_EN->VBAT pull-up
  R5 VUSB->GND (gate pull-down);  C26/C28 = input, C27/C29 (+ existing C25) = output capacitors

Nets are made with global labels at the pin ends, like gen/add_support_parts.py.  Run once; writes gen/_boost_uuids.json.
"""
import json, re, sys, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SCH = ROOT / 'dna-accesories.kicad_sch'
SYM = Path(r'C:\Program Files\KiCad\9.0\share\kicad\symbols')
PROJ_UUID = '39a00d90-ab18-44df-86d9-cc83da3529d4'
uid = lambda: str(uuid.uuid4())


def block(text, start):
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError


def indent(b):
    return '\n'.join('\t' + l if k else l for k, l in enumerate(b.split('\n')))


def lib_symbol(lib, name):
    """Embedded copy of a stock symbol (flattened when it `extends` another one), named Lib:Name."""
    d = (SYM / (lib + '.kicad_sym')).read_text(encoding='utf-8').replace('\r\n', '\n')
    b = block(d, d.index('\t(symbol "%s"\n' % name) + 1)
    m = re.search(r'\(extends "([^"]+)"\)', b)
    if m:
        parent = block(d, d.index('\t(symbol "%s"\n' % m.group(1)) + 1)
        # child properties win; the parent supplies pins and graphics
        for prop in ('Value', 'Footprint', 'Datasheet', 'Description', 'Reference'):
            cm = re.search(r'\(property "%s" "[^"]*"\n.*?\n\t\t\)\n' % prop, b, flags=re.S)
            pm = re.search(r'\(property "%s" "[^"]*"\n.*?\n\t\t\)\n' % prop, parent, flags=re.S)
            if cm and pm:
                parent = parent.replace(pm.group(0), cm.group(0), 1)
        parent = parent.replace('(symbol "%s_' % m.group(1), '(symbol "%s_' % name).replace('(symbol "%s"' % m.group(1), '(symbol "%s"' % name, 1)
        b = parent
    b = b.replace('(symbol "%s"' % name, '(symbol "%s:%s"' % (lib, name), 1)
    return indent(b)


# pin end positions in symbol coordinates (x, y up) and the direction the pin line points (into the body)
PINS = {
    'Device:C': {'1': (0, 3.81, 270), '2': (0, -3.81, 90)},
    'Device:R': {'1': (0, 3.81, 270), '2': (0, -3.81, 90)},
    'Device:L': {'1': (0, 3.81, 270), '2': (0, -3.81, 90)},
    'Device:D_Schottky': {'1': (-3.81, 0, 0), '2': (3.81, 0, 180)},                     # 1 = K, 2 = A
    'Regulator_Switching:MT3608': {'5': (-7.62, 2.54, 0), '4': (-7.62, -2.54, 0), '2': (0, -7.62, 90), '1': (7.62, 2.54, 180), '3': (7.62, -2.54, 180)},
    'Transistor_FET:Q_NMOS_GSD': {'1': (-5.08, 0, 0), '3': (2.54, 5.08, 270), '2': (2.54, -5.08, 90)},   # 1 = G, 2 = S, 3 = D (the symbol 2N7002 extends this one)
}
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
R0402 = 'Resistor_SMD:R_0402_1005Metric'
DSOD = 'Diode_SMD:D_SOD-123'
# ref, lib symbol, value, footprint, (x, y) on the A4 sheet, {pin: net}
PARTS = [
    ('U26', 'Regulator_Switching:MT3608', 'MT3608B', 'Package_TO_SOT_SMD:SOT-23-6', (229.87, 172.72), {'5': 'VBAT', '4': 'BOOST_EN', '2': 'GND', '1': 'SW', '3': 'FB'}),
    ('L1', 'Device:L', '10uH', 'Inductor_SMD:L_Bourns-SRN4018', (265.43, 172.72), {'1': 'VBAT', '2': 'SW'}),
    ('D1', 'Device:D_Schottky', '1N5819HW', DSOD, (229.87, 190.5), {'1': 'POWER', '2': 'SW'}),
    ('D2', 'Device:D_Schottky', '1N5819HW', DSOD, (254.0, 190.5), {'1': 'POWER', '2': 'VUSB'}),
    ('Q1', 'Transistor_FET:Q_NMOS_GSD', '2N7002', 'Package_TO_SOT_SMD:SOT-23', (275.59, 190.5), {'1': 'VUSB', '2': 'GND', '3': 'BOOST_EN'}),
    ('C26', 'Device:C', '10uF', C0805, (217.17, 139.7), {'1': 'VBAT', '2': 'GND'}),
    ('C28', 'Device:C', '10uF', C0805, (229.87, 139.7), {'1': 'VBAT', '2': 'GND'}),
    ('C27', 'Device:C', '10uF', C0805, (242.57, 139.7), {'1': 'POWER', '2': 'GND'}),
    ('C29', 'Device:C', '10uF', C0805, (255.27, 139.7), {'1': 'POWER', '2': 'GND'}),
    ('R2', 'Device:R', '110k', R0402, (217.17, 154.94), {'1': 'POWER', '2': 'FB'}),
    ('R3', 'Device:R', '15k', R0402, (229.87, 154.94), {'1': 'FB', '2': 'GND'}),
    ('R4', 'Device:R', '100k', R0402, (242.57, 154.94), {'1': 'VBAT', '2': 'BOOST_EN'}),
    ('R5', 'Device:R', '100k', R0402, (255.27, 154.94), {'1': 'VUSB', '2': 'GND'}),
]


def label(name, x, y, ang):
    j = 'left' if ang in (90, 0) else 'right'
    return ('\t(global_label "%s"\n\t\t(shape input)\n\t\t(at %.2f %.2f %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n'
            '\t\t(uuid "%s")\n\t\t(property "Intersheetrefs" "${INTERSHEET_REFS}"\n\t\t\t(at %.2f %.2f 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n\t)'
            % (name, x, y, ang, j, uid(), x, y))


def part(lib, ref, value, fp, x, y, uu, pin_numbers):
    def prop(k, v, dx, dy, hide):
        return ('\t\t(property "%s" "%s"\n\t\t\t(at %.2f %.2f 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n%s\t\t\t)\n\t\t)\n'
                % (k, v, x + dx, y + dy, '\t\t\t\t(hide yes)\n' if hide else '\t\t\t\t(justify left)\n'))
    pins = ''.join('\t\t(pin "%s"\n\t\t\t(uuid "%s")\n\t\t)\n' % (n, uid()) for n in pin_numbers)
    return ('\t(symbol\n\t\t(lib_id "%s")\n\t\t(at %.2f %.2f 0)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(uuid "%s")\n'
            % (lib, x, y, uu) + prop('Reference', ref, 1.5, -1.0, False) + prop('Value', value, 1.5, 1.0, False) + prop('Footprint', fp, 0, 0, True)
            + prop('Datasheet', '~', 0, 0, True) + prop('Description', '', 0, 0, True) + pins
            + '\t\t(instances\n\t\t\t(project "dna-accesories"\n\t\t\t\t(path "/%s"\n\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)' % (PROJ_UUID, ref))


def pwr_flag(x, y, n):
    return ('\t(symbol\n\t\t(lib_id "power:PWR_FLAG")\n\t\t(at %.2f %.2f 0)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom no)\n\t\t(on_board no)\n\t\t(dnp no)\n\t\t(uuid "%s")\n'
            '\t\t(property "Reference" "#FLG0%d"\n\t\t\t(at %.2f %.2f 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n'
            '\t\t(property "Value" "PWR_FLAG"\n\t\t\t(at %.2f %.2f 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n'
            '\t\t(property "Footprint" ""\n\t\t\t(at %.2f %.2f 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n'
            '\t\t(property "Datasheet" "~"\n\t\t\t(at %.2f %.2f 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n'
            '\t\t(pin "1"\n\t\t\t(uuid "%s")\n\t\t)\n'
            '\t\t(instances\n\t\t\t(project "dna-accesories"\n\t\t\t\t(path "/%s"\n\t\t\t\t\t(reference "#FLG0%d")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)'
            % (x, y, uid(), n, x, y - 3.81, x, y - 5.08, x, y, x, y, uid(), PROJ_UUID, n))


def main():
    t = SCH.read_text(encoding='utf-8', newline='').replace('\r\n', '\n')
    if '"MT3608B"' in t:
        sys.exit('already applied')
    # 1) embedded library symbols (C and R are already there)
    need = [('Device', 'L'), ('Device', 'D_Schottky'), ('Regulator_Switching', 'MT3608'), ('Transistor_FET', 'Q_NMOS_GSD'), ('power', 'PWR_FLAG')]
    libs = '\n'.join(lib_symbol(l, n) for l, n in need if '(symbol "%s:%s"' % (l, n) not in t)
    t = t.replace('\t(lib_symbols\n', '\t(lib_symbols\n' + libs + '\n', 1)
    # 2) U1.VUSB: the label that used to say POWER now says VUSB; U1.BAT+ gets the name VBAT
    old = '(global_label "POWER"\n\t\t(shape input)\n\t\t(at 17.78 -49.53 0)'
    assert old in t
    t = t.replace(old, old.replace('"POWER"', '"VUSB"'), 1)
    # BAT- of the XIAO is its GND (Seeed XIAO nRF52840 v1.1 schematic: the battery has only VBAT and GND), so the battery return joins GND here:
    # the boost input current then does not have to pass through the module
    items = [label('VBAT', 17.78, -44.45, 0), label('GND', 17.78, -13.97, 0)]
    # 3) parts with a label on every pin
    uuids = {}
    for ref, lib, value, fp, (x, y), nets in PARTS:
        u = uid(); uuids[ref] = u
        items.append(part(lib, ref, value, fp, x, y, u, list(PINS[lib])))
        for num, net in nets.items():
            px, py, pang = PINS[lib][num]
            items.append(label(net, round(x + px, 2), round(y - py, 2), (pang + 180) % 360))
    # 4) POWER is driven by passive pins (diodes) and VBAT by an off-board battery: power flags say so
    items.append(pwr_flag(285.75, 160.02, 1)); items.append(label('POWER', 285.75, 160.02, 90))
    items.append(pwr_flag(285.75, 175.26, 2)); items.append(label('VBAT', 285.75, 175.26, 90))
    k = t.index('\t(sheet_instances')
    t = t[:k] + '\n'.join(items) + '\n' + t[k:]
    SCH.write_text(t.replace('\n', '\r\n'), encoding='utf-8', newline='')
    (ROOT / 'gen' / '_boost_uuids.json').write_text(json.dumps(uuids, indent=1), encoding='utf-8')
    print('parts added:', ', '.join(uuids))


if __name__ == '__main__':
    main()
