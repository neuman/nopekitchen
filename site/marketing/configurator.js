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
const STORE = "edmonds-kitchen-config-v1";
const PRICE_KEY = { cab_line: "usd_lf", cab_install: "usd_lf", handles: "usd_each", counter: "usd_sqft",
  backsplash: "usd_sqft", sink: "usd", faucet: "usd", floor: "usd_sqft", floor_removal: "usd_sqft" };
const UNIT = { cab_line: "linear ft", cab_install: "linear ft", handles: "each", counter: "sq ft",
  backsplash: "sq ft", sink: "each", faucet: "each", floor: "sq ft", floor_removal: "sq ft" };
const BEGRIPA = { white: "#F4F4F0", yellow: "#F5D33B", "light blue": "#9CC4E4", "light red": "#EF6B6B", lilac: "#B79CE0" };
const BASIS = { seen: "seen online", tag: "store tag", estimate: "estimate" };

let T = null;          // twin.json
let S = null;          // the selection
let view = { people: "weeknight", flow: true, furniture: true, cam: "overview", begripa: "yellow" };

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
  const wear = T.catalog.floor[s.floor].wear;
  row("Floors", "C14", wear >= C.C14.limit, wear + " mil (min " + C.C14.limit + ")");
  const notes = [];
  if (line.integrated === "ask") notes.push("The integrated handle on this line is seen in one image only. Ask the maker before ordering (claim A4).");
  if (line.integrated === false) notes.push("This line has no integrated handle.");
  if (line.integrated === true && s.handles !== "integrated") notes.push("You chose added handles on a line that has an integrated one.");
  if (s.prep_sink) notes.push("The island sink needs a drain through the floor. A plumber must confirm it (claim A5).");
  if (!s.prep_sink && s.fridge_at === "hall") notes.push("Without an island sink the cook walks " + L.cleanup_ft + " ft from the refrigerator to the sink.");
  if (s.island_len > 0) notes.push("The island's seat edge is " + L.east_in + " in inside the post line. Check the dining table leaves 44 in behind the stools (claim P3).");
  if (s.fridge_at === "hall" && s.pantry === "cabinets") notes.push("Pantry cabinets need the alcove to be at least 36 in wide. It has not been measured (claim A1).");
  return { rows: out, notes };
}

