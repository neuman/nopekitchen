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
    "door": ("#EFEBE2", 1, 0.0, 0.8), "stool": ("#6E7479", 1, 0.6, 0.4), "faucet": ("#C9CBCD", 1, 0.9, 0.3), "knife_strip": ("#2B2D30", 1, 0.6, 0.4),
    "sofa": ("#B4532A", 1, 0.0, 0.95), "firebox": ("#6E5A40", 1, 0.0, 0.95), "wallshelf": ("#9A5A2E", 1, 0.0, 0.7),
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
    # this view draws no ceiling, so a post stops at the wall plate here; the model
    # and the configurator carry it up to the vault
    shell = [dict(b, dz=min(b["dz"], k.WALL_H - b["z"])) if b["kind"] == "post" else b for b in ctx.params["room"]]
    everything = shell + list(boxes)
    src = ctx.write_asset("twin.glb", glb(everything, looks))
    ctx.write_asset("twin.json", json.dumps(configurator(ctx, k), separators=(",", ":")))
    parts: dict[str, list[str]] = {}
    names = {"lower": "Lower cabinets", "upper": "Upper cabinets", "counter": "Countertops",
             "wall": "Walls", "floor": "Floor", "furniture": "Furniture", "sofa": "Furniture", "firebox": "Fireplace", "wallshelf": "Furniture"}
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
    "C13": "window_gap_in", "C15": "collision_count", "C16": "blocked_door_count", "C17": "walkway_min_in",
    "C18": "stow_unplaced_count", "C19": "stow_mixed_count", "C20": "stow_split_count", "C21": "stow_far_ft",
    "C22": "stow_kid_over_in", "C23": "stow_adult_margin_in",
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


# --------------------------------------------------------------------------- #
# the exploded view: how the contents of each compartment leave it
# --------------------------------------------------------------------------- #
TOWER_Z0, TOWER_STEP = 39.0, 13.0     # in: the lowest layer of a base cabinet's contents, shown just above counter height; layer to layer


