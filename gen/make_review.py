"""Build review.html (revision 6 board review: battery power path added) from the measured data.

Inputs (run these first):
  "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" gen/review_checks.py gen/_runs/review_checks.json
  "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" gen/compare_stats.py gen/_runs/compare_stats.json
  python gen/check_interference.py            # design/interference-check.json
  kicad-cli pcb drc ... -o design/wiring-drc.json ; kicad-cli sch erc ... -o design/wiring-erc.json
  gen/_runs/strict_summary.json               # DRC run with strict custom rules (see the measurement section)
  gen/_runs/compare_cache/new_{top,bottom}.png (from gen/make_comparison.py)
Writes review.html.  Earlier reviews: design/review-rev3-rev4.html and design/review-rev5.html.
"""
import base64, io, json, re
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
rc = json.loads((ROOT / 'gen' / '_runs' / 'review_checks.json').read_text(encoding='utf-8'))
strict = json.loads((ROOT / 'gen' / '_runs' / 'strict_summary.json').read_text(encoding='utf-8'))
stats = json.loads((ROOT / 'gen' / '_runs' / 'compare_stats.json').read_text(encoding='utf-8'))['new']
drc = json.loads((ROOT / 'design' / 'wiring-drc.json').read_text(encoding='utf-8'))
erc = json.loads((ROOT / 'design' / 'wiring-erc.json').read_text(encoding='utf-8'))
itf = json.loads((ROOT / 'design' / 'interference-check.json').read_text(encoding='utf-8'))
job = json.loads((ROOT / 'fusion' / 'gerber' / 'dna-accesories-job.gbrjob').read_text(encoding='utf-8'))['GeneralSpecs']['Size']
drill_hits = len(re.findall(r'^X-?[\d.]+Y-?[\d.]+', (ROOT / 'fusion' / 'gerber' / 'dna-accesories.drl').read_text(), flags=re.M))
erc_n = sum(len(s['violations']) for s in erc['sheets'])
assert len(drc['violations']) == 0 and len(drc['unconnected_items']) == 0 and len(drc['schematic_parity']) == 0
P1, P2 = list(rc['power'].values())
B1, U1c, B2 = P1['battery'], P1['usb'], P2['battery']
BP, BR = rc['battery_path'], rc['branch_currents']
VLO, VHI = rc['boost_vout_range']
def webp(path, width):
    im = Image.open(path).convert('RGBA')
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'WEBP', quality=84, method=6)
    return 'data:image/webp;base64,' + base64.b64encode(b.getvalue()).decode()
cache = ROOT / 'gen' / '_runs' / 'compare_cache'
img_top, img_bot = webp(cache / 'new_top.png', 360), webp(cache / 'new_bottom.png', 360)

def bars():
    d = B1['per_led_drop_mV']
    w, h, pad = 560, 150, 28
    s = [f'<svg viewBox="0 0 {w} {h + 34}" role="img" aria-label="LED ごとの電源損失">']
    for i, (u, v) in enumerate(d.items()):
        bw = (w - pad) / len(d); x = pad + i * bw; bh = v / 120 * h
        s.append(f'<rect x="{x + 2:.1f}" y="{h - bh:.1f}" width="{bw - 4:.1f}" height="{bh:.1f}" fill="#1f5a49"/>'
                 f'<text x="{x + bw / 2:.1f}" y="{h + 12}" font-size="8.5" text-anchor="middle" fill="#59695d">{u[1:]}</text>'
                 f'<text x="{x + bw / 2:.1f}" y="{h - bh - 3:.1f}" font-size="8" text-anchor="middle" fill="#173e34">{v:.0f}</text>')
    s.append(f'<line x1="{pad}" y1="{h}" x2="{w}" y2="{h}" stroke="#173e34"/><text x="0" y="10" font-size="9" fill="#59695d">mV</text>'
             f'<text x="{pad}" y="{h + 28}" font-size="9" fill="#59695d">U2〜U25（電池動作・全白）。昇圧の出力から LED までの電源と GND の往復の損失</text></svg>')
    return ''.join(s)

walk = ''.join(f'<li><span class="ok">✔</span> {x["check"]}</li>' for x in rc['netlist_walk'] if x['ok'])
bad_walk = [x['check'] for x in rc['netlist_walk'] if not x['ok']]
assert not bad_walk, bad_walk

def row(*cells, cls=''):
    return f'<tr class="{cls}">' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>'

