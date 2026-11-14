"""inventory.py — what lives in the kitchen today: the things, their sizes and their kinds.

Read on 2026-11-13 from thirteen photographs of the existing kitchen with every door
and drawer open (inputs/references/20261113_*.jpg, records inputs/20261113-*.json),
plus seven things the owner named that the photographs hide or half hide: the
Instant Pot, the Ninja blender, the food processor, the large stock pot, the brisket
knife, the toaster oven and the compost bin.

model/kitchen.py imports this file and finds every thing a place (`stow()`); the
site draws each thing from the `parts` written here. Standard library only.

What this is, and is not (claim A7 owns all of it):
  counts    what could be counted in the photographs. Dishes in the sink and on the
            counter are counted; what was in the dishwasher is not seen and not added.
  sizes     the usual size of that kind of thing, in inches. Nothing was measured.
  seen      the photograph a thing was read from (its time stamp), "named" (the owner
            said they have it; `seen` then also names the photo it is probably in),
            or "likely" (not visible; added because the photographs imply it).
  note      says so where a label could not be read or a thing was not identified.

Frame of a thing: x across as you face it in its cabinet, y from its front to its
back, z up. The origin is the middle of its footprint, on the shelf it stands on.
A part is one of
  ["b", x, y, z, dx, dy, dz, colour, material]      a box, from its low corner
  ["c", x, y, z, r, h, colour, material, r_top]     an upright cylinder or cone, from its base centre
  ["h", x, y, z, r, length, axis, colour, material] a lying cylinder, about its centre; axis "x" or "y"
  ["s", x, y, z, r, colour, material]               a ball, about its centre
Materials: "" (glazed or plastic), "metal", "iron", "glass", "wood", "paper", "soft".
"""
from __future__ import annotations

# ----------------------------------------------------------------------------
# The kinds. `cat` is the owner's own word for the category where they gave one
# ("dishes, pots, pans, appliances, silverware, ingredients, spices, snacks,
# cleaning stuff, 'everything drawer'"); the rest are named here.
#
#   near     where the things are first used, as a point model/kitchen.py knows:
#            range, sink, dishwasher, fridge, prep. None: food that is fetched once
#            per cooking session, or things with no one place of use.
#   freq     3 every day, 2 most weeks, 1 a few times a year
#   wants    the kinds of place that suit it, best first: drawer, shelf (behind a
#            door), floor (the bottom of a base cabinet), pantry (a shelf in the alcove),
#            susan (the corner carousel), undersink, counter
#   food     it is eaten or drunk            chemical  it is a cleaning chemical
#   kid      the children fetch it themselves: it goes where the 5-year-old reaches
#   adult    it goes above the 8-year-old's reach
#   heavy    it does not go above counter height
# ----------------------------------------------------------------------------
def _g(label, short, cat, near, freq, wants, **flags):
    # `short` is what you would write on the cabinet's label; `label` is the kind in full
    return {"label": label, "short": short, "cat": cat, "near": near, "freq": freq, "wants": list(wants), **flags}


GROUPS = {
    # dishes
    "plates": _g("Everyday plates and bowls", "Plates & bowls", "dishes", "dishwasher", 3, ("shelf", "pantry", "drawer")),
    "glasses": _g("Glasses and mugs", "Glasses & mugs", "dishes", "sink", 3, ("shelf", "pantry")),
    "kids": _g("The children's plates, bowls and cups", "Kids' dishes", "dishes", "dishwasher", 3, ("drawer", "pantry"), kid=True),
    "bottles": _g("Water bottles, travel mugs and the lunch bag", "Water bottles & lunch", "dishes", "sink", 3, ("drawer", "pantry", "shelf"), kid=True),
    "serving": _g("Serving bowls, jars, wine glasses and party things", "Serving & party", "dishes", None, 1, ("shelf", "pantry")),
    "silverware": _g("Silverware", "Silverware", "silverware", "dishwasher", 3, ("drawer",)),
    # pots and pans
    "pots": _g("Pots and their lids", "Pots & lids", "pots and pans", "range", 3, ("drawer", "floor"), heavy=True),
    "pans": _g("Frying pans, cast iron and the wok", "Pans", "pots and pans", "range", 3, ("drawer", "floor"), heavy=True),
    "ovenware": _g("Casseroles and baking dishes", "Baking dishes", "pots and pans", "range", 2, ("floor", "drawer", "susan", "shelf"), heavy=True),
    "sheets": _g("Baking sheets, racks and tins, on edge", "Baking sheets", "pots and pans", "range", 2, ("floor",), heavy=True),
    "bowls": _g("Mixing bowls, strainers and the grater", "Mixing bowls", "pots and pans", "prep", 3, ("drawer", "floor")),
    # appliances
    "appl_prep": _g("Stand mixer, food processor and blender", "Mixer & blender", "appliances", "prep", 2, ("floor", "pantry"), heavy=True),
    "appl_cook": _g("Instant Pot and the occasional appliances", "Instant Pot & appliances", "appliances", None, 2, ("pantry", "floor", "susan"), heavy=True),
    "toaster_oven": _g("Toaster oven", "Toaster oven", "appliances", "fridge", 3, ("counter",), counter=True),
    "espresso": _g("Espresso machine", "Espresso", "appliances", "sink", 3, ("counter",), counter=True, food=True),
    # the everything drawer, and what stands by the range
    "tools": _g("The everything drawer: cooking tools", "Everything drawer", "everything drawer", "range", 3, ("drawer",)),
    "crock": _g("Spoons and spatulas in the crock", "Spoons & spatulas", "everything drawer", "range", 3, ("counter",), counter=True),
    "mitts": _g("Oven mitts, pot holders and dish towels", "Mitts & towels", "everything drawer", "range", 3, ("drawer",)),
    "boards": _g("Cutting boards and the brisket knife", "Boards & brisket knife", "everything drawer", "prep", 3, ("drawer",)),
    "wraps": _g("Foil, film, parchment and bags", "Foil, wrap & bags", "food storage", "prep", 3, ("drawer",)),
    "containers": _g("Food containers and their lids", "Food containers", "food storage", "fridge", 3, ("drawer", "shelf", "floor")),
    # food
    "spices": _g("Spices", "Spices", "spices", "range", 3, ("shelf",), food=True),
    "oils": _g("Cooking oils and sauces", "Oils & sauces", "ingredients", "range", 3, ("shelf", "floor"), food=True),
    "coffee": _g("Coffee and tea", "Coffee & tea", "ingredients", "sink", 3, ("shelf", "pantry"), food=True),
    "baking": _g("Baking ingredients", "Baking", "ingredients", None, 2, ("pantry", "susan", "shelf", "floor"), food=True),
    "drygoods": _g("Dry goods, cans and jars", "Dry goods & cans", "ingredients", None, 2, ("pantry", "shelf", "floor"), food=True),
    "bulk": _g("Bulk oil and rice", "Bulk oil & rice", "ingredients", None, 1, ("pantry", "floor"), food=True, heavy=True),
    "snacks": _g("Snacks", "Snacks", "snacks", None, 3, ("pantry", "drawer", "shelf", "floor"), food=True, kid=True),
    "bar": _g("Liquor, wine and bar books", "Liquor & wine", "drinks", None, 1, ("shelf",), food=True, adult=True),
    # the rest
    "medicine": _g("Vitamins, medicine and sunscreen", "Medicine & vitamins", "medicine", "sink", 3, ("shelf",), adult=True),
    "household": _g("Chargers, cables and odds and ends", "Odds & ends", "household", None, 2, ("drawer", "shelf", "pantry")),
    "cleaning": _g("Cleaning chemicals and dishwasher tablets", "Cleaning", "cleaning", "sink", 3, ("undersink",), chemical=True),
    "bags": _g("Paper towels, rags and shopping bags", "Paper towels & bags", "cleaning", "sink", 2, ("undersink", "pantry", "floor")),
    "soap": _g("Dish soap and sponge", "Dish soap", "cleaning", "sink", 3, ("counter",), counter=True, chemical=True),
    "towels": _g("Paper towel holder", "Paper towels", "cleaning", "sink", 3, ("counter",), counter=True),
    "compost": _g("Compost bin", "Compost", "cleaning", "prep", 3, ("counter",), counter=True),
}
CATEGORIES = ["dishes", "silverware", "pots and pans", "appliances", "everything drawer", "food storage",
              "spices", "ingredients", "snacks", "drinks", "medicine", "household", "cleaning"]


