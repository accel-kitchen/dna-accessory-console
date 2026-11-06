"""Build the Seeed Fusion PCBA order package in fusion/.

Inputs : dna-accesories.kicad_pcb (via kicad-cli and gen/dump_assembly_data.py), 'BOM Template.xlsx'
Outputs: fusion/gerber/*, fusion/<name>_gerber.zip, fusion/BOM.xlsx (Seeed template), fusion/BOM_detail.xlsx,
         fusion/centroid.csv, fusion/centroid.pos, fusion/assembly-drawing.pdf
Usage  : python gen/make_fusion_package.py <asm_data.json>   (json from dump_assembly_data.py, KiCad python)
"""
import csv, json, re, shutil, subprocess, sys, zipfile
from pathlib import Path
import openpyxl, fitz
from openpyxl.styles import Alignment, Font

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'fusion'
KCLI = r'C:\Program Files\KiCad\9.0\bin\kicad-cli.exe'
PCB = str(ROOT / 'dna-accesories.kicad_pcb')
data = json.load(open(sys.argv[1]))
parts = data['parts']

# ---------------------------------------------------------------- part catalogue (MPN = manufacturer part number)
CAT = {
    ('XL-1010RGBC-WS2812B',): dict(
        mpn='XL-1010RGBC-WS2812B', mfr='XINGLIGHT', desc='1010 RGB LED with built-in WS2812B-type driver, 4-pad',
        pkg='1.0 x 1.0 mm SMD (4 pad)', lcsc='C5349953',
        link='https://www.lcsc.com/product-detail/Light-Emitting-Diodes-LED_XINGLIGHT-XL-1010RGBC-WS2812B_C5349953.html',
        alt='', note='Orientation-sensitive (pad 1 = DOUT). MSL: confirm with the reel label and bake if needed before reflow.'),
    ('100nF',): dict(
        mpn='CL05B104KA5NNNC', mfr='Samsung Electro-Mechanics', desc='MLCC 100 nF 25 V X7R +/-10 % 0402',
        pkg='0402 (1005 metric)', lcsc='',
        link='https://www.digikey.com/en/products/detail/samsung-electro-mechanics/CL05B104KA5NNNC/5961204',
        alt='Murata GRM155R71E104KE14D (same value/voltage/dielectric)', note='Non-polarized. One per LED, back side, directly behind the LED.'),
    ('10uF',): dict(
        mpn='CL21A106KAYNNNE', mfr='Samsung Electro-Mechanics', desc='MLCC 10 uF 25 V X5R +/-10 % 0805',
        pkg='0805 (2012 metric)', lcsc='C15850', link='https://www.lcsc.com/product-detail/C15850.html',
        alt='Murata GRM21BR61E106KA73L (same value/voltage/dielectric)', note='Non-polarized. Bulk capacitor on the 5 V rail.'),
    ('100',): dict(
        mpn='RC0402FR-07100RL', mfr='Yageo', desc='Thick-film resistor 100 ohm 1 % 1/16 W 0402',
        pkg='0402 (1005 metric)', lcsc='C106232', link='https://www.lcsc.com/product-detail/C106232.html',
        alt='UNI-ROYAL 0402WGF1000TCE', note='Series resistor in the LED data line (XIAO D6 -> U2 DIN).'),
    ('B2B-PH-SM4-TB',): dict(
        mpn='B2B-PH-SM4-TB(LF)(SN)', mfr='JST', desc='PH-series 2-pin 2.0 mm pitch SMD side-entry wafer, tin plated',
        pkg='SMD, side entry', lcsc='C160352',
        link='https://www.lcsc.com/product-detail/image/B2B-PH-SM4-TB-LF-SN_C160352.html',
        alt='', note='Battery connector. Pad 1 = BAT+ (left, "+" on the silkscreen), pad 2 = BAT-. Datasheet: jst-mfg.com ePH.pdf'),
    ('MT3608B',): dict(
        mpn='MT3608B', mfr='Aerosemi', desc='1.2 MHz step-up converter, 2.5-24 V in, 4 A switch, adjustable output, SOT-23-6',
        pkg='SOT-23-6', lcsc='', link='https://www.lcsc.com/search?q=MT3608B',
        alt='MT3608 (same SOT-23-6 pinout: 1 SW, 2 GND, 3 FB, 4 EN, 5 VIN, 6 NC)',
        note='Pin 1 = SW (see detail E). Output 5.0 V = 0.6 V x (1 + 110k/15k). Battery to LED boost; switched off by Q1 while USB is present.'),
    ('10uH',): dict(
        mpn='SRN4018TA-100M', mfr='Bourns', desc='Shielded power inductor 10 uH, Irms 1.2 A, Isat 1.3 A, DCR 0.15 ohm max, 4.0 x 4.0 x 1.8 mm',
        pkg='4.0 x 4.0 mm SMD', lcsc='', link='https://www.digikey.com/en/products/result?keywords=SRN4018TA-100M',
        alt='Sunlord SWPA4020S100MT (LCSC C82398; 10 uH, Irms 0.9 A, Isat 1.6 A, 4 x 4 x 2 mm): check its land pattern before substituting',
        note='Non-polarized. Boost inductor: carries up to ~0.8 A at full white on a 3.0 V cell.'),
    ('1N5819HW',): dict(
        mpn='1N5819HW-7-F', mfr='Diodes Incorporated', desc='Schottky diode 40 V 1 A, SOD-123',
        pkg='SOD-123', lcsc='C82544', link='https://lcsc.com/product-detail/Schottky-Diodes_Diodes-Incorporated-1N5819HW-7-F_C82544.html',
        alt='Any SOD-123 Schottky, 40 V, 1 A, Vf <= 0.5 V at 1 A', note='Polarized: cathode (bar) at pad 1. D1 = boost rectifier, D2 = USB to LED power (blocks battery current into USB).'),
    ('2N7002',): dict(
        mpn='2N7002-7-F', mfr='Diodes Incorporated', desc='N-channel MOSFET 60 V 210 mA, SOT-23',
        pkg='SOT-23', lcsc='C85049', link='https://www.lcsc.com/product-detail/C85049.html',
        alt='2N7002K-7 (LCSC C85047)', note='Pin 1 = gate, 2 = source, 3 = drain. Pulls the boost EN pin low while USB is present.'),
    ('110k',): dict(
        mpn='RC0402FR-07110KL', mfr='Yageo', desc='Thick-film resistor 110 kohm 1 % 1/16 W 0402',
        pkg='0402 (1005 metric)', lcsc='', link='https://www.lcsc.com/search?q=RC0402FR-07110KL', alt='Any 0402 110 kohm 1 %',
        note='Boost feedback divider (top): 5.0 V output with R3 = 15 kohm.'),
    ('15k',): dict(
        mpn='RC0402FR-0715KL', mfr='Yageo', desc='Thick-film resistor 15 kohm 1 % 1/16 W 0402',
        pkg='0402 (1005 metric)', lcsc='', link='https://www.lcsc.com/search?q=RC0402FR-0715KL', alt='Any 0402 15 kohm 1 %',
        note='Boost feedback divider (bottom).'),
    ('100k',): dict(
        mpn='RC0402FR-07100KL', mfr='Yageo', desc='Thick-film resistor 100 kohm 1 % 1/16 W 0402',
        pkg='0402 (1005 metric)', lcsc='', link='https://www.lcsc.com/search?q=RC0402FR-07100KL', alt='Any 0402 100 kohm',
        note='R4: boost EN pull-up to the battery. R5: gate pull-down of Q1.'),
    ('102010448',): dict(
        mpn='102010448', mfr='Seeed Studio', desc='Seeed Studio XIAO nRF52840 (XIAO BLE), plain version without pin headers',
        pkg='21 x 17.8 mm castellated SMD module', lcsc='',
        link='https://www.seeedstudio.com/Seeed-XIAO-BLE-nRF52840-p-5201.html',
        alt='', note='Seeed SKU 102010448 (NOT the "Pre-Soldered" variant 102010631). Bottom side of the PCB; USB-C end faces the board bottom edge.'),
}

