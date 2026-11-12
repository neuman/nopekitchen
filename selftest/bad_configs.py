"""Known-bad kitchens: the known-good design (`known_good.py`) with ONE change,
in the direction the gate under test cares about."""
from __future__ import annotations

import dataclasses
import os

from nopekit.modelio import load_path

known_good = load_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "known_good.py"))


def _with(ctx, **overrides):
    config = dict(known_good.CONFIG)
    config.update(overrides)
    return dataclasses.replace(known_good.context(ctx), params=known_good.params(config))


def no_prep_sink(ctx):
    """triangle_leg, triangle_total: the island sink removed. Refrigerator to the
    only sink is 12.8 ft and the triangle 27.0 ft."""
    return _with(ctx, prep_sink=False)


def island_crowds_range(ctx):
    """aisle_one_cook: the island 30 in from the long run."""
    return _with(ctx, island_aisle=30.0)


def one_cook_aisle(ctx):
    """aisle_two_cooks: 42 in, the one-cook width."""
    return _with(ctx, island_aisle=42.0)


def island_crowds_sink(ctx):
    """dishwasher_room: the island 40 in from the sink run leaves 14.5 in."""
    return _with(ctx, island_north_aisle=40.0)


def short_island(ctx):
    """island_seats: a 40 in island seats one."""
    return _with(ctx, island_len=40.0)


def shallow_island(ctx):
    """island_knee: a 36 in top leaves 11 in of knee room."""
    return _with(ctx, island_top_d=36.0)


def microwave_on_counter(ctx):
    """microwave_reach: bottom at 36 in, 4.6 in over the 5-year-old's reach."""
    return _with(ctx, microwave_at="counter")


def shaker_line(ctx):
    """finish_offered: the painted shaker line in its own colours: not gloss."""
    return _with(ctx, cab_line="gs_shaker", lower_color="navy_blue", upper_color="swan_white", handles="bar")


def wall_two_inches_longer(ctx):
    """run_fill: the long wall measures 195 in; the boxes still sum to 193."""
    return _with(ctx, wall1_len=195.0)


def wide_window(ctx):
    """window_gap: a 56 in window overlaps the uppers beside it."""
    return _with(ctx, window_w=56.0)


def thin_wear_layer(ctx):
    """floor_wear: the same floor with a 12 mil wear layer, a builder-grade plank.
    No such plank is in the catalog, so the derived value is set directly."""
    base = known_good.context(ctx)
    params = dict(base.params)
    params["floor_wear_mil"] = 12
    return dataclasses.replace(base, params=params)


def island_into_sink_run(ctx):
    """collisions: the island 10 in into the sink run; it stands in the sink base
    and the dishwasher."""
    return _with(ctx, island_north_aisle=-10.0)


def island_at_18_in(ctx):
    """doors_open: the island 18 in from the range. Nothing overlaps, and the oven
    door and the facing drawers cannot open."""
    return _with(ctx, island_aisle=18.0)


def island_30_from_sink_run(ctx):
    """walkways: 30 in between the sink run and the island."""
    return _with(ctx, island_north_aisle=30.0)
