"""Gates for the kitchen. Arithmetic over the model's projection, tier 0.

No gate here recomputes geometry: each reads one derived value from `ctx.params`
and its limit from the claim it settles (`ctx.acceptance`). The limits are the
National Kitchen and Bath Association's Kitchen Planning Guidelines where one
exists (basis `sourced`); the rest are this project's own rules (`model-only`).

Gate ids are project-scoped (`kitchen.*`). The budget is not here: it is the
sourcing pack's `bom.cost` and `bom.complete`, over the bill the model emits.

Every gate has a known-bad control in `selftest/bad_configs.py`: the known-good
design with one thing changed.
"""
from __future__ import annotations

from nopekit.gates import gate, GateContext
from nopekit.models import Locator, NegativeControl, Tier, Verdict

NKBA = "NKBA Kitchen Planning Guidelines"


def _judge(ctx, gate_id, claim, key, units, digits, words):
    acc = ctx.acceptance(claim)
    value = round(float(ctx.params[key]), digits)
    return Verdict(gate=gate_id, passed=acc.holds(value), measured=value, limit=acc.limit,
                   units=units, comparator=acc.comparator.value,
                   detail=f"{words}: {value:g} {units} (limit {acc.comparator.value} {acc.limit:g} {units})")


def _nc(name, note):
    return NegativeControl(fixture=f"selftest/bad_configs.py:{name}", note=note)


@gate(id="kitchen.triangle_leg", basis="sourced", title="Longest leg of the cook's triangle",
      claims=["triangle-leg"], tier=Tier.INSTANT, settles="longest triangle leg",
      negative_control=_nc("no_prep_sink", "the island sink removed: the cook walks from the "
                           "refrigerator at the hall end to the only sink, 12.8 ft"))
def triangle_leg(ctx: GateContext) -> Verdict:
    """NKBA: no leg of the work triangle over 9 ft, centre front to centre front."""
    p = ctx.params
    return _judge(ctx, "kitchen.triangle_leg", "C3", "triangle_longest_ft", "ft", 2,
                  f"sink-range {p['leg_wet_range_ft']:.1f}, range-fridge {p['leg_range_fridge_ft']:.1f}, "
                  f"fridge-sink {p['leg_fridge_wet_ft']:.1f}; longest")


@gate(id="kitchen.triangle_total", basis="sourced", title="Sum of the cook's triangle",
      claims=["triangle-total"], tier=Tier.INSTANT, settles="triangle perimeter",
      negative_control=_nc("no_prep_sink", "the island sink removed: the three legs sum to 27 ft"))
def triangle_total(ctx: GateContext) -> Verdict:
    """NKBA: the three legs sum to no more than 26 ft."""
    return _judge(ctx, "kitchen.triangle_total", "C4", "triangle_total_ft", "ft", 2, "the three legs sum to")


@gate(id="kitchen.aisle_one_cook", basis="sourced", title="Work aisle for one cook",
      claims=["aisle-one"], tier=Tier.INSTANT, settles="work aisle width",
      negative_control=_nc("island_crowds_range", "the island pushed to 30 in from the long run"))
def aisle_one_cook(ctx: GateContext) -> Verdict:
    """NKBA: a work aisle is at least 42 in for one cook."""
    return _judge(ctx, "kitchen.aisle_one_cook", "C5", "work_aisle_in", "in", 1, "long run to island")


@gate(id="kitchen.aisle_two_cooks", basis="sourced", title="Work aisle for several cooks",
      claims=["aisle-two"], tier=Tier.INSTANT, settles="work aisle width",
      negative_control=_nc("one_cook_aisle", "the island at 42 in: right for one cook, short for two"))
def aisle_two_cooks(ctx: GateContext) -> Verdict:
    """NKBA: a work aisle is at least 48 in where more than one person cooks."""
    return _judge(ctx, "kitchen.aisle_two_cooks", "C6", "work_aisle_in", "in", 1, "long run to island")


@gate(id="kitchen.dishwasher_room", basis="sourced", title="Standing room at the open dishwasher",
      claims=["dishwasher-room"], tier=Tier.INSTANT, settles="dishwasher standing room",
      negative_control=_nc("island_crowds_sink", "the island moved to 40 in from the sink run"))
