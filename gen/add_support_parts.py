"""Schematic additions for review items 04 / 05 / 08 (plain python, text edit of the .kicad_sch).

* C1..C24: 100 nF across every LED VDD/GND (datasheet p.7), C25: 10 uF bulk on POWER/GND
* R1: 100 ohm in series between D6 and the first LED DIN (net CODON_START | DIN_FIRST)
* U1: pin types for VUSB / GND / BAT corrected, no-connect flags on unused pins
"""
import re, uuid, json, sys
ROOT = r'D:\Document\Research\software\pcb\dna-accesories'
SCH = ROOT + r'\dna-accesories.kicad_sch'
LIB = ROOT + r'\lib\102010448\102010448.kicad_sym'
DEV = r'C:\Program Files\KiCad\9.0\share\kicad\symbols\Device.kicad_sym'
PROJ_UUID = '39a00d90-ab18-44df-86d9-cc83da3529d4'
uid = lambda: str(uuid.uuid4())


def block(text, start):
    """text of the parenthesised expression that begins at index start"""
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


def lib_symbol(name):
    d = open(DEV, encoding='utf8').read().replace('\r\n', '\n')
    i = d.index('\t(symbol "%s"\n' % name) + 1
    b = block(d, i)
    b = b.replace('(symbol "%s"' % name, '(symbol "Device:%s"' % name, 1)
    return '\n'.join('\t' + l if k else l for k, l in enumerate(b.split('\n')))  # indent one more level


def set_pin_types(text, changes):
    """changes: {pin number: new electrical type} inside the XIAO symbol"""
    a = text.index('(symbol "XIAO_NRF52840:102010448"') if 'XIAO_NRF52840:102010448"' in text else 0
    out = text; pos = a
    for m in list(re.finditer(r'\(pin (\w+) (?:line|clock|inverted|inverted_clock)', text[a:])):
        s = a + m.start(); b = block(text, s)
        num = re.search(r'\(number "([^"]+)"', b).group(1)
        if num in changes:
            nb = b.replace('(pin %s ' % m.group(1), '(pin %s ' % changes[num], 1)
            out = out.replace(b, nb, 1)
    return out


def xiao_pins(text):
    a = text.index('(symbol "XIAO_NRF52840:102010448"')
    pins = []
    seg = block(text, a)
    for m in re.finditer(r'\(pin (\w+) (?:line|clock|inverted|inverted_clock)', seg):
        m = type('M', (), {'start': lambda self, mm=m: mm.start()})()
        s = a + m.start(); b = block(text, s)
        at = re.search(r'\(at ([-\d.]+) ([-\d.]+) (\d+)\)', b)
        pins.append(dict(num=re.search(r'\(number "([^"]+)"', b).group(1), name=re.search(r'\(name "([^"]+)"', b).group(1),
                         x=float(at.group(1)), y=float(at.group(2))))
    return pins