meas = ''.join([
    row('銅箔どうしの最小間隔（別ネット）', f'{strict["clearance"]["min"]:.3f} mm', '0.102 mm（4 mil）', '約1.4倍', '<span class="b ok">余裕あり</span>'),
    row('最小線幅（信号／電源・GND／昇圧の大電流）', '0.15 ／ 0.20 ／ 0.40 mm', '0.102 mm（4 mil）', '約1.5倍以上', '<span class="b ok">余裕あり</span>'),
    row('銅箔〜基板外形（穴を含む）', f'{strict["edge_clearance"]["min"]:.3f} mm', '0.3 mm 以上（このプロジェクトの規則は 0.5 mm）', '約1.9倍', '<span class="b ok">余裕あり</span>'),
    row('LED パッドの間（ソルダーマスクのダム）', '0.39 mm', '0.32 mm 以上（緑・通常）／0.35 mm 以上（他色）', '1.1〜1.2倍', '<span class="b ok">足りる</span>'),
    row('ビア（パッド／穴／環）', f'0.56 ／ 0.30 ／ {strict["annular_width"]["min"]:.2f} mm', '最小穴 0.2 mm。環・パッド径の規定は公開ページで確認できず', '—', '<span class="b warn">要確認</span>'),
    row('ビア穴の縁どうし／穴〜銅箔', f'{strict["hole_to_hole"]["min"]:.2f} ／ {strict["hole_clearance"]["min"]:.3f} mm', '規定は公開ページで確認できず（このプロジェクトの規則は 0.25 mm）', '—', '<span class="b warn">要確認</span>'),
    row('シルク（線幅／文字高さ）', '0.12〜0.15 ／ 0.8 mm', '線幅 0.10 mm（4 mil）以上、文字高さ 0.58 mm（23 mil）以上', '約1.2〜1.4倍', '<span class="b ok">足りる</span>'),
    row('外形内の穴・抜き（吊り穴φ2.0 mm、襟上のスリット）', '最小幅 2.0 mm', '非メッキのスロット 0.8 mm 以上', '2.5倍', '<span class="b ok">余裕あり</span>'),
    row('基板サイズ', f'{stats["w"]:.1f} × {stats["h"]:.1f} mm', '10 × 10 〜 500 × 500 mm', '—', '<span class="b ok">範囲内</span>'),
])
web = min(v['min_web_mm'] for v in rc['chain_hole_webs'].values())
a_z = rc['antenna_zone']['track_length_mm']
bat_gnd = BR['GND, boost input return to the battery, 3.0 V cell']

CSS = '''
:root{--paper:#f4f1e7;--ink:#173e34;--muted:#59695d;--line:#b7c1ad;--rust:#983c2c;--green:#1f5a49;--white:#fcfaf3;--soft:#e8eddc;--amber:#87601c;--softred:#f0dfd2;--softamb:#f3e8c8}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.85 "Yu Gothic",Meiryo,sans-serif}
main{max-width:1080px;margin:0 auto;padding:34px 28px 80px}a{color:inherit;text-underline-offset:4px}
.mast{display:flex;justify-content:space-between;border-top:3px solid var(--ink);padding-top:10px;font:11px/1.4 monospace;letter-spacing:.08em;color:var(--muted)}
.nav{display:flex;gap:18px;flex-wrap:wrap;margin:14px 0 0;font-size:13px}.nav a{border-bottom:1px solid var(--line);text-decoration:none}
h1{font:700 clamp(30px,5vw,48px)/1.3 "Yu Mincho","Hiragino Mincho ProN",serif;margin:26px 0 8px}h1 em{font-style:normal;color:var(--rust)}
h2{font:700 24px/1.4 "Yu Mincho",serif;margin:0 0 6px}h3{font-size:16px;margin:26px 0 4px}.lab{font:11px monospace;letter-spacing:.14em;color:var(--muted)}
section{padding:44px 0 6px;border-top:1px solid var(--line);margin-top:38px}p{margin:.6em 0;max-width:46em}.lead{font-size:17px}
.verdict{border-left:5px solid var(--rust);background:var(--softred);padding:14px 18px;margin:20px 0;max-width:54em}.verdict b{color:var(--rust)}
.hero{display:grid;grid-template-columns:1fr 330px;gap:34px;align-items:start}.hero figure{display:flex;gap:14px;justify-content:center;background:var(--white);border:1px solid var(--line);border-radius:6px;padding:12px}.hero figure img{width:46%;height:auto}
.kpi{display:grid;grid-template-columns:repeat(4,1fr);margin:24px 0 0;border-top:1px solid var(--ink);border-bottom:1px solid var(--ink)}
.kpi div{padding:14px;border-left:1px solid var(--line)}.kpi div:first-child{border-left:0}.kpi b{display:block;font:700 26px/1.2 Georgia,serif;color:var(--green)}.kpi span{display:block;font-size:12.5px;color:var(--muted);line-height:1.5;margin-top:4px}
.tw{overflow-x:auto;margin-top:16px}table{border-collapse:collapse;width:100%;min-width:720px;background:var(--white);font-size:14px}
th,td{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}thead th{background:var(--ink);color:#fff;font-weight:600}tbody tr:nth-child(even){background:var(--soft)}
.b{display:inline-block;padding:1px 9px;border-radius:99px;font-size:12px;font-weight:700;white-space:nowrap}.ok{color:var(--green)}.b.ok{background:#d7e6d3}.b.warn{background:var(--softamb);color:var(--amber)}.b.bad{background:var(--softred);color:var(--rust)}.b.ref{background:#e4e4dc;color:var(--muted)}
.find{background:var(--white);border:1px solid var(--line);border-left:5px solid var(--line);border-radius:4px;padding:6px 20px 14px;margin:18px 0}.find.bad{border-left-color:var(--rust)}.find.warn{border-left-color:var(--amber)}.find.ref{border-left-color:#9aa597}
.find h3{margin:10px 0 2px}.find .id{font:11px monospace;letter-spacing:.1em;color:var(--muted)}.find p{max-width:none}.src{font-size:12.5px;color:var(--muted)}
ul{max-width:52em;padding-left:1.3em}li{margin:.35em 0}ul.walk{list-style:none;padding-left:0;columns:2;column-gap:30px}ul.walk li{break-inside:avoid;margin:.2em 0}
code{background:#e7e3d3;padding:1px 6px;border-radius:3px;font-size:.9em}.chart{background:var(--white);border:1px solid var(--line);border-radius:6px;padding:12px;max-width:620px}.chart svg{width:100%;height:auto}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:22px}footer{margin-top:56px;border-top:3px solid var(--ink);padding-top:12px;font-size:12px;color:var(--muted)}
@media(max-width:860px){main{padding:20px 16px 60px}.hero{grid-template-columns:1fr}.kpi{grid-template-columns:1fr 1fr}.grid2,ul.walk{grid-template-columns:1fr;columns:1}}
@media print{body{background:#fff;font-size:11px}main{max-width:none;padding:0}.nav{display:none}section{break-inside:avoid}}
'''