def dishwasher_room(ctx: GateContext) -> Verdict:
    """NKBA: 21 in of standing room between an open dishwasher door and what faces it."""
    return _judge(ctx, "kitchen.dishwasher_room", "C7", "dishwasher_standing_in", "in", 1,
                  "open dishwasher door to the island")


@gate(id="kitchen.island_seats", basis="sourced", title="Seats at the island",
      claims=["island-seats"], tier=Tier.INSTANT, settles="island seats",
      negative_control=_nc("short_island", "the island cut to 40 in: one 24 in seat"))
def island_seats(ctx: GateContext) -> Verdict:
    """NKBA: each seat takes 24 in of counter."""
    return _judge(ctx, "kitchen.island_seats", "C8", "island_seats", "seats", 0, "24 in seats along the island")


@gate(id="kitchen.island_knee", basis="sourced", title="Knee room at the island seats",
      claims=["island-knee"], tier=Tier.INSTANT, settles="island knee room",
      negative_control=_nc("shallow_island", "the island top at 36 in, as the contractor's plan suggests"))
def island_knee(ctx: GateContext) -> Verdict:
    """NKBA: 15 in of clear knee room at a 36 in high counter."""
    return _judge(ctx, "kitchen.island_knee", "C9", "island_knee_in", "in", 1, "overhang past the island bases")


@gate(id="kitchen.microwave_reach", basis="sourced", title="Microwave within the smaller child's reach",
      claims=["microwave-reach"], tier=Tier.INSTANT, settles="microwave height over the small child's reach",
      negative_control=_nc("microwave_on_counter", "the microwave back on the 36 in counter"))
def microwave_reach(ctx: GateContext) -> Verdict:
    """NKBA: a microwave's bottom is 3 in below its user's shoulder, or lower.

    The user here is the smaller child; shoulder height is 0.80 of stature.
    """
    p = ctx.params
    return _judge(ctx, "kitchen.microwave_reach", "C10", "microwave_over_reach_in", "in", 1,
                  f"microwave bottom at {p['microwave_bottom_in']:g} in, child's shoulder at "
                  f"{p['kid_small_shoulder_in']:.1f} in; bottom above shoulder less 3 in by")


@gate(id="kitchen.finish_offered", basis="model-only", title="The chosen cabinet line offers the finish",
      claims=["finish-offered"], tier=Tier.INSTANT, settles="finish requirements not offered",
      negative_control=_nc("shaker_line", "the contractor's painted shaker line: no gloss"))
def finish_offered(ctx: GateContext) -> Verdict:
    """Counts what the catalog says the chosen line cannot do: high gloss, the
    lower colour, the upper colour, two different colours. The integrated handle
    is not counted here: claim A4 owns it, as no maker's page confirms it."""
    unmet = list(ctx.params["finish_unmet"])
    return _judge(ctx, "kitchen.finish_offered", "C11", "finish_unmet_count", "requirements", 0,
                  ("not offered: " + ", ".join(unmet)) if unmet else "gloss, both colours and two tones are offered; unmet")


@gate(id="kitchen.run_fill", basis="model-only", title="The cabinets fill the walls as measured",
      claims=["run-fill"], tier=Tier.INSTANT, settles="run fill error",
      negative_control=_nc("wall_two_inches_longer", "the long wall 2 in longer than the cabinets were drawn for"))
def run_fill(ctx: GateContext) -> Verdict:
    """The widths drawn on each wall, summed, against the wall's stated length."""
    p = ctx.params
    return _judge(ctx, "kitchen.run_fill", "C12", "run_fill_error_in", "in", 2,
                  f"wall 1 off by {p['wall1_fill_error_in']:g}, wall 2 by {p['wall2_fill_error_in']:g}; worst")


@gate(id="kitchen.window_gap", basis="model-only", title="Uppers clear the sink window",
      claims=["window-gap"], tier=Tier.INSTANT, settles="window to upper gap",
      negative_control=_nc("wide_window", "a 56 in window where the 49 in one is"))
