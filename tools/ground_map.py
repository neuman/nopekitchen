"""ground_map.py: finish the grounding map after `nopekit site build`.

Run through tools/build_site.sh, never alone: `site build` rewrites the files
this edits (site/data/map.json, site/data/page.json).

Why it exists (nopekit issues are filed for each):

  1. nopekit's trace moves numeric choices by 10% and skips every other kind, so
     a choice made from a catalog (the cabinet line, the faucet, the floor) or a
     yes/no (the island sink) had no line to anything. Here each such choice is
     swapped through every option the model offers and the model is built again;
     a derived value that changes for any option is one that choice moves.
  2. A claim no gate settles (an assumption, a physical test) had no line to the
     choices it is about. An assumption is joined to the choices the model says
     rest on it (`PARAMS[..]["grounded_by"]`); a physical claim to the choices
     named for it in LINKS below. These are declared, not measured, and the note
     under the map says so.
  3. The map's three columns are CHOICES, IMPLICATIONS and CLAIMS. The
     requirement cards ("what was asked") joined nothing, so they are left off
     the drawing; every claim row still names the requirements it serves.

It then proves the rule the map is held to: every group of choices reaches at
least one claim and every claim reaches at least one group of choices, directly
or through an implication. It exits 1 if one does not.
"""
from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: physical claim -> the choices it tests. Declared by hand from each claim's statement.
LINKS = {
    "P1": ["lower_color", "upper_color", "cab_line"],                 # the two colours, in this room
    "P2": ["microwave_at", "pantry", "island_len", "kid_small_h", "kid_big_h"],   # what the children reach, and where
    "P3": ["island_top_d", "island_aisle", "kitchen_w"],              # the island's seat edge against the table
    "P4": ["fridge_at", "fridge_d", "wall1_len"],                     # the refrigerator at the hall end
    "P5": ["pantry", "island_len", "fridge_at", "stow_pins"],         # the real things in the real cabinets
}

#: a claim a check does settle, whose value no single change from the recorded design moves, so the
#: swaps above draw it no line: the choices it depends on. Declared by hand from the placing rules
#: (stow in model/kitchen.py); each one's control in selftest/bad_configs.py shows the dependence.
DEPENDS = {
    "C18": ["fridge_at", "island_len", "pantry", "stow_pins"],        # what there is to put things in
    "C19": ["stow_pins"],                                             # the rules keep them apart; only a pin can mix them
}