html = f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="DNA LED 基板 改訂6（24.0 × 82.1 mm、電池でも LED が光る昇圧回路を追加）のレビュー。配線・ネット連鎖・電源・製造余裕・3D干渉を実測し、未確認の点を整理。">
<title>DNA基板｜改訂6 レビュー</title><style>{CSS}</style></head><body><main>
<div class="mast"><span>DNA / PCB — ENGINEERING REVIEW · REV. 6</span><span>2026.11.06 · KiCad 9.0.4</span></div>
<nav class="nav" aria-label="目次"><a href="#verdict">判定</a><a href="#findings">指摘</a><a href="#carry">前回の指摘の結果</a><a href="#measure">実測</a><a href="#power">電源</a><a href="#files">製造データ</a><a href="#notdone">確認していないこと</a></nav>

<header class="hero"><div>
<h1>電池でも<em>光る</em>設計に。<br>配線と製造データは<em>整合</em>。</h1>
<p class="lead">改訂6（{stats["w"]:.1f} × {stats["h"]:.1f} mm、65 部品）は、前回（改訂5）の未解決点だった「電池だけでは LED が点灯しない」を、昇圧（MT3608B）と USB／電池の自動切り替えで解決した基板です。
KiCad の DRC・ERC に加えて、銅箔の間隔、電源の電圧降下、ネットの連鎖、部品の位置、3D 干渉、製造データを別の方法でも確かめました。</p>
<div class="verdict" id="verdict"><b>判定：回路の接続・形状・製造データに誤りは見つかりませんでした。</b>
電池 → 昇圧（5.0 V）→ LED の経路と、USB があるときは USB を優先する切り替えは、回路・基板・配線で確認できました。
<b>ただし、追加した昇圧回路は実機で動かしていません。</b>確認をおすすめするのは、昇圧部品の調達（型番と在庫）、電池の仕様と電流、昇圧の GND の戻り経路（0.2 mm 幅）、吊り穴まわりの肉厚、ビアの環です。実機の製造・点灯・Fusion の受入れ確認は、まだ行っていません。</div></div>
<figure><img src="{img_top}" alt="改訂6の表面"><img src="{img_bot}" alt="改訂6の裏面"></figure></header>
<div class="kpi">
<div><b>0 / 0 / 0</b><span>DRC：違反・未接続・回路図との差異<br>ERC は警告 {erc_n} 件（下記）</span></div>
<div><b>{strict["clearance"]["min"]:.2f} mm</b><span>銅箔どうしの最小間隔の実測<br>Fusion の下限 0.10 mm</span></div>
<div><b>{B1["vdd_loss_worst_mV"]:.0f} mV</b><span>全白（368 mA）時の最遠 LED の電源損失<br>昇圧出力からの往復</span></div>
<div><b>{VLO:.1f}〜{VHI:.1f} V</b><span>昇圧の出力電圧の範囲（公称 5.0 V）<br>LED の動作 2.5〜5.5 V</span></div></div>

