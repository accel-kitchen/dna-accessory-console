// 3D B-DNA model of the 12 base pairs on the board (three.js, ball-and-stick).
// Bases use the planar Watson-Crick geometry from molecules.js; the sugar-phosphate backbone follows an
// idealised B-DNA helix: 3.4 angstrom rise, 34.3 degree twist (10.5 bp per turn), phosphate radius 9 angstrom,
// minor groove about 130 degrees wide. Strand A runs 5' -> 3' upward, strand B is antiparallel.
import * as THREE from "three";

const MOL = window.MOL;
const L = 1.38, RISE = 3.4, TWIST = 34.3 * Math.PI / 180, DEG = Math.PI / 180;
const X0 = MOL.PAIR_X0;
const COMP = { A: "T", T: "A", G: "C", C: "G" };
const RADIUS = { C: 0.42, N: 0.40, O: 0.38, H: 0.24, P: 0.58 };
const BOND_R = 0.13;
const CPK = { C: "#A9B2C3", N: "#6C9BFF", O: "#FF6B5E", H: "#F1F1F4", P: "#F5B84A" };
const BACKBONE = { C: "#CDBFA4", O: "#E4705D", P: "#F2C95C" };

function buildModel(kinds) {
  const atoms = [], bonds = [], hbonds = [];
  const addAtom = (p, el, owner, ring) => { atoms.push({ p, el, owner, ring: !!ring }); return atoms.length - 1; };
  const addBond = (i, j, order, owner) => bonds.push({ i, j, order, owner });
  const sugar = [[], []], c3 = [[], []], c4 = [[], []];
  const pairInfo = [];

  for (let k = 0; k < kinds.length; k++) {
    const psi = k * TWIST;
    const eu = new THREE.Vector3(Math.cos(psi + 270 * DEG), Math.sin(psi + 270 * DEG), 0);
    const ev = new THREE.Vector3(Math.cos(psi + 180 * DEG), Math.sin(psi + 180 * DEG), 0);
    const kinL = kinds[k], kinR = COMP[kinds[k]];
    const left = MOL.base(kinL), right = MOL.base(kinR);
    const sl = left.sugar, sr = [X0 - right.sugar[0], right.sugar[1]];
    const xc = (sl[0] + sr[0]) / 2;
    const world = (x, y, z) => {
      const v = new THREE.Vector3().addScaledVector(eu, (x - xc) * L).addScaledVector(ev, y * L);
      v.z = k * RISE + (z || 0) * L;
      return v;
    };
    const idx = [{}, {}];
    [[left, false, 0], [right, true, 1]].forEach(([m, mirror, s]) => {
      const owner = k * 2 + s;
      m.atoms.forEach((a) => { idx[s][a.id] = addAtom(world(mirror ? X0 - a.x : a.x, a.y, a.z), a.el, owner, a.ring); });
      m.bonds.forEach((b) => addBond(idx[s][b.a], idx[s][b.b], b.order, owner));
      // C1' of the deoxyribose, one bond beyond the glycosidic nitrogen
      const sx = mirror ? X0 - m.sugar[0] : m.sugar[0];
      const c1 = addAtom(world(sx, m.sugar[1], 0), "C", -1);
      addBond(idx[s][m.glycosidic], c1, 1, -1);
      // deoxyribose ring in the (radial, axial) plane, C1' innermost; C3' on the 3' side of the strand
      const q = atoms[c1].p, rad = new THREE.Vector3(q.x, q.y, 0).normalize();
      const rho = 1.29, zs = s === 0 ? -1 : 1;
      const centre = q.clone().addScaledVector(rad, rho);
      const ring = [c1];
      const names = ["C", "C", "C", "C"];
      for (let i = 1; i < 5; i++) {
        const a = Math.PI + i * 72 * DEG;
        const p = centre.clone().addScaledVector(rad, rho * Math.cos(a));
        p.z += zs * rho * Math.sin(a);
        ring.push(addAtom(p, i === 4 ? "O" : names[i - 1], -1));
      }
      for (let i = 0; i < 5; i++) addBond(ring[i], ring[(i + 1) % 5], 1, -1);
      c3[s][k] = ring[2]; c4[s][k] = ring[3]; sugar[s][k] = ring[0];
    });
    // hydrogen bonds between the two bases
    (MOL.PAIR_BONDS[kinL + kinR] || []).forEach((b) => hbonds.push({ a: idx[0][b[0]], b: idx[1][b[1]], pair: k }));
    pairInfo.push({ eu, ev });
  }

  // phosphodiester linkages between neighbouring pairs
  for (let g = 0; g < kinds.length - 1; g++) {
    for (let s = 0; s < 2; s++) {
      const az = (g * TWIST + (g + 1) * TWIST) / 2 + (s === 0 ? 116 : 244) * DEG;
      const P = new THREE.Vector3(9 * Math.cos(az), 9 * Math.sin(az), (g + 0.5) * RISE);
      const i3 = s === 0 ? c3[0][g] : c3[1][g + 1];
      const j5 = s === 0 ? c4[0][g + 1] : c4[1][g];
      const pi = addAtom(P, "P", -1);
      const o3 = addAtom(atoms[i3].p.clone().lerp(P, 0.55), "O", -1);
      const c5p = atoms[j5].p.clone().lerp(P, 0.5);
      const c5 = addAtom(c5p, "C", -1);
      const o5 = addAtom(P.clone().lerp(c5p, 0.55), "O", -1);
      const rad = new THREE.Vector3(P.x, P.y, 0).normalize(), tan = new THREE.Vector3(-rad.y, rad.x, 0);
      const op1 = addAtom(P.clone().addScaledVector(rad.clone().addScaledVector(tan, 0.6).normalize(), 1.5), "O", -1);
      const op2 = addAtom(P.clone().addScaledVector(rad.clone().addScaledVector(tan, -0.6).normalize(), 1.5), "O", -1);
      addBond(i3, o3, 1, -1); addBond(o3, pi, 1, -1); addBond(pi, o5, 1, -1); addBond(o5, c5, 1, -1); addBond(c5, j5, 1, -1);
      addBond(pi, op1, 1, -1); addBond(pi, op2, 1, -1);
    }
  }
  // 5'/3' label anchors (strand A starts at the bottom, strand B ends there)
  const n = kinds.length;
  const anchor = (s, k, dz) => { const p = atoms[sugar[s][k]].p.clone(); const r = new THREE.Vector3(p.x, p.y, 0).normalize(); return p.addScaledVector(r, 3.2).add(new THREE.Vector3(0, 0, dz)); };
  const anchors = { a5: anchor(0, 0, -2.6), a3: anchor(0, n - 1, 2.6), b3: anchor(1, 0, -2.6), b5: anchor(1, n - 1, 2.6) };
  return { atoms, bonds, hbonds, anchors, pairInfo, n };
}

