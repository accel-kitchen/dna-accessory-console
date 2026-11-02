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
- `../review.html`: 最新PCBの動作・電源・端子配置・実装条件まで含めたレビュー。現状は未接続62件があり、点灯不可。
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
- U1（XIAO）とJ1にSTEPを設定し、全26部品が3Dモデルを持つ。`gen/check_interference.py` で干渉計算（`interference-check.json`）。部品間・基板との重なりは0件。USB-Cプラグ（仮寸法）は基板下端に食い込むため `review.html` の指摘09。
- 更新前の状態：`pre-silk-20261010/`。DRC違反0件、未接続62件は変わらず。

## 改訂4：配線（2026-10-10）

- `review.html` の指摘01に従い、LEDのVDD/DOUTを入れ替え（VDD=2番、DOUT=1番。`gen/swap_led_pins.py`。シンボル位置は不変）。
- POWER・GND・24段データ・J1とBAT端子を2層で配線（`gen/route_prep.py` → `gen/route_board.py` → `gen/route_apply.py`）。KiCad 9.0.4：DRC違反0、未接続0、回路図差異0（`wiring-drc.json`）。ERCは変わらず26件（`wiring-erc.json`）。
- 未対応：電池単独給電、LED近傍コンデンサ、DIN直列抵抗の場所、USB-C干渉（review指摘03〜09）。
- 配線前のバックアップ：`pre-wiring-20261010/`。`review.html` は先頭に注記のみ追加し、本文は配線前の状態。`rebuild_dna_board.py` を再実行すると配線は消える。
- 配線ルータは自作のグリッド探索で乱数順序（SEED）を使うため、結果の再現には `gen/_routes.json` を使用する。

## 発注用データ（2026-10-10）

- `../fusion/` に Seeed Fusion PCBA 用のガーバー zip・BOM・位置ファイル・実装図・手順を作成。詳細は `../fusion/README.md`。

## 改訂5：らせんの縮小・吊り穴の移動・塩基文字の削除（2026-11-02）

- 外形 29.0 × 116.6 mm → 24.0 × 96.9 mm（マイコン部の幅を29 → 24 mmに細くし、耳の分だけ下に延びた）。らせん部は約78 mm → 約62 mm、幅 26.8 mm → 19.0 mm。
  LED間隔 10 mm → 6 mm、塩基対ピッチ 6.5 mm → 5.2 mm、梯子幅 4.0 mm。
  これ以上詰めると、LED周りのビア・配線が収まらず（梯子幅3.8 mm以下で未配線が出る）、抜き穴も消えてベタ板になる。
- 吊り穴：らせん先端のφ3 mm を廃止し、マイコン部下端（USB-C側）の外側に、左右2つの耳（幅4 mm、長さ約4.5 mm）を延ばしてφ2.0 mm の穴を各1つ。
  耳の内側の間隔は16 mmで、USB-Cプラグはその間を通る。USB-C側を上にして吊る。
- シルク：各段の塩基文字（T/C/A/G）を削除。対番号は中央に移動し、水素結合の破線は左右に分けた。
  配列2行・START/STOP・凡例・水素結合の本数は従来どおり。
- 再生成手順：`gen/make_dna_geometry.py` → `gen/rebuild_dna_board.py`（起点は `pre-compact-20261102/` の配線済み基板）
  → `gen/route_prep.py`（--swapは付けない）→ `gen/route_board.py` → `gen/route_apply.py`。
  寸法は環境変数 `DNA_D / DNA_P / DNA_A / DNA_RAIL / DNA_RUNG` で変えられる。Shapelyは `gen/_deps/py313`（通常Python）と `gen/_deps/py311`（KiCad付属Python、`DNA_DEPS`）。
- KiCad 9.0.4：DRC違反0、未接続0、回路図差異0（`wiring-drc.json`）。
- 更新前の状態：`pre-compact-20261102/`。`base-pairs.csv` の `base` 列は配列上の塩基で、シルクには出ていない。
- `../fusion/` の発注データは旧基板のまま。発注する場合は `gen/dump_assembly_data.py` → `gen/make_fusion_package.py` を再実行すること。