<section><span class="lab">01 / WILL IT LIGHT?</span><h2>「ちゃんと動くか」の判定</h2>
<div class="tw"><table><thead><tr><th>条件</th><th>判定</th><th>根拠と限界</th></tr></thead><tbody>
{row('USB で給電して LED を点灯', '<span class="b ok">設計上は成立</span>', f'USB の 5 V → D2（ショットキー）→ POWER。Q1 が昇圧を止めるので電池は減らない。ダイオードの順電圧（約 0.4 V と見積り）を引いて LED は約 4.5 V。配線の損失は最遠 LED で {U1c["vdd_loss_worst_mV"]:.0f} mV。実機は未確認。')}
{row('電池だけで LED を点灯', '<span class="b ok">設計上は成立</span>', f'電池（VBAT）→ L1 → MT3608B → D1 → POWER（5.0 V）。出力電圧は帰還抵抗 110 kΩ／15 kΩ で決まり、部品の公差を入れて {VLO:.2f}〜{VHI:.2f} V。<b>実機での起動・出力は未確認。</b>')}
{row('USB を抜く・挿す瞬間', '<span class="b warn">要確認</span>', 'USB を抜くと Q1 が切れて昇圧が起動する。起動までの間は、昇圧の IC を通らず電池からインダクタとダイオード経由で LED に約 3.4 V が届く。LED が一瞬暗くなる、または再起動する可能性がある。USB を挿すと Q1 が EN を落とし、USB 経由に切り替わる。')}
{row('電池をつないだまま USB で給電（充電）', '<span class="b ok">設計上は成立</span>', 'J1 → VBAT → XIAO の BAT+（ネット一致を確認）。充電は XIAO の機能で、昇圧とは別の経路。電池の極性・仕様は未確認。')}
{row('XIAO D6 → 24 個の LED を順に制御', '<span class="b ok">配線は成立</span>', 'D6 → R1（100 Ω）→ U2.DIN → … → U25 の 23 段をネットで確認。ファームウェアは未コンパイル・未書き込み（USB 給電のときだけ動く処理は削除済み）。')}
{row('3.3 V の信号を LED が読めるか', '<span class="b warn">条件付き</span>', 'LED 資料 p.5：VDD=5 V での入力 High は 2.8 V 以上、Low は 1.6 V 以下。XIAO の 3.3 V は上回る。昇圧の出力が 4.8 V 台でも条件は近い。実波形は未測定。')}
{row('Bluetooth（BLE）', '<span class="b warn">未確認</span>', 'XIAO の周囲の銅箔・昇圧のスイッチングとアンテナの位置関係は要確認（R6-06）。コンソールは USB シリアルを使うので、LED 点灯には影響しない。')}
{row('Seeed Fusion での製造・組立', '<span class="b warn">見込みは良好</span>', '実測の余裕は公開仕様を満たす。ビアの環だけ規定を確認できなかった（R5-03）。昇圧部品の調達は未確認（R6-01）。Fusion の DFM 確認は未実施。')}
</tbody></table></div></section>

<section id="findings"><span class="lab">02 / FINDINGS</span><h2>指摘</h2>
<p>「要判断」は設計仕様の決めが必要なもの、「要確認」は実部品・製造先・実機で確かめるもの、「参考」は知っておけばよいものです。今回は要判断がなくなり、昇圧回路に関する要確認が新しく加わりました。</p>

<div class="find warn"><span class="id">R6-01 ／ 要確認 ／ 改訂6で追加</span><h3>昇圧回路は実機で動かしていない。部品の調達も未確認</h3>
<p>追加した 13 部品（MT3608B、10 µH インダクタ、ショットキー 2 個、MOSFET、10 µF ×4、抵抗 ×4）は、データシートの標準回路（Fig.1：5 V 出力、110 kΩ／15 kΩ）に沿って選び、定格の余裕を計算しました。
入力電流の最大（全白・3.0 V の電池）は約 0.73 A で、インダクタの実効電流 1.2 A、飽和電流 1.3 A、ダイオード 1 A、MT3608B のスイッチ電流制限 4 A のいずれにも収まります。出力コンデンサは合計 30 µF（公称）で、データシートの推奨 22 µF 以上です。</p>
<p>確認が必要なのは次の点です。①起動・5 V 出力・切り替え・効率・発熱・ノイズは、実機で測るまで分かりません。②MT3608B の LCSC 番号、Bourns SRN4018TA-100M の LCSC 番号、抵抗（110 kΩ、15 kΩ、100 kΩ）の LCSC 番号は確認できていません（BOM のリンクは検索ページ）。Fusion が調達できない場合の代替品は <code>fusion/BOM_detail.xlsx</code> に書きました。③インダクタの代替（Sunlord SWPA4020S100MT）は、パッド寸法を確認してから使ってください。</p>
<p class="src">根拠：MT3608B データシート Rev1.1（Aerosemi、取得日 2026-11-06）、Bourns SRN4018TA-100M の仕様（販売店の掲載値）、ネットリスト。部品の入手性は検索結果の範囲です。</p></div>

<div class="find warn"><span class="id">R6-02 ／ 要確認 ／ 前回の指摘 07（電池の仕様）に対応</span><h3>電池の仕様と、電池から流れる電流</h3>
<p>全白（LED 24 個で 0.37 A、5 V）のとき、電池から流れる電流は 3.7 V で約 {BP["3.7 V cell"]["I_in_A"]:.2f} A、3.0 V で約 {BP["3.0 V cell"]["I_in_A"]:.2f} A です（昇圧の効率 85 % の仮定）。ファームウェアの明るさ上限（128/255）では約半分です。
容量 500 mAh の電池なら、全白で約 0.9 時間、上限どおりで約 1.7 時間の見積りです（概算で、実測ではありません）。容量が小さい電池（150 mAh 以下）は、全白で 4C 前後になるので避けてください。</p>
<p>電池は<b>保護回路付きの 1 セル（3.7 V）</b>を使ってください。MT3608B は入力 2.4 V 付近で止まりますが、電池の過放電を防ぐ回路は基板にありません。J1 の 1 番ピン（基板の「+」側）が電池の＋です。JST PH の電池ケーブルは売り場によって赤黒の並びが逆の場合があるので、実物の極性を確かめずにつなぐと、XIAO や電池を壊すことがあります。</p></div>

