# DNA二重らせん基板：外形・配置の改訂版2

2026-10-08。主ファイル `../dna-accesories.kicad_pcb` を更新。

- 約29.0 × 116.6 mm、2本の鎖・12本の塩基対、吊り下げ穴φ3 mm。
- U2/U3、U4/U5、…、U24/U25の12対。LEDは1個ずつ塩基を表す。
- 全12対でLED中心間を10.0 mmに統一。LED本体1.0 mmを基準にした本体間隔は約9.0 mm。
- 表面シルクに二重線の鎖、交差部の重なり、塩基間の破線、5′・3′方向と対番号を記載。
- 各対内DOUT→DINを配線し、その他の配線は未完了。
- U1は裏面、J1は表面。LEDの型番・端子・ネット・UUIDは維持。
- らせんは装飾用の投影モデル。分子スケールの比率は表していない。
- LED/モジュールのローカルフットプリントはシルクだけを整理。パッドとモデルは維持。

## 確認済み

書き込み・読み戻し・削除に成功。KiCad 9.0.4で配置段階のDRCを実行し、違反0件、回路図との対応差異0件。未接続は別枠で62件あり、全配線完了を意味しない。

## 次工程

電源/GND、各対の間、電池・モジュール間の配線。電池単独でのLED給電、LED近傍コンデンサ、信号保護、採用品の端子位置照合。製造前に配線と電源設計を完成し、最終DRC・実装図・製造データを確認する。

## ファイル

- `base-pairs.csv`: 塩基対とLEDの対応・座標・ネット。
- `placement-drc.json`: 配置段階のDRCと未接続。
- `net-preservation.json`: 更新前後で部品UUIDとパッドネットが一致することの記録。
- `preview/dna-layout.svg`, `.png`: 実座標の配置図。色は鎖の識別用。
- `front-silkscreen.json`: 実PCBの表面シルクを抽出した描画データ。プレビューの白線はこの実データを使用。
- `preview/front-kicad.svg`, `back-kicad.svg`: 実PCBから出力した図。
- `pre-redesign-20261008/`: 改訂前のPCB・回路図・プロジェクト・ライブラリ表と変更したフットプリントのバックアップ。
- `revision-01/`: LED間隔変更前の外形・配置版のバックアップ。
- `../review.html`: 改訂5の基板レビュー（配線・ネット・電源・製造余裕・3D干渉を実測）。旧レビュー（改訂3＋改訂4の追記）は `review-rev3-rev4.html`。生成は `gen/review_checks.py` → `gen/make_review.py`。`gen/build_functional_review.py` は旧レビュー用（出力先を `review-rev3-rev4.html` に変更済み）。
- `functional-review/`: 再実行DRC/ERC、ネットリスト、対象ファイルのハッシュ、メーカー資料の保存版。
- `layout-review.html`: 配置プレビュー生成時に出力する配置説明。主レビューは上書きしない。

## 再生成

Python 3.13とShapely 2.2.0を使用。KiCad側スクリプトはKiCad付属Pythonで実行する。

```powershell
python gen/make_dna_geometry.py --dependency-path '<Shapelyインストール先>'
& 'C:\Program Files\KiCad\9.0\bin\python.exe' gen/clean_footprint_silk.py
& 'C:\Program Files\KiCad\9.0\bin\python.exe' gen/rebuild_dna_board.py
& 'C:\Program Files\KiCad\9.0\bin\kicad-cli.exe' pcb drc --schematic-parity --format json -o design/placement-drc.json dna-accesories.kicad_pcb
```

再生成はバックアップPCBを起点にするため、この改訂後に手作業で編集した配線は上書きされる。

動作レビューのHTMLは `python gen/build_functional_review.py` で再生成できる。`functional-review/summary.json` に記録したファイルハッシュと現設計が一致しない場合は生成を停止する。PCBを変更したら、DRC/ERC・ネットリスト・集計を再実行してレビュー内容も見直すこと。

## 改訂3（2026-10-10）

