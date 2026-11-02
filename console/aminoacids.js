// Amino acid data and the small "character" drawings used in the learning cards.
// Facts are kept to well-documented ones; the genetic code itself comes from codons.js.
(function () {
  "use strict";

  const CLASSES = {
    hydrophobic: { label: "疎水性", note: "水になじまない側鎖。タンパク質の内側に集まりやすい", fill: "#FBEBC2", stroke: "#B58A1F", ink: "#7A5A0C" },
    polar:       { label: "極性（電荷なし）", note: "水になじむ側鎖。タンパク質の表面に出やすい", fill: "#DCEBF5", stroke: "#4F86AB", ink: "#2E5F80" },
    acidic:      { label: "酸性（−）", note: "マイナスに帯電する側鎖", fill: "#FBE4D8", stroke: "#C8654E", ink: "#A84A37" },
    basic:       { label: "塩基性（＋）", note: "プラスに帯電する側鎖", fill: "#ECE3F4", stroke: "#8A6FB0", ink: "#5E4688" },
    special:     { label: "特殊", note: "形や結合に特徴のある側鎖", fill: "#E5EFE7", stroke: "#5E9A70", ink: "#3C6B4B" },
    stop:        { label: "終止", note: "アミノ酸を指定せず、翻訳を終える合図", fill: "#E9E5EE", stroke: "#4F4956", ink: "#2A2730" },
  };

  // sc: side-chain glyph, water: behaviour in the mini experiment, face: mouth/eye variant
  const AA = {
    A: { three: "Ala", ja: "アラニン", en: "Alanine", cls: "hydrophobic", sc: "methyl", water: "avoid", face: 0,
      says: "いちばん素朴なぼく。しっぽはメチル基がひとつだけ。",
      fact: "側鎖がメチル基（CH₃）だけと小さく、タンパク質のらせん（αヘリックス）をつくりやすい。" },
    R: { three: "Arg", ja: "アルギニン", en: "Arginine", cls: "basic", sc: "guan", water: "charge", face: 1,
      says: "プラスの電荷をもつ引き寄せ上手。DNAのリン酸（マイナス）と仲良しだよ。",
      fact: "側鎖に正電荷をもつグアニジノ基がある。DNAが巻きつくヒストンには、ArgとLysが多い。" },
    N: { three: "Asn", ja: "アスパラギン", en: "Asparagine", cls: "polar", sc: "amide", water: "swim", face: 2,
      says: "水になじむアミド基のしっぽ。名前はアスパラガスから。",
      fact: "1806年にアスパラガスの搾り汁から見つかった、最初のアミノ酸。" },
    D: { three: "Asp", ja: "アスパラギン酸", en: "Aspartic acid", cls: "acidic", sc: "acid", water: "charge", face: 3,
      says: "マイナスのしっぽをもつ酸性チーム。酵素の働きどころによく呼ばれる。",
      fact: "グルタミン酸とならぶ酸性アミノ酸。酵素の活性中心で働くことが多い。" },
    C: { three: "Cys", ja: "システイン", en: "Cysteine", cls: "special", sc: "thiol", water: "bridge", face: 4,
      says: "しっぽの先に硫黄（S）。ふたり並ぶと S–S 結合で手をつなぐよ。",
      fact: "2つのCysがジスルフィド結合（S–S）でつながり、タンパク質を縫い留める。髪のケラチンにも多く、パーマはこの結合をつなぎ替える。" },
    Q: { three: "Gln", ja: "グルタミン", en: "Glutamine", cls: "polar", sc: "amide2", water: "swim", face: 0,
      says: "血液のなかでいちばん多い遊離アミノ酸。体のあちこちで活躍中。",
      fact: "血液中に最も多く含まれる遊離アミノ酸。" },
    E: { three: "Glu", ja: "グルタミン酸", en: "Glutamic acid", cls: "acidic", sc: "acid2", water: "charge", face: 1,
      says: "昆布のうま味の正体はぼく。",
      fact: "1908年、池田菊苗が昆布のだしからグルタミン酸を取り出し、「うま味」と名づけた。" },
    G: { three: "Gly", ja: "グリシン", en: "Glycine", cls: "special", sc: "hydrogen", water: "tiny", face: 2,
      says: "ぼくは最小。しっぽが水素だけだから、どんな形にも曲がれる。",
      fact: "側鎖が水素原子だけで最小。コラーゲンでは、Glyが3残基に1個くり返し現れる。" },
    H: { three: "His", ja: "ヒスチジン", en: "Histidine", cls: "basic", sc: "imid", water: "charge", face: 3,
      says: "プラスになったり、ならなかったり。中性のあたりで切り替わる器用もの。",
      fact: "側鎖のイミダゾール環は中性付近でプロトンを受け渡せるため、酵素の活性中心によく登場する。" },
    I: { three: "Ile", ja: "イソロイシン", en: "Isoleucine", cls: "hydrophobic", sc: "branch", water: "avoid", face: 4,
      says: "枝分かれのしっぽ。水が苦手で、タンパク質の内側にかくれがち。",
      fact: "ロイシン・バリンとならぶ分岐鎖アミノ酸（BCAA）。ヒトの体内ではつくれない必須アミノ酸。" },
    L: { three: "Leu", ja: "ロイシン", en: "Leucine", cls: "hydrophobic", sc: "branch", water: "avoid", face: 0,
      says: "タンパク質のなかでいちばんよく使われる、人気もの。",
      fact: "ヒトのタンパク質で最も多いアミノ酸。コドンは6種類ある。" },
    K: { three: "Lys", ja: "リシン", en: "Lysine", cls: "basic", sc: "amine", water: "charge", face: 1,
      says: "プラスのしっぽが長くのびた世話好き。ヒストンの上で目印がつく。",
      fact: "ヒストンのLysにアセチル基やメチル基がつくと、遺伝子のオン・オフが変わる。必須アミノ酸。" },
    M: { three: "Met", ja: "メチオニン", en: "Methionine", cls: "hydrophobic", sc: "sulfur", water: "avoid", face: 2, start: true,
      says: "ATGのぼく。タンパク質づくりの「よーいドン」を告げるよ。",
      fact: "AUG（DNAではATG）は開始コドンでもある。しっぽに硫黄をもつ必須アミノ酸。" },
    F: { three: "Phe", ja: "フェニルアラニン", en: "Phenylalanine", cls: "hydrophobic", sc: "ring6", water: "avoid", face: 3,
      says: "ベンゼン環のしっぽ。平べったくて、仲間と重なるのが好き。",
      fact: "必須アミノ酸。甘味料アスパルテームの材料のひとつでもある。" },
    P: { three: "Pro", ja: "プロリン", en: "Proline", cls: "special", sc: "ring5", water: "stiff", face: 4,
      says: "しっぽが骨格につながって輪になってる。折れ曲がりの名人。",
      fact: "側鎖が主鎖につながった環状構造で、らせんを折り曲げる「ヘリックスブレーカー」として働く。" },
    S: { three: "Ser", ja: "セリン", en: "Serine", cls: "polar", sc: "hydroxyl", water: "swim", face: 0,
      says: "OH のしっぽ。名前は絹（silk）から。",
      fact: "1865年に絹から見つかった。リン酸がつく（リン酸化される）と、タンパク質のスイッチになる。" },
    T: { three: "Thr", ja: "スレオニン", en: "Threonine", cls: "polar", sc: "hydroxyl2", water: "swim", face: 1,
      says: "OH のしっぽをもつ必須アミノ酸。セリンのいとこ。",
      fact: "必須アミノ酸。セリンと同じく、リン酸化されてスイッチになる。" },
    W: { three: "Trp", ja: "トリプトファン", en: "Tryptophan", cls: "hydrophobic", sc: "indole", water: "avoid", face: 2,
      says: "いちばん大柄。コドンはTGGただひとつ。",
      fact: "側鎖が最大のアミノ酸で、コドンも1種類だけ。体内でセロトニンやメラトニンの材料になる。" },
    Y: { three: "Tyr", ja: "チロシン", en: "Tyrosine", cls: "polar", sc: "phenol", water: "swim", face: 3,
      says: "ベンゼン環に OH がついたしっぽ。名前はギリシャ語のチーズから。",
      fact: "チーズのカゼインから見つかった。ドーパミンやアドレナリンの材料になる。" },
    V: { three: "Val", ja: "バリン", en: "Valine", cls: "hydrophobic", sc: "branch2", water: "avoid", face: 4,
      says: "分岐のしっぽ。たった1文字の違いで鎌状赤血球症にかかわる。",
      fact: "ヘモグロビンβ鎖の6番目がGluからValに変わると、鎌状赤血球症になる（GAG→GTG、1塩基の置換）。" },
    "*": { three: "Stop", ja: "終止", en: "Stop", cls: "stop", sc: "stop", water: "stop", face: 5,
      says: "ここでおしまい。TAA・TAG・TGA の3つがぼくの合図。",
      fact: "3つの終止コドンには名前がある：TAA は ochre、TAG は amber、TGA は opal。" },
  };

  function lighten(hex, f) {
    const n = parseInt(hex.slice(1), 16);
    const c = [n >> 16, (n >> 8) & 255, n & 255].map((v) => Math.round(v + (255 - v) * f));
    return "rgb(" + c.join(",") + ")";
  }

  // Side-chain glyph drawn as a small "tail" to the right of the body (coordinates in the 100 x 100 box).
  function sideChain(kind, s) {
    const st = `stroke="${s}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"`;
    const dot = (x, y, t, c) => `<circle cx="${x}" cy="${y}" r="6.5" fill="#fff" stroke="${c || s}" stroke-width="1.8"/><text x="${x}" y="${y + 0.5}" font-size="7.5" font-weight="700" text-anchor="middle" dominant-baseline="central" fill="${c || s}">${t}</text>`;
    const hexa = (cx, cy, r) => {
      let p = "";
      for (let i = 0; i < 6; i++) { const a = Math.PI / 6 + i * Math.PI / 3; p += (i ? "L" : "M") + (cx + r * Math.cos(a)).toFixed(1) + " " + (cy + r * Math.sin(a)).toFixed(1); }
      return p + "Z";
    };
    const pent = (cx, cy, r, rot) => {
      let p = "";
      for (let i = 0; i < 5; i++) { const a = rot + i * 2 * Math.PI / 5; p += (i ? "L" : "M") + (cx + r * Math.cos(a)).toFixed(1) + " " + (cy + r * Math.sin(a)).toFixed(1); }
      return p + "Z";
    };
    const tail = `<path d="M70 52 L80 52" ${st}/>`;
    switch (kind) {
      case "methyl": return tail + dot(87, 52, "CH₃");
      case "hydrogen": return `<path d="M72 52 L80 52" ${st}/>` + dot(86, 52, "H");
      case "branch": return `<path d="M70 52 L80 52 L88 42 M80 52 L88 62" ${st}/>` + dot(91, 40, "") + dot(91, 64, "");
      case "branch2": return `<path d="M70 52 L82 52 L90 44 M82 52 L90 60" ${st}/>` + dot(93, 42, "") + dot(93, 62, "");
      case "ring6": return tail + `<path d="${hexa(90, 52, 10)}" ${st}/><circle cx="90" cy="52" r="5" ${st}/>`;
      case "phenol": return tail + `<path d="${hexa(88, 52, 9)}" ${st}/><circle cx="88" cy="52" r="4.5" ${st}/>` + `<path d="M96 52 L99 52" ${st}/>` + dot(95, 36, "OH");
      case "indole": return tail + `<path d="${hexa(88, 56, 8)}" ${st}/><path d="${pent(84, 42, 7, -Math.PI / 2 + 0.3)}" ${st}/>`;
      case "ring5": return `<path d="${pent(86, 56, 9, -Math.PI / 2)}" ${st}/>` + `<path d="M70 52 L78 54" ${st}/>`;
      case "imid": return tail + `<path d="${pent(88, 52, 9, -Math.PI / 2)}" ${st}/>` + dot(88, 40, "N") ;
      case "sulfur": return tail + dot(87, 52, "S", "#A88A10") + `<path d="M94 52 L98 46" ${st}/>`;
      case "thiol": return tail + dot(87, 52, "SH", "#A88A10");
      case "hydroxyl": return tail + dot(87, 52, "OH", "#C0402E");
      case "hydroxyl2": return `<path d="M70 52 L80 52 L88 44 M80 52 L89 60" ${st}/>` + dot(92, 42, "OH", "#C0402E");
      case "amide": return `<path d="M70 52 L80 52 L88 46 M80 52 L88 60" ${st}/>` + dot(92, 42, "O", "#C0402E") + dot(92, 64, "NH₂", "#3B63B8");
      case "amide2": return `<path d="M70 52 L78 52 L84 46 L90 46 M90 46 L96 40 M90 46 L96 54" ${st}/>` + dot(98, 38, "O", "#C0402E") + dot(98, 56, "NH₂", "#3B63B8");
      case "acid": return `<path d="M70 52 L80 52 L88 46 M80 52 L88 60" ${st}/>` + dot(92, 42, "O⁻", "#C0402E") + dot(92, 64, "O", "#C0402E");
      case "acid2": return `<path d="M70 52 L76 52 L82 46 L90 46 M90 46 L96 40 M90 46 L96 54" ${st}/>` + dot(98, 38, "O⁻", "#C0402E") + dot(98, 58, "O", "#C0402E");
      case "amine": return `<path d="M70 52 L78 52 L84 46 L90 52" ${st}/>` + dot(93, 56, "NH₃⁺", "#3B63B8");
      case "guan": return `<path d="M70 52 L78 52 L84 46 L90 52" ${st}/>` + dot(93, 56, "N⁺", "#3B63B8") + dot(95, 38, "NH₂", "#3B63B8");
      default: return "";
    }
  }

  // Mouth / eyes per variant so that neighbours do not look identical.
  function face(v, ink) {
    const eyes = {
      0: `<circle cx="35" cy="48" r="3.6" fill="${ink}"/><circle cx="55" cy="48" r="3.6" fill="${ink}"/>`,
      1: `<path d="M31 49 Q35 44 39 49 M51 49 Q55 44 59 49" stroke="${ink}" stroke-width="2.6" fill="none" stroke-linecap="round"/>`,
      2: `<circle cx="35" cy="48" r="4.4" fill="#fff" stroke="${ink}" stroke-width="1.6"/><circle cx="36" cy="49" r="2.2" fill="${ink}"/><circle cx="55" cy="48" r="4.4" fill="#fff" stroke="${ink}" stroke-width="1.6"/><circle cx="56" cy="49" r="2.2" fill="${ink}"/>`,
      3: `<circle cx="35" cy="48" r="3.4" fill="${ink}"/><path d="M49 49 Q55 43 61 49" stroke="${ink}" stroke-width="2.6" fill="none" stroke-linecap="round"/>`,
      4: `<path d="M31 47 L39 50 M59 47 L51 50" stroke="${ink}" stroke-width="2.4" stroke-linecap="round"/><circle cx="35" cy="52" r="2.6" fill="${ink}"/><circle cx="55" cy="52" r="2.6" fill="${ink}"/>`,
      5: `<path d="M31 45 L39 53 M39 45 L31 53 M51 45 L59 53 M59 45 L51 53" stroke="${ink}" stroke-width="2.4" stroke-linecap="round"/>`,
    }[v % 6];
    const mouths = [
      `<path d="M38 60 Q45 67 52 60" stroke="${ink}" stroke-width="2.6" fill="none" stroke-linecap="round"/>`,
      `<path d="M40 60 Q45 64 50 60" stroke="${ink}" stroke-width="2.6" fill="none" stroke-linecap="round"/>`,
      `<ellipse cx="45" cy="62" rx="3.6" ry="4.2" fill="${ink}"/>`,
      `<path d="M38 62 Q41.5 58 45 62 Q48.5 66 52 62" stroke="${ink}" stroke-width="2.4" fill="none" stroke-linecap="round"/>`,
      `<path d="M39 61 L51 61" stroke="${ink}" stroke-width="2.6" stroke-linecap="round"/>`,
      `<path d="M38 64 Q45 58 52 64" stroke="${ink}" stroke-width="2.6" fill="none" stroke-linecap="round"/>`,
    ];
    return eyes + mouths[v % 6];
  }

  // Returns an SVG string. opts: {size, tail:boolean, label:boolean}
  function mascot(code, opts) {
    opts = opts || {};
    const a = AA[code];
    if (!a) return "";
    const c = CLASSES[a.cls];
    const size = opts.size || 96;
    let body;
    if (a.cls === "stop") {
      // octagon with a bar, like a stop sign
      let p = "";
      for (let i = 0; i < 8; i++) { const t = Math.PI / 8 + i * Math.PI / 4; p += (i ? "L" : "M") + (45 + 33 * Math.cos(t)).toFixed(1) + " " + (52 + 33 * Math.sin(t)).toFixed(1); }
      body = `<path d="${p}Z" fill="#fff" stroke="${c.stroke}" stroke-width="3"/><path d="${p}Z" fill="${c.fill}" transform="translate(45 52) scale(.82) translate(-45 -52)"/>`;
    } else {
      body = `<path d="M45 20 C66 19 79 33 78 52 C77 72 64 84 45 84 C26 84 13 72 13 52 C13 33 25 21 45 20Z" fill="${c.fill}" stroke="${c.stroke}" stroke-width="3"/>` +
        `<ellipse cx="33" cy="32" rx="9" ry="4.6" fill="#fff" opacity=".55" transform="rotate(-24 33 32)"/>`;
    }
    const cheeks = a.cls === "stop" ? "" : `<ellipse cx="26" cy="58" rx="4.6" ry="3" fill="${c.stroke}" opacity=".22"/><ellipse cx="64" cy="58" rx="4.6" ry="3" fill="${c.stroke}" opacity=".22"/>`;
    let hat = "";
    if (a.start) hat = `<path d="M45 22 L45 4" stroke="${c.ink}" stroke-width="2.4" stroke-linecap="round"/><path d="M45 4 L66 10 L45 17Z" fill="#5E9A70" stroke="#3C6B4B" stroke-width="1.6" stroke-linejoin="round"/>`;
    const charge = a.cls === "acidic" ? `<text x="18" y="30" font-size="15" font-weight="700" fill="${c.stroke}">−</text>` :
      a.cls === "basic" ? `<text x="16" y="31" font-size="15" font-weight="700" fill="${c.stroke}">＋</text>` : "";
    const stopTxt = a.cls === "stop" ? `<text x="45" y="38" font-size="9" font-weight="700" text-anchor="middle" fill="${c.ink}" letter-spacing="1">STOP</text>` : "";
    const tail = (opts.tail === false || a.cls === "stop") ? "" : sideChain(a.sc, c.stroke);
    const faceSvg = a.cls === "stop" ? `<g transform="translate(0 4)">${face(a.face, c.ink)}</g>` : face(a.face, c.ink);
    return `<svg class="mascot ${a.water ? "w-" + a.water : ""}" viewBox="0 0 108 100" width="${size * 1.08}" height="${size}" role="img" aria-label="${a.ja}（${a.three}）のキャラクター">` +
      `<g class="m-body">${hat}${body}${cheeks}${faceSvg}${charge}${stopTxt}</g><g class="m-tail">${tail}</g></svg>`;
  }

  window.AMINO = { AA, CLASSES, mascot, lighten, classOf: (code) => (AA[code] ? CLASSES[AA[code].cls] : null) };
})();
