"""Margin measurement: run KiCad's DRC with deliberately strict rules and collect the *actual* values it reports.

The normal DRC rules of this project are 0 (minimum clearance / width), so "0 violations" says nothing about margins.  Here a temporary copy of
the board gets a .kicad_dru that asks for far more than any real process (clearance 1 mm, ...); every shortfall is reported with its actual value,
and the smallest actual value per kind is the real margin.  Output: gen/_runs/strict_summary.json (read by gen/make_review.py).

  python gen/strict_drc.py [board.kicad_pcb] [summary.json]
"""
import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
KCLI = r'C:\Program Files\KiCad\9.0\bin\kicad-cli.exe'
RULES = '''(version 1)
(rule "s_clearance" (constraint clearance (min 1.0mm)))
(rule "s_track" (constraint track_width (min 1.0mm)))
(rule "s_edge" (constraint edge_clearance (min 2.0mm)))
(rule "s_annular" (constraint annular_width (min 0.5mm)))
(rule "s_hh" (constraint hole_to_hole (min 1.0mm)))
(rule "s_hc" (constraint hole_clearance (min 1.0mm)))
(rule "s_silk" (constraint silk_clearance (min 1.0mm)))
(rule "s_via" (constraint via_diameter (min 2.0mm)))
'''
tmp = Path(tempfile.mkdtemp(prefix='strict_drc_'))
src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'dna-accesories.kicad_pcb'
shutil.copy(src, tmp / 'dna-accesories.kicad_pcb')
shutil.copy(ROOT / 'dna-accesories.kicad_pro', tmp / 'dna-accesories.kicad_pro')
(tmp / 'dna-accesories.kicad_dru').write_text(RULES, encoding='utf-8')
subprocess.run([KCLI, 'pcb', 'drc', '--format', 'json', '--severity-all', '-o', str(tmp / 'drc.json'), str(tmp / 'dna-accesories.kicad_pcb')], check=True, capture_output=True)
d = json.loads((tmp / 'drc.json').read_text(encoding='utf-8'))
by = {}
for v in d['violations']:
    m = re.search(r'actual ([\d.]+) mm', v['description'])
    by.setdefault(v['type'], []).append((float(m.group(1)) if m else None, v['type'], [(i['description'], i['pos']) for i in v['items']]))
KEYS = {'clearance': ['clearance'], 'track_width': ['track_width'], 'edge_clearance': ['copper_edge_clearance'], 'annular_width': ['annular_width'],
        'hole_to_hole': ['hole_to_hole'], 'hole_clearance': ['hole_clearance'],
        'silk_clearance': ['silk_edge_clearance', 'silk_over_copper', 'silk_overlap'], 'via_diameter': ['via_diameter']}
out = {}
for key, types in KEYS.items():
    vs = sorted((x for t in types for x in by.get(t, []) if x[0] is not None), key=lambda x: x[0])
    out[key] = {'count': sum(len(by.get(t, [])) for t in types), 'min': vs[0][0] if vs else None, 'types': types, 'worst': [[a, b, c] for a, b, c in vs[:3]]}
Path(sys.argv[2] if len(sys.argv) > 2 else ROOT / 'gen' / '_runs' / 'strict_summary.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
shutil.rmtree(tmp, ignore_errors=True)
print({k: (v['count'], v['min']) for k, v in out.items()})
