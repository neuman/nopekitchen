// The configurator on the marketing page. Yours to edit.
//
// It reads assets/twin.json, which `nopekit site build` generates from
// model/kitchen.py (views/twin.py). Every cabinet position, every quantity and
// every layout answer in that file is the model's. This script draws them, looks
// options up, and adds the bill up. It is a what-if: only the RECORDED design is
// checked by nopekit's gates, and the page says so whenever you leave it.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { RectAreaLightUniformsLib } from "three/addons/lights/RectAreaLightUniformsLib.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { GTAOPass } from "three/addons/postprocessing/GTAOPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

const $ = (s, r = document) => r.querySelector(s);
const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) n.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kids.flat()) if (k != null) n.append(k);
  return n;
};
const usd = (n) => "$" + Math.round(n).toLocaleString("en-US");
const signed = (n) => (Math.abs(n) < 0.5 ? "same" : (n > 0 ? "+" : "−") + usd(Math.abs(n)));
const STORE = "edmonds-kitchen-config-v2";
const PRICE_KEY = { cab_line: "usd_lf", cab_install: "usd_lf", handles: "usd_each", counter: "usd_sqft",
  backsplash: "usd_sqft", sink: "usd", faucet: "usd", floor: "usd_sqft", floor_removal: "usd_sqft" };
const UNIT = { cab_line: "linear ft", cab_install: "linear ft", handles: "each", counter: "sq ft",
  backsplash: "sq ft", sink: "each", faucet: "each", floor: "sq ft", floor_removal: "sq ft" };
const BEGRIPA = { white: "#F4F4F0", yellow: "#F5D33B", "light blue": "#9CC4E4", "light red": "#EF6B6B", lilac: "#B79CE0" };
const BEGRIPA_MIX = ["yellow", "light blue", "light red", "lilac", "white"];     // "mixed": one colour after another along each run
const BEGRIPA_MIX_SW = "conic-gradient(" + BEGRIPA_MIX.map((n, i) => BEGRIPA[n] + " " + i * 72 + "deg " + (i + 1) * 72 + "deg").join(", ") + ")";
const BASIS = { seen: "seen online", tag: "store tag", estimate: "estimate" };

let T = null;          // twin.json
let S = null;          // the selection
let view = { people: "none", flow: false, doors: false, furniture: true, cam: "overview", begripa: "yellow" };

// ---------------------------------------------------------------- state
function recorded() {
  const r = T.recorded;
  return { fridge_at: r.fridge_at, pantry: r.pantry, island_len: r.island_len, island_top_d: r.island_top_d,
    island_aisle: r.island_aisle, prep_sink: r.prep_sink, microwave_at: r.microwave_at,
    cab_line: r.cab_line, lower_color: r.lower_color, upper_color: r.upper_color, handles: r.handles,
    cab_install: r.cab_install, counter: r.counter, backsplash: r.backsplash, sink: r.sink, faucet: r.faucet,
    floor: r.floor, floor_removal: r.floor_removal, managed_by: r.managed_by };
}
function normalise(s) {
  // keep a selection inside what the model offers
  if (s.island_len === 0) { s.prep_sink = false; s.island_top_d = 40; s.island_aisle = 48; if (s.microwave_at === "island") s.microwave_at = "counter"; }
  if (s.fridge_at === "alcove") { s.pantry = "open"; if (s.microwave_at === "pantry") s.microwave_at = "counter"; }
  const line = T.catalog.cab_line[s.cab_line];
  if (!line.lower.includes(s.lower_color)) s.lower_color = line.lower[0];
  if (!line.upper.includes(s.upper_color)) s.upper_color = line.upper[0];
  if (!line.handles.includes(s.handles)) s.handles = line.handles[0];
  return s;
}
const keyOf = (s) => [s.fridge_at, s.pantry, s.island_len, s.island_top_d, s.island_aisle, s.prep_sink ? 1 : 0, s.microwave_at].join("|");
const layoutOf = (s) => T.layouts[keyOf(s)];
const isRecorded = (s) => Object.entries(recorded()).every(([k, v]) => s[k] === v);

// ---------------------------------------------------------------- money
function bill(s) {
  const L = layoutOf(s), cat = T.catalog, m = T.money, lines = [];
  const add = (group, qty, label) => {
    const o = cat[group][s[group]], price = o[PRICE_KEY[group]];
    const ext = Math.round(qty * price * 100) / 100;
    if (ext > 0) lines.push({ group, label: label || o.label, qty, unit: UNIT[group], price, ext, vendor: o.vendor, url: o.url, basis: o.v });
  };
  add("cab_line", L.qty.cab_line);
  add("cab_install", L.qty.cab_install, "Cabinets: " + cat.cab_install[s.cab_install].label.toLowerCase());
  add("handles", L.qty.handles);
  add("counter", L.qty.counter, "Countertop, installed: " + cat.counter[s.counter].label);
  add("backsplash", L.qty.backsplash, "Backsplash, installed: " + cat.backsplash[s.backsplash].label);
  add("sink", 1); add("faucet", 1);
  for (const [ref, label, ext, vendor, url, basis] of L.fixed) if (!ref.startsWith("floor") && ref !== "baseboard") lines.push({ group: "work", label, ext, vendor, url, basis });
  add("floor", m.floor_order, "LVP: " + cat.floor[s.floor].label);
  for (const [ref, label, ext, vendor, url, basis] of L.fixed) if (ref.startsWith("floor") || ref === "baseboard") lines.push({ group: "floor_work", label, ext, vendor, url, basis });
  add("floor_removal", m.floor_area, "Old bamboo: " + cat.floor_removal[s.floor_removal].label.toLowerCase());
  const sub = lines.reduce((a, l) => a + l.ext, 0);
  const markup = sub * cat.managed_by[s.managed_by].markup;
  const cont = (sub + markup) * m.contingency;
  const tax = (sub + markup + cont) * m.tax;
  const total = sub + markup + cont + tax + m.permits;
  const floorGroups = ["floor", "floor_work", "floor_removal"];
  const floors = lines.filter((l) => floorGroups.includes(l.group)).reduce((a, l) => a + l.ext, 0);
  return { lines, sub, markup, cont, tax, permits: m.permits, total, floors, kitchen: sub - floors };
}
const totalWith = (patch) => bill(normalise({ ...S, ...patch })).total;

// ---------------------------------------------------------------- what-if checks
function checks(s) {
  const L = layoutOf(s), C = T.claims, line = T.catalog.cab_line[s.cab_line], b = bill(s), out = [];
  const row = (lens, id, ok, value, note) => out.push({ lens, id, ok, statement: C[id].statement, value, note });
  const lay = (lens, id, fmt) => { const c = L.checks[id]; if (c) row(lens, id, c.ok, fmt(c.value)); };
  row("Budget", "C1", b.total <= C.C1.limit, usd(b.total) + " of " + usd(C.C1.limit));
  lay("One cook, a weeknight", "C3", (v) => v.toFixed(1) + " ft longest (max 9)");
  lay("One cook, a weeknight", "C4", (v) => v.toFixed(1) + " ft in all (max 26)");
  lay("One cook, a weeknight", "C5", (v) => v + " in (min 42)");
  lay("One cook, a weeknight", "C7", (v) => v + " in (min 21)");
  lay("Several cooks, a holiday", "C6", (v) => v + " in (min 48)");
  lay("The children", "C8", (v) => v + " seats (min 2)");
  lay("The children", "C9", (v) => v + " in (min 15)");
  lay("The children", "C10", (v) => (v <= 0 ? Math.abs(v).toFixed(1) + " in inside reach" : v.toFixed(1) + " in above reach"));
  const unmet = [];
  if (!line.gloss) unmet.push("not high gloss (" + line.sheen + ")");
  if (s.lower_color === s.upper_color) unmet.push("one colour, not two");
  row("Gloss two-tone", "C11", unmet.length === 0, unmet.length ? unmet.join("; ") : "gloss, both colours offered");
  lay("Fits the room", "C12", (v) => v + " in off (max 0.25)");
  lay("Fits the room", "C13", (v) => v + " in (min 1)");
  lay("Fits the room", "C15", (v) => (v ? v + " overlapping: " + L.hits.slice(0, 2).map((p) => p.join(" / ")).join("; ") : "nothing overlaps"));
  lay("Fits the room", "C16", (v) => (v ? v + " blocked: " + L.blocked.slice(0, 2).map((p) => p[0].replace(":", " ") + " by " + p[1]).join("; ") : "all " + L.opens.length + " open"));
  lay("Several cooks, a holiday", "C17", (v) => v + " in narrowest (min 36)");
  const wear = T.catalog.floor[s.floor].wear;
  row("Floors", "C14", wear >= C.C14.limit, wear + " mil (min " + C.C14.limit + ")");
  const notes = [];
  if (line.integrated === "ask") notes.push("The integrated handle on this line is seen in one image only. Ask the maker before ordering (claim A4).");
  if (line.integrated === false) notes.push("This line has no integrated handle.");
  if (line.integrated === true && s.handles !== "integrated") notes.push("You chose added handles on a line that has an integrated one.");
  if (s.prep_sink) notes.push("The island sink needs a drain through the floor. A plumber must confirm it (claim A5).");
  if (!s.prep_sink && s.fridge_at === "hall") notes.push("Without an island sink the cook walks " + L.cleanup_ft + " ft from the refrigerator to the sink.");
  if (s.island_len > 0) notes.push("The island's seat edge is " + L.east_in + " in inside the post line. Check the dining table leaves 44 in behind the stools (claim P3).");
  { const f = T.catalog.faucet[s.faucet], top = 36 + f.h_in; if (top > 54) notes.push("The " + f.label.split(",")[0] + " stands " + f.h_in.toFixed(1) + " in tall, so its top is " + (top - 54).toFixed(1) + " in above the window sill and in front of the glass; " + (84 - top).toFixed(1) + " in under the window head."); }
  if (s.fridge_at === "hall" && s.pantry === "cabinets") notes.push("Pantry cabinets need the alcove to be at least 36 in wide. It has not been measured (claim A1).");
  return { rows: out, notes };
}

// ---------------------------------------------------------------- 3D
// Inches. Model frame (x east, y south, z up) maps to three.js (x, z, y).
const G = { scene: null, cam: null, ctl: null, renderer: null, composer: null, gtao: null, root: null, over: null, shell: null,
  walls: [], dirty: true, host: null, pmrem: null, roomEnv: null, env: null, cube: null, cubeRT: null, tex: {} };