- 表裏のシルクを追加：塩基文字（配列 ATG GCA TCG TAA と相補鎖）、水素結合（A-T 2本／G-C 3本）、糖・リン酸の環、吊り下げ穴リング、配列・凡例、裏面のUSB-C目印。再生成は `DNA_DEPS=<Shapely>` を指定して `gen/rebuild_dna_board.py`。
- U1（XIAO）とJ1にSTEPを設定し、全26部品が3Dモデルを持つ。`gen/check_interference.py` で干渉計算（`interference-check.json`）。部品間・基板との重なりは0件。USB-Cプラグ（仮寸法）は基板下端に食い込むため `review-rev3-rev4.html` の指摘09（改訂4で解消、改訂5の `review.html` で再確認）。
- 更新前の状態：`pre-silk-20261010/`。DRC違反0件、未接続62件は変わらず。

## 改訂4：配線（2026-10-10）

- `review-rev3-rev4.html` の指摘01に従い、LEDのVDD/DOUTを入れ替え（VDD=2番、DOUT=1番。`gen/swap_led_pins.py`。シンボル位置は不変）。
- POWER・GND・24段データ・J1とBAT端子を2層で配線（`gen/route_prep.py` → `gen/route_board.py` → `gen/route_apply.py`）。KiCad 9.0.4：DRC違反0、未接続0、回路図差異0（`wiring-drc.json`）。ERCは警告1件（`wiring-erc.json`。ここに書いていた「26件」は誤りで、10月10日のファイルも1件）。
- 未対応：電池単独給電、LED近傍コンデンサ、DIN直列抵抗の場所、USB-C干渉（review指摘03〜09）。
- 配線前のバックアップ：`pre-wiring-20261010/`。旧レビューは先頭に注記のみ追加し、本文は配線前の状態（現在は `review-rev3-rev4.html`）。`rebuild_dna_board.py` を再実行すると配線は消える。
- 配線ルータは自作のグリッド探索で乱数順序（SEED）を使うため、結果の再現には `gen/_routes.json` を使用する。

## 発注用データ（2026-10-10）

- `../fusion/` に Seeed Fusion PCBA 用のガーバー zip・BOM・位置ファイル・実装図・手順を作成。詳細は `../fusion/README.md`。

## 改訂5：らせんの縮小・吊り穴の移動・塩基文字の削除（2026-11-02〜03）

- 外形 29.0 × 116.6 mm → 24.0 × 82.1 mm。マイコン部の幅は29 → 24 mm（XIAOのパッドが約20 mm）。
  らせん部（先端〜襟）は88.1 mm → 49.1 mm、うち12対の間隔の合計は78 → 48 mm（12 × 4.0 mm）。らせんの幅は26.8 → 16.2 mm。
  LED間隔 10 → 5.5 mm、塩基対ピッチ 6.5 → 4.0 mm、梁幅 3.0 mm、バックボーン幅 3.2 mm、振幅 6.5 mm。
  これ以上詰める限界の目安：ピッチ3.8 mmは配線が収束しにくく（銅箔〜外形 0.56 mm では未接続が残った）、3.6 mm以下は梁幅2.8 mm以下になりLED周りのビアが入らない。
  ピッチ4.9 mm以下では抜き穴がほぼ消える（外形は梁のふくらみだけでらせんに見える）。
- 吊り穴：らせん先端のφ3 mm を廃止し、マイコン部下端（USB-C側）の外側に、左右2つの耳（幅4 mm、長さ約4.5 mm）を延ばしてφ2.0 mm の穴を各1つ。
  耳の内側の間隔は16 mmで、USB-Cプラグはその間を通る。USB-C側を上にして吊る。
- シルク：各段の塩基文字（T/C/A/G）を削除。対番号は中央に移動し、水素結合の破線は左右に分けた。
  配列2行・START/STOP・凡例・水素結合の本数は従来どおり。
- 再生成手順：`gen/make_dna_geometry.py` → `gen/rebuild_dna_board.py`（起点は `pre-compact-20261102/` の配線済み基板）
  → `gen/route_prep.py`（--swapは付けない）→ `gen/route_board.py`（`WS=0.15 CL=0.16 WP=0.2 EDGE=0.56 VIAD=0.56`、失敗したネットを `PRIO` で先頭へ送って再試行）→ `gen/route_apply.py`。
  寸法は環境変数 `DNA_D / DNA_P / DNA_A / DNA_RAIL / DNA_RUNG` で変えられる。Shapelyは `gen/_deps/py313`（通常Python）と `gen/_deps/py311`（KiCad付属Python、`DNA_DEPS`）。
  `EDGE` を0.55以下にすると、ラスタ化の誤差で銅箔〜外形が0.5 mmを割る（DRCの銅箔外形エラー）ので0.56を使う。
