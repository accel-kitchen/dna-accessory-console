"""Build design/comparison-rev4-rev5.html: the previous board (design/pre-compact-20261102) next to the current one.

Needs Pillow and kicad-cli (KiCad 9).  Steps:
  1. "C:\\Program Files\\KiCad\\9.0\\bin\\python.exe" gen/compare_stats.py gen/_runs/compare_stats.json
  2. python gen/make_comparison.py [--quality high|basic]
The page is one self-contained file (images are embedded as WebP).
"""
import base64, csv, io, json, os, subprocess, sys, tempfile, shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
KCLI = r'C:\Program Files\KiCad\9.0\bin\kicad-cli.exe'
QUALITY = sys.argv[sys.argv.index('--quality') + 1] if '--quality' in sys.argv else 'high'
OLD_DIR = ROOT / 'design' / 'pre-compact-20261102'
stats = json.loads((ROOT / 'gen' / '_runs' / 'compare_stats.json').read_text(encoding='utf-8'))
O, N = stats['old'], stats['new']
GEO = {'old': json.loads((OLD_DIR / 'dna-geometry.json').read_text(encoding='utf-8')),
       'new': json.loads((ROOT / 'design' / 'dna-geometry.json').read_text(encoding='utf-8'))}
PX = 40                                        # px per mm of the working renders

# ------------------------------------------------------------------ renders
work = Path(tempfile.mkdtemp(prefix='dna_cmp_'))
def project_dir(name, pcb):
    d = work / name
    d.mkdir()
    shutil.copy(pcb, d / 'dna-accesories.kicad_pcb')
    shutil.copy(ROOT / 'dna-accesories.kicad_pro', d / 'dna-accesories.kicad_pro')
    subprocess.run(['cmd', '/c', 'mklink', '/J', str(d / 'lib'), str(ROOT / 'lib')], check=True, capture_output=True)
    return d / 'dna-accesories.kicad_pcb'
PCB = {'old': project_dir('old', OLD_DIR / 'dna-accesories.kicad_pcb'),
       'new': project_dir('new', ROOT / 'dna-accesories.kicad_pcb')}

def render(name, side):
    out = work / f'{name}_{side}.png'
    subprocess.run([KCLI, 'pcb', 'render', '--quality', QUALITY, '--background', 'transparent', '--width', '3200', '--height', '4800',
                    '--side', side, '--zoom', '0.6', '-o', str(out), str(PCB[name])], check=True, capture_output=True)
    im = Image.open(out).convert('RGBA')
    # only (nearly) opaque pixels define the board box: the ray-traced render adds faint shadows
    box = im.getchannel('A').point(lambda a: 255 if a > 200 else 0).getbbox()
    x0, y0, x1, y1 = GEO[name]['bounds']
    # the ray-traced render does not keep the x/y pixel ratio, so the cropped board is resized to its real proportions
    return im.crop(box).resize((round((x1 - x0) * PX), round((y1 - y0) * PX)), Image.LANCZOS)

CACHE = ROOT / 'gen' / '_runs' / 'compare_cache'
CACHE.mkdir(parents=True, exist_ok=True)
def cached(name, side):
    f = CACHE / f'{name}_{side}.png'
    if f.exists() and f.stat().st_mtime > max(PCB_SRC[name].stat().st_mtime, Path(__file__).stat().st_mtime if False else 0):
        return Image.open(f).convert('RGBA')
    im = render(name, side)
    im.save(f)
    return im
PCB_SRC = {'old': OLD_DIR / 'dna-accesories.kicad_pcb', 'new': ROOT / 'dna-accesories.kicad_pcb'}
IMG = {(n, s): cached(n, s) for n in ('old', 'new') for s in ('top', 'bottom')}

def webp(im, width=None, q=86):
    if width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, 'WEBP', quality=q, method=6)
    return 'data:image/webp;base64,' + base64.b64encode(b.getvalue()).decode()

