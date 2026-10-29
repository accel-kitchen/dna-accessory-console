// DNA LED Console: board preview, codon / text editing, Web Serial transport.
(function () {
  "use strict";
  const B = window.BOARD;
  const C = window.CODONS;
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
    previewFx: false,
  };
  const PERSIST_KEYS = ["frames", "cur", "hold", "bri", "fx", "speed", "palette", "complement", "text", "textMode", "textChoices", "brush", "unit", "customColor", "autoSend", "previewFx"];

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

  // ---- board preview -------------------------------------------------------------------------
  const svg = $("board");
  const ledEls = [];
  const codonLabels = [];
  function el(name, attrs, parent) {
    const e = document.createElementNS(NS, name);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function buildBoard() {
    svg.setAttribute("viewBox", "60 24 80 126");
    const defs = el("defs", {}, svg);
    const f = el("filter", { id: "blur", x: "-100%", y: "-100%", width: "300%", height: "300%" }, defs);
    el("feGaussianBlur", { stdDeviation: "1.6" }, f);
    el("path", { d: B.outer, class: "outline", "fill-rule": "evenodd" }, svg);
    B.holes.forEach((d) => el("path", { d, class: "hole" }, svg));

    for (let k = 0; k < N_PAIRS; k++) {
      const a = B.leds[2 * k], b = B.leds[2 * k + 1];
      el("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, class: "link" }, svg);
      const t = el("text", { x: 78, y: a.y + 0.9, class: "pairNo" }, svg);
      t.textContent = k + 1;
    }
    // codon brackets and labels on the right
    for (let c = 0; c < N_CODONS; c++) {
      const y0 = B.leds[6 * c].y - 4, y1 = B.leds[6 * c + 5].y + 4;
      el("path", { d: `M120 ${y0} h1.5 V${y1} h-1.5`, class: "brk" }, svg);
      const cy = (y0 + y1) / 2;
      const t1 = el("text", { x: 124, y: cy - 0.5, class: "cod" }, svg);
      const t2 = el("text", { x: 124, y: cy + 3.2, class: "cod2" }, svg);
      const t0 = el("text", { x: 124, y: cy - 4.2, class: "cod2" }, svg);
      t0.textContent = `コドン${c + 1}`;
      codonLabels.push([t1, t2]);
    }
    const sa = el("text", { x: 105, y: 33.5, class: "strandLbl" }, svg); sa.textContent = "";
    B.leds.forEach((l, i) => {
      const halo = el("circle", { cx: l.x, cy: l.y, r: 3.6, filter: "url(#blur)", class: "halo", opacity: 0 }, svg);
      const c = el("circle", { cx: l.x, cy: l.y, r: 3.1, class: "led", tabindex: 0, role: "button" }, svg);
      const tt = el("title", {}, c);
      tt.textContent = `${l.ref} / 鎖${l.strand} / 塩基対${l.pair + 1} / コドン${l.codon + 1}`;
      c.addEventListener("click", () => paintLed(i));
      c.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); paintLed(i); } });
      const lt = el("text", { x: l.x, y: l.y + 0.2, class: "ltr" }, svg);
      ledEls.push({ halo, c, lt });
    });
  }

  function updateBoard(now) {
    let f = frame();
    let scales = null;
    if (S.previewFx) {
      if (S.frames.length > 1) f = S.frames[Math.floor(now / S.hold) % S.frames.length];
      scales = simScales(S.fx, S.speed, now);
    }
    for (let i = 0; i < N_LEDS; i++) {
      const rgb = cellRgb(f[i]);
      const k = scales ? scales[i] / 255 : 1;
      const lit = rgb[0] + rgb[1] + rgb[2] > 0 && k > 0.02;
      const col = lit ? `rgb(${Math.round(rgb[0] * k)},${Math.round(rgb[1] * k)},${Math.round(rgb[2] * k)})` : "#161d2c";
      ledEls[i].c.setAttribute("fill", col);
      ledEls[i].halo.setAttribute("fill", col);
      ledEls[i].halo.setAttribute("opacity", lit ? 0.55 * k : 0);
    }
  }
  function loop(now) { updateBoard(now); requestAnimationFrame(loop); }

  // ---- editing -------------------------------------------------------------------------------
  function setPair(f, k, strandBase, clickedStrand, keepOther) {
    // strandBase: base letter / "-" / "#hex" for the clicked LED; the other LED gets the complement if applicable.
    const me = 2 * k + clickedStrand, other = 2 * k + (1 - clickedStrand);
    f[me] = strandBase;
    if (/^[ATGC]$/.test(strandBase)) { if (S.complement) f[other] = C.complement(strandBase); }
    else if (!keepOther) f[other] = strandBase;
  }
  function paintLed(i) {
    const f = frame();
    const brushVal = S.brush === "off" ? "-" : S.brush === "color" ? S.customColor : S.brush;
    const k = i >> 1, strand = i & 1, c = Math.floor(k / 3);
    if (S.unit === "led") {
      f[i] = brushVal;
    } else if (S.unit === "pair") {
      setPair(f, k, brushVal, strand, false);
    } else {
      for (let q = 3 * c; q < 3 * c + 3; q++) setPair(f, q, brushVal, strand, false);
    }
    changed();
  }

  function slotCodon(f, c) {
    let s = "";
    for (let j = 0; j < 3; j++) {
      const cell = f[2 * (3 * c + j)];
      if (!/^[ATGC]$/.test(cell)) return null;
      s += cell;
    }
    return s;
  }
  function setSlot(c, codon) {
    const f = frame();
    for (let j = 0; j < 3; j++) {
      const b = codon ? codon[j] : null;
      f[2 * (3 * c + j)] = b || "-";
      f[2 * (3 * c + j) + 1] = b && S.complement ? C.complement(b) : "-";
    }
    changed();
  }

  // ---- codon slots UI ------------------------------------------------------------------------
  const slotEls = [];
  function buildSlots() {
    const wrap = $("slots");
    const codonsSorted = C.allCodons().sort((a, b) => {
      const x = C.aaOf(a), y = C.aaOf(b);
      return x === y ? a.localeCompare(b) : (x === "*" ? "~" : x).localeCompare(y === "*" ? "~" : y);
    });
    for (let c = 0; c < N_CODONS; c++) {
      const d = document.createElement("div");
      d.className = "slot";
      d.innerHTML = `<h3>コドン${c + 1}（対${3 * c + 1}–${3 * c + 3}）</h3>
        <div class="bases"><i></i><i></i><i></i></div>
        <input type="text" maxlength="3" inputmode="text" autocomplete="off" spellcheck="false" aria-label="コドン${c + 1}の塩基3文字">
        <select aria-label="コドン${c + 1}を一覧から選ぶ"></select>
        <p class="meta"></p>
        <button type="button">消灯</button>`;
      const input = d.querySelector("input");
      const sel = d.querySelector("select");
      sel.innerHTML = '<option value="">一覧から選ぶ…</option>' + codonsSorted.map((k) => {
        const aa = C.aaOf(k);
        return `<option value="${k}">${k} · ${aa === "*" ? "終止" : aa + " " + C.AA_NAMES[aa]}</option>`;
      }).join("");
      input.addEventListener("input", () => {
        const norm = C.normalizeCodon(input.value);
        input.classList.toggle("bad", input.value.length > 0 && !norm && input.value.length >= 3);
        if (norm) setSlot(c, norm);
      });
      input.addEventListener("blur", () => { input.classList.remove("bad"); renderSlots(); });
      sel.addEventListener("change", () => { if (sel.value) setSlot(c, sel.value); sel.value = ""; });
      d.querySelector("button").addEventListener("click", () => setSlot(c, null));
      wrap.appendChild(d);
      slotEls.push({ d, input, meta: d.querySelector(".meta"), bars: d.querySelectorAll(".bases i") });
    }
  }
  function renderSlots() {
    const f = frame();
    for (let c = 0; c < N_CODONS; c++) {
      const s = slotEls[c];
      const codon = slotCodon(f, c);
      if (document.activeElement !== s.input) s.input.value = codon || "";
      s.input.placeholder = "---";
      for (let j = 0; j < 3; j++) {
        const cell = f[2 * (3 * c + j)];
        s.bars[j].style.background = cell === "-" ? "#26324a" : rgbToHex(cellRgb(cell));
      }
      if (codon) {
        const aa = C.aaOf(codon);
        const comp = codon.split("").map(C.complement).join("");
        s.meta.innerHTML = `<b>${aa === "*" ? "終止コドン" : aa + " · " + C.AA_NAMES[aa]}</b><br>相補 ${comp}`;
      } else {
        const any = [0, 1, 2].some((j) => f[2 * (3 * c + j)] !== "-" || f[2 * (3 * c + j) + 1] !== "-");
        s.meta.textContent = any ? "個別に塗った色（コドンではありません）" : "消灯";
      }
      const lab = codonLabels[c];
      lab[0].textContent = codon || "—";
      lab[1].textContent = codon ? (C.aaOf(codon) === "*" ? "Stop" : C.AA_NAMES[C.aaOf(codon)]) : "";
    }
  }

  // ---- text -> codons ------------------------------------------------------------------------
  let converted = [];   // [{ch, codon, aa, kind, options, note}]
  function convertText() {
    const chars = Array.from(S.text);
    converted = chars.map((ch, i) => C.charToCodon(ch, S.textMode, S.textChoices[i] || 0));
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
      chip.querySelector(".a").textContent = r.kind === "ok" ? (r.aa === "*" ? "Stop" : C.AA_NAMES[r.aa]) : r.note;
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
      const codons = [0, 1, 2, 3].map((j) => (list[i + j] ? list[i + j].codon : null));
      frames.push(codonsToFrame(codons, S.complement));
    }
    S.frames = frames;
    S.cur = 0;
    changed();
  }

  // ---- paint panel / frames / output UI --------------------------------------------------------
  function buildPaint() {
    const wrap = $("brushes");
    const items = [["A", "A"], ["T", "T"], ["G", "G"], ["C", "C"], ["off", "消灯"], ["color", "任意色"]];
    items.forEach(([v, label]) => {
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
      lab.querySelector("input").addEventListener("input", (e) => { S.palette[k] = e.target.value; changed(); });
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
      const fill = cell === "-" ? "#26324a" : rgbToHex(cellRgb(cell));
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
      const codons = [0, 1, 2, 3].map((c) => slotCodon(f, c) || "···").join(" ");
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
    $("textInput").value = S.text;
    $("textMode").value = S.textMode;
  }

  function renderAll() {
    renderSlots(); renderPaint(); renderFrames(); renderOutput();
    convertText(); renderChips();
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
    pill.className = "pill " + (on ? "on" : "off");
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
    $("complement").addEventListener("change", (e) => { S.complement = e.target.checked; persist(); });
    $("fxPreview").addEventListener("change", (e) => { S.previewFx = e.target.checked; persist(); });

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
      notice("このブラウザはWeb Serialに対応していないため、機器には接続できません（プレビューのみ）。ChromeまたはEdgeで開いてください。");
      $("btnConnect").disabled = true;
    }
  }

  // ---- start -----------------------------------------------------------------------------------
  loadSaved();
  buildBoard();
  buildSlots();
  buildPaint();
  wire();
  setConn(false);
  renderAll();
  requestAnimationFrame(loop);
  window.__dna = { S, C, Dev, cmd, frameHex, sendAll, readBack };   // handy for debugging in the console
})();
