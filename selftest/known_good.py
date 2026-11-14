"""The known-good kitchen: the design every control is one change away from.

Every Config field is stated, so an edit to the model's defaults does not move
it. It is the design recorded on 2026-11-12: refrigerator at the hall end, a
64 x 40 in island 48 in off both runs with a prep sink, microwave on the pantry
shelf, gloss lacquer fronts. All twenty-one kitchen gates pass on it.

CLAIMS holds the acceptance conditions it was calibrated against; a control
reads these, never the live claims/.
"""
from __future__ import annotations

import copy
import dataclasses
import os

from nopekit.modelio import flat_params, load_path
from nopekit.models import Claim, Ledger

_HERE = os.path.dirname(os.path.abspath(__file__))
kitchen = load_path(os.path.join(_HERE, os.pardir, "model", "kitchen.py"))

CONFIG: dict = {
    "wall1_len": 193.0, "wall2_len": 138.0, "window_w": 49.0, "kitchen_w": 141.0,
    "alcove_w": 40.0, "alcove_d": 34.0, "floor_area_sqft": 1257.0,
    "base_h": 34.5, "counter_t": 1.5, "upper_gap": 18.0, "base_d": 24.0,
    "counter_d": 25.5, "upper_d": 13.0, "fridge_d": 34.0,
    "fridge_at": "hall", "island_len": 64.0, "island_top_d": 40.0,
    "island_aisle": 48.0, "island_north_aisle": 48.0, "prep_sink": True,
    "pantry": "open", "microwave_at": "pantry", "stow_pins": "",
    "cab_line": "sektion_27e_gloss", "lower_color": "gentian", "upper_color": "oyster",
    "counter": "ikea_kasker", "sink": "ruvati_32", "faucet": "majsjon", "knife_strip": "backsplash",
    "backsplash": "tile", "floor": "lifeproof_sterling", "handles": "integrated",
    "managed_by": "self", "cab_install": "self_assemble", "floor_removal": "pro",
    "budget_usd": 60000.0, "sales_tax": 0.107, "contingency": 0.12,
    "kid_small_h": 43.0, "kid_big_h": 50.5,
}


def _acc(cid, statement, quantity, comparator, limit, units, tag):
    return {"id": cid, "statement": statement, "kind": "measurable",
            "acceptance": {"quantity": quantity, "comparator": comparator, "limit": limit, "units": units},
            "tags": [tag]}


CLAIMS: list = [
    _acc("C3", "No leg of the cook's triangle is over 9 ft", "longest triangle leg", "<=", 9.0, "ft", "triangle-leg"),
    _acc("C4", "The cook's triangle totals no more than 26 ft", "triangle perimeter", "<=", 26.0, "ft", "triangle-total"),
    _acc("C5", "The work aisle is at least 42 in", "work aisle width", ">=", 42.0, "in", "aisle-one"),
    _acc("C6", "The work aisle is at least 48 in", "work aisle width", ">=", 48.0, "in", "aisle-two"),
    _acc("C7", "21 in to stand at the open dishwasher", "dishwasher standing room", ">=", 21.0, "in", "dishwasher-room"),
    _acc("C8", "The island seats two", "island seats", ">=", 2.0, "seats", "island-seats"),
    _acc("C9", "15 in of knee room at the island", "island knee room", ">=", 15.0, "in", "island-knee"),
    _acc("C10", "The microwave is within the smaller child's reach", "microwave height over the small child's reach", "<=", 0.0, "in", "microwave-reach"),
    _acc("C11", "The cabinet line offers the finish", "finish requirements not offered", "<=", 0.0, "requirements", "finish-offered"),
    _acc("C12", "The cabinets fill the walls", "run fill error", "<=", 0.25, "in", "run-fill"),
    _acc("C13", "Uppers clear the window", "window to upper gap", ">=", 1.0, "in", "window-gap"),
    _acc("C14", "The plank's wear layer is at least 20 mil", "floor wear layer", ">=", 20.0, "mil", "floor-wear"),
    _acc("C15", "No two things occupy the same space", "interfering pairs", "<=", 0.0, "pairs", "collisions"),
    _acc("C16", "Every door and drawer opens", "doors that cannot open", "<=", 0.0, "doors", "doors-open"),
    _acc("C17", "36 in of passage round the island", "narrowest passage", ">=", 36.0, "in", "walkways"),
    _acc("C18", "Every thing has a place and fits in it", "things with no place", "<=", 0.0, "things", "stowed"),
    _acc("C19", "No cabinet holds both a cleaning chemical and food", "cabinets holding both food and chemicals", "<=", 0.0, "cabinets", "chemicals-apart"),
    _acc("C20", "Each kind of thing is kept in one place", "kinds split between places", "<=", 0.0, "kinds", "kinds-together"),
    _acc("C21", "Daily things within 5 ft of where they are used", "farthest daily thing from its place of use", "<=", 5.0, "ft", "near-use"),
    _acc("C22", "The children's things within the 5-year-old's reach", "highest children's shelf over the small child's shoulder", "<=", 0.0, "in", "kid-reach"),
    _acc("C23", "Alcohol and medicine above the 8-year-old's reach", "lowest adults-only shelf over the taller child's reach", ">=", 0.0, "in", "adult-only"),
]


def params(config: dict | None = None) -> dict:
    stated = dict(CONFIG if config is None else config)
    flat, _conflicts = flat_params({
        "config": stated,
        "derived": kitchen.build(kitchen.Config(**stated)),
    })
    return flat


def context(ctx):
    ledger = Ledger(claims=[Claim.from_dict(copy.deepcopy(row)) for row in CLAIMS])
    return dataclasses.replace(ctx, params=params(), ledger=ledger, extra={})