// ---------------------------------------------------------------- 3D
const G = { scene: null, cam: null, ctl: null, renderer: null, root: null, walls: [], dirty: true, host: null };
const M = (x, y, z) => new THREE.Vector3(x, z, y);        // model (x east, y south, z up) -> three (Y up)
function mat(hex, o = {}) {
  return new THREE.MeshStandardMaterial({ color: new THREE.Color(hex), roughness: 0.8, metalness: 0, ...o });
}
function glossMat(hex, sheen) {
  const p = { gloss: [0.07, 1.0, 0.03], satin: [0.38, 0.25, 0.3], matt: [0.72, 0.0, 0.5] }[sheen] || [0.5, 0, 0.5];
  return new THREE.MeshPhysicalMaterial({ color: new THREE.Color(hex), roughness: p[0], clearcoat: p[1], clearcoatRoughness: p[2], metalness: 0, envMapIntensity: 1.0 });
}
function box(parent, x, y, z, dx, dy, dz, material, o = {}) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(Math.max(dx, 0.02), Math.max(dz, 0.02), Math.max(dy, 0.02)), material);
  m.position.copy(M(x + dx / 2, y + dy / 2, z + dz / 2));
  m.castShadow = o.cast !== false; m.receiveShadow = o.receive !== false;
  parent.add(m);
  return m;
}
function canvasTex(w, h, draw, repeat) {
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  draw(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8;
  if (repeat) t.repeat.set(repeat[0], repeat[1]);
  return t;
}
function rng(seed) { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; }
function shade(hex, f) {
  const c = new THREE.Color(hex); const h = {}; c.getHSL(h);
  c.setHSL(h.h, h.s, Math.min(1, Math.max(0, h.l * f)));
  return "#" + c.getHexString();
}
function plankTex(floor, W, D) {
  // one tile = 6 planks across, 2 plank lengths; planks run north-south
  const [pw, pl] = floor.plank, r = rng(7), tw = 6 * pw, tl = 2 * pl;
  return canvasTex(512, 1024, (g, w, h) => {
    for (let i = 0; i < 6; i++) {
      const off = r() * h;
      for (let j = -2; j < 3; j++) {
        g.fillStyle = shade(floor.hex, 0.9 + r() * 0.2);
        g.fillRect(i * w / 6, off + j * h / 2, w / 6, h / 2);
        g.strokeStyle = "rgba(60,40,20,0.25)"; g.lineWidth = 1.5;
        g.strokeRect(i * w / 6, off + j * h / 2, w / 6, h / 2);
        for (let k = 0; k < 14; k++) {
          g.strokeStyle = "rgba(70,45,20," + (0.03 + r() * 0.06) + ")"; g.lineWidth = 1;
          const gx = i * w / 6 + r() * w / 6; g.beginPath(); g.moveTo(gx, off + j * h / 2); g.lineTo(gx + (r() - 0.5) * 6, off + (j + 1) * h / 2); g.stroke();
        }
      }
    }
  }, [W / tw, D / tl]);
}
function stoneTex(c) {
  const r = rng(11);
  return canvasTex(512, 512, (g, w, h) => {
    g.fillStyle = c.hex; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 9; i++) {
      g.strokeStyle = c.vein; g.globalAlpha = 0.25 + r() * 0.35; g.lineWidth = 0.6 + r() * 2.2;
      let x = r() * w, y = r() * h; g.beginPath(); g.moveTo(x, y);
      for (let k = 0; k < 7; k++) { x += 30 + r() * 60; y += (r() - 0.45) * 70; g.lineTo(x, y); }
      g.stroke();
    }
    g.globalAlpha = 1;
  });
}
function brickTex() {
  const r = rng(3);
  return canvasTex(256, 256, (g, w, h) => {
    g.fillStyle = "#cbb9a6"; g.fillRect(0, 0, w, h);
    for (let row = 0; row < 16; row++) for (let i = -1; i < 5; i++) {
      g.fillStyle = shade("#a8674b", 0.8 + r() * 0.4);
      g.fillRect(i * 64 + (row % 2) * 32 + 2, row * 16 + 2, 60, 12);
    }
  }, [1, 3]);
}
function label(text, color = "#111") {
  const c = document.createElement("canvas"), g = c.getContext("2d");
  g.font = "600 44px system-ui, sans-serif"; const w = Math.ceil(g.measureText(text).width) + 36;
  c.width = w; c.height = 64;
  g.font = "600 44px system-ui, sans-serif"; g.fillStyle = "rgba(255,255,255,0.92)";
  g.beginPath(); g.roundRect(0, 0, w, 64, 16); g.fill();
  g.fillStyle = color; g.textBaseline = "middle"; g.fillText(text, 18, 34);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, transparent: true }));
  s.scale.set(w / 64 * 9, 9, 1); s.renderOrder = 10;
  return s;
}

// a front panel on a box face. u runs along the face, z up, t is how far it stands proud
function panel(parent, b, u0, u1, z0, z1, t, material) {
  const g = 0.12;
  u0 += g; u1 -= g; z0 += g; z1 -= g;
  if (b.face === "E") return box(parent, b.x + b.dx, b.y + u0, z0, t, u1 - u0, z1 - z0, material);
  if (b.face === "W") return box(parent, b.x - t, b.y + u0, z0, t, u1 - u0, z1 - z0, material);
  if (b.face === "S") return box(parent, b.x + u0, b.y + b.dy, z0, u1 - u0, t, z1 - z0, material);
  return box(parent, b.x + u0, b.y - t, z0, u1 - u0, t, z1 - z0, material);
}
const faceW = (b) => (b.face === "E" || b.face === "W" ? b.dy : b.dx);

