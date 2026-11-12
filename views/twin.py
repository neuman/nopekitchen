"""The digital twin, in two forms, both generated from model/kitchen.py.

`twin`   a GLB of the RECORDED design in its room, for the engineering page's
         viewer. Node names are the model's box ids (`w1_b33`, `isl_top`,
         `fridge`, ...): a locator addresses a cabinet by that name.

`twin.json`  the configurator's data, for the marketing page: the room, the
         catalog, and every layout the configurator offers, each with its boxes,
         its quantities and the model's own answer to each layout claim. The
         browser draws and adds up; it does not measure a kitchen.

Standard library only: the GLB is written by hand (one unit cube, a node per
box), so the site needs nothing installed.
"""
from __future__ import annotations

import dataclasses
import itertools
import json
import os
import struct

from nopekit.modelio import load_path
from nopekit.models import View, ViewKind
from nopekit.site import ViewContext, viewgen

IN = 0.0254

# role -> (hex, alpha, metallic, roughness). Lower, upper, counter and floor take
# the recorded selection's colour instead.
LOOK = {
    "wall": ("#EFEBE2", 0.30, 0.0, 0.9), "floor": ("#C8A67A", 1, 0.0, 0.7),
    "post": ("#F2EEE6", 1, 0.0, 0.9), "brick": ("#A8674B", 1, 0.0, 0.95),
    "glass": ("#BFD9E6", 0.35, 0.0, 0.1), "stair": ("#3A3530", 1, 0.0, 0.9),
    "rail": ("#5B3A26", 1, 0.0, 0.6), "furniture": ("#8A6A4A", 1, 0.0, 0.7),
    "rug": ("#9AA3A8", 1, 0.0, 1.0), "lower": ("#0F5C8C", 1, 0.0, 0.12),
    "upper": ("#E3D9C6", 1, 0.0, 0.12), "counter": ("#F2F0EC", 1, 0.0, 0.3),
    "range": ("#B9BDC2", 1, 0.9, 0.35), "fridge": ("#B9BDC2", 1, 0.9, 0.35),
    "dishwasher": ("#B9BDC2", 1, 0.9, 0.35), "hood": ("#B9BDC2", 1, 0.9, 0.35),
    "microwave": ("#2B2D30", 1, 0.5, 0.4), "sink": ("#9EA3A8", 1, 0.9, 0.3),
    "window": ("#CFE6F2", 0.5, 0.0, 0.1), "shelf": ("#E8E2D4", 1, 0.0, 0.8),
    "door": ("#EFEBE2", 1, 0.0, 0.8), "stool": ("#6E7479", 1, 0.6, 0.4),
}


def _lin(hex_):
    out = []
    for i in (1, 3, 5):
        v = int(hex_[i:i + 2], 16) / 255.0
        out.append(round(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4, 5))
    return out


def _cube():
    """A unit cube from (0,0,0) to (1,1,1): 24 vertices with normals, 36 indices."""
    faces = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]),
             ((-1, 0, 0), [(0, 0, 1), (0, 1, 1), (0, 1, 0), (0, 0, 0)]),
             ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]),
             ((0, -1, 0), [(0, 0, 1), (0, 0, 0), (1, 0, 0), (1, 0, 1)]),
             ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
             ((0, 0, -1), [(1, 0, 0), (0, 0, 0), (0, 1, 0), (1, 1, 0)])]
    pos, nor, idx = [], [], []
    for n, quad in faces:
        b = len(pos)
        pos += quad
        nor += [n] * 4
        idx += [b, b + 1, b + 2, b, b + 2, b + 3]
    return pos, nor, idx