def natkey(r):
    m = re.match(r'([A-Za-z]+)(\d+)', r)
    return (m.group(1), int(m.group(2)))

groups = {}
for p in parts:
    groups.setdefault((p['value'],), []).append(p)
lines = []
for key, ps in groups.items():
    c = CAT[key]
    refs = sorted((p['ref'] for p in ps), key=natkey)
    sides = sorted({p['side'] for p in ps})
    lines.append(dict(refs=refs, qty=len(refs), sides='/'.join(sides), value=key[0], fp=ps[0]['fp'], **c))
order = {'102010448': 0, 'B2B-PH-SM4-TB': 1, 'XL-1010RGBC-WS2812B': 2, 'MT3608B': 3, '10uH': 4, '1N5819HW': 5, '2N7002': 6, '10uF': 7, '100nF': 8, '100': 9, '110k': 10, '15k': 11, '100k': 12}
lines.sort(key=lambda l: order[l['value']])
assert sum(l['qty'] for l in lines) == len(parts) == 65

OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------- BOM in the Seeed template (first 4 columns only)
wb = openpyxl.load_workbook(ROOT / 'BOM Template.xlsx')
ws = wb.worksheets[0]
for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
    for c in row:
        c.value = None
for i, l in enumerate(lines, start=2):
    ws.cell(i, 1, ','.join(l['refs'])); ws.cell(i, 2, l['mpn']); ws.cell(i, 3, l['qty']); ws.cell(i, 4, l['link'])
    for col in range(1, 5):
        src = ws.cell(2, col)
        ws.cell(i, col).alignment = Alignment(wrap_text=(col == 1), vertical='top')