function frontRects(b) {
  // [u0, u1, z0, z1, kind] for each door and drawer front on the box
  const w = faceW(b), z0 = b.kind === "base" ? b.z + 4.5 : b.z, z1 = b.z + b.dz, half = w / 2, out = [];
  const doors = (a, c) => (w >= 21 ? out.push([0, half, a, c, "door"], [half, w, a, c, "door"]) : out.push([0, w, a, c, "door"]));
  switch (b.fronts) {
    case "drawer3": out.push([0, w, z0, z0 + 15, "drawer"], [0, w, z0 + 15, z0 + 25, "drawer"], [0, w, z0 + 25, z1, "drawer"]); break;
    case "door2+drawer": case "door2+false": doors(z0, z1 - 5); out.push([0, w, z1 - 5, z1, "drawer"]); break;
    case "blind": out.push([0, w, z0, z1, "door"]); break;
    case "door2": doors(z0, z1); break;
    case "door1": out.push([0, w, z0, z1, "door"]); break;
    case "door1tall": out.push([0, w, z0 + 4.5, z0 + 60, "door"], [0, w, z0 + 60, z1, "door"]); break;
    case "microwave": out.push([0, w, z0, z0 + 10, "drawer"], [0, w, z0 + 10, z1, "mw"]); break;
  }
  return out;
}

function drawCabinet(parent, b, mats, s, line) {
  const body = b.role === "upper" ? mats.upper : mats.lower;
  const lowerish = b.role !== "upper";
  if (b.kind === "base") {
    box(parent, b.x, b.y, b.z + 4.5, b.dx, b.dy, b.dz - 4.5, body);
    const k = 3; // toe kick, set back from the front
    const kx = b.face === "E" ? [b.x, b.dx - k] : b.face === "W" ? [b.x + k, b.dx - k] : [b.x, b.dx];
    const ky = b.face === "S" ? [b.y, b.dy - k] : b.face === "N" ? [b.y + k, b.dy - k] : [b.y, b.dy];
    box(parent, kx[0], ky[0], b.z, kx[1], ky[1], 4.5, mats.toe);
  } else box(parent, b.x, b.y, b.z, b.dx, b.dy, b.dz, body);
  for (const [u0, u1, z0, z1, kind] of frontRects(b)) {
    if (kind === "mw") { panel(parent, b, u0, u1, z0, z1, 0.8, mats.blackGlass); continue; }
    const jpull = s.handles === "integrated" && line.door !== "shaker";
    const lip = jpull ? 1.3 : 0;
    // the integrated grip: a dark recess along the top of a lower front, the bottom of an upper door
    const [pz0, pz1] = lowerish ? [z0, z1 - lip] : [z0 + lip, z1];
    if (line.door === "shaker") {
      panel(parent, b, u0, u1, z0, z1, 0.45, body);
      const f = 2.2;
      panel(parent, b, u0, u0 + f, z0, z1, 0.8, body); panel(parent, b, u1 - f, u1, z0, z1, 0.8, body);
      panel(parent, b, u0 + f - 0.2, u1 - f + 0.2, z0, z0 + f, 0.8, body); panel(parent, b, u0 + f - 0.2, u1 - f + 0.2, z1 - f, z1, 0.8, body);
    } else {
      panel(parent, b, u0, u1, pz0, pz1, 0.8, body);
      if (jpull) panel(parent, b, u0, u1, lowerish ? z1 - lip : z0, lowerish ? z1 : z0 + lip, 0.25, lowerish ? mats.recess : mats.recessUp);
    }
    const mid = (u0 + u1) / 2, hz = lowerish ? z1 - 2.2 : z0 + 2.2;
    if (s.handles === "begripa") {
      const h = new THREE.Mesh(new THREE.CylinderGeometry(2.56, 2.56, 0.5, 24, 1, false, 0, Math.PI), mats.begripa);
      const out = b.face === "E" ? [b.x + b.dx + 1.05, b.y + mid] : b.face === "W" ? [b.x - 1.05, b.y + mid] : b.face === "S" ? [b.x + mid, b.y + b.dy + 1.05] : [b.x + mid, b.y - 1.05];
      h.position.copy(M(out[0], out[1], lowerish ? z1 - 0.6 : z0 + 0.6));
      // flat face along the door's edge, the round side hanging into the door
      h.rotation.set(0, 0, 0);
      if (b.face === "E" || b.face === "W") { h.rotation.z = Math.PI / 2; h.rotation.x = lowerish ? Math.PI : 0; }
      else { h.rotation.x = Math.PI / 2; h.rotation.z = lowerish ? -Math.PI / 2 : Math.PI / 2; }
      h.castShadow = true; parent.add(h);
    } else if (s.handles === "bar") {
      const len = kind === "drawer" ? Math.min(8, (u1 - u0) * 0.5) : 0.6, tall = kind === "drawer" ? 0.6 : 6;
      const uu = kind === "drawer" ? mid - len / 2 : (u0 === 0 && u1 < faceW(b) ? u1 - 2.2 : u0 + 1.6);
      const zz = kind === "drawer" ? (z0 + z1) / 2 : (lowerish ? z1 - 9 : z0 + 3);
      panel(parent, { ...b, x: b.face === "E" ? b.x + 0.8 : b.face === "W" ? b.x - 0.8 : b.x, y: b.face === "S" ? b.y + 0.8 : b.face === "N" ? b.y - 0.8 : b.y }, uu, uu + len + 0.24, zz, zz + tall + 0.24, 1.0, mats.steel);
    }
  }
}