const M = (x, y, z) => new THREE.Vector3(x, z, y);
const std = (hex, o = {}) => new THREE.MeshStandardMaterial({ color: new THREE.Color(hex), roughness: 0.8, metalness: 0, ...o });
function rng(seed) { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; }
function shade(hex, f) {
  const c = new THREE.Color(hex), h = {}; c.getHSL(h); c.setHSL(h.h, h.s, Math.min(1, Math.max(0, h.l * f)));
  return "#" + c.getHexString();
}
function canvasTex(w, h, draw, { repeat, srgb = true } = {}) {
  const c = document.createElement("canvas"); c.width = w; c.height = h; draw(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 16;
  if (repeat) t.repeat.set(repeat[0], repeat[1]);
  return t;
}
const cached = (key, make) => (G.tex[key] ||= make());

// ---- materials
function lacquer(hex, sheen) {
  const p = { gloss: [0.14, 1.0, 0.025], satin: [0.42, 0.3, 0.3], matt: [0.75, 0.0, 0.5] }[sheen] || [0.5, 0, 0.5];
  return new THREE.MeshPhysicalMaterial({ color: new THREE.Color(hex), roughness: p[0], clearcoat: p[1], clearcoatRoughness: p[2], metalness: 0, envMapIntensity: 1.0 });
}
function steelMat(dark) {
  const maps = cached("steel", () => {
    const r = rng(5);
    const rough = canvasTex(256, 256, (g, w, h) => {
      g.fillStyle = "#7a7a7a"; g.fillRect(0, 0, w, h);
      for (let i = 0; i < 900; i++) { g.strokeStyle = "rgba(" + (r() > 0.5 ? "255,255,255" : "0,0,0") + "," + (0.03 + r() * 0.07) + ")"; const x = r() * w; g.beginPath(); g.moveTo(x, 0); g.lineTo(x + (r() - 0.5) * 2, h); g.stroke(); }
    }, { srgb: false, repeat: [3, 1] });
    return { rough };
  });
  return new THREE.MeshPhysicalMaterial({ color: dark ? 0x8a8d91 : 0xcfd1d3, metalness: 1, roughness: dark ? 0.32 : 0.42, roughnessMap: maps.rough, anisotropy: 0.5, envMapIntensity: 1.1 });
}
function floorMats(floor, W, D) {
  const [pw, pl] = floor.plank, across = 8, tw = across * pw, tl = 2 * pl;
  const maps = cached("floor:" + floor.hex + pw + pl, () => {
    const r = rng(7), rows = [];
    for (let i = 0; i < across; i++) rows.push({ off: r(), tones: [0, 1, 2, 3, 4].map(() => 0.86 + r() * 0.26) });
    const paint = (g, w, h, mode) => {
      for (let i = 0; i < across; i++) for (let j = -2; j < 3; j++) {
        const x = i * w / across, y = rows[i].off * h + j * h / 2, pwid = w / across, tone = rows[i].tones[j + 2];
        if (mode === "color") {
          g.fillStyle = shade(floor.hex, tone); g.fillRect(x, y, pwid, h / 2);
          for (let k = 0; k < 46; k++) {           // grain: long soft streaks, a few cathedral arcs
            g.strokeStyle = "rgba(" + (r() > 0.4 ? "70,45,20" : "255,240,215") + "," + (0.03 + r() * 0.07) + ")"; g.lineWidth = 0.6 + r() * 1.6;
            const gx = x + r() * pwid, len = h / 2 * (0.3 + r() * 0.7), gy = y + r() * (h / 2 - len);
            g.beginPath(); g.moveTo(gx, gy); g.bezierCurveTo(gx + (r() - 0.5) * 5, gy + len * 0.33, gx + (r() - 0.5) * 5, gy + len * 0.66, gx + (r() - 0.5) * 3, gy + len); g.stroke();
          }
          if (r() > 0.55) { const kx = x + pwid * (0.25 + r() * 0.5), ky = y + r() * h / 2; g.fillStyle = "rgba(60,36,14,0.22)"; g.beginPath(); g.ellipse(kx, ky, 2 + r() * 3, 4 + r() * 7, 0, 0, 7); g.fill(); }
          g.strokeStyle = "rgba(40,26,12,0.5)"; g.lineWidth = 1.4; g.strokeRect(x, y, pwid, h / 2);
        } else {
          g.fillStyle = "#" + (150 + Math.round(tone * 20)).toString(16).repeat(3); g.fillRect(x, y, pwid, h / 2);
          for (let k = 0; k < 60; k++) { g.strokeStyle = "rgba(0,0,0," + (0.04 + r() * 0.08) + ")"; const gx = x + r() * pwid; g.beginPath(); g.moveTo(gx, y); g.lineTo(gx + (r() - 0.5) * 4, y + h / 2); g.stroke(); }
          g.strokeStyle = "#202020"; g.lineWidth = 2.5; g.strokeRect(x, y, pwid, h / 2);
        }
      }
    };
    return { color: canvasTex(1024, 2048, (g, w, h) => paint(g, w, h, "color")), bump: canvasTex(1024, 2048, (g, w, h) => paint(g, w, h, "bump"), { srgb: false }) };
  });
  for (const t of [maps.color, maps.bump]) t.repeat.set(1 / tw, 1 / tl);
  const m = new THREE.MeshStandardMaterial({ map: maps.color, bumpMap: maps.bump, bumpScale: 0.6, roughness: 0.46, metalness: 0, envMapIntensity: 0.8 });
  m.userData.world = true; return m;
}
function stoneMat(c, key) {
  // look: veined (the marble-look quartzes), concrete, soapstone, butcher, laminate
  const look = key === "butcher" || key === "laminate" ? key : c.look || "veined";
  const t = cached("stone:" + key, () => {
    const r = rng(11);
    return canvasTex(1024, 1024, (g, w, h) => {
      g.fillStyle = c.hex; g.fillRect(0, 0, w, h);
      if (look === "butcher") {
        for (let i = 0; i < 28; i++) { g.fillStyle = shade(c.hex, 0.85 + r() * 0.3); g.fillRect(0, i * h / 28, w, h / 28 + 1); }
        for (let i = 0; i < 500; i++) { g.strokeStyle = "rgba(80,50,20," + (0.04 + r() * 0.06) + ")"; const y = r() * h; g.beginPath(); g.moveTo(0, y); g.lineTo(w, y + (r() - 0.5) * 8); g.stroke(); }
        return;
      }
      const clouds = (n, light, dark, a0, a1) => {           // soft blotches, wrapped so the slab tiles without a seam
        for (let i = 0; i < n; i++) {
          const cx = r() * w, cy = r() * h, rad = 40 + r() * 170, col = r() > 0.5 ? light : dark, a = a0 + r() * a1;
          for (const ox of [-w, 0, w]) for (const oy of [-h, 0, h]) {
            const x = cx + ox, y = cy + oy; if (x + rad < 0 || x - rad > w || y + rad < 0 || y - rad > h) continue;
            const gr = g.createRadialGradient(x, y, 0, x, y, rad); gr.addColorStop(0, "rgba(" + col + "," + a + ")"); gr.addColorStop(1, "rgba(" + col + ",0)");
            g.fillStyle = gr; g.fillRect(x - rad, y - rad, 2 * rad, 2 * rad);
          }
        }
      };
      const veins = (n, widths) => {                         // one bold stroke with feathered branches
        for (let i = 0; i < n; i++) {
          let x = r() * w * 0.4 - 60, y = r() * h; const pts = [[x, y]];
          for (let k = 0; k < 9; k++) { x += 70 + r() * 110; y += (r() - 0.42) * 120; pts.push([x, y]); }
          for (const [lw, a] of widths) {
            g.strokeStyle = c.vein; g.globalAlpha = a * (0.6 + r() * 0.6); g.lineWidth = lw; g.lineJoin = "round"; g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
            for (let k = 1; k < pts.length; k++) g.quadraticCurveTo((pts[k - 1][0] + pts[k][0]) / 2, pts[k - 1][1] + (r() - 0.5) * 30, pts[k][0], pts[k][1]);
            g.stroke();
          }
          g.globalAlpha = 1;
        }
      };
      if (look === "concrete") {                             // trowelled grey: clouds, fine sand, a few pinholes, no veins
        clouds(240, "255,255,255", "45,45,42", 0.04, 0.07);
        for (let i = 0; i < 9000; i++) { g.fillStyle = "rgba(" + (r() > 0.5 ? "255,255,255" : "30,30,28") + "," + (0.03 + r() * 0.07) + ")"; g.fillRect(r() * w, r() * h, 1 + r() * 2, 1 + r() * 2); }
        for (let i = 0; i < 90; i++) { g.fillStyle = "rgba(40,40,38," + (0.12 + r() * 0.2) + ")"; g.beginPath(); g.arc(r() * w, r() * h, 0.8 + r() * 1.8, 0, 7); g.fill(); }
        return;
      }
      if (look === "soapstone") {                            // dark and soft, with a few thin pale veins
        clouds(160, "190,205,198", "0,0,0", 0.03, 0.05);
        for (let i = 0; i < 2600; i++) { g.fillStyle = "rgba(" + (r() > 0.6 ? "210,220,215" : "0,0,0") + "," + (0.02 + r() * 0.05) + ")"; g.fillRect(r() * w, r() * h, 1 + r() * 2, 1 + r() * 2); }
        veins(5, [[6, 0.04], [1.8, 0.16], [0.8, 0.45]]);
        return;
      }
      for (let i = 0; i < 2600; i++) { g.fillStyle = "rgba(" + (r() > 0.5 ? "255,255,255" : "120,110,95") + "," + (0.02 + r() * 0.04) + ")"; g.fillRect(r() * w, r() * h, 1 + r() * 3, 1 + r() * 3); }
      veins(7, [[9, 0.05], [3.5, 0.14], [1.1, 0.5]]);
    }, { repeat: [1 / 96, 1 / 96] });
  });
  const [rough, coat] = { butcher: [0.55, 0], laminate: [0.4, 0.35], concrete: [0.48, 0.08], soapstone: [0.6, 0.05] }[look] || [0.16, 0.35];
  const m = new THREE.MeshPhysicalMaterial({ map: t, roughness: rough, clearcoat: coat, clearcoatRoughness: 0.1, envMapIntensity: 0.9 });
  m.userData.world = true; return m;
}
function brickMat() {
  const m = cached("brick", () => {
    const r = rng(3), bricks = [];
    for (let row = 0; row < 24; row++) for (let i = -1; i < 5; i++) bricks.push([i * 128 + (row % 2) * 64 + 3, row * 42.6 + 3, 122, 37, 0.75 + r() * 0.5, r()]);
    const color = canvasTex(512, 1024, (g, w, h) => {
      g.fillStyle = "#b9ab9a"; g.fillRect(0, 0, w, h);
      for (const [x, y, bw, bh, tone, hue] of bricks) { g.fillStyle = shade(hue > 0.8 ? "#8a5a48" : hue > 0.6 ? "#c08a6a" : "#a8674b", tone); g.fillRect(x, y, bw, bh); for (let k = 0; k < 30; k++) { g.fillStyle = "rgba(0,0,0," + r() * 0.08 + ")"; g.fillRect(x + r() * bw, y + r() * bh, 2 + r() * 5, 1 + r() * 3); } }
    });
    const bump = canvasTex(512, 1024, (g, w, h) => { g.fillStyle = "#303030"; g.fillRect(0, 0, w, h); for (const [x, y, bw, bh] of bricks) { g.fillStyle = "#c8c8c8"; g.fillRect(x, y, bw, bh); } }, { srgb: false });
    for (const t of [color, bump]) t.repeat.set(1 / 32, 1 / 64);
    return { color, bump };
  });
  const mm = new THREE.MeshStandardMaterial({ map: m.color, bumpMap: m.bump, bumpScale: 1.2, roughness: 0.95 });
  mm.userData.world = true; return mm;
}
function tileMat(hex) {
  const m = cached("tile:" + hex, () => {
    const draw = (mode) => (g, w, h) => {
      g.fillStyle = mode ? "#404040" : "#d9d5cc"; g.fillRect(0, 0, w, h);
      for (let row = 0; row < 4; row++) for (let i = -1; i < 3; i++) { g.fillStyle = mode ? "#d0d0d0" : hex; g.beginPath(); g.roundRect(i * 256 + (row % 2) * 128 + 3, row * 128 + 3, 250, 122, 5); g.fill(); }
    };
    const color = canvasTex(512, 512, draw(false)), bump = canvasTex(512, 512, draw(true), { srgb: false });
    for (const t of [color, bump]) t.repeat.set(1 / 12, 1 / 12);
    return { color, bump };
  });
  const mm = new THREE.MeshPhysicalMaterial({ map: m.color, bumpMap: m.bump, bumpScale: 0.5, roughness: 0.14, clearcoat: 0.6, clearcoatRoughness: 0.05 });
  mm.userData.world = true; return mm;
}
// Hand-painted Spanish (Talavera) tile, 4 in square. Each tile is drawn from a few
// motifs in the usual glazes: cobalt, cream, terracotta, yellow, green and sky blue.
const TAL = { cobalt: "#1F3F9A", navy: "#16235A", cream: "#F4EFE0", terra: "#C9502B", yellow: "#F2B233", green: "#3F8F6C", sky: "#6DB3DE" };
function talaveraTile(g, x, y, s, r) {
  const u = s / 2, pal = [TAL.cobalt, TAL.cream, TAL.terra, TAL.yellow, TAL.green, TAL.sky], int = (n) => Math.floor(r() * n);
  const bg = [TAL.cream, TAL.cream, TAL.cream, TAL.cobalt, TAL.cobalt, TAL.cobalt, TAL.cobalt, TAL.yellow, TAL.terra, TAL.green][int(10)];
  const pick = (...not) => { let c; do c = pal[int(pal.length)]; while (c === bg || not.includes(c)); return c; };
  const c1 = pick(), c2 = pick(c1), c3 = pick(c1, c2);
  g.save(); g.beginPath(); g.roundRect(x, y, s, s, s * 0.035); g.clip(); g.translate(x + u, y + u);
  g.fillStyle = bg; g.fillRect(-u, -u, s, s);
  g.lineJoin = "round"; g.lineCap = "round"; g.strokeStyle = TAL.navy; g.lineWidth = s * 0.013;
  const paint = (fill) => { g.fillStyle = fill; g.fill(); g.stroke(); };
  const each = (n, draw, a0 = 0) => { for (let i = 0; i < n; i++) { g.save(); g.rotate(a0 + i * 2 * Math.PI / n); draw(); g.restore(); } };
  const petal = (len, wid, from = 0) => { g.beginPath(); g.moveTo(from, 0); g.bezierCurveTo(from + len * 0.3, -wid, from + len * 0.8, -wid, from + len, 0); g.bezierCurveTo(from + len * 0.8, wid, from + len * 0.3, wid, from, 0); };
  const corner = int(5);                                     // what sits in the four corners
  if (corner === 0) each(4, () => { g.beginPath(); g.arc(u, u, u * 0.62, 0, 7); paint(c2); g.beginPath(); g.arc(u, u, u * 0.34, 0, 7); paint(c3); }, 0);
  else if (corner === 1) each(4, () => { g.beginPath(); g.moveTo(u, u); g.lineTo(u, u * 0.3); g.lineTo(u * 0.3, u); g.closePath(); paint(c2); });
  else if (corner === 2) each(4, () => { petal(u * 0.78, u * 0.2, u * 0.55); paint(c2); }, Math.PI / 4);
  else if (corner === 3) each(4, () => { g.beginPath(); g.arc(u * 0.72, u * 0.72, u * 0.13, 0, 7); paint(c2); });
  const motif = int(6);                                      // and what sits in the middle
  if (motif === 0) { const n = r() > 0.5 ? 8 : 4; each(n, () => { petal(u * 0.74, u * (n === 8 ? 0.17 : 0.3), u * 0.08); paint(c1); }, n === 4 && corner === 2 ? 0 : Math.PI / n); }
  else if (motif === 1) { each(4, () => { g.beginPath(); g.arc(u * 0.36, 0, u * 0.36, 0, 7); paint(c1); }); g.beginPath(); g.moveTo(u * 0.34, 0); g.lineTo(0, u * 0.34); g.lineTo(-u * 0.34, 0); g.lineTo(0, -u * 0.34); g.closePath(); paint(c3); }
  else if (motif === 2) { each(12, () => { g.beginPath(); g.moveTo(u * 0.36, -u * 0.11); g.lineTo(u * 0.74, 0); g.lineTo(u * 0.36, u * 0.11); g.closePath(); paint(c1 === TAL.cobalt ? TAL.terra : c1); }); g.beginPath(); g.arc(0, 0, u * 0.42, 0, 7); paint(TAL.yellow === bg ? TAL.terra : TAL.yellow); }
  else if (motif === 3) { g.beginPath(); for (let i = 0; i < 16; i++) { const a = i * Math.PI / 8, rad = u * (i % 2 ? 0.42 : 0.8); g.lineTo(Math.cos(a) * rad, Math.sin(a) * rad); } g.closePath(); paint(c1); each(4, () => { petal(u * 0.4, u * 0.13, 0); paint(c3); }, Math.PI / 4); }
  else if (motif === 4) { g.beginPath(); g.moveTo(u * 0.74, 0); g.lineTo(0, u * 0.74); g.lineTo(-u * 0.74, 0); g.lineTo(0, -u * 0.74); g.closePath(); paint(c1); g.beginPath(); g.rect(-u * 0.27, -u * 0.27, u * 0.54, u * 0.54); paint(c3); each(4, () => { g.beginPath(); g.arc(u * 0.5, 0, u * 0.07, 0, 7); paint(c2); }); }
  else { each(4, () => { g.beginPath(); g.moveTo(u * 0.1, 0); g.bezierCurveTo(u * 0.25, -u * 0.5, u * 0.8, -u * 0.42, u * 0.62, -u * 0.05); g.lineTo(u * 0.5, 0); g.lineTo(u * 0.62, u * 0.05); g.bezierCurveTo(u * 0.8, u * 0.42, u * 0.25, u * 0.5, u * 0.1, 0); paint(c1); }); each(4, () => { petal(u * 0.5, u * 0.09, u * 0.1); paint(c3); }, Math.PI / 4); }
  g.beginPath(); g.arc(0, 0, u * 0.17, 0, 7); paint(c3 === c1 ? c2 : c3); g.beginPath(); g.arc(0, 0, u * 0.07, 0, 7); paint(c2);
  const gl = g.createLinearGradient(-u, -u, u, u); gl.addColorStop(0, "rgba(255,255,255,0.10)"); gl.addColorStop(0.5, "rgba(255,255,255,0)"); gl.addColorStop(1, "rgba(0,0,20,0.08)");
  g.fillStyle = gl; g.fillRect(-u, -u, s, s);                // the glaze pools toward one edge
  g.restore();
}
function talaveraMat(sparse) {
  // every tile painted, every other tile painted ("half": a checkerboard with white), or a white field with a painted tile here and there, never two side by side
  const m = cached("talavera:" + sparse, () => {
    const n = sparse ? 12 : 10, px = 2040 / n, r = rng(sparse ? 31 : 17), cells = [];
    for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
      const near = [[i - 1, j], [i, j - 1], [i - 1, j - 1], [i + 1, j - 1]].some(([a, b]) => cells[((b + n) % n) * n + ((a + n) % n)] === true);
      cells.push(!sparse || (sparse === "half" ? (i + j) % 2 === 0 : r() < 0.2 && !near && !(j === n - 1 && cells[i]) && !(i === n - 1 && cells[j * n])));
    }
    const color = canvasTex(2040, 2040, (g) => {
      g.fillStyle = "#e9e5db"; g.fillRect(0, 0, 2040, 2040);
      cells.forEach((painted, k) => {
        const x = (k % n) * px + 2.5, y = Math.floor(k / n) * px + 2.5, s = px - 5;
        if (painted) talaveraTile(g, x, y, s, r);
        else { g.fillStyle = shade("#F4F2EC", 0.965 + r() * 0.04); g.beginPath(); g.roundRect(x, y, s, s, s * 0.035); g.fill(); }
      });
    });
    const bump = canvasTex(1020, 1020, (g) => { g.fillStyle = "#404040"; g.fillRect(0, 0, 1020, 1020); g.fillStyle = "#d0d0d0"; for (let k = 0; k < n * n; k++) { g.beginPath(); g.roundRect((k % n) * px / 2 + 1.5, Math.floor(k / n) * px / 2 + 1.5, px / 2 - 3, px / 2 - 3, 3); g.fill(); } }, { srgb: false });
    for (const t of [color, bump]) t.repeat.set(1 / (n * 4), 1 / (n * 4));
    return { color, bump };
  });
  const mm = new THREE.MeshPhysicalMaterial({ map: m.color, bumpMap: m.bump, bumpScale: 0.5, roughness: 0.16, clearcoat: 0.6, clearcoatRoughness: 0.06 });
  mm.userData.world = true; return mm;
}
function woodMat(hex) {
  const t = cached("wood:" + hex, () => {
    const r = rng(21);
    return canvasTex(512, 512, (g, w, h) => {
      g.fillStyle = hex; g.fillRect(0, 0, w, h);
      for (let i = 0; i < 9; i++) { g.fillStyle = shade(hex, 0.88 + r() * 0.24); g.fillRect(i * w / 9, 0, w / 9 + 1, h); }
      for (let i = 0; i < 700; i++) { g.strokeStyle = "rgba(70,40,15," + (0.03 + r() * 0.07) + ")"; const x = r() * w; g.beginPath(); g.moveTo(x, 0); g.lineTo(x + (r() - 0.5) * 10, h); g.stroke(); }
    }, { repeat: [1 / 40, 1 / 60] });
  });
  const m = new THREE.MeshPhysicalMaterial({ map: t, roughness: 0.3, clearcoat: 0.5, clearcoatRoughness: 0.15 });
  m.userData.world = true; return m;
}
function skyTex() {
  return cached("sky", () => { const r = rng(9); return canvasTex(1024, 512, (g, w, h) => {
    const s = g.createLinearGradient(0, 0, 0, h); s.addColorStop(0, "#a9cdea"); s.addColorStop(0.55, "#e4eef5"); s.addColorStop(0.62, "#9fb89a"); s.addColorStop(1, "#5f7d57");
    g.fillStyle = s; g.fillRect(0, 0, w, h);
    g.filter = "blur(16px)";
    for (let i = 0; i < 90; i++) { const x = r() * w, rad = 30 + r() * 70, y = h * 0.62 - r() * 120; g.fillStyle = shade(r() > 0.25 ? "#55774d" : "#b79a45", 0.7 + r() * 0.5); g.globalAlpha = 0.7; g.beginPath(); g.ellipse(x, y, rad * 0.7, rad, 0, 0, 7); g.fill(); }
    g.globalAlpha = 1; g.filter = "none";
  }); });
}