ws.column_dimensions['A'].width = 52
wb.save(OUT / 'BOM.xlsx')

# ---------------------------------------------------------------- detailed BOM
wb2 = openpyxl.Workbook(); w = wb2.active; w.title = 'BOM detail'
hdr = ['Designator', 'Qty', 'Value', 'Description', 'Package / footprint', 'Side', 'Manufacturer', 'MPN / Seeed SKU', 'LCSC #', 'Approved alternate', 'Assembly note', 'Link']
w.append(hdr)
for l in lines:
    w.append([','.join(l['refs']), l['qty'], l['value'], l['desc'], l['pkg'] + ' / ' + l['fp'], l['sides'], l['mfr'], l['mpn'], l['lcsc'], l['alt'], l['note'], l['link']])
for c in w[1]:
    c.font = Font(bold=True)
for col, wd in zip('ABCDEFGHIJKL', (40, 5, 14, 46, 40, 10, 24, 24, 10, 36, 60, 50)):
    w.column_dimensions[col].width = wd
for row in w.iter_rows(min_row=2):
    for c in row:
        c.alignment = Alignment(wrap_text=True, vertical='top')
wb2.save(OUT / 'BOM_detail.xlsx')

# ---------------------------------------------------------------- gerbers / drill / centroid (absolute origin everywhere)
gdir = OUT / 'gerber'
if gdir.exists():
    shutil.rmtree(gdir)
gdir.mkdir()
run = lambda *a: subprocess.run([KCLI, *a], check=True, capture_output=True, text=True)
run('pcb', 'export', 'gerbers', '--layers', 'F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts',
    '--subtract-soldermask', '-o', str(gdir) + '/', PCB)
run('pcb', 'export', 'drill', '--format', 'excellon', '--drill-origin', 'absolute', '--excellon-units', 'mm',
    '-o', str(gdir) + '/', PCB)
run('pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both', '--smd-only', '-o', str(OUT / 'centroid_kicad.csv'), PCB)
run('pcb', 'export', 'pos', '--format', 'ascii', '--units', 'mm', '--side', 'both', '--smd-only', '-o', str(OUT / 'centroid.pos'), PCB)
# Fusion-style column names
rows = list(csv.DictReader(open(OUT / 'centroid_kicad.csv', encoding='utf-8')))
assert len(rows) == 65, len(rows)
with open(OUT / 'centroid.csv', 'w', newline='', encoding='utf-8') as f:
    cw = csv.writer(f)
    cw.writerow(['Designator', 'Val', 'Package', 'Mid X', 'Mid Y', 'Rotation', 'Layer'])
    for r in sorted(rows, key=lambda r: (r['Side'], natkey(r['Ref']))):
        cw.writerow([r['Ref'], r['Val'], r['Package'], r['PosX'], r['PosY'], r['Rot'], 'Top' if r['Side'] == 'top' else 'Bottom'])