def _load_model():
    spec = importlib.util.spec_from_file_location("kitchen", os.path.join(ROOT, "model", "kitchen.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["kitchen"] = mod
    spec.loader.exec_module(mod)
    return mod


def _scalars(d: dict) -> dict:
    """The derived values a swap can be seen to move: numbers, words, yes/no, and
    the bill as one value (`bom`), as the map's own stations name them."""
    out = {}
    for k, v in d.items():
        if k in ("boxes", "room", "opens", "config"):
            continue
        if k == "bom":
            out["bom"] = json.dumps(v, sort_keys=True)
        elif isinstance(v, (int, float, str, bool)) or v is None:
            out[k] = v
        elif isinstance(v, (list, dict)):
            out[k] = json.dumps(v, sort_keys=True)
    return out


def swaps(k) -> dict[str, set[str]]:
    """{choice: the derived values it moves}, for every choice that is not a number."""
    base_c = k.CONFIG
    base = _scalars(k.build(base_c))
    line = k.CATALOG["cab_line"][base_c.cab_line]
    options = {g: [o for o in k.CATALOG[g] if o != getattr(base_c, g)]
               for g in ("cab_line", "counter", "sink", "faucet", "knife_strip", "backsplash", "floor", "handles", "cab_install",
                         "floor_removal", "managed_by", "pantry", "microwave_at", "fridge_at")}
    options["lower_color"] = [c for c in list(line["lower"]) + list(k.COLORS) if c != base_c.lower_color]
    options["upper_color"] = [c for c in list(line["upper"]) + list(k.COLORS) if c != base_c.upper_color]
    options["prep_sink"] = [not base_c.prep_sink]
    moved: dict[str, set[str]] = {}
    for choice, alts in options.items():
        hit: set[str] = set()
        for alt in alts:
            c = dataclasses.replace(base_c, **{choice: alt})
            if choice == "fridge_at" and alt == "alcove":
                c = dataclasses.replace(c, pantry="open", microwave_at="counter")
            try:
                got = _scalars(k.build(c))
            except ValueError:
                continue
            hit |= {n for n in base if got.get(n) != base[n]}
        moved[choice] = hit
    return moved


def main() -> int:
    k = _load_model()
    map_path = os.path.join(ROOT, "site", "data", "map.json")
    page_path = os.path.join(ROOT, "site", "data", "page.json")
    m = json.load(open(map_path))
    page = json.load(open(page_path))

    nodes = {n["id"]: n for n in m["nodes"]}
    zones = [n for n in m["nodes"] if n["kind"] == "zone"]
    stations = [n for n in m["nodes"] if n["kind"] == "station"]
    zone_of = {member: z for z in zones for member in z["members"]}
    lines = {l["claim"]: l for l in m["lines"]}

    def add_unique(lst, item):
        if item not in lst:
            lst.append(item)

    def feed(zone, station, choice):
        row = next((f for f in m["feeds"] if f["zone"] == zone["id"] and f["to"] == station["id"]), None)
        if row is None:
            row = {"choices": [], "estimate": [], "to": station["id"], "zone": zone["id"]}
            m["feeds"].append(row)
        add_unique(row["choices"], choice)
        add_unique(zone["feeds"], station["id"])
        add_unique(zone.setdefault("moved", []), choice)
        add_unique(station["fed_by"], zone["id"])
        for cid in station.get("claims", []):
            add_unique(zone["claims"], cid)
            if cid in lines:
                add_unique(lines[cid]["fed_by"], zone["id"])

    def tap(zone, cid, choice):
        line = lines[cid]
        row = next((t for t in line["taps"] if t["zone"] == zone["id"]), None)
        if row is None:
            row = {"choices": [], "zone": zone["id"]}
            line["taps"].append(row)
        add_unique(row["choices"], choice)
        add_unique(line["fed_by"], zone["id"])
        add_unique(zone["claims"], cid)

    # 1. every catalog and yes/no choice, swapped through its options
    moved = swaps(k)
    reads: dict[str, set[str]] = {}          # claim -> the values its gates read
    for ev, claims in m["edges"]["settles"].items():
        vals = {v.split(":", 1)[1] for v in m["edges"]["reads"].get(ev, [])}
        for c in claims:
            reads.setdefault(c.split(":", 1)[1], set()).update(vals)
    swapped = []
    for choice, vals in sorted(moved.items()):
        zone = zone_of.get(choice)
        if zone is None or not vals:
            continue
        swapped.append(choice)
        through = set()
        for st in stations:
            if vals & set(st["members"]):
                feed(zone, st, choice)
                through.update(st.get("claims", []))
        for cid, read in reads.items():
            if cid in lines and cid not in through and vals & read:
                tap(zone, cid, choice)

    # 2. an assumption, to the choices that rest on it; a physical claim, to the choices it tests
    declared = []
    for row in k.PARAMS:
        for aid in row.get("grounded_by", []):
            zone = zone_of.get(row["name"])
            if zone is not None and aid in lines:
                tap(zone, aid, row["name"])
                declared.append(aid)
    for cid, choices in LINKS.items():
        for choice in choices:
            zone = zone_of.get(choice)
            if zone is not None and cid in lines:
                tap(zone, cid, choice)
                declared.append(cid)

    depends = []
    for cid, choices in DEPENDS.items():
        for choice in choices:
            zone = zone_of.get(choice)
            if zone is not None and cid in lines:
                tap(zone, cid, choice)
                depends.append(cid)

    # 3. three columns: choices, implications, claims
    cards = [n["id"] for n in m["nodes"] if n["kind"] == "requirement"]
    m["nodes"] = [n for n in m["nodes"] if n["kind"] != "requirement"]
    words = page.setdefault("words", {}).setdefault("lanes", {})
    words.update({"zones": "Choices", "stations": "Implications", "boards": "Claims"})

    # the rule: nothing floats
    floating = [z["title"] if "title" in z else z["key"] for z in zones if not z["claims"]]
    floating += [cid for cid, l in lines.items() if not l["fed_by"] and not l.get("sets")]
    for st in stations:
        if not st["fed_by"] or not st.get("claims"):
            floating.append(st["key"])

    t = m["trace"]
    text = t.get("text", "")
    cut = text.find("The test did not change")
    end = text.find("The test did not see")
    if cut >= 0:
        text = text[:cut] + (text[end:] if end >= 0 else "")
    t["text"] = (
        f"The {len(swapped)} choices made from a catalog or as a yes or no ({', '.join(swapped)}) cannot be changed by 10%. "
        "Each was swapped through every option the model offers and the model was built again; a line joins it to what changed. "
        f"The lines to the claims that no check settles ({', '.join(sorted(set(declared), key=lambda c: (c[0], int(c[1:]))))}) "
        "are declared in the model, not measured. "
        + (f"So are the lines to {' and '.join(sorted(set(depends)))}, which a check settles: no single change from the recorded design moves their value. "
           if depends else "")
        + text.replace("shared values", "implications")).strip()
    t["notice"] = t.get("notice", "").replace("shared value", "implication")
    for key, val in list((page.get("words", {}).get("trace") or {}).items()):
        if isinstance(val, str):
            page["words"]["trace"][key] = val.replace("shared values", "implications").replace("shared value", "implication")

    json.dump(m, open(map_path, "w"), indent=1, sort_keys=True)
    json.dump(page, open(page_path, "w"), indent=1, sort_keys=True)
    print(f"ground_map: {len(swapped)} catalog choices swapped, {len(m['feeds'])} feeds, "
          f"{sum(len(l['taps']) for l in m['lines'])} taps, {len(cards)} requirement cards left off")
    if floating:
        print("ground_map: FLOATING, joined to nothing: " + ", ".join(floating))
        return 1
    print(f"ground_map: all {len(zones)} groups of choices, {len(stations)} implications and {len(lines)} claims are joined")
    return 0


if __name__ == "__main__":
    sys.exit(main())