def glb(boxes: list[dict], looks: dict) -> bytes:
    pos, nor, idx = _cube()
    blob = b"".join(struct.pack("<3f", *p) for p in pos)
    blob += b"".join(struct.pack("<3f", *n) for n in nor)
    blob += struct.pack(f"<{len(idx)}H", *idx)
    roles = sorted({b["role"] for b in boxes})
    materials, meshes = [], []
    for r in roles:
        hex_, alpha, metal, rough = looks.get(r, ("#CCCCCC", 1, 0.0, 0.8))
        m = {"name": r, "pbrMetallicRoughness": {"baseColorFactor": _lin(hex_) + [alpha],
                                                 "metallicFactor": metal, "roughnessFactor": rough}}
        if alpha < 1:
            m["alphaMode"] = "BLEND"
        materials.append(m)
        meshes.append({"name": r, "primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1},
                                                  "indices": 2, "material": len(materials) - 1}]})
    nodes = []
    for b in boxes:
        # model (x east, y south, z up), inches -> glTF (X east, Y up, Z south), metres
        nodes.append({"name": b["id"], "mesh": roles.index(b["role"]),
                      "translation": [round(b["x"] * IN, 5), round(b["z"] * IN, 5), round(b["y"] * IN, 5)],
                      "scale": [round(max(b["dx"], 0.05) * IN, 5), round(max(b["dz"], 0.05) * IN, 5),
                                round(max(b["dy"], 0.05) * IN, 5)]})
    doc = {
        "asset": {"version": "2.0", "generator": "views/twin.py"},
        "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes, "meshes": meshes, "materials": materials,
        "buffers": [{"byteLength": len(blob)}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 288, "target": 34962},
                        {"buffer": 0, "byteOffset": 288, "byteLength": 288, "target": 34962},
                        {"buffer": 0, "byteOffset": 576, "byteLength": 72, "target": 34963}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": 24, "type": "VEC3", "min": [0, 0, 0], "max": [1, 1, 1]},
                      {"bufferView": 1, "componentType": 5126, "count": 24, "type": "VEC3"},
                      {"bufferView": 2, "componentType": 5123, "count": 36, "type": "SCALAR"}],
    }
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    blob += b"\0" * (-len(blob) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    return (struct.pack("<4sII", b"glTF", 2, total) + struct.pack("<I4s", len(js), b"JSON") + js
            + struct.pack("<I4s", len(blob), b"BIN\0") + blob)


def _model(ctx):
    return load_path(os.path.join(ctx.root, "model", "kitchen.py"))


@viewgen(id="twin", kind=ViewKind.MODEL3D, title="The kitchen in its room", order=1)
def twin(ctx: ViewContext) -> View | None:
    boxes = ctx.params.get("boxes")
    if not boxes:
        return None
    k = _model(ctx)
    cfg = ctx.params["config"]
    looks = dict(LOOK)
    looks["lower"] = (k.COLORS[cfg["lower_color"]]["hex"], 1, 0.0, 0.12)
    looks["upper"] = (k.COLORS[cfg["upper_color"]]["hex"], 1, 0.0, 0.12)
    looks["counter"] = (k.CATALOG["counter"][cfg["counter"]]["hex"], 1, 0.0, 0.3)
    looks["floor"] = (k.CATALOG["floor"][cfg["floor"]]["hex"], 1, 0.0, 0.7)
    everything = list(ctx.params["room"]) + list(boxes)
    src = ctx.write_asset("twin.glb", glb(everything, looks))
    ctx.write_asset("twin.json", json.dumps(configurator(ctx, k), separators=(",", ":")))
    parts: dict[str, list[str]] = {}
    names = {"lower": "Lower cabinets", "upper": "Upper cabinets", "counter": "Countertops",
             "wall": "Walls", "floor": "Floor", "furniture": "Furniture"}
    for b in everything:
        name = names.get(b["role"])
        if name:
            parts.setdefault(name, []).append(b["id"])
    return View(id="twin", kind=ViewKind.MODEL3D, title="The kitchen in its room", src=src,
                description="The recorded design in its room. The kitchen's walls are the contractor's "
                            "measurements; the rest of the room is approximate.",
                meta={"parts": parts, "units": "m", "up": "+Y"})


# --------------------------------------------------------------------------- #
# the configurator's data
# --------------------------------------------------------------------------- #
#: claim -> the derived value the model answers it with. The gates read the same keys.
LAYOUT_CLAIMS = {
    "C3": "triangle_longest_ft", "C4": "triangle_total_ft", "C5": "work_aisle_in",
    "C6": "work_aisle_in", "C7": "dishwasher_standing_in", "C8": "island_seats",
    "C9": "island_knee_in", "C10": "microwave_over_reach_in", "C12": "run_fill_error_in",
    "C13": "window_gap_in",
}
QTY = {"cab_line": "cab_run_lf", "cab_install": "cab_run_lf", "handles": "fronts",
       "counter": "counter_sqft", "backsplash": "backsplash_sqft"}


def _holds(comparator, value, limit):
    return {"<=": value <= limit, ">=": value >= limit, "<": value < limit, ">": value > limit}[comparator]


def layout_key(c) -> str:
    return "|".join(str(v) for v in (c.fridge_at, c.pantry, int(c.island_len), int(c.island_top_d),
                                     int(c.island_aisle), int(c.prep_sink), c.microwave_at))


def variants(k):
    """Every layout the configurator offers. An island-less kitchen has no island
    sink or drawer microwave; with the refrigerator in the alcove there is no pantry."""
    base = k.CONFIG
    for fridge, pantry, isl, depth, aisle, prep, mw in itertools.product(
            ("hall", "alcove"), ("open", "door", "cabinets"), (0.0, 64.0, 76.0), (36.0, 40.0),
            (42.0, 48.0), (False, True), ("pantry", "island", "counter")):
        if fridge == "alcove" and (pantry != "open" or mw == "pantry"):
            continue
        if isl == 0 and (prep or mw == "island" or depth != 40.0 or aisle != 48.0):
            continue
        yield dataclasses.replace(base, fridge_at=fridge, pantry=pantry, island_len=isl, island_top_d=depth,
                                  island_aisle=aisle, prep_sink=prep, microwave_at=mw)


def configurator(ctx, k) -> dict:
    acceptances = {}
    for claim in ctx.ledger.claims:
        acc = getattr(claim, "acceptance", None)
        if acc is not None and getattr(acc, "limit", None) is not None:
            acceptances[claim.id] = {"statement": claim.statement, "comparator": acc.comparator.value,
                                     "limit": acc.limit, "units": acc.units}
    table, index, layouts = [], {}, {}

    def ref(box):
        key = json.dumps(box, sort_keys=True)
        if key not in index:
            index[key] = len(table)
            table.append(box)
        return index[key]

    for c in variants(k):
        d = k.build(c)
        checks = {}
        for cid, key in LAYOUT_CLAIMS.items():
            acc = acceptances.get(cid)
            if not acc:
                continue
            value = round(float(d[key]), 2)
            checks[cid] = {"value": value, "ok": _holds(acc["comparator"], value, acc["limit"])}
        fixed = [[l["ref"], l["description"], l["extended"], l["vendor"], l["url"], l["basis"]]
                 for l in d["bom"]["lines"]
                 if l["group"] in ("fixed", "fridge_at", "pantry", "prep_sink", "microwave_at", "floor_work")]
        layouts[layout_key(c)] = {
            "boxes": [ref(b) for b in d["boxes"]],
            "checks": checks,
            "qty": {g: round(d[q], 2) for g, q in QTY.items()},
            "fixed": fixed,
            "flow": {n: d[n] for n in ("pt_sink", "pt_range", "pt_fridge", "pt_prep", "island_rect")},
            "legs": [round(d["leg_wet_range_ft"], 1), round(d["leg_range_fridge_ft"], 1), round(d["leg_fridge_wet_ft"], 1)],
            "cleanup_ft": round(d["fridge_to_cleanup_sink_ft"], 1),
            "east_in": round(d["east_of_island_in"], 1),
        }
    rec = k.build(k.CONFIG)
    cfg = dataclasses.asdict(k.CONFIG)
    return {
        "note": "Generated by views/twin.py from model/kitchen.py. Do not edit.",
        "recorded": cfg, "recorded_key": layout_key(k.CONFIG),
        "recorded_total": round(rec["total_usd"], 2),
        "room": rec["room"], "boxes": table, "layouts": layouts,
        "catalog": k.CATALOG, "colors": k.COLORS, "claims": acceptances,
        "money": {"budget": k.CONFIG.budget_usd, "tax": k.CONFIG.sales_tax, "contingency": k.CONFIG.contingency,
                  "permits": k.PERMITS_USD, "floor_area": k.CONFIG.floor_area_sqft,
                  "floor_order": round(rec["floor_order_sqft"], 1)},
        "people": {"kid_small": k.CONFIG.kid_small_h, "kid_big": k.CONFIG.kid_big_h},
        "wear_limit": acceptances.get("C14", {}).get("limit"),
    }
