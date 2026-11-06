# Seeed Fusion PCBA 発注パッケージ（DNA LED ペンダント）

作成日 2026-11-06（改訂6：電池でも LED が光る昇圧回路と USB／電池の自動切り替えを追加。基板 24.00 × 82.09 mm、部品 65 点）。元データ：`../dna-accesories.kicad_pcb`（KiCad 9.0.4、DRC 違反 0・未接続 0・回路図差異 0）。
再生成：`gen/dump_assembly_data.py`（KiCad 付属 Python）→ `gen/make_fusion_package.py`。PCB を変更したら両方を再実行すること。

## ファイル

| ファイル | 用途 | Fusion の入力先 |
|---|---|---|
| `dna-accesories_gerber.zip` | ガーバー 9 層（F/B Cu・Mask・Paste・Silk、Edge）＋ドリル `.drl` ＋ジョブ ＋ `assembly-drawing.pdf` | PCB アップロード |
| `BOM.xlsx` | Seeed 指定テンプレートに記入（A〜D 列のみ、空行なし）。13 行・65 点 | PCBA タブの BOM |
| `centroid.pos` / `centroid.csv` | 実装座標（SMD 65 点、表 38・裏 27、mm、KiCad 絶対座標） | PCB アップロードに同梱 |
| `assembly-drawing.pdf` | 表・裏の実装図（部品番号入り）と詳細 4 枚（LED の 1 番ピン、電池コネクタの極性、XIAO・R1・C25） | gerber.zip に同梱済み |
| `BOM_detail.xlsx` | 社内用の詳細 BOM（メーカー・パッケージ・実装面・代替品・注意）。発注には使わない | — |
| `gerber/` | zip の展開前ファイル | — |

基板の表面シルクに部品番号は印刷されていない。Seeed は「部品番号が基板にない場合は、実装図 PDF をガーバー zip に入れる」ことを求めているため、PDF を zip に入れてある。

## 部品表（65 点、13 品番）

| 部品番号 | 数量 | 型番（MPN / Seeed SKU） | 内容 | 面 |
|---|---|---|---|---|
| U1 | 1 | `102010448`（Seeed SKU） | Seeed Studio XIAO nRF52840。ピンヘッダなしの標準品 | 裏 |
| J1 | 1 | `B2B-PH-SM4-TB(LF)(SN)`（JST） | 電池用 PH 2 ピン SMD コネクタ | 表 |
| U2〜U25 | 24 | `XL-1010RGBC-WS2812B`（XINGLIGHT） | 1010 サイズの WS2812B 系 RGB LED | 表 |
| U26 | 1 | `MT3608B`（Aerosemi） | 昇圧 IC（電池 → 5.0 V）SOT-23-6。1 番ピン = SW | 表 |
| L1 | 1 | `SRN4018TA-100M`（Bourns） | 10 µH 1.2 A（Irms）4×4×1.8 mm シールド | 表 |
| D1, D2 | 2 | `1N5819HW-7-F`（Diodes Inc.） | ショットキー 40 V 1 A SOD-123。カソード（帯）が 1 番パッド | 表 |
| Q1 | 1 | `2N7002-7-F`（Diodes Inc.） | N-ch MOSFET SOT-23（USB があるとき昇圧を止める） | 表 |
| C25〜C29 | 5 | `CL21A106KAYNNNE`（Samsung） | 10 µF 25 V X5R 0805（C25 のみ裏。C26〜C29 は表の昇圧回路） | 表／裏 |
| C1〜C24 | 24 | `CL05B104KA5NNNC`（Samsung） | 100 nF 25 V X7R 0402（LED の真裏に 1 個ずつ） | 裏 |
| R1 | 1 | `RC0402FR-07100RL`（Yageo） | 100 Ω 1 % 0402（データ線の直列抵抗） | 裏 |
| R2 | 1 | `RC0402FR-07110KL`（Yageo） | 110 kΩ 1 % 0402（昇圧の帰還抵抗・上） | 表 |
| R3 | 1 | `RC0402FR-0715KL`（Yageo） | 15 kΩ 1 % 0402（帰還抵抗・下。出力 5.0 V） | 表 |
| R4, R5 | 2 | `RC0402FR-07100KL`（Yageo） | 100 kΩ 1 % 0402（昇圧の EN プルアップ、Q1 のゲートプルダウン） | 表 |

- 型番は、Seeed の BOM ガイドの「MPN 欄にはメーカー型番を書き、DigiKey/Mouser の品番は書かない」に従った。
- `U1` に Pre-Soldered 版（SKU 102010631）を選ばないこと。
- 容量・耐圧・誘電体が同じ代替品は `BOM_detail.xlsx` に記載。Seeed が在庫の都合で代替を提案してきた場合の確認用。
- リンクは検索で確認した商品ページ。在庫・価格は発注時点のものを必ず確認すること。

## 発注時の設定値

- 層数 2、板厚 1.6 mm（KiCad の基板設定どおり）。
- 基板サイズ 24.00 × 82.09 mm、複雑外形（内側の抜き・吊り穴φ2.0 mm ×2 あり）。
- 実装：両面。表は LED 24 個・コネクタ 1 個・昇圧回路 13 点（計 38 点）、裏は 27 点。
- 銅厚・表面処理・ソルダーマスク色は Fusion の選択肢から決める。プレビュー画像は緑のマスク・白シルクで作ってある。表面処理は、1010 LED と 0402 部品の平坦さを考えると無鉛 HASL より ENIG が無難と思うが、価格差を見て判断すること。
- 実装数量は PCB 数量以下にできる。BOM の数量は 1 枚あたり。

