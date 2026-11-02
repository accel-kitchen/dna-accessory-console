// Circular genetic-code chart. Rings from the centre: 1st base, 2nd base, 3rd base, amino acid (1-letter), amino acid name.
// Standard code (NCBI translation table 1), DNA alphabet (T instead of U).
(function () {
  "use strict";
  const NS = "http://www.w3.org/2000/svg";
  const C = window.CODONS, A = window.AMINO;
  const ORDER = "TCAG";
  const CX = 260, CY = 260;
  const RING = [[50, 92], [92, 134], [134, 170], [170, 208], [208, 248]];

  function pol(r, deg) {
    const a = (deg - 90) * Math.PI / 180;
    return [CX + r * Math.cos(a), CY + r * Math.sin(a)];
  }
  function arcPath(r0, r1, a0, a1) {
    const [x0, y0] = pol(r1, a0), [x1, y1] = pol(r1, a1), [x2, y2] = pol(r0, a1), [x3, y3] = pol(r0, a0);
    const big = a1 - a0 > 180 ? 1 : 0;
    return `M${x0.toFixed(2)} ${y0.toFixed(2)} A${r1} ${r1} 0 ${big} 1 ${x1.toFixed(2)} ${y1.toFixed(2)} L${x2.toFixed(2)} ${y2.toFixed(2)} A${r0} ${r0} 0 ${big} 0 ${x3.toFixed(2)} ${y3.toFixed(2)}Z`;
  }
  function el(name, attrs, parent, text) {
    const e = document.createElementNS(NS, name);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }

  function build(svg, handlers) {
    svg.textContent = "";
    svg.setAttribute("viewBox", "0 0 520 520");
    const cells = {};          // codon -> {path3, path4}
    const g = el("g", {}, svg);
    const baseFill = (b) => `var(--b-${b}-pale)`;
    const baseInk = (b) => `var(--b-${b})`;

    // ring 1 and 2 (decorative + shows grouping)
    for (let i = 0; i < 4; i++) {
      const a0 = i * 90, a1 = a0 + 90, b1 = ORDER[i];
      el("path", { d: arcPath(RING[0][0], RING[0][1], a0 + 0.3, a1 - 0.3), class: "w-r1", fill: baseFill(b1) }, g);
      const [tx, ty] = pol((RING[0][0] + RING[0][1]) / 2, a0 + 45);
      el("text", { x: tx, y: ty, class: "w-t1", fill: baseInk(b1) }, g, b1);
      for (let j = 0; j < 4; j++) {
        const s0 = a0 + j * 22.5, s1 = s0 + 22.5, b2 = ORDER[j];
        el("path", { d: arcPath(RING[1][0], RING[1][1], s0 + 0.25, s1 - 0.25), class: "w-r2", fill: baseFill(b2) }, g);
        const [ux, uy] = pol((RING[1][0] + RING[1][1]) / 2, s0 + 11.25);
        el("text", { x: ux, y: uy, class: "w-t2", fill: baseInk(b2) }, g, b2);
        // amino-acid name arcs: merge neighbouring codons of the same amino acid inside this block
        let run = [];
        const flush = () => {
          if (!run.length) return;
          const aa = run[0].aa, cls = A.AA[aa].cls;
          const r0 = run[0].a0, r1 = run[run.length - 1].a1;
          const d = el("path", { d: arcPath(RING[4][0], RING[4][1], r0 + 0.25, r1 - 0.25), class: "w-r5", fill: A.CLASSES[cls].fill, stroke: A.CLASSES[cls].stroke }, g);
          d.dataset.aa = aa;
          const mid = (r0 + r1) / 2, rr = (RING[4][0] + RING[4][1]) / 2;
          const [mx, my] = pol(rr, mid);
          const rot = mid > 90 && mid < 270 ? mid + 180 : mid;   // text follows the arc, never upside down
          const arcLen = (r1 - r0) * Math.PI / 180 * rr;
          const label = aa === "*" ? (arcLen < 40 ? "■" : "■ 終止") : arcLen < 40 ? aa : `${aa}・${A.AA[aa].three}`;
          el("text", { x: mx, y: my, class: "w-t5", fill: A.CLASSES[cls].ink, transform: `rotate(${rot.toFixed(1)} ${mx.toFixed(1)} ${my.toFixed(1)})` }, g, label);
          run = [];
        };
        for (let k = 0; k < 4; k++) {
          const b3 = ORDER[k], codon = b1 + b2 + b3, aa = C.CODON_TABLE[codon];
          const c0 = s0 + k * 5.625, c1 = c0 + 5.625, cls = A.AA[aa].cls;
          // ring 3: third base, ring 4: amino acid
          const p3 = el("path", { d: arcPath(RING[2][0], RING[2][1], c0 + 0.2, c1 - 0.2), class: "w-r3", fill: baseFill(b3), tabindex: 0, role: "button", "aria-label": `${codon} ${A.AA[aa].ja}` }, g);
          const [vx, vy] = pol((RING[2][0] + RING[2][1]) / 2, (c0 + c1) / 2);
          el("text", { x: vx, y: vy, class: "w-t3", fill: baseInk(b3) }, g, b3);
          const p4 = el("path", { d: arcPath(RING[3][0], RING[3][1], c0 + 0.2, c1 - 0.2), class: "w-r4", fill: A.CLASSES[cls].fill, stroke: A.CLASSES[cls].stroke, tabindex: 0, role: "button", "aria-label": `${codon} ${A.AA[aa].ja}` }, g);
          const [wx, wy] = pol((RING[3][0] + RING[3][1]) / 2, (c0 + c1) / 2);
          el("text", { x: wx, y: wy, class: "w-t4", fill: A.CLASSES[cls].ink }, g, aa === "*" ? "■" : aa);
          [p3, p4].forEach((p) => {
            el("title", {}, p, `${codon} → ${aa === "*" ? "終止" : aa + "（" + A.AA[aa].ja + "）"}`);
            p.dataset.codon = codon;
            p.addEventListener("click", () => handlers.onPick && handlers.onPick(codon));
            p.addEventListener("mouseenter", () => handlers.onHover && handlers.onHover(codon));
            p.addEventListener("mouseleave", () => handlers.onHover && handlers.onHover(null));
            p.addEventListener("focus", () => handlers.onHover && handlers.onHover(codon));
            p.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handlers.onPick && handlers.onPick(codon); } });
          });
          cells[codon] = { p3, p4 };
          if (run.length && run[0].aa !== aa) flush();
          run.push({ aa, a0: c0, a1: c1 });
        }
        flush();
      }
    }
    // centre: current codon
    const hole = el("g", { class: "w-hole" }, svg);
    el("circle", { cx: CX, cy: CY, r: 46, fill: "#FAF6EB", stroke: "#E8DFC8", "stroke-width": 1.5 }, hole);
    const ct = el("text", { x: CX, y: CY - 15, class: "w-centre" }, hole, "");
    const cl = el("text", { x: CX, y: CY + 6, class: "w-centre-letter" }, hole, "");
    const cs = el("text", { x: CX, y: CY + 27, class: "w-centre-sub" }, hole, "");
    // slot badges
    const badges = el("g", { class: "w-badges" }, svg);

    function update(state) {
      // state: {slots:[codon|null x4], selected:int, hover:codon|null}
      Object.keys(cells).forEach((k) => {
        cells[k].p3.classList.remove("on", "syn", "hov");
        cells[k].p4.classList.remove("on", "syn", "hov");
      });
      badges.textContent = "";
      const sel = state.slots[state.selected];
      if (sel) {
        const aa = C.CODON_TABLE[sel];
        C.AA_CODONS[aa].forEach((k) => { cells[k].p3.classList.add("syn"); cells[k].p4.classList.add("syn"); });
      }
      state.slots.forEach((codon, i) => {
        if (!codon) return;
        cells[codon].p3.classList.add("on"); cells[codon].p4.classList.add("on");
        const idx = C.allCodons().indexOf(codon);
        const m = ORDER.indexOf(codon[0]) * 16 + ORDER.indexOf(codon[1]) * 4 + ORDER.indexOf(codon[2]);
        const ang = (m + 0.5) * 5.625;
        const [bx, by] = pol(RING[4][1] + 3, ang);
        const bgd = el("g", { class: "w-badge" + (i === state.selected ? " sel" : "") }, badges);
        el("circle", { cx: bx, cy: by, r: 8.5 }, bgd);
        el("text", { x: bx, y: by + 0.5 }, bgd, String(i + 1));
      });
      const hv = state.hover || sel;
      if (state.hover && cells[state.hover]) { cells[state.hover].p3.classList.add("hov"); cells[state.hover].p4.classList.add("hov"); }
      if (hv) {
        const aa = C.CODON_TABLE[hv];
        ct.textContent = hv;
        cl.textContent = aa === "*" ? "■" : aa;
        cs.textContent = aa === "*" ? "終止コドン" : A.AA[aa].ja;
      } else { ct.textContent = ""; cl.textContent = ""; cs.textContent = ""; }
    }
    return { update };
  }

  window.WHEEL = { build };
})();