<div class="find warn"><span class="id">R6-03 ／ 要確認 ／ 改訂6で追加</span><h3>昇圧の GND の戻り経路が 0.2 mm 幅で、許容電流に近い</h3>
<p>基板には GND の面（ベタ）がなく、GND は 0.2 mm 幅の配線です。昇圧の入力電流が電池へ戻る経路は、全白・3.0 V の電池で最大 {bat_gnd["I_max_A"]:.2f} A が、幅 {bat_gnd["width_mm"]:.1f} mm の銅箔を通ります。同じ幅の外層の許容電流は、温度上昇 10 K で約 {rc["ampacity_A_10K"]:.2f} A（IPC-2221）で、ほぼ同じ値です。
ファームウェアの明るさ上限（128/255）では約 0.36 A、3.7 V の電池の全白でも約 0.58 A なので、実用上は余裕がありますが、全白を長く続けるとこの経路が温まります。</p>
<p>昇圧の大電流の線（VBAT、SW）は 0.4 mm 幅で引きました（VBAT の最大電流 {BR["VBAT, battery to inductor, 3.0 V cell"]["I_max_A"]:.2f} A）。スイッチ端子（SW）の配線は {rc["trunk_widths"]["SW"]["length_mm"]:.1f} mm と短くまとまっています。
改善案：GND を 0.4 mm 以上にする、または襟の部分に GND の銅箔（ベタ）を追加する。データシートも「強い GND 面」を勧めています。</p></div>

<div class="find ref"><span class="id">R6-04 ／ 参考 ／ 前提の確認</span><h3>電池のマイナス（BAT−）を GND に直結した</h3>
<p>昇圧の入力電流を XIAO の内部経由で戻さないため、J1 の 2 番ピンと XIAO の BAT−パッドを、基板上で GND につなぎました。Seeed の XIAO nRF52840 回路図（v1.1）では、電池は VBAT と GND だけで、BAT− は GND そのものです。この前提は回路図で確認しましたが、実物のモジュールでの導通は測っていません。
ERC は、電池の＋と電源フラグ、BAT− と GND の端子の型の組み合わせについて警告を出します（意図した接続です）。</p></div>

<div class="find warn"><span class="id">R5-02 ／ 要確認 ／ 改訂5で生じた点</span><h3>吊り穴まわりの肉厚が 1.0 mm</h3>
<p>吊り穴は φ2.0 mm の穴 2 つで、耳（幅 4 mm、先端 y=150.5 mm）の穴の縁から外形までが <b>{web:.2f} mm</b> です（FR4 厚 1.6 mm）。改訂4の穴（φ3.0 mm）は先端の周りが約 2.1 mm ありました。</p>
<p><b>概算：</b>ペンダントを約 10 g、動いたときの衝撃を 10 倍（1 N）とし、耳の先端がちぎれる面（穴の縁から外形まで 1.0 mm、2 面、厚 1.6 mm の合計 3.2 mm²）に FR4 のせん断強度を 40 MPa（一般的な値の仮定）とすると、耐えられる力は約 130 N で、安全率は約 100 です。静的な強度は足りる見積りですが、
金属のチェーンや指輪で縁がこすれて削れる、落とした衝撃で耳が欠ける、といった使い方の面では余裕が小さい部分です。気になる場合は、耳を 6 mm 幅にして穴の縁から 1.5 mm 以上取る方法があります。</p>
<p class="src">根拠：外形データ（<code>design/dna-geometry.json</code>）からの実測。強度は概算で、実物の試験はありません。穴の円は外形層の 128 角形で出力されます（Fusion の DFM で問題にならないか、発注時に確認してください）。</p></div>

<div class="find warn"><span class="id">R5-03 ／ 要確認 ／ 製造</span><h3>ビアの環が 0.13 mm</h3>
<p>ビアはパッド 0.56 mm・穴 0.30 mm で、環（穴の縁からパッドの縁まで）は <b>0.13 mm</b>、{drill_hits} 個すべて同じです。Seeed Fusion の公開ページ（製造仕様の wiki・製品ページ）では、最小穴径 0.2 mm は読み取れましたが、環やビアのパッド径の規定は見つかりませんでした。
古い資料に 0.15 mm 以上という記載があるという情報もありますが、現行の値とは確認できていません。</p>
<p><b>対応：</b>発注時に Fusion の DFM 確認を受けてください。0.15 mm が必要と言われた場合は、ビアのパッドを 0.60 mm にして配線をやり直します（ルーターの設定 <code>VIAD</code> と <code>gen/route_apply.py</code> のビア径を変えて再配線します。ただし、間隔の余裕は減ります）。</p></div>