// ---- geometry helpers. Every position is in the model's frame.
function place(mesh, x, y, z, dx, dy, dz, o = {}) {
  mesh.position.copy(M(x + dx / 2, y + dy / 2, z + dz / 2));
  mesh.castShadow = o.cast !== false; mesh.receiveShadow = o.receive !== false;
  (o.parent || G.root).add(mesh);
  return mesh;
}
function worldUV(geo, ox, oy, oz) {
  // u, v in inches from the model origin, picked by which way each face looks
  const p = geo.attributes.position, n = geo.attributes.normal, uv = new Float32Array(p.count * 2);
  for (let i = 0; i < p.count; i++) {
    const X = p.getX(i) + ox, Y = p.getY(i) + oy, Z = p.getZ(i) + oz, ax = Math.abs(n.getX(i)), ay = Math.abs(n.getY(i)), az = Math.abs(n.getZ(i));
    if (ay >= ax && ay >= az) { uv[2 * i] = X; uv[2 * i + 1] = Z; } else if (ax >= az) { uv[2 * i] = Z; uv[2 * i + 1] = Y; } else { uv[2 * i] = X; uv[2 * i + 1] = Y; }
  }
  geo.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
}
function box(parent, x, y, z, dx, dy, dz, material, o = {}) {
  dx = Math.max(dx, 0.02); dy = Math.max(dy, 0.02); dz = Math.max(dz, 0.02);
  const r = o.r ? Math.min(o.r, dx / 2.01, dy / 2.01, dz / 2.01) : 0;
  const geo = r ? new RoundedBoxGeometry(dx, dz, dy, 3, r) : new THREE.BoxGeometry(dx, dz, dy);
  if (material.userData && material.userData.world) worldUV(geo, x + dx / 2, z + dz / 2, y + dy / 2);
  return place(new THREE.Mesh(geo, material), x, y, z, dx, dy, dz, { ...o, parent });
}
function cyl(parent, x, y, z, radius, len, axis, material, o = {}) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(radius, o.r2 ?? radius, len, 20), material);
  if (axis === "x") m.rotation.z = Math.PI / 2; else if (axis === "y") m.rotation.x = Math.PI / 2;
  m.position.copy(M(x, y, z)); m.castShadow = o.cast !== false; m.receiveShadow = true; parent.add(m);
  return m;
}
function label(text, color = "#111") {
  const c = document.createElement("canvas"), g = c.getContext("2d");
  g.font = "600 44px system-ui, sans-serif"; const w = Math.ceil(g.measureText(text).width) + 36;
  c.width = w; c.height = 64; g.font = "600 44px system-ui, sans-serif"; g.fillStyle = "rgba(255,255,255,0.94)";
  g.beginPath(); g.roundRect(0, 0, w, 64, 16); g.fill(); g.fillStyle = color; g.textBaseline = "middle"; g.fillText(text, 18, 34);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, transparent: true, toneMapped: false }));
  s.scale.set(w / 64 * 9, 9, 1); s.renderOrder = 10;
  return s;
}
// a front on a box face: u along the face, z up, standing t proud, with a hairline gap all round
function panel(parent, b, u0, u1, z0, z1, t, material, o = {}) {
  const g = o.gap ?? 0.09; u0 += g; u1 -= g; z0 += g; z1 -= g;
  const q = { r: o.r ?? 0.11, ...o };
  if (b.face === "E") return box(parent, b.x + b.dx + (o.off || 0), b.y + u0, z0, t, u1 - u0, z1 - z0, material, q);
  if (b.face === "W") return box(parent, b.x - t - (o.off || 0), b.y + u0, z0, t, u1 - u0, z1 - z0, material, q);
  if (b.face === "S") return box(parent, b.x + u0, b.y + b.dy + (o.off || 0), z0, u1 - u0, t, z1 - z0, material, q);
  return box(parent, b.x + u0, b.y - t - (o.off || 0), z0, u1 - u0, t, z1 - z0, material, q);
}
// a point on a face: u along, z up, d out from the face
function onFace(b, u, z, d) {
  if (b.face === "E") return [b.x + b.dx + d, b.y + u, z];
  if (b.face === "W") return [b.x - d, b.y + u, z];
  if (b.face === "S") return [b.x + u, b.y + b.dy + d, z];
  return [b.x + u, b.y - d, z];
}
const faceW = (b) => (b.face === "E" || b.face === "W" ? b.dy : b.dx);
const alongAxis = (b) => (b.face === "E" || b.face === "W" ? "y" : "x");

