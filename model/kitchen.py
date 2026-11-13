"""kitchen.py — the one model of the Edmonds kitchen, living room and upstairs floors.

Everything else is generated from this file: the cabinet runs, the flow distances,
the bill of materials the budget gates read, the 3D twin the site draws, and every
option the configurator on the marketing page offers (rule 1).

Frame: inches, US dollars. Origin at the kitchen's inside north-west corner, at the
floor. +x runs east along wall 2 (the sink wall, 138 in). +y runs south along wall 1
(the long wall, 193 in). +z is up. "Hall end" is the south end of wall 1, beside the
hallway and the stairs; "alcove" is the recess at the east end of the sink wall where
the refrigerator stands today.

Where each number comes from is said beside it. Three kinds:
  stated    read off the contractor's drawings (inputs/sketches/contractor-*.jpg)
  scaled    read off the Homestyler floor plan, a consumer app: approximate
  assumed   nobody has measured it; an assumption claim owns it (claims/A*.json)

Standard library only. `python3 model/kitchen.py` prints the derived values.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

# ----------------------------------------------------------------------------
# The catalog: every thing that can be chosen, with its price and where the price
# came from. Filled in below (CATALOG) so the geometry reads first.
# ----------------------------------------------------------------------------


@dataclass
class Config:
    """Every input. Nothing outside this dataclass is an input."""

    # --- the room, as the contractor drew it (stated) ---
    wall1_len: float = 193.0
    """in, the long wall. Stated on the GS Kitchen and Bath plan and elevation; the
    cabinet widths on that elevation sum to it exactly."""

    wall2_len: float = 138.0
    """in, the sink wall, corner to the stub wall beside the alcove. Stated."""

    window_w: float = 49.0
    """in, the window over the sink (Win49 on the elevation). It stays."""

    kitchen_w: float = 141.0
    """in, wall 1 to the line of the two posts that open the kitchen to the dining
    area. Scaled from the floor plan (11 ft 9 in), not measured."""

    alcove_w: float = 40.0
    """in, the old refrigerator recess, wall to wall, north to south: it opens west,
    toward the kitchen, behind the pillar. ASSUMED from a 36 in refrigerator with trim; claim A1 owns it. 36 would not take two 18 in pantry
    cabinets with fillers; measure before ordering anything for it."""

    alcove_d: float = 34.0
    """in, front to back of the recess, running east from its opening. ASSUMED (a standard-depth refrigerator sits
    nearly flush in it in the photo). The recess keeps its walls: it is the size of
    a refrigerator and is reached into, not walked into."""

    floor_area_sqft: float = 1257.0
    """sq ft of new floor: kitchen 193, living and dining 507, office 52, bedrooms
    236 + 89 + 85, closets 49 + 26 + 10 + 10. Scaled: the sum of the floor plan's
    room labels, without the two bathrooms. A tape measure will move it."""

    # --- cabinet standards (stated on the elevations) ---
    base_h: float = 34.5
    counter_t: float = 1.5
    upper_gap: float = 18.0
    """in, counter to the underside of the uppers. Stated; also the NKBA minimum of
    15 with margin."""
    base_d: float = 24.0
    counter_d: float = 25.5
    upper_d: float = 13.0
    """in, wall cabinet with its door. 12 in box plus a slab front."""
    fridge_d: float = 34.0
    """in, wall to the refrigerator's door face. ASSUMED standard depth; the
    existing French-door unit is kept and its model is not recorded."""

    # --- layout choices ---
    fridge_at: str = "hall"
    """'hall' (the contractor's mock-up, requirement R6) or 'alcove' (where it is
    today). What each costs in walking distance is in PARAMS."""

    island_len: float = 64.0
    """in, the island top along the long wall; 0 is no island. 64 is the
    contractor's: two 30 in bases and a 2 in overhang each end. 76 seats three."""

    island_top_d: float = 40.0
    """in, the island top across. 24 in base, 1 in front overhang, 15 in of knee
    room: the NKBA depth for a seat at a 36 in counter. The 36 in top that the
    contractor's plan suggests leaves 11 in and lost; see PARAMS."""

    island_aisle: float = 48.0
    """in, the range's door face to the island: the work aisle at its narrowest,
    as the NKBA measures it (between counter fronts and appliances). 48 is its
    width for more than one cook; 42 for one. Measured from the counter edge the
    range's half inch of projection was lost; see PARAMS."""

    island_north_aisle: float = 48.0
    """in, the sink run's counter edge to the island's north end. Leaves 22.5 in to
    stand behind an open dishwasher door."""

    prep_sink: bool = True
    """A small second sink in the island. It is what brings the cook's triangle
    inside 9 ft a leg once the refrigerator is at the hall end; without it the walk
    from the refrigerator to the only sink is 12.7 ft. See PARAMS."""

    pantry: str = "open"
    """What the old alcove becomes when the refrigerator leaves it. No wall is
    removed for any of them: 'open' (the recess lined with shelves on its back and
    both sides, no door), 'door' (the same behind a hinged door) or 'cabinets'
    (tall cabinets with fronts in the lower colour)."""

    microwave_at: str = "pantry"
    """'counter' (as today), 'pantry' (a shelf at 30 in in the alcove) or
    'island' (a drawer microwave in the island)."""

    # --- selections (keys into CATALOG) ---
    cab_line: str = ""
    lower_color: str = ""
    upper_color: str = ""
    counter: str = ""
    sink: str = ""
    faucet: str = ""
    backsplash: str = ""
    floor: str = ""
    handles: str = "integrated"
    managed_by: str = "self"
    """'self': the person hires the trades; 'gc': a general contractor adds 18%."""
    cab_install: str = "pro"
    floor_removal: str = "pro"

    # --- money ---
    budget_usd: float = 60000.0
    """USD, the whole job: kitchen and upstairs floors. The person's number."""

    sales_tax: float = 0.107
    """Edmonds combined rate (location code 3104), 6.5% state + 4.2% local, in
    effect from 1 April 2026 per the WA DOR table as quoted by two aggregators; the
    Q4 2026 notice was not seen. Washington taxes remodel labour as well as
    materials, so it applies to every line but permits."""

    contingency: float = 0.12
    """Of the pre-tax subtotal. 10% is a contractor's usual line and 20% a
    budgeting guide's; 12 because the sink and the range stay where they are, and
    the island drain and the refrigerator circuit are the only work inside walls."""

    # --- the people (assumed; claim A3 owns them) ---
    kid_small_h: float = 43.0
    """in, a 5-year-old at the CDC 50th percentile. ASSUMED, not measured."""
    kid_big_h: float = 50.5
    """in, an 8-year-old at the CDC 50th percentile. ASSUMED, not measured."""


# What lost, beside the value it lost to (rule 3). Numbers are this model's own,
# at the default design with the one field changed.
PARAMS = [
    {"name": "prep_sink", "rejected": [
        {"value": "no island sink (the contractor's plan as drawn)",
         "why": "refrigerator to sink is 12.7 ft, over the 9 ft a leg may be, and "
                "the triangle is 26.9 ft against 26"}]},
    {"name": "fridge_at", "rejected": [
        {"value": "alcove (where it is today)",
         "why": "refrigerator to range is 10.0 ft, over 9 ft, and the alcove "
                "cannot become a pantry; the person asked for the move (R6)"}]},
    {"name": "island_top_d", "units": "in", "rejected": [
        {"value": "36 in", "why": "11 in of knee room, 4 in short of the 15 in "
                                  "a seat at a 36 in counter needs"}]},
    {"name": "island_aisle", "units": "in", "rejected": [
        {"value": "42 in", "why": "right for one cook, 6 in short of the width "
                                  "for two to pass on a holiday"},
        {"value": "48 in from the counter edge", "why": "the range stands half an inch "
                                  "proud of the counter, so the aisle at the range was 47.5 in"}]},
]

# Fixed sizes of the things that are kept (the range, dishwasher and refrigerator
# stay; requirement of the budget) and of the contractor's boxes.
RANGE_W, DW_W, FRIDGE_W = 30.0, 24.0, 36.0
RANGE_D = 26.0           # in, wall to the range's door face: ASSUMED for the kept slide-in range (A3)
CORNER = 36.0            # DCB36: the corner base takes 36 in of each wall
UPPER_TALL_TOP = 94.0    # tops of the 40 in uppers and of the cabinet over the fridge
CAB_TOP = 84.0           # tops of the 30 in uppers toward the corner
FILL_HALL = 2.75         # stated: the filler that lets the fridge door open past the return wall
TOE = 4.5                # toe kick height, inside base_h
STOOL_W = 24.0           # NKBA seat width at a counter
KNEE_36 = 15.0           # NKBA knee depth at a 36 in counter
DRAWER_MW_BOTTOM = 19.0  # in above the floor, a 24 in drawer microwave under a 36 in counter
REACH_DROP = 3.0         # NKBA: a microwave's bottom sits 3 in below the user's shoulder, or lower
SHOULDER = 0.80          # shoulder height over stature, children 5 to 9
PANTRY_BACK_D = 12.0     # in, the shelves across the back of the alcove
PANTRY_SIDE_D = 10.0     # in, the shelves down each side; 40 in of alcove leaves 20 in to reach through
WALL_H = 96.0            # in, the wall plate. Above it the ceiling is vaulted
NICHE_Y0 = 30.0          # in from the sink wall: the old refrigerator recess starts where return wall 3 ends
NICHE_HEAD = 82.0        # in, the underside of the header over the recess's opening. By eye from the photo
PILLAR_W = 20.0          # in, the pillar south of the recess, as wide as it looks in the photos
# Three cube sconces on the triangular wall over the kitchen, (x, z, colour), by eye from the photo.
# They hang in one level line, a little above the flat ceiling's edge.
SCONCES = ((60.0, 104.0, "#3B49B8"), (91.0, 104.0, "#E3D21F"), (123.0, 104.0, "#D8203F"))
# The vault, as (x, z): the west eave over the long wall, the ridge beam, the east
# eave. By eye from the photos, like the rest of the room (claim A3).
VAULT = ((-5.0, 96.0), (185.0, 150.0), (277.0, 120.0))


def soffit_y(c: "Config") -> float:
    """in from the sink wall: the plane of the pillar's back, the office's front wall
    and the triangular wall over the kitchen. North of it, over the sink run, the
    ceiling is flat at the wall plate; south of it the room is vaulted."""
    return NICHE_Y0 + c.alcove_w


def ceiling_z(x: float) -> float:
    """in, the height of the vaulted ceiling over a point x in from the long wall."""
    (x0, z0), (x1, z1), (x2, z2) = VAULT
    if x <= x1:
        return z0 + (x - x0) * (z1 - z0) / (x1 - x0)
    return z1 + (x - x1) * (z2 - z1) / (x2 - x1)