## LED が BOM 照合で見つからない場合

`XL-1010RGBC-WS2812B` は LCSC（C5349953）と DigiKey のマーケットプレイスにあるが、DigiKey/Mouser の自社在庫ではなく、Seeed の自動照合には出ない。見積依頼で対応できる。手順と英文は `quote-request-note.md`。

## 確認済みの項目（実測）

- 線幅 0.15／0.20 mm、ビア 外径 0.56／穴径 0.30 mm。Fusion の最小 4/4 mil（約 0.10 mm、1 oz、Fusion の wiki で確認）以上。
- らせん部のいちばん細いくびれは約 3.2 mm、内側の抜き・吊り穴の最小幅は 2.0 mm（吊り穴まわりのリングは 1.0 mm）。
- 同じ面の部品どうしのパッド端の間隔は最小 1.99 mm（C25〜U1）。表面は LED だけで最小 2.7 mm（U10〜U13）。Fusion の「チップ部品間 1 mm 以上」を満たす。
- LED のパッドから基板外形（内側の抜きを含む）までは最小 0.55 mm。
- すべて SMD。スルーホール部品なし、NPTH なし（吊り下げ穴は外形の抜き）。ドリルはビア 0.3 mm のみ。
- BOM・位置ファイル・回路図の部品番号が 65 点すべて一致（集合を照合済み）。

## Fusion に確認・相談すべき点（私が判断できなかったもの）

1. **XIAO（U1）の実装方法。** 裏面の大きなモジュールで、表面に LED を載せる 2 回目のリフローで落下しないか。モジュールを Fusion が実装できるのか、手はんだになるのか。実装図 Detail D に向き（USB-C が基板下端側）を書いてある。
2. **U1 と R1・C25 の近さ。** Fusion の規定「チップ部品〜コネクタ 5 mm 以上」を、USB-C を持つ XIAO に当てはめると R1・C25 が引っかかる可能性（パッド間 約 2.0 mm）。
3. **基板端の部品。** J1 と U1 のコートヤードが基板下端に接する（J1 は 0.13 mm、U1 は 0）。搬送レールを付ける面付け（パネル化）が必要か。フィデューシャルは基板に付いていない（Fusion の仕様ページには要件の記載なし）。
4. **ビアとパッドの重なり。** GND ビア 6 本（LED の 3 番パッドとコンデンサの 2 番パッドの付近）と、XIAO のパッド付近の 2 本。ビアはすべてマスクで覆ってあるが、はんだの吸い上げを指摘されたら、ビアの位置をずらす。数値は包含ボックスによる概算。
5. **位置ファイルの座標系。** KiCad の `.pos`／CSV は Y が上向き（値が負）。裏面部品の回転は KiCad の定義。ガーバーと同じ絶対原点なので整合するが、Fusion の取り込み後に実装図とのずれを確認してもらうこと。
6. **LED の保管・ベーク条件。** 1010 の小型 LED は吸湿管理が必要な場合がある。リールの MSL 表示を確認し、必要なら Fusion に伝える。

## 発注前に残る設計側の確認

- 新しい昇圧回路（U26、L1、D1、D2、Q1 と周辺）は実機で未確認。MT3608B・インダクタ・R2〜R5 は LCSC 番号を確認できていない（リンクは検索ページ）。Fusion の部品調達で見つからない場合は `BOM_detail.xlsx` の代替品を参照。詳しくは `../review.html`。
- 部品の最終選定（特に LED の MSL・VDD 耐圧、コンデンサの DC バイアス特性）は、メーカーのデータシートで最終確認すること。

## アップロード手順（Fusion の公式手順に準拠）

1. Fusion の PCB 発注ページで PCBA タブを開く。
2. `dna-accesories_gerber.zip` を PCB ファイルとしてアップロードし、上記の設定値を入力する。`centroid.pos` は同じアップロードに同梱する（Seeed は同梱を推奨）。
3. PCBA タブで `BOM.xlsx` をアップロード。MPN が DigiKey/Mouser と照合され、部品ごとの価格が出る。照合できない部品は、調達チームが 1 営業日を目安に見積もる。
4. 外部調達の部品は固定 SKU 508000001 で表示される。Seeed OPL の部品だけなら 7〜15 営業日、それ以外が含まれると 20〜25 営業日が目安（Fusion の仕様ページ）。
5. 実装数量と価格を確認して注文する。

## 参照

- [Fusion PCBA Specification](https://support.seeed.cc/portal/en/kb/articles/fusion-pcba-specification)
- [How do I place a Seeed Fusion PCBA order?](https://support.seeed.cc/portal/en/kb/articles/how-do-i-place-a-seeed-fusion-pcb-assembly-pcba-order)
- [Pick and Place (XY) ファイルの出力](https://support.seeed.cc/portal/en/kb/articles/how-do-i-export-pcb-pick-and-place-xy-files-for-seeed-fusion-pcba-orders)
- [XIAO nRF52840 データシート](https://files.seeedstudio.com/Bazaar/product_pdf/102010448.pdf)
- [JST PH シリーズ データシート](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf)
