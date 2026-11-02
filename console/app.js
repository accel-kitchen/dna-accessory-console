// DNA LED Console: board preview, codon learning panels, 3D model hook, Web Serial transport.
(function () {
  "use strict";
  const B = window.BOARD;
  const C = window.CODONS;
  const AM = window.AMINO;
  const MOL = window.MOL;
  const N_LEDS = 24, N_PAIRS = 12, N_CODONS = 4, MAX_FRAMES = 16;
  const NS = "http://www.w3.org/2000/svg";
  const $ = (id) => document.getElementById(id);

  // ---- state ---------------------------------------------------------------------------------
  // A frame is 24 cells. Cell i = pixel i (pair i>>1, strand A when even / B when odd).
  // A cell is "A" | "T" | "G" | "C" (coloured by the palette), "-" (off) or "#rrggbb".
  const DEFAULT_PALETTE = { A: "#00ff00", T: "#ff0000", G: "#0000ff", C: "#ff8000" };

  function codonsToFrame(codons, complement) {
    const cells = [];
    for (let c = 0; c < N_CODONS; c++) {
      const codon = codons[c];
      for (let j = 0; j < 3; j++) {
        const b = codon ? codon[j] : null;
        cells.push(b || "-");
        cells.push(b && complement ? C.complement(b) : "-");
      }
    }
    return cells;
  }
  function defaultFrame(complement) {
    const seq = B.defaultSeq;
    return codonsToFrame([0, 1, 2, 3].map((c) => seq.slice(3 * c, 3 * c + 3)), complement);
  }

  const S = {
    frames: [defaultFrame(true)],
    cur: 0,
    hold: 1500, bri: 40, fx: 1, speed: 5,
    palette: Object.assign({}, DEFAULT_PALETTE),
    complement: true,
    text: "", textMode: "amino", textChoices: [],
    brush: "A", unit: "pair", customColor: "#ff00ff",
    autoSend: true,
    maxBri: 128,
    previewFx: false, autoRotate: true, colorMode: "led",
    sel: 0, selPos: 2,
  };
  const PERSIST_KEYS = ["frames", "cur", "hold", "bri", "fx", "speed", "palette", "complement", "text", "textMode", "textChoices", "brush", "unit", "customColor", "autoSend", "previewFx", "autoRotate", "colorMode", "sel", "selPos"];
  const V = { tab: "codon", hoverPair: -1, hoverCodon: null, trace: -1 };   // view-only state

  function loadSaved() {
    try {
      const raw = localStorage.getItem("dna-led-console-v1");
      if (raw) applyProject(JSON.parse(raw), true);
    } catch (e) { /* storage may be unavailable: start from defaults */ }
  }
  let persistTimer = null;
  function persist() {
    clearTimeout(persistTimer);
    persistTimer = setTimeout(() => {
      try {
        const o = {};
        PERSIST_KEYS.forEach((k) => (o[k] = S[k]));
        localStorage.setItem("dna-led-console-v1", JSON.stringify(o));
      } catch (e) { /* ignore */ }
    }, 300);
  }

  function validCell(c) { return typeof c === "string" && (/^[ATGC-]$/.test(c) || /^#[0-9a-fA-F]{6}$/.test(c)); }
  function applyProject(o, quiet) {
    if (!o || typeof o !== "object") throw new Error("形式が正しくありません");
    if (Array.isArray(o.frames) && o.frames.length && o.frames.length <= MAX_FRAMES &&
        o.frames.every((f) => Array.isArray(f) && f.length === N_LEDS && f.every(validCell))) S.frames = o.frames.map((f) => f.slice());
    else if (!quiet && o.frames) throw new Error("フレームの形式が正しくありません");
    const num = (v, lo, hi, d) => (Number.isFinite(v) ? Math.min(hi, Math.max(lo, Math.round(v))) : d);
    S.hold = num(o.hold, 200, 5000, S.hold);
    S.bri = num(o.bri, 0, 255, S.bri);
    S.fx = num(o.fx, 0, 4, S.fx);
    S.speed = num(o.speed, 1, 10, S.speed);
    S.cur = num(o.cur, 0, S.frames.length - 1, 0);
    S.sel = num(o.sel, 0, N_CODONS - 1, S.sel);
    S.selPos = num(o.selPos, 0, 2, S.selPos);
    if (o.palette && ["A", "T", "G", "C"].every((k) => /^#[0-9a-fA-F]{6}$/.test(o.palette[k]))) S.palette = Object.assign({}, o.palette);
    if (typeof o.complement === "boolean") S.complement = o.complement;
    if (typeof o.text === "string") S.text = o.text;
    if (o.textMode === "amino" || o.textMode === "ascii6") S.textMode = o.textMode;
    if (Array.isArray(o.textChoices)) S.textChoices = o.textChoices.filter(Number.isInteger);
    if (typeof o.brush === "string" && /^[ATGC]$|^off$|^color$/.test(o.brush)) S.brush = o.brush;
    if (["led", "pair", "codon"].includes(o.unit)) S.unit = o.unit;
    if (/^#[0-9a-fA-F]{6}$/.test(o.customColor || "")) S.customColor = o.customColor;
    if (typeof o.autoSend === "boolean") S.autoSend = o.autoSend;
    if (typeof o.previewFx === "boolean") S.previewFx = o.previewFx;
    if (typeof o.autoRotate === "boolean") S.autoRotate = o.autoRotate;
    if (o.colorMode === "led" || o.colorMode === "cpk") S.colorMode = o.colorMode;
  }

  const frame = () => S.frames[S.cur];

  // ---- colour helpers ------------------------------------------------------------------------
  function hexToRgb(h) { return [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)); }
  function rgbToHex(rgb) { return "#" + rgb.map((v) => v.toString(16).padStart(2, "0")).join(""); }
  function cellRgb(cell) {
    if (cell === "-") return [0, 0, 0];
    if (cell[0] === "#") return hexToRgb(cell);
    return hexToRgb(S.palette[cell]);
  }
  const frameHex = (f) => f.map((c) => cellRgb(c).map((v) => v.toString(16).padStart(2, "0")).join("")).join("").toUpperCase();

  function hexToCell(rgb) {            // read-back: map device colours back to base letters when they match
    if (rgb.every((v) => v === 0)) return "-";
    for (const k of ["A", "T", "G", "C"]) {
      const p = hexToRgb(S.palette[k]);
      if (p[0] === rgb[0] && p[1] === rgb[1] && p[2] === rgb[2]) return k;
    }
    return rgbToHex(rgb);
  }

  // The LED colour stays the single source of truth; the reading colour on paper is the same hue, toned down.
  function hueOf(hex) {
    const [r, g, b] = hexToRgb(hex).map((v) => v / 255);
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
    if (!d) return [0, 0];
    let h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
    return [(h * 60 + 360) % 360, d / (1 - Math.abs(mx + mn - 1))];
  }
  function applyUiColours() {
    ["A", "T", "G", "C"].forEach((k) => {
      const [h, s] = hueOf(S.palette[k]);
      const sat = s < 0.15 ? 0 : 56;
      document.documentElement.style.setProperty("--b-" + k, `hsl(${h.toFixed(0)} ${sat}% 44%)`);
      document.documentElement.style.setProperty("--b-" + k + "-pale", `hsl(${h.toFixed(0)} ${Math.round(sat * 0.9)}% 93%)`);
    });
  }
  const uiBaseHex = (k) => {
    const cs = getComputedStyle(document.documentElement).getPropertyValue("--b-" + k).trim();
    const m = /hsl\((\d+)\s+(\d+)%\s+(\d+)%\)/.exec(cs);
    if (!m) return "#888888";
    const h = +m[1], s = +m[2] / 100, l = +m[3] / 100;
    const a = s * Math.min(l, 1 - l);
    const f = (n) => { const kk = (n + h / 30) % 12; return l - a * Math.max(-1, Math.min(kk - 3, 9 - kk, 1)); };
    return rgbToHex([f(0), f(8), f(4)].map((v) => Math.round(v * 255)));
  };

  // ---- effect simulation (mirrors render() in dna_console.ino) ---------------------------------
  function simScales(fx, speed, now) {
    const s = new Array(N_LEDS).fill(255);
    const stepMs = 60 + (10 - speed) * 60;
    if (fx === 1) {
      const lit = Math.min(Math.floor(now / stepMs) % 16, N_PAIRS);
      for (let k = lit; k < N_PAIRS; k++) s[2 * k] = s[2 * k + 1] = 0;
    } else if (fx === 2) {
      const period = stepMs * 16;
      const v = 0.5 - 0.5 * Math.cos(2 * Math.PI * (now % period) / period);
      s.fill(Math.floor(20 + v * 235));
    } else if (fx === 3) {
      const period = stepMs * 24;
      const ph = (now % period) / period;
      for (let k = 0; k < N_PAIRS; k++) {
        const v = 0.5 + 0.5 * Math.sin(2 * Math.PI * (ph - k / N_PAIRS));
        s[2 * k] = s[2 * k + 1] = Math.floor(25 + v * 230);
      }
    } else if (fx === 4) {
      const c = Math.floor(now / (stepMs * 6)) % 4;
      for (let i = 0; i < N_LEDS; i++) s[i] = Math.floor(i / 6) === c ? 255 : 30;
    }
    return s;
  }

  // ---- helpers on codons -----------------------------------------------------------------------
  function slotCodon(f, c) {
    let s = "";
    for (let j = 0; j < 3; j++) {
      const cell = f[2 * (3 * c + j)];
      if (!/^[ATGC]$/.test(cell)) return null;
      s += cell;
    }
    return s;
  }
  function slotCodons(f) { return [0, 1, 2, 3].map((c) => slotCodon(f, c)); }
  function setSlot(c, codon) {
    const f = frame();
    for (let j = 0; j < 3; j++) {
      const b = codon ? codon[j] : null;
      f[2 * (3 * c + j)] = b || "-";
      f[2 * (3 * c + j) + 1] = b && S.complement ? C.complement(b) : "-";
    }
    changed();
  }
  const aaName = (aa) => (aa === "*" ? "終止コドン" : AM.AA[aa].ja);
  const el = (name, attrs, parent) => {
    const e = document.createElementNS(NS, name);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };

  // ---- board preview -------------------------------------------------------------------------
  const svg = $("board");
  const ledEls = [], pairHi = [], codLabels = [], codSel = [];
  function buildBoard() {
    svg.setAttribute("viewBox", "70 24 70 126");
    const defs = el("defs", {}, svg);
    const f = el("filter", { id: "blur", x: "-100%", y: "-100%", width: "300%", height: "300%" }, defs);
    el("feGaussianBlur", { stdDeviation: "1.6" }, f);
    el("path", { d: B.outer, class: "pcb", "fill-rule": "evenodd" }, svg);
    B.holes.forEach((d) => el("path", { d, class: "hole" }, svg));
    for (let c = 0; c < N_CODONS; c++) {
      const y0 = B.leds[6 * c].y - 4, y1 = B.leds[6 * c + 5].y + 4;
      codSel.push(el("rect", { x: 87, y: y0 + 0.6, width: 26, height: y1 - y0 - 1.2, rx: 3, class: "codsel", opacity: 0 }, svg));
    }
    for (let k = 0; k < N_PAIRS; k++) {
      const a = B.leds[2 * k], b = B.leds[2 * k + 1];
      pairHi.push(el("rect", { x: 88, y: a.y - 4.2, width: 24, height: 8.4, rx: 4.2, class: "pairhi", opacity: 0 }, svg));
      el("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, class: "trace" }, svg);
      const t = el("text", { x: 80, y: a.y + 0.9, class: "pairNo" }, svg);
      t.textContent = k + 1;
    }
    for (let c = 0; c < N_CODONS; c++) {
      const y0 = B.leds[6 * c].y - 4, y1 = B.leds[6 * c + 5].y + 4;
      el("path", { d: `M120 ${y0} h1.5 V${y1} h-1.5`, class: "brk" }, svg);
      const cy = (y0 + y1) / 2;
      const t0 = el("text", { x: 124, y: cy - 4.2, class: "cod2" }, svg);
      t0.textContent = `コドン${c + 1}`;
      const t1 = el("text", { x: 124, y: cy - 0.5, class: "cod" }, svg);
      const t2 = el("text", { x: 124, y: cy + 3.2, class: "cod2" }, svg);
      const hit = el("rect", { x: 118, y: y0, width: 22, height: y1 - y0, fill: "transparent", style: "cursor:pointer" }, svg);
      hit.addEventListener("click", () => selectSlot(c));
      codLabels.push([t1, t2]);
    }
    B.leds.forEach((l, i) => {
      const halo = el("circle", { cx: l.x, cy: l.y, r: 3.7, filter: "url(#blur)", class: "halo", opacity: 0 }, svg);
      const c = el("circle", { cx: l.x, cy: l.y, r: 3.1, class: "led", tabindex: 0, role: "button" }, svg);
      const tt = el("title", {}, c);
      tt.textContent = `${l.ref} / 鎖${l.strand} / 塩基対${l.pair + 1} / コドン${l.codon + 1}`;
      c.addEventListener("click", () => onLedClick(i));
      c.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onLedClick(i); } });
      c.addEventListener("mouseenter", () => { V.hoverPair = l.pair; helixHover(l.pair); });
      c.addEventListener("mouseleave", () => { V.hoverPair = -1; helixHover(-1); });
      ledEls.push({ halo, c });
    });
  }

  function currentFrameForView(now) {
    let f = frame();
    let scales = null;
    if (S.previewFx) {
      if (S.frames.length > 1) f = S.frames[Math.floor(now / S.hold) % S.frames.length];
      scales = simScales(S.fx, S.speed, now);
    }
    return { f, scales };
  }
  function updateBoard(now) {
    const { f, scales } = currentFrameForView(now);
    for (let i = 0; i < N_LEDS; i++) {
      const rgb = cellRgb(f[i]);
      const k = scales ? scales[i] / 255 : 1;
      const lit = rgb[0] + rgb[1] + rgb[2] > 0 && k > 0.02;
      const col = lit ? `rgb(${Math.round(rgb[0] * k)},${Math.round(rgb[1] * k)},${Math.round(rgb[2] * k)})` : "#0E1126";
      ledEls[i].c.setAttribute("fill", col);
      ledEls[i].halo.setAttribute("fill", col);
      ledEls[i].halo.setAttribute("opacity", lit ? 0.6 * k : 0);
    }
    for (let k = 0; k < N_PAIRS; k++) pairHi[k].setAttribute("opacity", k === V.hoverPair ? 1 : 0);
  }
  let lastHelixPush = 0;
  function loop(now) {
    updateBoard(now);
    if (S.previewFx && now - lastHelixPush > 60) { lastHelixPush = now; pushHelix(now); }
    requestAnimationFrame(loop);
  }

  // ---- 3D model hook ---------------------------------------------------------------------------
  function helixHover(k) { if (window.Helix && window.Helix.ready && window.Helix.setHover) window.Helix.setHover(k); }
  function focusedCodon() { return V.trace >= 0 ? V.trace : (V.tab === "codon" ? S.sel : -1); }
  function pushHelix(now) {
    const H = window.Helix;
    if (!H || !H.ready) return;
    const { f, scales } = currentFrameForView(now || 0);
    const kinds = [], a = [], b = [];
    for (let k = 0; k < N_PAIRS; k++) {
      const ca = f[2 * k], cb = f[2 * k + 1];
      const letter = /^[ATGC]$/.test(ca) ? ca : /^[ATGC]$/.test(cb) ? C.complement(cb) : B.defaultSeq[k];
      kinds.push(letter);
      const mk = (cell, kind, idx) => {
        const rgb = cellRgb(cell), s = scales ? scales[idx] / 255 : 1;
        return { rgb: rgb.map((v) => v * s), lit: rgb[0] + rgb[1] + rgb[2] > 0 && s > 0.05, ident: uiBaseHex(kind) };
      };
      a.push(mk(ca, letter, 2 * k));
      b.push(mk(cb, C.complement(letter), 2 * k + 1));
    }
    const fc = focusedCodon();
    H.setState({ kinds, a, b, focus: fc >= 0 ? [3 * fc, 3 * fc + 1, 3 * fc + 2] : [] });
  }
  function bindHelix() {
    const H = window.Helix;
    const fb = $("helixFallback");
    const tip = $("tip");
    const ok = H && H.init({
      canvas: $("helix"),
      labels: { a5: $("lbA5"), a3: $("lbA3"), b5: $("lbB5"), b3: $("lbB3") },
      onHover(h, ev) {
        if (!h) { tip.hidden = true; V.hoverPair = -1; return; }
        V.hoverPair = h.pair;
        showTip(h, ev);
      },
      onMove(h, ev) { showTip(h, ev); },
      onClick(h) {
        if (V.tab === "paint") paintLed(2 * h.pair + h.strand);
        else { S.selPos = h.pair % 3; selectSlot(Math.floor(h.pair / 3)); }
      },
    });
    if (!ok) { fb.hidden = false; fb.textContent = "3Dモデルを表示できません（WebGLが使えないか、three.js を読み込めませんでした）。基板プレビューと各種機能は使えます。"; $("helix").style.display = "none"; return; }
    fb.hidden = true;
    H.setAutoRotate(S.autoRotate); H.setColorMode(S.colorMode);
    pushHelix();
  }
  function showTip(h, ev) {
    const tip = $("tip"), f = frame();
    const k = h.pair, cell = f[2 * k + h.strand];
    const base = /^[ATGC]$/.test(cell) ? cell : "—";
    const r = $("helix").parentElement.getBoundingClientRect();
    const cod = slotCodon(f, Math.floor(k / 3));
    tip.hidden = false;
    tip.innerHTML = `<b>鎖${h.strand ? "B" : "A"} · 塩基対 ${k + 1}</b> · ${base}<br>コドン${Math.floor(k / 3) + 1}${cod ? "：" + cod : ""}`;
    tip.style.left = (ev.clientX - r.left) + "px";
    tip.style.top = (ev.clientY - r.top) + "px";
  }
  function whenHelix(fn) {
    if (window.Helix) fn(); else window.addEventListener("helix-module", fn, { once: true });
  }

  // ---- selection / board click -----------------------------------------------------------------
  function onLedClick(i) {
    if (V.tab === "paint") { paintLed(i); return; }
    const k = i >> 1;
    S.selPos = k % 3;
    selectSlot(Math.floor(k / 3));
  }
  function selectSlot(c) {
    S.sel = c;
    renderAll(true);
    persist();
    const H = window.Helix;
    if (H && H.ready) H.focusPair(3 * c + 1);
  }

  // ---- painting --------------------------------------------------------------------------------
  function setPair(f, k, strandBase, clickedStrand) {
    const me = 2 * k + clickedStrand, other = 2 * k + (1 - clickedStrand);
    f[me] = strandBase;
    if (/^[ATGC]$/.test(strandBase)) { if (S.complement) f[other] = C.complement(strandBase); }
    else f[other] = strandBase;
  }
  function paintLed(i) {
    const f = frame();
    const brushVal = S.brush === "off" ? "-" : S.brush === "color" ? S.customColor : S.brush;
    const k = i >> 1, strand = i & 1, c = Math.floor(k / 3);
    if (S.unit === "led") f[i] = brushVal;
    else if (S.unit === "pair") setPair(f, k, brushVal, strand);
    else for (let q = 3 * c; q < 3 * c + 3; q++) setPair(f, q, brushVal, strand);
    changed();
  }

  // ---- codon slots -----------------------------------------------------------------------------
  const slotEls = [];
  function buildSlots() {
    const wrap = $("slots");
    for (let c = 0; c < N_CODONS; c++) {
      const d = document.createElement("div");
      d.className = "slot";
      d.setAttribute("role", "button");
      d.tabIndex = 0;
      d.innerHTML = `<span class="n">${c + 1}</span><div class="tiles"></div><div class="aa"></div>
        <input type="text" maxlength="3" autocomplete="off" spellcheck="false" aria-label="コドン${c + 1}の塩基3文字">`;
      const input = d.querySelector("input");
      d.addEventListener("click", (e) => { if (e.target === input) return; selectSlot(c); });
      d.addEventListener("keydown", (e) => { if (e.target === d && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); selectSlot(c); } });
      input.addEventListener("focus", () => { if (S.sel !== c) selectSlot(c); });
      input.addEventListener("input", () => {
        const norm = C.normalizeCodon(input.value);
        input.classList.toggle("bad", input.value.length >= 3 && !norm);
        if (norm) { S.sel = c; setSlot(c, norm); }
      });
      input.addEventListener("blur", () => { input.classList.remove("bad"); renderSlots(); });
      wrap.appendChild(d);
      slotEls.push({ d, input, tiles: d.querySelector(".tiles"), aa: d.querySelector(".aa") });
    }
  }
  function renderSlots() {
    const f = frame();
    for (let c = 0; c < N_CODONS; c++) {
      const s = slotEls[c];
      s.d.setAttribute("aria-pressed", String(c === S.sel));
      const codon = slotCodon(f, c);
      if (document.activeElement !== s.input) s.input.value = codon || "";
      s.input.placeholder = "---";
      s.tiles.textContent = "";
      for (let j = 0; j < 3; j++) {
        const cell = f[2 * (3 * c + j)];
        const t = document.createElement("span");
        t.className = "btile" + (c === S.sel && j === S.selPos ? " pos-sel" : "");
        if (/^[ATGC]$/.test(cell)) { t.dataset.b = cell; t.textContent = cell; }
        else { t.classList.add("off"); t.textContent = cell === "-" ? "·" : "◆"; if (cell[0] === "#") { t.style.background = cell; t.style.color = "#fff"; t.classList.remove("off"); } }
        t.addEventListener("click", (e) => { e.stopPropagation(); S.selPos = j; selectSlot(c); });
        s.tiles.appendChild(t);
      }
      if (codon) {
        const aa = C.aaOf(codon);
        s.aa.innerHTML = `${aa === "*" ? "終止" : AM.AA[aa].ja}<small>${aa === "*" ? "Stop" : AM.AA[aa].three + " · " + aa}</small>`;
      } else {
        const any = [0, 1, 2].some((j) => f[2 * (3 * c + j)] !== "-" || f[2 * (3 * c + j) + 1] !== "-");
        s.aa.innerHTML = any ? "個別の色<small>コドンではありません</small>" : "消灯<small>入力か表から選べます</small>";
      }
      const lab = codLabels[c];
      lab[0].textContent = codon || "—";
      lab[1].textContent = codon ? (C.aaOf(codon) === "*" ? "Stop" : AM.AA[C.aaOf(codon)].ja) : "";
      codSel[c].setAttribute("opacity", c === focusedCodon() ? 1 : 0);
    }
  }

  // ---- inspector (learning card for the selected codon) -----------------------------------------
  const WATER_TEXT = {
    avoid: "水が苦手。水の中では逃げるように、仲間どうしで集まります。",
    swim: "水になじむ。水の中でもすいすい広がります。",
    charge: "電荷があるので、水の分子に引き寄せられます。",
    tiny: "とても小さいので、狭いところでも自由に動けます。",
    stiff: "輪の形で曲がりにくい。らせんの途中で向きを変えます。",
    bridge: "水になじみ、ふたり並ぶと S–S 結合でつながります。",
    stop: "アミノ酸ではなく「ここで終わり」の合図です。",
  };
  const PAIR_NAME = { A: "アデニン", T: "チミン", G: "グアニン", C: "シトシン" };
  const POS_NAME = ["1番目", "2番目", "3番目"];

  function kindOfChange(from, to) {
    if (from === to) return { cls: "silent", label: "同義（サイレント）" };
    if (to === "*") return { cls: "stop", label: "ナンセンス（早期終止）" };
    if (from === "*") return { cls: "miss", label: "終止が消える" };
    return { cls: "miss", label: "ミスセンス" };
  }

  function renderInspector() {
    const box = $("insp");
    const f = frame();
    const c = S.sel;
    const codon = slotCodon(f, c);
    $("inspTitle").textContent = `コドン${c + 1}`;
    if (!codon) {
      box.innerHTML = `<p class="lead">この枠は消灯中（または個別に塗った色）です。コドンを入れると、アミノ酸の性質や、1文字変えたときの変化がここに出ます。</p>
        <div class="row"><button class="small" type="button" data-set="ATG">ATG（開始コドン）を入れる</button><button class="small" type="button" data-set="TAA">TAA（終止コドン）を入れる</button><button class="small" type="button" data-set="GCA">GCA を入れる</button></div>`;
      box.querySelectorAll("[data-set]").forEach((b) => b.addEventListener("click", () => setSlot(c, b.dataset.set)));
      return;
    }
    const aa = C.aaOf(codon), A = AM.AA[aa], cls = AM.CLASSES[A.cls];
    const syn = C.AA_CODONS[aa];
    const water = A.water || "swim";
    const badge = (txt, col, bg) => `<span class="badge" style="color:${col};border-color:${col};background:${bg}">${txt}</span>`;
    let html = `<div class="aa-head"><div class="aa-fig">${AM.mascot(aa, { size: 104 })}</div><div>
      <div class="aa-name">${A.ja}<small>${A.en}${aa === "*" ? "" : " · " + A.three + " · " + aa}</small></div>
      <div>${badge(cls.label, cls.stroke, cls.fill)}${A.start ? badge("開始コドン", "#3C6B4B", "#E5EFE7") : ""}${badge(`同義コドン ${syn.length}個`, "#6E6776", "#F2EBD9")}</div>
      <div class="says">${A.says}</div></div></div>
      <p class="fact"><b>メモ：</b>${A.fact}</p>`;
    // water mini experiment + synonyms
    html += `<div class="lab"><div><h3>水に入れてみると</h3><div class="water"><div class="wv"></div><div class="mfig ${water}">${AM.mascot(aa, { size: 80, tail: false })}</div></div>
      <p class="labcap" style="margin-top:6px">${WATER_TEXT[water]}<br><span style="color:var(--ink-3)">${cls.note}。</span></p></div>
      <div><h3>同じアミノ酸になる仲間</h3><div class="syn">${syn.map((k) => `<button class="chipc" type="button" data-set="${k}" aria-pressed="${k === codon}">${k}</button>`).join("")}</div>
      <p class="labcap" style="margin-top:8px">${syn.length === 1 ? `<b>${codon}</b> だけが ${aaName(aa)} を指定します。1文字変わると、別のアミノ酸になります。` : `${syn.length}種類のコドンが同じ ${aaName(aa)} を指定します。これを「縮重」と呼びます。`}</p></div></div>`;
    // the three bases with their partners
    html += `<div><h3>3つの塩基と、相手の塩基</h3><div class="bases3">${[0, 1, 2].map((j) => {
      const b = codon[j], p = C.complement(b), n = b === "A" || b === "T" ? 2 : 3;
      return `<div class="bcard" role="button" tabindex="0" data-pos="${j}" aria-pressed="${j === S.selPos}"><span class="pos">${POS_NAME[j]}</span>${MOL.pairFigure(b, { colors: { A: "#3E9B5E", T: "#D2584A", G: "#4A6FC8", C: "#B97F10" } })}<div class="cap">${b}（${PAIR_NAME[b]}）— ${p}<small>水素結合 ${n} 本</small></div></div>`;
    }).join("")}</div></div>`;
    // mutation lab
    const pos = S.selPos;
    const alts = "ATGC".split("").filter((x) => x !== codon[pos]).map((x) => codon.slice(0, pos) + x + codon.slice(pos + 1));
    const kinds = alts.map((a2) => kindOfChange(aa, C.aaOf(a2)));
    const nSil = kinds.filter((k) => k.cls === "silent").length;
    html += `<div><h3>${POS_NAME[pos]}の塩基を1文字変えると？</h3><div class="mut">${alts.map((a2, i) => {
      const a2aa = C.aaOf(a2), k = kinds[i];
      return `<button class="mtile" type="button" data-set="${a2}"><div class="cod">${a2.slice(0, pos)}<i>${a2[pos]}</i>${a2.slice(pos + 1)}</div>${AM.mascot(a2aa, { size: 58, tail: false })}<div class="nm">${aaName(a2aa)}</div><span class="kind ${k.cls}">${k.label}</span></button>`;
    }).join("")}</div>
      <p class="labcap" style="margin-top:8px">${pos === 2
        ? `3番目の塩基は変わっても、同じアミノ酸になることが多い（ゆらぎ）。この3通りのうち、同義は <b>${nSil}通り</b>。`
        : `${POS_NAME[pos]}の塩基が変わると、アミノ酸も変わりやすい。この3通りのうち、同義は <b>${nSil}通り</b> だけ。`}
      タイルを押すと、基板と3Dモデルにも反映されます。</p></div>`;
    box.innerHTML = html;
    box.querySelectorAll("[data-set]").forEach((b) => b.addEventListener("click", () => setSlot(c, b.dataset.set)));
    box.querySelectorAll(".bcard").forEach((b) => {
      const pick = () => { S.selPos = +b.dataset.pos; renderAll(true); persist(); };
      b.addEventListener("click", pick);
      b.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
    });
  }

  // ---- genetic code wheel ----------------------------------------------------------------------
  let wheel = null;
  function buildWheel() {
    wheel = window.WHEEL.build($("wheel"), {
      onPick(codon) { setSlot(S.sel, codon); },
      onHover(codon) { V.hoverCodon = codon; wheel.update(wheelState()); },
    });
    $("legend").innerHTML = ["hydrophobic", "polar", "acidic", "basic", "special", "stop"].map((k) => `<span><i style="background:${AM.CLASSES[k].fill};border-color:${AM.CLASSES[k].stroke}"></i>${AM.CLASSES[k].label}</span>`).join("");
  }
  const wheelState = () => ({ slots: slotCodons(frame()), selected: S.sel, hover: V.hoverCodon });

  // ---- bases guide -----------------------------------------------------------------------------
  const BASE_FACTS = {
    A: { ja: "アデニン", kind: "プリン塩基（二重環）", note: "Tと水素結合2本でペアになる。エネルギー通貨のATPにも含まれる。" },
    T: { ja: "チミン", kind: "ピリミジン塩基（単環）", note: "Aと水素結合2本。メチル基（CH₃）をもつ。RNAではかわりにウラシル（U）が使われる。" },
    G: { ja: "グアニン", kind: "プリン塩基（二重環）", note: "Cと水素結合3本。G–Cが多いDNAは、熱でほどけにくい。" },
    C: { ja: "シトシン", kind: "ピリミジン塩基（単環）", note: "Gと水素結合3本でペアになる。" },
  };
  function buildGuide() {
    const colors = { A: "#3E9B5E", T: "#D2584A", G: "#4A6FC8", C: "#B97F10" };
    let h = "";
    ["A", "T", "G", "C"].forEach((k) => {
      const f = BASE_FACTS[k];
      h += `<div class="gcard"><h3><span class="big" style="color:var(--b-${k})">${k}</span>${f.ja}</h3><div class="tags"><span class="tag2">${f.kind}</span></div>${MOL.svgBase(k, { colors })}<p>${f.note}</p></div>`;
    });
    h += ["A", "G"].map((k) => `<div class="gcard" style="grid-column:1/-1"><h3><span class="big">${k}–${C.complement(k)}</span>水素結合 ${k === "A" ? 2 : 3} 本</h3>${MOL.pairFigure(k, { colors, scale: 30 })}<p>点線が水素結合です。「糖」と書いた丸は、骨格のデオキシリボースにつながる位置。大きいプリン塩基と小さいピリミジン塩基が組むので、どの塩基対も幅はほぼ同じになります。</p></div>`).join("");
    $("guide").innerHTML = h;
  }

  // ---- text -> codons --------------------------------------------------------------------------
  let converted = [];
  function convertText() {
    converted = Array.from(S.text).map((ch, i) => C.charToCodon(ch, S.textMode, S.textChoices[i] || 0));
  }
  function renderChips() {
    const wrap = $("chips");
    wrap.textContent = "";
    const limit = MAX_FRAMES * N_CODONS;
    converted.forEach((r, i) => {
      const chip = document.createElement("div");
      chip.className = "chip" + (r.kind !== "ok" ? " none" : "") + (i >= limit ? " over" : "") + ((i % N_CODONS === N_CODONS - 1) ? " group-end" : "");
      const ch = r.ch === " " ? "␣" : r.ch;
      chip.innerHTML = `<span class="c"></span><span class="k"></span><span class="a"></span>`;
      chip.querySelector(".c").textContent = ch;
      chip.querySelector(".k").textContent = r.codon || "···";
      chip.querySelector(".a").textContent = r.kind === "ok" ? (r.aa === "*" ? "Stop" : AM.AA[r.aa].ja) : r.note;
      if (r.kind === "ok" && r.options > 1) {
        chip.classList.add("cycle");
        chip.tabIndex = 0;
        chip.setAttribute("role", "button");
        chip.title = `同義コドン ${r.options} 種。クリックで切替`;
        const cycle = () => { S.textChoices[i] = (S.textChoices[i] || 0) + 1; convertText(); renderChips(); persist(); };
        chip.addEventListener("click", cycle);
        chip.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); cycle(); } });
      }
      wrap.appendChild(chip);
    });
    const n = converted.length;
    const frames = Math.min(MAX_FRAMES, Math.ceil(n / N_CODONS));
    const none = converted.filter((r) => r.kind === "none").length;
    let info = n ? `${n}文字 → ${frames}フレーム` : "文字を入力してください";
    if (n > limit) info += `（${limit}文字を超えた分は無視）`;
    if (none) info += ` / 対応なし ${none}文字は消灯`;
    $("textInfo").textContent = info;
    $("btnApplyText").disabled = !n;
  }
  function applyText() {
    const list = converted.slice(0, MAX_FRAMES * N_CODONS);
    if (!list.length) return;
    const frames = [];
    for (let i = 0; i < list.length; i += N_CODONS) {
      frames.push(codonsToFrame([0, 1, 2, 3].map((j) => (list[i + j] ? list[i + j].codon : null)), S.complement));
    }
    S.frames = frames;
    S.cur = 0;
    changed();
  }

  // ---- translation animation -------------------------------------------------------------------
  let trTimer = null;
  function stopTranslate(msg) {
    clearTimeout(trTimer); trTimer = null;
    V.trace = -1;
    $("btnTranslate").textContent = "読み取りを始める";
    if (msg != null) $("trInfo").textContent = msg;
    renderSlots(); pushHelix();
  }
  function renderRibbon(i, done) {
    const codons = slotCodons(frame());
    $("rib").innerHTML = codons.map((k, j) => `<span class="cd ${j === i ? "now" : j < i || done ? "done" : ""}">${k || "···"}</span>`).join('<span class="lbl">›</span>');
  }
  function startTranslate() {
    if (trTimer) { stopTranslate("止めました"); return; }
    const codons = slotCodons(frame());
    $("peptide").textContent = "";
    $("btnTranslate").textContent = "止める";
    let i = 0, beads = 0;
    const step = () => {
      if (i >= N_CODONS) { renderRibbon(-1, true); stopTranslate(`終了（${beads}個のアミノ酸）`); return; }
      const codon = codons[i];
      V.trace = i;
      renderRibbon(i, false); renderSlots(); pushHelix();
      const H = window.Helix; if (H && H.ready) H.focusPair(3 * i + 1);
      if (!codon) { stopTranslate("空の枠に来たので、ここで終了しました"); renderRibbon(i, false); return; }
      const aa = C.aaOf(codon);
      $("trInfo").textContent = `${codon} → ${aaName(aa)}`;
      const pep = $("peptide");
      if (aa === "*") {
        const done = document.createElement("div"); done.className = "bead";
        done.innerHTML = AM.mascot("*", { size: 68, tail: false }) + "<span>終止</span>";
        pep.appendChild(done);
        trTimer = setTimeout(() => { renderRibbon(-1, true); stopTranslate(`終止コドンで終了（${beads}個のアミノ酸）`); }, 1400);
        return;
      }
      if (beads) { const l = document.createElement("div"); l.className = "link"; pep.appendChild(l); }
      const bead = document.createElement("div"); bead.className = "bead";
      bead.innerHTML = AM.mascot(aa, { size: 68, tail: false }) + `<span>${AM.AA[aa].three}</span>`;
      pep.appendChild(bead);
      beads++; i++;
      trTimer = setTimeout(step, 1300);
    };
    step();
  }

  // ---- paint panel / frames / output UI --------------------------------------------------------
  function buildPaint() {
    const wrap = $("brushes");
    [["A", "A"], ["T", "T"], ["G", "G"], ["C", "C"], ["off", "消灯"], ["color", "任意色"]].forEach(([v, label]) => {
      const b = document.createElement("button");
      b.type = "button"; b.dataset.brush = v; b.setAttribute("role", "radio");
      if (/^[ATGC]$/.test(v)) b.innerHTML = `<span class="sw"></span>${label}`; else b.textContent = label;
      b.addEventListener("click", () => { S.brush = v; renderPaint(); persist(); });
      wrap.appendChild(b);
    });
    $("units").querySelectorAll("button").forEach((b) => {
      b.setAttribute("role", "radio");
      b.addEventListener("click", () => { S.unit = b.dataset.unit; renderPaint(); persist(); });
    });
    $("customColor").addEventListener("input", (e) => { S.customColor = e.target.value; S.brush = "color"; renderPaint(); persist(); });
    const pr = $("paletteRow");
    ["A", "T", "G", "C"].forEach((k) => {
      const lab = document.createElement("label");
      lab.innerHTML = `${k}<input type="color" aria-label="${k}の色">`;
      lab.querySelector("input").addEventListener("input", (e) => { S.palette[k] = e.target.value; applyUiColours(); changed(); });
      pr.appendChild(lab);
    });
  }
  function renderPaint() {
    $("brushes").querySelectorAll("button").forEach((b) => {
      b.setAttribute("aria-checked", String(b.dataset.brush === S.brush));
      if (/^[ATGC]$/.test(b.dataset.brush)) b.querySelector(".sw").style.background = S.palette[b.dataset.brush];
    });
    $("units").querySelectorAll("button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.unit === S.unit)));
    $("customColor").value = S.customColor;
    $("paletteRow").querySelectorAll("input").forEach((inp, i) => (inp.value = S.palette["ATGC"[i]]));
  }

  function thumbSvg(f) {
    let s = '<svg viewBox="0 0 96 16" aria-hidden="true">';
    for (let k = 0; k < N_PAIRS; k++) for (let st = 0; st < 2; st++) {
      const cell = f[2 * k + st];
      const fill = cell === "-" ? "#E8DFC8" : rgbToHex(cellRgb(cell));
      s += `<circle cx="${4 + k * 8}" cy="${4 + st * 8}" r="3" fill="${fill}"/>`;
    }
    return s + "</svg>";
  }
  function renderFrames() {
    const strip = $("frameStrip");
    strip.textContent = "";
    S.frames.forEach((f, i) => {
      const t = document.createElement("div");
      t.className = "thumb";
      t.tabIndex = 0;
      t.setAttribute("role", "button");
      t.setAttribute("aria-current", String(i === S.cur));
      const codons = slotCodons(f).map((k) => k || "···").join(" ");
      t.innerHTML = thumbSvg(f) + `<span>${i + 1}: ${codons}</span>`;
      const pick = () => { S.cur = i; renderAll(); persist(); };
      t.addEventListener("click", pick);
      t.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
      strip.appendChild(t);
    });
    $("frameCount").textContent = `${S.cur + 1} / ${S.frames.length}`;
    $("btnFrameAdd").disabled = S.frames.length >= MAX_FRAMES;
    $("btnFrameDup").disabled = S.frames.length >= MAX_FRAMES;
    $("btnFrameDel").disabled = S.frames.length <= 1;
    $("btnFrameLeft").disabled = S.cur === 0;
    $("btnFrameRight").disabled = S.cur === S.frames.length - 1;
  }
  function renderOutput() {
    const bri = $("bri");
    bri.max = String(S.maxBri);
    if (S.bri > S.maxBri) S.bri = S.maxBri;
    bri.value = S.bri;
    $("briOut").textContent = `${S.bri} / ${S.maxBri}`;
    $("fx").value = String(S.fx);
    $("speed").value = S.speed;
    $("speedOut").textContent = S.speed;
    $("hold").value = S.hold;
    $("holdOut").textContent = `${(S.hold / 1000).toFixed(1)} 秒`;
    $("autoSend").checked = S.autoSend;
    $("complement").checked = S.complement;
    $("fxPreview").checked = S.previewFx;
    $("autoRotate").checked = S.autoRotate;
    $("colorMode").value = S.colorMode;
    $("textInput").value = S.text;
    $("textMode").value = S.textMode;
  }

  // ---- tabs ------------------------------------------------------------------------------------
  function setTab(name) {
    V.tab = name;
    document.querySelectorAll(".tab").forEach((t) => t.setAttribute("aria-selected", String(t.id === "tab-" + name)));
    document.querySelectorAll(".tabpanel").forEach((p) => (p.hidden = p.id !== "p-" + name));
    renderSlots(); pushHelix();
  }
  function wireTabs() {
    const tabs = [...document.querySelectorAll(".tab")];
    tabs.forEach((t, i) => {
      t.addEventListener("click", () => setTab(t.id.slice(4)));
      t.addEventListener("keydown", (e) => {
        const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
        if (d) { const n = tabs[(i + d + tabs.length) % tabs.length]; n.focus(); setTab(n.id.slice(4)); }
      });
    });
  }

  function renderAll(light) {
    applyUiColours();
    renderSlots(); renderInspector(); renderPaint(); renderFrames(); renderOutput();
    if (!light) { convertText(); renderChips(); }
    if (wheel) wheel.update(wheelState());
    pushHelix();
  }
  function changed() {
    renderAll();
    persist();
    scheduleSend();
  }

  // ---- log -----------------------------------------------------------------------------------
  const logEl = $("log");
  function log(msg) {
    const t = new Date().toTimeString().slice(0, 8);
    logEl.textContent += `${t} ${msg}\n`;
    const lines = logEl.textContent.split("\n");
    if (lines.length > 300) logEl.textContent = lines.slice(-300).join("\n");
    logEl.scrollTop = logEl.scrollHeight;
  }
  function notice(msg) {
    const n = $("notice");
    n.hidden = !msg;
    n.textContent = msg || "";
  }

  // ---- Web Serial ----------------------------------------------------------------------------
  const Dev = { port: null, writer: null, reader: null, connected: false, queue: Promise.resolve(), waiter: null, buf: "", sent: {} };
  const enc = new TextEncoder();

  function setConn(on, label) {
    Dev.connected = on;
    const pill = $("connPill");
    pill.textContent = label || (on ? "接続中" : "未接続");
    pill.className = "pill" + (on ? " on" : "");
    $("btnConnect").textContent = on ? "切断" : "接続";
    ["btnSend", "btnSave", "btnRead", "btnTest"].forEach((id) => ($(id).disabled = !on));
  }

  function onLine(line) {
    if (!line) return;
    log("← " + line);
    if (Dev.waiter) Dev.waiter(line);
  }
  async function readLoop() {
    const dec = new TextDecoder();
    const reader = Dev.reader;
    try {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        Dev.buf += dec.decode(value, { stream: true });
        let idx;
        while ((idx = Dev.buf.indexOf("\n")) >= 0) {
          onLine(Dev.buf.slice(0, idx).replace(/\r$/, ""));
          Dev.buf = Dev.buf.slice(idx + 1);
        }
      }
    } catch (e) {
      log("受信エラー: " + e.message);
    }
    if (Dev.connected) await teardown("切断されました");
  }

  // Sends one line and resolves with the reply lines. Calls are serialised.
  function cmd(line, opts) {
    opts = opts || {};
    const run = () => new Promise(async (resolve, reject) => {
      if (!Dev.writer) return reject(new Error("未接続"));
      const lines = [];
      const timer = setTimeout(() => { Dev.waiter = null; reject(new Error("応答なし: " + line.slice(0, 20))); }, opts.timeout || 3000);
      Dev.waiter = (l) => {
        lines.push(l);
        const done = opts.until ? opts.until(l) : /^(OK|ERR)/.test(l);
        if (done) { clearTimeout(timer); Dev.waiter = null; resolve(lines); }
      };
      log("→ " + (line.length > 60 ? line.slice(0, 60) + "…" : line));
      try { await Dev.writer.write(enc.encode(line + "\n")); }
      catch (e) { clearTimeout(timer); Dev.waiter = null; reject(e); }
    });
    const p = Dev.queue.then(run);
    Dev.queue = p.catch(() => {});
    return p;
  }
  const lastOf = (lines) => lines[lines.length - 1] || "";

  async function connect() {
    if (!("serial" in navigator)) { notice("このブラウザはWeb Serialに対応していません。ChromeまたはEdgeで開いてください。"); return; }
    notice("");
    try {
      Dev.port = await navigator.serial.requestPort();
      await Dev.port.open({ baudRate: 115200 });
      Dev.writer = Dev.port.writable.getWriter();
      Dev.reader = Dev.port.readable.getReader();
      Dev.buf = ""; Dev.sent = {};
      readLoop();
      setConn(true, "接続処理中…");
      const hello = lastOf(await cmd("HELLO"));
      const m = /maxbri=(\d+)/.exec(hello);
      if (!/^OK DNA-LED/.test(hello)) throw new Error("DNA-LEDのファームウェアではありません: " + hello);
      if (m) S.maxBri = Math.min(255, parseInt(m[1], 10));
      const fs = /fs=(\d)/.exec(hello);
      setConn(true, "接続中");
      $("btnSave").disabled = fs ? fs[1] !== "1" : false;
      renderOutput();
      log("接続しました");
    } catch (e) {
      if (e && e.name === "NotFoundError") { log("ポートの選択がキャンセルされました"); }
      else { log("接続失敗: " + (e && e.message)); notice("接続できませんでした: " + (e && e.message)); }
      await teardown();
    }
  }
  async function teardown(msg) {
    const wasOn = Dev.connected;
    Dev.connected = false;
    try { if (Dev.reader) { await Dev.reader.cancel().catch(() => {}); Dev.reader.releaseLock(); } } catch (e) { /* ignore */ }
    try { if (Dev.writer) { Dev.writer.releaseLock(); } } catch (e) { /* ignore */ }
    try { if (Dev.port) await Dev.port.close(); } catch (e) { /* ignore */ }
    Dev.port = Dev.writer = Dev.reader = null;
    Dev.waiter = null;
    Dev.sent = {};
    setConn(false);
    if (wasOn && msg) log(msg);
  }

  // Sends only what changed since the last successful send.
  let sending = false, again = false, sendTimer = null;
  function scheduleSend() {
    if (!Dev.connected || !S.autoSend) return;
    clearTimeout(sendTimer);
    sendTimer = setTimeout(sendAll, 120);
  }
  async function sendAll(force) {
    if (!Dev.connected) return;
    if (sending) { again = true; return; }
    sending = true;
    try {
      if (force) Dev.sent = {};
      const send = async (key, line) => {
        if (Dev.sent[key] === line) return;
        const r = lastOf(await cmd(line));
        if (!/^OK/.test(r)) throw new Error(`${line.slice(0, 12)} → ${r}`);
        Dev.sent[key] = line;
        return r;
      };
      for (let i = 0; i < S.frames.length; i++) await send("F" + i, `F ${i} ${frameHex(S.frames[i])}`);
      await send("N", `N ${S.frames.length}`);
      await send("T", `T ${S.hold}`);
      const rb = await send("B", `B ${S.bri}`);
      if (rb) { const v = parseInt(rb.split(" ")[1], 10); if (Number.isFinite(v) && v !== S.bri) { S.bri = v; renderOutput(); log("明るさをファーム側の上限に丸めました"); } }
      await send("FX", `FX ${S.fx}`);
      await send("SP", `SP ${S.speed}`);
    } catch (e) {
      log("送信エラー: " + e.message);
      Dev.sent = {};
    } finally {
      sending = false;
      if (again) { again = false; scheduleSend(); }
    }
  }

  async function readBack() {
    try {
      const lines = await cmd("DUMP", { until: (l) => l === "END" || /^ERR/.test(l), timeout: 5000 });
      const frames = [];
      const o = {};
      for (const l of lines) {
        const p = l.split(" ");
        if (p[0] === "N") o.n = +p[1];
        else if (p[0] === "T") o.hold = +p[1];
        else if (p[0] === "B") o.bri = +p[1];
        else if (p[0] === "FX") o.fx = +p[1];
        else if (p[0] === "SP") o.speed = +p[1];
        else if (p[0] === "F" && p[2] && p[2].length === 144) {
          const cells = [];
          for (let i = 0; i < N_LEDS; i++) cells.push(hexToCell([0, 2, 4].map((j) => parseInt(p[2].slice(i * 6 + j, i * 6 + j + 2), 16))));
          frames[+p[1]] = cells;
        }
      }
      const got = frames.filter(Boolean);
      if (!got.length) throw new Error("機器から設定を読めませんでした");
      applyProject({ frames: got.slice(0, o.n || got.length), hold: o.hold, bri: o.bri, fx: o.fx, speed: o.speed, cur: 0 }, false);
      Dev.sent = {};
      S.frames.forEach((f, i) => (Dev.sent["F" + i] = `F ${i} ${frameHex(f)}`));
      Dev.sent.N = `N ${S.frames.length}`; Dev.sent.T = `T ${S.hold}`; Dev.sent.B = `B ${S.bri}`;
      Dev.sent.FX = `FX ${S.fx}`; Dev.sent.SP = `SP ${S.speed}`;
      renderAll(); persist();
      log("機器の設定を読み込みました");
    } catch (e) { log("読み戻しエラー: " + e.message); }
  }

  async function simple(line, okMsg) {
    try {
      const r = lastOf(await cmd(line, { timeout: 5000 }));
      log(/^OK/.test(r) ? okMsg : "失敗: " + r);
    } catch (e) { log("エラー: " + e.message); }
  }

  // ---- project file ----------------------------------------------------------------------------
  function exportJson() {
    const o = { app: "dna-led-console", version: 1 };
    PERSIST_KEYS.forEach((k) => (o[k] = S[k]));
    const blob = new Blob([JSON.stringify(o, null, 1)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "dna-led-pattern.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  async function importJson(file) {
    try {
      applyProject(JSON.parse(await file.text()), false);
      changed();
      log("JSONを読み込みました: " + file.name);
    } catch (e) { log("読込エラー: " + e.message); notice("読み込めませんでした: " + e.message); }
  }

  // ---- wiring ----------------------------------------------------------------------------------
  function wire() {
    $("btnConnect").addEventListener("click", () => (Dev.connected ? teardown("切断しました") : connect()));
    $("btnSend").addEventListener("click", () => sendAll(true));
    $("btnSave").addEventListener("click", async () => { await sendAll(true); await simple("SAVE", "フラッシュに保存しました"); });
    $("btnRead").addEventListener("click", readBack);
    $("btnTest").addEventListener("click", () => simple("TEST", "動作テスト完了（24個が順に点灯したか確認）"));

    $("textInput").addEventListener("input", (e) => { S.text = e.target.value; S.textChoices = []; convertText(); renderChips(); persist(); });
    $("textInput").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.isComposing) applyText(); });
    $("textMode").addEventListener("change", (e) => { S.textMode = e.target.value; S.textChoices = []; convertText(); renderChips(); persist(); });
    $("btnApplyText").addEventListener("click", applyText);
    $("btnTranslate").addEventListener("click", startTranslate);
    $("complement").addEventListener("change", (e) => { S.complement = e.target.checked; persist(); });
    $("fxPreview").addEventListener("change", (e) => { S.previewFx = e.target.checked; persist(); pushHelix(); });
    $("autoRotate").addEventListener("change", (e) => { S.autoRotate = e.target.checked; if (window.Helix && window.Helix.ready) window.Helix.setAutoRotate(S.autoRotate); persist(); });
    $("colorMode").addEventListener("change", (e) => { S.colorMode = e.target.value; if (window.Helix && window.Helix.ready) window.Helix.setColorMode(S.colorMode); persist(); });

    $("bri").addEventListener("input", (e) => { S.bri = +e.target.value; renderOutput(); persist(); scheduleSend(); });
    $("fx").addEventListener("change", (e) => { S.fx = +e.target.value; renderOutput(); persist(); scheduleSend(); });
    $("speed").addEventListener("input", (e) => { S.speed = +e.target.value; renderOutput(); persist(); scheduleSend(); });
    $("hold").addEventListener("input", (e) => { S.hold = +e.target.value; renderOutput(); persist(); scheduleSend(); });
    $("autoSend").addEventListener("change", (e) => { S.autoSend = e.target.checked; persist(); if (S.autoSend) scheduleSend(); });

    $("btnFrameAdd").addEventListener("click", () => { S.frames.splice(S.cur + 1, 0, new Array(N_LEDS).fill("-")); S.cur++; changed(); });
    $("btnFrameDup").addEventListener("click", () => { S.frames.splice(S.cur + 1, 0, frame().slice()); S.cur++; changed(); });
    $("btnFrameDel").addEventListener("click", () => { S.frames.splice(S.cur, 1); S.cur = Math.min(S.cur, S.frames.length - 1); changed(); });
    $("btnFrameLeft").addEventListener("click", () => { const i = S.cur; [S.frames[i - 1], S.frames[i]] = [S.frames[i], S.frames[i - 1]]; S.cur--; changed(); });
    $("btnFrameRight").addEventListener("click", () => { const i = S.cur; [S.frames[i + 1], S.frames[i]] = [S.frames[i], S.frames[i + 1]]; S.cur++; changed(); });
    $("btnClearFrame").addEventListener("click", () => { S.frames[S.cur] = new Array(N_LEDS).fill("-"); changed(); });
    $("btnDefault").addEventListener("click", () => { S.frames = [defaultFrame(S.complement)]; S.cur = 0; changed(); });

    $("btnExport").addEventListener("click", exportJson);
    $("btnImport").addEventListener("click", () => $("fileImport").click());
    $("fileImport").addEventListener("change", (e) => { const f = e.target.files[0]; if (f) importJson(f); e.target.value = ""; });

    if ("serial" in navigator) {
      navigator.serial.addEventListener("disconnect", () => { if (Dev.connected) teardown("USBが外れました"); });
    } else {
      notice("このブラウザはWeb Serialに対応していないため、機器には接続できません（画面での学習・プレビューは使えます）。ChromeまたはEdgeで開いてください。");
      $("btnConnect").disabled = true;
    }
  }

  // ---- start -----------------------------------------------------------------------------------
  loadSaved();
  applyUiColours();
  buildBoard();
  buildSlots();
  buildPaint();
  buildWheel();
  buildGuide();
  wireTabs();
  wire();
  setConn(false);
  convertText();
  renderChips();
  renderAll();
  requestAnimationFrame(loop);
  whenHelix(bindHelix);
  setTimeout(() => { if (!(window.Helix && window.Helix.ready)) { const fb = $("helixFallback"); if (!window.Helix) { fb.hidden = false; fb.textContent = "3Dモデルを読み込めませんでした（three.js をインターネットから取得できない可能性があります）。基板プレビューと各種機能は使えます。"; } } }, 12000);
  window.__dna = { S, V, C, Dev, cmd, frameHex, sendAll, readBack, paintLed, setSlot, selectSlot, setTab, startTranslate };   // debugging handle
})();