def _box(id, kind, role, x, y, z, dx, dy, dz, face="", fronts="", label=""):
    return {"id": id, "kind": kind, "role": role, "x": x, "y": y, "z": z,
            "dx": dx, "dy": dy, "dz": dz, "face": face, "fronts": fronts,
            "label": label or id}


def wall1(c: Config) -> list[dict]:
    """The long wall's boxes, from the corner south. Widths are the contractor's."""
    out, y = [], 0.0
    bz, bh = 0.0, c.base_h

    def base(id, w, fronts, label):
        nonlocal y
        out.append(_box(id, "base", "lower", 0, y, bz, c.base_d, w, bh, "E", fronts, label))
        y += w

    base("w1_corner", CORNER, "corner", "corner base 36")
    base("w1_b24", 24, "door2+drawer", "base 24")
    out.append(_box("range", "appliance", "range", 0, y, 0, RANGE_D, RANGE_W, 36, "E", "", "range 30 (kept)"))
    range_y = y
    y += RANGE_W
    base("w1_b3d30", 30, "drawer3", "3-drawer base 30")
    base("w1_b33", 33, "door2+drawer", "base 33")
    if c.fridge_at == "hall":
        out.append(_box("w1_panel", "panel", "lower", 0, y, 0, c.base_d + 2, 1.25, UPPER_TALL_TOP, "E", "", "fridge panel"))
        y += 1.25
        fridge_y = y
        out.append(_box("fridge", "appliance", "fridge", 0, y, 0, c.fridge_d, FRIDGE_W, 70, "E", "", "refrigerator 36 (kept, moved)"))
        y += FRIDGE_W
        out.append(_box("w1_filler", "filler", "lower", 0, y, 0, c.base_d, FILL_HALL, UPPER_TALL_TOP, "E", "", "filler 2 3/4"))
    else:
        fridge_y = None
        base("w1_b3d36", 36, "drawer3", "3-drawer base 36")
        out.append(_box("w1_filler", "filler", "lower", 0, y, 0, c.base_d, 4.0, bh, "E", "", "filler 4"))

    # uppers, from the corner south
    uz30, uz40 = CAB_TOP - 30, UPPER_TALL_TOP - 40
    out.append(_box("w1_u_corner", "upper", "upper", 0, 0, uz30, c.upper_d, 24, 30, "E", "corner", "corner wall 24"))
    out.append(_box("w1_u30", "upper", "upper", 0, 24, uz30, c.upper_d, 30, 30, "E", "door2", "wall 30x30"))
    out.append(_box("w1_u_fill", "filler", "upper", 0, 54, uz30, c.upper_d, range_y - 54, UPPER_TALL_TOP - uz30, "E", "", "filler"))
    out.append(_box("w1_u_hood", "upper", "upper", 0, range_y, UPPER_TALL_TOP - 24, c.upper_d, 30, 24, "E", "door2", "wall 30x24 over hood"))
    out.append(_box("hood", "appliance", "hood", 0, range_y, UPPER_TALL_TOP - 30, 18, 30, 6, "E", "", "hood"))
    out.append(_box("w1_u3040", "upper", "upper", 0, range_y + 30, uz40, c.upper_d, 30, 40, "E", "door2", "wall 30x40"))
    out.append(_box("w1_u3340", "upper", "upper", 0, range_y + 60, uz40, c.upper_d, 33, 40, "E", "door2", "wall 33x40"))
    if c.fridge_at == "hall":
        out.append(_box("w1_u_fridge", "upper", "upper", 0, fridge_y, UPPER_TALL_TOP - 21, c.base_d, FRIDGE_W, 21, "E", "door2", "wall 36x21 over fridge"))
    else:
        out.append(_box("w1_u3640", "upper", "upper", 0, range_y + 93, uz40, c.upper_d, 36, 40, "E", "door2", "wall 36x40"))
    return out


def wall2(c: Config) -> list[dict]:
    """The sink wall's boxes, from the corner east."""
    out = []
    x = CORNER
    out.append(_box("w2_corner_return", "base", "lower", c.base_d, 0, 0, CORNER - c.base_d, c.base_d, c.base_h, "S", "corner", "corner base return"))
    out.append(_box("w2_fill_l", "filler", "lower", x, 0, 0, 2, c.base_d, c.base_h, "S", "", "filler 2"))
    x += 2
    out.append(_box("w2_b24", "base", "lower", x, 0, 0, 24, c.base_d, c.base_h, "S", "door2+drawer", "base 24"))
    x += 24
    out.append(_box("w2_sink", "base", "lower", x, 0, 0, 33, c.base_d, c.base_h, "S", "door2+false", "sink base 33"))
    sink_x = x + 16.5
    x += 33
    out.append(_box("dishwasher", "appliance", "dishwasher", x, 0, 0, DW_W, c.base_d, c.base_h, "S", "", "dishwasher 24 (kept)"))
    x += DW_W
    out.append(_box("w2_b3d18", "base", "lower", x, 0, 0, 18, c.base_d, c.base_h, "S", "drawer3", "3-drawer base 18"))
    x += 18
    out.append(_box("w2_fill_r", "filler", "lower", x, 0, 0, 1.0, c.base_d, c.base_h, "S", "", "filler 1"))
    uz = CAB_TOP - 30
    win_x0 = sink_x - c.window_w / 2
    out.append(_box("w2_u27", "upper", "upper", 24, 0, uz, 27, c.upper_d, 30, "S", "door2", "wall 27x30"))
    out.append(_box("w2_u33", "upper", "upper", x + 1.0 - 33, 0, uz, 33, c.upper_d, 30, "S", "door2", "wall 33x30"))
    out.append(_box("window", "window", "window", win_x0, -1, 44, c.window_w, 1, 40, "S", "", "window 49"))
    return out