function drawCabinet(parent, b, mats, s, line) {
  const body = b.role === "upper" ? mats.upper : mats.lower, lowerish = b.role !== "upper";
  const sinkBase = b.fronts === "door2+false";
  if (b.kind === "base") {
    box(parent, b.x, b.y, b.z + 4.5, b.dx, b.dy, b.dz - 4.5 - (sinkBase ? 10.5 : 0), mats.carcass);
    const k = 3;
    const kx = b.face === "E" ? [b.x, b.dx - k] : b.face === "W" ? [b.x + k, b.dx - k] : [b.x, b.dx];
    const ky = b.face === "S" ? [b.y, b.dy - k] : b.face === "N" ? [b.y + k, b.dy - k] : [b.y, b.dy];
    box(parent, kx[0], ky[0], b.z, kx[1], ky[1], 4.5, mats.toe);
  } else box(parent, b.x, b.y, b.z, b.dx, b.dy, b.dz, b.kind === "tall" ? mats.carcass : mats.carcassUp);
  if (b.fronts === "corner") {   // the rest of a corner unit's face is the next run
    const [u0, u1, z0, z1] = b.rects[0]; panel(parent, b, u0, u1, z0, z1, 0.8, body); return;
  }
  for (const [u0, u1, z0, z1, kind] of b.rects || []) {
    if (kind === "mw") { panel(parent, b, u0, u1, z0, z1, 0.8, mats.blackGlass); panel(parent, b, u0 + 2, u1 - 2, z1 - 2.2, z1 - 1.4, 1.5, mats.steelDark, { off: 0.8, gap: 0, r: 0.3 }); continue; }
    const lowerish = b.role !== "upper" && !(b.kind === "tall" && z0 > 50);   // the upper door of a tall cabinet is handled at its bottom edge
    const jpull = s.handles === "integrated" && line.door !== "shaker", lip = jpull ? 1.25 : 0;
    const [pz0, pz1] = lowerish ? [z0, z1 - lip] : [z0 + lip, z1];
    if (line.door === "shaker") {
      const f = 2.25; panel(parent, b, u0, u1, z0, z1, 0.4, body, { r: 0.05 });
      panel(parent, b, u0, u0 + f, z0, z1, 0.8, body, { r: 0.06 }); panel(parent, b, u1 - f, u1, z0, z1, 0.8, body, { r: 0.06 });
      panel(parent, b, u0 + f - 0.2, u1 - f + 0.2, z0, z0 + f, 0.8, body, { r: 0.06 }); panel(parent, b, u0 + f - 0.2, u1 - f + 0.2, z1 - f, z1, 0.8, body, { r: 0.06 });
    } else {
      panel(parent, b, u0, u1, pz0, pz1, 0.8, body);
      if (jpull) panel(parent, b, u0, u1, lowerish ? z1 - lip : z0, lowerish ? z1 : z0 + lip, 0.2, lowerish ? mats.recess : mats.recessUp, { r: 0 });
    }
    if (kind === "false") continue;
    const mid = (u0 + u1) / 2, ax = alongAxis(b);
    if (s.handles === "begripa") {
      const h = new THREE.Mesh(new THREE.CylinderGeometry(2.56, 2.56, 0.45, 32, 1, false, 0, Math.PI), mats.begripa());
      h.position.copy(M(...onFace(b, mid, lowerish ? z1 - 0.5 : z0 + 0.5, 1.05)));
      // the half disc lies flat on the front, straight edge along the door's edge, round side toward the door's middle
      if (ax === "y") { h.rotation.z = Math.PI / 2; h.rotation.x = lowerish ? Math.PI : 0; } else h.rotation.set(0, -Math.PI / 2, lowerish ? -Math.PI / 2 : Math.PI / 2);
      h.castShadow = true; parent.add(h);
    } else if (s.handles === "cup_black") {
      // a 3.5 in crescent, 1 in tall, standing 0.8 in off the front: flat edge toward the door's edge
      const h = new THREE.Mesh(new THREE.CylinderGeometry(1.75, 1.75, 0.8, 32, 1, false, 0, Math.PI), mats.pullBlack);
      h.scale.x = 0.57;
      const drawer = kind === "drawer" && z1 - z0 < 14;
      h.position.copy(M(...onFace(b, mid, drawer ? (z0 + z1) / 2 + 0.5 : (lowerish ? z1 - 2 : z0 + 2), 1.2)));
      const up = drawer || lowerish;
      if (ax === "y") { h.rotation.z = Math.PI / 2; h.rotation.x = up ? Math.PI : 0; } else h.rotation.set(0, -Math.PI / 2, up ? -Math.PI / 2 : Math.PI / 2);
      h.castShadow = true; parent.add(h);
    } else if (s.handles === "bar_black") {
      // 160 mm centres, about 6.9 in over all, square section; shortened on a front too narrow for it
      const horiz = kind === "drawer", len = horiz ? Math.min(6.9, (u1 - u0) - 3) : Math.min(6.9, (z1 - z0) - 3);
      const hu = horiz ? mid : (u0 < 0.5 && u1 < faceW(b) - 0.5 ? u1 - 2 : u0 + 2), hz = horiz ? (z0 + z1) / 2 : (lowerish ? z1 - 2.5 - len / 2 : z0 + 2.5 + len / 2);
      const box = (u, z, d, lu, lz, ld) => { const m = new THREE.Mesh(ax === "y" ? new THREE.BoxGeometry(ld, lz, lu) : new THREE.BoxGeometry(lu, lz, ld), mats.pullBlack); m.position.copy(M(...onFace(b, u, z, d))); m.castShadow = true; parent.add(m); };
      box(hu, hz, 1.75, horiz ? len : 0.5, horiz ? 0.5 : len, 0.4);
      for (const e of [-1, 1]) box(horiz ? hu + e * (len / 2 - 0.25) : hu, horiz ? hz : hz + e * (len / 2 - 0.25), 1.2, 0.5, 0.5, 0.8);
    } else if (s.handles === "bar") {
      const horiz = kind === "drawer", len = horiz ? Math.min(7, (u1 - u0) * 0.45) : 6;
      const hu = horiz ? mid : (u0 < 0.5 && u1 < faceW(b) - 0.5 ? u1 - 2 : u0 + 2), hz = horiz ? (z0 + z1) / 2 : (lowerish ? z1 - 6 : z0 + 6);
      cyl(parent, ...onFace(b, hu, hz, 1.9), 0.28, len, horiz ? ax : "z", mats.steel);
      for (const e of [-1, 1]) cyl(parent, ...onFace(b, horiz ? hu + e * (len / 2 - 0.6) : hu, horiz ? hz : hz + e * (len / 2 - 0.6), 1.3), 0.2, 1.2, ax === "y" ? "x" : "y", mats.steel);
    }
  }
}

function drawAppliance(parent, b, mats) {
  const w = faceW(b), ax = alongAxis(b);
  const bar = (u, z, len, axis, d = 2.2) => { cyl(parent, ...onFace(b, u, z, d), 0.36, len, axis, mats.steelDark); for (const e of [-1, 1]) cyl(parent, ...onFace(b, axis === "z" ? u : u + e * (len / 2 - 1), axis === "z" ? z + e * (len / 2 - 1) : z, d - 0.7), 0.26, 1.4, ax === "y" ? "x" : "y", mats.steelDark); };
  if (b.role === "fridge") {
    const body = { ...b, ...(b.face === "E" ? { dx: b.dx - 3 } : b.face === "W" ? { x: b.x + 3, dx: b.dx - 3 } : b.face === "N" ? { y: b.y + 3, dy: b.dy - 3 } : { dy: b.dy - 3 }) };
    box(parent, body.x, body.y, body.z + 0.5, body.dx, body.dy, body.dz - 0.5, mats.fridgeSide, { r: 0.3 });
    panel(parent, body, 0, w / 2, 29, 70, 3, mats.steel, { r: 0.5, gap: 0.12 }); panel(parent, body, w / 2, w, 29, 70, 3, mats.steel, { r: 0.5, gap: 0.12 });
    panel(parent, body, 0, w, 2, 29, 3, mats.steel, { r: 0.5, gap: 0.12 });
    bar(w / 2 - 2, 49, 26, "z", 4.6); bar(w / 2 + 2, 49, 26, "z", 4.6); bar(w / 2, 25.5, 24, ax, 4.6);
  } else if (b.role === "range") {
    box(parent, b.x, b.y, b.z, b.dx - 1.5, b.dy, b.dz - 0.4, mats.steel, { r: 0.2 });
    box(parent, b.x + 0.5, b.y + 0.3, 35.6, b.dx - 1.2, b.dy - 0.6, 0.5, mats.blackGlass, { r: 0.1 });
    for (const [bx, by, rad] of [[8, 8, 4.2], [8, 22, 3.2], [17, 8, 3.2], [17, 22, 4.2]]) {
      const ring = new THREE.Mesh(new THREE.RingGeometry(rad - 0.25, rad, 48), new THREE.MeshBasicMaterial({ color: 0x4a4d52 })); ring.rotation.x = -Math.PI / 2; ring.position.copy(M(b.x + bx, b.y + by, 36.13)); parent.add(ring);
    }
    const f = { ...b, dx: b.dx - 1.5 };
    panel(parent, f, 0, w, 3.5, 9, 1.2, mats.steel, { r: 0.2, gap: 0.1 });
    panel(parent, f, 0, w, 9, 30.5, 1.5, mats.steel, { r: 0.25, gap: 0.1 });
    panel(parent, f, 3.5, w - 3.5, 12, 26, 0.12, mats.blackGlass, { off: 1.5, gap: 0, r: 0 });
    panel(parent, f, 0, w, 30.5, 35.4, 1.5, mats.steel, { r: 0.25, gap: 0.1 });
    for (let i = 0; i < 5; i++) cyl(parent, ...onFace(f, 4 + i * (w - 8) / 4, 33, 2.1), 0.75, 1.2, ax === "y" ? "x" : "y", mats.steelDark);
    bar(w / 2, 28.6, w - 5, ax, 3.4);
  } else if (b.role === "dishwasher") {
    box(parent, b.x, b.y, 4.5, b.dx, b.dy, b.dz - 4.5, mats.carcass);
    panel(parent, b, 0, w, 4.5, b.dz, 0.9, mats.steel, { r: 0.2 });
    panel(parent, b, 2.5, w - 2.5, 31.2, 32.4, 0.25, mats.steelDark, { off: 0.9, gap: 0, r: 0.1 });
    const k = b.face === "S" ? [b.x, b.y, b.dx, b.dy - 3] : [b.x, b.y, b.dx - 3, b.dy]; box(parent, k[0], k[1], 0, k[2], k[3], 4.5, mats.toe);
  } else if (b.role === "hood") {
    box(parent, b.x, b.y + 0.2, b.z + 1.5, b.dx, b.dy - 0.4, b.dz - 1.5, mats.steel, { r: 0.3 });
    box(parent, b.x, b.y + 0.2, b.z, b.dx + 2, b.dy - 0.4, 1.5, mats.steel, { r: 0.3 });
  } else if (b.role === "microwave") {
    box(parent, b.x, b.y, b.z, b.dx, b.dy, b.dz, std("#1b1d20", { roughness: 0.35, metalness: 0.4 }), { r: 0.4 });
    const f = { ...b, face: b.face || "S" }; panel(parent, f, 1, faceW(f) - 5, b.z + 1, b.z + b.dz - 1, 0.15, mats.blackGlass, { gap: 0, r: 0 });
  } else box(parent, b.x, b.y, b.z, b.dx, b.dy, b.dz, mats.steel, { r: 0.3 });
}