<div class="find ref"><span class="id">R6-06 ／ 参考（前回の R5-05 を更新）</span><h3>XIAO のアンテナ側に配線の銅箔と昇圧回路がある</h3>
<p>XIAO の上端（らせんに向く側、モジュールの端は y=124 mm）を含む帯（x 90〜110、y 121〜129 mm）に、{a_z["F"] + a_z["B"]:.0f} mm 分の配線があります。さらに、昇圧回路は襟の表面（y 127〜141 mm）にあり、1.2 MHz で動くスイッチ部（インダクタとダイオード）はアンテナ側の端（y=124 mm）から約 4〜11 mm の位置です（L1 の端が 4 mm、D1 が 8 mm）。
アンテナの位置と銅箔の禁止範囲は Seeed の資料で確認していません。BLE を使うときは、昇圧が動いている状態で通信距離を実測してください。</p></div>

<div class="find ref"><span class="id">R6-07 ／ 参考</span><h3>シルク・LED 間隔・USB の電流</h3>
<ul><li>襟のシルクは、昇圧部品の場所をあけるため、START/STOP と凡例 3 行（A=T 2 BONDS…、2 TURNS…、WATSON CRICK…）を削除し、REV の表記を「REV 6」にしました。「+」「−」は J1 のそばに移しました。</li>
<li>LED の枠線 8 本の端が、外形に 0.08〜0.2 mm まで近づいています（DRC は警告扱い）。製造の外形の公差（±0.2 mm）で、端がわずかに欠ける可能性があります。</li>
<li>LED 間隔が 5.5 mm なので、隣の LED の光が混ざりやすくなります。らせん内の窓は消えて、襟の上のスリットだけです。</li>
<li>USB で給電するときは、LED 全白の 0.37 A に XIAO と電池の充電（最大 100 mA）が加わり、約 0.48 A で USB の 0.5 A に近づきます。ファームウェアの明るさ上限（128/255）では約 0.19 A です。</li></ul></div>

<div class="find ref"><span class="id">R6-08 ／ 参考 ／ 資料の食い違い（今回修正）</span><h3>文書の更新</h3>
<ul><li>旧 <code>review.html</code>（改訂5）は <code>design/review-rev5.html</code> に、さらに前のレビューは <code>design/review-rev3-rev4.html</code> にあります。</li>
<li><code>lp/</code>（試作ページ）、<code>console/README.md</code>、2 つのファームウェアの冒頭、<code>fusion/README.md</code>、<code>design/README.md</code> を、電池でも光る構成に合わせて更新しました。</li></ul></div>
</section>

<section id="carry"><span class="lab">03 / CARRY-OVER</span><h2>前回（改訂3）の指摘 01〜09 の結果</h2>
<div class="tw"><table><thead><tr><th>前回の指摘</th><th>現在</th><th>根拠</th></tr></thead><tbody>
{row('01 LED の VDD と DOUT が逆', '<span class="b ok">解決</span>', 'パッド 1=DOUT（左上）、2=VDD（右上）、3=GND（左下）、4=DIN（右下）。LED 資料 p.10 の上面図と一致。パッドの機能（ネット）は全 24 個で確認。座標は U2・U3 で確認（全 LED が同じフットプリントで、向きは 0°/180° のみ）。')}
{row('02 電源・GND・24 段の信号を配線', '<span class="b ok">解決</span>', 'DRC 未接続 0。ネットの連鎖を基板上で確認（下の一覧）。')}
{row('03 電池単独の LED 給電', '<span class="b ok">解決（設計・実装）</span>', '昇圧（MT3608B）と USB／電池の自動切り替えを追加。<b>実機は未確認</b>（R6-01）。')}
{row('04 LED 近傍のコンデンサ', '<span class="b ok">解決</span>', f'C1〜C24（100 nF）が各 LED の真裏、C25（10 µF）が入口。LED のパッド〜コンデンサ間の銅箔の長さは平均 {rc["decoupling"]["mean_power_path_mm"]:.1f} mm、最大 {rc["decoupling"]["max_power_path_mm"]:.1f} mm（GND 側 最大 {rc["decoupling"]["max_gnd_path_mm"]:.1f} mm）。')}
{row('05 3.3 V の信号', '<span class="b warn">条件付き</span>', '100 Ω の直列抵抗 R1 を実装。しきい値は満たす見込み。実波形は未測定。')}
{row('06 ファームウェア', '<span class="b warn">コードあり・未検証</span>', 'D6・24 個・GRB・明るさ上限 128。電池でも動くよう、USB 給電のときだけ動く処理を削除。未コンパイル・未書き込み。')}
{row('07 XIAO 裏面実装と電池', '<span class="b warn">一部</span>', 'U1 は裏面の底面パッドで実装する前提。電池の仕様と極性は → R6-02。')}
{row('08 ERC と製造ルール', '<span class="b warn">一部</span>', f'ERC は警告 {erc_n} 件（ラベル 1、端子の型の組み合わせ 2）。DRC の規則は最小間隔・最小線幅が 0 のままだが、実測と Fusion 公開仕様を比較して余裕を確認した（下の表）。')}
{row('09 USB-C プラグの干渉', '<span class="b ok">解決</span>', f'USB-C の差込口は y={itf["usb_plug"]["mouth_board_y"]:.2f} mm で基板端（146.0）より外。プラグ外形（規格上限 12.35 × 6.5 mm）と基板の重なり {itf["usb_plug"]["overlap_with_board_mm3"]:.1f} mm³。耳の内側の間隔 16 mm、片側の余裕 {rc["plug_clearance_each_side_mm"]:.2f} mm。')}
</tbody></table></div></section>