- KiCad 9.0.4：DRC違反0、未接続0、回路図差異0（`wiring-drc.json`）。
- 更新前の状態：`pre-compact-20261102/`。`base-pairs.csv` の `base` 列は配列上の塩基で、シルクには出ていない。
- 発注データ（`../fusion/`）は改訂5に合わせて再生成済み（`gen/dump_assembly_data.py` → `gen/make_fusion_package.py`）。
- 試作ページ `../lp/` は `gen/make_lp_images.py` で、画像（3Dレンダリング）とLED座標の対応を再生成する。

## 新旧の比較資料

`comparison-rev4-rev5.html`（1ファイルで開ける）：改訂4（`pre-compact-20261102/`）と現在の基板を、同縮尺の3D画像・外形の重ね図・数値表で比較。
再生成：`gen/compare_stats.py`（KiCad付属Python）→ `gen/make_comparison.py`。

## 改訂5のレビュー（2026-11-06、`review-rev5.html`）

`../review.html`。DRC・ERCに加え、厳しい規則のDRCで間隔を実測、基板のトラックから電源の電圧降下を計算、ネット連鎖と部品位置を照合、3D干渉と製造データ（ガーバー・ドリル・BOM・実装座標）を確認。結論：配線・形状・製造データに誤りなし。未解決は「電池単独でLEDが点灯しない」（設計判断）。吊り穴まわりの肉厚1.0 mm、ビア環0.13 mmは確認をすすめる。

## 改訂6：電池でも LED が光る（2026-11-06）

- 改訂5の未解決点（LED の電源が USB の 5 V だけ）に対し、昇圧と USB／電池の自動切り替えを追加。
  電池（VBAT）→ L1 → MT3608B（U26）→ D1 → POWER（5.0 V）。USB があるときは USB → D2 → POWER、Q1 が U26 の EN を落として昇圧を止める。
  出力電圧は 0.6 V × (1 + R2/R3) = 5.0 V（110 kΩ／15 kΩ、データシート Fig.1 の値）。部品 13 点（U26、L1、D1、D2、Q1、C26〜C29、R2〜R5）は襟の表面。
  電池のマイナス（J1.2・XIAO の BAT−）は GND に直結（Seeed 回路図 v1.1 で BAT− は GND）。
- 回路図：`gen/add_boost_sch.py`（1 回だけ実行。起点は `pre-boost-20261106/`）。基板：`gen/place_boost.py`（配置の探索、結果は `gen/_boost_place.json`）
  → `gen/add_boost_pcb.py`（`boost-base/` を作る）→ `gen/rebuild_dna_board.py`（起点は `boost-base/`）→ `gen/route_prep.py` → `gen/route_search.py`（シードを変えて並列）→ `gen/route_apply.py`。
  ルーターは、VBAT・SW を 0.4 mm、電源・GND・VUSB を 0.2 mm、信号を 0.15 mm で引き、XIAO のフットプリントの禁止領域（テストパッド周り）を避ける。
- シルク：襟の表面は昇圧部品の場所をあけるため、START/STOP と凡例 3 行を削除。REV は「REV 6」。
- 検証：KiCad 9.0.4 の DRC 違反 0・未接続 0・回路図差異 0。ERC は警告 3 件（ラベル 1、BAT−／BAT＋の端子の型の組み合わせ 2）。銅箔間隔の最小 0.143 mm、銅箔〜外形 0.560 mm。3D 干渉 0。
- ファームウェア（`../console/firmware/`、`../firmware/`）：USB 給電がないときに D6 を浮かせる処理を削除。
- 発注データ（`../fusion/`）は 65 点・13 品番で再生成。実装図に昇圧部の拡大図（Detail E）を追加。
- 実機での昇圧回路の動作は未確認。レビューは `../review.html`、改訂4との比較は `comparison-rev4-rev5.html`。
- 更新前の状態：`pre-boost-20261106/`。