// a counter slab with a real opening and a steel bowl in it
function slabWithSink(parent, b, sk, mats, apron) {
  const sh = new THREE.Shape(); sh.moveTo(0, 0); sh.lineTo(b.dx, 0); sh.lineTo(b.dx, b.dy); sh.lineTo(0, b.dy); sh.closePath();
  const hx = sk.x - b.x, hy = sk.y - b.y, r = 1.2, hole = new THREE.Path();
  hole.moveTo(hx + r, hy); hole.lineTo(hx + sk.dx - r, hy); hole.quadraticCurveTo(hx + sk.dx, hy, hx + sk.dx, hy + r); hole.lineTo(hx + sk.dx, hy + sk.dy - r);
  hole.quadraticCurveTo(hx + sk.dx, hy + sk.dy, hx + sk.dx - r, hy + sk.dy); hole.lineTo(hx + r, hy + sk.dy); hole.quadraticCurveTo(hx, hy + sk.dy, hx, hy + sk.dy - r); hole.lineTo(hx, hy + r); hole.quadraticCurveTo(hx, hy, hx + r, hy);
  sh.holes.push(hole);
  const geo = new THREE.ExtrudeGeometry(sh, { depth: b.dz - 0.2, bevelEnabled: true, bevelThickness: 0.1, bevelSize: 0.1, bevelSegments: 2 });
  geo.rotateX(Math.PI / 2);                    // shape (x, y) -> (x, z); thickness goes down
  worldUV(geo, b.x, b.z + b.dz - 0.1, b.y);
  const m = new THREE.Mesh(geo, mats.counter); m.position.copy(M(b.x, b.y, b.z + b.dz - 0.1)); m.castShadow = m.receiveShadow = true; parent.add(m);
  const bowl = apron ? std("#f6f6f2", { roughness: 0.12 }) : mats.steelDark, d = sk.dz - 0.1, t = 0.3, top = b.z + b.dz - 0.2;
  box(parent, sk.x, sk.y, top - d, sk.dx, sk.dy, t, bowl, { cast: false });
  box(parent, sk.x - t, sk.y, top - d, t, sk.dy, d, bowl, { cast: false }); box(parent, sk.x + sk.dx, sk.y, top - d, t, sk.dy, d, bowl, { cast: false });
  box(parent, sk.x, sk.y - t, top - d, sk.dx, t, d, bowl, { cast: false }); box(parent, sk.x, sk.y + sk.dy, top - d, sk.dx, t, d, bowl, { cast: false });
  cyl(parent, sk.x + sk.dx / 2, sk.y + sk.dy / 2, top - d + t + 0.05, 1.7, 0.1, "z", std("#55585c", { metalness: 1, roughness: 0.3 }), { cast: false });
}
// A faucet to the maker's stated height and reach (catalog.faucet: style, h_in,
// reach_in, body, arm). "gooseneck": a plain high arc with a pull-down head.
// "spring": a riser, an exposed coil over the arc, the hose inside it, and the
// spray head docked at the end of a side arm, the commercial look.
class HelixCurve extends THREE.Curve {
  constructor(path, radius, turns, axis) { super(); this.path = path; this.radius = radius; this.turns = turns; this.axis = axis; }
  getPoint(t, target = new THREE.Vector3()) {
    const p = this.path.getPoint(t), tan = this.path.getTangent(t).normalize();
    const n = new THREE.Vector3().crossVectors(this.axis, tan).normalize(), a = 2 * Math.PI * this.turns * t;
    return target.copy(p).addScaledVector(n, Math.cos(a) * this.radius).addScaledVector(this.axis, Math.sin(a) * this.radius);
  }
}
function faucet(parent, x, y, z, dirY, mats, spec) {
  const f = spec || { style: "gooseneck", h_in: 15.6, reach_in: 8.6, body: "round", arm: false };
  const h = f.h_in, reach = f.reach_in, P = (a, b2, c) => M(x + a, y + b2, z + c);
  const lever = (lz, len) => { cyl(parent, x + 1.6, y, z + lz, 0.28, len, "x", mats.steel); cyl(parent, x + 1.6 + len / 2, y, z + lz, 0.34, 0.6, "x", mats.steel); };
  if (f.style !== "spring") {
    const k = h / 15.6, r = reach / 8.6;
    const pts = [[0, 0, 0], [0, 0, 11 * k], [0, dirY * 1.5 * r, 14.5 * k], [0, dirY * 5 * r, 15.6 * k], [0, dirY * 8 * r, 14 * k], [0, dirY * 8.6 * r, 11 * k]].map(([a, b2, c]) => P(a, b2, c));
    const tube = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 48, 0.55, 16), mats.steel); tube.castShadow = true; parent.add(tube);
    cyl(parent, x, y, z + 1.2, 0.95, 2.4, "z", mats.steel); lever(2.2, 3.2);
    cyl(parent, x, y + dirY * 8.6 * r, z + 10.4 * k, 0.7, 1.6, "z", mats.steelDark);
    return;
  }
  // the riser: a round or square body to a little over half the height, on a flange
  const riserH = 0.52 * h, bodyR = 0.95;
  if (f.body === "square") { box(parent, x - 0.9, y - 0.9, z, 1.8, 1.8, riserH, mats.steel, { r: 0.15 }); box(parent, x - 1.5, y - 1.5, z, 3, 3, 0.4, mats.steel, { r: 0.2 }); }
  else { cyl(parent, x, y, z + riserH / 2, bodyR, riserH, "z", mats.steel); cyl(parent, x, y, z + 0.2, 1.5, 0.4, "z", mats.steel); }
  lever(riserH - 1.8, 3.4);
  // the arc the coil follows: from the riser's top, up to the stated height, over and down to the dock
  const dock = riserH - 1.5, apex = h - 0.9;
  const arc = new THREE.CatmullRomCurve3([P(0, 0, riserH - 0.5), P(0, 0, riserH + 0.3 * (apex - riserH)), P(0, dirY * reach * 0.12, apex - 0.6), P(0, dirY * reach * 0.5, apex),
    P(0, dirY * reach * 0.9, apex - 0.35 * (apex - dock)), P(0, dirY * reach, dock + 1.6)]);
  const hose = new THREE.Mesh(new THREE.TubeGeometry(arc, 64, 0.42, 12), mats.hose); hose.castShadow = true; parent.add(hose);
  const coilLen = arc.getLength(), turns = Math.round(coilLen / 0.42);      // about 0.42 in of pitch, like the real coils
  const coil = new THREE.Mesh(new THREE.TubeGeometry(new HelixCurve(arc, 0.78, turns, new THREE.Vector3(1, 0, 0)), Math.min(2400, turns * 14), 0.1, 6), mats.steel);
  coil.castShadow = true; parent.add(coil);
  cyl(parent, x, y, z + riserH - 0.3, 1.0, 0.7, "z", mats.steel);
  // the spray head, docked at the arc's end, and the side arm that holds it
  const hx = x, hy = y + dirY * reach;
  cyl(parent, hx, hy, z + dock + 0.9, 0.78, 1.8, "z", mats.steel);
  cyl(parent, hx, hy, z + dock - 1.1, 0.8, 2.2, "z", mats.steelDark);
  if (f.body === "square") cyl(parent, hx, hy, z + dock - 2.9, 0.5, 1.6, "z", mats.steel, { r2: 1.5 });
  else cyl(parent, hx, hy, z + dock - 2.7, 0.75, 1.2, "z", mats.steel, { r2: 1.0 });
  if (f.arm) {
    const armZ = z + dock - 0.3;
    const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, reach - 1.6, 10), mats.steel);
    arm.rotation.x = Math.PI / 2; arm.position.copy(M(x, y + dirY * (reach - 1.6) / 2 + dirY * 0.8, armZ)); arm.castShadow = true; parent.add(arm);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.95, 0.16, 8, 24), mats.steel); ring.rotation.x = Math.PI / 2; ring.position.copy(M(hx, hy, armZ)); parent.add(ring);
  }
}
function chair(parent, x, y, rot, m) {
  const g = new THREE.Group(); g.position.copy(M(x, y, 0)); g.rotation.y = rot; parent.add(g);
  const add = (mesh, px, py, pz) => { mesh.position.set(px, pz, py); mesh.castShadow = true; mesh.receiveShadow = true; g.add(mesh); };
  add(new THREE.Mesh(new RoundedBoxGeometry(15, 0.8, 15, 2, 0.35), m), 0, 0, 17.5);
  add(new THREE.Mesh(new RoundedBoxGeometry(14, 9, 0.7, 2, 0.3), m), 0, 7.2, 29);
  for (const [lx, ly] of [[-6.5, -6.5], [6.5, -6.5], [-6.5, 6.5], [6.5, 6.5]]) add(new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.6, 17.3, 10), m), lx, ly, 8.6);
  for (const lx of [-6.5, 6.5]) add(new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 16, 10), m), lx, 7.2, 25);
}
function person(parent, x, y, h, color, name) {
  const g = new THREE.Group(), m = std(color, { roughness: 0.6 }), r = h * 0.105, bodyH = h * 0.56, legH = h * 0.30, headR = h * 0.068;
  const leg = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.75, r * 0.6, legH, 16), std(shade(color, 0.6))); leg.position.y = legH / 2;
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(r, bodyH - 2 * r, 6, 16), m); body.position.y = legH + bodyH / 2;
  const head = new THREE.Mesh(new THREE.SphereGeometry(headR, 20, 16), std("#e9c9a8")); head.position.y = h - headR;
  for (const p of [leg, body, head]) { p.castShadow = true; g.add(p); }
  g.position.copy(M(x, y, 0)); const tag = label(name, "#222"); tag.position.set(0, h + 7, 0); tag.scale.multiplyScalar(0.8); g.add(tag); parent.add(g);
}

function initScene(host) {
  G.host = host;
  const r = (G.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true, powerPreference: "high-performance" }));
  r.setPixelRatio(Math.min(devicePixelRatio, 2));
  r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap;
  r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = 0.8;
  host.append(r.domElement);
  RectAreaLightUniformsLib.init();
  G.scene = new THREE.Scene();
  G.pmrem = new THREE.PMREMGenerator(r);
  G.roomEnv = G.pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  G.scene.environment = G.roomEnv; G.scene.environmentIntensity = 0.3;
  G.cubeRT = new THREE.WebGLCubeRenderTarget(256, { type: THREE.HalfFloatType });
  G.cube = new THREE.CubeCamera(2, 3000, G.cubeRT); G.cube.position.copy(M(96, 112, 56)); G.scene.add(G.cube);
  G.cam = new THREE.PerspectiveCamera(42, 1, 3, 4000);
  G.ctl = new OrbitControls(G.cam, r.domElement);
  Object.assign(G.ctl, { enableDamping: true, dampingFactor: 0.08, maxPolarAngle: Math.PI / 2 - 0.02, minDistance: 12, maxDistance: 900 });
  G.ctl.addEventListener("change", () => (G.dirty = true));
  // daylight: sun through the south gable, sky from each window, the skylight, and a little bounce
  G.scene.add(new THREE.HemisphereLight(0xdfe9f5, 0xc9b79c, 0.22));
  const sun = new THREE.DirectionalLight(0xfff0dc, 1.7);
  sun.position.copy(M(250, 640, 330)); sun.target.position.copy(M(130, 200, 0));
  sun.castShadow = true; sun.shadow.mapSize.set(4096, 4096); sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.5; sun.shadow.radius = 5;
  Object.assign(sun.shadow.camera, { left: -340, right: 340, top: 340, bottom: -340, near: 50, far: 1600 });
  G.scene.add(sun, sun.target);
  const area = (color, intensity, w, h, pos, look) => { const l = new THREE.RectAreaLight(color, intensity, w, h); l.position.copy(M(...pos)); l.lookAt(M(...look)); G.scene.add(l); };
  area(0xe8f1ff, 2.2, 180, 100, [176, 374, 75], [176, 0, 40]);     // south gable windows
  area(0xeaf2ff, 2.4, 49, 40, [78.5, 1, 64], [78.5, 100, 40]);     // sink window
  area(0xffffff, 2.6, 32, 36, [82, 38, 95], [82, 38, 0]);         // skylight over the sink run
  area(0xfff3e2, 0.8, 52, 80, [228, 78, 40], [228, 200, 40]);      // office slider
  for (const [x, y] of [[9, 40], [9, 105], [9, 137], [38, 9], [122, 9]]) { const p = new THREE.PointLight(0xffe2b8, 140, 60, 2); p.position.copy(M(x, y, 52.5)); G.scene.add(p); }
  try {
    const rt = new THREE.WebGLRenderTarget(4, 4, { samples: 4, type: THREE.HalfFloatType });
    G.composer = new EffectComposer(r, rt);
    G.composer.addPass(new RenderPass(G.scene, G.cam));
    G.gtao = new GTAOPass(G.scene, G.cam, 4, 4);
    G.gtao.updateGtaoMaterial({ radius: 9, distanceExponent: 1.4, thickness: 1.2, scale: 1.25, samples: 16, distanceFallOff: 1, screenSpaceRadius: false });
    G.gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 5, radiusExponent: 1, rings: 2, samples: 16 });
    G.composer.addPass(G.gtao);
    G.composer.addPass(new OutputPass());
  } catch (e) { G.composer = null; }
  new ResizeObserver(resize).observe(host);
  resize(); setCamera(view.cam in CAMS ? view.cam : "overview");
  let visible = true;
  new IntersectionObserver((e) => (visible = e[0].isIntersecting)).observe(host);
  (function loop() {
    requestAnimationFrame(loop);
    if (!visible || document.hidden) return;
    if (G.ctl.update() || G.dirty) { frame(); G.dirty = false; }
  })();
}
function frame() {
  fadeWalls();
  if (G.composer) { try { G.composer.render(); return; } catch (e) { G.composer = null; } }
  G.renderer.render(G.scene, G.cam);
}
function resize() {
  const w = G.host.clientWidth, h = G.host.clientHeight;
  if (!w || !h) return;
  G.renderer.setSize(w, h, false); G.cam.aspect = w / h; G.cam.updateProjectionMatrix();
  if (G.composer) G.composer.setSize(w, h);
  G.dirty = true;
}
const CAMS = {
  overview: { label: "Overview", pos: [380, 400, 270], look: [100, 115, 15], fov: 38 },
  plan: { label: "Plan", pos: [120, 150.5, 640], look: [120, 150, 0], fov: 38 },
  living: { label: "From the living room", pos: [222, 246, 60], look: [56, 92, 42], fov: 60 },
  hall: { label: "From the hallway", pos: [84, 214, 61], look: [72, 30, 40], fov: 66 },
  cook: { label: "At the range", pos: [118, 150, 62], look: [14, 66, 44], fov: 62 },
  sink: { label: "At the sink", pos: [112, 78, 56], look: [78, 4, 44], fov: 42 },
  pantry: { label: "Facing the alcove", pos: [84, 56, 60], look: [170, 49, 46], fov: 58 },
  child: { label: "5-year-old's eyes", pos: [150, 150, 39], look: [20, 80, 34], fov: 66 },
};
const inside = () => { const p = G.cam.position; return p.y < 150 && p.x > -5 && p.x < 277 && p.z > -5 && p.z < 381; };
function setCamera(name) {
  const c = CAMS[name]; view.cam = name;
  if (!G.scene) return;
  G.cam.position.copy(M(...c.pos)); G.ctl.target.copy(M(...c.look)); G.cam.fov = c.fov;
  G.cam.updateProjectionMatrix(); G.ctl.update(); G.dirty = true;
}
function fadeWalls() {
  // seen from outside, a wall between the camera and the room goes faint and the ceiling comes off
  const out = !inside() || G.cam.position.y > 96;
  if (G.shell) G.shell.visible = !out;
  for (const w of G.walls) {
    const hide = out && G.cam.position.clone().sub(w.center).dot(w.out) > 0;
    if (w.hidden === hide) continue;
    // `transparent` is compiled into the wall's shader: without needsUpdate a wall that was solid when the scene
    // was built stays solid when it should fade, and walls come and go with the order things were clicked in
    w.hidden = hide; w.mesh.material.opacity = hide ? 0.06 : 1; w.mesh.material.transparent = hide; w.mesh.material.depthWrite = !hide; w.mesh.material.needsUpdate = true; w.mesh.castShadow = !hide;
  }
}
function captureEnv() {
  // the gloss fronts reflect THIS room: its windows, its floor, its brick
  try {
    G.over.visible = false; if (G.shell) G.shell.visible = true;
    for (const w of G.walls) { w.hidden = null; w.mesh.material.opacity = 1; w.mesh.material.transparent = false; w.mesh.material.depthWrite = true; w.mesh.material.needsUpdate = true; w.mesh.castShadow = true; }
    G.scene.environment = G.roomEnv; G.scene.environmentIntensity = 0.3;
    G.cube.update(G.renderer, G.scene);
    if (G.env) G.env.dispose();
    G.env = G.pmrem.fromCubemap(G.cubeRT.texture).texture;
    G.scene.environment = G.env; G.scene.environmentIntensity = 0.75;
  } catch (e) { G.scene.environment = G.roomEnv; }
  G.over.visible = true;
}