function drawAppliance(parent, b, mats) {
  const f = { ...b };
  if (b.role === "fridge") {
    box(parent, b.x, b.y, b.z, b.dx, b.dy, b.dz, mats.steel);
    const w = faceW(b);
    panel(parent, f, 0, w / 2, 30, 70, 0.6, mats.steel); panel(parent, f, w / 2, w, 30, 70, 0.6, mats.steel);
    panel(parent, f, 0, w, 3, 30, 0.6, mats.steel);
    panel(parent, f, w / 2 - 2.2, w / 2 - 1.2, 36, 62, 1.8, mats.steelDark); panel(parent, f, w / 2 + 1.2, w / 2 + 2.2, 36, 62, 1.8, mats.steelDark);
    panel(parent, f, 5, w - 5, 25.5, 26.5, 1.8, mats.steelDark);
  } else if (b.role === "range") {
    box(parent, b.x, b.y, b.z, b.dx, b.dy, b.dz, mats.steel);
    box(parent, b.x + 1, b.y + 0.5, 36, b.dx - 2, b.dy - 1, 0.3, mats.blackGlass);
    const w = faceW(b);
    panel(parent, f, 2, w - 2, 9, 29, 0.5, mats.blackGlass); panel(parent, f, 2, w - 2, 30.5, 31.5, 1.8, mats.steelDark);
    panel(parent, f, 0, w, 3, 8, 0.5, mats.steel);
  } else if (b.role === "dishwasher") {
    box(parent, b.x, b.y, 4.5, b.dx, b.dy, b.dz - 4.5, mats.steel);
    const w = faceW(b); panel(parent, f, 0, w, 4.5, b.dz, 0.7, mats.steel); panel(parent, f, 3, w - 3, 30.5, 31.3, 1.6, mats.steelDark);
  } else if (b.role === "microwave") {
    box(parent, b.x, b.y, b.z, b.dx, b.dy, b.dz, mats.blackGlass);
  } else box(parent, b.x, b.y, b.z, b.dx, b.dy, b.dz, mats.steel);
}

function person(parent, x, y, h, color, name) {
  const g = new THREE.Group(), m = mat(color, { roughness: 0.6 });
  const r = h * 0.105, bodyH = h * 0.56, legH = h * 0.30, headR = h * 0.068;
  const leg = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.75, r * 0.6, legH, 16), mat(shade(color, 0.6)));
  leg.position.y = legH / 2;
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(r, bodyH - 2 * r, 6, 16), m); body.position.y = legH + bodyH / 2;
  const head = new THREE.Mesh(new THREE.SphereGeometry(headR, 20, 16), mat("#e9c9a8")); head.position.y = h - headR;
  for (const p of [leg, body, head]) { p.castShadow = true; g.add(p); }
  g.position.copy(M(x, y, 0));
  const tag = label(name, "#222"); tag.position.set(0, h + 7, 0); tag.scale.multiplyScalar(0.8); g.add(tag);
  parent.add(g);
}