(OUT / 'centroid_kicad.csv').unlink()

# ---------------------------------------------------------------- assembly drawing (SVG -> PDF, ASCII text only)
x0, y0, x1, y1 = data['bounds']
def poly_path(pts, mx=lambda x: x, my=lambda y: y):
    return 'M' + ' L'.join(f'{mx(x):.3f},{my(y):.3f}' for x, y in pts) + ' Z'

def outline_svg(mx, my, sw):
    d = ''
    for o in data['outline']:
        d += poly_path(o['ext'], mx, my) + ' '
        for h in o['holes']:
            d += poly_path(h, mx, my) + ' '
    return f'<path d="{d}" fill="#e9efe6" fill-rule="evenodd" stroke="#111" stroke-width="{sw}"/>'

def rot_pt(px, py, cx, cy, a):
    import math
    r = math.radians(a)
    return (cx + (px - cx) * math.cos(r) + (py - cy) * math.sin(r), cy - (px - cx) * math.sin(r) + (py - cy) * math.cos(r))

def pad_svg(p, d, mx, my, s, col):
    cx, cy = mx(d['x']), my(d['y'])
    w_, h_ = d['w'] * s, d['h'] * s
    rot = (-d['rot']) if True else 0
    return f'<rect x="{cx - w_ / 2:.3f}" y="{cy - h_ / 2:.3f}" width="{w_:.3f}" height="{h_:.3f}" fill="{col}" transform="rotate({rot:.1f} {cx:.3f} {cy:.3f})"/>'

def page(side, scale=3.5, detail=None):
    """Full-board view. side='top' or 'bottom' (bottom is mirrored as seen from below)."""
    k = scale / 2.0
    M = 12 * scale
    bw = (x1 - x0) * scale
    W = max(bw + 2 * M, 360)
    H = (y1 - y0) * scale + 2 * M + 50
    mir = side == 'bottom'
    ox = (W - bw) / 2
    mx = (lambda x: (x1 - x) * scale + ox) if mir else (lambda x: (x - x0) * scale + ox)
    my = lambda y: (y - y0) * scale + M + 50
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}" height="{H:.1f}" viewBox="0 0 {W:.1f} {H:.1f}" font-family="Helvetica">']
    svg.append(f'<rect width="100%" height="100%" fill="white"/>')
    svg.append(f'<text x="14" y="18" font-size="13" font-weight="bold">DNA LED pendant - {side.upper()} side assembly drawing</text>')
    svg.append(f'<text x="14" y="30" font-size="7.5">{"Viewed from below (mirrored). " if mir else ""}PCB {x1 - x0:.2f} x {y1 - y0:.2f} mm, 2 layers, 1.6 mm.</text>')
    svg.append(f'<text x="14" y="40" font-size="7.5">{"" if mir else "Black dot beside an LED = its pin 1 side. "}Designators are NOT printed on the board silkscreen.</text>')
    svg.append(outline_svg(mx, my, 0.4))
    for p in parts:
        if p['side'] != side:
            continue
        for d in p['pads']:
            svg.append(pad_svg(p, d, mx, my, scale, '#c9a227'))
        cx, cy = mx(p['x']), my(p['y'])
        lab = p['ref']
        if p['ref'].startswith('U') and p['ref'] != 'U1':      # LED : body + pin-1 triangle
            pad1 = next(d for d in p['pads'] if d['num'] == '1')
            body = 1.0 * scale
            svg.append(f'<rect x="{cx - body / 2:.2f}" y="{cy - body / 2:.2f}" width="{body:.2f}" height="{body:.2f}" fill="none" stroke="#333" stroke-width="0.25"/>')
            px_, py_ = mx(pad1['x']), my(pad1['y'])
            ux, uy = (px_ - cx), (py_ - cy)
            n = (ux * ux + uy * uy) ** .5 or 1
            ux, uy = ux / n, uy / n
            tx, ty = cx + ux * body * 0.95, cy + uy * body * 0.95
            svg.append(f'<circle cx="{tx:.2f}" cy="{ty:.2f}" r="0.9" fill="#000"/>')
            svg.append(f'<text x="{cx + body * 1.7:.2f}" y="{cy + 1.2:.2f}" font-size="3.2" fill="#003">{lab}</text>')
        elif p['ref'] == 'U1':
            xs = [mx(d['x']) for d in p['pads']]; ys = [my(d['y']) for d in p['pads']]
            svg.append(f'<rect x="{min(xs) - 1.5:.1f}" y="{min(ys) - 1.5:.1f}" width="{max(xs) - min(xs) + 3:.1f}" height="{max(ys) - min(ys) + 3:.1f}" fill="none" stroke="#06c" stroke-width="0.5" stroke-dasharray="2,1"/>')
            cxm, cym = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            for j, (txt, fs) in enumerate((('U1 XIAO nRF52840', 3.4), ('SKU 102010448', 2.6), ('USB-C end -> board edge', 2.2))):
                svg.append(f'<text x="{cxm:.1f}" y="{cym - 4 + j * 6:.1f}" font-size="{fs}" text-anchor="middle" fill="#06c">{txt}</text>')
        elif p['ref'] == 'J1':
            svg.append(f'<text x="{cx - 12:.1f}" y="{cy - 14:.1f}" font-size="5" fill="#a00">J1 B2B-PH-SM4-TB(LF)(SN)</text>')
            svg.append(f'<text x="{cx - 12:.1f}" y="{cy - 8:.1f}" font-size="4" fill="#a00">pad1 = BAT+ (marked +)  pad2 = BAT-</text>')
        else:                                                  # passives (no polarity)
            if not re.match(r'C([1-9]|1\d|2[0-4])$', p['ref']):
                svg.append(f'<text x="{cx - 2:.1f}" y="{cy - 3:.1f}" font-size="4" fill="#060">{lab}</text>')
            else:
                svg.append(f'<text x="{cx + (3.2 if p["x"] > 100 else -3.2 - 7):.2f}" y="{cy + 3.4:.2f}" font-size="3" fill="#060">{lab}</text>')
    svg.append('</svg>')
    return '\n'.join(svg), W, H