function rebuild() {
  if (!G.scene) return;
  const s = S, L = layoutOf(s), cat = T.catalog, line = cat.cab_line[s.cab_line];
  for (const g of [G.root, G.over]) if (g) { G.scene.remove(g); g.traverse((o) => { if (o.geometry) o.geometry.dispose(); }); }
  const root = (G.root = new THREE.Group()), over = (G.over = new THREE.Group()), shell = (G.shell = new THREE.Group());
  G.scene.add(root, over); root.add(shell); G.walls = [];
  const lowerHex = T.colors[s.lower_color].hex, upperHex = T.colors[s.upper_color].hex;
  const counter = cat.counter[s.counter], floor = cat.floor[s.floor], splash = cat.backsplash[s.backsplash];
  const begripaMats = Object.fromEntries(Object.entries(BEGRIPA).map(([n, hex]) => [n, std(hex, { roughness: 0.45 })]));
  let begripaN = 0;
  if (view.begripa !== "mixed" && !BEGRIPA[view.begripa]) view.begripa = "yellow";
  const mats = {
    lower: lacquer(lowerHex, line.sheen), upper: lacquer(upperHex, line.sheen),
    carcass: std(shade(lowerHex, 0.92), { roughness: 0.5 }), carcassUp: std(shade(upperHex, 0.97), { roughness: 0.5 }),
    toe: std("#1c1c1c", { roughness: 0.7 }), recess: std(shade(lowerHex, 0.3), { roughness: 0.9 }), recessUp: std(shade(upperHex, 0.5), { roughness: 0.9 }),
    pipe: std("#1d1d1f", { metalness: 0.6, roughness: 0.4 }),     hose: std("#2a2b2e", { roughness: 0.55, metalness: 0.15 }),     pullBlack: std("#1b1b1d", { roughness: 0.6 }),     steel: steelMat(false), steelDark: steelMat(true), fridgeSide: std("#5e6165", { metalness: 0.6, roughness: 0.5 }),
    blackGlass: new THREE.MeshPhysicalMaterial({ color: 0x0b0c0e, roughness: 0.06, clearcoat: 1, clearcoatRoughness: 0.02 }),
    counter: stoneMat(counter, s.counter), begripa: () => begripaMats[view.begripa === "mixed" ? BEGRIPA_MIX[begripaN++ % BEGRIPA_MIX.length] : view.begripa],
    wall: () => std("#f3f0e9", { roughness: 0.93 }), trim: std("#f7f5f0", { roughness: 0.6 }),
    glass: new THREE.MeshPhysicalMaterial({ color: 0xdfeef6, transparent: true, opacity: 0.16, roughness: 0.02, metalness: 0, envMapIntensity: 1.4 }),
  };
  // ---- the room
  const V = T.vault || [[-5, 96], [185, 150], [277, 120]], WH = T.wall_h || 96;
  const zc = (x) => (x <= V[1][0] ? V[0][1] + (x - V[0][0]) * (V[1][1] - V[0][1]) / (V[1][0] - V[0][0]) : V[1][1] + (x - V[1][0]) * (V[2][1] - V[1][1]) / (V[2][0] - V[1][0]));
  const beamX = V[1][0], beamZ = V[1][1] - 9;              // the ridge beam's centre line and underside
  const center = M(136, 188, 48);
  for (const b of T.room) {
    if (b.kind === "furniture" || b.kind === "rug" || b.kind === "sofa") continue;
    if (b.kind === "floor") { box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, floorMats(floor, b.dx, b.dy), { cast: false }); continue; }
    if (b.kind === "wall") {
      const m = box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, mats.wall());
      const c = M(b.x + b.dx / 2, b.y + b.dy / 2, 48), out = c.clone().sub(center);
      if (b.dx < b.dy) out.set(Math.sign(out.x) || 1, 0, 0); else out.set(0, 0, Math.sign(out.z) || 1);
      if (!b.inner) G.walls.push({ mesh: m, center: c, out });   // a wall inside the room is never faded away
      continue;
    }
    if (b.kind === "glass") {
      box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, mats.glass, { cast: false });
      const n = Math.max(1, Math.round(b.dx / 45));    // mullions and a frame
      for (let i = 0; i <= n; i++) box(root, b.x + i * (b.dx - 2) / n, b.y - 0.5, b.z, 2, 3, b.dz, mats.trim, { cast: true });
      box(root, b.x, b.y - 0.5, b.z + b.dz - 2, b.dx, 3, 2, mats.trim); box(root, b.x, b.y - 0.5, b.z + b.dz * 0.52, b.dx, 3, 2, mats.trim);
      continue;
    }
    if (b.kind === "rail") {
      box(root, b.x, b.y, b.z + b.dz - 2.5, b.dx, b.dy, 2.5, woodMat("#7a4a2c"));
      const horiz = b.dx > b.dy, len = horiz ? b.dx : b.dy, n = Math.max(2, Math.round(len / 40));
      for (let i = 0; i <= n; i++) box(root, horiz ? b.x + i * (len - 1.5) / n : b.x + 0.25, horiz ? b.y + 0.25 : b.y + i * (len - 1.5) / n, 0, 1.5, 1.5, b.dz - 2.5, std("#1d1d1f", { metalness: 0.6, roughness: 0.4 }));
      for (let k = 1; k < 7; k++) cyl(root, b.x + b.dx / 2, b.y + b.dy / 2, k * 4.8, 0.09, len, horiz ? "x" : "y", mats.steelDark, { cast: false });
      continue;
    }
    if (b.kind === "post") {
      // floor to the vaulted ceiling. What stands above the wall plate comes off with the ceiling when the room is seen from outside
      const top = Math.min(b.z + b.dz, b.x < beamX + 4 && b.x + b.dx > beamX - 4 ? beamZ : 1e9);
      box(root, b.x, b.y, b.z, b.dx, b.dy, Math.min(top, WH) - b.z, mats.wall(), { r: 0.15 });
      if (top > WH) box(shell, b.x, b.y, WH, b.dx, b.dy, top - WH, mats.wall(), { r: 0.15 });
      continue;
    }
    if (b.kind === "wallshelf") {
      box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, woodMat("#9a5a2e"), { r: 0.1 });
      for (const y of [b.y + 3, b.y + b.dy - 3]) { cyl(root, b.x + b.dx / 2, y, b.z - 0.4, 0.4, b.dx - 1, "x", mats.pipe, { cast: false }); cyl(root, b.x + b.dx - 0.6, y, b.z - 2, 0.4, 3.2, "z", mats.pipe, { cast: false }); }
      continue;
    }
    const look = { brick: brickMat(), stair: std("#2c2622", { roughness: 0.95 }), firebox: std("#6e5a40", { roughness: 0.95 }) }[b.kind];
    box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, look);
  }
  // backdrops seen through the windows
  const sky = new THREE.MeshBasicMaterial({ map: skyTex(), toneMapped: false });
  const bd = (x, y, z, w, h, ry) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), sky); m.position.copy(M(x, y, z)); m.rotation.y = ry; shell.add(m); };
  bd(176, 470, 60, 520, 260, Math.PI); bd(78, -40, 70, 200, 120, 0);
  // furniture, as it stands in the photographs
  if (view.furniture) {
    const top = woodMat("#c98f52"), teal = std("#1f7f8a", { roughness: 0.5 }), tolix = steelMat(false);
    box(root, 196, 78, 28.5, 40, 108, 1.75, top, { r: 0.3 });
    for (const [lx, ly] of [[199, 82], [230, 82], [199, 179], [230, 179]]) box(root, lx, ly, 0, 3.5, 3.5, 28.5, teal);
    box(root, 199, 84, 22, 3, 96, 3.5, teal); box(root, 230.5, 84, 22, 3, 96, 3.5, teal);
    for (const y of [98, 132, 166]) { chair(root, 186, y, -Math.PI / 2, tolix); chair(root, 246, y, Math.PI / 2, tolix); }
    const sb = T.room.find((b) => b.id === "f_sofa_seat"), bb = T.room.find((b) => b.id === "f_sofa_back");
    if (sb && bb) {     // the new couch: square arms, a low square back, block cushions, in a spice colour. It faces south
      const spice = std("#B4532A", { roughness: 0.96 }), cushion = std("#BC5B30", { roughness: 0.98 }), arm = 10, top = bb.z + bb.dz, seat = sb.z + sb.dz;
      const inW = sb.dx - 2 * arm, half = inW / 2;
      for (const [lx, ly] of [[1.5, 1.5], [sb.dx - 4.5, 1.5], [1.5, sb.dy - 4.5], [sb.dx - 4.5, sb.dy - 4.5]]) box(root, sb.x + lx, sb.y + ly, 0, 3, 3, 2.5, std("#2a211c", { roughness: 0.6 }));
      box(root, sb.x, sb.y, 2.5, sb.dx, sb.dy, 9, spice, { r: 0.8 });                                   // the base
      box(root, sb.x, sb.y, 2.5, sb.dx, bb.dy, top - 2.5, spice, { r: 1 });                              // the back
      for (const x of [sb.x, sb.x + sb.dx - arm]) box(root, x, sb.y, 2.5, arm, sb.dy, seat + 6.5, spice, { r: 1 });   // square arms
      for (const i of [0, 1]) {
        box(root, sb.x + arm + i * half + 0.2, sb.y + bb.dy, 11.5, half - 0.4, sb.dy - bb.dy + 0.5, seat - 11.5 + 1, cushion, { r: 1.2 });       // seat cushions
        box(root, sb.x + arm + i * half + 0.2, sb.y + bb.dy - 0.5, seat + 1, half - 0.4, 7.5, top - seat - 1.5, cushion, { r: 1.4 });           // back cushions
      }
    }
    const rug = cached("rug", () => { const r = rng(4); return canvasTex(256, 256, (g, w, h) => { g.fillStyle = "#a7adb0"; g.fillRect(0, 0, w, h); for (let i = 0; i < 26; i++) { g.fillStyle = ["#d8d6cf", "#7f878c", "#c9b24a", "#8f959a"][Math.floor(r() * 4)]; g.fillRect(Math.floor(r() * 8) * 32, Math.floor(r() * 8) * 32, 32 + Math.floor(r() * 3) * 32, 32); } }); });
    box(root, 140, 290, 0, 100, 70, 0.5, std("#ffffff", { map: rug, roughness: 1 }), { cast: false });
    for (const x of [150, 200]) { const arm = std("#5a3d66", { roughness: 0.95 }); box(root, x, 338, 4, 30, 28, 12, arm, { r: 3 }); box(root, x, 358, 12, 30, 8, 16, arm, { r: 3 }); }
    box(root, 269.5, 215, 44, 1.6, 42, 24, mats.blackGlass, { r: 0.3 });        // the television south of the fireplace
    box(root, 150, 300, 0, 42, 22, 15, woodMat("#b5773f"), { r: 0.4 });         // coffee table
  }
  // ---- the kitchen
  const byId = {}; for (const i of L.boxes) byId[T.boxes[i].id] = T.boxes[i];
  for (const i of L.boxes) {
    const b = T.boxes[i];
    if (b.kind === "base" || b.kind === "upper" || b.kind === "tall") drawCabinet(root, b, mats, s, line);
    else if (b.kind === "panel" || b.kind === "filler") box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, b.role === "upper" ? mats.upper : mats.lower, { r: 0.08 });
    else if (b.kind === "appliance") drawAppliance(root, b, mats);
    else if (b.kind === "counter") {
      const sk = b.id === "top_w2" ? byId.sink : b.id === "isl_top" ? byId.prep_sink : null;
      if (sk) slabWithSink(root, b, sk, mats, sk.id === "sink" && cat.sink[s.sink].style === "apron"); else box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, mats.counter, { r: 0.18 });
    } else if (b.kind === "window") {
      box(root, b.x - 2.5, 0, b.z - 2.5, b.dx + 5, 1.2, 2.5, mats.trim); box(root, b.x - 2.5, 0, b.z + b.dz, b.dx + 5, 1.2, 2.5, mats.trim);
      box(root, b.x - 2.5, 0, b.z, 2.5, 1.2, b.dz, mats.trim); box(root, b.x + b.dx, 0, b.z, 2.5, 1.2, b.dz, mats.trim); box(root, b.x + b.dx / 2 - 0.75, 0, b.z, 1.5, 1.0, b.dz, mats.trim);
      const pane = new THREE.Mesh(new THREE.PlaneGeometry(b.dx, b.dz), new THREE.MeshBasicMaterial({ map: skyTex(), toneMapped: false })); pane.position.copy(M(b.x + b.dx / 2, 0.25, b.z + b.dz / 2)); root.add(pane);
    } else if (b.kind === "shelf") box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, woodMat("#d8c7a6"), { r: 0.1 });
    else if (b.kind === "door") { box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, mats.trim, { r: 0.1 }); if (b.face === "W") cyl(root, b.x - 1.2, b.y + 3, 36, 0.5, 4, "y", mats.steel); else cyl(root, b.x + 3, b.y + b.dy + 1.2, 36, 0.5, 4, "x", mats.steel); }
    else if (b.kind === "stool") {
      const cx = b.x + 7.5, cy = b.y + 7.5, m = steelMat(true);
      box(root, cx - 6.5, cy - 6.5, 24.2, 13, 13, 0.9, m, { r: 0.4 });
      for (const [ex, ey] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) { const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.55, 25, 10), m); leg.position.copy(M(cx + ex * 6.6, cy + ey * 6.6, 12.2)); leg.rotation.set(ey * 0.07, 0, -ex * 0.07); leg.castShadow = true; root.add(leg); }
      for (const e of [-1, 1]) { cyl(root, cx, cy + e * 7, 8, 0.3, 14, "x", m); cyl(root, cx + e * 7, cy, 8, 0.3, 14, "y", m); }
    } else if (b.kind === "sink") {
      const wall = b.id === "sink";
      if (wall && cat.sink[s.sink].style === "apron") box(root, b.x - 0.5, 23.3, 26.5, b.dx + 1, 2.9, 9.4, std("#f6f6f2", { roughness: 0.12 }), { r: 0.6 });
      faucet(root, b.x + b.dx / 2, wall ? b.y - 1.4 : b.y + b.dy + 1.6, 36, wall ? 1 : -1, mats, wall ? cat.faucet[s.faucet] : cat.faucet.macksjon);
    }
  }
  // backsplash and the light strips under the uppers
  const w1End = s.fridge_at === "hall" ? 153 : 189;
  if (splash.usd_sqft > 0) {
    const sm = s.backsplash === "quartz_slab" ? mats.counter : splash.look === "talavera" ? talaveraMat(false) : splash.look === "talavera_half" ? talaveraMat("half") : splash.look === "talavera_sparse" ? talaveraMat(true) : tileMat(splash.hex);
    box(root, 0, 0, 36, 0.35, w1End, 18, sm, { cast: false });
    const win = byId.window, sill = win ? Math.min(54, win.z - 2.5) : 54;      // on the sink wall the tile runs under the window and up each side of it, not across it
    box(root, 0, 0, 36, 138, 0.35, sill - 36, sm, { cast: false });
    if (win && sill < 54) { box(root, 0, 0, sill, win.x - 2.5, 0.35, 54 - sill, sm, { cast: false }); box(root, win.x + win.dx + 2.5, 0, sill, 138 - (win.x + win.dx + 2.5), 0.35, 54 - sill, sm, { cast: false }); }
  }
  const glow = new THREE.MeshBasicMaterial({ color: 0xfff0d8, toneMapped: false });
  for (const i of L.boxes) { const b = T.boxes[i]; if (b.kind === "upper" && b.z < 60 && b.id !== "w1_u_hood") { if (b.face === "E") box(root, 2, b.y + 1.5, b.z - 0.25, 0.8, b.dy - 3, 0.2, glow, { cast: false }); else box(root, b.x + 1.5, 2, b.z - 0.25, b.dx - 3, 0.8, 0.2, glow, { cast: false }); } }
  // ---- the ceiling: a vault rising from the long wall to a ridge beam, with the skylight. Indoors only.
  const ceil = std("#f5f2eb", { roughness: 0.95, side: THREE.DoubleSide });
  const quad = (pts, material) => { const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(pts.flatMap((p) => M(...p).toArray()), 3)); g.setIndex([0, 1, 2, 0, 2, 3]); g.computeVertexNormals(); const m = new THREE.Mesh(g, material); m.receiveShadow = true; shell.add(m); return m; };
  quad([[-5, -5, zc(-5)], [185, -5, 150], [185, 381, 150], [-5, 381, zc(-5)]], ceil); quad([[185, -5, 150], [277, -5, zc(277)], [277, 381, zc(277)], [185, 381, 150]], ceil);
  for (const y of [-5, 376]) { const sh = new THREE.Shape(); sh.moveTo(-5, 96); sh.lineTo(-5, zc(-5)); sh.lineTo(185, 150); sh.lineTo(277, zc(277)); sh.lineTo(277, 96); sh.closePath(); const g = new THREE.ExtrudeGeometry(sh, { depth: 5, bevelEnabled: false }); const m = new THREE.Mesh(g, mats.wall()); m.position.set(0, 0, y); shell.add(m); }
  box(shell, 272, -5, 96, 5, 386, zc(277) - 96, mats.wall(), { cast: false });
  box(shell, -75, 204, 96, 70, 59, 1, mats.wall(), { cast: false });
  box(shell, 181, -5, 141, 8, 386, 9, woodMat("#6b3a2a"), { cast: false });        // the ridge beam
  const gable = new THREE.Shape(); gable.moveTo(95, 100); gable.lineTo(95, zc(95) - 4); gable.lineTo(185, 144); gable.lineTo(262, zc(262) - 4); gable.lineTo(262, 100); gable.closePath();
  const gm = new THREE.Mesh(new THREE.ShapeGeometry(gable), new THREE.MeshBasicMaterial({ map: skyTex(), toneMapped: false, side: THREE.DoubleSide })); gm.position.set(0, 0, 375.6); shell.add(gm);
  for (const x of [95, 140, 185, 224, 262]) box(shell, x - 1.5, 374.5, 100, 3, 1.6, zc(x) - 104, mats.trim, { cast: false });
  // ---- over the sink run the ceiling is flat, with the skylight in it. Where it stops, a wall parallel to the sink wall
  // rises to the vault: a triangle over the kitchen, with three cube sconces, and the office's front wall east of the pillar.
  const SF = T.soffit, skyMat = new THREE.MeshBasicMaterial({ color: 0xf4f9ff, toneMapped: false, side: THREE.DoubleSide });
  if (SF) {
    box(shell, SF.x0, -5, SF.z, SF.x1 + 5 - SF.x0, SF.y + 5, 1, ceil, { cast: false });
    quad([[66, 20, SF.z - 0.2], [98, 20, SF.z - 0.2], [98, 56, SF.z - 0.2], [66, 56, SF.z - 0.2]], skyMat);
    const sh = new THREE.Shape(); sh.moveTo(SF.x0, SF.z); sh.lineTo(SF.x0, zc(SF.x0)); sh.lineTo(V[1][0], V[1][1]); sh.lineTo(277, zc(277)); sh.lineTo(277, SF.z); sh.closePath();
    const tw = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: SF.t, bevelEnabled: false }), mats.wall()); tw.position.set(0, 0, SF.y); tw.receiveShadow = true; shell.add(tw);
    const glow = new THREE.MeshBasicMaterial({ color: 0xffe9b0, toneMapped: false });
    for (const [x, z, hex] of T.sconces || []) {
      box(shell, x - 2.5, SF.y + SF.t, z - 2.5, 5, 4, 5, std(hex, { roughness: 0.5, emissive: new THREE.Color(hex), emissiveIntensity: 0.25 }), { cast: false });
      box(shell, x - 2, SF.y + SF.t + 0.4, z + 2.5, 4, 3.2, 0.2, glow, { cast: false }); box(shell, x - 2, SF.y + SF.t + 0.4, z - 2.7, 4, 3.2, 0.2, glow, { cast: false });
    }
  } else quad([[58, 38, zc(58) - 0.3], [102, 38, zc(102) - 0.3], [102, 82, zc(102) - 0.3], [58, 82, zc(58) - 0.3]], skyMat);
  // ---- overlays: never in the reflections
  if (view.doors) {
    const hit = new Set(L.blocked.map((p) => p[0]));
    for (const i of L.opens) { const o = T.boxes[i], bad = hit.has(o.id); const m = box(over, o.x, o.y, o.z, o.dx, o.dy, o.dz, new THREE.MeshBasicMaterial({ color: bad ? 0xd03b3b : 0x2a78d6, transparent: true, opacity: bad ? 0.5 : 0.16, depthWrite: false }), { cast: false, receive: false }); m.renderOrder = 5; }
  }
  if (view.flow) {
    const f = L.flow, wet = f.pt_prep || f.pt_sink, pts = [wet, f.pt_range, f.pt_fridge, wet], ok = L.checks.C3.ok && L.checks.C4.ok, col = ok ? 0x2e9d5f : 0xe04545;
    for (let i = 0; i < 3; i++) {
      const m = new THREE.Mesh(new THREE.TubeGeometry(new THREE.LineCurve3(M(pts[i][0], pts[i][1], 0.8), M(pts[i + 1][0], pts[i + 1][1], 0.8)), 1, 0.75, 8), new THREE.MeshBasicMaterial({ color: col, depthTest: false, toneMapped: false })); m.renderOrder = 9; over.add(m);
      const t = label(L.legs[i].toFixed(1) + " ft", ok ? "#1f6a3f" : "#b3261e"); t.position.copy(M((pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2, 5)); over.add(t);
    }
    if (f.island_rect) { const a = label(L.checks.C5.value + " in aisle", L.checks.C6.ok ? "#1f6a3f" : L.checks.C5.ok ? "#8a5a00" : "#b3261e"); a.position.copy(M((26 + f.island_rect[0]) / 2, f.island_rect[1] + 12, 40)); over.add(a); }
  }
  if (view.people !== "none") {
    const f = L.flow, k = T.people, isl = f.island_rect, wet = f.pt_prep || f.pt_sink, east = isl ? isl[2] + 10 : 110, hall = s.fridge_at === "hall";
    if (view.people === "weeknight") {
      person(over, wet[0] - 13, wet[1], 67, "#3f6fae", "cook"); person(over, east, isl ? isl[1] + 20 : 100, k.kid_big, "#d07a3a", "8 yr"); person(over, east, isl ? isl[3] - 20 : 130, k.kid_small, "#c7559a", "5 yr");
    } else {
      person(over, f.pt_range[0] + 13, f.pt_range[1], 70, "#3f6fae", "cook"); person(over, wet[0] - 13, f.pt_prep ? wet[1] : wet[1] + 13, 64, "#3d8f6b", "prep");
      person(over, f.pt_sink[0] + 28, f.pt_sink[1] + 13, 66, "#8a63b5", "dishes"); person(over, f.pt_fridge[0] + (hall ? 14 : -16), f.pt_fridge[1], 68, "#b0503f", "guest");
      person(over, east, isl ? isl[1] + 20 : 100, k.kid_big, "#d07a3a", "8 yr");
      const p = s.microwave_at === "pantry" && hall; person(over, p ? 128 : east, p ? 52 : (isl ? isl[3] - 20 : 130), k.kid_small, "#c7559a", "5 yr");
    }
  }
  captureEnv();
  G.dirty = true;
}