def island(c: Config) -> list[dict]:
    """The island: bases on the range side, knees on the dining side."""
    if c.island_len <= 0:
        return []
    out = []
    x0 = RANGE_D + c.island_aisle
    y0 = c.counter_d + c.island_north_aisle
    over = 2.0
    run = c.island_len - 2 * over
    n = max(1, round(run / 30.0))
    w = run / n
    for i in range(n):
        y = y0 + over + i * w
        south = i == n - 1
        if c.prep_sink and south:
            kind, fronts, label = "base", "door2+false", f"prep sink base {w:.0f}"
        elif c.microwave_at == "island" and i == 0:
            kind, fronts, label = "base", "microwave", f"drawer microwave base {w:.0f}"
        else:
            kind, fronts, label = "base", "drawer3", f"3-drawer base {w:.0f}"
        out.append(_box(f"isl_b{i}", kind, "lower", x0 + 1, y, 0, c.base_d, w, c.base_h, "W", fronts, label))
    out.append(_box("isl_back", "panel", "lower", x0 + 1 + c.base_d, y0 + over, 0, 0.75, run, c.base_h, "E", "", "island back panel"))
    out.append(_box("isl_top", "counter", "counter", x0, y0, c.base_h, c.island_top_d, c.island_len, c.counter_t, "", "", "island top"))
    if c.prep_sink:
        ys = y0 + over + (n - 0.5) * w
        out.append(_box("prep_sink", "sink", "sink", x0 + 5, ys - 7.5, c.base_h + c.counter_t - 7, 15, 15, 7.05, "", "", "prep sink 15"))
    for s in range(int(c.island_len // STOOL_W)):
        ys = y0 + (c.island_len - (c.island_len // STOOL_W) * STOOL_W) / 2 + s * STOOL_W + STOOL_W / 2
        out.append(_box(f"stool{s}", "stool", "stool", x0 + c.island_top_d - 9, ys - 7.5, 0, 15, 15, 25, "", "", "stool"))
    return out


def alcove(c: Config) -> list[dict]:
    """What stands in the old refrigerator recess. The recess is east of return
    wall 3 and behind the pillar; its opening faces west, into the kitchen."""
    x0 = c.wall2_len + 5.0          # the inside of the opening: return wall 3 is ~5 in thick
    y0, w, d = NICHE_Y0, c.alcove_w, c.alcove_d
    out = []
    if c.fridge_at == "alcove":
        out.append(_box("fridge", "appliance", "fridge", x0, y0 + (w - FRIDGE_W) / 2, 0, c.fridge_d, FRIDGE_W, 70, "W", "", "refrigerator 36 (kept, stays)"))
        return out
    if c.pantry == "cabinets":
        cw = (w - 4) / 2
        cx = x0 + d - c.base_d
        for i in range(2):
            out.append(_box(f"pantry_tall{i}", "tall", "lower", cx, y0 + 2 + i * cw, 0, c.base_d, cw, 80, "W", "door1tall", f"pantry cabinet {cw:.0f}x80"))
        if c.microwave_at == "pantry":
            out.append(_box("microwave", "appliance", "microwave", cx, y0 + 2, 30, 16, 20, 12, "W", "", "microwave in pantry niche"))
        return out
    # the recess as it stands, lined with shelves: across the back and down both sides
    bd, sd = PANTRY_BACK_D, PANTRY_SIDE_D
    for i, z in enumerate((16, 30, 44, 58, 72)):
        out.append(_box(f"pantry_shelf_back{i}", "shelf", "shelf", x0 + d - bd, y0, z, bd, w, 1, "W", "", "pantry shelf, back"))
        out.append(_box(f"pantry_shelf_north{i}", "shelf", "shelf", x0 + 2, y0, z, d - bd - 2, sd, 1, "S", "", "pantry shelf, north side"))
        out.append(_box(f"pantry_shelf_south{i}", "shelf", "shelf", x0 + 2, y0 + w - sd, z, d - bd - 2, sd, 1, "N", "", "pantry shelf, south side"))
    if c.microwave_at == "pantry":
        out.append(_box("microwave", "appliance", "microwave", x0 + d - 14, y0 + w - 21, 31, 14, 20, 12, "W", "", "microwave on the 30 in shelf"))
    if c.pantry == "door":
        out.append(_box("pantry_door", "door", "door", x0 - 3.5, y0 + 2, 0, 1.5, w - 4, 80, "W", "", "pantry door"))
    return out


def counters(c: Config) -> list[dict]:
    """The countertop slabs on the two walls (the island's is in island())."""
    z, t, d = c.base_h, c.counter_t, c.counter_d
    range_y = CORNER + 24
    w1_end = (CORNER + 24 + RANGE_W + 30 + 33) if c.fridge_at == "hall" else c.wall1_len - 4
    out = [
        _box("top_w1_north", "counter", "counter", 0, 0, z, d, range_y, t, "", "", "counter, corner to range"),
        _box("top_w1_south", "counter", "counter", 0, range_y + RANGE_W, z, d, w1_end - range_y - RANGE_W, t, "", "", "counter, range to fridge"),
        _box("top_w2", "counter", "counter", d, 0, z, c.wall2_len - d, d, t, "", "", "counter, sink wall"),
        _box("sink", "sink", "sink", CORNER + 2 + 24 + 1.5, 3, z + t - 9, 30, 18, 9.05, "", "", "sink"),
    ]
    f = CATALOG["faucet"][c.faucet]
    # the faucet stands 1.5 in off the wall behind the sink's centre; the box is its
    # footprint and its stated height, so the twin shows it and nothing else reads it
    out.append(_box("faucet", "faucet", "faucet", CORNER + 2 + 24 + 16.5 - 1, 1.0, z + t, 2, 2, f["h_in"], "", "", f["label"]))
    if c.microwave_at == "counter":
        out.append(_box("microwave", "appliance", "microwave", 2, 4, z + t, 16, 20, 12, "E", "", "microwave on the counter"))
    return out


def room(c: Config) -> list[dict]:
    """The shell the kitchen stands in: walls, posts, windows, the office, the
    stair opening, the fireplace, and the furniture that is there today.

    APPROXIMATE. The kitchen's own walls are the contractor's; everything else is
    scaled from the Homestyler floor plan and placed by eye from five photos. It
    is drawn so the kitchen can be seen in its room; no gate reads it. Claim A3.
    """
    H, T = WALL_H, 5.0
    nx0 = c.wall2_len                     # the west face of return wall 3 and of the pillar
    nx1 = nx0 + T + c.alcove_d            # the back (east) wall of the old refrigerator recess
    ny0, ny1 = NICHE_Y0, soffit_y(c)      # the recess, north to south; ny1 is the pillar's back
    px1 = nx0 + PILLAR_W                  # the pillar's east edge
    E, S = 272.0, 376.0                   # inside faces of the east and south walls
    hall0, hall1 = 209.0, 258.0           # the hallway's mouth in the west wall
    out = []

    def add(id, kind, x, y, z, dx, dy, dz, label="", inner=False):
        out.append(_box(id, kind, kind, x, y, z, dx, dy, dz, "", "", label or id))
        if inner:       # a wall that stands inside the room: a viewer never hides it to see in
            out[-1]["inner"] = True

    def post(id, x, y, dx=6.0, dy=6.0, label="post, floor to the vaulted ceiling"):
        # a post carries the roof: it runs from the floor to the vaulted ceiling
        add(id, "post", x, y, 0, dx, dy, max(ceiling_z(x), ceiling_z(x + dx)), label)

    add("floor_main", "floor", -T, -T, -1, E + 2 * T, S + 2 * T, 1, "floor")
    add("floor_hall", "floor", -70, hall0, -1, 70 - T, hall1 - hall0, 1, "hallway floor")
    add("wall_w_kitchen", "wall", -T, -T, 0, T, hall0 + T, H, "wall 1 (long wall)")
    add("wall_hall_n", "wall", -70, hall0 - T, 0, 70 - T, T, H, "hallway wall")
    add("wall_hall_s", "wall", -70, hall1, 0, 70 - T, T, H, "hallway wall")
    add("wall_hall_end", "wall", -70 - T, hall0 - T, 0, T, hall1 - hall0 + 2 * T, H, "hallway end")
    add("wall_w_south", "wall", -T, hall1, 0, T, S - hall1 + T, H, "west wall")
    add("wall_n", "wall", 0, -T, 0, E + T, T, H, "wall 2 (sink wall)")
    add("wall_stub3", "wall", nx0, 0, 0, T, ny0, H, "return wall 3", inner=True)
    add("wall_stub4", "wall", 0, c.wall1_len, 0, 30, T, H, "return wall 4", inner=True)
    # the old refrigerator recess: behind the pillar, open to the west under a header
    add("wall_niche_n", "wall", nx0 + T, ny0 - T, 0, nx1 - nx0, T, H, "recess north wall", inner=True)
    add("wall_niche_e", "wall", nx1, ny0, 0, T, ny1 - ny0, H, "recess back wall", inner=True)
    add("wall_niche_head", "wall", nx0, ny0, NICHE_HEAD, T, ny1 - ny0, H - NICHE_HEAD, "header over the recess", inner=True)
    # the office's front wall, in the plane of the pillar's back
    add("wall_office_s1", "wall", px1, ny1, 0, 197 - px1, T, H, "office front wall")
    add("office_slider", "glass", 197, ny1 + 1.5, 0, 52, 2, 80, "office sliding door")
    add("wall_office_s2", "wall", 249, ny1, 0, E - 249, T, H, "office front wall")
    add("wall_office_head", "wall", 197, ny1, 80, 52, T, H - 80, "office door header")
    add("wall_e", "wall", E, -T, 0, T, S + 2 * T, H, "east wall")
    add("wall_s_sill", "wall", -T, S, 0, E + 2 * T, T, 30, "south wall below the windows")
    add("win_south", "glass", 86, S + 1.5, 30, 180, 2, 66, "gable windows")
    add("wall_s_w", "wall", -T, S, 30, 91, T, H - 30, "south wall")
    add("wall_s_e", "wall", 266, S, 30, E + T - 266, T, H - 30, "south wall")
    post("post_se", c.kitchen_w, 195)
    post("post_ne", nx0, ny1, PILLAR_W, 7.0, "pillar south of the recess, floor to the vaulted ceiling")
    # the brick fireplace, with its firebox open at the floor: 30 in wide, 26 in high
    add("fireplace_n", "brick", E - 10, 150, 0, 10, 11, H, "brick fireplace")
    add("fireplace_s", "brick", E - 10, 191, 0, 10, 11, H, "brick fireplace")
    add("fireplace_top", "brick", E - 10, 161, 26, 10, 30, H - 26, "brick fireplace")
    add("fireplace_box", "firebox", E - 2, 161, 0, 2, 30, 26, "firebox")
    add("fireplace_hearth", "firebox", E - 10, 161, 0, 8, 30, 0.5, "firebox floor")
    # three wood shelves on pipe brackets, on the east wall between the office's sliding door and the fireplace
    for i, (y, ln, z) in enumerate(((ny1 + T + 2, 17.0, 46.0), (ny1 + T + 1, 48.0, 58.0), (ny1 + T + 16, 16.0, 70.0))):
        add(f"wall_shelf{i}", "wallshelf", E - 8, y, z, 8, ln, 1.5, "wall shelf")
    add("stair_well", "stair", 0, 300, -0.5, 85, S - 300, 1, "stair opening")
    add("stair_rail_n", "rail", 0, 298, 0, 87, 2, 38, "stair rail")
    add("stair_rail_e", "rail", 85, 298, 0, 2, S - 298, 38, "stair rail")
    add("f_table", "furniture", 196, 94, 28.5, 40, 108, 1.5, "dining table")
    for i, (lx, ly) in enumerate(((198, 96), (232, 96), (198, 198), (232, 198))):
        add(f"f_table_leg{i}", "furniture", lx, ly, 0, 3, 3, 28.5, "table leg")
    # the new couch: larger and squarer than the grey one in the photos, in a spice
    # colour. Its size is not measured: 94 x 40 in is a deep three-seater.
    add("f_sofa_seat", "sofa", 145, 254, 0, 94, 40, 17, "couch (new: larger, square, spice)")
    add("f_sofa_back", "sofa", 145, 254, 17, 94, 9, 15, "couch back")
    add("f_rug", "rug", 140, 290, 0, 100, 70, 0.4, "rug")
    return out


# ----------------------------------------------------------------------------
# Fronts, open doors, collisions and walkways. The site draws the fronts from the
# same rectangles the door check swings, so the picture and the check cannot part.
# ----------------------------------------------------------------------------
DRAWER_TRAVEL = 20.0     # in, a full-extension drawer pulled out
DW_DOOR, OVEN_DOOR, FREEZER_TRAVEL, MW_TRAVEL = 26.0, 21.0, 24.0, 16.0
PANTRY_DOOR_W = 36.0
SOLID = ("base", "upper", "tall", "appliance", "panel", "filler", "counter", "shelf", "door")
ROOM_SOLID = ("wall", "post", "brick")
TOL = 0.1                # in; boxes that only touch do not collide


def _face_w(b):
    return b["dy"] if b["face"] in ("E", "W") else b["dx"]


def front_rects(b: dict) -> list:
    """[u0, u1, z0, z1, kind] for each door and drawer front of a box. u runs
    along the face from the box's low corner; kind is door, drawer, corner or mw."""
    w = _face_w(b)
    z0 = b["z"] + TOE if b["kind"] == "base" else b["z"]
    z1 = b["z"] + b["dz"]
    half = w / 2
    f = b["fronts"]

    def doors(a, c):
        return [[0, half, a, c, "door"], [half, w, a, c, "door"]] if w >= 21 else [[0, w, a, c, "door"]]

    if f == "drawer3":
        return [[0, w, z0, z0 + 15, "drawer"], [0, w, z0 + 15, z0 + 25, "drawer"], [0, w, z0 + 25, z1, "drawer"]]
    if f in ("door2+drawer", "door2+false"):
        return doors(z0, z1 - 5) + [[0, w, z1 - 5, z1, "drawer" if f == "door2+drawer" else "false"]]
    if f == "corner":
        # a bifold corner door: only the 12 in beside the next cabinet is a leaf
        return [[w - 12, w, z0, z1, "corner"]]
    if f == "door2":
        return doors(z0, z1)
    if f == "door1":
        return [[0, w, z0, z1, "door"]]
    if f == "door1tall":
        return [[0, w, z0 + TOE, z0 + 60, "door"], [0, w, z0 + 60, z1, "door"]]
    if f == "microwave":
        return [[0, w, z0, z0 + 10, "drawer"], [0, w, z0 + 10, z1, "mw"]]
    return []


def _out(b, u0, u1, z0, z1, reach):
    """The box a front sweeps when it opens `reach` inches out of its face."""
    if b["face"] == "E":
        return b["x"] + b["dx"], b["y"] + u0, z0, reach, u1 - u0, z1 - z0
    if b["face"] == "W":
        return b["x"] - reach, b["y"] + u0, z0, reach, u1 - u0, z1 - z0
    if b["face"] == "S":
        return b["x"] + u0, b["y"] + b["dy"], z0, u1 - u0, reach, z1 - z0
    return b["x"] + u0, b["y"] - reach, z0, u1 - u0, reach, z1 - z0


def open_volumes(c: Config, boxes: list[dict]) -> list[dict]:
    """What each door, drawer and appliance door sweeps as it opens.

    A hinged leaf sweeps a quarter circle; its bounding box is taken, as wide as
    the leaf and as far out as the leaf is wide. A corner bifold folds inside its
    own 12 in and is not swept. Wall-cabinet doors are swept too: they hit a
    hood or a neighbour, never a person, and this check is about things."""
    out = []

    def add(b, name, u0, u1, z0, z1, reach, kind):
        x, y, z, dx, dy, dz = _out(b, u0, u1, z0, z1, reach)
        out.append({"id": f"{b['id']}:{name}", "of": b["id"], "kind": kind, "x": x, "y": y, "z": z, "dx": dx, "dy": dy, "dz": dz})

    for b in boxes:
        if not b["face"]:
            continue
        w = _face_w(b)
        if b["kind"] in ("base", "upper", "tall"):
            for i, (u0, u1, z0, z1, kind) in enumerate(front_rects(b)):
                if kind == "door":
                    add(b, f"door{i}", u0, u1, z0, z1, u1 - u0, "door")
                elif kind == "drawer":
                    add(b, f"drawer{i}", u0, u1, z0, z1, DRAWER_TRAVEL, "drawer")
                elif kind == "mw":
                    add(b, f"mw{i}", u0, u1, z0, z1, MW_TRAVEL, "drawer")
        elif b["role"] == "dishwasher":
            add(b, "door", 0, w, 0, b["dz"], DW_DOOR, "door")
        elif b["role"] == "range":
            add(b, "oven", 0, w, 0, 30, OVEN_DOOR, "door")
        elif b["role"] == "fridge":
            add(b, "door_a", 0, w / 2, 30, 70, w / 2, "door")
            add(b, "door_b", w / 2, w, 30, 70, w / 2, "door")
            add(b, "freezer", 0, w, 3, 30, FREEZER_TRAVEL, "drawer")
        elif b["kind"] == "door":      # the pantry door, swinging out into the kitchen
            out.append({"id": f"{b['id']}:swing", "of": b["id"], "kind": "door", "x": b["x"] - b["dy"], "y": b["y"],
                        "z": 0, "dx": b["dy"], "dy": b["dy"], "dz": b["dz"]})
    return out


def _hit(a, b):
    return all(min(a[k] + a["d" + k], b[k] + b["d" + k]) - max(a[k], b[k]) > TOL for k in "xyz")


def collisions(boxes: list[dict], shell: list[dict]) -> list[list[str]]:
    """Pairs of solid things that occupy the same space. The microwave is left
    out (it sits inside a shelf bay or a cabinet niche by design), as are sinks,
    which are set into their counter. Shell against shell is not checked: the
    room outside the kitchen is approximate."""
    solid = [b for b in boxes if b["kind"] in SOLID and b["id"] != "microwave"]
    walls = [b for b in shell if b["kind"] in ROOM_SOLID]
    pairs = []
    for i, a in enumerate(solid):
        for b in solid[i + 1:]:
            if _hit(a, b):
                pairs.append([a["id"], b["id"]])
        for b in walls:
            if _hit(a, b):
                pairs.append([a["id"], b["id"]])
    return pairs


def blocked_doors(opens: list[dict], boxes: list[dict], shell: list[dict]) -> list[list[str]]:
    """[what opens, what it hits] for each door or drawer that cannot open."""
    solid = [b for b in boxes if b["kind"] in SOLID and b["id"] != "microwave"] + [b for b in shell if b["kind"] in ROOM_SOLID]
    out = []
    for o in opens:
        for b in solid:
            if b["id"] != o["of"] and _hit(o, b):
                out.append([o["id"], b["id"]])
                break
    return out


def walkways(c: Config, boxes: list[dict], shell: list[dict]) -> dict:
    """Clear passage on each side of the island, to the nearest fixed thing."""
    if c.island_len <= 0:
        w = c.kitchen_w - c.counter_d
        return {"west": w, "north": w, "south": w, "east": w}
    x0, y0 = RANGE_D + c.island_aisle, c.counter_d + c.island_north_aisle
    x1, y1 = x0 + c.island_top_d, y0 + c.island_len
    fixed = [b for b in boxes if b["kind"] in SOLID and not b["id"].startswith("isl_") and b["z"] < 36] + \
            [b for b in shell if b["kind"] in ROOM_SOLID + ("rail",)]
    far = 999.0
    west = min([x0 - (b["x"] + b["dx"]) for b in fixed if b["x"] + b["dx"] <= x0 + TOL and b["y"] < y1 and b["y"] + b["dy"] > y0], default=far)
    east = min([b["x"] - x1 for b in fixed if b["x"] >= x1 - TOL and b["y"] < y1 and b["y"] + b["dy"] > y0], default=far)
    north = min([y0 - (b["y"] + b["dy"]) for b in fixed if b["y"] + b["dy"] <= y0 + TOL and b["x"] < x1 and b["x"] + b["dx"] > x0], default=far)
    south = min([b["y"] - y1 for b in fixed if b["y"] >= y1 - TOL and b["x"] < x1 and b["x"] + b["dx"] > x0], default=far)
    return {"west": west, "north": north, "south": south, "east": east}


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _seg_in_rect(a, b, r):
    """Length of segment a-b inside the axis-aligned rect r = (x0, y0, x1, y1)."""
    (x0, y0, x1, y1) = r
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0:
                return 0.0
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
    return max(0.0, t1 - t0) * math.hypot(dx, dy)


def flow(c: Config) -> dict:
    """Distances a cook walks, measured as the NKBA measures them: centre front of
    each work centre, in straight lines."""
    range_y = CORNER + 24
    sink = (CORNER + 2 + 24 + 16.5, c.counter_d)
    rng = (c.counter_d, range_y + RANGE_W / 2)
    if c.fridge_at == "hall":
        fy = range_y + RANGE_W + 30 + 33 + 1.25
        fridge = (c.fridge_d, fy + FRIDGE_W / 2)
    else:
        fridge = (c.wall2_len + 5.0, NICHE_Y0 + c.alcove_w / 2)   # its door faces west
    has_island = c.island_len > 0
    ix0 = RANGE_D + c.island_aisle
    iy0 = c.counter_d + c.island_north_aisle
    rect = (ix0, iy0, ix0 + c.island_top_d, iy0 + c.island_len)
    prep = None
    if has_island and c.prep_sink:
        run = c.island_len - 4
        n = max(1, round(run / 30.0))
        prep = (ix0, iy0 + 2 + (n - 0.5) * run / n)
    wet = prep or sink            # the sink the cook preps at
    legs = {"wet_range": _dist(wet, rng), "range_fridge": _dist(rng, fridge), "fridge_wet": _dist(fridge, wet)}
    cut = 0.0
    if has_island:
        for a, b in ((sink, rng), (rng, fridge), (fridge, sink)):
            cut = max(cut, _seg_in_rect(a, b, rect))
    return {
        "pt_sink": list(sink), "pt_range": list(rng), "pt_fridge": list(fridge),
        "pt_prep": list(prep) if prep else None, "island_rect": list(rect) if has_island else None,
        "leg_wet_range_ft": legs["wet_range"] / 12, "leg_range_fridge_ft": legs["range_fridge"] / 12,
        "leg_fridge_wet_ft": legs["fridge_wet"] / 12,
        "triangle_longest_ft": max(legs.values()) / 12,
        "triangle_shortest_ft": min(legs.values()) / 12,
        "triangle_total_ft": sum(legs.values()) / 12,
        "fridge_to_cleanup_sink_ft": _dist(fridge, sink) / 12,
        "island_cut_in": cut,
    }


# ----------------------------------------------------------------------------
# CATALOG — what can be chosen, what it costs, and where the price was seen.
#
# Read on 2026-11-12 by three web searches (cabinets, floors, everything else).
# No retailer page could be opened from the build machine, so every price here is
# from a search-result snippet or is an estimate. `v` says which:
#   "seen"      the figure was in a retailer's or maker's search snippet
#   "tag"       the figure is on a store tag in one of the person's own photos
#   "estimate"  arithmetic or a range from cost guides; no page states it
# None of them is a quote. Claim A2 owns that. Hex colours are approximations for
# the drawing only; order samples (claim P2).
# ----------------------------------------------------------------------------
def _c(name, hex_, ral=""):
    return {"name": name, "hex": hex_, "ral": ral}


COLORS = {
    # bright lowers (27estore RAL lacquer; any RAL can be ordered)
    "ultramarine": _c("Ultramarine blue", "#1E3A8A", "RAL 5002"),
    "gentian": _c("Gentian blue", "#0F5C8C", "RAL 5010"),
    "sky": _c("Sky blue", "#1F82C0", "RAL 5015"),
    "emerald": _c("Emerald green", "#2F6B3A", "RAL 6001"),
    "mint": _c("Mint green", "#0E7A45", "RAL 6029"),
    "terracotta": _c("Terracotta", "#A9562F", "RAL 8023"),
    "redorange": _c("Red orange", "#C4491C", "RAL 2001"),
    "yellow": _c("Traffic yellow", "#F2B600", "RAL 1023"),
    "red": _c("Traffic red", "#BE1622", "RAL 3020"),
    "bordo": _c("Bordo red (polyester)", "#7A1E2B"),
    "cobalt": _c("Cobalt pearl (polyester)", "#23408F"),
    # light uppers
    "signalwhite": _c("Signal white", "#ECECE7", "RAL 9003"),
    "purewhite": _c("Pure white", "#F1ECE1", "RAL 9010"),
    "oyster": _c("Oyster white", "#E3D9C6", "RAL 1013"),
    "ivory": _c("Ivory", "#DDC49A", "RAL 1014"),
    "lightgrey": _c("Light grey", "#C5C7C4", "RAL 7035"),
    "pastelgreen": _c("Pastel green", "#B9CEAC", "RAL 6019"),
    # IKEA
    "ikea_gloss_white": _c("RINGHULT high-gloss white", "#F5F5F2"),
    "ikea_graybrown": _c("VOXTORP high-gloss dark gray-brown", "#4A4543"),
    "ikea_matt_white": _c("VOXTORP matt white", "#F2F1EC"),
    "ikea_dark_gray": _c("VOXTORP dark gray", "#4B4D50"),
    # Lioher
    "azul_marino": _c("Luxe Azul Marino gloss", "#1F2A44"),
    "luxe_blanco": _c("Luxe Blanco gloss", "#F4F4F2"),
    # the contractor's shaker line
    "fairy_green": _c("Fairy Green", "#6F8F96"),
    "navy_blue": _c("Navy Blue", "#232B45"),
    "swan_white": _c("Swan White", "#EFEDE4"),
    "artisanal_ash": _c("Artisanal Ash", "#B9BCBC"),
    "timber": _c("Timber", "#B08A60"),
    "gs_black": _c("Black", "#1F2023"),
}
_RAL_LOW = ["ultramarine", "gentian", "sky", "emerald", "mint", "terracotta", "redorange", "yellow", "red"]
_RAL_UP = ["signalwhite", "purewhite", "oyster", "ivory", "lightgrey", "pastelgreen"]
_BM = _RAL_LOW + _RAL_UP        # Bofronts matches any Benjamin Moore colour

CATALOG = {
    "cab_line": {
        # usd_lf: USD per linear foot of run, counted as IKEA counts its "$/lin.ft"
        # (the 10x10 price over 20 ft): wall length with base and wall cabinets,
        # fronts, hinges, drawers, legs, toe kicks and cover panels.
        "sektion_27e_gloss": {
            "label": "IKEA SEKTION boxes + 27estore high-gloss lacquer fronts",
            "vendor": "IKEA Renton + 27estore (online)", "usd_lf": 335.0, "v": "estimate",
            "range": "8,500 to 13,000 USD for this kitchen",
            "gloss": True, "integrated": "ask", "sheen": "gloss", "door": "slab",
            "lower": _RAL_LOW + ["bordo", "cobalt"], "upper": _RAL_UP, "handles": ["integrated", "push", "begripa", "cup_black", "bar_black"],
            "note": "The only route found with true high gloss, any RAL colour and a published price "
                    "(32 to 36 USD per sq ft of front). One product image shows a routed integrated handle; "
                    "no spec for it was found, so ask before ordering. About 6 to 7 weeks.",
            "url": "https://www.27estore.com/high-gloss-color-lacquered-cabinet-doors"},
        "ringhult_27e_hybrid": {
            "label": "IKEA RINGHULT gloss white uppers + 27estore gloss lowers",
            "vendor": "IKEA Renton + 27estore (online)", "usd_lf": 270.0, "v": "estimate",
            "range": "7,000 to 10,500 USD for this kitchen",
            "gloss": True, "integrated": "ask", "sheen": "gloss", "door": "slab",
            "lower": _RAL_LOW + ["bordo", "cobalt"], "upper": ["ikea_gloss_white"], "handles": ["integrated", "push", "begripa", "cup_black", "bar_black"],
            "note": "Cheapest gloss two-tone when the uppers are IKEA's own white, which open by push latch; "
                    "the two gloss surfaces come from two makers and will not match exactly.",
            "url": "https://www.ikea.com/us/en/cat/ringhult-high-gloss-white-fronts-700370/"},
        "voxtorp_gloss": {
            "label": "IKEA VOXTORP high gloss, integrated handle",
            "vendor": "IKEA Renton", "usd_lf": 225.0, "v": "tag",
            "range": "7,000 to 9,500 USD for this kitchen",
            "gloss": True, "integrated": True, "sheen": "gloss", "door": "slab-jpull",
            "lower": ["ikea_graybrown"], "upper": ["ikea_graybrown", "ikea_matt_white"], "handles": ["integrated", "begripa", "cup_black", "bar_black"],
            "note": "In stock, integrated handle, high gloss, but one colour in the US: dark gray-brown. "
                    "225 USD per linear ft on the tag in your photo.",
            "url": "https://www.ikea.com/us/en/cat/voxtorp-fronts-700359/"},
        "voxtorp_matt": {
            "label": "IKEA VOXTORP matt two-tone, integrated handle",
            "vendor": "IKEA Renton", "usd_lf": 215.0, "v": "estimate",
            "range": "7,000 to 9,500 USD for this kitchen",
            "gloss": False, "integrated": True, "sheen": "matt", "door": "slab-jpull",
            "lower": ["ikea_dark_gray"], "upper": ["ikea_matt_white"], "handles": ["integrated", "begripa", "cup_black", "bar_black"],
            "note": "Integrated handle and two tones from stock, but matt and not bright.",
            "url": "https://www.ikea.com/us/en/cat/voxtorp-fronts-700359/"},
        "sektion_bofronts": {
            "label": "IKEA SEKTION boxes + Bofronts 'Pull' lacquer fronts",
            "vendor": "IKEA Renton + Bofronts (online)", "usd_lf": 520.0, "v": "estimate",
            "range": "14,000 to 20,000 USD for this kitchen",
            "gloss": False, "integrated": True, "sheen": "satin", "door": "slab-jpull",
            "lower": _BM, "upper": _BM, "handles": ["integrated", "begripa", "cup_black", "bar_black"],
            "note": "A recessed integrated pull and any Benjamin Moore colour at no extra cost, with a "
                    "published price (15x30 door 277 USD). The sheen is not stated and is probably satin.",
            "url": "https://bofronts.com/en-us/collections/lacquer-2"},
        "gs_shaker": {
            "label": "GS painted shaker (your contractor's line)",
            "vendor": "GS, 4th Ave S, Seattle", "usd_lf": 160.0, "v": "estimate",
            "range": "put your contractor's quote here",
            "gloss": False, "integrated": False, "sheen": "matt", "door": "shaker",
            "lower": ["fairy_green", "navy_blue", "gs_black", "timber"], "upper": ["swan_white", "artisanal_ash", "fairy_green", "timber"],
            "handles": ["bar", "begripa", "cup_black", "bar_black"],
            "note": "The line in your showroom photo. No public price; a like line sells online at about "
                    "2,540 USD per 10x10, so this figure is a guess. Painted shaker with pulls.",
            "url": "https://www.checkbook.org/wa/seattle/cabinet-suppliers/gs-building-supply/ob7qf"},
        "lioher_shop": {
            "label": "Local shop, Lioher finger-pull gloss doors",
            "vendor": "a Seattle-area cabinet shop", "usd_lf": 650.0, "v": "estimate",
            "range": "15,000 to 28,000 USD for this kitchen; quotes needed",
            "gloss": True, "integrated": True, "sheen": "gloss", "door": "slab-jpull",
            "lower": ["azul_marino"], "upper": ["luxe_blanco"], "handles": ["integrated", "begripa", "cup_black", "bar_black"],
            "note": "A routed finger-pull edge in high gloss, navy over white only. No list price found.",
            "url": "https://lioher.com/doors/fingerpull/"},
        "bauformat": {
            "label": "Bauformat Seattle, handleless gloss lacquer",
            "vendor": "Bauformat, 2605 Western Ave, Seattle", "usd_lf": 900.0, "v": "estimate",
            "range": "25,000 USD and up per kitchen",
            "gloss": True, "integrated": True, "sheen": "gloss", "door": "slab-channel",
            "lower": _RAL_LOW, "upper": _RAL_UP, "handles": ["integrated", "begripa", "cup_black", "bar_black"],
            "note": "German handleless cabinets with lacquered channels, exactly the look, at a showroom "
                    "20 minutes away. Another dealer puts kitchens at 25,000 USD and up.",
            "url": "https://bauformatseattle.com/showroom"},
    },
    "handles": {
        "integrated": {"label": "Integrated (no hardware)", "usd_each": 0.0, "v": "seen", "vendor": "the front maker", "url": ""},
        "push": {"label": "Push-to-open latches", "usd_each": 7.0, "v": "estimate", "vendor": "IKEA UTRUSTA or Blum", "url": ""},
        "begripa": {"label": "IKEA BEGRIPA half-round, one colour or mixed", "usd_each": 4.0, "v": "tag", "vendor": "IKEA Renton",
                    "url": "https://www.ikea.com/us/en/p/begripa-handle-yellow-half-round-50572600/"},
        "cup_black": {"label": "Matte black cup pull, 3.5 in", "usd_each": 6.5, "v": "seen", "vendor": "LynnsGraceland on Amazon",
                      "url": "https://www.amazon.com/dp/B09NLR9YR8?th=1"},
        "bar_black": {"label": "Matte black square bar pull, 160 mm centres", "usd_each": 2.2, "v": "seen", "vendor": "Rergy on Amazon, 10 for $21.95",
                      "url": "https://www.amazon.com/dp/B07RZRNTRR?th=1"},
        "bar": {"label": "Bar pulls", "usd_each": 6.0, "v": "estimate", "vendor": "the cabinet supplier", "url": ""},
    },
    "cab_install": {
        "pro": {"label": "Installer assembles and installs", "usd_lf": 180.0, "v": "estimate",
                "vendor": "IKEA-kitchen installer", "url": "https://www.inchcalculator.com/new-cabinets-cost-guide/"},
        "self_assemble": {"label": "You assemble the boxes, installer hangs them", "usd_lf": 100.0, "v": "estimate",
                          "vendor": "IKEA-kitchen installer", "url": "https://www.thumbtack.com/wa/seattle/cabinets-companies"},
    },
    "counter": {
        "quartz_calacatta": {"label": "Quartz, Calacatta look (MSI or Pental)", "usd_sqft": 95.0, "v": "estimate", "hex": "#F1EEE8", "vein": "#C9B48F",
                             "vendor": "Granite & Marble Specialties, Lynnwood", "url": "https://granitemarblewa.com/showrooms/lynnwood-wa/quartz-countertops/"},
        "ikea_kasker": {"label": "IKEA KASKER custom quartz", "usd_sqft": 60.0, "v": "seen", "hex": "#F2F0EC", "vein": "#D5CBB8",
                        "vendor": "IKEA Renton", "url": "https://www.hunker.com/13723444/ikea-countertops-kitchen-ideas-and-inspiration"},
        "quartz_premium": {"label": "Quartz, Caesarstone or Cambria marble look", "usd_sqft": 120.0, "v": "estimate", "hex": "#F4F1EA", "vein": "#B9A27A",
                           "vendor": "Granite & Marble Specialties, Lynnwood", "url": "https://fixr.com/costs/install-quartz-countertop"},
        "porcelain": {"label": "Sintered stone / porcelain", "usd_sqft": 90.0, "v": "seen", "hex": "#EDEAE4", "vein": "#BDB6A8",
                      "vendor": "a Lynnwood fabricator", "url": "https://www.fixr.com/costs/install-stone-slab-countertops"},
        # Concrete greys and soapstone. `look` tells the drawing how to paint the slab.
        "quartz_concrete_light": {"label": "Quartz, pale concrete (Caesarstone Fresh or Raw Concrete)", "usd_sqft": 100.0, "v": "estimate", "hex": "#D3D0C9", "vein": "#B9B5AC", "look": "concrete",
                                  "vendor": "a Lynnwood fabricator", "url": "https://angi.com/articles/how-much-do-caesarstone-countertops-cost.htm"},
        "quartz_concrete": {"label": "Quartz, concrete grey (Caesarstone Sleek or Rugged Concrete)", "usd_sqft": 100.0, "v": "estimate", "hex": "#9C9B96", "vein": "#7F7E79", "look": "concrete",
                            "vendor": "a Lynnwood fabricator", "url": "https://angi.com/articles/how-much-do-caesarstone-countertops-cost.htm"},
        "soapstone": {"label": "Soapstone, honed (natural stone; soft, darkens when oiled)", "usd_sqft": 95.0, "v": "estimate", "hex": "#454B49", "vein": "#C3CAC6", "look": "soapstone",
                      "vendor": "a Seattle-area stone yard", "url": "https://www.fixr.com/costs/soapstone-countertop-installation"},
        "quartz_soapstone": {"label": "Quartz, soapstone look (Silestone Charcoal Soapstone)", "usd_sqft": 95.0, "v": "estimate", "hex": "#3D4144", "vein": "#B4B9BB", "look": "soapstone",
                             "vendor": "a Lynnwood fabricator", "url": "https://slabwise.com/guides/cost-per-sq-ft-quartz-countertop"},
        "butcher": {"label": "Butcher block, edge grain", "usd_sqft": 55.0, "v": "seen", "hex": "#C99B66", "vein": "#B5854F",
                    "vendor": "a Lynnwood fabricator", "url": "https://slabwise.com/guides/countertop-cost"},
        "laminate": {"label": "High-pressure laminate", "usd_sqft": 35.0, "v": "seen", "hex": "#E9E7E2", "vein": "#E0DDD6",
                     "vendor": "a Lynnwood fabricator", "url": "https://www.inchcalculator.com/new-countertop-cost-guide/"},
    },
    "sink": {
        "ruvati_32": {"label": "Ruvati 32 in undermount workstation, 16 ga", "usd": 430.0, "v": "seen", "style": "undermount",
                      "vendor": "The Sink Boutique (online)", "url": "https://thesinkboutique.com/products/ruvati-roma-32-inch-undermount-stainless-steel-workstation-kitchen-sink-16-gauge-rvh8300"},
        "havsen": {"label": "IKEA HAVSEN apron-front, white", "usd": 299.0, "v": "tag", "style": "apron",
                   "vendor": "IKEA Renton", "url": "https://www.ikea.com/us/en/p/havsen-apron-front-sink-white-40359228/"},
        "kraus_32": {"label": "Kraus Kore 32 in workstation", "usd": 600.0, "v": "seen", "style": "undermount",
                     "vendor": "DirectSinks (online)", "url": "https://directsinks.com/collections/kitchen-sinks-with-off-set-drains/products/kraus-kore-32-inch-undermount-workstation-kitchen-sink"},
        "hillesjon": {"label": "IKEA HILLESJON stainless double bowl", "usd": 189.0, "v": "seen", "style": "undermount",
                      "vendor": "IKEA Renton", "url": "https://www.ikea.com/us/en/p/hillesjoen-double-bowl-dual-mount-sink-stainless-steel-30324890"},
    },
    "faucet": {
        # `style` tells the drawing what to build: a "spring" (an exposed coil with
        # the spray head docked on a side arm, the commercial look) or a "gooseneck"
        # (a plain high arc with a pull-down head). `h_in` is the maker's overall
        # height, deck to top; `reach_in` the spout reach. Both are for the drawing
        # and for clearance under the window header, not for any gate.
        "majsjon": {"label": "IKEA MAJSJON pull-down, spring, stainless", "usd": 199.0, "v": "tag", "vendor": "IKEA Renton",
                    "style": "spring", "h_in": 22.375, "reach_in": 9.0, "hex": "#C9CBCD", "body": "square", "arm": True,
                    "note": "The faucet on the showroom display: boxy body, cone spray head, coil with a side arm. 199 USD on the store tag; 229 on ikea.com.",
                    "url": "https://www.ikea.com/us/en/p/majsjoen-pull-down-kitchen-faucet-with-spray-stainless-steel-90610619/"},
        "taksjon": {"label": "IKEA TAKSJON pull-down, spring, stainless", "usd": 179.0, "v": "seen", "vendor": "IKEA Renton",
                    "style": "spring", "h_in": 18.875, "reach_in": 8.0, "hex": "#C9CBCD", "body": "round", "arm": True,
                    "note": "The same spring-and-arm idea as MAJSJON, 3.5 in shorter, round body, curved lever.",
                    "url": "https://www.ikea.com/us/en/p/taksjoen-pull-down-kitchen-faucet-with-spray-stainless-steel-10610500/"},
        "kraus_bolden": {"label": "Kraus Bolden KPF-1610SFS, spring, spot-free stainless", "usd": 215.0, "v": "seen", "vendor": "Kraus (online); Home Depot sells it for less",
                         "style": "spring", "h_in": 18.0, "reach_in": 8.75, "hex": "#C4C6C8", "body": "round", "arm": True,
                         "note": "The most-bought faucet of this kind: brass body, open coil, two-function head with a flow toggle, 180 degree swivel, 1.8 gpm. 214.95 at Kraus; 143 to 192 seen at Home Depot and Riverbend Home.",
                         "url": "https://www.kraususa.com/kitchen/kitchen-faucet-collections/bolden.html"},
        "delta_antoni": {"label": "Delta Antoni 18803-SP-DST, spring, Spotshield stainless", "usd": 613.0, "v": "seen", "vendor": "Delta (list; out of stock at deltafaucet.com)",
                         "style": "spring", "h_in": 19.75, "reach_in": 9.25, "hex": "#C8CACB", "body": "round", "arm": True,
                         "note": "Delta's pro-style spring with a magnetic docking head and a braided hose; closest in proportion to the IKEA one.",
                         "url": "https://www.deltafaucet.com/kitchen/product/18803-SP-DST"},
        "moen_align": {"label": "Moen Align 5923SRS, pre-rinse spring, Spot Resist stainless", "usd": 793.0, "v": "seen", "vendor": "Moen (online); 672 to 743 at supply houses",
                       "style": "spring", "h_in": 21.75, "reach_in": 10.0, "hex": "#C6C8CA", "body": "round", "arm": True,
                       "note": "Pre-rinse spring with the Power Boost button, a 68 in hose and a lifetime warranty. 793.28 web price against a 991.60 list.",
                       "url": "https://www.moen.com/products/Align/Align-Spot-Resist-Stainless-One-Handle-Pre-Rinse-Spring-Pulldown-Kitchen-Faucet/5923SRS"},
        "delta_trinsic_pro": {"label": "Delta Trinsic Pro 9659-AR-DST, spring, Arctic stainless", "usd": 629.0, "v": "seen", "vendor": "Splashes (online; chrome); Arctic Stainless lists at 970",
                              "style": "spring", "h_in": 18.375, "reach_in": 9.0, "hex": "#C8CACB", "body": "round", "arm": True,
                              "note": "A 360 degree spring spout with a magnetic docking head, 1.8 gpm; a Touch2O version exists. 535 to 629 seen for the chrome 9659-DST.",
                              "url": "https://www.deltafaucet.com/kitchen/product/9659-AR-DST"},
        "kohler_tournant": {"label": "Kohler Tournant K-77515-VS, semi-pro spring, Vibrant stainless", "usd": 984.0, "v": "seen", "vendor": "SupplyHouse / GN Kitchen & Bath (online); discontinued by Kohler",
                            "style": "spring", "h_in": 24.5625, "reach_in": 10.0, "hex": "#C2C4C6", "body": "round", "arm": False,
                            "note": "The tallest: 24 9/16 in with a removable coil and a three-function head, 1.5 gpm. Kohler has discontinued it; 750 to 985 while retailers have stock.",
                            "url": "https://www.supplyhouse.com/Kohler-K-77515-VS-Tournant-Semi-Professional-1-Handle-Pull-Out-Kitchen-Faucet-with-Spray-Stainless-Steel"},
        "macksjon": {"label": "IKEA MACKSJON pull-down", "usd": 109.0, "v": "seen", "vendor": "IKEA Renton",
                     "style": "gooseneck", "h_in": 16.5, "reach_in": 8.5, "hex": "#C9CBCD", "body": "round", "arm": False,
                     "url": "https://www.ikea.com/us/en/p/macksjoen-pull-down-kitchen-faucet-with-spray-stainless-steel-80600833/"},
        "delta_leland": {"label": "Delta Leland pull-down", "usd": 320.0, "v": "seen", "vendor": "Home Depot Lynnwood",
                         "style": "gooseneck", "h_in": 14.875, "reach_in": 9.5, "hex": "#C8CACB", "body": "round", "arm": False,
                         "url": "https://www.homedepot.com/p/204184513"},
        "moen_arbor": {"label": "Moen Arbor pull-down", "usd": 338.0, "v": "seen", "vendor": "Home Depot Lynnwood",
                       "style": "gooseneck", "h_in": 15.5, "reach_in": 7.875, "hex": "#C6C8CA", "body": "round", "arm": False,
                       "url": "https://www.homedepot.com/p/203399674"},
    },
    "backsplash": {
        "tile": {"label": "Tile", "usd_sqft": 40.0, "v": "estimate", "hex": "#EDEBE6", "vendor": "a tile setter",
                 "url": "https://www.homeadvisor.com/cost/kitchens/tile-backsplash-install"},
        # Hand-painted 4 in tile is 8 to 20 USD per sq ft and a setter 12 to 22; small
        # patterned tile sets slowly. The white field with accents is mostly plain tile.
        "talavera": {"label": "Spanish (Talavera) patterned tile, assorted 4 in", "usd_sqft": 55.0, "v": "estimate", "hex": "#2C4FA3", "look": "talavera",
                     "vendor": "a tile setter; tile from a Talavera importer (online)", "url": "https://dgfloors.com/talavera-tile-backsplash/"},
        "half_talavera": {"label": "Spanish tiles alternating with white 4 in tile", "usd_sqft": 50.0, "v": "estimate", "hex": "#8FA0C8", "look": "talavera_half",
                          "vendor": "a tile setter; tile from a Talavera importer (online)", "url": "https://dgfloors.com/talavera-tile-backsplash/"},
        "white_talavera": {"label": "White 4 in tile with Spanish tiles scattered through it", "usd_sqft": 45.0, "v": "estimate", "hex": "#F2F0EA", "look": "talavera_sparse",
                           "vendor": "a tile setter; tile from a Talavera importer (online)", "url": "https://dgfloors.com/mexican-tile-backsplash/"},
        "quartz_slab": {"label": "Full-height quartz slab, matching the counter", "usd_sqft": 100.0, "v": "seen", "hex": "#F1EEE8",
                        "vendor": "the counter fabricator", "url": "https://slabwise.com/guides/how-to-price-a-full-height-stone-backsplash-vs-a-tile-backsplash"},
        "paint": {"label": "Painted wall for now", "usd_sqft": 0.0, "v": "estimate", "hex": "#F3F0E8", "vendor": "none", "url": ""},
    },
    "floor": {
        # wear in mil; usd_sqft is material only
        "flooret_sig_soho": {"label": "Flooret Modin Signature, Soho (natural oak)", "usd_sqft": 4.95, "v": "seen", "wear": 40, "thick_mm": 7, "plank": [9, 72], "hex": "#C8A67A",
                             "vendor": "Flooret (online)", "url": "https://www.flooret.com/products/soho"},
        "flooret_sig_elmstead": {"label": "Flooret Modin Signature, Elmstead (mid brown oak)", "usd_sqft": 4.95, "v": "seen", "wear": 40, "thick_mm": 7, "plank": [9, 72], "hex": "#9E7B56",
                                 "vendor": "Flooret (online)", "url": "https://www.flooret.com/products/elmstead"},
        "flooret_base_soho": {"label": "Flooret Modin Base, Soho", "usd_sqft": 2.95, "v": "seen", "wear": 20, "thick_mm": 5.5, "plank": [7, 48], "hex": "#C8A67A",
                              "vendor": "Flooret (online)", "url": "https://www.flooret.com/soho-base"},
        "lifeproof_sterling": {"label": "LifeProof Sterling Oak", "usd_sqft": 3.69, "v": "seen", "wear": 22, "thick_mm": 6.5, "plank": [8.7, 72], "hex": "#CDB89A",
                               "vendor": "Home Depot, 2901 184th St SW, Lynnwood", "url": "https://homedepot.com/p/327346474"},
        "nucore_dolce": {"label": "NuCore Performance Dolce Oak", "usd_sqft": 3.79, "v": "seen", "wear": 20, "thick_mm": 6.5, "plank": [7, 48], "hex": "#B9986E",
                         "vendor": "Floor & Decor, 13200 Aurora Ave N, Seattle", "url": "https://www.flooranddecor.com/nucore-performance-flooring/dolce-oak-waterproof-rigid-core-luxury-vinyl-plank---cork-pad-101329555.html"},
        "coretec_pro_bedford": {"label": "COREtec Pro Plus Enhanced HD, Bedford Oak", "usd_sqft": 5.39, "v": "seen", "wear": 20, "thick_mm": 5, "plank": [9, 72], "hex": "#B79670",
                                "vendor": "Great Floors, 5501 196th St SW, Lynnwood", "url": "https://build.com/coretec-vv492-02005/s1881737"},
        "coretec_premium_coretta": {"label": "COREtec Originals Premium 9 in, Coretta Oak", "usd_sqft": 9.09, "v": "seen", "wear": 30, "thick_mm": 12, "plank": [9, 72], "hex": "#CDB592",
                                    "vendor": "Great Floors, 5501 196th St SW, Lynnwood", "url": "https://coretecfloors.com/en-us/products/coretec-premium/coretta-oak-vv457-02908"},
        "adura_almond": {"label": "Mannington ADURA Max, Swiss Oak Almond", "usd_sqft": 5.69, "v": "seen", "wear": 20, "thick_mm": 8, "plank": [7, 48], "hex": "#D2B48C",
                         "vendor": "Great Floors, 5501 196th St SW, Lynnwood", "url": "https://www.nfm.com/mannington-swiss-oak-almond-7-x-48-luxury-vinyl-plank-6966073/6966073.html"},
        "karndean_baltic": {"label": "Karndean Korlok Select, Baltic Washed Oak", "usd_sqft": 3.99, "v": "seen", "wear": 20, "thick_mm": 6.5, "plank": [9, 56], "hex": "#D6C3A3",
                            "vendor": "a Karndean dealer", "url": "https://carpetexchange.com/karndean/korlok-select-baltic-washed-oak-rkp8101-balticwashedoak.html"},
        "provenza_naturally": {"label": "Provenza Uptown Chic, Naturally Yours", "usd_sqft": 5.09, "v": "seen", "wear": 20, "thick_mm": 8, "plank": [7.15, 60], "hex": "#C6A77F",
                               "vendor": "Contract Furnishings Mart, Everett", "url": "https://nfm.com/provenza-vinyl-uptown-chic-naturally-yours-7-15-x-48-luxury-vinyl-plank/3355304.html"},
    },
    "floor_removal": {
        "pro": {"label": "Installer removes and hauls the bamboo", "usd_sqft": 3.00, "v": "estimate", "vendor": "the flooring installer",
                "url": "https://contractorplus.app/resources/construction-costs/remove-flooring/tacoma-wa"},
        "diy": {"label": "You pull the bamboo; pay the dump", "usd_sqft": 0.35, "v": "estimate", "vendor": "transfer station", "url": ""},
    },
    "managed_by": {
        "self": {"label": "You hire the trades directly", "markup": 0.0, "v": "seen", "vendor": "", "url": ""},
        "gc": {"label": "A general contractor runs it", "markup": 0.18, "v": "seen", "vendor": "a general contractor",
               "url": "https://construction2style.com/contractor-markup-30-percent-normal-what-it-covers/"},
    },
    "pantry": {
        "open": {"label": "Lined with open shelves, walls as they are", "v": "estimate"},
        "door": {"label": "The same shelves behind a hinged door", "v": "estimate"},
        "cabinets": {"label": "Tall pantry cabinets, lower colour", "v": "estimate"},
    },
    "microwave_at": {
        "pantry": {"label": "On a 30 in shelf in the pantry"},
        "island": {"label": "Drawer microwave in the island"},
        "counter": {"label": "On the counter, as today"},
    },
    "fridge_at": {
        "hall": {"label": "Hall end of the long wall (the mock-up)"},
        "alcove": {"label": "Stays in the alcove"},
    },
}

# Every colour a line's maker offers can go on the lowers or on the uppers: each
# list is the maker's whole palette, with the colours meant for that position first.
for _line_ in CATALOG["cab_line"].values():
    _lo, _up = _line_["lower"], _line_["upper"]
    _line_["lower"] = _lo + [k for k in _up if k not in _lo]
    _line_["upper"] = _up + [k for k in _lo if k not in _up]

# Fixed work that no selection moves. usd is the typical figure from the trades
# search; all are estimates built from national guides with Seattle labour rates.
FIXED = {
    "demo": ("Demolition and disposal of the old kitchen", 1800.0, "a demolition crew", "https://angi.com/articles/how-to-demo-kitchen.htm"),
    "plumb_reconnect": ("Plumber: sink, faucet, disposal and dishwasher reconnect", 800.0, "a plumber", "https://bobvila.com/articles/cost-to-install-kitchen-faucet"),
    "undercab_labor": ("Electrician: under-cabinet lighting", 500.0, "an electrician", "https://homeadvisor.com/cost/electrical/install-under-cabinet-lighting"),
    "undercab_lights": ("IKEA MITTLED LED strips, driver and cords", 250.0, "IKEA Renton", "https://www.ikea.com/us/en/p/mittled-led-kitchen-cntrtp-lighting-strip-dimmable-white-10455434/"),
    "drywall_paint": ("Drywall patch and kitchen repaint", 1500.0, "a painter", "https://www.angi.com/articles/how-much-does-it-cost-paint-room/wa/seattle"),
}
FRIDGE_MOVE = {
    "fridge_circuit": ("Electrician: new 120 V refrigerator receptacle at the hall end", 700.0, "an electrician", "https://angi.com/articles/cost-to-install-dedicated-circuit.htm"),
    "ice_line": ("Plumber: ice-maker water line to the hall end", 400.0, "a plumber", "https://homeguide.com/costs/refrigerator-water-line-installation-cost"),
}
PREP_SINK = {
    "prep_rough": ("Plumber: supply, drain and vent to the island through the floor, ceiling below patched", 3000.0, "a plumber", ""),
    "prep_bowl": ("15 in undermount bar sink", 250.0, "Ruvati (online)", ""),
    "prep_faucet": ("IKEA MACKSJON pull-down faucet", 109.0, "IKEA Renton", "https://www.ikea.com/us/en/p/macksjoen-pull-down-kitchen-faucet-with-spray-stainless-steel-80600833/"),
    "prep_cutout": ("Second sink cut-out in the island top", 250.0, "the counter fabricator", ""),
}
PANTRY = {
    "open": [("pantry_shelves", "Shelving lining the alcove: back and both sides (IKEA BOAXEL or site-built)", 300.0, "IKEA Renton", "https://www.ikea.com/us/en/p/boaxel-shelving-unit-white-s09392616")],
    "door": [("pantry_shelves", "Shelving lining the alcove: back and both sides (IKEA BOAXEL or site-built)", 300.0, "IKEA Renton", "https://www.ikea.com/us/en/p/boaxel-shelving-unit-white-s09392616"),
             ("pantry_door", "Hinged door: frame the opening to 36 in, prehung door, casing, paint", 1000.0, "a carpenter", "https://www.homeadvisor.com/cost/doors-and-windows/interior-door")],
    "cabinets": [],     # priced as 3 linear ft more of the chosen cabinet line
}
MICROWAVE = {
    "counter": [],
    "pantry": [("mw_outlet", "Electrician: receptacle at the pantry shelf", 350.0, "an electrician", "")],
    "island": [("mw_drawer", "24 in drawer microwave", 1300.0, "an appliance dealer", ""),
               ("mw_circuit", "Electrician: circuit to the island", 450.0, "an electrician", "")],
}
FLOOR_WORK = {      # per sq ft of floor, typical
    "floor_labor": ("Floating click LVP installation", 3.50, "the flooring installer", "https://www.countbricks.com/post/lvp-installation-cost"),
    "floor_prep": ("Subfloor prep and levelling", 1.00, "the flooring installer", "https://dgfloors.com/cost-to-install-lvp-flooring/"),
}
FLOOR_WASTE = 0.10          # planks ordered over floor measured; 7% is the low convention, 12 to 15% for diagonal lays
BASEBOARD_LF, BASEBOARD_USD = 500.0, 3.50   # ASSUMED length; remove and reinstall
FLOOR_TRIM_USD = 700.0      # transitions at two baths, flush stair nose, scribe at the rail posts
PERMITS_USD = 200.0         # L&I electrical 78.80 (seen) plus an Edmonds plumbing permit; not taxed
PANTRY_CAB_LF = 3.0


def _line(ref, desc, qty, unit, price, vendor, url, v, group):
    qty = round(qty, 2)      # the bill states two decimals; every sum uses the stated quantity
    return {"ref": ref, "description": desc, "qty_per_unit": qty, "unit": unit,
            "unit_price": round(price, 2), "price_currency": "USD", "vendor": vendor or "to be chosen",
            "vendor_pn": ref, "url": url, "basis": v, "group": group,
            "extended": round(qty * price, 2)}


def quantities(c: Config, boxes: list[dict]) -> dict:
    tops = [b for b in boxes if b["kind"] == "counter"]
    counter_sqft = sum(b["dx"] * b["dy"] for b in tops) / 144.0
    range_y = CORNER + 24
    w1_run = (range_y) + ((CORNER + 24 + RANGE_W + 63) if c.fridge_at == "hall" else c.wall1_len - 4) - range_y - RANGE_W
    splash_in = w1_run + (c.wall2_len - c.counter_d) - c.window_w
    fronts = 0
    for b in boxes:
        f = b["fronts"]
        fronts += {"drawer3": 3, "door2+drawer": 3, "door2+false": 3, "door2": 2, "door1": 1,
                   "door1tall": 2, "corner": 1, "microwave": 1}.get(f, 0)
    run_lf = (c.wall1_len + c.wall2_len + c.island_len) / 12.0
    if c.fridge_at == "hall" and c.pantry == "cabinets":
        run_lf += PANTRY_CAB_LF
    frontage = sum((b["dy"] if b["dx"] <= c.counter_d + 0.01 and b["id"].startswith("top_w1") else b["dx"] if b["id"] == "top_w2" else b["dy"] if b["id"] == "isl_top" else 0) for b in tops)
    return {"counter_sqft": counter_sqft, "backsplash_sqft": splash_in * c.upper_gap / 144.0,
            "fronts": fronts, "cab_run_lf": run_lf, "counter_frontage_in": frontage,
            "floor_order_sqft": c.floor_area_sqft * (1 + FLOOR_WASTE)}


def bom_lines(c: Config, q: dict) -> list[dict]:
    """Every line of the job, before contingency and tax."""
    L = []
    cat = CATALOG
    line = cat["cab_line"][c.cab_line]
    L.append(_line("cabinets", line["label"], q["cab_run_lf"], "linear ft", line["usd_lf"], line["vendor"], line["url"], line["v"], "cab_line"))
    ins = cat["cab_install"][c.cab_install]
    L.append(_line("cab_install", "Cabinets: " + ins["label"].lower(), q["cab_run_lf"], "linear ft", ins["usd_lf"], ins["vendor"], ins["url"], ins["v"], "cab_install"))
    h = cat["handles"][c.handles]
    if h["usd_each"] > 0:
        L.append(_line("handles", h["label"], q["fronts"], "each", h["usd_each"], h["vendor"], h["url"], h["v"], "handles"))
    t = cat["counter"][c.counter]
    L.append(_line("counter", "Countertop, installed: " + t["label"], q["counter_sqft"], "sq ft", t["usd_sqft"], t["vendor"], t["url"], t["v"], "counter"))
    s = cat["backsplash"][c.backsplash]
    if s["usd_sqft"] > 0:
        L.append(_line("backsplash", "Backsplash, installed: " + s["label"], q["backsplash_sqft"], "sq ft", s["usd_sqft"], s["vendor"], s["url"], s["v"], "backsplash"))
    k = cat["sink"][c.sink]
    L.append(_line("sink", k["label"], 1, "each", k["usd"], k["vendor"], k["url"], k["v"], "sink"))
    f = cat["faucet"][c.faucet]
    L.append(_line("faucet", f["label"], 1, "each", f["usd"], f["vendor"], f["url"], f["v"], "faucet"))
    for ref, (d, usd, ven, url) in FIXED.items():
        L.append(_line(ref, d, 1, "job", usd, ven, url, "estimate", "fixed"))
    if c.fridge_at == "hall":
        for ref, (d, usd, ven, url) in FRIDGE_MOVE.items():
            L.append(_line(ref, d, 1, "job", usd, ven, url, "estimate", "fridge_at"))
        for ref, d, usd, ven, url in PANTRY[c.pantry]:
            L.append(_line(ref, d, 1, "job", usd, ven, url, "estimate", "pantry"))
    if c.island_len > 0 and c.prep_sink:
        for ref, (d, usd, ven, url) in PREP_SINK.items():
            L.append(_line(ref, d, 1, "job", usd, ven, url, "estimate", "prep_sink"))
    for ref, d, usd, ven, url in MICROWAVE[c.microwave_at]:
        L.append(_line(ref, d, 1, "job", usd, ven, url, "estimate", "microwave_at"))
    fl = cat["floor"][c.floor]
    L.append(_line("floor", "LVP: " + fl["label"], q["floor_order_sqft"], "sq ft", fl["usd_sqft"], fl["vendor"], fl["url"], fl["v"], "floor"))
    for ref, (d, usd, ven, url) in FLOOR_WORK.items():
        L.append(_line(ref, d, c.floor_area_sqft, "sq ft", usd, ven, url, "estimate", "floor_work"))
    rm = cat["floor_removal"][c.floor_removal]
    L.append(_line("floor_removal", "Old bamboo: " + rm["label"].lower(), c.floor_area_sqft, "sq ft", rm["usd_sqft"], rm["vendor"], rm["url"], rm["v"], "floor_removal"))
    L.append(_line("baseboard", "Baseboard removed and reinstalled", BASEBOARD_LF, "linear ft", BASEBOARD_USD, "the flooring installer", "", "estimate", "floor_work"))
    L.append(_line("floor_trim", "Transitions, stair nose and scribing at the rail", 1, "job", FLOOR_TRIM_USD, "the flooring installer", "", "estimate", "floor_work"))
    return L


def money(c: Config, lines: list[dict]) -> dict:
    sub = sum(l["extended"] for l in lines)
    markup = sub * CATALOG["managed_by"][c.managed_by]["markup"]
    cont = (sub + markup) * c.contingency
    tax = (sub + markup + cont) * c.sales_tax
    total = sub + markup + cont + tax + PERMITS_USD
    return {"subtotal_usd": sub, "markup_usd": markup, "contingency_usd": cont, "tax_usd": tax,
            "permits_usd": PERMITS_USD, "total_usd": total, "headroom_usd": c.budget_usd - total}


def build(config: Config | None = None) -> dict:
    """Resolve every derived quantity. Pure, deterministic, no I/O."""
    c = config or CONFIG
    for g in ("cab_line", "counter", "sink", "faucet", "backsplash", "floor", "handles",
              "cab_install", "floor_removal", "managed_by", "pantry", "microwave_at", "fridge_at"):
        if getattr(c, g) not in CATALOG[g]:
            raise ValueError(f"{g}={getattr(c, g)!r} is not in CATALOG[{g!r}]: {sorted(CATALOG[g])}")
    if c.microwave_at == "island" and c.island_len <= 0:
        raise ValueError("microwave_at='island' needs an island")
    boxes = wall1(c) + wall2(c) + island(c) + alcove(c) + counters(c)
    for b in boxes:
        if b["face"] and b["kind"] in ("base", "upper", "tall"):
            b["rects"] = front_rects(b)
    shell = room(c)
    opens = open_volumes(c, boxes)
    hits = collisions(boxes, shell)
    blocked = blocked_doors(opens, boxes, shell)
    ways = walkways(c, boxes, shell)
    f = flow(c)
    q = quantities(c, boxes)
    lines = bom_lines(c, q)
    m = money(c, lines)
    line = CATALOG["cab_line"][c.cab_line]
    fl = CATALOG["floor"][c.floor]

    # agreement between representations (rule 6): the boxes drawn on each wall
    # must fill the wall the contractor measured
    w1 = sum(b["dy"] for b in boxes if b["id"].startswith("w1_") and b["z"] == 0 and b["kind"] in ("base", "panel", "filler")) + RANGE_W + (FRIDGE_W if c.fridge_at == "hall" else 0)
    w2 = CORNER + sum(b["dx"] for b in boxes if b["id"].startswith("w2_") and b["z"] == 0 and b["id"] != "w2_corner_return") + DW_W
    win = next(b for b in boxes if b["id"] == "window")
    u_l = next(b for b in boxes if b["id"] == "w2_u27")
    u_r = next(b for b in boxes if b["id"] == "w2_u33")
    window_gap = min(win["x"] - (u_l["x"] + u_l["dx"]), u_r["x"] - (win["x"] + win["dx"]))

    seats = int(c.island_len // STOOL_W) if c.island_len > 0 else 0
    knee = c.island_top_d - c.base_d - 1.0 if c.island_len > 0 else 0.0
    east_of_island = c.kitchen_w - (RANGE_D + c.island_aisle + c.island_top_d) if c.island_len > 0 else c.kitchen_w - c.counter_d
    dw_stand = c.island_north_aisle - c.base_d - 1.5 if c.island_len > 0 else 99.0
    mw = next((b for b in boxes if b["id"] == "microwave"), None)
    mw_bottom = mw["z"] if mw else DRAWER_MW_BOTTOM
    finish_unmet = [n for n, ok in (
        ("high gloss", bool(line["gloss"])),
        ("lower colour offered", c.lower_color in line["lower"]),
        ("upper colour offered", c.upper_color in line["upper"]),
        ("two different colours", c.lower_color != c.upper_color)) if not ok]

    out = {
        "boxes": boxes,
        "room": shell,
        "opens": opens,
        "collision_pairs": hits,
        "collision_count": len(hits),
        "blocked_doors": blocked,
        "blocked_door_count": len(blocked),
        "walkway_min_in": min(ways.values()),
        "walkways": ways,
        **f, **q, **m,
        "wall1_fill_error_in": abs(w1 - c.wall1_len),
        "wall2_fill_error_in": abs(w2 - c.wall2_len),
        "run_fill_error_in": max(abs(w1 - c.wall1_len), abs(w2 - c.wall2_len)),
        "window_gap_in": window_gap,
        "work_aisle_in": ways["west"],
        "dishwasher_standing_in": dw_stand,
        "island_seats": seats,
        "island_knee_in": knee,
        "east_of_island_in": east_of_island,
        "microwave_bottom_in": mw_bottom,
        "microwave_over_reach_in": mw_bottom - (c.kid_small_h * SHOULDER - REACH_DROP),
        "kid_big_shoulder_in": c.kid_big_h * SHOULDER,
        "kid_small_shoulder_in": c.kid_small_h * SHOULDER,
        "finish_unmet": finish_unmet,
        "finish_unmet_count": len(finish_unmet),
        "handle_integrated": line["integrated"],
        "floor_wear_mil": fl["wear"],
        "faucet_h_in": CATALOG["faucet"][c.faucet]["h_in"],
        "faucet_style": CATALOG["faucet"][c.faucet]["style"],
        "faucet_under_window_head_in": win["z"] + win["dz"] - (c.base_h + c.counter_t + CATALOG["faucet"][c.faucet]["h_in"]),
        "floor_cover": q["floor_order_sqft"] / c.floor_area_sqft,
        "bom": {
            "schema": "nopekit.bom/1", "currency": "USD", "build_quantity": 1,
            "budget_total": c.budget_usd,
            "charges": [
                {"id": "gc-markup", "amount": round(m["markup_usd"], 2), "description": "general contractor overhead and profit"},
                {"id": "contingency", "amount": round(m["contingency_usd"], 2), "description": f"contingency, {c.contingency:.0%} of the subtotal"},
                {"id": "sales-tax", "amount": round(m["tax_usd"], 2), "description": f"Edmonds sales tax, {c.sales_tax:.1%}, on labour and materials"},
                {"id": "permits", "amount": PERMITS_USD, "description": "electrical and plumbing permits"},
            ],
            "lines": lines,
        },
        "config": asdict(c),
    }
    return out


# The recorded design. Why these, and what lost, is in decisions/.
CONFIG = Config(
    cab_line="sektion_27e_gloss", lower_color="gentian", upper_color="oyster",
    counter="ikea_kasker", sink="ruvati_32", faucet="majsjon", backsplash="tile",
    floor="lifeproof_sterling", handles="integrated", managed_by="self",
    cab_install="self_assemble", floor_removal="pro",
)

if __name__ == "__main__":
    import json
    d = build()
    d.pop("boxes"); d.pop("bom"); d.pop("room"); d.pop("opens")
    print(json.dumps(d, indent=2, sort_keys=True))
