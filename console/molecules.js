// Skeletal structures of the four DNA bases, in Watson-Crick orientation, shared by the 2D cards and the 3D model.
// Units: 1 = C-C bond length (about 1.4 angstrom). x to the right, y downwards. Each base is drawn with its
// Watson-Crick edge on the right (x = +1); the partner base is mirrored to the other side of the pair.
// Ring atoms follow the standard numbering: pyrimidine N1 C2 N3 C4 C5 C6, purine N1 C2 N3 C4 C5 C6 N7 C8 N9.
(function () {
  "use strict";

  const H3 = Math.sqrt(3) / 2;
  const VERT = [[1, 0], [0.5, H3], [-0.5, H3], [-1, 0], [-0.5, -H3], [0.5, -H3]];   // 0..5 = angles 0,60,...,300 degrees (y down)
  const NH = 0.72, CH = 0.78;                                                         // N-H / C-H bond lengths in these units

  function mk() {
    const atoms = [], bonds = [], byId = {};
    return {
      atoms, bonds, byId,
      atom(id, el, x, y, z, extra) {
        const a = Object.assign({ id, el, x, y, z: z || 0 }, extra || {});
        atoms.push(a); byId[id] = a; return a;
      },
      bond(a, b, order) { bonds.push({ a, b, order: order || 1 }); },
    };
  }
  const dirOf = (deg) => [Math.cos(deg * Math.PI / 180), Math.sin(deg * Math.PI / 180)];

  // Build one base. kind: A | T | G | C.
  function build(kind) {
    const m = mk();
    const ring = (names, els) => names.forEach((n, i) => m.atom(n, els[i], VERT[i][0], VERT[i][1], 0, { ring: true }));
    const out = (from, id, el, deg, len, extra) => {                  // exocyclic atom along an outward direction
      const p = m.byId[from], d = dirOf(deg);
      return m.atom(id, el, p.x + d[0] * len, p.y + d[1] * len, 0, extra);
    };
    const hOn = (from, id, deg, len, extra) => out(from, id, "H", deg, len, extra);

    if (kind === "C" || kind === "T") {
      // vertex order 0..5 = N3, C2, N1, C6, C5, C4 (WC edge on the right: C4 upper right, N3 right, C2 lower right)
      ring(["N3", "C2", "N1", "C6", "C5", "C4"], ["N", "C", "N", "C", "C", "C"]);
      m.bond("N3", "C2"); m.bond("C2", "N1"); m.bond("N1", "C6"); m.bond("C6", "C5", 2); m.bond("C5", "C4"); m.bond("C4", "N3", kind === "C" ? 2 : 1);
      if (kind === "C") {
        // N3=C4 and C5=C6 are the double bonds; C2=O2 exocyclic
        out("C2", "O2", "O", 60, 1, { site: "bottom", role: "acceptor" }); m.bond("C2", "O2", 2);
        out("C4", "N4", "N", 300, 1, { site: "top" }); m.bond("C4", "N4");
        hOn("N4", "H41", 0, NH, { site: "top", role: "donor", hb: true }); m.bond("N4", "H41");
        hOn("N4", "H42", 240, NH); m.bond("N4", "H42");
        m.byId.N3.site = "mid"; m.byId.N3.role = "acceptor";
        hOn("C5", "H5", 240, CH); m.bond("C5", "H5");
        hOn("C6", "H6", 180, CH); m.bond("C6", "H6");
      } else {
        out("C2", "O2", "O", 60, 1); m.bond("C2", "O2", 2);
        out("C4", "O4", "O", 300, 1, { site: "top", role: "acceptor" }); m.bond("C4", "O4", 2);
        hOn("N3", "H3", 0, NH, { site: "mid", role: "donor", hb: true }); m.bond("N3", "H3");
        const me = out("C5", "C7", "C", 240, 1, { methyl: true }); m.bond("C5", "C7");
        // methyl hydrogens (tetrahedral, two of them out of the ring plane)
        const d = dirOf(240), p = [-d[1], d[0]];
        [90, 210, 330].forEach((phi, i) => {
          const c = Math.cos(phi * Math.PI / 180), s = Math.sin(phi * Math.PI / 180);
          m.atom("H7" + i, "H", me.x + CH * (0.333 * d[0] + 0.943 * c * p[0]), me.y + CH * (0.333 * d[1] + 0.943 * c * p[1]), CH * 0.943 * s);
          m.bond("C7", "H7" + i);
        });
        hOn("C6", "H6", 180, CH); m.bond("C6", "H6");
      }
      m.byId.N1.glyco = true;
      m.glycosidic = "N1";
    } else {
      // purine: vertex order 0..5 = N1, C2, N3, C4, C5, C6 (WC edge on the right: C6 upper right, N1 right, C2 lower right)
      // the six-ring is placed so that vertex 0 is N1 (right), 1 = C2 (lower right) ... 5 = C6 (upper right)
      ring(["N1", "C2", "N3", "C4", "C5", "C6"], ["N", "C", "N", "C", "C", "C"]);
      // imidazole fused on C4-C5 (the upper-left edge of the hexagon)
      const c4 = m.byId.C4, c5 = m.byId.C5;
      const mx = (c4.x + c5.x) / 2, my = (c4.y + c5.y) / 2, mn = Math.hypot(mx, my);
      const nx = mx / mn, ny = my / mn, apo = 0.688, R = 0.8507;
      const pc = [mx + nx * apo, my + ny * apo];
      const a4 = Math.atan2(c4.y - pc[1], c4.x - pc[0]), a5 = Math.atan2(c5.y - pc[1], c5.x - pc[0]);
      let step = a5 - a4; while (step > Math.PI) step -= 2 * Math.PI; while (step < -Math.PI) step += 2 * Math.PI;
      const at = (k) => [pc[0] + R * Math.cos(a5 + k * step), pc[1] + R * Math.sin(a5 + k * step)];
      const n7 = at(1), c8 = at(2), n9 = at(3);
      m.atom("N7", "N", n7[0], n7[1], 0, { ring: true });
      m.atom("C8", "C", c8[0], c8[1], 0, { ring: true });
      m.atom("N9", "N", n9[0], n9[1], 0, { ring: true, glyco: true });
      m.glycosidic = "N9";
      m.pent = pc;
      m.bond("N1", "C2"); m.bond("C2", "N3"); m.bond("N3", "C4"); m.bond("C4", "C5"); m.bond("C5", "C6"); m.bond("C6", "N1");
      m.bond("C5", "N7"); m.bond("N7", "C8"); m.bond("C8", "N9"); m.bond("N9", "C4");
      // H on C8 points away from the pentagon centre
      const hc8 = Math.atan2(c8[1] - pc[1], c8[0] - pc[0]) * 180 / Math.PI;
      hOn("C8", "H8", hc8, CH); m.bond("C8", "H8");
      if (kind === "A") {
        m.bond("N1", "C6", 2); m.bond("C2", "N3", 2); m.bond("C4", "C5", 2); m.bond("N7", "C8", 2);
        out("C6", "N6", "N", 300, 1, { site: "top" }); m.bond("C6", "N6");
        hOn("N6", "H61", 0, NH, { site: "top", role: "donor", hb: true }); m.bond("N6", "H61");
        hOn("N6", "H62", 240, NH); m.bond("N6", "H62");
        m.byId.N1.site = "mid"; m.byId.N1.role = "acceptor";
        hOn("C2", "H2", 60, CH); m.bond("C2", "H2");
      } else {
        m.bond("C2", "N3", 2); m.bond("C4", "C5", 2); m.bond("N7", "C8", 2);
        out("C6", "O6", "O", 300, 1, { site: "top", role: "acceptor" }); m.bond("C6", "O6", 2);
        hOn("N1", "H1", 0, NH, { site: "mid", role: "donor", hb: true }); m.bond("N1", "H1");
        out("C2", "N2", "N", 60, 1, { site: "bottom" }); m.bond("C2", "N2");
        hOn("N2", "H21", 0, NH, { site: "bottom", role: "donor", hb: true }); m.bond("N2", "H21");
        hOn("N2", "H22", 120, NH); m.bond("N2", "H22");
      }
    }
    // glycosidic N: where the deoxyribose is attached (outward from the ring system)
    const g = m.byId[m.glycosidic];
    const cx = m.pent ? m.pent[0] : 0, cy = m.pent ? m.pent[1] : 0;
    const ang = Math.atan2(g.y - cy, g.x - cx);
    m.sugar = [g.x + Math.cos(ang), g.y + Math.sin(ang)];
    m.kind = kind;
    // the generic ring bonds were added as single bonds first: keep one bond per atom pair, highest order
    const seen = {};
    m.bonds.forEach((b) => {
      const k = [b.a, b.b].sort().join("-");
      if (!seen[k] || seen[k].order < b.order) seen[k] = b;
    });
    m.bonds = Object.keys(seen).map((k) => seen[k]);
    return m;
  }

  const CACHE = {};
  const base = (k) => CACHE[k] || (CACHE[k] = build(k));

  // Hydrogen bonds of a pair, as [donorH atom on left/right, acceptor atom on the other side] ids
  const PAIR_BONDS = {
    // left base letter + right base letter: [[leftAtom, rightAtom], ...]
    AT: [["H61", "O4"], ["N1", "H3"]],
    TA: [["O4", "H61"], ["H3", "N1"]],
    GC: [["O6", "H41"], ["H1", "N3"], ["H21", "O2"]],
    CG: [["H41", "O6"], ["N3", "H1"], ["O2", "H21"]],
  };
  const PAIR_X0 = 4.1;                                              // distance between the two mirror centres (x of the right base = X0 - x)
  const complement = { A: "T", T: "A", G: "C", C: "G" };

  // ---- 2D rendering -------------------------------------------------------------------------------------
  const EL_COLOR = { C: "#4F4956", N: "#3B63B8", O: "#C0402E", H: "#8B8494" };

  function svgBase(kind, opts) {
    opts = opts || {};
    const m = base(kind);
    return pairSVG([{ m, mirror: false, dx: 0 }], [], opts, kind);
  }

  // groups: [{m, mirror, dx}] ; hbonds: [{from:[groupIdx, atomId], to:[groupIdx, atomId]}]
  function pairSVG(groups, hbonds, opts, title) {
    const L = opts.scale || 26, pad = 34;
    const pts = [];
    const tx = (g, a) => (g.mirror ? PAIR_X0 - a.x : a.x) + g.dx;
    groups.forEach((g) => { g.m.atoms.forEach((a) => pts.push([tx(g, a), a.y])); const s = g.m.sugar; pts.push([g.mirror ? PAIR_X0 - s[0] : s[0], s[1]]); });
    const minx = Math.min(...pts.map((p) => p[0])) - 1.2, maxx = Math.max(...pts.map((p) => p[0])) + 1.2;
    const miny = Math.min(...pts.map((p) => p[1])) - 1.2, maxy = Math.max(...pts.map((p) => p[1])) + 1.2;
    const W = (maxx - minx) * L, Hh = (maxy - miny) * L;
    const X = (x) => ((x - minx) * L).toFixed(1), Y = (y) => ((y - miny) * L).toFixed(1);
    const col = opts.colors || {};
    let s = `<svg class="mol" viewBox="0 0 ${W.toFixed(0)} ${Hh.toFixed(0)}" role="img" aria-label="${title || "塩基の構造"}">`;
    groups.forEach((g, gi) => {
      const tint = col[g.m.kind] || "#4F4956";
      const P = (a) => [tx(g, a), a.y];
      const atomPos = (id) => P(g.m.byId[id]);
      // fused ring fill
      const ringIds = g.m.atoms.filter((a) => a.ring).map((a) => a.id);
      const hexIds = g.m.kind === "A" || g.m.kind === "G" ? ["N1", "C2", "N3", "C4", "C5", "C6"] : ["N3", "C2", "N1", "C6", "C5", "C4"];
      const poly = (ids) => ids.map((id) => X(atomPos(id)[0]) + "," + Y(atomPos(id)[1])).join(" ");
      s += `<polygon points="${poly(hexIds)}" fill="${tint}" fill-opacity=".13" stroke="none"/>`;
      if (g.m.kind === "A" || g.m.kind === "G") s += `<polygon points="${poly(["C4", "C5", "N7", "C8", "N9"])}" fill="${tint}" fill-opacity=".13"/>`;
      // bonds
      g.m.bonds.forEach((b) => {
        const a = atomPos(b.a), c = atomPos(b.b);
        const A = g.m.byId[b.a], B = g.m.byId[b.b];
        const hasH = A.el === "H" || B.el === "H";
        if (hasH && !opts.allH && !(A.hb || B.hb)) return;     // hidden hydrogens would read as methyl stubs
        const ax = a[0], ay = a[1], bx = c[0], by = c[1];
        const line = (x1, y1, x2, y2, w) => `<line x1="${X(x1)}" y1="${Y(y1)}" x2="${X(x2)}" y2="${Y(y2)}" stroke="#4F4956" stroke-width="${w || 1.8}" stroke-linecap="round"/>`;
        if (b.order === 2) {
          const dx = bx - ax, dy = by - ay, n = Math.hypot(dx, dy), px = -dy / n, py = dx / n;
          const ringBond = A.ring && B.ring;
          if (ringBond) {
            // inner second line, shortened, towards the centre of the ring the bond belongs to
            const hexSet = g.m.kind === "A" || g.m.kind === "G" ? ["N1", "C2", "N3", "C4", "C5", "C6"] : ["N3", "C2", "N1", "C6", "C5", "C4"];
            const inHex = hexSet.indexOf(b.a) >= 0 && hexSet.indexOf(b.b) >= 0;
            const ctr = inHex ? [g.mirror ? PAIR_X0 : 0, 0] : [tx(g, { x: g.m.pent[0] }), g.m.pent[1]];
            const mx = (ax + bx) / 2, my = (ay + by) / 2;
            const side = ((ctr[0] - mx) * px + (ctr[1] - my) * py) >= 0 ? 1 : -1;
            const o = 0.17 * side, sh = 0.16;
            s += line(ax, ay, bx, by);
            s += line(ax + dx * sh + px * o, ay + dy * sh + py * o, bx - dx * sh + px * o, by - dy * sh + py * o, 1.5);
          } else {
            const o = 0.09;
            s += line(ax + px * o, ay + py * o, bx + px * o, by + py * o) + line(ax - px * o, ay - py * o, bx - px * o, by - py * o);
          }
        } else s += line(ax, ay, bx, by, hasH ? 1.4 : 1.8);
      });
      // atoms (labels for heteroatoms; carbons are vertices)
      g.m.atoms.forEach((a) => {
        if (a.el === "C" && !a.methyl) return;
        const p = P(a), r = a.el === "H" ? 0.34 : 0.43;
        const showH = a.el !== "H" || a.hb || opts.allH;
        if (!showH) return;
        const label = a.methyl ? "CH₃" : a.el;
        const fs = a.el === "H" ? 12 : a.methyl ? 12 : 15;
        s += `<g class="atom el-${a.el}" data-atom="${gi}:${a.id}"><circle cx="${X(p[0])}" cy="${Y(p[1])}" r="${(r * L).toFixed(1)}" fill="#FFFDF7" stroke="${a.el === "H" ? "#B4AEBB" : "none"}" stroke-width="1"/>` +
          `<text x="${X(p[0])}" y="${Y(p[1])}" font-size="${fs}" font-weight="700" text-anchor="middle" dominant-baseline="central" fill="${EL_COLOR[a.el]}">${label}</text></g>`;
      });
      // sugar attachment
      const gl = atomPos(g.m.glycosidic), sg = g.m.sugar;
      const sx = g.mirror ? PAIR_X0 - sg[0] : sg[0];
      s += `<line x1="${X(gl[0])}" y1="${Y(gl[1])}" x2="${X(sx)}" y2="${Y(sg[1])}" stroke="#4F4956" stroke-width="1.8"/>`;
      s += `<g class="sugar"><circle cx="${X(sx)}" cy="${Y(sg[1])}" r="${(0.55 * L).toFixed(1)}" fill="#F2EBD9" stroke="#A39CA8" stroke-width="1.4" stroke-dasharray="3 2"/>` +
        `<text x="${X(sx)}" y="${Y(sg[1])}" font-size="11" font-weight="700" text-anchor="middle" dominant-baseline="central" fill="#6E6776">糖</text></g>`;
    });
    // hydrogen bonds (dashed, animated)
    hbonds.forEach((hb, i) => {
      const ga = groups[hb.from[0]], gb = groups[hb.to[0]];
      const pa = ga.m.byId[hb.from[1]], pb = gb.m.byId[hb.to[1]];
      const ax = tx(ga, pa), bx = tx(gb, pb);
      // end the line at the atom circles
      const dx = bx - ax, dy = pb.y - pa.y, n = Math.hypot(dx, dy);
      const ra = (pa.el === "H" ? 0.34 : 0.43), rb = (pb.el === "H" ? 0.34 : 0.43);
      const x1 = ax + dx / n * ra, y1 = pa.y + dy / n * ra, x2 = bx - dx / n * rb, y2 = pb.y - dy / n * rb;
      s += `<line class="hbond" style="--i:${i}" x1="${X(x1)}" y1="${Y(y1)}" x2="${X(x2)}" y2="${Y(y2)}" stroke="#D77A95" stroke-width="2.6" stroke-linecap="round" stroke-dasharray="4 4"/>`;
    });
    return s + "</svg>";
  }

  function pairFigure(leftKind, opts) {
    const rightKind = complement[leftKind];
    const m1 = base(leftKind), m2 = base(rightKind);
    const key = leftKind + rightKind;
    const bonds = (PAIR_BONDS[key] || []).map((b) => ({ from: [0, b[0]], to: [1, b[1]] }));
    return pairSVG([{ m: m1, mirror: false, dx: 0 }, { m: m2, mirror: true, dx: 0 }], bonds, opts || {}, `${leftKind}-${rightKind} 塩基対`);
  }

  window.MOL = { base, svgBase, pairFigure, PAIR_BONDS, PAIR_X0, EL_COLOR, complement };
})();