// ---------------------------------------------------------------- controls
function group(title, hint, ...kids) {
  return el("section", { class: "cfg-group" }, el("h3", { text: title }), hint ? el("p", { class: "cfg-hint", text: hint }) : null, ...kids);
}
function set(patch) { S = normalise({ ...S, ...patch }); save(); render(); }
function save() { try { localStorage.setItem(STORE, JSON.stringify({ S, view })); } catch (e) { /* private window */ } }
function choice(field, options, { delta = true, sub = null } = {}) {
  const now = bill(S).total;
  return el("div", { class: "cfg-choices", role: "radiogroup" }, options.map(([value, label, disabled]) => {
    const on = S[field] === value;
    const d = delta && !on && !disabled ? totalWith({ [field]: value }) - now : null;
    return el("button", { class: "cfg-choice" + (on ? " is-on" : ""), type: "button", role: "radio", "aria-checked": String(on), disabled: !!disabled,
      onclick: () => set({ [field]: value }) },
      el("span", { class: "cfg-choice-label", text: label }),
      sub ? el("span", { class: "cfg-choice-sub", text: sub(value) }) : null,
      d != null ? el("span", { class: "cfg-delta " + (d > 0.5 ? "up" : d < -0.5 ? "down" : ""), text: signed(d) }) : null);
  }));
}
function swatches(field, ids) {
  return el("div", { class: "cfg-swatches" }, ids.map((id) => {
    const c = T.colors[id], on = S[field] === id;
    return el("button", { class: "cfg-swatch" + (on ? " is-on" : ""), type: "button", title: c.name + (c.ral ? " · " + c.ral : ""), "aria-label": c.name, "aria-pressed": String(on),
      style: "--sw:" + c.hex, onclick: () => set({ [field]: id }) });
  }));
}
const catOpts = (g) => Object.entries(T.catalog[g]).map(([k, o]) => [k, o.label]);