function initScene(host) {
  G.host = host;
  const r = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  r.setPixelRatio(Math.min(devicePixelRatio, 2));
  r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap;
  r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = 0.82;
  host.append(r.domElement);
  G.renderer = r;
  G.scene = new THREE.Scene();
  G.scene.environment = new THREE.PMREMGenerator(r).fromScene(new RoomEnvironment(), 0.04).texture;
  G.scene.environmentIntensity = 0.55;
  G.cam = new THREE.PerspectiveCamera(42, 1, 2, 4000);
  G.ctl = new OrbitControls(G.cam, r.domElement);
  G.ctl.enableDamping = true; G.ctl.dampingFactor = 0.08; G.ctl.maxPolarAngle = Math.PI / 2 - 0.02;
  G.ctl.minDistance = 20; G.ctl.maxDistance = 900;
  G.ctl.addEventListener("change", () => (G.dirty = true));
  G.scene.add(new THREE.HemisphereLight(0xffffff, 0xb8a890, 0.35));
  const sun = new THREE.DirectionalLight(0xfff2e0, 1.9);
  sun.position.copy(M(330, 560, 420)); sun.target.position.copy(M(120, 160, 0));
  sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); sun.shadow.bias = -0.0006; sun.shadow.normalBias = 0.6;
  Object.assign(sun.shadow.camera, { left: -330, right: 330, top: 330, bottom: -330, near: 50, far: 1500 });
  G.scene.add(sun, sun.target);
  const sky = new THREE.PointLight(0xffffff, 6000, 320, 2); sky.position.copy(M(80, 50, 110)); G.scene.add(sky);
  new ResizeObserver(resize).observe(host);
  resize(); setCamera("overview");
  let visible = true;
  new IntersectionObserver((e) => (visible = e[0].isIntersecting)).observe(host);
  (function loop() {
    requestAnimationFrame(loop);
    if (!visible || document.hidden) return;
    if (G.ctl.update() || G.dirty) { fadeWalls(); r.render(G.scene, G.cam); G.dirty = false; }
  })();
}
function resize() {
  const w = G.host.clientWidth, h = G.host.clientHeight;
  if (!w || !h) return;
  G.renderer.setSize(w, h, false); G.cam.aspect = w / h; G.cam.updateProjectionMatrix(); G.dirty = true;
}
const CAMS = {
  overview: { label: "Overview", pos: [380, 400, 270], look: [100, 115, 15], fov: 38 },
  plan: { label: "Plan", pos: [120, 150.5, 640], look: [120, 150, 0], fov: 38 },
  living: { label: "From the living room", pos: [228, 250, 60], look: [60, 95, 40], fov: 62 },
  hall: { label: "From the hallway", pos: [78, 222, 62], look: [70, 30, 38], fov: 68 },
  child: { label: "5-year-old's eyes", pos: [150, 150, 39], look: [20, 80, 34], fov: 68 },
};
function setCamera(name) {
  const c = CAMS[name]; view.cam = name;
  if (!G.scene) return;
  G.cam.position.copy(M(...c.pos)); G.ctl.target.copy(M(...c.look)); G.cam.fov = c.fov;
  G.cam.updateProjectionMatrix(); G.ctl.update(); G.dirty = true;
}
function fadeWalls() {
  // a wall between the camera and the room goes faint, so the kitchen is always in view
  for (const w of G.walls) {
    const toCam = G.cam.position.clone().sub(w.center);
    const hide = toCam.dot(w.out) > 0 && view.cam !== "living" && view.cam !== "hall" && view.cam !== "child";
    w.mesh.material.opacity = hide ? 0.07 : 1; w.mesh.material.transparent = hide; w.mesh.castShadow = !hide;
    w.mesh.material.depthWrite = !hide;
  }
}

