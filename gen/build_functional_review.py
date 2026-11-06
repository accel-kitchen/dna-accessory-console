"""Build the offline functional review from checked KiCad evidence, without editing hardware."""
from pathlib import Path
import base64
import hashlib
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'design' / 'functional-review'
summary = json.loads((EVIDENCE / 'summary.json').read_text(encoding='utf-8'))
for name, expected in summary['hashes'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, f'Stale evidence: {name}'
drc = json.loads((EVIDENCE / 'drc.json').read_text(encoding='utf-8'))
erc = json.loads((EVIDENCE / 'erc.json').read_text(encoding='utf-8'))
geometry = json.loads((ROOT / 'design' / 'dna-geometry.json').read_text(encoding='utf-8'))
escape = html.escape
intf = json.loads((ROOT / 'design' / 'interference-check.json').read_text(encoding='utf-8'))
u1, j1 = intf['bboxes']['U1'], intf['bboxes']['J1']
rng = lambda v: f'{v[0]:.1f}–{v[1]:.1f}'
assert not intf['component_collisions'] and not intf['board_collisions'] and intf['usb_plug']['overlap_with_board_mm3'] > 0
rows = []
for number, finding in enumerate(drc['unconnected_items'], 1):
    net = re.search(r'\[(.+?)\]', finding['items'][0]['description']).group(1)
    items = ' ↔ '.join(i['description'] for i in finding['items'])
    rows.append(f'<tr><td>{number:02}</td><td><code>{escape(net)}</code></td><td>{escape(items)}</td></tr>')
erc_rows = []
for sheet in erc['sheets']:
    for finding in sheet['violations']:
        items = ' / '.join(i['description'] for i in finding['items'])
        erc_rows.append(f'<tr><td>{escape(finding["severity"])}</td><td><code>{escape(finding["type"])}</code></td><td>{escape(items)}</td></tr>')
pair_rows = []
chain = []
for p in geometry['pairs']:
    a, b = p['a'], p['b']
    pair_rows.append(f'<tr><td>{p["pair"]:02}</td><td>{a["ref"]} → {b["ref"]}</td><td>{a["xy"][0]:.1f}, {a["xy"][1]:.1f}</td><td>{b["xy"][0]:.1f}, {b["xy"][1]:.1f}</td><td>10.0</td></tr>')
    chain.append(f'<div class="chain-pair"><small>PAIR {p["pair"]:02}</small><div>{a["ref"]} <span class="routed" aria-label="設計ネットの対内配線あり">→</span> {b["ref"]}</div></div>')
replacements = {
    '@@BOARD_IMAGE@@': 'data:image/svg+xml;base64,' + base64.b64encode((ROOT / 'design' / 'preview' / 'dna-layout.svg').read_bytes()).decode(),
    '@@DRC_ROWS@@': ''.join(rows),
    '@@ERC_ROWS@@': ''.join(erc_rows),
    '@@PAIR_ROWS@@': ''.join(pair_rows),
    '@@CHAIN@@': ''.join(chain),
    '@@HASH_ROWS@@': ''.join(f'<tr><td>{escape(n)}</td><td><code>{v}</code></td></tr>' for n, v in summary['hashes'].items()),
    '@@USB_MOUTH@@': f"{intf['usb_plug']['mouth_board_y']:.1f}",
    '@@PLUG_OVERLAP@@': f"{intf['usb_plug']['overlap_with_board_mm3']:.0f}",
    '@@PLUG_TOP@@': f"{intf['usb_plug']['overlap_height_mm']:.1f}",
    '@@U1_X@@': rng(u1['x']), '@@U1_Y@@': rng(u1['board_y']), '@@J1_X@@': rng(j1['x']), '@@J1_Y@@': rng(j1['board_y']),
    '@@CHECK_TIME@@': escape(summary['review_date']),
}
report = (ROOT / 'gen' / 'functional_review.html').read_text(encoding='utf-8')
for token, value in replacements.items():
    report = report.replace(token, value)
assert not re.search(r'@@[A-Z_]+@@', report)
assert len(rows) == 62 and len(erc_rows) == 26
(ROOT / 'design' / 'review-rev3-rev4.html').write_text(report, encoding='utf-8')
print(f'Saved design/review-rev3-rev4.html: {len(rows)} unconnected, {len(erc_rows)} ERC findings; source hashes unchanged.')
