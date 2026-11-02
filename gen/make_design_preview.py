"""Render an exact-coordinate placement preview and a self-contained review page."""
from pathlib import Path
import json, math, html, base64, hashlib
import fitz
ROOT=Path(__file__).resolve().parents[1]
g=json.loads((ROOT/'design'/'dna-geometry.json').read_text())
d=json.loads((ROOT/'design'/'placement-drc.json').read_text())
def path(points):return 'M '+' L '.join(f'{x:.4f},{y:.4f}' for x,y in points)+' Z'
outline=' '.join(path(p) for p in [g['outer']]+g['holes'])
parts=[f'<path d="{outline}" fill="#214e43" fill-rule="evenodd" stroke="#163c34" stroke-width=".2"/>']
# Draw the actual PCB's front silk, including its over/under gaps and pad keep-outs.
for item in json.loads((ROOT/'design'/'front-silkscreen.json').read_text()):
    if item['type']=='line':
        a,z=item['a'],item['b']
        parts.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{z[0]}" y2="{z[1]}" stroke="#f4f4dc" stroke-width="{item["width"]}" stroke-linecap="round"/>')
    elif item['type']=='circle':
        parts.append(f'<circle cx="{item["c"][0]}" cy="{item["c"][1]}" r="{item["r"]}" fill="none" stroke="#f4f4dc" stroke-width="{item["width"]}"/>')
    else:
        x,y=item['xy'];label=html.escape(item['text']);size=item['size']
        parts.append(f'<text x="{x}" y="{y+size*.34}" text-anchor="middle" font-family="Consolas,monospace" font-size="{size}" fill="#f4f4dc">{label}</text>')
for pair in g['pairs']:
    a,b=pair['a']['xy'],pair['b']['xy'];y=a[1]
    for key,color in [('a','#ffd269'),('b','#aeece5')]:
        led=pair[key];x,y=led['xy']
        parts.append(f'<circle cx="{x}" cy="{y}" r="1.3" fill="{color}" opacity=".14"/>')
        parts.append(f'<rect x="{x-.5}" y="{y-.5}" width="1" height="1" rx=".12" fill="{color}" stroke="#fcfae6" stroke-width=".09"/>')
        # Assembly labels sit on the rung's inward side, away from the pads.
        tx=x+1.3 if x<100 else x-1.3
        anchor='start' if x<100 else 'end'
        # Narrow projected pairs use offset labels above / below their respective base.
        if abs(a[0]-b[0])<8:tx=x;anchor='middle';ty=y+1.24
        else:ty=y+1.45
        parts.append(f'<text x="{tx}" y="{ty}" text-anchor="{anchor}" font-family="Consolas,monospace" font-size=".85" fill="#eff3da">{led["ref"]}</text>')