def detail_page(title, refs, scale, notes):
    sel = [p for p in parts if p['ref'] in refs]
    xs = [d['x'] for p in sel for d in p['pads']]; ys = [d['y'] for p in sel for d in p['pads']]
    pad = 2.0
    bx0, bx1, by0, by1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    side = sel[0]['side']
    mir = side == 'bottom'
    M = 20
    import textwrap
    notes = [ln for n in notes for ln in textwrap.wrap(n, 78)]
    W = max((bx1 - bx0) * scale + 2 * M, 440); H = (by1 - by0) * scale + 2 * M + 60 + 11 * len(notes) + 11 * len(sel)
    ox = (W - (bx1 - bx0) * scale) / 2
    mx = (lambda x: (bx1 - x) * scale + ox) if mir else (lambda x: (x - bx0) * scale + ox)
    my = lambda y: (y - by0) * scale + M + 40 + 11 * len(sel)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" font-family="Helvetica"><rect width="100%" height="100%" fill="white"/>']
    svg.append(f'<text x="{M}" y="16" font-size="11" font-weight="bold">{title}</text>')
    svg.append(f'<text x="{M}" y="30" font-size="8">{side.upper()} side{" - viewed from below (mirrored)" if mir else ""}; scale {scale}:1</text>')
    for p in sel:
        for d in p['pads']:
            svg.append(pad_svg(p, d, mx, my, scale, '#c9a227'))
            svg.append(f'<text x="{mx(d["x"]):.1f}" y="{my(d["y"]) + 2.5:.1f}" font-size="7" text-anchor="middle" font-weight="bold">{d["num"]}</text>')
            net = d['net'].replace('unconnected-', 'NC ').replace('Net-(', '').replace(')', '')
            if len(sel) == 1 and p['ref'] != 'U1' and d['net']:
                svg.append(f'<text x="{mx(d["x"]):.1f}" y="{my(d["y"]) + d["h"] * scale / 2 + 8:.1f}" font-size="6" text-anchor="middle" fill="#444">{net[:30]}</text>')
        svg.append(f'<text x="{M}" y="{46 + 11 * sel.index(p):.0f}" font-size="9" fill="#003">Part {p["ref"]}: {p["value"]} ({p["fp"]}) at X={p["x"]:.2f} Y={p["y"]:.2f} rot {p["rot"]:.0f}</text>')
    for i, n in enumerate(notes):
        svg.append(f'<text x="{M}" y="{H - 8 - 11 * (len(notes) - 1 - i):.0f}" font-size="8">{n}</text>')
    svg.append('</svg>')
    return '\n'.join(svg), W, H