const Helix = (() => {
  let renderer, scene, camera, root, helixGroup, canvas, opts;
  let model = null, kinds = null, atomMesh, bondMesh, hbMesh, plates = [], glows = [], glowTex = null;
  let state = null, hover = -1, focusSet = new Set(), colorMode = "led";
  let rotY = 0.5, tilt = -0.08, velY = 0, auto = true, dragging = false, moved = 0, last = null;
  let dist = 90, targetDist = 90, camY = 0, targetCamY = 0, fitDist = 90, focusPair = -1;
  let raf = 0, visible = true, clock = performance.now();
  const tmp = new THREE.Object3D(), ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
  const Z = new THREE.Vector3(0, 0, 1), Y = new THREE.Vector3(0, 1, 0);

  function init(o) {
    opts = o; canvas = o.canvas;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
    } catch (e) { return false; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(30, 1, 1, 500);
    scene.add(new THREE.HemisphereLight(0xdde7ff, 0x1d1a35, 1.15));
    const key = new THREE.DirectionalLight(0xffffff, 2.6); key.position.set(-40, 60, 80); scene.add(key);
    const rim = new THREE.DirectionalLight(0x8fb6ff, 1.2); rim.position.set(50, -10, -70); scene.add(rim);
    root = new THREE.Group(); scene.add(root);
    helixGroup = new THREE.Group(); helixGroup.rotation.x = -Math.PI / 2; root.add(helixGroup);
    bindPointer();
    new ResizeObserver(resize).observe(canvas.parentElement);
    document.addEventListener("visibilitychange", () => { visible = !document.hidden; });
    new IntersectionObserver((e) => { visible = e[0].isIntersecting; }).observe(canvas);
    resize();
    loop();
    return true;
  }

  function resize() {
    if (!renderer) return;
    const r = canvas.parentElement.getBoundingClientRect();
    const w = Math.max(120, r.width), h = Math.max(160, r.height);
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
    const halfH = 31, halfW = 17, t = Math.tan(camera.fov * DEG / 2);
    fitDist = Math.max(halfH / t, halfW / (t * camera.aspect));
    if (focusPair < 0) targetDist = fitDist;
    render();
  }

  function rebuild(newKinds) {
    kinds = newKinds.slice();
    model = buildModel(kinds);
    [atomMesh, bondMesh, hbMesh].forEach((m) => { if (m) { helixGroup.remove(m); m.geometry.dispose(); m.material.dispose(); } });
    glows.forEach((g) => { helixGroup.remove(g); g.material.dispose(); }); glows = [];
    plates.forEach((p) => { helixGroup.remove(p); p.geometry.dispose(); p.material.dispose(); });
    plates = [];
    const na = model.atoms.length;
    atomMesh = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 22, 16), new THREE.MeshStandardMaterial({ roughness: 0.32, metalness: 0.04 }), na);
    model.atoms.forEach((a, i) => { tmp.position.copy(a.p); tmp.scale.setScalar(RADIUS[a.el]); tmp.quaternion.identity(); tmp.updateMatrix(); atomMesh.setMatrixAt(i, tmp.matrix); atomMesh.setColorAt(i, new THREE.Color(1, 1, 1)); });
    helixGroup.add(atomMesh);

    // bonds (double bonds drawn as two thin sticks)
    const sticks = [];
    model.bonds.forEach((b) => {
      const pa = model.atoms[b.i].p, pb = model.atoms[b.j].p;
      if (b.order === 2) {
        const dir = pb.clone().sub(pa).normalize(), off = new THREE.Vector3().crossVectors(dir, Z).normalize().multiplyScalar(0.2);
        sticks.push({ a: pa.clone().add(off), b: pb.clone().add(off), r: 0.085, o: b });
        sticks.push({ a: pa.clone().sub(off), b: pb.clone().sub(off), r: 0.085, o: b });
      } else sticks.push({ a: pa, b: pb, r: BOND_R, o: b });
    });
    bondMesh = new THREE.InstancedMesh(new THREE.CylinderGeometry(1, 1, 1, 10, 1, true), new THREE.MeshStandardMaterial({ roughness: 0.5, metalness: 0.02 }), sticks.length);
    bondMesh.userData.sticks = sticks;
    sticks.forEach((s, i) => { setStick(bondMesh, i, s.a, s.b, s.r); bondMesh.setColorAt(i, new THREE.Color(1, 1, 1)); });
    helixGroup.add(bondMesh);

    // hydrogen bonds: three dashes each
    const dashes = [];
    model.hbonds.forEach((h) => {
      const pa = model.atoms[h.a].p, pb = model.atoms[h.b].p;
      for (let d = 0; d < 3; d++) {
        const t0 = (d + 0.12) / 3, t1 = (d + 0.7) / 3;
        dashes.push({ a: pa.clone().lerp(pb, t0), b: pa.clone().lerp(pb, t1), pair: h.pair });
      }
    });
    hbMesh = new THREE.InstancedMesh(new THREE.CylinderGeometry(1, 1, 1, 8, 1, true), new THREE.MeshBasicMaterial({ color: 0xffb3c6, transparent: true, opacity: 0.9 }), Math.max(1, dashes.length));
    hbMesh.userData.dashes = dashes;
    dashes.forEach((d, i) => setStick(hbMesh, i, d.a, d.b, 0.075));
    helixGroup.add(hbMesh);

    // glow sprites: one per half base, shown for lit LEDs
    if (!glowTex) {
      const cv = document.createElement("canvas"); cv.width = cv.height = 64;
      const g = cv.getContext("2d"), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
      gr.addColorStop(0, "rgba(255,255,255,.95)"); gr.addColorStop(0.35, "rgba(255,255,255,.35)"); gr.addColorStop(1, "rgba(255,255,255,0)");
      g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
      glowTex = new THREE.CanvasTexture(cv);
    }
    for (let o = 0; o < kinds.length * 2; o++) {
      const c = new THREE.Vector3(); let n = 0;
      model.atoms.forEach((a) => { if (a.owner === o && a.ring) { c.add(a.p); n++; } });
      c.multiplyScalar(1 / Math.max(1, n));
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false, opacity: 0.0 }));
      sp.position.copy(c); sp.scale.setScalar(8.5); sp.renderOrder = 5;
      helixGroup.add(sp); glows.push(sp);
    }

    // invisible pick plates, one per pair
    for (let k = 0; k < kinds.length; k++) {
      const m = new THREE.Mesh(new THREE.CylinderGeometry(9.5, 9.5, 3.2, 28), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthWrite: false }));
      m.rotation.x = Math.PI / 2; m.position.set(0, 0, k * RISE); m.userData.pair = k;
      helixGroup.add(m); plates.push(m);
    }
    helixGroup.position.set(0, 0, 0);
    paint();
  }

  function setStick(mesh, i, a, b, r) {
    const dir = b.clone().sub(a), len = dir.length();
    tmp.position.copy(a).addScaledVector(dir, 0.5);
    tmp.quaternion.setFromUnitVectors(Y, dir.normalize());
    tmp.scale.set(r, len, r);
    tmp.updateMatrix();
    mesh.setMatrixAt(i, tmp.matrix);
  }

  // colours for the current state
  function paint() {
    if (!model || !state) return;
    const col = new THREE.Color();
    const dimBase = new THREE.Color("#2A3354");
    const owners = kinds.length * 2;
    const ownerCol = [], ownerLit = [];
    for (let k = 0; k < kinds.length; k++) for (let s = 0; s < 2; s++) {
      const half = state[s === 0 ? "a" : "b"][k];
      const o = k * 2 + s, focus = focusSet.size === 0 || focusSet.has(k);
      const ident = new THREE.Color(half.ident);
      const c = half.lit ? new THREE.Color(half.rgb[0] / 255, half.rgb[1] / 255, half.rgb[2] / 255) : ident.clone().lerp(dimBase, 0.62);
      if (half.lit) c.lerp(new THREE.Color(1, 1, 1), 0.12);
      ownerCol[o] = c.multiplyScalar(focus ? 1 : 0.42);
      ownerLit[o] = half.lit && focus;
    }
    const focusOf = (o) => (o < 0 ? 1 : focusSet.size === 0 || focusSet.has(o >> 1) ? 1 : 0.55);
    model.atoms.forEach((a, i) => {
      if (colorMode === "cpk" || a.owner < 0) {
        col.set(colorMode === "cpk" ? (a.owner < 0 ? (a.el === "C" ? BACKBONE.C : CPK[a.el]) : CPK[a.el]) : (BACKBONE[a.el] || BACKBONE.C)).multiplyScalar(focusOf(a.owner));
      } else {
        col.copy(ownerCol[a.owner]);
        if (a.el === "H") col.lerp(new THREE.Color(1, 1, 1), 0.45);
        else if (a.el === "N") col.lerp(new THREE.Color(0.35, 0.5, 1), 0.18);
        else if (a.el === "O") col.lerp(new THREE.Color(1, 0.3, 0.25), 0.18);
      }
      atomMesh.setColorAt(i, col);
    });
    atomMesh.instanceColor.needsUpdate = true;
    bondMesh.userData.sticks.forEach((s, i) => {
      const o = s.o.owner;
      if (o < 0 || colorMode === "cpk") col.set("#8E97AD").multiplyScalar(focusOf(o)); else col.copy(ownerCol[o]).multiplyScalar(0.85);
      bondMesh.setColorAt(i, col);
    });
    bondMesh.instanceColor.needsUpdate = true;
    for (let o = 0; o < owners; o++) {
      glows[o].material.color.copy(ownerCol[o]);
      glows[o].material.opacity = ownerLit[o] ? 0.42 : 0;
    }
    render();
  }

  // ---- interaction ----------------------------------------------------------------------------------
  function pick(ev) {
    const r = canvas.getBoundingClientRect();
    ptr.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ptr, camera);
    const hit = ray.intersectObjects(plates, false)[0];
    if (!hit) return null;
    const k = hit.object.userData.pair;
    const p = helixGroup.worldToLocal(hit.point.clone());
    const info = model.pairInfo[k];
    const side = (p.x * info.eu.x + p.y * info.eu.y) > 0 ? 1 : 0;
    return { pair: k, strand: side };
  }
  function bindPointer() {
    canvas.addEventListener("pointerdown", (e) => { dragging = true; moved = 0; last = [e.clientX, e.clientY]; velY = 0; canvas.setPointerCapture(e.pointerId); });
    canvas.addEventListener("pointermove", (e) => {
      if (dragging) {
        const dx = e.clientX - last[0], dy = e.clientY - last[1];
        moved += Math.abs(dx) + Math.abs(dy);
        rotY += dx * 0.011; velY = dx * 0.011; tilt = Math.max(-0.5, Math.min(0.5, tilt + dy * 0.004));
        last = [e.clientX, e.clientY];
      } else if (model) {
        const h = pick(e);
        const k = h ? h.pair : -1;
        if (k !== hover) { hover = k; opts.onHover && opts.onHover(h, e); }
        else if (h && opts.onMove) opts.onMove(h, e);
        canvas.style.cursor = h ? "pointer" : "grab";
      }
    });
    const up = (e) => {
      if (!dragging) return;
      dragging = false;
      if (moved < 5 && model) { const h = pick(e); if (h && opts.onClick) opts.onClick(h, e); }
    };
    canvas.addEventListener("pointerup", up);
    canvas.addEventListener("pointercancel", () => { dragging = false; });
    canvas.addEventListener("pointerleave", () => { if (hover !== -1) { hover = -1; opts.onHover && opts.onHover(null); } });
    canvas.addEventListener("wheel", (e) => { e.preventDefault(); targetDist = Math.max(fitDist * 0.35, Math.min(fitDist * 1.6, targetDist * (1 + e.deltaY * 0.0012))); }, { passive: false });
    canvas.addEventListener("dblclick", () => focus(-1));
  }

  function focus(k) {
    focusPair = k;
    if (k < 0) { targetDist = fitDist; targetCamY = 0; return; }
    targetDist = Math.max(fitDist * 0.78, 40);
    targetCamY = k * RISE - ((kinds.length - 1) * RISE) / 2;
  }

  // ---- render loop ------------------------------------------------------------------------------------
  function render() {
    if (!renderer || !kinds) return;
    root.rotation.y = rotY; root.rotation.x = tilt;
    const half = ((kinds.length - 1) * RISE) / 2;
    helixGroup.position.set(0, 0, 0);
    root.position.set(0, -camY * 0, 0);
    camera.position.set(0, camY, dist);
    camera.lookAt(0, camY, 0);
    // helix is centred by shifting its group down by half its height (z of the helix becomes y after rotation)
    helixGroup.position.y = -half;
    plates.forEach((p, k) => { p.material.opacity = k === hover ? 0.1 : focusSet.has(k) && focusSet.size < kinds.length ? 0.035 : 0; });
    renderer.render(scene, camera);
    placeLabels();
  }
  function placeLabels() {
    if (!opts.labels || !model) return;
    const r = canvas.getBoundingClientRect();
    const v = new THREE.Vector3();
    for (const key of ["a5", "a3", "b5", "b3"]) {
      const el = opts.labels[key]; if (!el) continue;
      v.copy(model.anchors[key]);
      helixGroup.localToWorld(v);
      v.project(camera);
      el.style.transform = `translate(${((v.x + 1) / 2 * r.width).toFixed(1)}px, ${((1 - v.y) / 2 * r.height).toFixed(1)}px) translate(-50%, -50%)`;
      el.style.opacity = v.z < 1 ? 1 : 0;
    }
  }
  function loop() {
    raf = requestAnimationFrame(loop);
    const now = performance.now(), dt = Math.min(0.05, (now - clock) / 1000); clock = now;
    if (!visible) return;
    if (!dragging) {
      if (Math.abs(velY) > 0.0004) { rotY += velY; velY *= 0.94; }
      else if (auto) rotY += dt * 0.28;
      tilt += (-0.08 - tilt) * Math.min(1, dt * 1.2) * (auto && !dragging ? 1 : 0);
    }
    dist += (targetDist - dist) * Math.min(1, dt * 6);
    camY += (targetCamY - camY) * Math.min(1, dt * 6);
    render();
  }

  return {
    init,
    resize,
    setAutoRotate(v) { auto = !!v; },
    setColorMode(m) { colorMode = m; paint(); },
    focusPair: focus,
    setHover(k) { hover = k; },
    // s: {kinds:[12 letters of strand A], a:[{rgb,lit,ident}], b:[...], focus:[pair indexes]}
    setState(s) {
      state = s;
      focusSet = new Set(s.focus || []);
      const key = s.kinds.join("");
      if (!kinds || kinds.join("") !== key) rebuild(s.kinds); else paint();
    },
    get ready() { return !!renderer; },
  };
})();

window.Helix = Helix;
window.dispatchEvent(new Event("helix-module"));