parts.append('<rect x="90" y="121.5" width="20" height="21" rx="1" fill="none" stroke="#8dad91" stroke-width=".2" stroke-dasharray=".8 .5"/>')
parts.append('<rect x="96.5" y="136.5" width="7" height="6.5" rx=".3" fill="#e1e3d6" stroke="#31493a" stroke-width=".15"/><text x="100" y="140.1" text-anchor="middle" font-size="1.2" fill="#214136">J1</text>')
svg='<svg xmlns="http://www.w3.org/2000/svg" width="360" height="1230" viewBox="82 26 36 123"><rect x="82" y="26" width="36" height="123" fill="#f3f0e6"/>'+''.join(parts)+'</svg>'
(ROOT/'design'/'preview'/'dna-layout.svg').write_text(svg,encoding='utf-8')
doc=fitz.open(stream=svg.encode(),filetype='svg');pdf=fitz.open('pdf',doc.convert_to_pdf());pdf[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(ROOT/'design'/'preview'/'dna-layout.png')
rows=''.join(f'<tr><td>{p["pair"]:02}</td><td>{p["a"]["ref"]}</td><td>{p["b"]["ref"]}</td><td>{p["codon_group"]}</td><td>{p["a"]["xy"][1]:.1f}</td></tr>' for p in g['pairs'])
image=base64.b64encode(svg.encode()).decode()
css='''*{box-sizing:border-box}body{margin:0;background:#f3f0e6;color:#173e34;font:15px/1.85 "Yu Gothic","Meiryo",sans-serif}main{max-width:1050px;margin:0 auto;padding:40px 30px}header{border-top:2px solid #173e34;padding:22px 0}h1{font-family:"Yu Mincho",Georgia,serif;font-size:42px;line-height:1.4;margin:12px 0}h2{font-size:22px;margin:0 0 16px}.eyebrow,code{font-family:Consolas,monospace;font-size:12px;letter-spacing:.06em}.layout{display:grid;grid-template-columns:330px 1fr;gap:40px}.layout img{width:100%;max-height:1140px;object-fit:contain;object-position:top;background:#f3f0e6}.panel{border-top:1px solid #9dac98;padding:24px 0}.status{background:#e1e8d2;padding:15px 20px;margin:22px 0}.attention{background:#ede2cf;padding:14px 18px;font-size:13px}.metrics{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid #173e34;border-bottom:1px solid #173e34;margin:24px 0}.metrics>div{padding:16px 8px}.metrics b{display:block;font:35px Georgia,serif}.metrics span{font-size:12px}a{color:inherit;text-underline-offset:4px}table{width:100%;border-collapse:collapse;font-size:13px}td,th{text-align:left;padding:7px 9px;border-bottom:1px solid #cad0bf}th{background:#e5e8db}ul{padding-left:20px}.links{display:flex;gap:15px;flex-wrap:wrap;font-size:13px}.fine{font-size:12px;color:#5e6e5c}code{overflow-wrap:anywhere}.footer{border-top:1px solid #173e34;padding-top:15px;margin-top:35px;font-size:12px}@media(max-width:750px){main{padding:20px}.layout{display:block}.layout img{max-height:850px;margin-bottom:25px}h1{font-size:32px}}@media print{body{background:white}main{padding:0}.layout{grid-template-columns:240px 1fr;gap:25px}h1{font-size:26px}.links{display:none}.panel{break-inside:avoid}td,th{padding:3px 7px}}'''
htmltext=f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DNA基板・外形と塩基対配置の改訂</title><style>{css}</style></head><body><main><header><div class="eyebrow">DNA / PCB · LAYOUT REVISION 01 · 2026.10.08</div><h1>2本の鎖、12組の塩基対。</h1><p>1個のLEDを1個の塩基として、24個を左右の鎖に12対で配置しました。各対は連続するLED番号でつながり、交差位置では鎖とLEDの左右が入れ替わります。</p><div class="status"><strong>書き込み確認：成功</strong> — 作成・読み戻し・削除を確認してから元設計をバックアップし、主PCBファイルを更新しました。</div></header><div class="layout"><div><img src="data:image/svg+xml;base64,{image}" alt="DNA二重らせん形の基板。24個のLEDが12対になり、下端にXIAOと電池コネクタ。"><p class="fine">実座標に基づく配置図。LEDの黄／青は鎖の識別用で、塩基種・発光色の指定ではありません。XIAOは裏面です。実際のシルクはKiCad出力図を参照。</p></div><div><div class="metrics"><div><b>12</b><span>塩基対</span></div><div><b>24</b><span>RGB LED</span></div><div><b>29×117</b><span>外形寸法 / 約mm</span></div></div><section class="panel"><h2>変更した形状と配置</h2><ul><li>外形を2本のらせん状の鎖と12本の塩基対の横棒で構成する、連続した1枚の基板へ再設計。</li><li>横棒の両端に1個ずつLEDを配置し、U2/U3からU24/U25まで12組に対応。</li><li>LED間隔をらせんの投影形状に合わせて変化させ、鎖の交差に沿って左右を反転。</li><li>下端に裏面のXIAOと表面のJ1をまとめ、上端に直径3 mmの吊り下げ穴を追加。</li><li>小さな切抜き片を除き、内部スロットの角を約0.6 mm半径で丸める。</li><li>LED番号は組立図に、塩基対番号01〜12は基板シルクに記載。</li></ul><p class="fine">装飾用の2回転モデルです。塩基対数／1回転の比率や寸法は分子スケールを再現していません。</p></section><section class="panel"><h2>回路図との対応</h2><p><code>U1.D6 → U2 → U3 → … → U25</code><br>部品UUID、パッド番号、全ネット名を維持しています。各ペア内のDOUT→DINを12本配線済みです。3対＝6個のLEDが元のCODON区分1組に対応します。</p><table><thead><tr><th>対</th><th>鎖A</th><th>鎖B</th><th>区分</th><th>Y / mm</th></tr></thead><tbody>{rows}</tbody></table></section><section class="panel"><h2>配置段階の検証</h2><ul><li>KiCad 9.0.4：外形、銅箔と基板端、シルク、ライブラリ一致等の違反 <strong>{len(d['violations'])}件</strong>。</li><li>回路図との対応差異 <strong>{len(d['schematic_parity'])}件</strong>。</li><li>全26個のフットプリントとパッドネットの対応を更新前後で比較。</li><li>基板外のLED配置を解消し、単一外周と内部切抜きに整理。</li></ul><div class="attention"><strong>この版は外形・配置の改訂版です。</strong><br>未接続は{len(d['unconnected_items'])}件あります。電源・GND、対と対の間、XIAO・電池端子の配線は次工程です。電池単独でのLED給電、デカップリング、採用LEDの1番／2番端子対応は前回のレビューから継続する設計課題で、今回の配置変更では解決していません。製造・点灯試験用の完成版ではありません。</div></section><section class="panel"><h2>設計ファイル</h2><div class="links"><a href="dna-accesories.kicad_pcb">KiCad PCB</a><a href="dna-accesories.kicad_sch">回路図</a><a href="design/preview/front-kicad.svg">表面のKiCad出力</a><a href="design/preview/back-kicad.svg">裏面のKiCad出力</a><a href="design/base-pairs.csv">塩基対一覧</a><a href="design/placement-drc.json">DRC結果</a><a href="design/pre-redesign-20261008/review-original.html">改訂前レビュー</a></div></section></div></div><footer class="footer">元ファイルのバックアップ：design/pre-redesign-20261008/ · 再生成用スクリプト：gen/ · 最小幅・厚さ・材質・色等の製造条件は別途確定。</footer></main></body></html>'''
htmltext=htmltext.replace('LAYOUT REVISION 01','LAYOUT REVISION 02')
htmltext=htmltext.replace('2本の鎖、12組の塩基対。','12組の塩基対を、同じ間隔で。')
htmltext=htmltext.replace('横棒の両端に1個ずつLEDを配置し、U2/U3からU24/U25まで12組に対応。','各横棒に中心間10.0 mmで2個のLEDを配置し、U2/U3からU24/U25まで12組に対応。')
htmltext=htmltext.replace('LED間隔をらせんの投影形状に合わせて変化させ、鎖の交差に沿って左右を反転。','全12組のLED中心間を10.0 mmに統一。鎖の交差に沿ってLEDの左右を反転し、ねじれを表現。')
htmltext=htmltext.replace('LED番号は組立図に、塩基対番号01〜12は基板シルクに記載。','シルクに二重線の鎖、交差部の重なり、塩基の両側の線、塩基間の破線、5′・3′方向を追加。塩基対番号01〜12も記載。')
htmltext=htmltext.replace('<b>29×117</b><span>外形寸法 / 約mm</span>','<b>10.0 mm</b><span>全12対のLED中心間</span>')
htmltext=htmltext.replace('実際のシルクはKiCad出力図を参照。','白い線と塩基対番号は実PCBのシルクから描画。LED番号とXIAOの点線枠は組立用の補助表示です。外形は約29×117 mm。')
# This placement-only report now lives one directory below the project root.
htmltext=htmltext.replace('href="design/','href="').replace('href="dna-accesories.','href="../dna-accesories.')
(ROOT/'design'/'layout-review.html').write_text(htmltext,encoding='utf-8')
print('Saved design/layout-review.html and design/preview/dna-layout.svg / .png; functional review.html preserved')