def scaled(im, name_w_mm, px_per_mm=17):
    """WebP of a crop at a fixed px/mm so that old and new crops share one scale."""
    return webp(im, round(name_w_mm * px_per_mm))

def crop_mm(name, side, x0, y0, x1, y1):
    bx0, by0 = GEO[name]['bounds'][:2]
    return IMG[(name, side)].crop((round((x0 - bx0) * PX), round((y0 - by0) * PX), round((x1 - bx0) * PX), round((y1 - by0) * PX)))

# ------------------------------------------------------------------ figures
def ring(pts):
    return 'M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in pts) + ' Z'
def leds(csv_path):
    return [(float(r['x_mm']), float(r['y_mm'])) for r in csv.DictReader(csv_path.open(encoding='utf-8-sig', newline=''))]
LED = {'old': leds(OLD_DIR / 'base-pairs.csv'), 'new': leds(ROOT / 'design' / 'base-pairs.csv')}
def outline_path(name):
    g = GEO[name]
    return ring(g['outer']) + ' ' + ' '.join(ring(h) for h in g['holes'])

def overlay_svg():
    x0, y0, x1, y1 = 82, 26, 118, 154
    s = [f'<svg viewBox="{x0} {y0} {x1 - x0} {y1 - y0}" role="img" aria-label="旧基板と新基板の外形の重ね図">']
    s.append(f'<path d="{outline_path("old")}" fill="#d9d4c3" stroke="#8d8672" stroke-width=".25" fill-rule="evenodd"/>')
    s.append(f'<path d="{outline_path("new")}" fill="#1f5a49" fill-opacity=".86" stroke="#0f3a2e" stroke-width=".3" fill-rule="evenodd"/>')
    for x, y in LED['old']:
        s.append(f'<rect x="{x - .6:.2f}" y="{y - .6:.2f}" width="1.2" height="1.2" fill="#8d8672"/>')
    for x, y in LED['new']:
        s.append(f'<rect x="{x - .6:.2f}" y="{y - .6:.2f}" width="1.2" height="1.2" fill="#f2d16b"/>')
    # dimension lines
    ob, nb = GEO['old']['bounds'], GEO['new']['bounds']
    s.append(f'<g stroke="#983c2c" stroke-width=".25" fill="#983c2c" font-size="2.6" font-family="sans-serif">'
             f'<line x1="{ob[0] - 3}" y1="{ob[1]}" x2="{ob[0] - 3}" y2="{ob[3]}"/><text x="{ob[0] - 4.2}" y="{(ob[1] + ob[3]) / 2}" text-anchor="middle" stroke="none" transform="rotate(-90 {ob[0] - 4.2} {(ob[1] + ob[3]) / 2})">旧 {O["h"]:.1f} mm</text>'
             f'<line x1="{nb[2] + 3}" y1="{nb[1]}" x2="{nb[2] + 3}" y2="{nb[3]}" stroke="#1f5a49"/><text x="{nb[2] + 4.4}" y="{(nb[1] + nb[3]) / 2}" text-anchor="middle" stroke="none" fill="#1f5a49" transform="rotate(90 {nb[2] + 4.4} {(nb[1] + nb[3]) / 2})">新 {N["h"]:.1f} mm</text></g>')
    s.append(f'<g font-size="2.4" font-family="sans-serif" fill="#59695d"><text x="{ob[0]}" y="{ob[3] + 4}">旧 幅 {O["w"]:.1f} mm</text>'
             f'<text x="{nb[0]}" y="{nb[3] + 4}" fill="#1f5a49" dy="3">新 幅 {N["w"]:.1f} mm</text></g>')
    s.append(f'<g><line x1="{x0 + 2}" y1="{y1 - 4}" x2="{x0 + 12}" y2="{y1 - 4}" stroke="#173e34" stroke-width=".4"/>'
             f'<text x="{x0 + 2}" y="{y1 - 5.2}" font-size="2.4" font-family="sans-serif" fill="#173e34">10 mm</text></g></svg>')
    return ''.join(s)