def explode(k, boxes: list[dict], bays: list[dict]) -> dict:
    """{bay id: [sx, sy, lx, ly, rise, wave, waves]}, for the configurator's slider.

    What stands in a bay first slides out of the cabinet by (sx, sy), then rises by
    `rise` while it drifts sideways by (lx, ly). A drawing aid: nothing checks it.

    A wall cabinet's shelves slide straight out and spread a little apart. A base
    cabinet empties from the bottom up, one drawer or shelf at a time (`wave` of
    `waves`), and its contents hang in layers above counter height in front of it:
    the bottom drawer's on top, so nothing passes through anything. The pantry's
    shelves come out of the recess as they stand. Where two cabinets' contents would
    hang in the same place (at the inside corner, beside the pantry), one is moved
    along its run.
    """
    by = {b["id"]: b for b in boxes}
    hosts: dict[str, list[dict]] = {}
    for b in bays:
        hosts.setdefault(b["host"], []).append(b)
    out = {}
    taken = [(b["x"], b["y"], b["x"] + b["dx"], b["y"] + b["dy"]) for b in boxes if b["kind"] == "counter"]
    pantry = [b for b in bays if b["unit"] == "pantry"]
    if pantry:
        for b in pantry:
            out[b["id"]] = [-34.0, 0.0, 0.0, 0.0, 0.0, 0, 1]
        taken.append((min(b["x"] for b in pantry) - 34.0, min(b["y"] for b in pantry),
                      max(b["x"] + b["dx"] for b in pantry) - 34.0, max(b["y"] + b["dy"] for b in pantry)))
    towers = []
    for host, bs in hosts.items():
        if bs[0]["unit"] == "pantry":
            continue
        if bs[0]["kind"] == "counter":
            for b in bs:
                out[b["id"]] = [0.0, 0.0, 0.0, 0.0, 0.0, 0, 1]
            continue
        box, bs = by[host], sorted(bs, key=lambda b: b["z"])
        (rx, ry), (ox, oy) = k._FRAME[bs[0]["face"]]
        front = box["x"] + box["dx"] if ox > 0 else box["x"] if ox < 0 else box["y"] + box["dy"] if oy > 0 else box["y"]

        def clear(b, gap):      # how far a bay slides for its back edge to stand `gap` in front of the cabinet's face
            back = b["x"] if ox > 0 else b["x"] + b["dx"] if ox < 0 else b["y"] if oy > 0 else b["y"] + b["dy"]
            return abs(front - back) + gap

        if box["kind"] != "base":
            for i, b in enumerate(bs):
                d = clear(b, 1.75)
                out[b["id"]] = [ox * d, oy * d, 0.0, 0.0, round(i * 3.2, 2), 0, 1]
            continue
        rect = [1e9, 1e9, -1e9, -1e9]
        for j, b in enumerate(bs):
            d = clear(b, 1.75)
            out[b["id"]] = [ox * d, oy * d, 0.0, 0.0, round(TOWER_Z0 + TOWER_STEP * (len(bs) - 1 - j) - b["z"], 2), j, len(bs)]
            rect = [min(rect[0], b["x"] + ox * d), min(rect[1], b["y"] + oy * d),
                    max(rect[2], b["x"] + b["dx"] + ox * d), max(rect[3], b["y"] + b["dy"] + oy * d)]
        towers.append((rect[0] + rect[1], host, bs, rect, (abs(rx), abs(ry))))

    def over(r):
        a = (r[0] + 0.75, r[1] + 0.75, r[2] - 0.75, r[3] - 0.75)
        return sum(max(0.0, min(a[2], t[2]) - max(a[0], t[0])) * max(0.0, min(a[3], t[3]) - max(a[1], t[1])) for t in taken)

    def inside(r, wall):     # a wall run's contents stay in front of their own wall; the island's hang where they are
        return not wall or (r[0] >= 0.0 and r[1] >= 0.0 and r[2] <= k.CONFIG.wall2_len and r[3] <= k.CONFIG.wall1_len)

    for _d, host, bs, rect, (ax, ay) in sorted(towers, key=lambda t: (t[0], t[1])):     # from the inside corner outward
        moved = lambda sh: [rect[0] + ax * sh, rect[1] + ay * sh, rect[2] + ax * sh, rect[3] + ay * sh]      # noqa: E731
        best = min((sh for sh in range(-40, 41) if inside(moved(sh), host.startswith("w"))),
                   key=lambda sh: (round(over(moved(sh)), 1), abs(sh), -sh), default=0)
        for b in bs:
            out[b["id"]][2:4] = [float(ax * best), float(ay * best)]
        taken.append((rect[0] + ax * best, rect[1] + ay * best, rect[2] + ax * best, rect[3] + ay * best))
    return out


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

    # where everything goes: the things once, then for each layout its compartments and what stands in each
    inv = k.inventory
    thing_no = {t["id"]: i for i, t in enumerate(inv.THINGS)}
    bay_table, put_table, stow_table, tables = [], [], [], ({}, {}, {})

    def intern(rows, seen, row):
        key = json.dumps(row, sort_keys=True)
        if key not in seen:
            seen[key] = len(rows)
            rows.append(row)
        return seen[key]

    def stow_of(d):
        st = d["stow"]
        how = explode(k, d["boxes"], st["bays"])
        no = {}
        for b in st["bays"]:
            row = {n: (round(b[n], 2) if isinstance(b[n], float) else b[n]) for n in ("id", "host", "unit", "kind", "face", "x", "y", "z", "dx", "dy", "dz", "front", "words")}
            row["place"] = k.place_words(b["unit"])
            row["e"] = how[b["id"]]
            no[b["id"]] = intern(bay_table, tables[0], row)
        puts = [intern(put_table, tables[1], [thing_no[p["t"]], no[p["bay"]], p["x"], p["y"], p["z"], p["rot"]]) for p in st["placed"]]
        return intern(stow_table, tables[2], {
            "bays": sorted(no.values()), "items": puts, "unplaced": [thing_no[t] for t in st["unplaced"]],
            "notes": {"unplaced": d["stow_unplaced"], "mixed": d["stow_mixed"], "split": d["stow_split"], "far": d["stow_far_what"]}})

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
            "opens": [ref(o) for o in d["opens"]],
            "blocked": d["blocked_doors"], "hits": d["collision_pairs"], "ways": d["walkways"],
            "stow": stow_of(d),
        }
    rec = k.build(k.CONFIG)
    cfg = dataclasses.asdict(k.CONFIG)
    return {
        "note": "Generated by views/twin.py from model/kitchen.py. Do not edit.",
        "recorded": cfg, "recorded_key": layout_key(k.CONFIG),
        "recorded_total": round(rec["total_usd"], 2),
        "room": rec["room"], "vault": [list(p) for p in k.VAULT], "wall_h": k.WALL_H, "soffit": {"x0": -5.0, "x1": k.CONFIG.wall2_len, "y": k.soffit_y(k.CONFIG), "t": 5.0, "z": k.WALL_H},
        "table_y": k.TABLE_Y,
        "knife_strips": {key: (lambda b: b and {n: b[n] for n in ("x", "y", "z", "dx", "dy", "dz", "face")})(
            k.knife_strip(dataclasses.replace(k.CONFIG, knife_strip=key, fridge_at="hall"))) for key in k.CATALOG["knife_strip"]},
        "sconces": [list(q) for q in k.SCONCES], "boxes": table, "layouts": layouts,
        "things": [{n: t[n] for n in ("id", "label", "group", "w", "d", "h", "parts", "seen", "note", "unsure")} for t in inv.THINGS],
        "kinds": {gid: {"label": g["label"], "short": g["short"], "cat": g["cat"]} for gid, g in inv.GROUPS.items()}, "cats": inv.CATEGORIES,
        "bays": bay_table, "puts": put_table, "stows": stow_table,
        "reach": {"kid_max": round(rec["stow_kid_max_in"], 1), "adult_min": round(rec["stow_adult_min_in"], 1)},
        "catalog": k.CATALOG, "colors": k.COLORS, "claims": acceptances,
        "money": {"budget": k.CONFIG.budget_usd, "tax": k.CONFIG.sales_tax, "contingency": k.CONFIG.contingency,
                  "permits": k.PERMITS_USD, "floor_area": k.CONFIG.floor_area_sqft,
                  "floor_order": round(rec["floor_order_sqft"], 1)},
        "people": {"kid_small": k.CONFIG.kid_small_h, "kid_big": k.CONFIG.kid_big_h},
        "wear_limit": acceptances.get("C14", {}).get("limit"),
    }