def window_gap(ctx: GateContext) -> Verdict:
    return _judge(ctx, "kitchen.window_gap", "C13", "window_gap_in", "in", 2, "nearest upper to the window")


@gate(id="kitchen.floor_wear", basis="sourced", title="Wear layer of the chosen plank",
      claims=["floor-wear"], tier=Tier.INSTANT, settles="floor wear layer",
      negative_control=_nc("thin_wear_layer", "a 12 mil builder-grade plank"))
def floor_wear(ctx: GateContext) -> Verdict:
    """The wear layer the maker states for the chosen plank, in mil."""
    return _judge(ctx, "kitchen.floor_wear", "C14", "floor_wear_mil", "mil", 0, "stated wear layer")


@gate(id="kitchen.collisions", basis="model-only", title="No two things occupy the same space",
      claims=["collisions"], tier=Tier.INSTANT, settles="interfering pairs",
      negative_control=_nc("island_into_sink_run", "the island moved 10 in into the sink run"))
def collisions(ctx: GateContext) -> Verdict:
    """Every cabinet, appliance, panel, counter and shelf as a box, each against
    each other and against the walls and posts. Boxes that only touch pass."""
    pairs = list(ctx.params["collision_pairs"])
    v = _judge(ctx, "kitchen.collisions", "C15", "collision_count", "pairs", 0,
               ("interfering: " + "; ".join(f"{a} / {b}" for a, b in pairs[:4])) if pairs else "no box overlaps another; interfering")
    v.locators = [Locator(view="twin", target=t, label=f"overlaps {o}") for a, b in pairs[:8] for t, o in ((a, b), (b, a))]
    return v


@gate(id="kitchen.doors_open", basis="model-only", title="Every door and drawer opens",
      claims=["doors-open"], tier=Tier.INSTANT, settles="doors that cannot open",
      negative_control=_nc("island_at_18_in", "the island 18 in from the range: the oven door and the drawers hit it"))
def doors_open(ctx: GateContext) -> Verdict:
    """Each door swung through a quarter turn, each drawer pulled 20 in, the
    dishwasher, oven, refrigerator and pantry doors opened, against everything solid."""
    blocked = list(ctx.params["blocked_doors"])
    v = _judge(ctx, "kitchen.doors_open", "C16", "blocked_door_count", "doors", 0,
               ("blocked: " + "; ".join(f"{a} by {b}" for a, b in blocked[:4])) if blocked
               else f"{len(ctx.params['opens'])} doors and drawers swept; blocked")
    v.locators = [Locator(view="twin", target=a.split(":")[0], label=f"cannot open: hits {b}") for a, b in blocked[:8]]
    return v


@gate(id="kitchen.walkways", basis="sourced", title="Passage round the island",
      claims=["walkways"], tier=Tier.INSTANT, settles="narrowest passage",
      negative_control=_nc("island_30_from_sink_run", "the island 30 in from the sink run"))
def walkways(ctx: GateContext) -> Verdict:
    """NKBA: a walkway is at least 36 in. The narrowest side of the island, to the
    nearest fixed thing; furniture is not counted."""
    w = ctx.params["walkways"]
    return _judge(ctx, "kitchen.walkways", "C17", "walkway_min_in", "in", 1,
                  "west %g, north %g, south %g, east %g; narrowest" % (w["west"], w["north"], w["south"], w["east"]))


# ---- a place for everything (model/inventory.py, stow) -------------------------
def _list(words, n=4):
    words = list(words)
    return "; ".join(words[:n]) + (f"; and {len(words) - n} more" if len(words) > n else "")


@gate(id="kitchen.stowed", basis="model-only", title="Every thing has a place and fits in it",
      claims=["stowed"], tier=Tier.INSTANT, settles="things with no place",
      negative_control=_nc("no_island_fridge_in_alcove", "no island and the refrigerator left in its alcove: no pantry and "
                           "three drawers fewer, and things are left over"))