<section id="measure"><span class="lab">04 / MEASUREMENTS</span><h2>製造に対する余裕の実測</h2>
<p>DRC の規則が 0 のままだと「違反 0」は余裕を表しません。そこで、一時的に厳しい規則（間隔 1.0 mm 以上など）を KiCad に与え、違反の「実測値」の最小を集めました。Fusion の値は 2026-11-06 に公式ページ（製造仕様の wiki、製品ページ）で読んだものです。</p>
<div class="tw"><table><thead><tr><th>項目</th><th>この基板の実測</th><th>Fusion の公開仕様</th><th>余裕</th><th>判定</th></tr></thead><tbody>{meas}</tbody></table></div>
<p class="src">ビアは表裏とも被覆（テンティング）の設定です。外形の穴は 128 角形の外形線で出力されます。製造先の最終確認は、発注時の Fusion の DFM 確認によります。</p></section>

<section id="power"><span class="lab">05 / POWER</span><h2>電源</h2>
<h3>LED までの電圧降下（基板の銅箔から計算）</h3>
<p>基板の実際のトラックとビアから抵抗網を作り（銅 35 µm、0.49 mΩ/□、ビア 1.1 mΩ）、電源の出口（電池動作は D1 のカソードと昇圧の GND、USB 動作は D2 のカソードと XIAO の GND）から各 LED のパッドまでの電位差を計算しました。LED は定電流（R・G・B 各 5 mA）なので、全白でも 1 個あたり約 15.35 mA です。</p>
<div class="tw"><table><thead><tr><th>負荷</th><th>動作</th><th>電源側の最大降下</th><th>GND 側の最大上昇</th><th>最も損失の大きい LED（{B1["worst_led"]}）</th></tr></thead><tbody>
{row('全白 15.35 mA／個（368 mA）', '電池', f'{B1["power_drop_max_mV"]:.0f} mV', f'{B1["gnd_rise_max_mV"]:.0f} mV', f'<b>{B1["vdd_loss_worst_mV"]:.0f} mV</b>')}
{row('全白 15.35 mA／個（368 mA）', 'USB', f'{U1c["power_drop_max_mV"]:.0f} mV', f'{U1c["gnd_rise_max_mV"]:.0f} mV', f'<b>{U1c["vdd_loss_worst_mV"]:.0f} mV</b>')}
{row('2 倍の余裕 30 mA／個（720 mA）', '電池', f'{B2["power_drop_max_mV"]:.0f} mV', f'{B2["gnd_rise_max_mV"]:.0f} mV', f'<b>{B2["vdd_loss_worst_mV"]:.0f} mV</b>')}
</tbody></table></div>
<div class="chart">{bars()}</div>
<h3>電池から昇圧までの経路</h3>
<div class="tw"><table><thead><tr><th>電池の電圧</th><th>電池から流れる電流（概算）</th><th>電池 → インダクタ（VBAT）の降下</th><th>昇圧の GND → 電池の降下</th></tr></thead><tbody>
{row('3.7 V', f'{BP["3.7 V cell"]["I_in_A"]:.2f} A', f'{BP["3.7 V cell"]["vbat_path_mV"]:.0f} mV', f'{BP["3.7 V cell"]["gnd_return_mV"]:.0f} mV')}
{row('3.0 V（空に近い）', f'{BP["3.0 V cell"]["I_in_A"]:.2f} A', f'{BP["3.0 V cell"]["vbat_path_mV"]:.0f} mV', f'{BP["3.0 V cell"]["gnd_return_mV"]:.0f} mV')}
</tbody></table></div>
<ul><li>LED の動作電圧は 2.5〜5.5 V（資料 p.5）。昇圧の出力は {VLO:.2f}〜{VHI:.2f} V、配線の損失は 0.1〜0.2 V なので問題ありません（USB 動作では D2 の順電圧で約 4.5 V）。この昇圧は、電池の電圧が下がっても 5 V 近くを保つので、LED の色（A/T/G/C の識別色）が電池の残量で変わりません。</li>
<li>各配線の最大電流：電源の本線 {BR["POWER trunk, all white (battery mode)"]["I_max_A"]:.2f} A（幅 {BR["POWER trunk, all white (battery mode)"]["width_mm"]:.1f} mm）、LED の GND 戻り {BR["GND, LED return, all white"]["I_max_A"]:.2f} A（幅 {BR["GND, LED return, all white"]["width_mm"]:.1f} mm）、電池〜インダクタ {BR["VBAT, battery to inductor, 3.0 V cell"]["I_max_A"]:.2f} A（幅 {BR["VBAT, battery to inductor, 3.0 V cell"]["width_mm"]:.1f} mm）、昇圧の GND 戻り {bat_gnd["I_max_A"]:.2f} A（幅 {bat_gnd["width_mm"]:.1f} mm → R6-03）。0.2 mm 幅の許容電流は約 {rc["ampacity_A_10K"]:.2f} A（10 K 上昇、IPC-2221）。</li>
<li>この計算は直流で、銅箔の温度・接触抵抗・昇圧のスイッチング（1.2 MHz）の影響・XIAO の USB 5 V 経路の降下は含みません。実機の測定が必要です。</li></ul></section>