def pct(a, b):
    return f'{(b - a) / a * 100:+.0f}%'
helix_top = {k: 117.5 - GEO[k]['bounds'][1] for k in ('old', 'new')}
helix_span = {'old': 12 * 6.5, 'new': 12 * N['pair_pitch']}
helix_w = {'old': 2 * 11.0 + O['rail_width'], 'new': 2 * GEO['new']['amplitude_mm'] + N['rail_width']}
fr4 = lambda a: a * 1.6 * 1.85e-3                    # g: area x 1.6 mm x 1.85 g/cm3 (board only)

rows = [
    ('基板の幅', f'{O["w"]:.1f} mm', f'{N["w"]:.1f} mm', pct(O['w'], N['w']), 'マイコン部の幅を XIAO のパッドに合わせて詰めた'),
    ('基板の長さ', f'{O["h"]:.1f} mm', f'{N["h"]:.1f} mm', pct(O['h'], N['h']), '吊り穴の耳（4.5 mm）を含む'),
    ('外形の面積', f'{O["area"]:,.0f} mm²', f'{N["area"]:,.0f} mm²', pct(O['area'], N['area']), '抜き穴を除いた実面積'),
    ('らせん部の長さ（先端〜襟）', f'{helix_top["old"]:.1f} mm', f'{helix_top["new"]:.1f} mm', pct(helix_top['old'], helix_top['new']), '旧は先端の吊り環を含む'),
    ('らせんの幅', f'{helix_w["old"]:.1f} mm', f'{helix_w["new"]:.1f} mm', pct(helix_w['old'], helix_w['new']), '振幅 ×2 ＋ バックボーン幅'),
    ('塩基対の LED 間隔', f'{O["pair_distance"]:.1f} mm', f'{N["pair_distance"]:.1f} mm', pct(O['pair_distance'], N['pair_distance']), '中心間。向かい合う 2 個'),
    ('塩基対のピッチ', f'{O["pair_pitch"]:.1f} mm', f'{N["pair_pitch"]:.1f} mm', pct(O['pair_pitch'], N['pair_pitch']), '12 対・2 回転は変わらず'),
    ('バックボーン幅 / 梯子の幅', f'{O["rail_width"]:.1f} / {O["rung_width"]:.1f} mm', f'{N["rail_width"]:.1f} / {N["rung_width"]:.1f} mm', '', '梯子 3.0 mm が LED 周りのビアの限界'),
    ('吊り穴', 'φ3.0 mm × 1（らせん先端）', 'φ2.0 mm × 2（USB-C 側の耳）', '', '耳の内側の間隔 16 mm'),
    ('外形内の抜き穴', f'{O["cutouts"]} 個', f'{N["cutouts"]} 個', '', '新はらせん内の窓が消え、襟の上のスリットと吊り穴だけ'),
    ('シルクの塩基文字（T/C/A/G）', f'{O["letters"]} 個', f'{N["letters"]} 個', '', '表裏とも削除。対番号・5′3′・水素結合は残した'),
    ('配線の総延長', f'{O["track_len"]:,.0f} mm', f'{N["track_len"]:,.0f} mm', pct(O['track_len'], N['track_len']), ''),
    ('ビア', f'{O["vias"]} 個', f'{N["vias"]} 個', pct(O['vias'], N['vias']), '密度が上がり、わずかに増えた'),
    ('FR4 基板の重さ（概算）', f'{fr4(O["area"]):.1f} g', f'{fr4(N["area"]):.1f} g', pct(fr4(O['area']), fr4(N['area'])), '面積 × 1.6 mm × 1.85 g/cm³。部品・銅は含まない'),
    ('部品点数', f'{O["footprints"]} 点', f'{N["footprints"]} 点', '', '新は昇圧・切り替えの 13 部品と電源スイッチの 3 部品を追加（BOM は 6 → 15 品番）'),
    ('DRC（KiCad 9.0.4）', '違反 0 / 未接続 0 / 差異 0', '違反 0 / 未接続 0 / 差異 0', '', '回路図は昇圧回路などを追加'),
]
table = ''.join(f'<tr><th scope="row">{a}</th><td>{b}</td><td>{c}</td><td class="d">{d}</td><td class="n">{e}</td></tr>' for a, b, c, d, e in rows)