# ----------------------------------------------------------------------------
# Shapes. Each returns (w, d, h, parts): the footprint across and front to back,
# the height, and the parts that draw it.
# ----------------------------------------------------------------------------
def _shade(hex_, f):
    v = [min(255, max(0, round(int(hex_[i:i + 2], 16) * f))) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(v)


WHITE, STEEL, IRON, WOOD, BLACK, GLASS = "#f4f2ec", "#c9cbcd", "#1e1f21", "#c99b66", "#1b1c1e", "#dfeef6"


def box(w, d, h, col, mat="", band=None, lid=None):
    parts = [["b", -w / 2, -d / 2, 0, w, d, h, col, mat]]
    if band:
        parts.append(["b", -w / 2 - 0.04, -d / 2 - 0.04, h * 0.28, w + 0.08, d + 0.08, h * 0.4, band, "paper"])
    if lid:
        parts.append(["b", -w / 2 - 0.12, -d / 2 - 0.12, h - 0.7, w + 0.24, d + 0.24, 0.7, lid, mat])
    return w, d, h, parts


def can(dia, h, col, mat="", label=None, lid=None, lid_h=0.5):
    r = dia / 2
    parts = [["c", 0, 0, 0, r, h, col, mat, None]]
    if label:
        parts.append(["c", 0, 0, h * 0.2, r + 0.04, h * 0.5, label, "paper", None])
    if lid:
        parts.append(["c", 0, 0, h - lid_h, r + 0.06, lid_h, lid, "", None])
    return dia, dia, h, parts


def bottle(dia, h, col, cap=BLACK, label=None, mat="glass"):
    r, body, sh = dia / 2, h * 0.62, h * 0.14
    parts = [["c", 0, 0, 0, r, body, col, mat, None], ["c", 0, 0, body, r, sh, col, mat, r * 0.38],
             ["c", 0, 0, body + sh, r * 0.38, h - body - sh - 0.5, col, mat, None],
             ["c", 0, 0, h - 0.5, r * 0.46, 0.5, cap, "", None]]
    if label:
        parts.append(["c", 0, 0, body * 0.22, r + 0.04, body * 0.55, label, "paper", None])
    return dia, dia, h, parts


def stack(dia, h, col, mat=""):
    """Plates, stacked: a foot, the stack, and the well of the top plate."""
    r = dia / 2
    return dia, dia, h, [["c", 0, 0, 0, r * 0.6, h * 0.2, col, mat, r], ["c", 0, 0, h * 0.2, r, h * 0.8, col, mat, None],
                         ["c", 0, 0, h - 0.03, r * 0.7, 0.07, _shade(col, 0.92), mat, None]]


def bowls(dia, h, col, mat="", inside=None):
    """Bowls, nested: wide at the rim, with the inside of the top one."""
    r = dia / 2
    return dia, dia, h, [["c", 0, 0, 0, r * 0.5, h, col, mat, r],
                         ["c", 0, 0, h - 0.04, r * 0.88, 0.08, inside or _shade(col, 0.86), mat, None]]


def mug(col):
    return 4.5, 3.3, 4.2, [["c", -0.6, 0, 0, 1.65, 4.2, col, "", None], ["b", 1.0, -0.25, 1.0, 1.15, 0.5, 2.2, col, ""],
                           ["c", -0.6, 0, 4.17, 1.4, 0.06, "#3a2a20", "", None]]


def glass(dia, h):
    return dia, dia, h, [["c", 0, 0, 0, dia / 2 * 0.84, h, GLASS, "glass", dia / 2]]


def wine_glass():
    return 3.3, 3.3, 7.5, [["c", 0, 0, 0, 1.4, 0.15, GLASS, "glass", None], ["c", 0, 0, 0.15, 0.16, 3.2, GLASS, "glass", None],
                           ["c", 0, 0, 3.35, 0.6, 4.15, GLASS, "glass", 1.65]]


def bag(w, d, h, col, band=None):
    """A soft bag standing up: its body, a paler band, and the crimp across the top."""
    parts = [["b", -w / 2, -d / 2, 0, w, d, h * 0.9, col, "soft"], ["b", -w * 0.46, -d * 0.12, h * 0.9, w * 0.92, d * 0.24, h * 0.1, _shade(col, 0.8), "soft"]]
    if band:
        parts.append(["b", -w / 2 - 0.04, -d / 2 - 0.04, h * 0.3, w + 0.08, d + 0.08, h * 0.3, band, "soft"])
    return w, d, h, parts


def pan(dia, h, handle, col=IRON, mat="iron", inside=None):
    """A frying pan, its handle pointing to the back."""
    r, y0 = dia / 2, -handle / 2
    return dia, dia + handle, h, [["c", 0, y0, 0, r * 0.86, h, col, mat, r], ["c", 0, y0, h - 0.04, r * 0.9, 0.06, inside or _shade(col, 0.8), mat, None],
                                  ["b", -0.55, y0 + r - 0.3, h * 0.55, 1.1, handle + 0.3, 0.55, col if mat == "iron" else BLACK, mat if mat == "iron" else ""]]


def pot(dia, h, col=STEEL, mat="metal", ears=True, lid=None, handle=0.0, knob=BLACK):
    """A pot: two ear handles or one long one to the back, and a lid."""
    r, y0 = dia / 2, -handle / 2
    body = h - (1.1 if lid else 0)
    parts = [["c", 0, y0, 0, r, body, col, mat, None]]
    if ears:
        parts += [["b", -r - 1.3, y0 - 0.9, body * 0.72, 1.3, 1.8, 0.5, col, mat], ["b", r, y0 - 0.9, body * 0.72, 1.3, 1.8, 0.5, col, mat]]
    if handle:
        parts.append(["b", -0.5, y0 + r - 0.2, body * 0.7, 1.0, handle + 0.2, 0.6, BLACK, ""])
    if lid:
        parts += [["c", 0, y0, body, r + 0.1, 0.5, lid, "glass" if lid == GLASS else mat, r * 0.8], ["c", 0, y0, body + 0.5, 0.6, 0.6, knob, "", None]]
    return dia + (2.6 if ears else 0), dia + handle, h, parts


def tool(w, d, h, grip, head=None, mat=""):
    """A tool lying flat, its handle to the front: a narrow grip and a head as wide as the tool."""
    gw = min(w, 1.1)
    return w, d, h, [["b", -gw / 2, -d / 2, 0, gw, d * 0.58, min(h, 0.9), grip, ""], ["b", -w / 2, -d / 2 + d * 0.55, 0, w, d * 0.45, h, head or grip, mat]]


def spice(dia, h, col, lid, label=WHITE):
    r = dia / 2
    return dia, dia, h, [["c", 0, 0, 0, r, h - 0.6, col, "glass", None], ["c", 0, 0, h * 0.18, r + 0.04, h * 0.42, label, "paper", None],
                         ["c", 0, 0, h - 0.6, r + 0.05, 0.6, lid, "", None]]


def on_edge(t, long, short, col, mat="metal"):
    """A flat thing stood on its long edge between dividers: t across, its long side front to back."""
    return t, long, short, [["b", -t / 2, -long / 2, 0, t, long, short, col, mat]]


def stand_mixer():
    w, d, h = 9.0, 14.0, 14.0
    return w, d, h, [["b", -4.5, -7, 0, 9, 14, 1.6, WHITE, ""], ["b", -2.4, 2.2, 1.6, 4.8, 4.4, 8.6, WHITE, ""],
                     ["b", -3.2, -6.4, 9.6, 6.4, 13, 4.4, WHITE, ""], ["c", 0, -2.6, 1.6, 2.6, 5.4, STEEL, "metal", 3.9],
                     ["c", 0, -2.6, 7.0, 0.5, 2.6, STEEL, "metal", None]]


def food_processor():
    return 8.0, 10.5, 16.0, [["b", -4, -5.25, 0, 8, 10.5, 5.6, "#3a3d42", ""], ["c", 0, -0.6, 5.6, 3.5, 7.4, GLASS, "glass", 3.7],
                             ["c", 0, -0.6, 13.0, 3.8, 0.8, "#3a3d42", "", None], ["b", -1.3, -1.6, 13.8, 2.6, 3.4, 2.2, GLASS, "glass"],
                             ["c", 0, -0.6, 5.8, 0.5, 4.5, "#8a8d91", "metal", None]]


def blender():
    return 7.5, 8.0, 17.0, [["b", -3.75, -4, 0, 7.5, 8, 6.4, BLACK, ""], ["b", -2.2, -4.06, 1.6, 4.4, 0.1, 2.6, "#4a8fd6", ""],
                            ["c", 0, 0, 6.4, 2.5, 9.4, GLASS, "glass", 3.3], ["c", 0, 0, 15.8, 3.4, 1.2, BLACK, "", None]]


def instant_pot():
    return 13.4, 12.6, 12.5, [["c", 0, 0, 0, 6.1, 9.6, STEEL, "metal", None], ["c", 0, 0, 9.6, 6.3, 2.0, BLACK, "", 5.6],
                              ["c", 0, 0, 11.6, 1.2, 0.9, BLACK, "", None], ["b", -2.6, -6.3, 2.2, 5.2, 0.5, 5.0, BLACK, ""],
                              ["b", -6.7, -1.2, 8.2, 0.8, 2.4, 1.0, BLACK, ""], ["b", 5.9, -1.2, 8.2, 0.8, 2.4, 1.0, BLACK, ""]]


def toaster_oven():
    return 18.0, 14.0, 10.0, [["b", -9, -7, 0.6, 18, 14, 9.4, "#b9bcc0", "metal"], ["b", -8.2, -7.08, 1.8, 11.6, 0.12, 7.0, "#14161a", "glass"],
                              ["h", -2.4, -7.5, 8.2, 0.3, 10.6, "x", "#8a8d91", "metal"],
                              ["h", 6.2, -7.2, 7.4, 0.8, 0.5, "y", BLACK, ""], ["h", 6.2, -7.2, 5.0, 0.8, 0.5, "y", BLACK, ""], ["h", 6.2, -7.2, 2.6, 0.8, 0.5, "y", BLACK, ""],
                              ["b", -8.6, -6.6, 0, 1, 1, 0.6, BLACK, ""], ["b", 7.6, -6.6, 0, 1, 1, 0.6, BLACK, ""], ["b", -8.6, 5.6, 0, 1, 1, 0.6, BLACK, ""], ["b", 7.6, 5.6, 0, 1, 1, 0.6, BLACK, ""]]


def espresso_machine():
    return 9.5, 17.0, 14.0, [["b", -4.75, -4.5, 0, 9.5, 13, 14, "#1d1d1f", ""], ["b", -4.75, -8.5, 0, 9.5, 4, 1.6, "#1d1d1f", ""],
                             ["b", -4.3, -8.3, 1.6, 8.6, 3.6, 0.2, STEEL, "metal"], ["b", -1.6, -6.2, 6.2, 3.2, 1.8, 2.6, "#2a2b2e", ""],
                             ["b", -3.8, -4.56, 10.2, 7.6, 0.1, 2.6, "#3a3d42", ""], ["c", 0, 3, 14, 2.6, 0.5, "#3a3d42", "", None],
                             ["c", 0, -6.4, 1.8, 1.3, 2.4, WHITE, "", 1.5]]


def compost_bin():
    return 9.0, 6.0, 9.0, [["b", -4.5, -3, 0, 9, 6, 7.6, "#c4c6c8", "metal"], ["b", -4.6, -3.1, 7.6, 9.2, 6.2, 0.9, "#b4b7ba", "metal"],
                           ["h", 0, 0, 8.8, 0.18, 6.0, "x", "#8a8d91", "metal"], ["b", -3.1, -0.15, 8.5, 0.3, 0.3, 0.5, "#8a8d91", "metal"], ["b", 2.8, -0.15, 8.5, 0.3, 0.3, 0.5, "#8a8d91", "metal"]]


def crock():
    parts = [["c", 0, 0, 0, 2.6, 7.0, "#b9bcc0", "metal", None]]
    for i, (x, y, top, col, mat, head) in enumerate(((-1.2, 0.6, 13.0, WOOD, "wood", "s"), (1.1, 0.9, 12.4, STEEL, "metal", "s"),
                                                      (0.2, -1.2, 12.8, BLACK, "", "b"), (1.4, -0.6, 11.6, WOOD, "wood", "b"),
                                                      (-1.3, -0.8, 12.0, STEEL, "metal", "s"))):
        parts.append(["c", x, y, 1.0, 0.28, top - 2.4, col, mat, None])
        parts.append(["s", x, y, top - 0.9, 1.0, col, mat] if head == "s" else ["b", x - 0.9, y - 0.2, top - 2.6, 1.8, 0.4, 2.6, col, mat])
    return 5.2, 5.2, 13.0, parts


def paper_towels():
    return 6.0, 6.0, 13.0, [["c", 0, 0, 0, 3.0, 0.4, STEEL, "metal", None], ["c", 0, 0, 0.4, 0.3, 12.6, STEEL, "metal", None],
                            ["c", 0, 0, 0.6, 2.7, 11.0, "#fbfaf6", "paper", None]]


def soap_and_sponge():
    return 6.6, 3.0, 7.6, [["c", -1.9, 0, 0, 1.2, 6.0, STEEL, "metal", None], ["c", -1.9, 0, 6.0, 0.25, 1.2, STEEL, "metal", None],
                           ["b", -2.1, -1.6, 7.0, 0.4, 1.8, 0.35, STEEL, "metal"], ["b", 0.2, -1.3, 0, 3.0, 2.6, 0.7, "#8a8d91", "metal"],
                           ["b", 0.4, -1.1, 0.7, 2.6, 2.2, 1.0, "#e9c93a", "soft"]]


def cutlery_tray():
    """The bamboo organiser: forks, spoons and knives in lanes, the small knives across the back."""
    w, d = 14.5, 17.0
    parts = [["b", -w / 2, -d / 2, 0, w, d, 0.35, "#d9b67c", "wood"]]
    for x in (-w / 2, w / 2 - 0.35):
        parts.append(["b", x, -d / 2, 0.35, 0.35, d, 1.85, "#d9b67c", "wood"])
    for y in (-d / 2, d / 2 - 0.35, 2.6):
        parts.append(["b", -w / 2, y, 0.35, w, 0.35, 1.85, "#d9b67c", "wood"])
    lanes = [-w / 2 + (i + 1) * (w / 5) for i in range(4)]
    for x in lanes:
        parts.append(["b", x - 0.15, -d / 2, 0.35, 0.3, d / 2 + 2.6, 1.6, "#d9b67c", "wood"])
    for i in range(5):
        parts.append(["b", -w / 2 + i * (w / 5) + 0.75, -d / 2 + 1.2, 0.4, w / 5 - 1.5, 8.4, 0.7, "#cfd1d3", "metal"])
    parts.append(["b", -w / 2 + 1.2, 3.6, 0.4, w - 2.4, 4.0, 0.6, "#b9bcc0", "metal"])
    return w, d, 2.2, parts


# ----------------------------------------------------------------------------
# The things. `add` records one row; qty > 1 with several shapes gives one of each.
# ----------------------------------------------------------------------------
THINGS: list[dict] = []
P = {k: "20261113-" + k for k in ("151935", "151940", "151942", "152008", "152012", "152017", "152021",
                                   "152025", "152029", "152034", "152049", "152110", "152142")}


# words in a note that say the thing itself is in doubt (the page marks those)
_UNSURE = ("not legible", "not identified", "not visible", "not seen clearly", "not found", "a guess", "probably", "partly hidden", "foil pans or steel plates", "are guesses")


def add(id, label, group, shapes, seen, note="", qty=None):
    """One kind of thing. `shapes` is one shape, or a list: one thing each."""
    if isinstance(shapes, tuple):
        shapes = [shapes] * (qty or 1)
    for i, (w, d, h, parts) in enumerate(shapes):
        THINGS.append({"id": id if len(shapes) == 1 else f"{id}{i + 1}", "kind": id, "label": label, "group": group,
                       "w": round(w, 2), "d": round(d, 2), "h": round(h, 2), "parts": parts,
                       "seen": [P.get(s, s) for s in seen.split()], "note": note,
                       "unsure": "likely" in seen or any(k in note for k in _UNSURE)})


# --- dishes -----------------------------------------------------------------
add("plates_dinner", "Dinner plates, 12", "plates", stack(10.5, 5.4, WHITE), "151935 151940", "two of them were in the sink")
add("plates_dark", "Dark dinner plates, 6", "plates", stack(10.0, 2.8, "#5a5f66"), "151935")
add("plates_salad", "Salad plates, 8", "plates", stack(8.0, 3.2, "#f1efe8"), "151935")
add("bowls_pasta", "Shallow pasta bowls, 6", "plates", stack(9.5, 4.0, "#ecebe6"), "151935")
add("bowls_cereal", "Cereal bowls, 6", "plates", bowls(6.5, 5.6, "#f6f5f0"), "151935 151940", "four more were in the sink", qty=2)
add("bowls_small", "Small bowls, 6", "plates", bowls(4.8, 3.6, "#f6f5f0"), "151935")
add("plates_square", "Square side plates, 4", "plates", box(6.0, 6.0, 2.0, WHITE), "151935")
add("glass_pint", "Pint glass", "glasses", glass(3.3, 5.8), "151940", qty=10)
add("glass_small", "Small glass", "glasses", glass(2.8, 4.0), "151940 152110", qty=6)
add("mug", "Mug", "glasses", [mug(c) for c in (WHITE, "#e5823a", "#2f5fa8", "#f2c230", "#f6f5f0", "#7a8fa3", "#c94f3a", "#3f7d5a")], "151940")
add("glass_wine", "Stemmed glass", "serving", wine_glass(), "152110", "a snifter and stemware behind the glass door; the count is a guess", qty=4)
add("bowl_serving", "Serving bowls, 2 nested", "serving", bowls(9.5, 5.0, WHITE), "151935")
add("bowl_terracotta", "Terracotta bowl", "serving", bowls(7.0, 5.5, "#b0643c", inside="#8a4a2c"), "151935")
add("mason_quart", "Mason jar, quart", "serving", can(3.7, 6.9, GLASS, "glass", lid="#b9bcc0"), "151940 152110", qty=5)
add("mason_pint", "Mason jar, pint", "serving", can(3.2, 5.2, GLASS, "glass", lid="#b9bcc0"), "151940", qty=3)
add("pitcher", "Plastic pitcher", "serving", can(5.5, 8.8, "#b9bcc0"), "152110")
add("foil_pans", "Foil pans, a stack", "serving", stack(9.5, 5.0, "#c9cbcd", "metal"), "151935", "a ridged silver stack over the hood: foil pans or steel plates")
add("napkins", "Paper napkins", "serving", box(6.5, 6.5, 3.0, "#fbfaf6", "paper"), "151935")
add("kid_plates", "Children's plates, 6", "kids", stack(8.0, 2.0, "#4fb3bf"), "likely", "not visible; the straws and small cutlery in the silverware drawer say there are some")
add("kid_bowls", "Children's bowls, 6", "kids", bowls(5.5, 3.6, "#f2b84b"), "likely", "not visible")
add("kid_cup", "Children's cup", "kids", [can(3.0, 4.3, c) for c in ("#e2574c", "#4fb3bf", "#f2b84b", "#7a6ad0", "#57b36a", "#e98ab5")], "likely", "not visible")
add("straws", "Reusable straws and their brushes", "kids", box(3.0, 9.5, 1.5, "#bfe3d6", "soft"), "152017")
add("kid_cutlery", "Children's forks and spoons", "kids", box(4.0, 7.0, 1.0, "#f08fc0", ""), "152017")
add("water_bottle", "Water bottle", "bottles", [can(3.0, 9.5, c, lid=l, lid_h=1.6) for c, l in (("#2f6fb8", "#1b1c1e"), ("#cfe3ef", "#2f6fb8"), ("#2a2b2e", "#2a2b2e"), ("#57b36a", "#1b1c1e"), ("#e98ab5", "#f4f2ec"), ("#cfd1d3", "#1b1c1e"))], "151935")
add("tumbler", "Insulated tumbler", "bottles", can(3.5, 8.0, STEEL, "metal", lid="#2a2b2e"), "151935", qty=3)
add("thermos", "Thermos", "bottles", can(3.2, 10.0, "#b3202c", lid="#1b1c1e", lid_h=1.4), "151935")
add("lunch_bag", "Lunch bag", "bottles", box(10.0, 7.0, 8.0, "#1d1d1f", "soft"), "151940")
add("cutlery_tray", "Forks, spoons and knives in the bamboo organiser", "silverware", cutlery_tray(), "152017")
add("soup_spoons", "Ceramic soup spoons, 10", "silverware", box(4.5, 9.0, 1.8, "#fbfaf6"), "152017")
add("chopsticks", "Chopsticks and steak knives", "silverware", box(3.5, 10.0, 1.2, "#d9b67c", "wood", band="#8a8d91"), "152017")

# --- pots and pans ----------------------------------------------------------
add("stock_pot", "Large stock pot", "pots", pot(11.0, 11.5, lid=STEEL), "named 152008", "the big steel pot at the bottom right of the pot cabinet")
add("dutch_oven", "Dutch oven, blue enamel", "pots", pot(10.5, 7.0, "#1f3f8a", "", lid="#1f3f8a", knob=STEEL), "152029")
add("saucepan_3qt", "Saucepan, 3 quart", "pots", pot(8.0, 5.5, ears=False, lid=GLASS, handle=7.0), "152008 151940", "one was in the sink")
add("saucepan_2qt", "Saucepan, 2 quart", "pots", pot(7.0, 5.0, ears=False, lid=GLASS, handle=6.5), "152008")
add("saucepan_1qt", "Saucepan, 1 quart", "pots", pot(6.0, 4.2, ears=False, lid=GLASS, handle=6.0), "152008")
add("lids", "Spare lids, 4", "pots", stack(11.0, 2.6, GLASS, "glass"), "152008")
add("skillets_iron", "Cast-iron skillets, 12 and 10 in, and the crepe pan, nested", "pans", pan(12.5, 4.2, 5.5), "152142")
add("fry_pans", "Frying pans, 2 nested", "pans", pan(11.0, 3.0, 8.0, "#3a3d42", "metal", inside="#2a2b2e"), "152008")
add("wok", "Wok with its glass lid", "pans", pan(14.0, 5.0, 6.0, "#3b2f2a", "iron"), "152029 152021")
add("casseroles", "White casserole dishes, 2 nested", "ovenware", box(12.0, 9.0, 5.5, WHITE, lid=GLASS), "152029 152021")
add("pyrex_9x13", "Glass baking dishes, 9 x 13, 2", "ovenware", box(15.0, 9.5, 4.0, GLASS, "glass"), "152021")
add("pyrex_8x8", "Glass baking dish, 8 x 8", "ovenware", box(9.0, 9.0, 2.5, GLASS, "glass"), "152021")
add("loaf_pans", "Loaf pans, 2 nested", "ovenware", box(9.5, 5.5, 3.2, "#8a8d91", "metal"), "152021")
add("sheet_half", "Half sheet pan", "sheets", on_edge(1.1, 18.0, 13.0, "#c4c6c8"), "152021 151935", qty=3)
add("sheet_quarter", "Quarter sheet pan", "sheets", on_edge(1.1, 13.0, 9.5, "#c4c6c8"), "152021", qty=2)
add("rack", "Cooling rack", "sheets", on_edge(0.7, 17.0, 12.0, "#a9acb0"), "152021", qty=2)
add("pizza_pan", "Pizza pan", "sheets", on_edge(0.8, 14.0, 14.0, "#d9d3c3"), "152021")
add("muffin_tin", "Muffin tin", "sheets", on_edge(1.6, 14.0, 10.5, "#5a5d62"), "152021", "one of the dark tins in the stack; not seen clearly")
add("bowls_glass", "Glass mixing bowls nested in the green and red ones", "bowls", bowls(12.0, 6.5, "#b9cf8a", inside=GLASS), "152012")
add("bowls_steel", "Steel mixing bowls, nested", "bowls", bowls(10.5, 5.0, STEEL, "metal"), "152012")
add("strainers", "Strainers and colander, nested", "bowls", bowls(9.0, 4.5, "#a9acb0", "metal", inside="#6f9fd0"), "152012")
add("grater", "Box grater", "bowls", box(4.0, 3.2, 7.2, "#e9e9e6", "metal"), "151935")

# --- appliances -------------------------------------------------------------
add("stand_mixer", "KitchenAid stand mixer", "appl_prep", stand_mixer(), "152008")
add("food_processor", "Food processor", "appl_prep", food_processor(), "named 152008", "the clear bowl with blades at the left of the appliance cabinet")
add("blender", "Ninja blender", "appl_prep", blender(), "named 152008", "the tall pitcher at the back of the appliance cabinet")
add("instant_pot", "Instant Pot", "appl_cook", instant_pot(), "named 152008")
add("waffle_iron", "Black countertop appliance", "appl_cook", box(10.0, 9.0, 5.0, "#1d1d1f", ""), "152021", "a waffle iron or a grill; not identified")
add("spinner", "Round white tub with a lid", "appl_cook", can(10.0, 8.0, "#eeeeea", lid="#dcdcd8", lid_h=1.5), "151935", "a salad spinner or a rice cooker, on the top shelf at the far left; not identified")
add("toaster_oven", "Toaster oven", "toaster_oven", toaster_oven(), "named 151935")
add("espresso_machine", "DeLonghi espresso machine", "espresso", espresso_machine(), "151940")

# --- the everything drawer --------------------------------------------------
# One drawer holds all of these today, lying on each other. Things that lie together are one row here.
add("rolling_pin", "Rolling pin", "tools", box(2.0, 18.0, 2.0, "#d9b67c", "wood"), "152025")
add("whisk", "Whisk", "tools", tool(2.6, 11.0, 2.6, STEEL, "#dcdee0", "metal"), "152025")
add("masher", "Potato masher", "tools", tool(3.5, 11.0, 2.6, WHITE, STEEL, "metal"), "152025")
add("turners", "Steel turner and fish spatula", "tools", tool(3.5, 13.0, 1.6, BLACK, STEEL, "metal"), "152025")
add("tongs", "Tongs and bamboo skewers", "tools", box(2.0, 12.0, 2.0, STEEL, "metal"), "152025")
add("spatula", "Silicone spatula, basting brush and rice paddle", "tools", tool(3.0, 11.0, 2.2, STEEL, "#c8302c"), "152025")
add("scraper", "Bench scraper and pizza cutter", "tools", tool(4.5, 9.0, 1.9, BLACK, STEEL, "metal"), "152025")
add("mallet", "Meat mallet", "tools", tool(2.6, 9.5, 2.0, STEEL, "#b9bcc0", "metal"), "152025")
add("claws", "Meat claws, folding funnels and icing nozzles", "tools", box(4.5, 7.0, 2.6, "#e8622c"), "152025")
add("salad_hands", "Wooden salad hands, a pair", "tools", box(3.5, 7.0, 2.0, "#d9b67c", "wood"), "152025")
add("squeezer", "Lemon squeezer", "tools", tool(3.0, 9.0, 2.0, "#f2c230", "#f2c230"), "152025")
add("can_opener", "Can opener and ice cream scoop", "tools", tool(4.0, 7.5, 1.8, BLACK, STEEL, "metal"), "152025")
add("measures", "Measuring cups and spoons, peeler, corkscrew and tea infuser", "tools", tool(3.4, 8.0, 2.6, STEEL, STEEL, "metal"), "152025")
add("crock", "Utensil crock: ladles, spoons and spatulas", "crock", crock(), "151935 151940")
add("mitts", "Oven mitts, a pair", "mitts", box(9.0, 7.0, 3.0, "#e8622c", "soft"), "151935")
add("pot_holders", "Pot holders", "mitts", box(7.0, 7.0, 1.5, "#c8302c", "soft"), "151935")
add("dish_towels", "Dish towels", "mitts", box(9.0, 7.0, 3.0, "#d9a13a", "soft", band="#3f8f6c"), "151935")
add("boards", "Cutting boards, 3", "boards", box(18.0, 13.0, 1.6, "#c9805a", "wood", band=None), "152034 151935")
add("brisket_knife", "Brisket knife in a guard", "boards", tool(2.0, 19.0, 0.8, BLACK, "#3a3d42"), "named", "not found in the photographs; 14 in of blade is longer than the 10 in between the knife strip and the counter, so it lies in a drawer")

# --- food storage -----------------------------------------------------------
add("foil_heavy", "Heavy-duty foil, 18 in", "wraps", box(18.5, 3.0, 3.0, "#1f3f9a", "paper"), "152034")
add("foil", "Foil, 12 in", "wraps", box(12.5, 2.6, 2.6, "#2f5fb8", "paper"), "152034")
add("cling", "Cling film", "wraps", box(12.2, 2.6, 2.6, "#f2c230", "paper"), "152034")
add("parchment", "Parchment paper", "wraps", box(15.0, 2.6, 2.6, "#e9df4a", "paper"), "152049")
add("jar_lids", "Jar lids and rings", "wraps", box(6.0, 6.0, 2.6, "#b9bcc0", "metal"), "152034")
add("zip_bags", "Zip-top bags", "wraps", box(7.5, 6.5, 3.0, "#2f6fb8", "paper"), "likely", "not visible; freezer bags are in use in the snack cabinet", qty=2)
add("deli_tubs", "Deli containers, nested", "containers", can(4.7, 9.0, "#e9eef0", "glass"), "152029 152021", qty=2)
add("deli_lids", "Deli container lids", "containers", can(4.8, 4.0, "#f4f2ec"), "152029")
add("glass_tubs", "Round containers with red lids, nested", "containers", can(7.0, 6.0, "#b3202c"), "152029 152021")
add("bento", "Divided lunch containers, 4", "containers", box(9.0, 7.0, 6.0, "#d9d3c3", lid="#e2a52a"), "152029")
add("tub_green", "Glass container, green lid", "containers", box(8.0, 6.0, 3.0, GLASS, "glass", lid="#7fb069"), "152029")

# --- spices and what is used at the range -----------------------------------
_SPICE_BIG = (("#3b3530", "#1b1c1e"), ("#5a4a3a", "#1b1c1e"), ("#6f7a45", "#1b1c1e"), ("#d8cba8", "#2f6b3a"), ("#6b7f4a", "#1b1c1e"), ("#b23a1e", "#8a8d91"),
              ("#a8321c", "#b3202c"), ("#8a3a22", "#1b1c1e"), ("#a87a3a", "#1b1c1e"), ("#d9c9a0", "#1b1c1e"), ("#8a5a34", "#1b1c1e"), ("#d9a21e", "#1b1c1e"))
add("spice_big", "Large spice jar", "spices", [spice(2.7, 7.4, c, l) for c, l in _SPICE_BIG], "151935 151940 152110",
    "black pepper, garlic salt, paprika, crushed red pepper, chili powder and cinnamon could be read; the rest are guesses at the colour")
_SPICE_SMALL = ("#c9a24a", "#7a8a3a", "#b0472a", "#3b3530", "#d9d0b8", "#8a6a3a", "#a8321c", "#6f7a45", "#e0b83a", "#5a3a2a", "#c8b48a", "#9a5a2a", "#d8cba8", "#7a2a1e")
add("spice_small", "Small spice jar", "spices", [spice(2.1, 4.4, c, "#b3202c" if i % 3 == 0 else "#1b1c1e") for i, c in enumerate(_SPICE_SMALL)], "151940 152110", "ginger and seasoned salt could be read")
add("spice_tin", "Spice tin", "spices", [box(3.0, 2.0, 3.6, "#f4f2ec"), can(2.9, 5.0, "#f2c230", label="#c8302c"), box(2.2, 2.2, 3.6, "#1b1c1e")], "151940 152110", "a white tin, Slap Ya Mama and a mustard tin")
add("spice_bag", "Spice bag", "spices", [bag(5.0, 2.0, 6.0, c) for c in ("#3f6f4a", "#2a2b2e", "#8a8d91")], "151940")
add("worcestershire", "Worcestershire sauce", "spices", bottle(2.4, 8.3, "#3a241a", "#d9c7a0", "#e9d9a8"), "151940 152110")
add("salt", "Salt canister", "spices", can(3.3, 5.4, "#1f3f8a", label="#f4f2ec"), "151935")
add("white_tub", "Large white tub", "spices", can(4.5, 6.5, "#f1efe8"), "151940", "at the left of the top spice shelf: salt or sugar; not legible")
add("avocado_oil", "Avocado oil", "oils", bottle(3.0, 10.5, "#3f4a22", "#1b1c1e", "#f1efe8"), "152049")
add("olive_oil", "Dark bottle: olive oil or wine", "oils", bottle(3.0, 11.5, "#2a2f1e", "#1b1c1e"), "151935", "beside the squeeze bottles; not legible")
add("squeeze_bottle", "Squeeze bottle", "oils", [can(2.5, 8.5, c, "glass", lid="#f4f2ec", lid_h=1.4) for c in ("#e9dfb0", "#e2c86a", "#f1efe8", "#d9b23a")], "151935")
add("agave", "Agave syrup", "oils", bottle(2.8, 7.5, "#c98a2a", "#1b1c1e", "#f4f2ec"), "151940")

# --- ingredients ------------------------------------------------------------
add("coffee_beans", "Coffee beans", "coffee", bag(6.0, 3.5, 9.0, "#1f3f8a"), "152110", qty=2)
add("tea_box", "Tetley tea, a large box", "coffee", box(7.5, 4.5, 5.0, "#6a3fa0", "paper"), "151935")
add("tea_tin", "Tea tin", "coffee", box(3.0, 3.0, 4.0, "#1b1c1e"), "151935", qty=2)
add("flour_bag", "Flour, 5 lb bag", "baking", bag(5.5, 3.5, 8.5, "#f1efe8", "#c8302c"), "152049", qty=2)
add("flour_tub", "Flour in a clear tub", "baking", box(8.0, 8.0, 7.0, "#eef2f2", "glass", lid="#8a8d91"), "152049")
add("sugar", "Sugar, 4 lb bag", "baking", bag(6.0, 3.5, 7.5, "#fbfaf6", "#e98ab5"), "152049")
add("brown_sugar", "Organic brown sugar", "baking", bag(5.0, 3.0, 7.0, "#b08a5a"), "152049")
add("baking_soda", "Baking soda", "baking", box(3.0, 1.7, 4.6, "#f2a21e", "paper"), "152049")
add("baking_powder", "White canister: baking powder or the like", "baking", can(3.0, 4.8, "#f4f2ec", label="#cfd8ea"), "152049", "label not legible")
add("corn_starch", "Corn starch", "baking", can(3.6, 6.6, "#f2c230", label="#1f3f8a", lid="#1f3f8a"), "152049")
add("cocoa", "Black bag: cocoa or a baking mix", "baking", bag(6.0, 3.0, 8.0, "#1d1d1f"), "152049", "label partly hidden")
add("yeast", "Active dry yeast", "baking", bag(5.0, 2.5, 7.0, "#f4f2ec", "#c8302c"), "152049")
add("vanilla", "Vanilla extract", "baking", bottle(2.8, 7.5, "#5a3a1e", "#1b1c1e", "#f1efe8"), "152049")
add("sprinkles", "Sprinkles", "baking", [can(2.5, 5.6, "#bfe3c8", "glass", label="#f08fc0", lid="#f4f2ec"), can(2.3, 4.6, "#f6b8cf", "glass", lid="#e9559a")], "152049")
add("food_colour", "Food colouring", "baking", box(3.0, 1.0, 3.2, "#1b1c1e", "paper"), "152049")
add("cupcake_liners", "Cupcake liners", "baking", can(3.2, 3.0, "#7fd0c8"), "152049")
add("frosting", "White tub with a black lid", "baking", can(3.6, 4.6, "#f4f2ec", lid="#1b1c1e"), "152049", "frosting or salt; not legible")
add("syrup_bottle", "Bottle at the back of the carousel", "baking", bottle(2.6, 8.0, "#3a2a1e", "#1b1c1e"), "152049", "molasses, syrup or vinegar; not legible", qty=2)
add("oats", "Oats canister", "baking", can(5.0, 9.5, "#f1e6d0", label="#c98a5a", lid="#f4f2ec"), "152049")
add("beans_bag", "Dried beans", "drygoods", [bag(7.0, 2.5, 9.0, c) for c in ("#2a2224", "#7a2a2a", "#e9e0c8")], "152110")
add("barley", "Barley", "drygoods", box(4.0, 2.0, 6.5, "#1f3f8a", "paper"), "152110")
add("pasta", "Pasta", "drygoods", [bag(6.0, 2.5, 9.0, "#d9b85a", "#57b36a"), bag(7.0, 2.0, 8.0, "#e9e6dc")], "152110")
add("broth", "Carton: broth or the like", "drygoods", [box(3.8, 2.5, 6.5, "#c8302c", "paper", band="#f4f2ec"), box(3.8, 2.5, 6.5, "#f4f2ec", "paper", band="#2f6fb8")], "152110", "labels not legible")
add("can", "Can", "drygoods", [can(3.0, 4.4, "#b9bcc0", "metal", label=c) for c in ("#2f6b3a", "#f4f2ec", "#f2c230", "#c8302c", "#2f6fb8")], "152110")
add("mayo", "Mayonnaise", "drygoods", box(3.5, 2.6, 8.2, "#f6f1d8", band="#2f6fb8"), "152110")
add("chickpeas", "Jar of white beans", "drygoods", can(4.0, 7.0, "#e9e0c8", "glass", lid="#c8302c"), "152110")
add("bouillon", "Bouillon, a large jar", "drygoods", can(4.2, 5.0, "#7a4a2a", "glass", label="#1d3a2a", lid="#b9bcc0"), "152110")
add("peanut_butter", "Peanut butter", "drygoods", can(4.3, 7.2, "#b9803a", "glass", label="#c8302c", lid="#2f6fb8"), "151940 151942")
add("lentils", "Clear bag of grain", "drygoods", bag(6.0, 3.0, 8.0, "#d9c9a0"), "151942", "lentils or quinoa; not legible")
add("drink_mix", "Gatorade powder", "drygoods", can(5.5, 8.5, "#f4f2ec", label="#e8622c", lid="#e8622c"), "152049")
add("deli_food", "Deli tub with food in it", "drygoods", can(4.7, 5.6, "#e9eef0", "glass", lid="#f4f2ec"), "152110")
add("oil_jug", "Vegetable oil, a gallon", "bulk", box(6.0, 6.0, 12.0, "#e2c84a", "glass", lid="#2f6fb8"), "152049")
add("rice_bag", "Large clear bag of rice or oats", "bulk", bag(9.0, 5.0, 12.0, "#e9e0c8"), "151940 151942", "it was on the counter")

# --- snacks -----------------------------------------------------------------
add("chips", "Bag of chips", "snacks", [bag(9.0, 4.0, 11.0, c) for c in ("#c8102e", "#f28a1e", "#2f6fb8")], "151940 151942")
add("tortilla_chips", "Tortilla chips, a large bag", "snacks", bag(10.0, 4.5, 12.0, "#b9803a"), "151942")
add("chip_packs", "Small chip bags, a dozen", "snacks", box(12.0, 8.0, 6.0, "#f2c230", "soft", band="#c8102e"), "151942")
add("fruit_cups", "Fruit cups, a box of 12", "snacks", box(10.0, 7.0, 3.3, "#2f8fd0", "paper", band="#f28a1e"), "151942", qty=2)
add("crackers", "Crackers", "snacks", box(5.5, 2.5, 8.5, "#e2742a", "paper"), "151942")
add("pancake_mix", "Yellow box: cereal or pancake mix", "snacks", box(7.5, 2.6, 10.0, "#e9c93a", "paper"), "151942", "not legible")
add("bars", "Box of bars", "snacks", box(7.0, 2.5, 6.0, "#7fb8e0", "paper", band="#f2c230"), "151942")
add("nuts", "Kirkland nuts, a tin", "snacks", can(5.6, 6.2, "#f4f2ec", label="#c9a24a", lid="#c9a24a"), "151942")
add("trail_mix", "Trail mix", "snacks", bag(6.0, 3.0, 8.0, "#8a6a4a"), "151942", qty=2)
add("marshmallows", "Mini marshmallows", "snacks", bag(7.0, 3.0, 6.0, "#fbfaf6", "#2f6fb8"), "151942")
add("dried_fruit", "Freezer bags of dried fruit", "snacks", bag(8.0, 3.0, 7.0, "#d0d8dc", "#c8302c"), "151942")
add("pretzels", "Blue and white box", "snacks", box(9.0, 3.0, 6.0, "#f4f2ec", "paper", band="#1f3f8a"), "151942", "Bavarian something: pretzels, probably")
add("popcorn", "Popcorn kernels", "snacks", bag(5.0, 2.5, 8.0, "#f2c230"), "151942")
add("bread", "Loaf of bread", "snacks", box(11.0, 4.5, 4.5, "#2f6fb8", "soft"), "151942")
add("candy_bucket", "Halloween candy bucket", "snacks", can(7.0, 6.5, "#c8102e"), "151940 151942", "it was on the counter")

# --- drinks, medicine, household ---------------------------------------------
_LIQUOR = (("#e9e4d2", "#1b1c1e"), ("#3a2a1a", "#c9a24a"), ("#2f5a3a", "#f4f2ec"), ("#dfeef6", "#c8302c"), ("#5a3a1e", "#1b1c1e"), ("#dfeef6", "#1f3f8a"),
           ("#7a4a1e", "#f4f2ec"), ("#2a2b2e", "#c9a24a"), ("#dfeef6", "#f4f2ec"), ("#8a5a2a", "#1b1c1e"))
add("liquor", "Bottle of liquor", "bar", [bottle(3.2, 12.0, c, "#1b1c1e", l) for c, l in _LIQUOR], "151935", "Bacardi and a green gin bottle could be read")
add("wine", "Bottle of wine", "bar", bottle(3.0, 12.0, "#1e2a1e", "#7a1e2b", "#f1efe8"), "151935", qty=2)
add("bitters", "Small bottle: bitters", "bar", bottle(2.0, 5.0, "#5a2a1e", "#f2c230", "#f1efe8"), "151935", qty=2)
add("bar_books", "Cocktail and recipe books, 3", "bar", box(3.0, 7.0, 9.0, "#1f3f8a", "paper", band="#f2c230"), "151935")
add("vitamins", "Vitamin bottle", "medicine", [can(2.3, 4.5, c, lid="#f4f2ec", label=l) for c, l in (("#f4f2ec", "#e2574c"), ("#7a4a2a", "#f2c230"), ("#f4f2ec", "#2f6fb8"), ("#2f6b3a", "#f4f2ec"), ("#f2a21e", "#f4f2ec"))], "151935")
add("med_box", "Medicine box", "medicine", [box(4.0, 1.6, 2.6, c, "paper") for c in ("#f4f2ec", "#e9559a", "#7fb8e0", "#f4f2ec")], "151935")
add("sunscreen", "Sunscreen", "medicine", [box(2.6, 1.6, 7.0, c) for c in ("#f28a1e", "#f4f2ec", "#2f6fb8")], "151935")
add("rubbing_alcohol", "Rubbing alcohol or peroxide", "medicine", can(2.8, 8.0, "#e9eef0", "glass", label="#f4f2ec", lid="#f4f2ec"), "151935")
add("first_aid", "Box of bandages", "medicine", box(6.0, 4.0, 3.0, "#f4f2ec", "paper", band="#c8302c"), "151935")
add("cables_bin", "Bin of chargers and cables", "household", box(7.0, 5.0, 3.0, "#cfd8dc", "glass"), "151935")
add("chargers", "Loose chargers and cords", "household", box(8.0, 6.0, 2.6, "#2a2b2e", "soft"), "151935")
add("box_72", "Box marked 72", "household", box(7.0, 5.0, 3.0, "#1b1c1e", "paper", band="#f4f2ec"), "151935", "in the liquor cabinet; not legible")

# --- cleaning ---------------------------------------------------------------
add("spray", "Spray cleaner", "cleaning", [box(4.0, 2.5, 11.0, c, band=b) for c, b in (("#c8302c", "#2f6fb8"), ("#f4f2ec", None), ("#f4f2ec", "#2f6fb8"))], "152029 151935", "one stood in the cabinet over the hood")
add("goo_gone", "Goo Gone", "cleaning", box(2.5, 1.5, 7.5, "#f2c230"), "152029")
add("dish_soap", "Dish soap, a refill", "cleaning", bottle(3.0, 10.5, "#2f6fd0", "#f4f2ec", mat=""), "152029")
add("dw_tabs", "Dishwasher tablets, a tub", "cleaning", box(9.0, 7.0, 8.0, "#f4f2ec", lid="#2f6fb8"), "152029")
add("jug", "White jug with a green cap", "cleaning", can(4.5, 9.5, "#f4f2ec", lid="#2f8a4a", lid_h=1.0), "151935", "over the hood, beside the spray bottle: a cleaner or vinegar; not legible. Kept with the cleaners")
add("aerosol", "Black aerosol can", "cleaning", can(2.6, 9.5, "#1b1c1e", "metal", lid="#c8302c"), "151935", "over the hood: a polish, or cooking spray; not legible. Kept with the cleaners")
add("paper_roll", "Paper towels, a spare roll", "bags", can(5.6, 11.0, "#fbfaf6", "paper"), "152029")
add("rag_bag", "Cloth bag of bags and rags", "bags", box(9.0, 7.0, 12.0, "#d9d3c3", "soft"), "152029")
add("bin_bags", "Compost and bin bags", "bags", box(8.0, 4.0, 5.0, "#57b36a", "paper"), "likely", "not visible; the compost bin is lined")
add("shopping_bags", "Reusable shopping bags, folded", "bags", box(13.0, 5.0, 10.0, "#2a63b8", "soft"), "151940 151942", "three stood on the counter")
add("soap_sponge", "Dish soap pump and sponge", "soap", soap_and_sponge(), "151940")
add("paper_towels", "Paper towels on their holder", "towels", paper_towels(), "151940")
add("compost_bin", "Compost bin", "compost", compost_bin(), "named 152142", "on the counter beside the range today")


def summary():
    """{category: {group label: [(thing label, count)]}}, for a person to read."""
    out: dict = {}
    for t in THINGS:
        g = GROUPS[t["group"]]
        rows = out.setdefault(g["cat"], {}).setdefault(g["label"], {})
        rows[t["label"]] = rows.get(t["label"], 0) + 1
    return out


if __name__ == "__main__":
    for cat in CATEGORIES:
        print(cat.upper())
        for group, rows in summary().get(cat, {}).items():
            print("  " + group + ": " + "; ".join(f"{label}" + (f" x{n}" if n > 1 else "") for label, n in rows.items()))
    print(len(THINGS), "things in", len(GROUPS), "kinds")