<section id="files"><span class="lab">06 / NETS & FILES</span><h2>ネット・部品・製造データの整合</h2>
<h3>基板上のネットの確認（KiCad の基板データから）</h3><ul class="walk">{walk}</ul>
<h3>改訂5から変えたこと・変えていないこと</h3>
<ul><li>追加：昇圧と電源切り替えの 13 部品（表面の襟）、電池のマイナスの GND 直結、シルクの整理。</li>
<li>変えていない：らせんの形（24.0 × 82.09 mm）、LED 24 個とコンデンサ 24 個の位置・向き・面、U1・J1・R1・C25 の位置、LED のデータ連鎖（U2 → U25）。</li>
<li>回路図を更新（部品 13 点とネットの追加、<code>U1.VUSB</code> のネット名を POWER から VUSB へ、電池の＋を VBAT へ）。部品の UUID は、既存の 52 個で変更なし。</li></ul>
<h3>製造データ（<code>fusion/</code>）</h3>
<ul><li>ガーバー・ドリル・実装座標を現在の基板から作り直した。外形サイズ {job["X"]:.2f} × {job["Y"]:.2f} mm（ガーバーのジョブ情報）。</li>
<li>ドリルは φ0.30 mm のみで {drill_hits} 箇所＝基板のビアの数と一致。穴あけ（NPTH）はなし。</li>
<li>BOM は 13 行・65 点、実装座標は {rc["centroid"]["rows"]} 行で、基板の座標・面と 0.01 mm 以内で一致（不一致 {len(rc["centroid"]["mismatch"])} 件）。実装図に昇圧部の拡大図（Detail E）を追加。</li>
<li>コンソールの LED 座標（<code>console/board-data.js</code>）は <code>base-pairs.csv</code> と一致。</li></ul>
<h3>3D 干渉</h3>
<ul><li>全 {itf["components"]} 部品の STEP で、部品どうし・部品と基板の衝突は 0 件。</li>
<li>XIAO の USB-C の口は基板端から 0.51 mm 外。USB-C プラグの外形（規格上限）と基板（耳を含む）の重なりは 0。</li></ul></section>

<section id="notdone"><span class="lab">07 / NOT VERIFIED</span><h2>確認していないこと</h2>
<ul><li><b>昇圧回路の動作</b>（起動、5 V の出力、負荷変動、USB の抜き差しでの切り替え、効率、発熱、スイッチングのノイズ）。</li>
<li>実際の基板の製造、はんだ付け、通電、LED の点灯、温度、電池での持続時間、BLE の通信距離、ペンダントとしての重さ・つり合い。</li>
<li>ファームウェアのコンパイル、書き込み、コンソールとの実機接続。</li>
<li>昇圧部品の調達（MT3608B、インダクタ、抵抗の LCSC 番号と在庫）と、インダクタ代替品のパッド寸法。</li>
<li>Seeed Fusion の DFM 確認・見積・受入れ（ビアの環、穴・ビアの間隔、組立の部品間隔、基準マーク、XIAO を裏面に実装する工程は、公開ページで規定を確認できませんでした）。</li>
<li>XIAO の底面パッド・アンテナ・充電の仕様の最新版との照合（Seeed の回路図は v1.1 を使用）。BAT− が GND であることの実物での導通確認。</li>
<li>LED の最大定格・実際の購入ロットの仕様（資料は XINGLIGHT の公開データシート）。</li>
<li>耳の強度は概算で、実物の引っ張りや衝撃の試験はありません。</li></ul></section>

<footer>測定・生成：<code>gen/review_checks.py</code>（抵抗網・ネット・位置）、<code>gen/check_interference.py</code>（3D 干渉）、厳しい規則の DRC（<code>gen/_runs/strict_summary.json</code>）、<code>gen/make_review.py</code>。
旧レビュー：<code>design/review-rev5.html</code>、<code>design/review-rev3-rev4.html</code>　比較資料：<code>design/comparison-rev4-rev5.html</code>　Fusion 公開仕様：seeedstudio.com の製造仕様 wiki と Fusion PCB のページ。　MT3608B：Aerosemi データシート Rev1.1。</footer>
</main></body></html>'''
(ROOT / 'review.html').write_text(html, encoding='utf-8')
print('wrote review.html', round((ROOT / 'review.html').stat().st_size / 1e3), 'kB')