function rebuild() {
  if (!G.scene) return;
  const s = S, L = layoutOf(s), cat = T.catalog, line = cat.cab_line[s.cab_line];
  if (G.root) { G.scene.remove(G.root); G.root.traverse((o) => { if (o.geometry) o.geometry.dispose(); }); }
  const root = (G.root = new THREE.Group()); G.scene.add(root); G.walls = [];
  const lowerHex = T.colors[s.lower_color].hex, upperHex = T.colors[s.upper_color].hex;
  const counter = cat.counter[s.counter], floor = cat.floor[s.floor], splash = cat.backsplash[s.backsplash];
  const stone = stoneTex(counter);
  const mats = {
    lower: glossMat(lowerHex, line.sheen), upper: glossMat(upperHex, line.sheen),
    toe: mat("#2a2a2a"), recess: mat(shade(lowerHex, 0.35), { roughness: 0.9 }), recessUp: mat(shade(upperHex, 0.55), { roughness: 0.9 }),
    steel: mat("#c3c6ca", { metalness: 0.85, roughness: 0.32 }), steelDark: mat("#8d9196", { metalness: 0.9, roughness: 0.3 }),
    blackGlass: new THREE.MeshPhysicalMaterial({ color: 0x111316, roughness: 0.08, clearcoat: 1 }),
    counter: mat("#ffffff", { map: stone, roughness: s.counter === "butcher" ? 0.6 : 0.22 }),
    begripa: mat(BEGRIPA[view.begripa], { roughness: 0.5 }),
  };
  // the room
  const center = M(136, 188, 48);
  for (const b of T.room) {
    if (b.kind === "furniture" || b.kind === "rug") { if (view.furniture) box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, mat(b.kind === "rug" ? "#aab3b8" : b.id.startsWith("f_sofa") ? "#5c5a66" : "#b98a55", { roughness: 0.85 }), { cast: b.kind !== "rug" }); continue; }
    if (b.kind === "floor") { box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, mat("#ffffff", { map: plankTex(floor, b.dx, b.dy), roughness: 0.55 }), { cast: false }); continue; }
    if (b.kind === "wall") {
      const m = box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, mat("#f1ede4", { roughness: 0.95 }));
      const c = M(b.x + b.dx / 2, b.y + b.dy / 2, 48), out = c.clone().sub(center); out.y = 0;
      // outward is the wall's thin axis, pointing away from the room
      if (b.dx < b.dy) out.set(Math.sign(out.x) || 1, 0, 0); else out.set(0, 0, Math.sign(out.z) || 1);
      G.walls.push({ mesh: m, center: c, out });
      continue;
    }
    const look = { post: mat("#f4f0e8"), brick: mat("#ffffff", { map: brickTex(), roughness: 0.95 }),
      glass: new THREE.MeshPhysicalMaterial({ color: 0xbcd9ea, transparent: true, opacity: 0.28, roughness: 0.05 }),
      stair: mat("#3b342d"), rail: mat("#6b4329", { roughness: 0.5, transparent: true, opacity: 0.3 }) }[b.kind];
    box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, look, { cast: b.kind !== "glass" && b.kind !== "rail" });
    if (b.kind === "rail") box(root, b.x, b.y, b.z + b.dz - 2, b.dx, b.dy, 2.5, mat("#6b4329", { roughness: 0.5 }));
  }
  // the kitchen
  for (const i of L.boxes) {
    const b = T.boxes[i];
    if (b.kind === "base" || b.kind === "upper" || b.kind === "tall") drawCabinet(root, b, mats, s, line);
    else if (b.kind === "panel" || b.kind === "filler") box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, b.role === "upper" ? mats.upper : mats.lower);
    else if (b.kind === "appliance") drawAppliance(root, b, mats);
    else if (b.kind === "counter") box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, mats.counter);
    else if (b.kind === "window") { box(root, b.x - 2, b.y - 5.5, b.z - 2, b.dx + 4, 6.6, b.dz + 4, mat("#ffffff"), { cast: false }); box(root, b.x, b.y - 5.6, b.z, b.dx, 6.9, b.dz, new THREE.MeshBasicMaterial({ color: 0xd8ecf7 }), { cast: false }); }
    else if (b.kind === "shelf") box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, mat("#e9e3d5"));
    else if (b.kind === "door") box(root, b.x, b.y, b.z, b.dx, b.dy, b.dz, mat("#f4f0e8"));
    else if (b.kind === "stool") {
      const seat = new THREE.Mesh(new THREE.CylinderGeometry(7, 7, 1.5, 24), mat("#3f4347", { metalness: 0.4, roughness: 0.5 })); seat.position.copy(M(b.x + 7.5, b.y + 7.5, 25)); seat.castShadow = true;
      const post = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 4.5, 24.5, 12), mats.steelDark); post.position.copy(M(b.x + 7.5, b.y + 7.5, 12.2)); post.castShadow = true;
      root.add(seat, post);
    } else if (b.kind === "sink") {
      const apron = b.id === "sink" && cat.sink[s.sink].style === "apron";
      box(root, b.x, b.y + (apron ? 5 : 0), 36 - 0.3, b.dx, b.dy, 0.4, apron ? mat("#f7f7f4", { roughness: 0.2 }) : mats.steelDark, { cast: false });
      if (apron) box(root, b.x, 23.4, 27, b.dx, 2.6, 9.1, mat("#f7f7f4", { roughness: 0.2 }));
      // faucet: behind the wall sink, at the island sink's south side
      const fx = b.x + b.dx / 2, fy = b.id === "sink" ? b.y - 1 : b.y + b.dy + 1.5, dir = b.id === "sink" ? 1 : -1;
      box(root, fx - 0.6, fy - 0.6, 36, 1.2, 1.2, 13, mats.steel); box(root, fx - 0.6, dir > 0 ? fy : fy - 7, 48, 1.2, 7.6, 1.2, mats.steel);
    }
  }
  // backsplash, on the two walls between counter and uppers
  if (splash.usd_sqft > 0) {
    const sm = s.backsplash === "quartz_slab" ? mat("#ffffff", { map: stone, roughness: 0.25 }) : mat(splash.hex, { roughness: 0.3 });
    const w1End = s.fridge_at === "hall" ? 153 : 189;
    box(root, 0, 0, 36, 0.4, w1End, 18, sm, { cast: false }); box(root, 0, 0, 36, 138, 0.4, 18, sm, { cast: false });
  }
  // flow: the cook's triangle on the floor, and the aisle widths
  if (view.flow) {
    const f = L.flow, wet = f.pt_prep || f.pt_sink, pts = [wet, f.pt_range, f.pt_fridge, wet];
    const ok = L.checks.C3.ok && L.checks.C4.ok, col = ok ? 0x2e7d4f : 0xd03b3b;
    const line3 = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts.map((p) => M(p[0], p[1], 0.6))), new THREE.LineBasicMaterial({ color: col, depthTest: false }));
    line3.renderOrder = 9; root.add(line3);
    const tube = (a, b2) => { const g = new THREE.TubeGeometry(new THREE.LineCurve3(M(a[0], a[1], 0.7), M(b2[0], b2[1], 0.7)), 1, 0.7, 8); const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: col, depthTest: false })); m.renderOrder = 9; root.add(m); };
    for (let i = 0; i < 3; i++) {
      tube(pts[i], pts[i + 1]);
      const t = label(L.legs[i].toFixed(1) + " ft", ok ? "#1f6a3f" : "#b3261e");
      t.position.copy(M((pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2, 5)); root.add(t);
    }
    if (f.island_rect) {
      const a = label(s.island_aisle + " in aisle", L.checks.C6.ok ? "#1f6a3f" : L.checks.C5.ok ? "#8a5a00" : "#b3261e");
      a.position.copy(M((25.5 + f.island_rect[0]) / 2, f.island_rect[1] + 12, 40)); root.add(a);
    }
  }
  // people, for scale and for the two days the brief names
  if (view.people !== "none") {
    const f = L.flow, k = T.people, isl = f.island_rect;
    const wet = f.pt_prep || f.pt_sink, east = isl ? isl[2] + 10 : 110;
    if (view.people === "weeknight") {
      person(root, wet[0] - 13, wet[1], 67, "#3f6fae", "cook");
      person(root, east, isl ? isl[1] + 20 : 100, k.kid_big, "#d07a3a", "8 yr");
      person(root, east, isl ? isl[3] - 20 : 130, k.kid_small, "#c7559a", "5 yr");
    } else {
      person(root, f.pt_range[0] + 13, f.pt_range[1], 70, "#3f6fae", "cook");
      person(root, wet[0] - 13 + (f.pt_prep ? 0 : 0), f.pt_prep ? wet[1] : wet[1] + 13, 64, "#3d8f6b", "prep");
      person(root, f.pt_sink[0] + 28, f.pt_sink[1] + 13, 66, "#8a63b5", "dishes");
      person(root, f.pt_fridge[0] + (s.fridge_at === "hall" ? 14 : 0), f.pt_fridge[1] + (s.fridge_at === "hall" ? 0 : 14), 68, "#b0503f", "guest");
      person(root, east, isl ? isl[1] + 20 : 100, k.kid_big, "#d07a3a", "8 yr");
      person(root, s.microwave_at === "pantry" && s.fridge_at === "hall" ? 163 : east, s.microwave_at === "pantry" && s.fridge_at === "hall" ? 50 : (isl ? isl[3] - 20 : 130), k.kid_small, "#c7559a", "5 yr");
    }
  }
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
    group("Handles", null, choice("handles", line.handles.map((h) => [h, cat.handles[h].label])),
      S.handles === "begripa" ? el("div", { class: "cfg-swatches" }, Object.entries(BEGRIPA).map(([n, hex]) => el("button", { class: "cfg-swatch" + (view.begripa === n ? " is-on" : ""), type: "button", title: "BEGRIPA " + n, "aria-label": "BEGRIPA " + n, style: "--sw:" + hex, onclick: () => { view.begripa = n; save(); render(); } }))) : null),
    group("Refrigerator", null, choice("fridge_at", catOpts("fridge_at"))),
    group("Island", "64 in is the contractor's. 40 in deep gives the seats knee room; 48 in of aisle lets two cooks pass.",
      choice("island_len", [[64, "64 in, two seats"], [76, "76 in, three seats"], [0, "No island"]]),
      el("div", { class: "cfg-row" },
        el("div", {}, el("h4", { text: "Top depth" }), choice("island_top_d", [[40, "40 in", noIsland], [36, "36 in", noIsland]], { delta: false })),
        el("div", {}, el("h4", { text: "Aisle to the range" }), choice("island_aisle", [[48, "48 in", noIsland], [42, "42 in", noIsland]], { delta: false }))),
      el("h4", { text: "Island prep sink" }), choice("prep_sink", [[true, "Yes", noIsland], [false, "No"]])),
    group("Old refrigerator alcove", alcove ? "The refrigerator is still in it." : "Assumed 40 in wide and 34 in deep. Measure it.",
      choice("pantry", [["open", cat.pantry.open.label, alcove], ["door", cat.pantry.door.label, alcove], ["cabinets", cat.pantry.cabinets.label, alcove]])),
    group("Microwave", null, choice("microwave_at", [["pantry", cat.microwave_at.pantry.label, alcove], ["island", cat.microwave_at.island.label, noIsland], ["counter", cat.microwave_at.counter.label]])),
    group("Countertop", null, choice("counter", catOpts("counter"), { sub: (k) => "$" + cat.counter[k].usd_sqft + " / sq ft installed" })),
    group("Backsplash", null, choice("backsplash", catOpts("backsplash"))),
    group("Sink and faucet", null, choice("sink", catOpts("sink"), { sub: (k) => usd(cat.sink[k].usd) }), choice("faucet", catOpts("faucet"), { sub: (k) => usd(cat.faucet[k].usd) })),
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
    seg("People", [["weeknight", "Weeknight"], ["holiday", "Holiday"], ["none", "Empty"]], view.people, (v) => { view.people = v; save(); render(); }),
    seg("Overlays", [["flow", (view.flow ? "✓ " : "") + "Cook's triangle"], ["furniture", (view.furniture ? "✓ " : "") + "Furniture"]], null, (v) => { view[v] = !view[v]; save(); render(); }));
}
function render() { renderControls(); renderSummary(); renderView(); rebuild(); }