def main():
    t = open(SCH, encoding='utf8', newline='').read().replace('\r\n', '\n')
    if 'Device:C' in t:
        sys.exit('already applied')
    # 1) library symbols for C and R
    t = t.replace('\t(lib_symbols\n', '\t(lib_symbols\n' + lib_symbol('C') + '\n' + lib_symbol('R') + '\n', 1)
    # 2) U1 pin types; NC flags
    types = {'VUSB': 'power_out', 'GND': 'power_out', 'BAT_P': 'bidirectional', 'BAT_N': 'bidirectional'}
    t = set_pin_types(t, types)
    ux, uy = -2.54, -29.21
    nc_nums = ['0', '1', '2', '3', '4', '5', '7', '8', '9', '10', 'NFC1', 'NFC2', 'TP1', 'TP2', 'TP3', 'TP5', '3V3']
    pins = {p['num']: p for p in xiao_pins(t)}
    extra = []
    for n in nc_nums:
        p = pins[n]
        extra.append('\t(no_connect\n\t\t(at %.2f %.2f)\n\t\t(uuid "%s")\n\t)' % (ux + p['x'], uy - p['y'], uid()))
    # 3) parts
    def label(name, x, y, ang):
        j = 'left' if ang in (90, 0) else 'right'
        return ('\t(global_label "%s"\n\t\t(shape input)\n\t\t(at %.2f %.2f %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s)\n\t\t)\n'
                '\t\t(uuid "%s")\n\t\t(property "Intersheetrefs" "${INTERSHEET_REFS}"\n\t\t\t(at %.2f %.2f 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n\t)'
                % (name, x, y, ang, j, uid(), x, y))

    def part(lib, ref, value, fp, x, y, uu):
        def prop(k, v, dx, dy, hide):
            return ('\t\t(property "%s" "%s"\n\t\t\t(at %.2f %.2f 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n%s\t\t\t)\n\t\t)\n'
                    % (k, v, x + dx, y + dy, '\t\t\t\t(hide yes)\n' if hide else '\t\t\t\t(justify left)\n'))
        return ('\t(symbol\n\t\t(lib_id "%s")\n\t\t(at %.2f %.2f 0)\n\t\t(unit 1)\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(dnp no)\n\t\t(uuid "%s")\n'
                % (lib, x, y, uu) + prop('Reference', ref, 1.5, -1.0, False) + prop('Value', value, 1.5, 1.0, False) + prop('Footprint', fp, 0, 0, True)
                + prop('Datasheet', '~', 0, 0, True) + prop('Description', '', 0, 0, True)
                + '\t\t(pin "1"\n\t\t\t(uuid "%s")\n\t\t)\n\t\t(pin "2"\n\t\t\t(uuid "%s")\n\t\t)\n' % (uid(), uid())
                + '\t\t(instances\n\t\t\t(project "dna-accesories"\n\t\t\t\t(path "/%s"\n\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)' % (PROJ_UUID, ref))

    uuids = {}
    items = []
    for k in range(25):
        ref = 'C%d' % (k + 1)
        x = round((200 + 17 * (k % 5)) / 1.27) * 1.27; y = round((30 + 24 * (k // 5)) / 1.27) * 1.27
        u = uid(); uuids[ref] = u
        fp, val = ('Capacitor_SMD:C_0805_2012Metric', '10uF') if k == 24 else ('Capacitor_SMD:C_0402_1005Metric', '100nF')
        items.append(part('Device:C', ref, val, fp, x, y, u))
        items.append(label('POWER', x, y - 3.81, 90)); items.append(label('GND', x, y + 3.81, 270))
    u = uid(); uuids['R1'] = u
    items.append(part('Device:R', 'R1', '100', 'Resistor_SMD:R_0402_1005Metric', 200.66, 160.02, u))
    items.append(label('CODON_START', 200.66, 160.02 - 3.81, 90)); items.append(label('DIN_FIRST', 200.66, 160.02 + 3.81, 270))
    # first LED DIN label gets the new net name
    old = '(global_label "CODON_START"\n\t\t(shape input)\n\t\t(at 54.61 35.56 180)'
    assert old in t
    t = t.replace(old, old.replace('CODON_START', 'DIN_FIRST'), 1)
    # insert before sheet_instances
    k = t.index('\t(sheet_instances')
    t = t[:k] + '\n'.join(extra + items) + '\n' + t[k:]
    open(SCH, 'w', encoding='utf8', newline='').write(t.replace('\n', '\r\n'))
    # library file
    lt = open(LIB, encoding='utf8', newline='').read().replace('\r\n', '\n')
    lt = set_pin_types(lt, types) if 'XIAO_NRF52840:102010448"' in lt else lt
    # library symbol uses its own name, apply by number on the whole file
    lt2 = open(LIB, encoding='utf8', newline='').read().replace('\r\n', '\n')
    for m in list(re.finditer(r'\(pin (\w+) (?:line|clock|inverted|inverted_clock)', lt2)):
        pass
    out = lt2
    for m in list(re.finditer(r'\(pin (\w+) (?:line|clock|inverted|inverted_clock)', lt2)):
        b = block(lt2, m.start()); num = re.search(r'\(number "([^"]+)"', b).group(1)
        if num in types:
            out = out.replace(b, b.replace('(pin %s ' % m.group(1), '(pin %s ' % types[num], 1), 1)
    open(LIB, 'w', encoding='utf8', newline='').write(out.replace('\n', '\r\n'))
    json.dump(uuids, open(ROOT + r'\gen\_part_uuids.json', 'w'))
    print('parts', len(uuids), 'nc', len(extra))


main()