function renderControls() {
  const cat = T.catalog, line = cat.cab_line[S.cab_line], host = $("#cfg-controls");
  const lc = T.colors[S.lower_color], uc = T.colors[S.upper_color];
  const noIsland = S.island_len === 0, alcove = S.fridge_at === "alcove";
  host.replaceChildren(
    group("Cabinets", "Each line offers its own colours. Prices are per linear foot of run, as IKEA quotes them.",
      choice("cab_line", catOpts("cab_line"), { sub: (k) => cat.cab_line[k].sheen + (cat.cab_line[k].integrated === true ? " · integrated handle" : cat.cab_line[k].integrated === "ask" ? " · integrated handle to confirm" : " · pulls") }),
      el("p", { class: "cfg-note", text: line.note })),
    group("Lower colour", lc.name + (lc.ral ? " · " + lc.ral : ""), swatches("lower_color", line.lower)),
    group("Upper colour", uc.name + (uc.ral ? " · " + uc.ral : ""), swatches("upper_color", line.upper)),
    group("Handles", S.handles === "begripa" ? "BEGRIPA colour: " + (view.begripa === "mixed" ? "mixed, all five" : view.begripa) : null,
      choice("handles", line.handles.map((h) => [h, cat.handles[h].label])),
      S.handles === "begripa" ? el("div", { class: "cfg-swatches" }, [["mixed", BEGRIPA_MIX_SW], ...Object.entries(BEGRIPA)].map(([n, sw]) => el("button", { class: "cfg-swatch" + (view.begripa === n ? " is-on" : ""), type: "button", title: "BEGRIPA " + (n === "mixed" ? "mixed colours" : n), "aria-label": "BEGRIPA " + (n === "mixed" ? "mixed colours" : n), "aria-pressed": String(view.begripa === n), style: "--sw:" + sw, onclick: () => { view.begripa = n; save(); render(); } }))) : null),
    group("Refrigerator", null, choice("fridge_at", catOpts("fridge_at"))),
    group("Island", "64 in is the contractor's. 40 in deep gives the seats knee room; 48 in of aisle lets two cooks pass.",
      choice("island_len", [[64, "64 in, two seats"], [76, "76 in, three seats"], [0, "No island"]]),
      el("div", { class: "cfg-row" },
        el("div", {}, el("h4", { text: "Top depth" }), choice("island_top_d", [[40, "40 in", noIsland], [36, "36 in", noIsland]], { delta: false })),
        el("div", {}, el("h4", { text: "Aisle to the range" }), choice("island_aisle", [[48, "48 in", noIsland], [42, "42 in", noIsland]], { delta: false }))),
      el("h4", { text: "Island prep sink" }), choice("prep_sink", [[true, "Yes", noIsland], [false, "No"]])),
    group("Old refrigerator alcove", alcove ? "The refrigerator is still in it." : "No wall comes down: the alcove stays the size of the refrigerator. Assumed 40 in wide and 34 in deep. Measure it.",
      choice("pantry", [["open", cat.pantry.open.label, alcove], ["door", cat.pantry.door.label, alcove], ["cabinets", cat.pantry.cabinets.label, alcove]])),
    group("Microwave", null, choice("microwave_at", [["pantry", cat.microwave_at.pantry.label, alcove], ["island", cat.microwave_at.island.label, noIsland], ["counter", cat.microwave_at.counter.label]])),
    group("Countertop", null, choice("counter", catOpts("counter"), { sub: (k) => "$" + cat.counter[k].usd_sqft + " / sq ft installed" })),
    group("Backsplash", null, choice("backsplash", catOpts("backsplash"))),
    group("Sink and faucet", null, choice("sink", catOpts("sink"), { sub: (k) => usd(cat.sink[k].usd) }), choice("faucet", catOpts("faucet"), { sub: (k) => { const f = cat.faucet[k]; return usd(f.usd) + " · " + (f.style === "spring" ? "spring coil" : "gooseneck") + " · " + Math.round(f.h_in) + " in tall"; } }),
      el("p", { class: "cfg-note", text: cat.faucet[S.faucet].note || "" })),
    group("Upstairs floor", T.money.floor_area.toLocaleString() + " sq ft of floor, " + T.money.floor_order.toLocaleString() + " sq ft ordered with waste.",
      choice("floor", catOpts("floor"), { sub: (k) => { const f = cat.floor[k]; return "$" + f.usd_sqft.toFixed(2) + " / sq ft · " + f.wear + " mil · " + f.plank[0] + " x " + f.plank[1] + " in · " + f.vendor.split(",")[0]; } })),
    group("Who does the work", null,
      el("h4", { text: "Cabinet assembly" }), choice("cab_install", catOpts("cab_install")),
      el("h4", { text: "Old bamboo floor" }), choice("floor_removal", catOpts("floor_removal")),
      el("h4", { text: "Running the job" }), choice("managed_by", catOpts("managed_by"))),
  );
  for (const b of host.querySelectorAll(".cfg-choice")) {
    const f = T.catalog.floor, lab = b.querySelector(".cfg-choice-label").textContent;
    const hit = Object.values(f).find((o) => o.label === lab) || Object.values(T.catalog.counter).find((o) => o.label === lab);
    if (hit) b.style.setProperty("--chip", hit.hex), b.classList.add("has-chip");
  }
}

function renderSummary() {
  const b = bill(S), c = checks(S), budget = T.money.budget, over = b.total > budget, rec = isRecorded(S);
  const fails = c.rows.filter((r) => !r.ok);
  const pct = Math.min(100, (b.total / budget) * 100);
  $("#cfg-budget").replaceChildren(
    el("div", { class: "cfg-total" + (over ? " is-over" : "") },
      el("span", { class: "cfg-total-num", text: usd(b.total) }),
      el("span", { class: "cfg-total-of", text: " of " + usd(budget) + (over ? " · " + usd(b.total - budget) + " over" : " · " + usd(budget - b.total) + " to spare") })),
    el("div", { class: "cfg-bar", role: "img", "aria-label": "Share of the budget used" },
      el("span", { class: "cfg-bar-k", style: "width:" + (b.kitchen / b.sub) * pct + "%", title: "Kitchen " + usd(b.kitchen) }),
      el("span", { class: "cfg-bar-f", style: "width:" + (b.floors / b.sub) * pct + "%", title: "Floors " + usd(b.floors) })),
    el("p", { class: "cfg-split", text: "Kitchen " + usd(b.kitchen) + " · floors " + usd(b.floors) + " · contingency " + usd(b.cont) + " · tax " + usd(b.tax) + (b.markup ? " · contractor " + usd(b.markup) : "") }));
  const lenses = [...new Set(c.rows.map((r) => r.lens))];
  $("#cfg-chips").replaceChildren(...lenses.map((l) => {
    const rows = c.rows.filter((r) => r.lens === l), bad = rows.filter((r) => !r.ok).length;
    return el("a", { class: "cfg-chip " + (bad ? "bad" : "ok"), href: "marketing/#cfg-checks" }, el("span", { "aria-hidden": "true", text: bad ? "✕ " : "✓ " }), l);
  }));
  $("#cfg-state").replaceChildren(rec
    ? el("p", { class: "cfg-state rec" }, el("strong", { text: "This is the recorded design. " }), "nopekit's gates have run on it; their verdict is ", el("a", { href: "engineering/", text: "on the engineering page" }), ".")
    : el("p", { class: "cfg-state" }, el("strong", { text: "What-if. " }), "You have left the recorded design. The answers below come from the same model, but no gate has run on this combination. ",
      el("button", { class: "cfg-link", type: "button", onclick: () => { S = normalise(recorded()); save(); render(); }, text: "Back to the recorded design" })));
  $("#cfg-checks-body").replaceChildren(
    ...lenses.map((l) => el("div", { class: "cfg-lens" }, el("h4", { text: l }),
      el("ul", {}, c.rows.filter((r) => r.lens === l).map((r) => el("li", { class: r.ok ? "ok" : "bad" },
        el("span", { class: "cfg-mark", "aria-hidden": "true", text: r.ok ? "✓" : "✕" }),
        el("span", { class: "cfg-st" }, r.statement, " ", el("a", { class: "cfg-id", href: "engineering/#claim=" + r.id, text: r.id })),
        el("span", { class: "cfg-val", text: r.value })))))),
    c.notes.length ? el("div", { class: "cfg-lens cfg-notes" }, el("h4", { text: "Not settled by any drawing" }), el("ul", {}, c.notes.map((n) => el("li", { text: n })))) : null);
  $("#cfg-checks-head").textContent = fails.length ? fails.length + " of " + c.rows.length + " answers fail" : "All " + c.rows.length + " answers pass";
  const rows = b.lines.map((l) => el("tr", {},
    el("td", {}, l.url ? el("a", { href: l.url, target: "_blank", rel: "noopener", text: l.label }) : l.label, el("span", { class: "cfg-vendor", text: l.vendor || "" })),
    el("td", { class: "num", text: l.qty != null ? (Math.round(l.qty * 10) / 10).toLocaleString() + " " + l.unit + " × $" + l.price.toLocaleString() : "" }),
    el("td", {}, el("span", { class: "cfg-basis " + l.basis, text: BASIS[l.basis] || l.basis })),
    el("td", { class: "num", text: usd(l.ext) })));
  const tot = (label, n, cls) => el("tr", { class: cls || "sum" }, el("td", { colspan: "3", text: label }), el("td", { class: "num", text: usd(n) }));
  $("#cfg-bill-body").replaceChildren(el("table", { class: "cfg-table" },
    el("thead", {}, el("tr", {}, el("th", { text: "Line" }), el("th", { class: "num", text: "Quantity" }), el("th", { text: "Price is" }), el("th", { class: "num", text: "USD" }))),
    el("tbody", {}, rows, tot("Subtotal", b.sub),
      b.markup ? tot("General contractor, " + Math.round(T.catalog.managed_by[S.managed_by].markup * 100) + "%", b.markup) : null,
      tot("Contingency, " + Math.round(T.money.contingency * 100) + "%", b.cont), tot("Edmonds sales tax, " + (T.money.tax * 100).toFixed(1) + "%, on labour and materials", b.tax),
      tot("Permits", b.permits), tot("Total", b.total, "sum grand"))));
  $("#cfg").dataset.total = b.total.toFixed(2);
}

function renderView() {
  const seg = (name, opts, cur, on) => el("div", { class: "cfg-seg", role: "group", "aria-label": name }, opts.map(([v, l]) => el("button", { type: "button", class: cur === v ? "is-on" : "", "aria-pressed": String(cur === v), onclick: () => on(v), text: l })));
  $("#cfg-viewbar").replaceChildren(
    seg("Camera", Object.entries(CAMS).map(([k, c]) => [k, c.label]), view.cam, (v) => { setCamera(v); renderView(); }),
    seg("People", [["none", "Empty"], ["weeknight", "Weeknight"], ["holiday", "Holiday"]], view.people, (v) => { view.people = v; save(); render(); }),
    seg("Overlays", [["flow", (view.flow ? "✓ " : "") + "Cook's triangle"], ["doors", (view.doors ? "✓ " : "") + "Doors open"], ["furniture", (view.furniture ? "✓ " : "") + "Furniture"]], null, (v) => { view[v] = !view[v]; save(); render(); }));
}
function render() { renderControls(); renderSummary(); renderView(); rebuild(); }

function summaryText() {
  const b = bill(S), cat = T.catalog, c = checks(S);
  return ["Edmonds kitchen: my configuration", "Total " + usd(b.total) + " of " + usd(T.money.budget),
    "Cabinets: " + cat.cab_line[S.cab_line].label, "Lower: " + T.colors[S.lower_color].name + " " + (T.colors[S.lower_color].ral || ""), "Upper: " + T.colors[S.upper_color].name + " " + (T.colors[S.upper_color].ral || ""),
    "Handles: " + cat.handles[S.handles].label + (S.handles === "begripa" ? " (" + (view.begripa === "mixed" ? "mixed colours" : view.begripa) + ")" : ""), "Refrigerator: " + cat.fridge_at[S.fridge_at].label,
    "Island: " + (S.island_len ? S.island_len + " x " + S.island_top_d + " in, " + S.island_aisle + " in aisle, prep sink " + (S.prep_sink ? "yes" : "no") : "none"),
    "Alcove: " + cat.pantry[S.pantry].label, "Microwave: " + cat.microwave_at[S.microwave_at].label,
    "Counter: " + cat.counter[S.counter].label, "Backsplash: " + cat.backsplash[S.backsplash].label, "Sink: " + cat.sink[S.sink].label, "Faucet: " + cat.faucet[S.faucet].label,
    "Floor: " + cat.floor[S.floor].label, "Cabinet assembly: " + cat.cab_install[S.cab_install].label, "Old floor: " + cat.floor_removal[S.floor_removal].label, "Managed by: " + cat.managed_by[S.managed_by].label,
    "Failing answers: " + (c.rows.filter((r) => !r.ok).map((r) => r.id).join(", ") || "none"), "", "model fields: " + JSON.stringify(S)].join("\n");
}

async function main() {
  const host = $("#cfg");
  if (!host) return;
  try {
    T = await (await fetch("assets/twin.json", { cache: "no-store" })).json();
  } catch (e) {
    $("#cfg-stage").textContent = "The configurator's data (assets/twin.json) is missing. Run: nopekit site build"; return;
  }
  S = recorded();
  try { const saved = JSON.parse(localStorage.getItem(STORE) || "null"); if (saved && saved.S && T.layouts[keyOf(saved.S)] && T.catalog.cab_line[saved.S.cab_line]) { S = { ...S, ...saved.S }; view = { ...view, ...saved.view }; } } catch (e) { /* ignore */ }
  S = normalise(S);
  const camHash = (location.hash.match(/cam=([a-z]+)/) || [])[1];      // marketing/#cam=sink opens on that camera
  if (camHash && CAMS[camHash]) view.cam = camHash;
  try { initScene($("#cfg-stage")); } catch (e) { $("#cfg-stage").textContent = "This browser could not start WebGL, so the room is not drawn. The options, the bill and the answers below still work."; G.scene = null; }
  $("#cfg-reset").addEventListener("click", () => { S = normalise(recorded()); save(); render(); });
  const fullBtn = $("#cfg-full"), fullBox = $("#cfg-view");
  if (fullBtn && fullBox && document.fullscreenEnabled && fullBox.requestFullscreen) {
    fullBtn.hidden = false;
    fullBtn.addEventListener("click", () => { if (document.fullscreenElement) document.exitFullscreen(); else fullBox.requestFullscreen().catch(() => {}); });
    document.addEventListener("fullscreenchange", () => {
      const on = document.fullscreenElement === fullBox;
      fullBtn.setAttribute("aria-pressed", String(on)); fullBtn.textContent = on ? "Exit full screen" : "Full screen";
    });
  }
  $("#cfg-copy").addEventListener("click", async (e) => { try { await navigator.clipboard.writeText(summaryText()); e.target.textContent = "Copied"; } catch (err) { prompt("Copy your configuration:", summaryText()); } setTimeout(() => (e.target.textContent = "Copy my configuration"), 1600); });
  render();
  window.__cfg = { get total() { return bill(S).total; }, recordedTotal: T.recorded_total, set, get S() { return S; }, setCamera, lookFrom: (pos, look, fov = 50) => { G.cam.position.copy(M(...pos)); G.ctl.target.copy(M(...look)); G.cam.fov = fov; G.cam.updateProjectionMatrix(); G.ctl.update(); G.dirty = true; }, checks: () => checks(S) };
}
main();