function summaryText() {
  const b = bill(S), cat = T.catalog, c = checks(S);
  return ["Edmonds kitchen: my configuration", "Total " + usd(b.total) + " of " + usd(T.money.budget),
    "Cabinets: " + cat.cab_line[S.cab_line].label, "Lower: " + T.colors[S.lower_color].name + " " + (T.colors[S.lower_color].ral || ""), "Upper: " + T.colors[S.upper_color].name + " " + (T.colors[S.upper_color].ral || ""),
    "Handles: " + cat.handles[S.handles].label, "Refrigerator: " + cat.fridge_at[S.fridge_at].label,
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
  try { initScene($("#cfg-stage")); } catch (e) { $("#cfg-stage").textContent = "This browser could not start WebGL, so the room is not drawn. The options, the bill and the answers below still work."; G.scene = null; }
  $("#cfg-reset").addEventListener("click", () => { S = normalise(recorded()); save(); render(); });
  $("#cfg-copy").addEventListener("click", async (e) => { try { await navigator.clipboard.writeText(summaryText()); e.target.textContent = "Copied"; } catch (err) { prompt("Copy your configuration:", summaryText()); } setTimeout(() => (e.target.textContent = "Copy my configuration"), 1600); });
  render();
  window.__cfg = { get total() { return bill(S).total; }, recordedTotal: T.recorded_total, set, get S() { return S; }, setCamera, checks: () => checks(S) };
}
main();
