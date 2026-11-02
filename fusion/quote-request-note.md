# Seeed Fusion 見積依頼メモ（XL-1010RGBC-WS2812B が BOM 照合で見つからない場合）

Seeed の手順では、BOM の型番が DigiKey/Mouser と自動照合できない部品でも、調達チームに見積を依頼できる（目安 1 営業日）。
カートに入れると依頼が自動で送られる。下の英文は、サポートへの問い合わせや注文時のコメント欄に貼る用。

## 英文（コピー用）

Subject: Sourcing request for XL-1010RGBC-WS2812B (PCBA order)

Hello,

The BOM line for XL-1010RGBC-WS2812B (XINGLIGHT, 24 pcs per board) was not matched automatically.
This is a 1.0 x 1.0 mm 4-pad addressable RGB LED (WS2812B-compatible driver inside).

- Manufacturer: XINGLIGHT
- MPN: XL-1010RGBC-WS2812B
- LCSC: C5349953  https://www.lcsc.com/product-detail/Light-Emitting-Diodes-LED_XINGLIGHT-XL-1010RGBC-WS2812B_C5349953.html
- Also listed as a marketplace item on DigiKey (XINGLIGHT XL-1010RGBC-WS2812B).

Could you please:
1. Quote this part from your procurement team (we only need about 24 pcs per board plus the usual overage; we cannot buy a full 4,000-pc reel).
2. Tell us if you need a datasheet, or if you would prefer to substitute another part. Please do not substitute without confirming with us first, because the pad layout and pin order (1 = DOUT, 2 = VDD, 3 = GND, 4 = DIN) are specific to this package.

Also, please let us know whether double-sided assembly with the XIAO nRF52840 module (Seeed SKU 102010448) on the bottom side is possible. The assembly drawing PDF is included in the Gerber zip.

Thank you.

## 代替品について

- 1010 サイズでピン順・パッドが同じ互換品は見つからなかった。2020（WS2812B-2020 など）や SK6805 系に替えると、フットプリント・ピン割り当て・配線（24 段のデータ線）の作り直しが必要になる。
- WS2812B-2020 のピン順は、検索で見つかったデータシートでは 1=DO、2=GND、3=DI、4=VDD。現在の 1=DOUT、2=VDD、3=GND、4=DIN とは違う。
- 見積の返事が「調達できない」だった場合に、代替品への設計変更を検討する。