def to_pdf_page(doc, svg, W, H, rotate_to_fit=False):
    tmp = fitz.open('svg', svg.encode())
    pdf = fitz.open('pdf', tmp.convert_to_pdf())
    doc.insert_pdf(pdf)

doc = fitz.open()
for side in ('top', 'bottom'):
    s, W, H = page(side)
    to_pdf_page(doc, s, W, H)
led_ref = 'U2'
for title, refs, sc, notes in (
    ('Detail A - WS2812B-type LED XL-1010RGBC (U2..U25), top', ['U2'], 60,
     ['Pad 1 = DOUT, pad 2 = VDD (5 V), pad 3 = GND, pad 4 = DIN. Pin 1 corner is marked by the black dot on the overview.',
      'All 24 LEDs sit on the TOP side at 0/180 degrees; chain order U2 -> U25 (DOUT -> next DIN).']),
    ('Detail B - bypass capacitor behind each LED (C1 behind U2), bottom', ['C1'], 60,
     ['C1..C24: 100 nF 0402, non-polarized, one per LED, on the BOTTOM side exactly behind the LED (rotated 45/-135 degrees).']),
    ('Detail C - battery connector J1 (JST B2B-PH-SM4-TB), top', ['J1'], 14,
     ['Pad 1 (left, silkscreen +) = BAT+ ; pad 2 = BAT-. Mechanical tabs S1/S2 are soldered but carry no net.']),
    ('Detail D - XIAO nRF52840 U1, R1 100R and C25 10uF, bottom', ['U1', 'R1', 'C25'], 7,
     ['U1: castellated SMD module (Seeed SKU 102010448) placed on the BOTTOM; USB-C connector faces the bottom board edge.',
      'R1 (100 ohm 0402) and C25 (10 uF 0805) are non-polarized.']),
    ('Detail E - battery boost U26 (MT3608B), L1, D1, D2, Q1, top', ['U26', 'L1', 'D1', 'D2', 'Q1'], 14,
     ['U26 SOT-23-6: pad 1 = SW is on the side with three pads 1-2-3 (pad numbers are drawn). Pins: 1 SW, 2 GND, 3 FB, 4 EN, 5 VIN, 6 NC.',
      'D1 and D2: cathode (bar on the part) at pad 1. Q1 SOT-23: 1 gate, 2 source, 3 drain. L1 non-polarized.',
      'C26-C29 (10 uF 0805) and R2-R5 (0402) are non-polarized; C25..C29 are all the 10 uF part.']),
):
    s, W, H = detail_page(title, refs, sc, notes)
    to_pdf_page(doc, s, W, H)
doc.save(OUT / 'assembly-drawing.pdf')

# ---------------------------------------------------------------- zips
# 1) PCB upload zip, flat: gerbers + drill + placement (XY) + drawing PDF
zpath = OUT / 'dna-accesories_gerber.zip'
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(gdir.iterdir()):
        z.write(f, f.name)
    for name in ('centroid.pos', 'centroid.csv', 'assembly-drawing.pdf'):
        z.write(OUT / name, name)
# 2) everything in one archive for hand-over / backup
fpath = OUT / 'dna-accesories_fusion_order.zip'
with zipfile.ZipFile(fpath, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(zpath, 'PCB_upload/dna-accesories_gerber.zip')
    for f in sorted(gdir.iterdir()):
        z.write(f, 'gerber/' + f.name)
    for name in ('BOM.xlsx', 'BOM_detail.xlsx', 'centroid.pos', 'centroid.csv', 'assembly-drawing.pdf', 'README.md', 'quote-request-note.md'):
        z.write(OUT / name, name)
print('lines', [(l['refs'][0] + '..', l['qty'], l['mpn']) for l in lines])
for zp in (zpath, fpath):
    print(zp.name, zp.stat().st_size, [i.filename for i in zipfile.ZipFile(zp).infolist()])