# ------------------------------------------------------------------ crops
old_hole = crop_mm('old', 'top', 85.5, 29.4, 114.5, 46.0)
new_hole = crop_mm('new', 'top', 88.0, 133.0, 112.0, 150.6)
y_old = LED['old'][0][1]; y_new = LED['new'][0][1]
old_silk = crop_mm('old', 'top', 85.5, y_old - 3.2, 114.5, y_old + 2 * 6.5 + 3.2)
new_silk = crop_mm('new', 'top', 88.0, y_new - 3.2, 112.0, y_new + 2 * 4.0 + 3.2)
lp = ROOT / 'lp' / 'assets' / 'img'
collar_front = Image.open(lp / 'collar-front.png'); collar_back = Image.open(lp / 'collar-back.png')

TOP_W = 360
def board_fig(name, label, side):
    return (f'<figure class="p"><img src="{webp(IMG[(name, side)], round((GEO[name]["bounds"][2] - GEO[name]["bounds"][0]) * 14))}" '
            f'alt="{label}（{"表" if side == "top" else "裏"}面）の3Dレンダリング"><figcaption>{label}</figcaption></figure>')

html = f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DNA基板｜旧基板との比較（改訂4 → 改訂7）</title>
<style>
:root{{--paper:#f4f1e7;--ink:#173e34;--muted:#59695d;--line:#b7c1ad;--rust:#983c2c;--green:#1f5a49;--white:#fcfaf3;--soft:#e8eddc}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.85 "Yu Gothic",Meiryo,sans-serif}}
main{{max-width:1080px;margin:0 auto;padding:34px 28px 80px}}
.mast{{display:flex;justify-content:space-between;border-top:3px solid var(--ink);padding-top:10px;font:11px/1.4 monospace;letter-spacing:.08em;color:var(--muted)}}
h1{{font:700 clamp(30px,5vw,50px)/1.25 "Yu Mincho","Hiragino Mincho ProN",serif;margin:26px 0 8px}}h1 em{{font-style:normal;color:var(--rust)}}
h2{{font:700 24px/1.4 "Yu Mincho",serif;margin:0 0 6px}}.lab{{font:11px monospace;letter-spacing:.14em;color:var(--muted)}}
section{{padding:46px 0 6px;border-top:1px solid var(--line);margin-top:40px}}p{{margin:.6em 0;max-width:46em}}.lead{{font-size:17px}}
.kpi{{display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin:26px 0 0;border-top:1px solid var(--ink);border-bottom:1px solid var(--ink)}}
.kpi div{{padding:16px 14px;border-left:1px solid var(--line)}}.kpi div:first-child{{border-left:0}}
.kpi b{{display:block;font:700 30px/1.15 Georgia,serif;color:var(--green)}}.kpi s{{color:var(--muted);font-size:13px}}.kpi span{{display:block;font-size:12.5px;color:var(--muted);line-height:1.5;margin-top:4px}}
.pair{{display:flex;gap:34px;justify-content:center;align-items:flex-start;margin:26px 0;flex-wrap:wrap}}
figure{{margin:0}}figure img{{display:block;max-width:100%;height:auto;margin:0 auto}}figure.p{{background:var(--white);border:1px solid var(--line);border-radius:6px;padding:14px}}
figcaption{{font:12px/1.5 monospace;color:var(--muted);margin-top:8px;letter-spacing:.04em}}figcaption b{{color:var(--ink)}}
.arrow{{align-self:center;font:34px serif;color:var(--rust)}}
.overlay svg{{width:100%;max-width:520px;height:auto;display:block;margin:0 auto;background:var(--white);border:1px solid var(--line);border-radius:6px}}
.legend{{display:flex;gap:18px;justify-content:center;font-size:13px;margin-top:10px;flex-wrap:wrap}}.legend i{{display:inline-block;width:14px;height:14px;vertical-align:-2px;margin-right:6px;border:1px solid #0003}}
.tw{{overflow-x:auto;margin-top:20px}}table{{border-collapse:collapse;width:100%;min-width:760px;background:var(--white);font-size:14px}}
th,td{{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}thead th{{background:var(--ink);color:#fff;font-weight:600}}
tbody th{{font-weight:600;white-space:nowrap}}td.d{{font:700 14px monospace;color:var(--rust);white-space:nowrap}}td.n{{color:var(--muted);font-size:13px}}tbody tr:nth-child(even){{background:var(--soft)}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:26px;margin:22px 0;align-items:start}}.grid2 figure{{background:var(--white);border:1px solid var(--line);border-radius:6px;padding:14px}}
.note{{border-left:4px solid var(--rust);background:#f0dfd2;padding:12px 16px;margin:22px 0;max-width:52em}}.ok{{border-left-color:var(--green);background:var(--soft)}}
ul{{max-width:50em;padding-left:1.3em}}li{{margin:.4em 0}}code{{background:#e7e3d3;padding:1px 6px;border-radius:3px;font-size:.9em}}
footer{{margin-top:56px;border-top:3px solid var(--ink);padding-top:12px;font-size:12px;color:var(--muted)}}
@media(max-width:760px){{main{{padding:20px 16px 60px}}.kpi{{grid-template-columns:1fr 1fr}}.kpi div:nth-child(3){{border-left:0}}.grid2{{grid-template-columns:1fr}}.arrow{{display:none}}}}
@media print{{body{{background:#fff;font-size:11px}}main{{max-width:none;padding:0}}section{{break-inside:avoid}}}}
</style></head><body><main>
<div class="mast"><span>DNA / PCB — REVISION COMPARISON</span><span>2026.11.05 · KiCad 9.0.4</span></div>
<h1>旧基板より、<em>約4割</em>小さく。<br>吊り穴はマイコン側へ、<br>電池でも光り、<br>スイッチで切れる。</h1>
<p class="lead">改訂4（配線済みの旧基板、29.0 × 116.6 mm）と改訂7（現在の基板、24.0 × 82.1 mm）を、同じ縮尺で並べて比べた資料です。
LED の並び順とデータ連鎖は変えず、外形・LED の配置・吊り穴・シルクを変え、電池でも光るように昇圧と電源切り替えの 13 部品を、電池を入り切りする電源スイッチの 3 部品とともに襟の表面に追加しました。</p>
<div class="kpi">
<div><b>{O["h"]:.0f} → {N["h"]:.0f} mm</b><span>基板の長さ（{pct(O["h"], N["h"])}）</span></div>
<div><b>{O["w"]:.0f} → {N["w"]:.0f} mm</b><span>基板の幅（{pct(O["w"], N["w"])}）</span></div>
<div><b>{pct(O["area"], N["area"])}</b><span>外形の面積<br>{O["area"]:,.0f} → {N["area"]:,.0f} mm²</span></div>
<div><b>0 / 0 / 0</b><span>DRC 違反・未接続・差異<br>新旧とも</span></div>
</div>

<section><span class="lab">01 / SIDE BY SIDE</span><h2>同じ縮尺で並べる</h2>
<p>左が旧基板、右が新基板です（表面、3D レンダリング）。らせんが短く細くなり、襟の幅が詰まり、下端に吊り穴の耳が付きました。</p>
<div class="pair">{board_fig("old", "<b>旧</b> 改訂4　29.0 × 116.6 mm", "top")}<div class="arrow">→</div>{board_fig("new", "<b>新</b> 改訂7　24.0 × 82.1 mm", "top")}</div>
<div class="pair">{board_fig("old", "<b>旧</b> 裏面（XIAO nRF52840）", "bottom")}<div class="arrow">→</div>{board_fig("new", "<b>新</b> 裏面（XIAO nRF52840）", "bottom")}</div>
</section>

<section class="overlay"><span class="lab">02 / OUTLINE OVERLAY</span><h2>外形を重ねる</h2>
<p>襟（マイコン部）の位置は同じなので、そのまま重ねられます。薄い灰色が旧、緑が新、点は LED（旧は灰色、新は黄色）です。</p>
{overlay_svg()}
<div class="legend"><span><i style="background:#d9d4c3"></i>旧基板</span><span><i style="background:#1f5a49"></i>新基板</span><span><i style="background:#f2d16b"></i>新の LED 24 個</span></div>
</section>

<section><span class="lab">03 / NUMBERS</span><h2>数値の比較</h2>
<div class="tw"><table><thead><tr><th>項目</th><th>旧（改訂4）</th><th>新（改訂5）</th><th>変化</th><th>メモ</th></tr></thead><tbody>{table}</tbody></table></div>
</section>

<section><span class="lab">04 / THREE CHANGES</span><h2>変えた3点</h2>
<h3>① 吊り穴を、らせん先端からマイコン側へ</h3>
<div class="grid2"><figure><img src="{scaled(old_hole, 29.0)}" style="width:{29.0 / 29.0 * 100:.1f}%" alt="旧基板の先端の吊り穴"><figcaption><b>旧</b> らせんの先端に φ3.0 mm の穴</figcaption></figure>
<figure><img src="{scaled(new_hole, 24.0)}" style="width:{24.0 / 29.0 * 100:.1f}%" alt="新基板の下端の耳と吊り穴"><figcaption><b>新</b> USB-C 側の下端に耳を2つ、φ2.0 mm の穴</figcaption></figure></div>
<p>下端の中央は USB-C の差し込み口と電池コネクタ（J1）で埋まっているため、穴は左右の耳に分けました。耳の内側の間隔は 16 mm で、USB-C のプラグはその間を通ります。
チェーンを2つの穴に通すと、USB-C 側を上にして、らせんが下に垂れます。先端の吊り環がなくなった分、らせん側も短くなりました。</p>
<h3>② DNA 部分を小さく</h3>
<p>LED 間隔を 10 mm から 5.5 mm、塩基対ピッチを 6.5 mm から 4.0 mm にし、梯子の幅を 3.4 mm から 3.0 mm に細くしました。マイコン部の幅は、XIAO のパッドが約 20 mm なので 29 mm から 24 mm まで詰めています。
配線ツールで試した限界は、ピッチ 3.8 mm で配線が収束せず、3.6 mm 以下は梯子が 2.8 mm 以下になって LED 周りのビアが入りません。</p>
<h3>③ シルクの塩基文字を削除</h3>
<div class="grid2"><figure><img src="{scaled(old_silk, 29.0)}" style="width:{29.0 / 29.0 * 100:.1f}%" alt="旧基板の塩基文字つきシルク"><figcaption><b>旧</b> 各段に T/C/A/G の文字（表裏で 48 個）</figcaption></figure>
<figure><img src="{scaled(new_silk, 24.0)}" style="width:{24.0 / 29.0 * 100:.1f}%" alt="新基板のシルク"><figcaption><b>新</b> 文字なし。対番号・水素結合・糖とリン酸の環は残す</figcaption></figure></div>
<p>LED の色はソフトウェアで決めるので、基板に固定の塩基文字は印刷しません。襟の配列表記（5′-ATG GCA TCG TAA-3′ など）と水素結合の本数は、そのままです。襟の表面は、昇圧部品の場所をあけるため、START/STOP と凡例 3 行を削除しました。</p>
<h3>④ 電池でも光る：昇圧・電源切り替え・電源スイッチを追加</h3>
<p>旧基板の LED の電源は XIAO の USB の 5 V だけで、電池では光りませんでした。新基板は、電池を昇圧（MT3608B で 5.0 V）して LED に供給し、USB があるときは USB を優先して自動で切り替えます（部品 13 点、襟の表面）。電池のマイナスは GND に直結し、昇圧の電流が XIAO の内部を通らないようにしました。電池は、基板上のスライドスイッチ（P-MOSFET を駆動）で入り切りでき、OFF にすると USB がないとき電池の電流は流れません（昇圧は消灯中も約 19 mA 流れるため）。詳しい確認結果は <code>review.html</code> にあります。</p>
</section>

<section><span class="lab">05 / NEW COLLAR</span><h2>新しい襟まわり（3D）</h2>
<div class="grid2"><figure><img src="{webp(collar_front, 560)}" alt="襟の表面：電池コネクタ、昇圧回路、吊り穴の耳"><figcaption>表：電池コネクタ（J1）、電源スイッチ、昇圧回路、吊り穴の耳</figcaption></figure>
<figure><img src="{webp(collar_back, 560)}" alt="襟の裏面：マイコンモジュール"><figcaption>裏：XIAO と USB-C。プラグは耳の間を通る</figcaption></figure></div>
</section>

<section><span class="lab">06 / UNCHANGED</span><h2>変えていないこと</h2>
<ul><li>プロジェクト設定（同一ファイル）。回路図は昇圧回路などを追加。既存の 52 部品の UUID は変更前後で一致。</li>
<li>LED 24 個（12 対）、データ連鎖の順（U2 → U25）、4 コドンの区切り。<code>console/</code> のピクセル順もそのまま使える。</li>
<li>既存の 52 部品の型番。配線は引き直したが、DRC は新旧とも違反 0・未接続 0・差異 0。</li>
<li>2 回転・12 塩基対のらせんの形、表裏のシルクの意匠（糖・リン酸の環、水素結合、5′/3′）。</li></ul>
</section>

<section><span class="lab">07 / TRADE-OFFS</span><h2>注意点</h2>
<div class="note"><b>らせん内の窓（抜き穴）が消えた。</b>ピッチを 4.0 mm にすると梯子の間が 1.0 mm で、抜きを作れません。外形のふくらみでらせんに見えますが、旧基板の「窓の開いたらせん」の見た目とは違います。</div>
<ul><li>LED が近づいたので（間隔 5.5 mm）、隣の LED の光が混ざりやすくなります。実機の見え方は未確認です。</li>
<li>耳は 4.5 mm 突き出します。USB-C のケーブルの根元（プラグ）が 16 mm より大きいと当たります。</li>
<li>ビアは 86 → {N["vias"]} 個。配線の総延長は短くなりましたが、密度は上がっています。</li>
<li>確認したのは KiCad 上の DRC と 3D 表示までです。実機の製造・点灯・重さは未確認です。</li>
<li>発注データ（<code>fusion/</code>）は改訂5に合わせて再生成済みですが、Seeed Fusion への再見積・再注文はしていません。</li></ul>
</section>

<footer>旧：<code>design/pre-compact-20261102/</code>　新：<code>dna-accesories.kicad_pcb</code>　生成：<code>gen/compare_stats.py</code> → <code>gen/make_comparison.py</code></footer>
</main></body></html>'''
out = ROOT / 'design' / 'comparison-rev4-rev5.html'
out.write_text(html, encoding='utf-8')
print('wrote', out, round(out.stat().st_size / 1e6, 2), 'MB')
shutil.rmtree(work, ignore_errors=True)  # the renders are cached in gen/_runs/compare_cache