def stowed(ctx: GateContext) -> Verdict:
    """Each thing in the inventory, stood in a compartment by the placing rules;
    the ones no compartment takes are counted. Sizes are typical ones (claim A7)."""
    p = ctx.params
    left = list(p["stow_unplaced"])
    return _judge(ctx, "kitchen.stowed", "C18", "stow_unplaced_count", "things", 0,
                  ("no place for: " + _list(left)) if left else f"all {p['stow_things']} things have a place; left over")


@gate(id="kitchen.chemicals_apart", basis="model-only", title="Cleaning chemicals apart from food",
      claims=["chemicals-apart"], tier=Tier.INSTANT, settles="cabinets holding both food and chemicals",
      negative_control=_nc("soap_in_the_pantry", "the dish soap refill pinned to the pantry shelf the snacks are on"))
def chemicals_apart(ctx: GateContext) -> Verdict:
    """Counts the cabinets, pantries and counter spots that hold a cleaning
    chemical and something eaten or drunk."""
    both = list(ctx.params["stow_mixed"])
    return _judge(ctx, "kitchen.chemicals_apart", "C19", "stow_mixed_count", "cabinets", 0,
                  ("food and chemicals together in: " + _list(both)) if both else "no cabinet holds food and a chemical; holding both")


@gate(id="kitchen.kinds_together", basis="model-only", title="Each kind of thing in one place",
      claims=["kinds-together"], tier=Tier.INSTANT, settles="kinds split between places",
      negative_control=_nc("one_spice_in_the_pantry", "one spice jar pinned to a pantry shelf, away from the rest"))
def kinds_together(ctx: GateContext) -> Verdict:
    """Counts the kinds (plates and bowls, pots, spices, snacks, ...) whose things
    are in more than one cabinet."""
    split = list(ctx.params["stow_split"])
    return _judge(ctx, "kitchen.kinds_together", "C20", "stow_split_count", "kinds", 0,
                  ("split between places: " + _list(split)) if split else "every kind is in one place; split")


@gate(id="kitchen.near_use", basis="model-only", title="Daily things near where they are used",
      claims=["near-use"], tier=Tier.INSTANT, settles="farthest daily thing from its place of use",
      negative_control=_nc("plates_by_the_refrigerator", "the dinner plates pinned to the wall cabinet beside the refrigerator, "
                           "12 ft from the dishwasher"))
def near_use(ctx: GateContext) -> Verdict:
    """The longest straight line from a daily kind's cabinet to the range, sink,
    dishwasher, refrigerator or prep sink it serves."""
    return _judge(ctx, "kitchen.near_use", "C21", "stow_far_ft", "ft", 1, f"farthest: {ctx.params['stow_far_what']}")


@gate(id="kitchen.kid_reach", basis="sourced", title="The children's things within the smaller child's reach",
      claims=["kid-reach"], tier=Tier.INSTANT, settles="highest children's shelf over the small child's shoulder",
      negative_control=_nc("cups_on_the_top_shelf", "one of the children's cups pinned to the top shelf over the dishwasher"))
def kid_reach(ctx: GateContext) -> Verdict:
    """NKBA puts what a person uses at or below their shoulder; shoulder height is
    0.80 of stature, as for the microwave (C10). The user here is the smaller child."""
    p = ctx.params
    return _judge(ctx, "kitchen.kid_reach", "C22", "stow_kid_over_in", "in", 1,
                  f"child's shoulder at {p['stow_kid_max_in']:.1f} in; highest shelf of theirs above it by")


@gate(id="kitchen.adult_only", basis="model-only", title="Alcohol and medicine above the taller child's reach",
      claims=["adult-only"], tier=Tier.INSTANT, settles="lowest adults-only shelf over the taller child's reach",
      negative_control=_nc("liquor_in_a_low_drawer", "one bottle of liquor pinned to the bottom drawer beside the dishwasher"))
def adult_only(ctx: GateContext) -> Verdict:
    """The lowest shelf holding liquor, wine, vitamins or medicine, against 1.25
    times the taller child's stature."""
    p = ctx.params
    return _judge(ctx, "kitchen.adult_only", "C23", "stow_adult_margin_in", "in", 1,
                  f"taller child reaches {p['stow_adult_min_in']:.1f} in; lowest adults-only shelf above that by")
