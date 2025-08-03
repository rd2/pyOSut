# BSD 3-Clause License
#
# Copyright (c) 2022-2025, rd2
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re
import math
import collections
import openstudio
from oslg import oslg
from dataclasses import dataclass

@dataclass(frozen=True)
class _CN:
    DBG  = oslg.CN.DEBUG
    INF  = oslg.CN.INFO
    WRN  = oslg.CN.WARN
    ERR  = oslg.CN.ERROR
    FTL  = oslg.CN.FATAL
    TOL  = 0.01      # default distance tolerance (m)
    TOL2 = TOL * TOL # default area tolerance (m2)
    HEAD = 2.032     # standard 80" door
    SILL = 0.762     # standard 30" window sill
CN = _CN()

# General surface orientations (see 'facets' method).
_sidz = ("bottom", "top", "north", "east", "south", "west")

# This first set of utilities support OpenStudio materials, constructions,
# construction sets, etc. If relying on default StandardOpaqueMaterial:
#   - roughness            (rgh) : "Smooth"
#   - thickness                  :    0.1 m
#   - thermal conductivity (k  ) :    0.1 W/m.K
#   - density              (rho) :    0.1 kg/m3
#   - specific heat        (cp ) : 1400.0 J/kg•K
#
#   https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/
#   OpenStudio-3.6.1-doc/model/html/
#   classopenstudio_1_1model_1_1_standard_opaque_material.html

# ... apart from surface roughness, rarely would these material properties be
# suitable - and are therefore explicitly set below. On roughness:
#   - "Very Rough"    : stucco
#   - "Rough"	      : brick
#   - "Medium Rough"  : concrete
#   - "Medium Smooth" : clear pine
#   - "Smooth"        : smooth plaster
#   - "Very Smooth"   : glass

# Thermal mass categories (e.g. exterior cladding, interior finish, framing).
#  - "none"   : token for 'no user selection', resort to defaults
#  - "light"  : e.g. 16mm drywall interior
#  - "medium" : e.g. 100mm brick cladding
#  - "heavy"  : e.g. 200mm poured concrete
_mass = ("none", "light", "medium", "heavy")

# Basic materials (StandardOpaqueMaterials only).
_mats = dict(
    material = {}, # generic, e.g. lightweight cladding over furring, fibreboard
        sand = {},
    concrete = {},
       brick = {},
     drywall = {}, # e.g. finished drywall, intermediate sheating
     mineral = {}, # e.g. light, semi-rigid rock wool insulation
     polyiso = {}, # e.g. polyisocyanurate panel (or similar)
   cellulose = {}, # e.g. blown, dry/stabilized fibre
        door = {}  # single composite material (45mm insulated steel door)
    )

# Default inside + outside air film resistances (m2.K/W).
_film = dict(
      shading = 0.000, # NA
    partition = 0.150, # uninsulated wood- or steel-framed wall
         wall = 0.150, # un/insulated wall
         roof = 0.140, # un/insulated roof
        floor = 0.190, # un/insulated (exposed) floor
     basement = 0.120, # un/insulated basement wall
         slab = 0.160, # un/insulated basement slab or slab-on-grade
         door = 0.150, # standard, 45mm insulated steel (opaque) door
       window = 0.150, # vertical fenestration, e.g. glazed doors, windows
     skylight = 0.140  # e.g. domed 4' x 4' skylight
    )

# Default (~1980s) envelope Uo (W/m2•K), based on surface type.
_uo = dict(
      shading = None,   # N/A
    partition = None,   # N/A
         wall = 0.384, # rated R14.8 hr•ft2F/Btu
         roof = 0.327, # rated R17.6 hr•ft2F/Btu
        floor = 0.317, # rated R17.9 hr•ft2F/Btu (exposed floor)
     basement = None,
         slab = None,
         door = 1.800, # insulated, unglazed steel door (single layer)
       window = 2.800, # e.g. patio doors (simple glazing)
     skylight = 3.500  # all skylight technologies
    )

# Standard opaque materials, taken from a variety of sources (e.g. energy
# codes, NREL's BCL).
#   - sand
#   - concrete
#   - brick
#
# Material properties remain largely constant between projects. What does
# tend to vary (between projects) are thicknesses. Actual OpenStudio opaque
# material objects can be (re)set in more than one way by class methods.
# In genConstruction, OpenStudio object identifiers are later suffixed with
# actual material thicknesses, in mm, e.g.:
#   - "concrete200" : 200mm concrete slab
#   - "drywall13"   : 1/2" gypsum board
#   - "drywall16"   : 5/8" gypsum board
#
# Surface absorptances are also defaulted in OpenStudio:
#   - thermal, long-wave   (thm) : 90%
#   - solar                (sol) : 70%
#   - visible              (vis) : 70%
#
# These can also be explicitly set (see "sand").
_mats["material" ]["rgh"] = "MediumSmooth"
_mats["material" ]["k"  ] =    0.115
_mats["material" ]["rho"] =  540.000
_mats["material" ]["cp" ] = 1200.000

_mats["sand"     ]["rgh"] = "Rough"
_mats["sand"     ]["k"  ] =    1.290
_mats["sand"     ]["rho"] = 2240.000
_mats["sand"     ]["cp" ] =  830.000
_mats["sand"     ]["thm"] =    0.900
_mats["sand"     ]["sol"] =    0.700
_mats["sand"     ]["vis"] =    0.700

_mats["concrete" ]["rgh"] = "MediumRough"
_mats["concrete" ]["k"  ] =    1.730
_mats["concrete" ]["rho"] = 2240.000
_mats["concrete" ]["cp" ] =  830.000

_mats["brick"    ]["rgh"] = "Rough"
_mats["brick"    ]["k"  ] =    0.675
_mats["brick"    ]["rho"] = 1600.000
_mats["brick"    ]["cp" ] =  790.000

_mats["drywall"  ]["k"  ] =    0.160
_mats["drywall"  ]["rho"] =  785.000
_mats["drywall"  ]["cp" ] = 1090.000

_mats["mineral"  ]["k"  ] =    0.050
_mats["mineral"  ]["rho"] =   19.000
_mats["mineral"  ]["cp" ] =  960.000

_mats["polyiso"  ]["k"  ] =    0.025
_mats["polyiso"  ]["rho"] =   25.000
_mats["polyiso"  ]["cp" ] = 1590.000

_mats["cellulose"]["rgh"] = "VeryRough"
_mats["cellulose"]["k"  ] =    0.050
_mats["cellulose"]["rho"] =   80.000
_mats["cellulose"]["cp" ] =  835.000

_mats["door"     ]["rgh"] = "MediumSmooth"
_mats["door"     ]["k"  ] =    0.080
_mats["door"     ]["rho"] =  600.000
_mats["door"     ]["cp" ] = 1000.000


def sidz() -> tuple:
    """Returns available 'sidz' keywords."""
    return _sidz


def mass() -> tuple:
    """Returns available 'mass' keywords."""
    return _mass


def mats() -> dict:
    """Returns stored materials dictionary."""
    return _mats


def film() -> dict:
    """Returns inside + outside air film resistance dictionary."""
    return _film


def uo() -> dict:
    """Returns (surface type-specific) Uo dictionary."""
    return _uo


def each_cons(it, n):
    """A proxy for Ruby enumerate's 'each_cons(n)' method.

    Args:
        it:
            A sequence.
        n (int):
            The number of sequential items in sequence.

    Returns:
        tuple: n-sized sequenced items.

    """
    # see: docs.ruby-lang.org/en/3.2/enumerate.html#method-i-each_cons
    #
    # James Wong's Python workaround implementation:
    # stackoverflow.com/questions/5878403/python-equivalent-to-rubys-each-cons

    # Convert as iterator.
    it  = iter(it)
    deq = collections.deque()

    # Insert first n items to a list first.
    for _ in range(n):
        try:
            deq.append(next(it))
        except StopIteration:
            for _ in range(n - len(deq)):
                deq.append(None)
            yield tuple(deq)
            return

    yield tuple(deq)

    # Main loop.
    while True:
        try:
            val = next(it)
        except StopIteration:
            return
        deq.popleft()
        deq.append(val)
        yield tuple(deq)


def clamp(value, minimum, maximum) -> float:
    """In-house alternative to Numpy's 'clip' (re: Ruby's 'clamp').

    Args:
        value (float):
            A float-convertible value (to clip/clamp).
        minimum (float):
            Lower bound.
        maximum (float):
            Upper bound.

    Returns:
        float: Clamped value. Either value, min, max or '0' if invalid inputs.

    """
    try:
        value = float(value)
    except:
        try:
            minimum = float(minimum)
            return minimum
        except:
            try:
                maximum = float(maximum)
                return maximum
            except:
                return 0.0

    try:
        minimum = float(minimum)
    except:
        return value

    try:
        maximum = float(maximum)
    except:
        return value

    if value < minimum: return minimum
    if value > maximum: return maximum

    return value


def genConstruction(model=None, specs=dict()):
    """Generates an OpenStudio multilayered construction, + materials if needed.

    Args:
        specs:
            A dictionary holding multilayered construction parameters:
            - "id" (str): construction identifier
            - "type" (str): surface type - see OSut 'uo()'
            - "uo" (float): assembly clear-field Uo, in W/m2•K - see OSut 'uo()'
            - "clad" (str): exterior cladding - see OSut 'mass()'
            - "frame" (str): assembly framing - see OSut 'mass()'
            - "finish" (str): interior finish - see OSut 'mass()'

    Returns:
        openstudio.model.Construction: A generated construction.
        None: If invalid inputs (see logs).

    """
    mth = "osut.genConstruction"
    cl  = openstudio.model.Model

    if not isinstance(model, cl):
        return oslg.mismatch("model", model, cl, mth, CN.DBG)
    if not isinstance(specs, dict):
        return oslg.mismatch("specs", specs, dict, mth, CN.DBG)

    if "type" not in specs: specs["type"] = "wall"
    if "id"   not in specs: specs["id"  ] = ""

    ide = oslg.trim(specs["id"])

    if not ide:
        ide = "OSut.CON." + specs["type"]
    if specs["type"] not in uo():
        return oslg.invalid("surface type", mth, 2, CN.ERR)
    if "uo" not in specs:
        specs["uo"] = uo()[ specs["type"] ]

    u = specs["uo"]

    if u:
        try:
            u = float(u)
        except:
            return oslg.mismatch(id + " Uo", u, float, mth, CN.ERR)

        if u < 0:
            return oslg.negative(id + " Uo", mth, CN.ERR)
        if u > 5.678:
            return oslg.invalid(id + " Uo (> 5.678)", mth, 2, CN.ERR)

    # Optional specs. Log/reset if invalid.
    if "clad"   not in specs: specs["clad"  ] = "light" # exterior
    if "frame"  not in specs: specs["frame" ] = "light"
    if "finish" not in specs: specs["finish"] = "light" # interior
    if specs["clad"  ] not in mass(): oslg.log(CN.WRN, "Reset: light cladding")
    if specs["frame" ] not in mass(): oslg.log(CN.WRN, "Reset: light framing")
    if specs["finish"] not in mass(): oslg.log(CN.WRN, "Reset: light finish")
    if specs["clad"  ] not in mass(): specs["clad"  ] = "light"
    if specs["frame" ] not in mass(): specs["frame" ] = "light"
    if specs["frame" ] not in mass(): specs["finish"] = "light"

    flm = film()[ specs["type"] ]

    # Layered assembly (max 4 layers):
    #   - cladding
    #   - intermediate sheathing
    #   - composite insulating/framing
    #   - interior finish
    a = dict(clad={}, sheath={}, compo={}, finish={}, glazing={})

    if specs["type"] == "shading":
        mt = "material"
        d  = 0.015
        a["compo"]["mat"] = mats()[mt]
        a["compo"]["d"  ] = d
        a["compo"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

    elif specs["type"] == "partition":
        if not specs["clad"] == "none":
            mt = "drywall"
            d  = 0.015
            a["clad"]["mat"] = mats()[mt]
            a["clad"]["d"  ] = d
            a["clad"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

        mt = "concrete"
        d  = 0.015
        if specs["frame"] == "light": mt = "material"
        if u:                         mt = "mineral"
        if specs["frame"] == "medium": d = 0.100
        if specs["frame"] == "heavy":  d = 0.200
        if u:                          d = 0.100
        a["compo"]["mat"] = mats()[mt]
        a["compo"]["d"  ] = d
        a["compo"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

        if not specs["finish"] == "none":
            mt = "drywall"
            d  = 0.015
            a["finish"]["mat"] = mats()[mt]
            a["finish"]["d"  ] = d
            a["finish"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

    elif specs["type"] == "wall":
        if not specs["clad"] == "none":
            mt = "material"
            d  = 0.100
            if specs["clad"] == "medium": mt = "brick"
            if specs["clad"] == "heavy":  mt = "concrete"
            if specs["clad"] == "light":   d = 0.015
            a["clad"]["mat"] = mats()[mt]
            a["clad"]["d"  ] = d
            a["clad"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

        mt = "drywall"
        d  = 0.100
        if specs["frame"] == "medium": mt = "mineral"
        if specs["frame"] == "heavy":  mt = "polyiso"
        if specs["frame"] == "light":   d = 0.015
        a["sheath"]["mat"] = mats()[mt]
        a["sheath"]["d"  ] = d
        a["sheath"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

        mt = "mineral"
        d  = 0.100
        if specs["frame"] == "medium": mt = "cellulose"
        if specs["frame"] == "heavy":  mt = "concrete"
        if not u:                      mt = "material"
        if specs["frame"] == "heavy":   d = 0.200
        if not u:                       d = 0.015
        a["compo"]["mat"] = mats()[mt]
        a["compo"]["d"  ] = d
        a["compo"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

        if not specs["finish"] == "none":
            mt = "concrete"
            d  = 0.015
            if specs["finish"] == "light":  mt = "drywall"
            if specs["finish"] == "medium":  d = 0.100
            if specs["finish"] == "heavy":   d = 0.200
            a["finish"]["mat"] = mats()[mt]
            a["finish"]["d"  ] = d
            a["finish"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

    elif specs["type"] == "roof":
        if not specs["clad"] == "none":
            mt = "concrete"
            d  = 0.015
            if specs["clad"] == "light": mt = "material"
            if specs["clad"] == "medium": d = 0.100 # e.g. terrace
            if specs["clad"] == "heavy":  d = 0.200 # e.g. parking garage
            a["clad"]["mat"] = mats()[mt]
            a["clad"]["d"  ] = d
            a["clad"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

        mt = "mineral"
        d  = 0.100
        if specs["frame"] == "medium": mt = "polyiso"
        if specs["frame"] == "heavy":  mt = "cellulose"
        if not u:                      mt = "material"
        if not u:                       d = 0.015
        a["compo"]["mat"] = mats()[mt]
        a["compo"]["d"  ] = d
        a["compo"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

        if not specs["finish"] == "none":
            mt = "concrete"
            d  = 0.015
            if specs["finish"] == "light":  mt = "drywall"
            if specs["finish"] == "medium":  d = 0.100 # proxy for steel decking
            if specs["finish"] == "heavy":   d = 0.200
            a["finish"]["mat"] = mats()[mt]
            a["finish"]["d"  ] = d
            a["finish"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

    elif specs["type"] == "floor":
        if not specs["clad"] == "none":
            mt = "material"
            d  = 0.015
            a["clad"]["mat"] = mats()[mt]
            a["clad"]["d"  ] = d
            a["clad"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

        mt = "mineral"
        d  = 0.100
        if specs["frame"] == "medium": mt = "polyiso"
        if specs["frame"] == "heavy":  mt = "cellulose"
        if not u:                      mt = "material"
        if not u:                       d = 0.015
        a["compo"]["mat"] = mats()[mt]
        a["compo"]["d"  ] = d
        a["compo"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

        if not specs["finish"] == "none":
            mt = "concrete"
            d  = 0.015
            if specs["finish"] == "light": mt = "material"
            if specs["finish"] == "medium": d = 0.100
            if specs["finish"] == "heavy":  d = 0.200
            a["finish"]["mat"] = mats()[mt]
            a["finish"]["d"  ] = d
            a["finish"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

    elif specs["type"] == "slab":
        mt = "sand"
        d  = 0.100
        a["clad"]["mat"] = mats()[mt]
        a["clad"]["d"  ] = d
        a["clad"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

        if not specs["frame"] == "none":
            mt = "polyiso"
            d  = 0.025
            a["sheath"]["mat"] = mats()[mt]
            a["sheath"]["d"  ] = d
            a["sheath"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

        mt = "concrete"
        d  = 0.100
        if specs["frame"] == "heavy": d = 0.200
        a["compo"]["mat"] = mats()[mt]
        a["compo"]["d"  ] = d
        a["compo"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

        if not specs["finish"] == "none":
            mt = "material"
            d  = 0.015
            a["finish"]["mat"] = mats()[mt]
            a["finish"]["d"  ] = d
            a["finish"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

    elif specs["type"] == "basement":
        if not specs["clad"] == "none":
            mt = "concrete"
            d  = 0.100
            if specs["clad"] == "light": mt = "material"
            if specs["clad"] == "light":  d = 0.015
            a["clad"]["mat"] = mats[mt]
            a["clad"]["d"  ] = d
            a["clad"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

            mt = "polyiso"
            d  = 0.025
            a["sheath"]["mat"] = mats()[mt]
            a["sheath"]["d"  ] = d
            a["sheath"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

            mt = "concrete"
            d  = 0.200
            a["compo"]["mat"] = mats()[mt]
            a["compo"]["d"  ] = d
            a["compo"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)
        else:
            mt = "concrete"
            d  = 0.200
            a["sheath"]["mat"] = mats()[mt]
            a["sheath"]["d"  ] = d
            a["sheath"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

            if not specs["finish"] == "none":
                mt = "mineral"
                d  = 0.075
                a["compo"]["mat"] = mats()[mt]
                a["compo"]["d"  ] = d
                a["compo"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

                mt = "drywall"
                d  = 0.015
                a["finish"]["mat"] = mats()[mt]
                a["finish"]["d"  ] = d
                a["finish"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

    elif specs["type"] == "door":
        mt = "door"
        d  = 0.045
        a["compo"  ]["mat" ] = mats()[mt]
        a["compo"  ]["d"   ] = d
        a["compo"  ]["id"  ] = "OSut." + mt + ".%03d" % int(d * 1000)

    elif specs["type"] == "window":
        a["glazing"]["u"   ]  = specs["uo"]
        a["glazing"]["shgc"]  = 0.450
        if "shgc" in specs: a["glazing"]["shgc"] = specs["shgc"]
        a["glazing"]["id"  ]  = "OSut.window"
        a["glazing"]["id"  ] += ".U%.1f"  % a["glazing"]["u"]
        a["glazing"]["id"  ] += ".SHGC%d" % (a["glazing"]["shgc"]*100)

    elif specs["type"] == "skylight":
        a["glazing"]["u"   ]  = specs["uo"]
        a["glazing"]["shgc"]  = 0.450
        if "shgc" in specs: a["glazing"]["shgc"] = specs["shgc"]
        a["glazing"]["id"  ]  = "OSut.skylight"
        a["glazing"]["id"  ] += ".U%.1f"  % a["glazing"]["u"]
        a["glazing"]["id"  ] += ".SHGC%d" % (a["glazing"]["shgc"]*100)

    if a["glazing"]:
        layers = openstudio.model.FenestrationMaterialVector()

        u    = a["glazing"]["u"   ]
        shgc = a["glazing"]["shgc"]
        lyr  = model.getSimpleGlazingByName(a["glazing"]["id"])

        if lyr:
            lyr = lyr.get()
        else:
            lyr = openstudio.model.SimpleGlazing(model, u, shgc)
            lyr.setName(a["glazing"]["id"])

        layers.append(lyr)
    else:
        layers = openstudio.model.OpaqueMaterialVector()

        # Loop through each layer spec, and generate construction.
        for i, l in a.items():
            if not l: continue

            lyr = model.getStandardOpaqueMaterialByName(l["id"])

            if lyr:
                lyr = lyr.get()
            else:
                lyr = openstudio.model.StandardOpaqueMaterial(model)
                lyr.setName(l["id"])
                lyr.setThickness(l["d"])
                if "rgh" in l["mat"]: lyr.setRoughness(l["mat"]["rgh"])
                if "k"   in l["mat"]: lyr.setConductivity(l["mat"]["k"])
                if "rho" in l["mat"]: lyr.setDensity(l["mat"]["rho"])
                if "cp"  in l["mat"]: lyr.setSpecificHeat(l["mat"]["cp" ])
                if "thm" in l["mat"]: lyr.setThermalAbsorptance(l["mat"]["thm"])
                if "sol" in l["mat"]: lyr.setSolarAbsorptance(l["mat"]["sol"])
                if "vis" in l["mat"]: lyr.setVisibleAbsorptance(l["mat"]["vis"])

            layers.append(lyr)

    c  = openstudio.model.Construction(layers)
    c.setName(ide)

    # Adjust insulating layer thickness or conductivity to match requested Uo.
    if not a["glazing"]:
        ro = 1 / specs["uo"] - film()[specs["type"]] if specs["uo"] else 0

        if specs["type"] == "door": # 1x layer, adjust conductivity
            layer = c.getLayer(0).to_StandardOpaqueMaterial()

            if not layer:
                return oslg.invalid(id + " standard material?", mth, 0)

            layer = layer.get()
            k     = layer.thickness() / ro
            layer.setConductivity(k)

        elif ro > 0: # multiple layers, adjust insulating layer thickness
            lyr = insulatingLayer(c)

            if not lyr["index"] or not lyr["type"] or not lyr["r"]:
                return oslg.invalid(id + " construction", mth, 0)

            index = lyr["index"]
            layer = c.getLayer(index).to_StandardOpaqueMaterial()

            if not layer:
                return oslg.invalid(id + " material %d" % index, mth, 0)

            layer = layer.get()
            k     = layer.conductivity()
            d     = (ro - rsi(c) + lyr["r"]) * k

            if d < 0.03:
                return oslg.invalid(id + " adjusted material thickness", mth, 0)

            nom = re.sub(r'[^a-zA-Z]', '', layer.nameString())
            nom = re.sub(r'OSut', '', nom)
            nom = "OSut." + nom + ".%03d" % int(d * 1000)

            if not model.getStandardOpaqueMaterialByName(nom):
                layer.setName(nom)
                layer.setThickness(d)

    return c


def genShade(subs=None) -> bool:
    """Generates solar shade(s) (e.g. roller, textile) for glazed OpenStudio
    SubSurfaces (v321+), controlled to minimize overheating in cooling months
    (May to October in Northern Hemisphere), when outdoor dry bulb temperature
    is above 18°C and impinging solar radiation is above 100 W/m2.

    Args:
        subs:
            A list of sub surfaces.

    Returns:
        True: If shade successfully generated.
        False: If invalid input (see logs).

    """
    # Filter OpenStudio warnings for ShadingControl:
    #   ref: https://github.com/NREL/OpenStudio/issues/4911
    # str = ".*(?<!ShadingControl)$"
    # openstudio.Logger().instance().standardOutLogger().setChannelRegex(str)

    mth = "osut.genShade"
    cl  = openstudio.model.SubSurfaceVector

    if int("".join(openstudio.openStudioVersion().split("."))) < 321:
        return False
    if not isinstance(subs, cl):
        return oslg.mismatch("subs", subs, cl, mth, CN.DBG, False)
    if not subs:
        return oslg.empty("subs", mth, CN.WRN, False)

    # Shading availability period.
    model = subs[0].model()
    ide   = "onoff"
    onoff = model.getScheduleTypeLimitsByName(ide)

    if onoff:
        onoff = onoff.get()
    else:
        onoff = openstudio.model.ScheduleTypeLimits(model)
        onoff.setName(ide)
        onoff.setLowerLimitValue(0)
        onoff.setUpperLimitValue(1)
        onoff.setNumericType("Discrete")
        onoff.setUnitType("Availability")

    # Shading schedule.
    ide = "OSut.SHADE.Ruleset"
    sch = model.getScheduleRulesetByName(ide)

    if sch:
        sch = sch.get()
    else:
        sch = openstudio.model.ScheduleRuleset(model, 0)
        sch.setName(ide)
        sch.setScheduleTypeLimits(onoff)
        sch.defaultDaySchedule().setName("OSut.SHADE.Ruleset.Default")

    # Summer cooling rule.
    ide  = "OSut.SHADE.ScheduleRule"
    rule = model.getScheduleRuleByName(ide)

    if rule:
        rule = rule.get()
    else:
        may     = openstudio.MonthOfYear("May")
        october = openstudio.MonthOfYear("Oct")
        start   = openstudio.Date(may, 1)
        finish  = openstudio.Date(october, 31)

        rule = openstudio.model.ScheduleRule(sch)
        rule.setName(ide)
        rule.setStartDate(start)
        rule.setEndDate(finish)
        rule.setApplyAllDays(True)
        rule.daySchedule().setName("OSut.SHADE.Rule.Default")
        rule.daySchedule().addValue(openstudio.Time(0,24,0,0), 1)

    # Shade object.
    ide = "OSut.SHADE"
    shd = model.getShadeByName(ide)

    if shd:
        shd = shd.get()
    else:
        shd = openstudio.model.Shade(model)
        shd.setName(ide)

    # Shading control (unique to each call).
    ide = "OSut.ShadingControl"
    ctl = openstudio.model.ShadingControl(shd)
    ctl.setName(ide)
    ctl.setSchedule(sch)
    ctl.setShadingControlType("OnIfHighOutdoorAirTempAndHighSolarOnWindow")
    ctl.setSetpoint(18)   # °C
    ctl.setSetpoint2(100) # W/m2
    ctl.setMultipleSurfaceControlType("Group")
    ctl.setSubSurfaces(subs)

    return True


def genMass(sps=None, ratio=2.0) -> bool:
    """ Generates an internal mass definition and instances for target spaces.
    This is largely adapted from OpenStudio-Standards:
        https://github.com/NREL/openstudio-standards/blob/
        eac3805a65be060b39ecaf7901c908f8ed2c051b/lib/openstudio-standards/
        prototypes/common/objects/Prototype.Model.rb#L572

    Args:
        sps (OpenStudio::Model::SpaceVector):
            Target spaces.
        ratio (float):
            Ratio of internal mass surface area to floor surface area.

    Returns:
        bool: Whether successfully generated.
        False: If invalid inputs (see logs).

    """
    mth = "osut.genMass"
    cl = openstudio.model.SpaceVector

    if not isinstance(sps, cl):
        return oslg.mismatch("spaces", sps, cl, mth, CN.DBG, False)

    try:
        ratio = float(ratio)
    except:
        return oslg.mismatch("ratio", ratio, float, mth, CN.DBG, False)

    if not sps:
        return oslg.empty("spaces", mth, CN.DBG, False)
    if ratio < 0:
        return oslg.negative("ratio", mth, CN.ERR, False)

    # A single material.
    mdl = sps[0].model()
    ide = "OSut.MASS.Material"
    mat = mdl.getOpaqueMaterialByName(ide)

    if mat:
        mat = mat.get()
    else:
        mat = openstudio.model.StandardOpaqueMaterial(mdl)
        mat.setName(ide)
        mat.setRoughness("MediumRough")
        mat.setThickness(0.15)
        mat.setConductivity(1.12)
        mat.setDensity(540)
        mat.setSpecificHeat(1210)
        mat.setThermalAbsorptance(0.9)
        mat.setSolarAbsorptance(0.7)
        mat.setVisibleAbsorptance(0.17)

    # A single, 1x layered construction.
    ide = "OSut.MASS.Construction"
    con = mdl.getConstructionByName(ide)

    if con:
        con = con.get()
    else:
        con = openstudio.model.Construction(mdl)
        con.setName(ide)
        layers = openstudio.model.MaterialVector()
        layers.append(mat)
        con.setLayers(layers)

    ide = "OSut.InternalMassDefinition.%.2f" % ratio
    df  = mdl.getInternalMassDefinitionByName(ide)

    if df:
        df = df.get
    else:
        df = openstudio.model.InternalMassDefinition(mdl)
        df.setName(ide)
        df.setConstruction(con)
        df.setSurfaceAreaperSpaceFloorArea(ratio)

    for sp in sps:
        mass = openstudio.model.InternalMass(df)
        mass.setName("OSut.InternalMass.%s" % sp.nameString())
        mass.setSpace(sp)

    return True


def holdsConstruction(cset=None, base=None, gr=False, ex=False, type=""):
    """Validates whether a default construction set holds a base construction.

    Args:
        cset (openstudio.model.DefaultConstructionSet):
            A default construction set.
        base (openstudio.model.ConstructionBase):
            A construction base.
        gr (bool):
            Whether ground-facing surface.
        ex (bool):
            Whether exterior-facing surface.
        type:
            An OpenStudio surface (or sub surface) type (e.g. "Wall").

    Returns:
        bool: Whether default set holds construction.
        False: If invalid input (see logs).

    """
    mth = "osut.holdsConstruction"
    cl1 = openstudio.model.DefaultConstructionSet
    cl2 = openstudio.model.ConstructionBase
    t1  = openstudio.model.Surface.validSurfaceTypeValues()
    t2  = openstudio.model.SubSurface.validSubSurfaceTypeValues()
    t1  = [t.lower() for t in t1]
    t2  = [t.lower() for t in t2]
    c   = None

    if not isinstance(cset, cl1):
        return oslg.mismatch("set", cset, cl1, mth, CN.DBG, False)
    if not isinstance(base, cl2):
        return oslg.mismatch("base", base, cl2, mth, CN.DBG, False)
    if not isinstance(gr, bool):
        return oslg.mismatch("ground", gr, bool, mth, CN.DBG, False)
    if not isinstance(ex, bool):
        return oslg.mismatch("exterior", ex, bool, mth, CN.DBG, False)

    try:
        type = str(type)
    except:
        return oslg.mismatch("surface type", type, str, mth, CN.DBG, False)

    type = type.lower()

    if type in t1:
        if gr:
            if cset.defaultGroundContactSurfaceConstructions():
                c = cset.defaultGroundContactSurfaceConstructions().get()
        elif ex:
            if cset.defaultExteriorSurfaceConstructions():
                c = cset.defaultExteriorSurfaceConstructions().get()
        else:
            if cset.defaultInteriorSurfaceConstructions():
                c = cset.defaultInteriorSurfaceConstructions().get()
    elif type in t2:
        if gr:
            return False
        if ex:
            if cset.defaultExteriorSubSurfaceConstructions():
                c = cset.defaultExteriorSubSurfaceConstructions().get()
        else:
            if cset.defaultInteriorSubSurfaceConstructions():
                c = cset.defaultInteriorSubSurfaceConstructions().get()
    else:
        return oslg.invalid("surface type", mth, 5, CN.DBG, False)

    if c is None: return False

    if type in t1:
        if type == "roofceiling":
            if c.roofCeilingConstruction():
                if c.roofCeilingConstruction().get() == base: return True
        elif type == "floor":
            if c.floorConstruction():
                if c.floorConstruction().get() == base: return True
        else: # "wall"
            if c.wallConstruction():
                if c.wallConstruction().get() == base: return True
    else: # t2
        if type == "tubulardaylightdiffuser":
            if c.tubularDaylightDiffuserConstruction():
                if c.tubularDaylightDiffuserConstruction() == base: return True
        elif type == "tubulardaylightdome":
            if c.tubularDaylightDomeConstruction():
                if c.tubularDaylightDomeConstruction().get() == base: return True
        elif type == "skylight":
            if c.overheadDoorConstruction():
                if c.overheadDoorConstruction().get() == base: return True
        elif type == "glassdoor":
            if c.glassDoorConstruction():
                if c.glassDoorConstruction().get() == base: return True
        elif type == "door":
            if c.doorConstruction():
                if c.doorConstruction().get() == base: return True
        elif type == "operablewindow":
            if c.operableWindowConstruction():
                if c.operableWindowConstruction().get() == base: return True
        else: # "fixedwindow"
            if c.fixedWindowConstruction():
                if c.fixedWindowConstruction().get() == base: return True

    return False


def defaultConstructionSet(s=None):
    """Returns a surface's default construction set.

    Args:
        s (openstudio.model.Surface):
            A surface.

    Returns:
        openstudio.model.DefaultConstructionSet: A default construction set.
        None: If invalid inputs (see logs).

    """
    mth = "osut.defaultConstructionSet"
    cl  = openstudio.model.Surface

    if not isinstance(s, cl):
        return oslg.mismatch("surface", s, cl, mth)
    if not s.isConstructionDefaulted():
        oslg.log(CN.WRN, "construction not defaulted (%s)" % mth)
        return None
    if not s.construction():
        return oslg.empty("construction", mth, CN.WRN)
    if not s.space():
        return oslg.empty("space", mth, CN.WRN)

    mdl   = s.model()
    base  = s.construction().get()
    space = s.space().get()
    type  = s.surfaceType()
    bnd   = s.outsideBoundaryCondition().lower()

    ground   = True if s.isGroundSurface() else False
    exterior = True if bnd == "outdoors"   else False

    if space.defaultConstructionSet():
        cset = space.defaultConstructionSet().get()

        if holdsConstruction(cset, base, ground, exterior, type): return cset

    if space.spaceType():
        spacetype = space.spaceType().get()

        if spacetype.defaultConstructionSet():
            cset = spacetype.defaultConstructionSet().get()

            if holdsConstruction(cset, base, ground, exterior, type):
                return cset

    if space.buildingStory():
        story = space.buildingStory().get()

        if story.defaultConstructionSet():
            cset = story.defaultConstructionSet().get()

            if holdsConstruction(cset, base, ground, exterior, type):
                return cset


    building = mdl.getBuilding()

    if building.defaultConstructionSet():
        cset = building.defaultConstructionSet().get()

        if holdsConstruction(cset, base, ground, exterior, type):
            return cset

    return None


def areStandardOpaqueLayers(lc=None) -> bool:
    """Validates if every material in a layered construction is standard/opaque.

    Args:
        lc (openstudio.model.LayeredConstruction):
            an OpenStudio layered construction

    Returns:
        True: If all layers are valid (standard & opaque).
        False: If invalid inputs (see logs).

    """
    mth = "osut.areStandardOpaqueLayers"
    cl  = openstudio.model.LayeredConstruction

    if not isinstance(lc, cl):
        return oslg.mismatch("lc", lc, cl, mth, CN.DBG, 0.0)

    for m in lc.layers():
        if not m.to_StandardOpaqueMaterial(): return False

    return True


def thickness(lc=None) -> float:
    """Returns total (standard opaque) layered construction thickness (m).

    Args:
        lc (openstudio.model.LayeredConstruction):
            an OpenStudio layered construction

    Returns:
        float: A standard opaque construction thickness.
        0.0: If invalid inputs (see logs).

    """
    mth = "osut.thickness"
    cl  = openstudio.model.LayeredConstruction
    d   = 0.0

    if not isinstance(lc, cl):
        return oslg.mismatch("lc", lc, cl, mth, CN.DBG, 0.0)
    if not areStandardOpaqueLayers(lc):
        oslg.log(CN.ERR, "holding non-StandardOpaqueMaterial(s) %s" % mth)
        return d

    for m in lc.layers(): d += m.thickness()

    return d


def glazingAirFilmRSi(usi=5.85) -> float:
    """Returns total air film resistance of a fenestrated construction (m2•K/W).

    Args:
        usi (float):
            A fenestrated construction's U-factor (W/m2•K).

    Returns:
        float: Total air film resistances.
        0.1216: If invalid input (see logs).

    """
    # The sum of thermal resistances of calculated exterior and interior film
    # coefficients under standard winter conditions are taken from:
    #
    #   https://bigladdersoftware.com/epx/docs/9-6/engineering-reference/
    #   window-calculation-module.html#simple-window-model
    #
    # These remain acceptable approximations for flat windows, yet likely
    # unsuitable for subsurfaces with curved or projecting shapes like domed
    # skylights. The solution here is considered an adequate fix for reporting,
    # awaiting eventual OpenStudio (and EnergyPlus) upgrades to report NFRC 100
    # (or ISO) air film resistances under standard winter conditions.
    #
    # For U-factors above 8.0 W/m2•K (or invalid input), the function returns
    # 0.1216 m2•K/W, which corresponds to a construction with a single glass
    # layer thickness of 2mm & k = ~0.6 W/m.K.
    #
    # The EnergyPlus Engineering calculations were designed for vertical
    # windows, not for horizontal, slanted or domed surfaces - use with caution.
    mth = "osut.glazingAirFilmRSi"
    val = 0.1216

    try:
        usi = float(usi)
    except:
        return oslg.mismatch("usi", usi, float, mth, CN.DBG, val)

    if usi > 8.0:
        return oslg.invalid("usi", mth, 1, CN.WRN, val)
    elif usi < 0:
        return oslg.negative("usi", mth, CN.WRN, val)
    elif abs(usi) < CN.TOL:
        return oslg.zero("usi", mth, CN.WRN, val)

    rsi = 1 / (0.025342 * usi + 29.163853) # exterior film, next interior film

    if usi < 5.85:
        return rsi + 1 / (0.359073 * math.log(usi) + 6.949915)

    return rsi + 1 / (1.788041 * usi - 2.886625)


def rsi(lc=None, film=0.0, t=0.0) -> float:
    """Returns a construction's 'standard calc' thermal resistance (m2•K/W),
    which includes air film resistances. It excludes insulating effects of
    shades, screens, etc. in the case of fenestrated constructions. Adapted
    from BTAP's 'Material' Module "get_conductance" (P. Lopez).

    Args:
        lc (openstudio.model.LayeredConstruction):
            an OpenStudio layered construction
        film (float):
            thermal resistance of surface air films (m2•K/W)
        t (float):
            gas temperature (°C) (optional)

    Returns:
        float: A layered construction's thermal resistance.
        0.0: If invalid input (see logs).

    """
    mth = "osut.rsi"
    cl  = openstudio.model.LayeredConstruction

    if not isinstance(lc, cl):
        return oslg.mismatch("lc", lc, cl, mth, CN.DBG, 0.0)

    try:
        film = float(film)
    except:
        return oslg.mismatch("film", film, float, mth, CN.DBG, 0.0)

    try:
        t = float(t)
    except:
        return oslg.mismatch("temp K", t, float, mth, CN.DBG, 0.0)

    t += 273.0 # °C to K

    if t < 0:
        return oslg.negative("temp K", mth, CN.ERR, 0.0)
    if film < 0:
        return oslg.negative("film", mth, CN.ERR, 0.0)

    rsi = film

    for m in lc.layers():
        if m.to_SimpleGlazing():
            return 1 / m.to_SimpleGlazing().get().uFactor()
        elif m.to_StandardGlazing():
            rsi += m.to_StandardGlazing().get().thermalResistance()
        elif m.to_RefractionExtinctionGlazing():
            rsi += m.to_RefractionExtinctionGlazing().get().thermalResistance()
        elif m.to_Gas():
            rsi += m.to_Gas().get().getThermalResistance(t)
        elif m.to_GasMixture():
            rsi += m.to_GasMixture().get().getThermalResistance(t)

        # Opaque materials next.
        if m.to_StandardOpaqueMaterial():
            rsi += m.to_StandardOpaqueMaterial().get().thermalResistance()
        elif m.to_MasslessOpaqueMaterial():
            rsi += m.to_MasslessOpaqueMaterial()
        elif m.to_RoofVegetation():
            rsi += m.to_RoofVegetation().get().thermalResistance()
        elif m.to_AirGap():
            rsi += m.to_AirGap().get().thermalResistance()

    return rsi


def insulatingLayer(lc=None) -> dict:
    """Identifies a layered construction's (opaque) insulating layer.

    Args:
        lc (openStudio.model.LayeredConstruction):
            an OpenStudio layered construction

    Returns:
        An insulating-layer dictionary:
            - "index" (int): construction's insulating layer index [0, n layers)
            - "type" (str): layer material type ("standard" or "massless")
            - "r" (float): material thermal resistance in m2•K/W.
        If unsuccessful, dictionary is voided as follows (see logs):
            "index": None
            "type": None
            "r": 0.0

    """
    mth = "osut.insulatingLayer"
    cl  = openstudio.model.LayeredConstruction
    res = dict(index=None, type=None, r=0.0)
    i   = 0  # iterator

    if not isinstance(lc, cl):
        return oslg.mismatch("lc", lc, cl, mth, CN.DBG, res)

    for l in lc.layers():
        if l.to_MasslessOpaqueMaterial():
            l = l.to_MasslessOpaqueMaterial().get()

            if l.thermalResistance() < 0.001 or l.thermalResistance() < res["r"]:
                i += 1
                continue
            else:
                res["r"    ] = m.thermalResistance()
                res["index"] = i
                res["type" ] = "massless"

        if l.to_StandardOpaqueMaterial():
            l = l.to_StandardOpaqueMaterial().get()
            k = l.thermalConductivity()
            d = l.thickness()

            if (d < 0.003) or (k > 3.0) or (d / k < res["r"]):
                i += 1
                continue
            else:
                res["r"    ] = d / k
                res["index"] = i
                res["type" ] = "standard"

        i += 1

    return res


def areSpandrels(surfaces=None) -> bool:
    """Validates whether one or more opaque surface(s) can be considered as
    curtain wall (or similar technology) spandrels, regardless of construction
    layers, by looking up AdditionalProperties or identifiers.

    Args:
        surfaces (list):
            One or more openstudio.model.Surface instances.

    Returns:
        bool: Whether surface(s) can be considered 'spandrels'.
        False: If invalid input (see logs).
    """
    mth = "osut.areSpandrels"
    cl  = openstudio.model.Surface

    if isinstance(surfaces, cl):
        surfaces = [surfaces]
    else:
        try:
            surfaces = list(surfaces)
        except:
            return oslg.mismatch("surfaces", surfaces, list, mth, CN.DBG, False)

    for i, s in enumerate(surfaces):
        if not isinstance(s, cl):
            return oslg.mismatch("surface %d" % i, s, cl, mth, CN.DBG, False)

        if s.additionalProperties().hasFeature("spandrel"):
            val = s.additionalProperties().getFeatureAsBoolean("spandrel")

            if val:
                if val.get() is True: continue
                else: return False
            else:
                oslg.invalid("spandrel %d" % i, mth, 1, CN.ERR)

        if "spandrel" not in s.nameString().lower(): return False

    return True


def isFenestrated(s=None) -> bool:
    """Validates whether a sub surface is fenestrated.

    Args:
        s (openstudio.model.SubSurface):
            An OpenStudio sub surface.

    Returns:
        bool: Whether subsurface can be considered 'fenestrated'.
        False: If invalid input (see logs).

    """
    mth = "osut.isFenestrated"
    cl  = openstudio.model.SubSurface

    if not isinstance(s, cl):
        return oslg.mismatch("subsurface", s, cl, mth, CN.DBG, False)

    # OpenStudio::Model::SubSurface.validSubSurfaceTypeValues
    #   "FixedWindow"              : fenestration
    #   "OperableWindow"           : fenestration
    #   "Door"
    #   "GlassDoor"                : fenestration
    #   "OverheadDoor"
    #   "Skylight"                 : fenestration
    #   "TubularDaylightDome"      : fenestration
    #   "TubularDaylightDiffuser"  : fenestration
    if s.subSurfaceType().lower() in ["door", "overheaddoor"]: return False

    return True

# ---- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---- #
# ---- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---- #
# This next set of utilities (~850 lines) help distinguish spaces that are
# directly vs indirectly CONDITIONED, vs SEMIHEATED. The solution here
# relies as much as possible on space conditioning categories found in
# standards like ASHRAE 90.1 and energy codes like the Canadian NECBs.
#
# Both documents share many similarities, regardless of nomenclature. There
# are however noticeable differences between approaches on how a space is
# tagged as falling into one of the aforementioned categories. First, an
# overview of 90.1 requirements, with some minor edits for brevity/emphasis:
#
# www.pnnl.gov/main/publications/external/technical_reports/PNNL-26917.pdf
#
#   3.2.1. General Information - SPACE CONDITIONING CATEGORY
#
#     - CONDITIONED space: an ENCLOSED space that has a heating and/or
#       cooling system of sufficient size to maintain temperatures suitable
#       for HUMAN COMFORT:
#         - COOLED: cooled by a system >= 10 W/m2
#         - HEATED: heated by a system, e.g. >= 50 W/m2 in Climate Zone CZ-7
#         - INDIRECTLY: heated or cooled via adjacent space(s) provided:
#             - UA of adjacent surfaces > UA of other surfaces
#                 or
#             - intentional air transfer from HEATED/COOLED space > 3 ACH
#
#               ... includes plenums, atria, etc.
#
#     - SEMIHEATED space: an ENCLOSED space that has a heating system
#       >= 10 W/m2, yet NOT a CONDITIONED space (see above).
#
#     - UNCONDITIONED space: an ENCLOSED space that is NOT a conditioned
#       space or a SEMIHEATED space (see above).
#
#       NOTE: Crawlspaces, attics, and parking garages with natural or
#       mechanical ventilation are considered UNENCLOSED spaces.
#
#       2.3.3 Modeling Requirements: surfaces adjacent to UNENCLOSED spaces
#       shall be treated as exterior surfaces. All other UNENCLOSED surfaces
#       are to be modeled as is in both proposed and baseline models. For
#       instance, modeled fenestration in UNENCLOSED spaces would not be
#       factored in WWR calculations.
#
#
# Related NECB definitions and concepts, starting with CONDITIONED space:
#
# "[...] the temperature of which is controlled to limit variation in
# response to the exterior ambient temperature by the provision, either
# DIRECTLY or INDIRECTLY, of heating or cooling [...]". Although criteria
# differ (e.g., not sizing-based), the general idea is sufficiently similar
# to ASHRAE 90.1 (e.g. heating and/or cooling based, no distinction for
# INDIRECTLY conditioned spaces like plenums).
#
# SEMIHEATED spaces are described in the NECB (yet not a defined term). The
# distinction is also based on desired/intended design space setpoint
# temperatures (here 15°C) - not system sizing criteria. No further treatment
# is implemented here to distinguish SEMIHEATED from CONDITIONED spaces;
# notwithstanding the AdditionalProperties tag (described further in this
# section), it is up to users to determine if a CONDITIONED space is
# indeed SEMIHEATED or not (e.g. based on MIN/MAX setpoints).
#
# The single NECB criterion distinguishing UNCONDITIONED ENCLOSED spaces
# (such as vestibules) from UNENCLOSED spaces (such as attics) remains the
# intention to ventilate - or rather to what degree. Regardless, the methods
# here are designed to process both classifications in the same way, namely
# by focusing on adjacent surfaces to CONDITIONED (or SEMIHEATED) spaces as
# part of the building envelope.

# In light of the above, OSut methods here are designed without a priori
# knowledge of explicit system sizing choices or access to iterative
# autosizing processes. As discussed in greater detail below, methods here
# are developed to rely on zoning and/or "intended" setpoint temperatures.
# In addition, OSut methods here cannot distinguish between UNCONDITIONED vs
# UNENCLOSED spaces from OpenStudio geometry alone. They are henceforth
# considered synonymous.
#
# For an OpenStudio model in an incomplete or preliminary state, e.g. holding
# fully-formed ENCLOSED spaces WITHOUT thermal zoning information or setpoint
# temperatures (early design stage assessments of form, porosity or
# envelope), OpenStudio spaces are considered CONDITIONED by default. This
# default behaviour may be reset based on the (Space) AdditionalProperties
# "space_conditioning_category" key (4x possible values), which is relied
# upon by OpenStudio-Standards:
#
#   github.com/NREL/openstudio-standards/blob/
#   d2b5e28928e712cb3f137ab5c1ad6d8889ca02b7/lib/openstudio-standards/
#   standards/Standards.Space.rb#L1604C5-L1605C1
#
# OpenStudio-Standards recognizes 4x possible value strings:
#   - "NonResConditioned"
#   - "ResConditioned"
#   - "Semiheated"
#   - "Unconditioned"
#
# OSut maintains existing "space_conditioning_category" key/value pairs
# intact. Based on these, OSut methods may return related outputs:
#
#   "space_conditioning_category" | OSut status   | heating °C | cooling °C
# -------------------------------   -------------   ----------   ----------
#   - "NonResConditioned"           CONDITIONED     21.0         24.0
#   - "ResConditioned"              CONDITIONED     21.0         24.0
#   - "Semiheated"                  SEMIHEATED      15.0         NA
#   - "Unconditioned"               UNCONDITIONED   NA           NA
#
# OSut also looks up another (Space) AdditionalProperties 'key',
# "indirectlyconditioned" to flag plenum or occupied spaces indirectly
# conditioned with transfer air only. The only accepted 'value' for an
# "indirectlyconditioned" 'key' is the name (string) of another (linked)
# space, e.g.:
#
#   "indirectlyconditioned" space | linked space, e.g. "core_space"
# -------------------------------   ---------------------------------------
#   return air plenum               occupied space below
#   supply air plenum               occupied space above
#   dead air space (not a plenum)   nearby occupied space
#
# OSut doesn't validate whether the "indirectlyconditioned" space is actually
# adjacent to its linked space. It nonetheless relies on the latter's
# conditioning category (e.g. CONDITIONED, SEMIHEATED) to determine
# anticipated ambient temperatures in the former. For instance, an
# "indirectlyconditioned"-tagged return air plenum linked to a SEMIHEATED
# space is considered as free-floating in terms of cooling, and unlikely to
# have ambient conditions below 15°C under heating (winter) design
# conditions. OSut will associate this plenum to a 15°C heating setpoint
# temperature. If the SEMIHEATED space instead has a heating setpoint
# temperature of 7°C, then OSut will associate a 7°C heating setpoint to this
# plenum.
#
# Even with a (more developed) OpenStudio model holding valid space/zone
# setpoint temperatures, OSut gives priority to these AdditionalProperties.
# For instance, a CONDITIONED space can be considered INDIRECTLYCONDITIONED,
# even if its zone thermostat has a valid heating and/or cooling setpoint.
# This is in sync with OpenStudio-Standards' method
# "space_conditioning_category()".

def hasAirLoopsHVAC(model=None) -> bool:
    """Validates if model has zones with HVAC air loops.

    Args:
        model (openstudio.model.Model):
            An OpenStudio model.

    Returns:
        bool: Whether model has HVAC air loops.
        False: If invalid input (see logs).
    """
    mth = "osut.hasAirLoopsHVAC"
    cl  = openstudio.model.Model

    if not isinstance(model, cl):
        return oslg.mismatch("model", model, cl, mth, CN.DBG, False)

    for zone in model.getThermalZones():
        if zone.canBePlenum(): continue
        if zone.airLoopHVACs() or zone.isPlenum(): return True

    return False


def scheduleRulesetMinMax(sched=None) -> dict:
    """Returns MIN/MAX values of a schedule (ruleset).

    Args:
        sched (openstudio.model.ScheduleRuleset):
            A schedule.

    Returns:
        dict:
        - "min" (float): min temperature. (None if invalid inputs - see logs).
        - "max" (float): max temperature. (None if invalid inputs - see logs).
    """
    # Largely inspired from David Goldwasser's
    # "schedule_ruleset_annual_min_max_value":
    #
    #   github.com/NREL/openstudio-standards/blob/
    #   99cf713750661fe7d2082739f251269c2dfd9140/lib/openstudio-standards/
    #   standards/Standards.ScheduleRuleset.rb#L124
    mth = "osut.scheduleRulesetMinMax"
    cl  = openstudio.model.ScheduleRuleset
    res = dict(min=None, max=None)

    if not isinstance(sched, cl):
        return oslg.mismatch("sched", sched, cl, mth, CN.DBG, res)

    values = list(sched.defaultDaySchedule().values())

    for rule in sched.scheduleRules(): values += rule.daySchedule().values()

    res["min"] = min(values)
    res["max"] = max(values)

    try:
        res["min"] = float(res["min"])
    except:
        res["min"] = None

    try:
        res["max"] = float(res["max"])
    except:
        res["max"] = None

    return res


def scheduleConstantMinMax(sched=None) -> dict:
    """Returns MIN/MAX values of a schedule (constant).

    Args:
        sched (openstudio.model.ScheduleConstant):
            A schedule.

    Returns:
        dict:
        - "min" (float): min temperature. (None if invalid inputs - see logs).
        - "max" (float): max temperature. (None if invalid inputs - see logs).
    """
    # Largely inspired from David Goldwasser's
    # "schedule_constant_annual_min_max_value":
    #
    #   github.com/NREL/openstudio-standards/blob/
    #   99cf713750661fe7d2082739f251269c2dfd9140/lib/openstudio-standards/
    #   standards/Standards.ScheduleConstant.rb#L21
    mth = "osut.scheduleConstantMinMax"
    cl  = openstudio.model.ScheduleConstant
    res = dict(min=None, max=None)

    if not isinstance(sched, cl):
        return oslg.mismatch("sched", sched, cl, mth, CN.DBG, res)

    try:
        value = float(sched.value())
    except:
        return None

    res["min"] = value
    res["max"] = value

    return res


def scheduleCompactMinMax(sched=None) -> dict:
    """Returns MIN/MAX values of a schedule (compact).

    Args:
        sched (openstudio.model.ScheduleCompact):
            A schedule.

    Returns:
        dict:
        - "min" (float): min temperature. (None if invalid inputs - see logs).
        - "max" (float): max temperature. (None if invalid inputs - see logs).
    """
    # Largely inspired from Andrew Parker's
    # "schedule_compact_annual_min_max_value":
    #
    #   github.com/NREL/openstudio-standards/blob/
    #   99cf713750661fe7d2082739f251269c2dfd9140/lib/openstudio-standards/
    #   standards/Standards.ScheduleCompact.rb#L8
    mth  = "osut.scheduleCompactMinMax"
    cl   = openstudio.model.ScheduleCompact
    vals = []
    prev = ""
    res  = dict(min=None, max=None)

    if not isinstance(sched, cl):
        return oslg.mismatch("sched", sched, cl, mth, CN.DBG, res)

    for eg in sched.extensibleGroups():
        if "until" in prev:
            if eg.getDouble(0): vals.append(eg.getDouble(0).get())

        str  = eg.getString(0)

        if str: prev = str.get().lower()

    if not vals:
        return oslg.empty("compact sched values", mth, CN.WRN, res)

    res["min"] = min(vals)
    res["max"] = max(vals)

    try:
        res["min"] = float(res["min"])
    except:
        res["min"] = None

    try:
        res["max"] = float(res["max"])
    except:
        res["max"] = None

    return res


def scheduleIntervalMinMax(sched=None) -> dict:
    """Returns MIN/MAX values of a schedule (interval).

    Args:
        sched (openstudio.model.ScheduleInterval):
            A schedule.

    Returns:
        dict:
        - "min" (float): min temperature. (None if invalid inputs - see logs).
        - "max" (float): max temperature. (None if invalid inputs - see logs).
    """
    mth  = "osut.scheduleCompactMinMax"
    cl   = openstudio.model.ScheduleInterval
    vals = []
    res  = dict(min=None, max=None)

    if not isinstance(sched, cl):
        return oslg.mismatch("sched", sched, cl, mth, CN.DBG, res)

    vals = sched.timeSeries().values()

    res["min"] = min(values)
    res["max"] = max(values)

    try:
        res["min"] = float(res["min"])
    except:
        res["min"] = None

    try:
        res["max"] = float(res["max"])
    except:
        res["max"] = None

    return res


def maxHeatScheduledSetpoint(zone=None) -> dict:
    """Returns MAX zone heating temperature schedule setpoint [°C] and
    whether zone has an active dual setpoint thermostat.

    Args:
        zone (openstudio.model.ThermalZone):
            An OpenStudio thermal zone.

    Returns:
        dict:
        - spt (float): MAX heating setpoint (None if invalid inputs - see logs).
        - dual (bool): dual setpoint? (False if invalid inputs - see logs).
    """
    # Largely inspired from Parker & Marrec's "thermal_zone_heated?" procedure.
    # The solution here is a tad more relaxed to encompass SEMIHEATED zones as
    # per Canadian NECB criteria (basically any space with at least 10 W/m2 of
    # installed heating equipement, i.e. below freezing in Canada).
    #
    #   github.com/NREL/openstudio-standards/blob/
    #   58964222d25783e9da4ae292e375fb0d5c902aa5/lib/openstudio-standards/
    #   standards/Standards.ThermalZone.rb#L910
    mth = "osut.maxHeatScheduledSetpoint"
    cl  = openstudio.model.ThermalZone
    res = dict(spt=None, dual=False)

    if not isinstance(zone, cl):
        return oslg.mismatch("zone", zone, cl, mth, CN.DBG, res)

    # Zone radiant heating? Get schedule from radiant system.
    for equip in zone.equipment():
        sched = None

        if equip.to_ZoneHVACHighTemperatureRadiant():
            equip = equip.to_ZoneHVACHighTemperatureRadiant().get()

            if equip.heatingSetpointTemperatureSchedule():
                sched = equip.heatingSetpointTemperatureSchedule().get()

        if equip.to_ZoneHVACLowTemperatureRadiantElectric():
            equip = equip.to_ZoneHVACLowTemperatureRadiantElectric().get()

            sched = equip.heatingSetpointTemperatureSchedule()

        if equip.to_ZoneHVACLowTempRadiantConstFlow():
            equip = equip.to_ZoneHVACLowTempRadiantConstFlow().get()
            coil = equip.heatingCoil()

            if coil.to_CoilHeatingLowTempRadiantConstFlow():
                coil = coil.to_CoilHeatingLowTempRadiantConstFlow().get()

                if coil.heatingHighControlTemperatureSchedule():
                    sched = c.heatingHighControlTemperatureSchedule().get()

        if equip.to_ZoneHVACLowTempRadiantVarFlow():
            equip = equip.to_ZoneHVACLowTempRadiantVarFlow().get()
            coil = equip.heatingCoil()

            if coil.to_CoilHeatingLowTempRadiantVarFlow():
                coil = coil.to_CoilHeatingLowTempRadiantVarFlow().get()

                if coil.heatingControlTemperatureSchedule():
                    sched = coil.heatingControlTemperatureSchedule().get()

        if sched is None: continue

        if sched.to_ScheduleRuleset():
            sched = sched.to_ScheduleRuleset().get()
            maximum = scheduleRulesetMinMax(sched)["max"]

            if maximum:
                if res["spt"] is None or res["spt"] < maximum:
                    res["spt"] = maximum

            dd = sched.winterDesignDaySchedule()

            if dd.values():
                if res["spt"] is None or res["spt"] < max(dd.values()):
                    res["spt"] = max(dd.values())

        if sched.to_ScheduleConstant():
            sched = sched.to_ScheduleConstant().get()
            maximum = scheduleConstantMinMax(sched)["max"]

            if maximum:
                if res["spt"] is None or res["spt"] < maximum:
                    res["spt"] = maximum

        if sched.to_ScheduleCompact():
            sched = sched.to_ScheduleCompact().get()
            maximum = scheduleCompactMinMax(sched)["max"]

            if maximum:
                if res["spt"] is None or res["spt"] < maximum:
                    res["spt"] = maximum

        if sched.to_ScheduleInterval():
            sched = sched.to_ScheduleInterval().get()
            maximum = scheduleIntervalMinMax(sched)["max"]

            if maximum:
                if res["spt"] is None or res["spt"] < maximum:
                    res["spt"] = maximum

    if not zone.thermostat(): return res

    tstat = zone.thermostat().get()
    res["spt"] = None

    if (tstat.to_ThermostatSetpointDualSetpoint() or
        tstat.to_ZoneControlThermostatStagedDualSetpoint()):

        if tstat.to_ThermostatSetpointDualSetpoint():
            tstat = tstat.to_ThermostatSetpointDualSetpoint().get()
        else:
            tstat = tstat.to_ZoneControlThermostatStagedDualSetpoint().get()

        if tstat.heatingSetpointTemperatureSchedule():
            res["dual"] = True
            sched = tstat.heatingSetpointTemperatureSchedule().get()

            if sched.to_ScheduleRuleset():
                sched = sched.to_ScheduleRuleset().get()
                maximum = scheduleRulesetMinMax(sched)["max"]

                if maximum:
                    if res["spt"] is None or res["spt"] < maximum:
                        res["spt"] = maximum

                dd = sched.winterDesignDaySchedule()

                if dd.values():
                    if res["spt"] is None or res["spt"] < max(dd.values()):
                        res["spt"] = max(dd.values())

            if sched.to_ScheduleConstant():
                sched = sched.to_ScheduleConstant().get()
                maximum = scheduleConstantMinMax(sched)["max"]

                if maximum:
                    if res["spt"] is None or res["spt"] < maximum:
                        res["spt"] = maximum

            if sched.to_ScheduleCompact():
                sched = sched.to_ScheduleCompact().get()
                maximum = scheduleCompactMinMax(sched)["max"]

                if maximum:
                    if res["spt"] is None or res["spt"] < maximum:
                        res["spt"] = maximum

            if sched.to_ScheduleInterval():
                sched = sched.to_ScheduleInterval().get()
                maximum = scheduleIntervalMinMax(sched)["max"]

                if maximum:
                    if res["spt"] is None or res["spt"] < maximum:
                        res["spt"] = maximum

            if sched.to_ScheduleYear():
                sched = sched.to_ScheduleYear().get()

                for week in sched.getScheduleWeeks():
                    if not week.winterDesignDaySchedule():
                        dd = week.winterDesignDaySchedule().get()

                        if dd.values():
                            if res["spt"] is None or res["spt"] < max(dd.values()):
                                res["spt"] = max(dd.values())
    return res


def hasHeatingTemperatureSetpoints(model=None):
    """Confirms if model has zones with valid heating setpoint temperature.

    Args:
        model (openstudio.model.Model):
            An OpenStudio model.

    Returns:
        bool: Whether model holds valid heating setpoint temperatures.
        False: If invalid inputs (see logs).
    """
    mth = "osut.hasHeatingTemperatureSetpoints"
    cl  = openstudio.model.Model

    if not isinstance(model, cl):
        return oslg.mismatch("model", model, cl, mth, CN.DBG, False)

    for zone in model.getThermalZones():
        if maxHeatScheduledSetpoint(zone)["spt"]: return True

    return False


def minCoolScheduledSetpoint(zone=None):
    """Returns MIN zone cooling temperature schedule setpoint [°C] and
    whether zone has an active dual setpoint thermostat.

    Args:
        zone (openstudio.model.ThermalZone):
            An OpenStudio thermal zone.

    Returns:
        dict:
        - spt (float): MIN cooling setpoint (None if invalid inputs - see logs).
        - dual (bool): dual setpoint? (False if invalid inputs - see logs).
    """
    # Largely inspired from Parker & Marrec's "thermal_zone_cooled?" procedure.
    #
    #   github.com/NREL/openstudio-standards/blob/
    #   99cf713750661fe7d2082739f251269c2dfd9140/lib/openstudio-standards/
    #   standards/Standards.ThermalZone.rb#L1058
    mth = "osut.minCoolScheduledSetpoint"
    cl  = openstudio.model.ThermalZone
    res = dict(spt=None, dual=False)

    if not isinstance(zone, cl):
        return oslg.mismatch("zone", zone, cl, mth, CN.DBG, res)

    # Zone radiant cooling? Get schedule from radiant system.
    for equip in zone.equipment():
        sched = None

        if equip.to_ZoneHVACLowTempRadiantConstFlow():
            equip = equip.to_ZoneHVACLowTempRadiantConstFlow().get()
            coil = equip.coolingCoil()

            if coil.to_CoilCoolingLowTempRadiantConstFlow():
                coil = coil.to_CoilCoolingLowTempRadiantConstFlow().get()

                if coil.coolingLowControlTemperatureSchedule():
                    sched = coil.coolingLowControlTemperatureSchedule().get()

        if equip.to_ZoneHVACLowTempRadiantVarFlow():
            equip = equip.to_ZoneHVACLowTempRadiantVarFlow().get()
            coil = equip.coolingCoil()

            if coil.to_CoilCoolingLowTempRadiantVarFlow():
                coil = coil.to_CoilCoolingLowTempRadiantVarFlow().get()

                if coil.coolingControlTemperatureSchedule():
                    sched = coil.coolingControlTemperatureSchedule().get()

        if sched is None: continue

        if sched.to_ScheduleRuleset():
            sched = sched.to_ScheduleRuleset().get()
            minimum = scheduleRulesetMinMax(sched)["min"]

            if minimum:
                if res["spt"] is None or res["spt"] > minimum:
                    res["spt"] = minimum

            dd = sched.summerDesignDaySchedule()

            if dd.values():
                if res["spt"] is None or res["spt"] > min(dd.values()):
                    res["spt"] = min(dd.values())

        if sched.to_ScheduleConstant():
            sched = sched.to_ScheduleConstant().get()
            minimum = scheduleConstantMinMax(sched)["min"]

            if minimum:
                if res["spt"] is None or res["spt"] > minimum:
                    res["spt"] = minimum

        if sched.to_ScheduleCompact():
            sched = sched.to_ScheduleCompact().get()
            minimum = scheduleCompactMinMax(sched)["min"]

            if minimum:
                if res["spt"] is None or res["spt"] > minimum:
                    res["spt"] = minimum

        if sched.to_ScheduleInterval():
            sched = sched.to_ScheduleInterval().get()
            minimum = scheduleIntervalMinMax(sched)["min"]

            if minimum:
                if res["spt"] is None or res["spt"] > minimum:
                    res["spt"] = minimum

    if not zone.thermostat(): return res

    tstat     = zone.thermostat().get()
    res["spt"] = None

    if (tstat.to_ThermostatSetpointDualSetpoint() or
        tstat.to_ZoneControlThermostatStagedDualSetpoint()):

        if tstat.to_ThermostatSetpointDualSetpoint():
            tstat = tstat.to_ThermostatSetpointDualSetpoint().get()
        else:
            tstat = tstat.to_ZoneControlThermostatStagedDualSetpoint().get()

        if tstat.coolingSetpointTemperatureSchedule():
            res["dual"] = True
            sched = tstat.coolingSetpointTemperatureSchedule().get()

            if sched.to_ScheduleRuleset():
                sched = sched.to_ScheduleRuleset().get()

                minimum = scheduleRulesetMinMax(sched)["min"]

                if minimum:
                    if res["spt"] is None or res["spt"] > minimum:
                        res["spt"] = minimum

                dd = sched.summerDesignDaySchedule()

                if dd.values():
                    if res["spt"] is None or res["spt"] > min(dd.values()):
                        res["spt"] = min(dd.values())

            if sched.to_ScheduleConstant():
                sched = sched.to_ScheduleConstant().get()
                minimum = scheduleConstantMinMax(sched)["min"]

                if minimum:
                    if res["spt"] is None or res["spt"] > minimum:
                        res["spt"] = minimum

            if sched.to_ScheduleCompact():
                sched = sched.to_ScheduleCompact().get()
                minimum = scheduleCompactMinMax(sched)["min"]

                if minimum:
                    if res["spt"] is None or res["spt"] > minimum:
                        res["spt"] = minimum

            if sched.to_ScheduleInterval():
                sched = sched.to_ScheduleInterval().get()
                minimum = scheduleIntervalMinMax(sched)["min"]

                if minimum:
                    if res["spt"] is None or res["spt"] > minimum:
                        res["spt"] = minimum

            if sched.to_ScheduleYear():
                sched = sched.to_ScheduleYear().get()

                for week in sched.getScheduleWeeks():
                    if not week.summerDesignDaySchedule():
                        dd = week.summerDesignDaySchedule().get()

                        if dd.values():
                            if res["spt"] is None or res["spt"] < min(dd.values()):
                                res["spt"] = min(dd.values())

    return res


def hasCoolingTemperatureSetpoints(model=None):
    """Confirms if model has zones with valid cooling setpoint temperatures.

    Args:
        model (openstudio.model.Model):
            An OpenStudio model.

    Returns:
        bool: Whether model holds valid cooling setpoint temperatures.
        False: If invalid inputs (see logs).
    """
    mth = "osut.hasCoolingTemperatureSetpoints"
    cl  = openstudio.model.Model

    if not isinstance(model, cl):
        return oslg.mismatch("model", model, cl, mth, CN.DBG, False)

    for zone in model.getThermalZones():
        if minCoolScheduledSetpoint(zone)["spt"]: return True

    return False


def areVestibules(spaces=None):
    """Validates whether one or more spaces can be considered vestibules(s).

    Args:
        spaces (list):
            One or more openstudio.model.Space instances.

    Returns:
        bool: Whether space(s) can be considered as vestibule(s).
        False: If invalid input (see logs).
    """
    # INFO: OpenStudio-Standards' "thermal_zone_vestibule" criteria:
    #   - zones less than 200ft2; AND
    #   - having infiltration using Design Flow Rate
    #
    #   github.com/NREL/openstudio-standards/blob/
    #   86bcd026a20001d903cc613bed6d63e94b14b142/lib/openstudio-standards/
    #   standards/Standards.ThermalZone.rb#L1264
    #
    # This (unused) OpenStudio-Standards method likely needs revision; it
    # returns "False" if thermal zone areas were less than 200ft2. Not sure
    # which edition of 90.1 relies on a 200ft2 threshold (2010?) - 90.1 2016
    # doesn't. Yet even fixed, the method would nonetheless misidentify as
    # "vestibule" a small space along an exterior wall, such as a semiheated
    # storage space.
    #
    # The code below is intended as a simple (short-term?) workaround, relying
    # on AdditionalProperties, or (if missing) a "vestibule" substring within a
    # space's spaceType name (or the latter's standardsSpaceType).
    #
    # Some future method could infer its status as vestibule based on a few
    # basic features (common to all vintages):
    #   - 1x+ outdoor-facing wall(s) holding 1x+ door(s)
    #   - adjacent to 1x+ 'occupied' conditioned space(s)
    #   - ideally, 1x+ door(s) between vestibule and 1x+ such adjacent space(s)
    #
    # An additional method parameter (e.g. std = "necb") could be added to
    # ensure supplementary Standard-specific checks (e.g. maximum floor area,
    # minimum distance between doors).
    #
    # Finally, an entirely separate method could be developed to first identify
    # whether "building entrances" (a defined term in 90.1) actually require
    # vestibules as per specific code requirements. Food for thought.
    mth = "osut.areVestibules"
    cl  = openstudio.model.Space

    if isinstance(spaces, cl):
        spaces = [spaces]
    elif not isinstance(spaces, list):
        return oslg.mismatch("spaces", spaces, list, mth, CN.DBG, False)

    for space in spaces:
        if not isinstance(space, cl):
            return oslg.mismatch("space", space, cl, mth, CN.DBG, False)

        if space.additionalProperties().hasFeature("vestibule"):
            val = space.additionalProperties().getFeatureAsBoolean("vestibule")

            if val:
                if val.get() is True: continue
                else: return False
            else:
                oslg.invalid("vestibule", mth, 1, CN.ERR)

        if space.spaceType():
            type = space.spaceType().get()
            if "plenum" in type.nameString().lower(): return False
            if "vestibule" in type.nameString().lower(): continue

            if type.standardsSpaceType():
                type = type.standardsSpaceType().get().lower()
                if "plenum" in type: return False
                if "vestibule" in type: continue

        return False

    return True


def arePlenums(spaces=None):
    """Validates whether one or more spaces can be considered
    indirectly-conditioned plenum(s).

    Args:
        spaces (list):
            One or more openstudio.model.Space instances.

    Returns:
        bool: Whether space(s) can be considered plenum(s).
        False: If invalid input (see logs).
    """
    # Largely inspired from NREL's "space_plenum?":
    #
    #   github.com/NREL/openstudio-standards/blob/
    #   58964222d25783e9da4ae292e375fb0d5c902aa5/lib/openstudio-standards/
    #   standards/Standards.Space.rb#L1384
    #
    # Ideally, OSut's "arePlenums" should be in sync with OpenStudio SDK's
    # "isPlenum" method, which solely looks for either HVAC air mixer objects:
    #  - AirLoopHVACReturnPlenum
    #  - AirLoopHVACSupplyPlenum
    #
    # Of the OpenStudio-Standards Prototype models, only the LargeOffice
    # holds AirLoopHVACReturnPlenum objects. OpenStudio-Standards' method
    # "space_plenum?" indeed catches them by checking if the space is
    # "partofTotalFloorArea" (which internally has an "isPlenum" check). So
    # "isPlenum" closely follows ASHRAE 90.1 2016's definition of "plenum":
    #
    #   "plenum": a compartment or chamber ...
    #             - to which one or more ducts are connected
    #             - that forms a part of the air distribution system, and
    #             - that is NOT USED for occupancy or storage.
    #
    # Canadian NECB 2020 has the following (not as well) defined term:
    #   "plenum": a chamber forming part of an air duct system.
    #             ... we'll assume that a space shall also be considered
    #             UNOCCUPIED if it's "part of an air duct system".
    #
    # As intended, "isPlenum" would NOT identify as a "plenum" any vented
    # UNCONDITIONED or UNENCLOSED attic or crawlspace - good. Yet "isPlenum"
    # would also ignore dead air spaces integrating ducted return air. The
    # SDK's "partofTotalFloorArea" would be more suitable in such cases, as
    # long as modellers have, a priori, set this parameter to FALSE.
    #
    # By initially relying on the SDK's "partofTotalFloorArea", "space_plenum?"
    # ends up catching a MUCH WIDER range of spaces, which aren't caught by
    # "isPlenum". This includes attics, crawlspaces, non-plenum air spaces above
    # ceiling surfaces, and any other UNOCCUPIED space in a model. The term
    # "plenum" in that context is more of a catch-all shorthand - to be used
    # with caution. For instance, "space_plenum?" shouldn't be used (in
    # isolation) to determine whether an UNOCCUPIED space should have its
    # envelope insulated ("plenum") or not ("attic").
    #
    # In contrast to OpenStudio-Standards' "space_plenum?", OSut's "arePlenums"
    # strictly returns FALSE if a space is indeed "partofTotalFloorArea". It
    # also returns FALSE if the space is a vestibule. Otherwise, it needs more
    # information to determine if such an UNOCCUPIED space is indeed a
    # plenum. Beyond these 2x criteria, a space is considered a plenum if:
    #
    # CASE A: it includes the substring "plenum" (case insensitive) in its
    #         spaceType's name, or in the latter's standardsSpaceType string;
    #
    # CASE B: "isPlenum" is TRUE in an OpenStudio model WITH HVAC airloops; OR
    #
    # CASE C: its zone holds an 'inactive' thermostat (i.e. can't extract valid
    #         setpoints) in an OpenStudio model with setpoint temperatures.
    #
    # If a modeller is instead simply interested in identifying UNOCCUPIED
    # spaces that are INDIRECTLYCONDITIONED (not necessarily plenums), then the
    # following combination is likely more reliable and less confusing:
    #   - SDK's partofTotalFloorArea == FALSE
    #   - OSut's isUnconditioned == FALSE
    mth = "osut.arePlenums"
    cl  = openstudio.model.Space

    if isinstance(spaces, cl):
        spaces = [spaces]
    elif not isinstance(spaces, list):
        return oslg.mismatch("spaces", spaces, list, mth, CN.DBG, False)

    for space in spaces:
        if not isinstance(space, cl):
            return oslg.mismatch("space", space, cl, mth, CN.DBG, False)

        if space.partofTotalFloorArea(): return False
        if areVestibules(space): return False

        # CASE A: "plenum" spaceType.
        if space.spaceType():
            type = space.spaceType().get()
            if "plenum" in type.nameString().lower(): continue

            if type.standardsSpaceType():
                type = type.standardsSpaceType().get().lower()
                if "plenum" in type: continue

        # CASE B: "isPlenum" is TRUE if airloops.
        if hasAirLoopsHVAC(space.model()):
            if space.isPlenum(): continue

        # CASE C: zone holds an 'inactive' thermostat.
        zone   = space.thermalZone()
        heated = hasHeatingTemperatureSetpoints(space.model())
        cooled = hasCoolingTemperatureSetpoints(space.model())

        if heated or cooled:
            if zone:
                zone = zone.get()
                heat = maxHeatScheduledSetpoint(zone)
                cool = minCoolScheduledSetpoint(zone)

                # Directly CONDITIONED?
                if heat["spt"]: return False
                if cool["spt"]: return False

                # Inactive thermostat?
                if heat["dual"]: continue
                if cool["dual"]: continue

        return False

    return True


def setpoints(space=None):
    """Retrieves a space's (implicit or explicit) heating/cooling setpoints.

    Args:
        space (OpenStudio::Model::Space):
            An OpenStudio space.
    Returns:
        dict:
        - heating (float): heating setpoint (None if invalid inputs - see logs).
        - cooling (float): cooling setpoint (None if invalid inputs - see logs).
    """
    mth = "osut.setpoints"
    cl1 = openstudio.model.Space
    cl2 = str
    res = dict(heating=None, cooling=None)
    tg1 = "space_conditioning_category"
    tg2 = "indirectlyconditioned"
    cts = ["nonresconditioned", "resconditioned", "semiheated", "unconditioned"]
    cnd = None

    if not isinstance(space, cl1):
        return oslg.mismatch("space", space, cl1, mth, CN.DBG, res)

    # 1. Check for OpenStudio-Standards' space conditioning categories.
    if space.additionalProperties().hasFeature(tg1):
        cnd = space.additionalProperties().getFeatureAsString(tg1)

        if cnd:
            cnd = cnd.get()

            if cnd.lower() in cts:
                if cnd.lower() == "unconditioned": return res
            else:
                oslg.invalid("%s:%s" % (tg1, cnd), mth, 0, CN.ERR)
                cnd = None
        else:
            cnd = None

    # 2. Check instead OSut's INDIRECTLYCONDITIONED (parent space) link.
    if cnd is None:
        ide = space.additionalProperties().getFeatureAsString(tg2)

        if ide:
            ide = ide.get()
            dad = space.model().getSpaceByName(ide)

            if dad:
                # Now focus on 'parent' space of INDIRECTLYCONDITIONED space.
                space = dad.get()
                cnd   = tg2
            else:
                oslg.log(ERR, "Unknown space %s (%s)" % (ide, mth))

    # 3. Fetch space setpoints (if model indeed holds valid setpoints).
    heated = hasHeatingTemperatureSetpoints(space.model())
    cooled = hasCoolingTemperatureSetpoints(space.model())
    zone   = space.thermalZone()

    if heated or cooled:
        if not zone: return res # UNCONDITIONED

        zone = zone.get()
        res["heating"] = maxHeatScheduledSetpoint(zone)["spt"]
        res["cooling"] = minCoolScheduledSetpoint(zone)["spt"]

    # 4. Reset if AdditionalProperties were found & valid.
    if cnd:
        if cnd.lower() == "unconditioned":
            res["heating"] = None
            res["cooling"] = None
        elif cnd.lower() == "semiheated":
            if not res["heating"]: res["heating"] = 14.0
            res["cooling"] = None
        elif "conditioned" in cnd.lower():
            # "nonresconditioned", "resconditioned" or "indirectlyconditioned"
            if not res["heating"]: res["heating"] = 21.0 # default
            if not res["cooling"]: res["cooling"] = 24.0 # default

    # 5. Reset if plenum.
    if arePlenums(space):
        if not res["heating"]: res["heating"] = 21.0 # default
        if not res["cooling"]: res["cooling"] = 24.0 # default

    return res


def isUnconditioned(space=None):
    """Validates if a space is UNCONDITIONED.

    Args:
        space (openstudio.model.Space):
            An OpenStudio space.
    Returns:
        bool: Whether space is considered UNCONDITIONED.
        False: If invalid input (see logs).
    """
    mth = "osut.isUnconditioned"
    cl  = openstudio.model.Space

    if not isinstance(space, cl):
        return oslg.mismatch("space", space, cl, mth, CN.DBG, False)

    if setpoints(space)["heating"]: return False
    if setpoints(space)["cooling"]: return False

    return True


def isRefrigerated(space=None):
    """Confirms if a space can be considered as REFRIGERATED.

    Args:
        space (openstudio.model.Space):
            An OpenStudio space.

    Returns:
        bool: Whether space is considered REFRIGERATED.
        False: If invalid inputs (see logs).
    """
    mth = "osut.isRefrigerated"
    cl  = openstudio.model.Space
    tg0 = "refrigerated"

    if not isinstance(space, cl):
        return oslg.mismatch("space", space, cl, mth, CN.DBG, False)

    ide = space.nameString()

    # 1. First check OSut's REFRIGERATED status.
    status = space.additionalProperties().getFeatureAsString(tg0)

    if status:
        status = status.get()
        if isinstance(status, bool): return status
        oslg.log(ERR, "Unknown %s REFRIGERATED %s (%s)" % (ide, status, mth))

    # 2. Else, compare design heating/cooling setpoints.
    stps = setpoints(space)
    if stps["heating"]: return False
    if not stps["cooling"]: return False
    if stps["cooling"] < 15: return True

    return False


def isSemiheated(space=None):
    """Confirms if a space can be considered as SEMIHEATED as per NECB 2020
    1.2.1.2. 2): Design heating setpoint < 15°C (and non-REFRIGERATED).

    Args:
        space (openstudio.model.space):
            An OpenStudio space.

    Returns:
        bool: Whether space is considered SEMIHEATED.
        False: If invalid inputs (see logs).
    """
    mth = "osut.isSemiheated"
    cl  = openstudio.model.Space

    if not isinstance(space, cl):
        return oslg.mismatch("space", space, cl, mth, CN.DBG, False)
    if isRefrigerated(space):
        return False

    stps = setpoints(space)
    if stps["cooling"]: return False
    if not stps["heating"]: return False
    if stps["heating"] < 15: return True

    return False


def availabilitySchedule(model=None, avl=""):
    """Generates an HVAC availability schedule (if missing from model).

    Args:
        model (openstudio.model.Model):
            An OpenStudio model.
        avl (str):
            Seasonal availability choice (optional, default "ON").

    Returns:
        OpenStudio::Model::Schedule: An OpenStudio HVAC availability schedule.
        None: If invalid input (see logs).
    """
    mth    = "osut.availabilitySchedule"
    cl     = openstudio.model.Model
    limits = None

    if not isinstance(model, cl):
        return oslg.mismatch("model", model, cl, mth)

    try:
        avl = str(avl)
    except:
        return oslg.mismatch("availability", avl, str, mth, CN.ERR)

    # Either fetch availability ScheduleTypeLimits object, or create one.
    for l in model.getScheduleTypeLimitss():
        ide = l.nameString().lower()

        if limits: break
        if not l.lowerLimitValue(): continue
        if not l.upperLimitValue(): continue
        if not l.numericType(): continue
        if not int(l.lowerLimitValue().get()) == 0: continue
        if not int(l.upperLimitValue().get()) == 1: continue
        if not l.numericType().get().lower() == "discrete": continue
        if not l.unitType().lower() == "availability": continue
        if ide != "hvac operation scheduletypelimits": continue

        limits = l

    if limits is None:
        limits = openstudio.model.ScheduleTypeLimits(model)
        limits.setName("HVAC Operation ScheduleTypeLimits")
        limits.setLowerLimitValue(0)
        limits.setUpperLimitValue(1)
        limits.setNumericType("Discrete")
        limits.setUnitType("Availability")

    time = openstudio.Time(0,24)
    secs = time.totalSeconds()
    on   = openstudio.model.ScheduleDay(model, 1)
    off  = openstudio.model.ScheduleDay(model, 0)

    # Seasonal availability start/end dates.
    year = model.yearDescription()

    if not year:
        return oslg.empty("yearDescription", mth, CN.ERR)

    year  = year.get()
    may01 = year.makeDate(openstudio.MonthOfYear("May"),  1)
    oct31 = year.makeDate(openstudio.MonthOfYear("Oct"), 31)

    if oslg.trim(avl).lower() == "winter":
        # available from November 1 to April 30 (6 months)
        val = 1
        sch = off
        nom = "WINTER Availability SchedRuleset"
        dft = "WINTER Availability dftDaySched"
        tag = "May-Oct WINTER Availability SchedRule"
        day = "May-Oct WINTER SchedRule Day"
    elif oslg.trim(avl).lower() == "summer":
        # available from May 1 to October 31 (6 months)
        val = 0
        sch = on
        nom = "SUMMER Availability SchedRuleset"
        dft = "SUMMER Availability dftDaySched"
        tag = "May-Oct SUMMER Availability SchedRule"
        day = "May-Oct SUMMER SchedRule Day"
    elif oslg.trim(avl).lower() == "off":
        # never available
        val = 0
        sch = on
        nom = "OFF Availability SchedRuleset"
        dft = "OFF Availability dftDaySched"
        tag = ""
        day = ""
    else:
        # always available
        val = 1
        sch = on
        nom = "ON Availability SchedRuleset"
        dft = "ON Availability dftDaySched"
        tag = ""
        day = ""

    # Fetch existing schedule.
    ok = True
    schedule = model.getScheduleByName(nom)

    if schedule:
        schedule = schedule.get().to_ScheduleRuleset()

        if schedule:
            schedule = schedule.get()
            default  = schedule.defaultDaySchedule()
            ok = ok and default.nameString()           == dft
            ok = ok and len(default.times())           == 1
            ok = ok and len(default.values())          == 1
            ok = ok and default.times()[0]          == time
            ok = ok and default.values()[0]         == val
            rules = schedule.scheduleRules()
            ok = ok and len(rules) < 2

            if len(rules) == 1:
                rule = rules[0]
                ok = ok and rule.nameString()            == tag
                ok = ok and rule.startDate()
                ok = ok and rule.endDate()
                ok = ok and rule.startDate().get()         == may01
                ok = ok and rule.endDate().get()           == oct31
                ok = ok and rule.applyAllDays()

                d = rule.daySchedule()
                ok = ok and d.nameString()               == day
                ok = ok and len(d.times())              == 1
                ok = ok and len(d.values())              == 1
                ok = ok and d.times()[0].totalSeconds() == secs
                ok = ok and int(d.values()[0])       != val

        if ok: return schedule

    schedule = openstudio.model.ScheduleRuleset(model)
    schedule.setName(nom)

    if not schedule.setScheduleTypeLimits(limits):
        oslg.log(ERR, "'%s': Can't set schedule type limits (%s)" % (nom, mth))
        return nil

    if not schedule.defaultDaySchedule().addValue(time, val):
        oslg.log(ERR, "'%s': Can't set default day schedule (%s)" % (nom, mth))
        return None

    schedule.defaultDaySchedule().setName(dft)

    if tag:
        rule = openstudio.model.ScheduleRule(schedule, sch)
        rule.setName(tag)

        if not rule.setStartDate(may01):
            oslg.log(ERR, "'%s': Can't set start date (%s)" % (tag, mth))
            return None

        if not rule.setEndDate(oct31):
            oslg.log(ERR, "'%s': Can't set end date (%s)" % (tag, mth))
            return None

        if not rule.setApplyAllDays(True):
            oslg.log(ERR, "'%s': Can't apply to all days (%s)" % (tag, mth))
            return None

        rule.daySchedule().setName(day)

    return schedule


def transforms(group=None) -> dict:
    """"Returns OpenStudio site/space transformation & rotation angle.

    Args:
        group:
            A site or space PlanarSurfaceGroup object.

    Returns:
        A transformation + rotation dictionary:
        - t (openstudio.Transformation): site/space transformation.
          None: if invalid inputs (see logs).
        - r (float): Site/space rotation angle [0,2PI) radians.
          None: if invalid inputs (see logs).

    """
    mth = "osut.transforms"
    res = dict(t=None, r=None)
    cl  = openstudio.model.PlanarSurfaceGroup

    if not isinstance(group, cl):
        return oslg.mismatch("group", group, cl, mth, CN.DBG, res)

    mdl = group.model()

    res["t"] = group.siteTransformation()
    res["r"] = group.directionofRelativeNorth() + mdl.getBuilding().northAxis()

    return res


def trueNormal(s=None, r=0):
    """Returns the site/true outward normal vector of a surface.

    Args:
        s (OpenStudio::Model::PlanarSurface):
            An OpenStudio Planar Surface.
        r (float):
            a group/site rotation angle [0,2PI) radians

    Returns:
        openstudio.Vector3d: A surface's true normal vector.
        None: If invalid input (see logs).

    """
    mth = "osut.trueNormal"
    cl  = openstudio.model.PlanarSurface

    if not isinstance(s, cl):
        return oslg.mismatch("surface", s, cl, mth)

    try:
        r = float(r)
    except:
        return oslg.mismatch("rotation", r, float, mth)

    r = float(-r) * math.pi / 180.0

    vx = s.outwardNormal().x * math.cos(r) - s.outwardNormal().y * math.sin(r)
    vy = s.outwardNormal().x * math.sin(r) + s.outwardNormal().y * math.cos(r)
    vz = s.outwardNormal().z

    return openstudio.Point3d(vx, vy, vz) - openstudio.Point3d(0, 0, 0)


def scalar(v=None, mag=0) -> openstudio.Vector3d:
    """Returns scalar product of an OpenStudio Vector3d.

    Args:
        v (OpenStudio::Vector3d):
            An OpenStudio vector.
        m (float):
            A scalar.

    Returns:
        (openstudio.Vector3d) scaled points (see logs if (0,0,0)).

    """
    mth = "osut.scalar"
    cl  = openstudio.Vector3d
    v0  = openstudio.Vector3d()

    if not isinstance(v, cl):
        return oslg.mismatch("vector", v, cl, mth, CN.DBG, v0)

    try:
        mag = float(mag)
    except:
        return oslg.mismatch("scalar", mag, float, mth, CN.DBG, v0)

    v0 = openstudio.Vector3d(mag * v.x(), mag * v.y(), mag * v.z())

    return v0


def p3Dv(pts=None) -> openstudio.Point3dVector:
    """Returns OpenStudio 3D points as an OpenStudio point vector, validating
    points in the process.

    Args:
        pts (list): OpenStudio 3D points.

    Returns:
        openstudio.Point3dVector: Vector of 3D points (see logs if empty).

    """
    mth = "osut.p3Dv"
    cl  = openstudio.Point3d
    v   = openstudio.Point3dVector()

    if isinstance(pts, cl):
        v.append(pts)
        return v
    elif isinstance(pts, openstudio.Point3dVector):
        return pts
    elif isinstance(pts, openstudio.model.PlanarSurface):
        pts = list(pts.vertices())

    try:
        pts = list(pts)
    except:
        return oslg.mismatch("points", pts, list, mth, CN.DBG, v)

    for pt in pts:
        if not isinstance(pt, cl):
            return oslg.mismatch("point", pt, cl, mth, CN.DBG, v)

    for pt in pts:
        v.append(openstudio.Point3d(pt.x(), pt.y(), pt.z()))

    return v


def areSame(s1=None, s2=None, indexed=True) -> bool:
    """Returns True if 2 sets of OpenStudio 3D points are nearly equal.

    Args:
        s1:
            1st set of OpenStudio 3D points
        s2:
            2nd set of OpenStudio 3D points
        indexed (bool):
            whether to attempt to harmonize vertex sequence

    Returns:
        bool: Whether sets are nearly equal (within TOL).
        False: If invalid input (see logs).

    """
    s1 = list(p3Dv(s1))
    s2 = list(p3Dv(s2))
    if not s1: return False
    if not s2: return False
    if len(s1) != len(s2): return False
    if not isinstance(indexed, bool): indexed = True

    if indexed:
        if len(s1) == 1:
            if abs(s1[0].x() - s2[0].x()) > CN.TOL: return False
            if abs(s1[0].y() - s2[0].y()) > CN.TOL: return False
            if abs(s1[0].z() - s2[0].z()) > CN.TOL: return False
        else:
            indx = None

            for i, pt in enumerate(s2):
                if indx: break

                if abs(s1[0].x() - s2[i].x()) > CN.TOL: continue
                if abs(s1[0].y() - s2[i].y()) > CN.TOL: continue
                if abs(s1[0].z() - s2[i].z()) > CN.TOL: continue

                indx = i

            if indx is None: return False

            s2 = collections.deque(s2)
            s2.rotate(-indx)
            s2 = list(s2)

    # openstudio.isAlmostEqual3dPt(p1, p2, TOL) # ... from v350 onwards.
    for i in range(len(s1)):
        if abs(s1[i].x() - s2[i].x()) > CN.TOL: return False
        if abs(s1[i].y() - s2[i].y()) > CN.TOL: return False
        if abs(s1[i].z() - s2[i].z()) > CN.TOL: return False

    return True


def holds(pts=None, p1=None) -> bool:
    """Returns True if an OpenStudio 3D point is part of a set of 3D points.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.
        p1 (openstudio.Point3d):
            An OpenStudio 3D point.

    Returns:
        bool: Whether part of a set of 3D points.
        False: If invalid inputs (see logs).

    """
    mth = "osut.holds"
    pts = p3Dv(pts)
    cl  = openstudio.Point3d

    if not isinstance(p1, cl):
        return oslg.mismatch("point", p1, cl, mth, CN.DBG, False)

    for pt in pts:
        if areSame(p1, pt): return True

    return False


def nearest(pts=None, p01=None):
    """Returns the vector index of an OpenStudio 3D point nearest to a point of
    reference, e.g. grid origin. If left unspecified, the method systematically
    returns the bottom-left corner (BLC) of any horizontal set. If more than
    one point fits the initial criteria, the method relies on deterministic
    sorting through triangulation.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.
        p1 (openstudio.Point3d):
            An OpenStudio 3D point of reference.

    Returns:
        int: Vector index of nearest point to point of reference.
        None: If invalid input (see logs).

    """
    mth = "osut.nearest"
    l   = 100
    d01 = 10000
    d02 = 0
    d03 = 0
    idx = None
    pts = p3Dv(pts)
    if not pts: return idx

    p03 = openstudio.Point3d( l,-l,-l)
    p02 = openstudio.Point3d( l, l, l)

    if not p01: p01 = openstudio.Point3d(-l,-l,-l)

    if not isinstance(p01, openstudio.Point3d):
        return oslg.mismatch("point", p01, cl, mth)

    for i, pt in enumerate(pts):
        if areSame(pt, p01): return i

    for i, pt in enumerate(pts):
        length01 = (pt - p01).length()
        length02 = (pt - p02).length()
        length03 = (pt - p03).length()

        if round(length01, 2) == round(d01, 2):
            if round(length02, 2) == round(d02, 2):
                if round(length03, 2) > round(d03, 2):
                    idx = i
                    d03 = length03
            elif round(length02, 2) > round(d02, 2):
                idx = i
                d03 = length03
                d02 = length02
        elif round(length01, 2) < round(d01, 2):
            idx = i
            d01 = length01
            d02 = length02
            d03 = length03

    return idx


def farthest(pts=None, p01=None):
    """Returns the vector index of an OpenStudio 3D point farthest from a point
    of reference, e.g. grid origin. If left unspecified, the method
    systematically returns the top-right corner (TRC) of any horizontal set. If
    more than one point fits the initial criteria, the method relies on
    deterministic sorting through triangulation.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.
        p1 (openstudio.Point3d):
            An OpenStudio 3D point of reference.

    Returns:
        int: Vector index of farthest point from point of reference.
        None: If invalid input (see logs).

    """
    mth = "osut.farthest"
    l   = 100
    d01 = 0
    d02 = 10000
    d03 = 10000
    idx = None
    pts = p3Dv(pts)
    if not pts: return idx

    p03 = openstudio.Point3d( l,-l,-l)
    p02 = openstudio.Point3d( l, l, l)

    if not p01: p01 = openstudio.Point3d(-l,-l,-l)

    if not isinstance(p01, openstudio.Point3d):
        return oslg.mismatch("point", p01, cl, mth)

    for i, pt in enumerate(pts):
        if areSame(pt, p01): continue

        length01 = (pt - p01).length()
        length02 = (pt - p02).length()
        length03 = (pt - p03).length()

        if round(length01, 2) == round(d01, 2):
            if round(length02, 2) == round(d02, 2):
                if round(length03, 2) < round(d03, 2):
                    idx = i
                    d03 = length03
            elif round(length02, 2) < round(d02, 2):
                idx = i
                d03 = length03
                d02 = length02
        elif round(length01, 2) > round(d01, 2):
            idx = i
            d01 = length01
            d02 = length02
            d03 = length03

    return idx


def flatten(pts=None, axs="z", val=0) -> openstudio.Point3dVector:
    """Flattens OpenStudio 3D points vs X, Y or Z axes.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.
        axs (str):
            Selected "x", "y" or "z" axis.
        val (float):
            Axis value.

    Returns:
        openstudio.Point3dVector: flattened points (see logs if empty)
    """
    mth = "osut.flatten"
    pts = p3Dv(pts)
    v   = openstudio.Point3dVector()

    try:
        val = float(val)
    except:
        return oslg.mismatch("val", val, float, mth, CN.DBG, v)

    try:
        axs = str(axs)
    except:
        return oslg.mismatch("axis (XYZ?)", axs, str, mth, CN.DBG, v)

    if axs.lower() == "x":
        for pt in pts: v.append(openstudio.Point3d(val, pt.y(), pt.z()))
    elif axs.lower() == "y":
        for pt in pts: v.append(openstudio.Point3d(pt.x(), val, pt.z()))
    elif axs.lower() == "z":
        for pt in pts: v.append(openstudio.Point3d(pt.x(), pt.y(), val))
    else:
        return oslg.invalid("axis (XYZ?)", mth, 2, CN.DBG, v)

    return v


def shareXYZ(pts=None, axs="z", val=0) -> bool:
    """Validates whether 3D points share X, Y or Z coordinates.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.
        axs (str):
            Selected "x", "y" or "z" axis.
        val (float):
            Axis value.

    Returns:
        bool: If points share X, Y or Z coordinates.
        False: If invalid inputs (see logs).

    """
    mth = "osut.shareXYZ"
    pts = p3Dv(pts)
    if not pts: return False

    try:
        val = float(val)
    except:
        return oslg.mismatch("val", val, float, mth, CN.DBG, False)

    try:
        axs = str(axs)
    except:
        return oslg.mismatch("axis (XYZ?)", axs, str, mth, CN.DBG, False)

    if axs.lower() == "x":
        for pt in pts:
            if abs(pt.x() - val) > CN.TOL: return False
    elif axs.lower() == "y":
        for pt in pts:
            if abs(pt.y() - val) > CN.TOL: return False
    elif axs.lower() == "z":
        for pt in pts:
            if abs(pt.z() - val) > CN.TOL: return False
    else:
        return invalid("axis", mth, 2, CN.DBG, False)

    return True


def nextUp(pts=None, pt=None):
    """Returns next sequential point in an OpenStudio 3D point vector.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.
        p1 (openstudio.Point3d):
            An OpenStudio 3D point of reference.

    Returns:
        openstudio.Point3d: The next sequential 3D point.
        None: If invalid inputs (see logs).

    """
    mth = "osut.nextUP"
    pts = p3Dv(pts)
    cl  = openstudio.Point3d

    if not isinstance(pt, cl):
        return oslg.mismatch("point", pt, cl, mth)

    if len(pts) < 2:
        return oslg.invalid("points (2+)", mth, 1, CN.WRN)

    for pair in each_cons(pts, 2):
        if areSame(pair[0], pt): return pair[-1]

    return pts[0]


def width(pts=None) -> float:
    """Returns 'width' of a set of OpenStudio 3D points.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.

    Returns:
        float: 'Width' along X-axis.
        0.0: If invalid input (see logs).
    """
    pts = p3Dv(pts)
    if len(pts) < 2: return 0

    xs = [pt.x() for pt in pts]

    return max(xs) - min(xs)


def height(pts=None) -> float:
    """Returns 'height' of a set of OpenStudio 3D points.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.

    Returns:
        float: 'Height' along Z-axis, or Y-axis if points are flat.
        0.0: If invalid input (see logs).
    """
    pts = p3Dv(pts)
    if len(pts) < 2: return 0

    zs = [pt.z() for pt in pts]
    ys = [pt.y() for pt in pts]
    dz = max(zs) - min(zs)
    dy = max(ys) - min(ys)

    if abs(dz) > CN.TOL: return dz

    return dy


def midpoint(p1=None, p2=None):
    """Returns midpoint coordinates of a line segment.

    Args:
        p1 (openstudio.Point3d):
            1st 3D point of a line segment.
        p2 (openstudio.Point3d):
            2nd 3D point of a line segment.

    Returns:
        openstudio.Point3d: Midpoint.
        None: If invalid input (see logs).

    """
    mth = "osut.midpoint"
    cl  = openstudio.Point3d

    if not isinstance(p1, cl):
        return oslg.mismatch("point 1", p1, cl, mth)
    if not isinstance(p2, cl):
        return oslg.mismatch("point 2", p1, cl, mth)
    if areSame(p1, p2):
        return oslg.invalid("same points", mth)

    midX = p1.x() + (p2.x() - p1.x())/2
    midY = p1.y() + (p2.y() - p1.y())/2
    midZ = p1.z() + (p2.z() - p1.z())/2

    return openstudio.Point3d(midX, midY, midZ)


def verticalPlane(p1=None, p2=None):
    """Returns a vertical 3D plane from 2x 3D points, right-hand rule. Input
    points are considered last 2 (of 3) points forming the plane; the first
    point is assumed zenithal. Input points cannot align vertically.

    Args:
        p1 (openstudio.Point3d):
            1st 3D point of a line segment.
        p2 (openstudio.Point3d):
            2nd 3D point of a line segment.

    Returns:
        openstudio.Plane: A vertical 3D plane.
        None: If invalid inputs.

    """
    mth = "osut.verticalPlane"
    cl = openstudio.Point3d

    if not isinstance(p1, cl):
        return oslg.mismatch("point 1", p1, cl, mth)
    if not isinstance(p2, cl):
        return oslg.mismatch("point 2", p1, cl, mth)
    if areSame(p1, p2):
        return oslg.invalid("same points", mth)

    if abs(p1.x() - p2.x()) < CN.TOL and abs(p1.y() - p2.y()) < CN.TOL:
        return oslg.invalid("vertically aligned points", mth)

    zenith = openstudio.Point3d(p1.x(), p1.y(), (p2 - p1).length())
    points = openstudio.Point3dVector()
    points.append(zenith)
    points.append(p1)
    points.append(p2)

    return openstudio.Plane(points)


def uniques(pts=None, n=0) -> openstudio.Point3dVector:
    """Returns unique OpenStudio 3D points from an OpenStudio 3D point vector.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.
        n (int):
            Requested number of unique points (0 returns all).

    Returns:
        openstudio.Point3dVector: Unique points (see logs if empty).

    """
    mth = "osut.uniques"
    pts = p3Dv(pts)
    v   = openstudio.Point3dVector()
    if not pts: return v

    try:
        n = int(n)
    except:
        return oslg.mismatch("n unique points", n, int, mth, CN.DBG, v)

    for pt in pts:
        if not holds(v, pt): v.append(pt)

    if abs(n) > len(v): n = 0
    if n > 0: v = v[0:n]
    if n < 0: v = v[n:]

    return v


def segments(pts=None) -> openstudio.Point3dVectorVector:
    """Returns paired sequential points as (non-zero length) line segments
    (similar to tuple pairs). If the set holds only 2x unique points, a single
    segment is returned. Otherwise, the returned number of segments equals the
    number of unique points.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.

    Returns:
        openstudio.Point3dVectorVector: 3D point segments (see logs if empty).

    """
    mth = "osut.segments"
    vv  = openstudio.Point3dVectorVector()
    pts = uniques(pts)
    if len(pts) < 2: return vv

    for i1, p1 in enumerate(pts):
        i2 = i1 + 1
        if i2 == len(pts): i2 = 0
        p2 = pts[i2]

        line = openstudio.Point3dVector()
        line.append(p1)
        line.append(p2)
        vv.append(line)
        if len(pts) == 2: break

    return vv


def isSegment(pts=None) -> bool:
    """Determines if a set of 3D points if a valid segment.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.

    Returns:
        bool: Whether set is a valid segment.
        False: If invalid input (see logs).

    """
    pts = p3Dv(pts)
    if len(pts) != 2: return False
    if areSame(pts[0], pts[1]): return False

    return True


def triads(pts=None, co=False) -> openstudio.Point3dVectorVector:
    """Returns points as (non-zero length) 'triads', i.e. 3x sequential points.
    If the set holds less than 3x unique points, an empty triad is returned.
    Otherwise, the returned number of triads equals the number of unique points.
    If non-collinearity is requested, then the number of returned triads equals
    the number of non-collinear points.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.

    Returns:
        openStudio.Point3dVectorVector: 3D point triads (see logs if empty).

    """
    vv  = openstudio.Point3dVectorVector()
    pts = uniques(pts)
    if len(pts) < 2: return vv

    for i1, p1 in enumerate(pts):
        i2 = i1 + 1
        if i2 == len(pts): i2 = 0

        i3 = i2 + 1
        if i3 == len(pts): i3 = 0

        p2 = pts[i2]
        p3 = pts[i3]

        tri = openstudio.Point3dVector()
        tri.append(p1)
        tri.append(p2)
        tri.append(p3)
        vv.append(tri)

    return vv


def isTriad(pts=None) -> bool:
    """Determines if a set of 3D points if a valid 'triad'.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.

    Returns:
        bool: Whether set is a valid 'triad', i.e. trio of sequential 3D points.
        False: If invalid input (see logs).

    """
    pts = p3Dv(pts)
    if len(pts) != 3: return False
    if areSame(pts[0], pts[1]): return False
    if areSame(pts[0], pts[2]): return False
    if areSame(pts[1], pts[2]): return False

    return True


def isPointAlongSegment(p0=None, sg=[]) -> bool:
    """Validates whether a 3D point lies ~along a 3D point segment, i.e. less
    than 10mm from any segment.

    Args:
        p0 (openstudio.Point3d):
            A 3D point.
        sg (openstudio.Point3dVector):
            A 3D point segment.

    Returns:
        bool: Whether a 3D point lies ~along a 3D point segment.
        False: If invalid inputs.

    """
    mth = "osut.isPointAlongSegment"
    cl1 = openstudio.Point3d
    cl2 = openstudio.Point3dVector

    if not isinstance(p0, cl1):
        return oslg.mismatch("point", p0, cl1, mth, CN.DBG, False)
    if not isSegment(sg):
        return oslg.mismatch("segment", sg, cl2, mth, CN.DBG, False)

    if holds(sg, p0): return True

    a   = sg[0]
    b   = sg[-1]
    ab  = b - a
    abn = b - a
    abn.normalize()
    ap  = p0 - a
    sp = ap.dot(abn)
    if sp < 0: return False

    apd = scalar(abn, sp)
    if apd.length() > ab.length() + CN.TOL: return False

    ap0 = a + apd
    if round((p0 - ap0).length(), 2) <= CN.TOL: return True

    return False


def isPointAlongSegments(p0=None, sgs=[]) -> bool:
    """Validates whether a 3D point lies anywhere ~along a set of 3D point
    segments, i.e. less than 10mm from any segment.

    Args:
        p0 (openstudio.Point3d):
            A 3D point.
        sgs (openstudio.Point3dVectorVector):
            3D point segments.

    Returns:
        bool: Whether a 3D point lies ~along a set of 3D point segments.
        False: If invalid inputs (see logs).

    """
    mth = "osut.isPointAlongSegments"
    cl1 = openstudio.Point3d
    cl2 = openstudio.Point3dVectorVector

    if not isinstance(sgs, cl2):
        sgs = segments(sgs)
    if not sgs:
        return oslg.empty("segments", mth, CN.DBG, False)
    if not isinstance(p0, cl1):
        return oslg.mismatch("point", p0, cl, mth, CN.DBG, False)

    for sg in sgs:
        if isPointAlongSegment(p0, sg): return True

    return False


def lineIntersection(s1=[], s2=[]):
    """Returns point of intersection of 2x 3D line segments.

    Args:
        s1 (openstudio.Point3dVectorVector):
            1st 3D line segment.
        s2 (openstudio.Point3dVectorVector):
            2nd 3D line segment.

    Returns:
        openStudio.Point3d: Point of intersection of both lines.
        None: If no intersection, or invalid input (see logs).

    """
    s1 = segments(s1)
    s2 = segments(s2)
    if not s1: return None
    if not s2: return None

    s1 = s1[0]
    s2 = s2[0]

    # Matching segments?
    s2x = list(s2)
    s2x.reverse()
    if areSame(s1, s2x): return None
    if areSame(s1, s2) : return None

    a1 = s1[0]
    a2 = s1[1]
    b1 = s2[0]
    b2 = s2[1]

    # Matching segment endpoints?
    if areSame(a1, b1): return a1
    if areSame(a2, b1): return a2
    if areSame(a1, b2): return a1
    if areSame(a2, b2): return a2

    # Segment endpoint along opposite segment?
    if isPointAlongSegment(a1, s2): return a1
    if isPointAlongSegment(a2, s2): return a2
    if isPointAlongSegment(b1, s1): return b1
    if isPointAlongSegment(b2, s1): return b2

    # Line segments as vectors. Skip if collinear or parallel.
    a   = a2 - a1
    b   = b2 - b1
    xab = a.cross(b)
    if round(xab.length(), 4) < CN.TOL2: return None

    # Link 1st point to other segment endpoints as vectors. Must be coplanar.
    a1b1  = b1 - a1
    a1b2  = b2 - a1
    xa1b1 = a.cross(a1b1)
    xa1b2 = a.cross(a1b2)
    xa1b1.normalize()
    xa1b2.normalize()
    xab.normalize()
    if round(xab.cross(xa1b1).length(), 4) > CN.TOL2: return None
    if round(xab.cross(xa1b2).length(), 4) > CN.TOL2: return None

    # Reset.
    xa1b1 = a.cross(a1b1)
    xa1b2 = a.cross(a1b2)

    if xa1b1.length() < CN.TOL2:
        if isPointAlongSegment(a1, [a2, b1]): return None
        if isPointAlongSegment(a2, [a1, b1]): return None

    if xa1b2.length() < CN.TOL2:
        if isPointAlongSegment(a1, [a2, b2]): return None
        if isPointAlongSegment(a2, [a1, b2]): return None

    # Both segment endpoints can't be 'behind' point.
    if a.dot(a1b1) < 0 and a.dot(a1b2) < 0: return None

    # Both in 'front' of point? Pick farthest from 'a'.
    if a.dot(a1b1) > 0 and a.dot(a1b2) > 0:
        lxa1b1 = xa1b1.length()
        lxa1b2 = xa1b2.length()

        c1 = b1 if round(lxa1b1, 4) < round(lxa1b2, 4) else b2
    else:
        c1 = b1 if a.dot(a1b1) > 0 else b2

    c1a1  = a1 - c1
    xc1a1 = a.cross(c1a1)
    d1    = a1 + xc1a1
    n     = a.cross(xc1a1)
    dot   = b.dot(n)
    if dot < 0: n = n.reverseVector()
    if abs(b.dot(n)) < CN.TOL: return None
    f     = c1a1.dot(n) / b.dot(n)
    p0    = c1 + scalar(b, f)

    # Intersection can't be 'behind' point.
    if a.dot(p0 - a1) < 0: return None

    # Ensure intersection is sandwiched between endpoints.
    if not isPointAlongSegment(p0, s2): return None
    if not isPointAlongSegment(p0, s1): return None

    return p0


def doesLineIntersect(l=[], s=[]) -> bool:
    """Validates whether a 3D line segment intersects 3D segments, e.g. polygon.

    Args:
        l (openstudio.Point3dVector):
            A 3D line segment.
        s (openstudio.Point3dVector):
            3D segments.

    Returns:
        bool: Whether a 3D line intersects 3D segments.
        False: If invalid input (see logs).

    """
    l = segments(l)
    s = segments(s)
    if not l: return None
    if not s: return None

    l = l[0]

    for segment in s:
        if lineIntersection(l, segment): return True

    return False


def isClockwise(pts=None) -> bool:
    """Validates whether OpenStudio 3D points are listed clockwise, assuming
    points have been pre-'aligned' - not just flattened along XY (i.e. Z = 0).

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of pre-aligned 3D points.

    Returns:
        bool: Whether sequence is clockwise.
        False: If invalid input (see logs).

    """
    mth = "osut.isClockwise"
    pts = p3Dv(pts)

    if len(pts) < 3:
        return oslg.invalid("3+ points", mth, 1, CN.DBG, False)
    if not shareXYZ(pts, "z"):
        return oslg.invalid("flat points", mth, 1, CN.DBG, False)

    n = openstudio.getOutwardNormal(pts)

    if not n:
        return invalid("polygon", mth, 1, CN.DBG, False)
    elif n.get().z() > 0:
        return False

    return True


def ulc(pts=None) -> openstudio.Point3dVector:
    """Returns OpenStudio 3D points (min 3x) conforming to an UpperLeftCorner
    (ULC) convention. Points Z-axis values must be ~= 0. Points are returned
    counterclockwise.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of pre-aligned 3D points.

    Returns:
        openstudio.Point3dVector: ULC points (see logs if empty).
    """
    mth = "osut.ulc"
    v   = openstudio.Point3dVector()
    pts = list(p3Dv(pts))

    if len(pts) < 3:
        return oslg.invalid("points (3+)", mth, 1, CN.DBG, v)
    if not shareXYZ(pts, "z"):
        return oslg.invalid("points (aligned)", mth, 1, CN.DBG, v)

    # Ensure counterclockwise sequence.
    if isClockwise(pts): pts.reverse()

    minX = min([pt.x() for pt in pts])
    i0   = nearest(pts)
    p0   = pts[i0]

    pts_x = [pt for pt in pts if round(pt.x(), 2) == round(minX, 2)]
    pts_x.reverse()
    p1 = pts_x[0]

    for pt in pts_x:
        if round((pt - p0).length(), 2) > round((p1 - p0).length(), 2): p1 = pt

    i1  = pts.index(p1)
    pts = collections.deque(pts)
    pts.rotate(-i1)

    return p3Dv(list(pts))


def blc(pts=None) -> openstudio.Point3dVector:
    """Returns OpenStudio 3D points (min 3x) conforming to an BottomLeftCorner
    (BLC) convention. Points Z-axis values must be ~= 0. Points are returned
    counterclockwise.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of pre-aligned 3D points.

    Returns:
        openstudio.Point3dVector: BLC points (see logs if empty).
    """
    mth = "osut.blc"
    v   = openstudio.Point3dVector()
    pts = list(p3Dv(pts))

    if len(pts) < 3:
        return oslg.invalid("points (3+)", mth, 1, CN.DBG, v)
    if not shareXYZ(pts, "z"):
        return oslg.invalid("points (aligned)", mth, 1, CN.DBG, v)

    # Ensure counterclockwise sequence.
    if isClockwise(pts): pts.reverse()

    minX = min([pt.x() for pt in pts])
    i0   = nearest(pts)
    p0   = pts[i0]

    pts_x = [pt for pt in pts if round(pt.x(), 2) == round(minX, 2)]
    pts_x.reverse()
    p1 = pts_x[0]

    if p0 in pts_x:
        pts = collections.deque(pts)
        pts.rotate(-i0)
        return p3Dv(list(pts))

    for pt in pts_x:
        if round((pt - p0).length(), 2) < round((p1 - p0).length(), 2): p1 = pt

    i1  = pts.index(p1)
    pts = collections.deque(pts)
    pts.rotate(-i1)

    return p3Dv(list(pts))


def nonCollinears(pts=None, n=0) -> openstudio.Point3dVector:
    """Returns sequential non-collinear points in an OpenStudio 3D point vector.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.
        n (int):
            Requested number of non-collinears (0 returns all).

    Returns:
        openstudio.Point3dVector: non-collinears (see logs if empty).

    """
    mth = "osut.nonCollinears"
    v   = openstudio.Point3dVector()
    a   = []
    pts = uniques(pts)
    if len(pts) < 3: return pts

    try:
        n = int(n)
    except:
        oslg.mismatch("n non-collinears", n, int, mth, CN.DBG, v)

    if n > len(pts):
        return oslg.invalid("+n non-collinears", mth, 0, CN.ERR, v)
    elif n < 0 and abs(n) > len(pts):
        return oslg.invalid("-n non-collinears", mth, 0, CN.ERR, v)

    # Evaluate cross product of vectors of 3x sequential points.
    for i2, p2 in enumerate(pts):
        i1 = i2 - 1
        i3 = i2 + 1
        if i3 == len(pts): i3 = 0
        p1 = pts[i1]
        p3 = pts[i3]

        v13 = p3 - p1
        v12 = p2 - p1
        if v12.cross(v13).length() < CN.TOL2: continue

        a.append(p2)

    if pts[0] in a:
        if not areSame(a[0], pts[0]):
            a = collections.deque(a)
            a.rotate(1)
            a = list(a)

    if n > len(a): return p3Dv(a)
    if n < 0 and abs(n) > len(a): return p3Dv(a)

    if n > 0: a = a[0:n]
    if n < 0: a = a[n:]

    return p3Dv(a)


def collinears(pts=None, n=0) -> openstudio.Point3dVector:
    """
    Returns sequential collinear points in an OpenStudio 3D point vector.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.
        n (int):
            Requested number of collinears (0 returns all).

    Returns:
        openstudio.Point3dVector: collinears (see logs if empty).

    """
    mth = "osut.collinears"
    v   = openstudio.Point3dVector()
    a   = []
    pts = uniques(pts)
    if len(pts) < 3: return pts

    try:
        n = int(n)
    except:
        oslg.mismatch("n collinears", n, int, mth, CN.DBG, v)

    if n > len(pts):
        return oslg.invalid("+n collinears", mth, 0, CN.ERR, v)
    elif n < 0 and abs(n) > len(pts):
        return oslg.invalid("-n collinears", mth, 0, CN.ERR, v)

    ncolls = nonCollinears(pts)
    if not ncolls: return pts

    for pt in pts:
        if pt not in ncolls: a.append(pt)

    if n > len(a): return p3Dv(a)
    if n < 0 and abs(n) > len(a): return p3Dv(a)

    if n > 0: a = a[0:n]
    if n < 0: a = a[n:]

    return p3Dv(a)


def poly(pts=None, vx=False, uq=False, co=False, tt=False, sq="no") -> openstudio.Point3dVector:
    """Returns an OpenStudio 3D point vector as basis for a valid OpenStudio 3D
    polygon. In addition to basic OpenStudio polygon tests (e.g. all points
    sharing the same 3D plane, non-self-intersecting), the method can
    optionally check for convexity, or ensure uniqueness and/or non-collinearity.
    Returned vector can also be 'aligned', as well as in UpperLeftCorner (ULC),
    BottomLeftCorner (BLC), in clockwise (or counterclockwise) sequences.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.
        vx (bool):
            Whether to check for convexity.
        uq (bool):
            Whether to ensure uniqueness.
        co (bool):
            Whether to ensure non-collinearity.
        tt (bool, openstudio.Transformation):
            Whether to 'align'.
        sq ("no", "ulc", "blc", "cw"):
            Unaltered, ULC, BLC or clockwise sequence.

    Returns:
        openstudio.Point3dVector: 3D points (see logs if empty).

    """
    mth = "osut.poly"
    pts = p3Dv(pts)
    cl  = openstudio.Transformation
    v   = openstudio.Point3dVector()
    sqs = ["no", "ulc", "blc", "cw"]
    if not isinstance(vx, bool): vx = False
    if not isinstance(uq, bool): uq = False
    if not isinstance(co, bool): co = False

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Exit if mismatched/invalid arguments.
    if not isinstance(tt, bool) and not isinstance(tt, cl):
        return oslg.invalid("transformation", mth, 5, CN.DBG, v)

    if sq not in sqs:
        return oslg.invalid("sequence", mth, 6, CN.DBG, v)

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Minimum 3 points?
    p3 = nonCollinears(pts, 3)

    if len(p3) < 3:
        return oslg.empty("polygon (non-collinears < 3)", mth, CN.ERR, v)

    # Coplanar?
    pln = openstudio.Plane(p3)

    for pt in pts:
        if not pln.pointOnPlane(pt): return oslg.empty("plane", mth, CN.ERR, v)

    t  = openstudio.Transformation.alignFace(pts)
    at = list(t.inverse() * pts)
    at.reverse()

    if isinstance(tt, cl):
        att = list(tt.inverse() * pts)
        att.reverse()

        if areSame(at, att):
            a = att
            if isClockwise(a): a = list(ulc(a))
            t = None
        else:
            if shareXYZ(att, "z"):
                t = None
            else:
                t = openstudio.Transformation.alignFace(att)

            if t:
                a = list(t.inverse() * att)
                a.reverse()
            else:
                a = att
    else:
        a = at

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Ensure uniqueness and/or non-collinearity. Preserve original sequence.
    p0 = a[0]
    i0 = None
    if uq: a = list(uniques(a))
    if co: a = list(nonCollinears(a))

    i0 = [i for i, pt in enumerate(a) if areSame(pt, p0)]

    if i0:
        i0 = i0[0]
        a  = collections.deque(a)
        a.rotate(-i0)
        a  = list(a)

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Check for convexity (optional).
    if vx and len(a) > 3:
        zen = openstudio.Point3d(0, 0, 1000)

        for trio in triads(a):
            p1  = trio[0]
            p2  = trio[1]
            p3  = trio[2]
            v12 = p2 - p1
            v13 = p3 - p1
            x   = (zen - p1).cross(v12)
            if round(x.dot(v13), 4) > 0: return v

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Alter sequence (optional).
    if sq != "cw": a.reverse()

    if isinstance(tt, cl):
        if sq == "ulc":
            a = p3Dv(t * ulc(a)) if t else p3Dv(ulc(a))
        elif sq == "blc":
            a = p3Dv(t * blc(a)) if t else p3Dv(blc(a))
        elif sq == "cw":
            a = p3Dv(t * a) if t else p3Dv(a)
        else:
            a = p3Dv(t * a) if t else p3Dv(a)
    else:
        if sq == "ulc":
            a = p3Dv(ulc(a)) if tt else p3Dv(t * ulc(a))
        elif sq == "blc":
            a = p3Dv(blc(a)) if tt else p3Dv(t * blc(a))
        elif sq == "cw":
            a = p3Dv(a) if tt else p3Dv(t * a)
        else:
            a = p3Dv(a) if tt else p3Dv(t * a)

    return a


def isPointWithinPolygon(p0=None, s=[], entirely=False) -> bool:
    """Validates whether 3D point is within a 3D polygon. If option 'entirely'
    is set to True, then the method returns False if point lies along any of
    the polygon edges, or is very near any of its vertices.

    Args:
        p0 (openstudio.Point3d):
            a 3D point.
        s (openstudio.Point3dVector):
            A 3D polygon.
        entirely (bool):
            Whether point should be neatly within polygon limits.

    Returns:
        bool: Whether 3D point lies within 3D polygon.
        False: If invalid inputs (see logs).

    """
    mth = "osut.isPointWithinPolygon"
    cl  = openstudio.Point3d

    if not isinstance(p0, cl):
        return oslg.mismatch("point", p0, cl, mth, CN.DBG, False)

    s = poly(s, False, True, True)
    if not s: return oslg.empty("polygon", mth, CN.DBG, False)

    n = openstudio.getOutwardNormal(s)
    if not n: return oslg.invalid("plane/normal", mth, 2, CN.DBG, False)

    n  = n.get()
    pl = openstudio.Plane(s[0], n)
    if not pl.pointOnPlane(p0): return False
    if not isinstance(entirely, bool): entirely = False

    segs = segments(s)

    # Along polygon edges, or near vertices?
    if isPointAlongSegments(p0, segs):
        return False if entirely else True

    for segment in segs:
        # - draw vector from segment midpoint to point
        # - scale 1000x (assuming no building surface would be 1km wide)
        # - convert vector to an independent line segment
        # - loop through polygon segments, tally the number of intersections
        # - avoid double-counting polygon vertices as intersections
        # - return False if number of intersections is even
        mid = midpoint(segment[0], segment[1])
        mpV = scalar(mid - p0, 1000)
        p1  = p0 + mpV
        ctr = 0

        # Skip if ~collinear.
        if round(mpV.cross(segment[1] - segment[0]).length(), 4) < CN.TOL2:
            continue

        for sg in segs:
            intersect = lineIntersection([p0, p1], sg)
            if not intersect: continue

            # Skip test altogether if one of the polygon vertices.
            if holds(s, intersect):
                ctr = 0
                break
            else:
                ctr += 1

        if ctr == 0: continue
        if ctr % 2 == 0: return False # 'even'?

    return True


def areParallel(p1=None, p2=None) -> bool:
    """Validates whether 2 polygons are parallel, regardless of their direction.

    Args:
        p1 (openstudio.Point3dVector):
            1st set of 3D points.
        p2 (openstudio.Point3dVector):
            2nd set of 3D points.

    Returns:
        bool: Whether 2 polygons are parallel.
        False: If invalid inputs.

    """
    p1 = poly(p1, False, True)
    p2 = poly(p2, False, True)
    if not p1: return False
    if not p2: return False

    n1 = openstudio.getOutwardNormal(p1)
    n2 = openstudio.getOutwardNormal(p2)
    if not n1: return False
    if not n2: return False

    return abs(n1.get().dot(n2.get())) > 0.99


def isRoof(pts=None) -> bool:
    """Validates whether a polygon can be considered a valid 'roof' surface, as
    per ASHRAE 90.1 & Canadian NECBs, i.e. outward normal within 60° from
    vertical.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of pre-aligned 3D points.

    Returns:
        bool: If considered a roof surface.
        False: If invalid input (see logs).

    """
    ray = openstudio.Point3d(0,0,1) - openstudio.Point3d(0,0,0)
    dut = math.cos(60 * math.pi / 180)
    pts = poly(pts, False, True, True)
    if not pts: return False

    dot = ray.dot(openstudio.getOutwardNormal(pts).get())
    if round(dot, 2) <= 0: return False
    if round(dot, 2) == 1: return True

    return round(dot, 4) >= round(dut, 4)


def facingUp(pts=None) -> bool:
    """Validates whether a polygon faces upwards, harmonized with OpenStudio
    Utilities' "alignZPrime" function.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.

    Returns:
        bool: If facing upwards.
        False: If invalid inputs (see logs).

    """
    ray = openstudio.Point3d(0,0,1) - openstudio.Point3d(0,0,0)
    pts = poly(pts, False, True, True)
    if not pts : return False

    return openstudio.getOutwardNormal(pts).get().dot(ray) > 0.99


def facingDown(pts=None) -> bool:
    """Validates whether a polygon faces downwards, harmonized with OpenStudio
    Utilities' "alignZPrime" function.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.

    Returns:
        bool: If facing downwards.
        False: If invalid inputs (see logs).

    """
    ray = openstudio.Point3d(0,0,-1) - openstudio.Point3d(0,0,0)
    pts = poly(pts, False, True, True)
    if not pts: return False

    return openstudio.getOutwardNormal(pts).get().dot(ray) > 0.99


def isSloped(pts=None) -> bool:
    """Validates whether a surface can be considered 'sloped' (i.e. not ~flat,
    as per OpenStudio Utilities' "alignZPrime"). Vertical polygons returns True.

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.

    Returns:
        bool: Whether surface is sloped.
        False: If invalid input (see logs).

    """
    pts = poly(pts, False, True, True)
    if not pts: return False
    if facingUp(pts): return False
    if facingDown(pts): return False

    return True


def isRectangular(pts=None) -> bool:
    """Validates whether an OpenStudio polygon is a rectangle (4x sides + 2x
    diagonals of equal length, meeting at midpoints).

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.

    Returns:
        bool: Whether polygon is rectangular.
        False: If invalid input (see logs).

    """
    pts = poly(pts, False, False, False)
    if not pts: return False
    if len(pts) != 4: return False

    m1 = midpoint(pts[0], pts[2])
    m2 = midpoint(pts[1], pts[3])
    if not areSame(m1, m2): return False

    diag1 = pts[2] - pts[0]
    diag2 = pts[3] - pts[1]
    if abs(diag1.length() - diag2.length()) < CN.TOL: return True

    return False


def isSquare(pts=None) -> bool:
    """Validates whether an OpenStudio polygon is a square (rectangular,
    4x ~equal sides).

    Args:
        pts (openstudio.Point3dVector):
            An OpenStudio vector of 3D points.

    Returns:
        bool: Whether polygon is a square.
        False: If invalid input (see logs).

    """
    d   = None
    pts = poly(pts, False, False, False)
    if not pts: return False
    if not isRectangular(pts): return False

    for pt in segments(pts):
        l = (pt[1] - pt[0]).length()
        if not d: d = l
        if round(l, 2) != round(d, 2): return False

    return True


def fits(p1=None, p2=None, entirely=False) -> bool:
    """Determines whether a 1st OpenStudio polygon (p1) fits within a 2nd
    polygon (p2). Vertex sequencing of both polygons must be counterclockwise.
    If option 'entirely' is True, then the method returns False if a 'p1' point
    lies along any of the 'p2' polygon edges, or is very near any of its
    vertices.

    Args:
        p1 (openstudio.Point3d):
            1st OpenStudio vector of 3D points.
        p2 (openstudio.Point3d):
            2nd OpenStudio vector of 3D points.
        entirely (bool):
            Whether point should be neatly within polygon limits.

    Returns:
        bool: Whether 1st polygon fits within the 2nd polygon.
        False: If invalid input (see logs).

    """
    pts = []
    p1  = poly(p1)
    p2  = poly(p2)
    if not p1: return False
    if not p2: return False

    for p0 in p1:
        if not isPointWithinPolygon(p0, p2): return False

    # Although p2 points may lie ALONG p1, none may lie entirely WITHIN p1.
    for p0 in p2:
        if isPointWithinPolygon(p0, p1, True): return False

    # p1 segment mid-points must not lie OUTSIDE of p2.
    for sg in segments(p1):
        mp = midpoint(sg[0], sg[1])
        if not isPointWithinPolygon(mp, p2): return False

    if not isinstance(entirely, bool): entirely = False
    if not entirely: return True

    for p0 in p1:
        if not isPointWithinPolygon(p0, p2, entirely): return False

    return True


def overlap(p1=None, p2=None, flat=False) -> bool:
    """Returns intersection of overlapping polygons, empty if non intersecting.
    If the optional 3rd argument is left as False, the 2nd polygon may only
    overlap if it shares the 3D plane equation of the 1st one. If the 3rd
    argument is instead set to True, then the 2nd polygon is first 'cast' onto
    the 3D plane of the 1st one; the method therefore returns (as overlap) the
    intersection of a 'projection' of the 2nd polygon onto the 1st one. The
    method returns the smallest of the 2 polygons if either fits within the
    larger one.

    Args:
        p1 (openstudio.Point3d):
            1st OpenStudio vector of 3D points.
        p2 (openstudio.Point3d):
            2nd OpenStudio vector of 3D points.
        flat (bool):
             Whether to first project the 2nd set onto the 1st set plane.

    Returns:
        openstudio.Point3dVector: Largest intersection (see logs if empty).

    """
    mth  = "osut.overlap"
    face = openstudio.Point3dVector()
    p01  = poly(p1)
    p02  = poly(p2)
    if not p01: return oslg.empty("points 1", mth, CN.DBG, face)
    if not p02: return oslg.empty("points 2", mth, CN.DBG, face)
    if fits(p01, p02): return p01
    if fits(p02, p01): return p02
    if not isinstance(flat, bool): flat = False

    if shareXYZ(p01, "z"):
        t   = None
        a1  = list(p01)
        a2  = list(p02)
        cw1 = isClockwise(p01)

        if cw1:
            a1.reverse()
            a1 = list(a1)
    else:
        t  = openstudio.Transformation.alignFace(p01)
        a1 = list(t.inverse() * p01)
        a2 = list(t.inverse() * p02)

    if flat: a2 = list(flatten(a2))

    if not shareXYZ(a2, "z"):
        return invalid("points 2", mth, 2, CN.DBG, face)

    cw2 = isClockwise(a2)

    if cw2:
        a2.reverse()
        a2 = list(a2)

    # Return either (transformed) polygon if one fits into the other.
    p02 = list(a2)

    if t:
        if not cw2: p02.reverse()

        p02 = p3Dv(t * p02)
    else:
        if cw1:
            if cw2: p02.reverse()
        else:
            if not cw2: p02.reverse()

        p02 = p3Dv(p02)

    if fits(a1, a2): return p01
    if fits(a2, a1): return p02

    area1 = openstudio.getArea(a1)
    area2 = openstudio.getArea(a2)
    if not area1: return oslg.empty("points 1 area", mth, CN.ERR, face)
    if not area2: return oslg.empty("points 2 area", mth, CN.ERR, face)

    area1 = area1.get()
    area2 = area2.get()
    a1.reverse()
    a2.reverse()

    union = openstudio.join(a1, a2, CN.TOL2)
    if not union: return face

    union = union.get()
    area  = openstudio.getArea(union)
    if not area: return face

    area  = area.get()
    delta = area1 + area2 - area

    if area > CN.TOL:
        if round(area,  2) == round(area1, 2): return face
        if round(area,  2) == round(area1, 2): return face
        if round(delta, 2) == 0:               return face

    res = openstudio.intersect(a1, a2, CN.TOL)
    if not res: return face

    res  = res.get()
    res1 = list(res.polygon1())
    res1.reverse()
    if not res1: return face
    if t: res1 = list(t * res1)

    return p3Dv(res1)


def overlapping(p1=None, p2=None, flat=False) -> bool:
    """Determines whether OpenStudio polygons overlap.

    Args:
        p1 (openstudio.Point3d):
            1st OpenStudio vector of 3D points.
        p2 (openstudio.Point3d):
            2nd OpenStudio vector of 3D points.
        flat (bool):
             Whether to first project the 2nd set onto the 1st set plane.

    Returns:
        bool: Whether polygons overlap (or fit).
        False: If invalid input (see logs).
    """
    if overlap(p1, p2, flat): return True

    return False


def cast(p1=None, p2=None, ray=None) -> openstudio.Point3dVector:
    """Casts an OpenStudio polygon onto the 3D plane of a 2nd polygon, relying
    on an independent 3D ray vector.

    Args:
        p1 (openstudio.Point3dVector):
            1st OpenStudio vector of 3D points.
        p2 (openstudio.Point3dvector):
            2nd OpenStudio vector of 3D points.
        ray (openstudio.Point3d):
            A 3D vector.

    Returns:
        (openstudio.Point3dVector): Cast of p1 onto p2 (see logs if empty).

    """
    mth  = "osut.cast"
    cl   = openstudio.Vector3d
    face = openstudio.Point3dVector()
    p1   = poly(p1)
    p2   = poly(p2)
    if not p1: return face
    if not p2: return face

    if not isinstance(ray, cl):
        return oslg.mismatch("ray", ray, cl, mth, CN.DBG, face)

    # From OpenStudio SDK v3.7.0 onwards, one could/should rely on:
    #
    # s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.7.0-doc/
    # utilities/html/classopenstudio_1_1_plane.html
    # #abc4747b1b041a7f09a6887bc0e5abce1
    #
    #   Example Ruby implementation.
    #   e.g. p1.each { |pt| face << pl.rayIntersection(pt, ray) }
    #
    # The following +/- replicates the same solution, based on:
    #   https://stackoverflow.com/a/65832417
    p0 = p2[0]
    pl = openstudio.Plane(p2)
    n  = pl.outwardNormal()
    if abs(n.dot(ray)) < CN.TOL: return face

    for pt in p1:
        length = n.dot(pt - p0) / n.dot(ray.reverseVector())
        face.append(pt + scalar(ray, length))

    return face


def offset(p1=None, w=0, v=0) -> openstudio.Point3dVector:
    """Generates offset vertices (by width) for a 3- or 4-sided, convex polygon.
    If width is negative, the vertices are contracted inwards.

    Args:
        p1 (openstudio.Point3dVector):
            OpenStudio vector of 3D points.
        w (float):
            Offset width (absolute min: 0.0254m).
        v (int):
            OpenStudio SDK version, eg '321' for "v3.2.1" (optional).

    Returns:
        openstudio.Point3dVector: Offset points (see logs if unaltered).

    """
    mth = "osut.offset"
    vs  = int("".join(openstudio.openStudioVersion().split(".")))
    pts = poly(p1, True, True, False, True, "cw")

    if len(pts) < 3 or len(pts) > 4:
        return oslg.invalid("points", mth, 1, CN.DBG, p1)
    elif len(pts) == 4:
        iv = True
    else:
        iv = False

    try:
        w = float(w)
    except:
        oslg.mismatch("width", w, float, mth)
        w = 0

    try:
        v = int(v)
    except:
        oslg.mismatch("version", v, int, mth)
        v = vs

    if abs(w) < 0.0254: return p1

    if v >= 340:
        t = openstudio.Transformation.alignFace(p1)
        offst = openstudio.buffer(pts, w, CN.TOL)
        if not offst: return p1

        offst = offst.get()
        offst.reverse()
        return p3Dv(list(t * offst))
    else: # brute force approach
        pz      = {}
        pz["A"] = {}
        pz["B"] = {}
        pz["C"] = {}
        if iv:
            pz["D"] = {}

        pz["A"]["p"] = openstudio.Point3d(p1[0].x(), p1[0].y(), p1[0].z())
        pz["B"]["p"] = openstudio.Point3d(p1[1].x(), p1[1].y(), p1[1].z())
        pz["C"]["p"] = openstudio.Point3d(p1[2].x(), p1[2].y(), p1[2].z())
        if iv:
            pz["D"]["p"] = openstudio.Point3d(p1[3].x(), p1[3].y(), p1[3].z())

        pzAp = pz["A"]["p"]
        pzBp = pz["B"]["p"]
        pzCp = pz["C"]["p"]
        if iv:
            pzDp = pz["D"]["p"]

        # Generate vector pairs, from next point & from previous point.
        # :f_n : "from next"
        # :f_p : "from previous"
        #
        #
        #
        #
        #
        #
        #             A <---------- B
        #              ^
        #               \
        #                \
        #                 C (or D)
        #
        pz["A"]["f_n"] = pzAp - pzBp
        if iv:
            pz["A"]["f_p"] = pzAp - pzDp
        else:
            pz["A"]["f_p"] = pzAp - pzCp

        pz["B"]["f_n"] = pzBp - pzCp
        pz["B"]["f_p"] = pzBp - pzAp

        pz["C"]["f_p"] = pzCp - pzBp
        if iv:
            pz["C"]["f_n"] = pzCp - pzDp
        else:
            pz["C"]["f_n"] = pzCp - pzAp

        if iv:
            pz["D"]["f_n"] = pzDp - pzAp
            pz["D"]["f_p"] = pzDp - pzCp

        # Generate 3D plane from vectors.
        #
        #
        #             |  <<< 3D plane ... from point A, with normal B>A
        #             |
        #             |
        #             |
        # <---------- A <---------- B
        #             |\
        #             | \
        #             |  \
        #             |   C (or D)
        #
        pz["A"]["pl_f_n"] = openstudio.Plane(pzAp, pz["A"]["f_n"])
        pz["A"]["pl_f_p"] = openstudio.Plane(pzAp, pz["A"]["f_p"])

        pz["B"]["pl_f_n"] = openstudio.Plane(pzBp, pz["B"]["f_n"])
        pz["B"]["pl_f_p"] = openstudio.Plane(pzBp, pz["B"]["f_p"])

        pz["C"]["pl_f_n"] = openstudio.Plane(pzCp, pz["C"]["f_n"])
        pz["C"]["pl_f_p"] = openstudio.Plane(pzCp, pz["C"]["f_p"])

        if iv:
            pz["D"]["pl_f_n"] = openstudio.Plane(pzDp, pz["D"]["f_n"])
            pz["D"]["pl_f_p"] = openstudio.Plane(pzDp, pz["D"]["f_p"])

        # Project an extended point (pC) unto 3D plane.
        #
        #             pC   <<< projected unto extended B>A 3D plane
        #        eC   |
        #          \  |
        #           \ |
        #            \|
        # <---------- A <---------- B
        #             |\
        #             | \
        #             |  \
        #             |   C (or D)
        #
        pz["A"]["p_n_pl"] = pz["A"]["pl_f_n"].project(pz["A"]["p"] + pz["A"]["f_p"])
        pz["A"]["n_p_pl"] = pz["A"]["pl_f_p"].project(pz["A"]["p"] + pz["A"]["f_n"])

        pz["B"]["p_n_pl"] = pz["B"]["pl_f_n"].project(pz["B"]["p"] + pz["B"]["f_p"])
        pz["B"]["n_p_pl"] = pz["B"]["pl_f_p"].project(pz["B"]["p"] + pz["B"]["f_n"])

        pz["C"]["p_n_pl"] = pz["C"]["pl_f_n"].project(pz["C"]["p"] + pz["C"]["f_p"])
        pz["C"]["n_p_pl"] = pz["C"]["pl_f_p"].project(pz["C"]["p"] + pz["C"]["f_n"])

        if iv:
            pz["D"]["p_n_pl"] = pz["D"]["pl_f_n"].project(pz["D"]["p"] + pz["D"]["f_p"])
            pz["D"]["n_p_pl"] = pz["D"]["pl_f_p"].project(pz["D"]["p"] + pz["D"]["f_n"])

        # Generate vector from point (e.g. A) to projected extended point (pC).
        #
        #             pC
        #        eC   ^
        #          \  |
        #           \ |
        #            \|
        # <---------- A <---------- B
        #             |\
        #             | \
        #             |  \
        #             |   C (or D)
        #
        pz["A"]["n_p_n_pl"] = pz["A"]["p_n_pl"] - pzAp
        pz["A"]["n_n_p_pl"] = pz["A"]["n_p_pl"] - pzAp

        pz["B"]["n_p_n_pl"] = pz["B"]["p_n_pl"] - pzBp
        pz["B"]["n_n_p_pl"] = pz["B"]["n_p_pl"] - pzBp

        pz["C"]["n_p_n_pl"] = pz["C"]["p_n_pl"] - pzCp
        pz["C"]["n_n_p_pl"] = pz["C"]["n_p_pl"] - pzCp

        if iv:
            pz["D"]["n_p_n_pl"] = pz["D"]["p_n_pl"] - pzDp
            pz["D"]["n_n_p_pl"] = pz["D"]["n_p_pl"] - pzDp

        # Fetch angle between both extended vectors (A>pC & A>pB),
        # ... then normalize (Cn).
        #
        #             pC
        #        eC   ^
        #          \  |
        #           \ Cn
        #            \|
        # <---------- A <---------- B
        #             |\
        #             | \
        #             |  \
        #             |   C (or D)
        #
        a1 = openstudio.getAngle(pz["A"]["n_p_n_pl"], pz["A"]["n_n_p_pl"])
        a2 = openstudio.getAngle(pz["B"]["n_p_n_pl"], pz["B"]["n_n_p_pl"])
        a3 = openstudio.getAngle(pz["C"]["n_p_n_pl"], pz["C"]["n_n_p_pl"])
        if iv:
            a4 = openstudio.getAngle(pz["D"]["n_p_n_pl"], pz["D"]["n_n_p_pl"])

        # Generate new 3D points A', B', C' (and D') ... zigzag.
        #
        #
        #
        #
        #     A' ---------------------- B'
        #      \
        #       \      A <---------- B
        #        \      \
        #         \      \
        #          \      \
        #           C'      C
        pz["A"]["f_n"].normalize()
        pz["A"]["n_p_n_pl"].normalize()
        pzAp = pzAp + scalar(pz["A"]["n_p_n_pl"], w)
        pzAp = pzAp + scalar(pz["A"]["f_n"], w * math.tan(a1/2))

        pz["B"]["f_n"].normalize()
        pz["B"]["n_p_n_pl"].normalize()
        pzBp = pzBp + scalar(pz["B"]["n_p_n_pl"], w)
        pzBp = pzBp + scalar(pz["B"]["f_n"], w * math.tan(a2/2))

        pz["C"]["f_n"].normalize()
        pz["C"]["n_p_n_pl"].normalize()
        pzCp = pzCp + scalar(pz["C"]["n_p_n_pl"], w)
        pzCp = pzCp + scalar(pz["C"]["f_n"], w * math.tan(a3/2))

        if iv:
            pz["D"]["f_n"].normalize()
            pz["D"]["n_p_n_pl"].normalize()
            pzDp = pzDp + scalar(pz["D"]["n_p_n_pl"], w)
            pzDp = pzDp + scalar(pz["D"]["f_n"], w * math.tan(a4/2))

        # Re-convert to OpenStudio 3D points.
        vec = openstudio.Point3dVector()
        vec.append(openstudio.Point3d(pzAp.x(), pzAp.y(), pzAp.z()))
        vec.append(openstudio.Point3d(pzBp.x(), pzBp.y(), pzBp.z()))
        vec.append(openstudio.Point3d(pzCp.x(), pzCp.y(), pzCp.z()))
        if iv:
            vec.append(openstudio.Point3d(pzDp.x(), pzDp.y(), pzDp.z()))

    return vec


def outline(a=[], bfr=0, flat=True) -> openstudio.Point3dVector:
    """Generates a ULC OpenStudio 3D point vector (a bounding box) that
    surrounds multiple (smaller) OpenStudio 3D point vectors. The generated,
    4-point outline is optionally buffered (or offset). Frame and Divider frame
    widths are taken into account.

    Args:
        a (list):
            One or more sets of OpenStudio 3D points.
        bfr (float):
            An optional buffer size (min: 0.0254m).
        flat (bool):
            Whether points are to be pre-flattened (Z=0).
    Returns:
        openstudio.Point3dVector: ULC outline (see logs if empty).

    """
    mth  = "osut.outline"
    out  = openstudio.Point3dVector()
    xMIN = None
    xMAX = None
    yMIN = None
    yMAX = None
    a2   = []

    try:
        bfr = float(bfr)
        if bfr < 0.0254: bfr = 0
    except:
        oslg.mismatch("buffer", bfr, float, mth)
        bfr = 0

    try:
        flat = bool(flat)
    except:
        flat = True

    try:
        a = list(a)
    except:
        return oslg.mismatch("array", a, list, mth, CN.DBG, out)

    if not a: return oslg.empty("array", mth, CN.DBG, out)

    vtx = poly(a[0])
    if not vtx: return out

    t = openstudio.Transformation.alignFace(vtx)

    for pts in a:
        points = poly(pts, False, True, False, t)
        if flat: points = flatten(points)
        if not points: continue

        a2.append(points)

    for pts in a2:
        xs = [pt.x() for pt in pts]
        ys = [pt.y() for pt in pts]

        minX = min(xs)
        maxX = max(xs)
        minY = min(ys)
        maxY = max(ys)

        # Consider frame width, if frame-and-divider-enabled sub surface.
        if hasattr(pts, "allowWindowPropertyFrameAndDivider"):
            w  = 0
            fd = pts.windowPropertyFrameAndDivider()
            if fd: w = fd.get().frameWidth()

            if w > CN.TOL:
                minX -= w
                maxX += w
                minY -= w
                maxY += w

        if not xMIN: xMIN = minX
        if not xMAX: xMAX = maxX
        if not yMIN: yMIN = minY
        if not yMAX: yMAX = maxY

        xMIN = min(xMIN, minX)
        xMAX = max(xMAX, maxX)
        yMIN = min(yMIN, minY)
        yMAX = max(yMAX, maxY)

    if xMAX < xMIN:
        return oslg.negative("outline width", mth, CN.DBG, out)
    if yMAX < yMIN:
        return oslg.negative("outline height", mth, Cn.DBG, out)
    if abs(xMIN - xMAX) < CN.TOL:
        return oslg.zero("outline width", mth, CN.DBG, out)
    if abs(yMIN - yMAX) < CN.TOL:
        return oslg.zero("outline height", mth, CN.DBG, out)

    # Generate ULC point 3D vector.
    out.append(openstudio.Point3d(xMIN, yMAX, 0))
    out.append(openstudio.Point3d(xMIN, yMIN, 0))
    out.append(openstudio.Point3d(xMAX, yMIN, 0))
    out.append(openstudio.Point3d(xMAX, yMAX, 0))

    # Apply buffer, apply ULC (options).
    if bfr > 0.0254: out = offset(out, bfr, 300)

    return p3Dv(t * out)


def triadBox(pts=None) -> openstudio.Point3dVector:
    """Generates a BLC box from a triad (3D points). Points must be unique and
    non-collinear.

    Args:
        pts (openstudio.Point3dVector):
            A 'triad' - an OpenStudio vector of 3x 3D points.

    Returns:
        openstudio.Point3dVector:
            A rectangular BLC box (see logs if empty).

    """
    mth = "osut.triadBox"
    t   = None
    bkp = openstudio.Point3dVector()
    box = []
    pts = nonCollinears(pts)
    if not pts: return bkp

    if not shareXYZ(pts, "z"):
        t = openstudio.Transformation.alignFace(pts)
        pts = poly(pts, False, True, True, t)
        if not pts: return bkp

    if len(pts) != 3: return oslg.invalid("triad", mth, 1, CN.ERR, bkp)

    if isClockwise(pts):
        pts = list(pts)
        pts.reverse()
        pts = p3Dv(pts)

    p0 = pts[0]
    p1 = pts[1]
    p2 = pts[2]

    # Cast p0 unto vertical plane defined by p1/p2.
    pp0 = verticalPlane(p1, p2).project(p0)
    v00 = p0  - pp0
    v11 = pp0 - p1
    v10 = p0  - p1
    v12 = p2  - p1

    # Reset p0 and/or p1 if obtuse or acute.
    if v12.dot(v10) < 0:
        p0 = p1 + v00
    elif v12.dot(v10) > 0:
        if v11.length() < v12.length():
            p1 = pp0
        else:
            p0 = p1 + v00

    p3 = p2 + v00

    box.append(openstudio.Point3d(p0.x(), p0.y(), p0.z()))
    box.append(openstudio.Point3d(p1.x(), p1.y(), p1.z()))
    box.append(openstudio.Point3d(p2.x(), p2.y(), p2.z()))
    box.append(openstudio.Point3d(p3.x(), p3.y(), p3.z()))

    box = nonCollinears(box, 4)
    if len(box) != 4: return bkp

    box = blc(box)
    if not isRectangular(box): return bkp

    if t: box = p3Dv(t * box)

    return box


def medialBox(pts=None) -> openstudio.Point3dVector:
    """Generates a BLC box bounded within a triangle (midpoint theorem).

    Args:
        pts (openstudio.Point3dVector):
            A triangular polygon.

    Returns:
        openstudio.Point3dVector: A medial bounded box (see logs if empty).
    """
    mth = "osut.medialBox"
    t   = None
    bkp = openstudio.Point3dVector()
    box = []
    pts = poly(pts, True, True, True)
    if not pts: return bkp
    if len(pts) != 3: return oslg.invalid("triangle", mth, 1, CN.ERR, bkp)

    if not shareXYZ(pts, "z"):
        t = openstudio.Transformation.alignFace(pts)
        pts = poly(pts, False, False, False, t)
        if not pts: return bkp

    if isClockwise(pts):
        pts = list(pts)
        pts.reverse()
        pts = p3Dv(pts)

    # Generate vertical plane along longest segment.
    sgs = segments(pts)

    mpoints  = []
    longest  = sgs[0]
    distance = openstudio.getDistanceSquared(longest[0], longest[1])

    for sg in sgs:
        if sg == longest: continue

        d0 = openstudio.getDistanceSquared(sg[0], sg[1])

        if distance < d0:
            distance = d0
            longest  = sg

    plane = verticalPlane(longest[0], longest[1])

    # Fetch midpoints of other 2 segments.
    for sg in sgs:
        if sg != longest: mpoints.append(midpoint(sg[0], sg[1]))

    if len(mpoints) != 2: return bkp

    # Generate medial bounded box.
    box.append(plane.project(mpoints[0]))
    box.append(mpoints[0])
    box.append(mpoints[1])
    box.append(plane.project(mpoints[1]))

    box = list(nonCollinears(box))
    if len(box) != 4: return bkp

    if isClockwise(box): box.reverse()

    box = blc(box)
    if not isRectangular(box): return bkp
    if not fits(box, pts): return bkp

    if t: box = p3Dv(t * box)

    return box


def boundedBox(pts=None) -> openstudio.Point3dVector:
    """Generates a BLC bounded box within a polygon.

    Args:
        pts (openstudio.Point3dVector):
            A set of OpenStudio 3D points.

    Returns:
         openstudio.Point3dVector: A bounded box (see logs if empty).
    """
    # str = ".*(?<!utilities.geometry.join)$"
    # OpenStudio::Logger.instance.standardOutLogger.setChannelRegex(str)

    mth = "osut.boundedBox"
    t   = None
    bkp = openstudio.Point3dVector()
    box = []
    pts = poly(pts, False, True, True)
    if not pts: return bkp

    if not shareXYZ(pts, "Z"):
        t   = openstudio.Transformation.alignFace(pts)
        pts = p3Dv(t.inverse() * pts)
        if not pts: return bkp

    if isClockwise(pts):
        pts = list(pts)
        pts.reverse()
        pts = p3Dv(pts)

    # PATH A : Return medial bounded box if polygon is a triangle.
    if len(pts) == 3:
        box = medialBox(pts)

        if box:
            if t: box = p3Dv(t * box)
            return box

    # PATH B : Return polygon itself if already rectangular.
    if isRectangular(pts):
        box = p3Dv(t * pts) if t else pts
        return box

    aire = 0

    # PATH C : Right-angle, midpoint triad approach.
    for sg in segments(pts):
        m0 = midpoint(sg[0], sg[1])

        for seg in segments(pts):
            p1 = seg[0]
            p2 = seg[1]
            if areSame(p1, sg[0]): continue
            if areSame(p1, sg[1]): continue
            if areSame(p2, sg[0]): continue
            if areSame(p2, sg[1]): continue

            out = triadBox(openstudio.Point3dVector([m0, p1, p2]))
            if not out: continue
            if not fits(out, pts): continue
            if fits(pts, out): continue

            area = openstudio.getArea(out)
            if not area: continue

            area = area.get()
            if area < CN.TOL: continue
            if area < aire: continue

            aire = area
            box  = out

    # PATH D : Right-angle triad approach, may override PATH C boxes.
    for sg in segments(pts):
        p0 = sg[0]
        p1 = sg[1]

        for p2 in pts:
            if areSame(p2, p0): continue
            if areSame(p2, p1): continue

            out = triadBox(openstudio.Point3dVector([p0, p1, p2]))
            if not out: continue
            if not fits(out, pts): continue
            if fits(pts, out): continue

            area = openstudio.getArea(out)
            if not area: continue

            area = area.get()
            if area < CN.TOL: continue
            if area < aire: continue

            aire = area
            box  = out

    if aire > CN.TOL:
        if t: box = p3Dv(t * box)
        return box

    # PATH E : Medial box, segment approach.
    aire = 0

    for sg in segments(pts):
        p0 = sg[0]
        p1 = sg[1]

        for p2 in pts:
            if areSame(p2, p0): continue
            if areSame(p2, p1): continue

            out = medialBox(openstudioPoint3dVector([p0, p1, p2]))
            if not out: continue
            if not fits(out, pts): continue
            if fits(pts, out): continue

            area = openstudio.getArea(box)
            if not area: continue

            area = area.get()
            if area < CN.TOL: continue
            if area < aire: continue

            aire = area
            box  = out

    if aire > CN.TOL:
        if t: box = p3Dv(t * box)
        return box

    # PATH F : Medial box, triad approach.
    aire = 0

    for sg in triads(pts):
        p0 = sg[0]
        p1 = sg[1]
        p2 = sg[2]

        out = medialBox(openstudio.Point3dVector([p0, p1, p2]))
        if not out: continue
        if not fits(out, pts): continue
        if fits(pts, out): continue

        area = openstudio.getArea(box)
        if not area: continue

        area = area.get()
        if area < CN.TOL: continue
        if area < aire: continue

        aire = area
        box  = out

    if aire > CN.TOL:
        if t: box = p3Dv(t * box)
        return box

    # PATH G : Medial box, triangulated approach.
    aire  = 0
    outer = list(pts)
    outer.reverse()
    outer = p3Dv(outer)
    holes = openstudio.Point3dVectorVector()

    for triangle in openstudio.computeTriangulation(outer, holes):
        for sg in segments(triangle):
            p0 = sg[0]
            p1 = sg[1]

            for p2 in pts:
                if areSame(p2, p0): continue
                if areSame(p2, p1): continue

                out = medialBox(openstudio.Point3dVector([p0, p1, p2]))
                if not out: continue
                if not fits(out, pts): continue
                if fits(pts, out): continue

                area = openstudio.getArea(out)
                if not area: continue

                area = area.get()
                if area < CN.TOL: continue
                if area < aire: continue

                aire = area
                box  = out

    if aire < CN.TOL: return bkp
    if t: box = p3Dv(t * box)

    return box


def realignedFace(pts=None, force=False) -> dict:
    """Generates re-'aligned' polygon vertices with respect to main axis of
    symmetry of its largest 'bounded box'. Input polygon vertex Z-axis values
    must equal 0, and be counterclockwise. First, cloned polygon vertices are
    rotated so the longest axis of symmetry of its bounded box lies parallel to
    the X-axis (see returned key "o": midpoint of the narrow side of the bounded
    box, nearest to grid origin [0,0,0]). If the axis of symmetry of the bounded
    box is already parallel to the X-axis, then the rotation step is skipped
    (unless 'force' is True). Whether rotated or not, polygon vertices are then
    translated as to ensure one or more vertices are aligned along the X-axis
    and one or more vertices are aligned along the Y-axis (no vertices with
    negative X or Y coordinate values). To unalign the returned set of vertices
    (or its bounded box, or its bounding box), first inverse the translation
    transformation, then inverse the rotation transformation. If failure (e.g.
    invalid inputs), the returned dict values are set to None.

    Args:
        pts (openstudio.Point3dVector):
            A set of OpenStudio 3D points.
        force (bool):
            Whether to force rotation for aligned (yet narrow) boxes.

    Returns:
        dict:
        - "set" (openstudio.Point3dVector): realigned (cloned) polygon vertices
        - "box" (openstudio.Point3dVector): its bounded box (wrt to "set")
        - "bbox" (openstudio.Point3dVector): its bounding box
        - "t" (openstudio.Transformation): its translation transformation
        - "r" (openstudio.Transformation): its rotation transformation
        - "o" (openstudio.Point3d): origin coordinates of its axis of rotation

    """
    mth = "osut.realignedFace"
    out = dict(set=None, box=None, bbox=None, t=None, r=None, o=None)
    pts = poly(pts, False, True)
    if not pts: return out

    if not shareXYZ(pts, "z"):
        return oslg.invalid("aligned plane", mth, 1, CN.DBG, out)

    if isClockwise(pts):
        return oslg.invalid("clockwise pts", mth, 1, CN.DBG, out)

    # Optionally force rotation so bounded box ends up wider than taller.
    # Strongly suggested for flat surfaces like roofs (see 'isSloped').
    try:
        force = bool(force)
    except:
        oslg.log(CN.DBG, "Ignoring force input (%s)" % mth)
        force = False

    o   = openstudio.Point3d(0, 0, 0)
    w   = width(pts)
    h   = height(pts)
    d   = h if h > w else w
    box = boundedBox(pts)

    if not box:
        return oslg.invalid("bounded box", mth, 0, CN.DBG, out)

    sgs  = []
    segs = segments(box)

    if not segs:
        return oslg.invalid("bounded box segments", mth, 0, CN.DBG, out)

    # Deterministic identification of box rotation/translation 'origin'.
    for idx, segment in enumerate(segs):
        sg        = {}
        sg["idx"] = idx
        sg["mid"] = midpoint(segment[0], segment[1])
        sg["l"  ] = (segment[1] - segment[0]).length()
        sg["mo" ] = (sg["mid"] - o).length()
        sgs.append(sg)

    if isSquare(box):
        sgs = sorted(sgs, key=lambda x: x["mo"])[:2]
    else:
        sgs = sorted(sgs, key=lambda x: x["l" ])[:2]
        sgs = sorted(sgs, key=lambda x: x["mo"])[:2]

    sg0 = sgs[0]
    sg1 = sgs[1]

    i = sg0["idx"]

    if round(sg0["mo"], 2) == round(sg1["mo"], 2):
        if round(sg1["mid"].y(), 2) < round(sg0["mid"].y(), 2):
            i = sg1["idx"]

    k = i+2 if i+2 < len(segs) else i-2

    origin   = midpoint(segs[i][0], segs[i][1])
    terminal = midpoint(segs[k][0], segs[k][1])

    seg   = terminal - origin
    right = openstudio.Point3d(origin.x() + d, origin.y()    , 0) - origin
    north = openstudio.Point3d(origin.x(),     origin.y() + d, 0) - origin
    axis  = openstudio.Point3d(origin.x(),     origin.y()    , d) - origin
    angle = openstudio.getAngle(right, seg)

    if north.dot(seg) < 0: angle = -angle

    # Skip rotation if bounded box is already aligned along XY grid (albeit
    # 'narrow'), i.e. if the angle is 90°.
    if round(angle, 3) == round(math.pi/2, 3):
        if force is False: angle = 0

    r    = openstudio.createRotation(origin, axis, angle)
    pts  = p3Dv(r.inverse() * pts)
    box  = p3Dv(r.inverse() * box)
    dX   = min([pt.x() for pt in pts])
    dY   = min([pt.y() for pt in pts])
    xy   = openstudio.Point3d(origin.x() + dX, origin.y() + dY, 0)
    o2   = xy - origin
    t    = openstudio.createTranslation(o2)
    st   = p3Dv(t.inverse() * pts)
    box  = p3Dv(t.inverse() * box)
    bbox = outline([st])

    out["set" ] = blc(st)
    out["box" ] = blc(box)
    out["bbox"] = blc(bbox)
    out["t"   ] = t
    out["r"   ] = r
    out["o"   ] = origin

    return out


def alignedWidth(pts=None, force=False) -> float:
    """Returns 'width' of a set of OpenStudio 3D points, once re/aligned.

    Args:
        pts (openstudio.Point3dVector):
            A set of OpenStudio 3D points.
        force (bool):
            Whether to force rotation for aligned (yet narrow) boxes.

    Returns:
        float: Width along X-axis, once re/aligned.
        0.0: If invalid inputs (see logs).

    """
    mth = "osut.alignedWidth"
    pts = poly(pts, False, True, True, True)
    if len(pts) < 2: return 0

    try:
        force = bool(force)
    except:
        oslg.log(CN.DBG, "Ignoring force input (%s)" % mth)
        force = False

    pts = realignedFace(pts, force)["set"]
    if len(pts) < 2: return 0

    xs = [pt.x() for pt in pts]

    return max(xs) - min(xs)


def alignedHeight(pts=None, force=False) -> float:
    """Returns 'height' of a set of OpenStudio 3D points, once re/aligned.

    Args:
        pts (openstudio.Point3dVector):
            A set of OpenStudio 3D points.
        force (bool):
            Whether to force rotation for aligned (yet narrow) boxes.

    Returns:
        float: Height along Y-axis, once re/aligned.
        0.0: If invalid inputs (see logs).

    """

    mth = "osut.alignedHeight"
    pts = poly(pts, False, True, True, True)
    if len(pts) < 2: return 0

    try:
        force = bool(force)
    except:
        oslg.log(CN.DBG, "Ignoring force input (%s)" % mth)
        force = False

    pts = realignedFace(pts, force)["set"]
    if len(pts) < 2: return 0

    ys = [pt.y() for pt in pts]

    return max(ys) - min(ys)


def spaceHeight(space=None) -> float:
    """Fetch a space's full height.

    Args:
        space (openstudio.model.Space):
            An OpenStudio space.

    Returns:
        (float): Full height of space (0.0 if invalid input).

    """
    if not isinstance(space, openstudio.model.Space):
        return 0

    hght =  0
    minZ =  10000
    maxZ = -10000

    # The solution considers all surface types: "Floor", "Wall", "RoofCeiling".
    # No presumption that floor are necessarily at ground level.
    for surface in space.surfaces():
        zs   = [pt.z() for pt in surface.vertices()]
        minZ = min(minZ, min(zs))
        maxZ = max(maxZ, max(zs))

    hght = maxZ - minZ
    if hght < 0: hght = 0

    return maxZ - minZ


def spaceWidth(space=None) -> float:
    """Fetches a space's 'width', i.e. at its narrowest. For instance, an 100m
    (long) hospital corridor may only have a 'width' of 2.4m. This is a common
    requirement for LPD calculations (e.g. 90.1, NECB). Not to confuse with
    vertical wall widths in methods 'width' & 'alignedWidth'.

    Args:
        space (openstudio.model.Space):
            An OpenStudio space.

    Returns:
        (float): Width of space (0.0 if invalid input).

    """
    if not isinstance(space, openstudio.model.Space):
        return 0

    floors = facets(space, "all", "Floor")
    if not floors: return 0

    # Automatically determining a space's "width" is not so straightforward:
    #   - a space may hold multiple floor surfaces at various Z-axis levels
    #   - a space may hold multiple floor surfaces, with unique "widths"
    #   - a floor surface may expand/contract (in "width") along its length.
    #
    # First, attempt to merge all floor surfaces together as 1x polygon:
    #   - select largest floor surface (in area)
    #   - determine its 3D plane
    #   - retain only other floor surfaces sharing same 3D plane
    #   - recover potential union between floor surfaces
    #   - fall back to largest floor surface if invalid union
    floors = sorted(floors, key=lambda fl: fl.grossArea(), reverse=True)
    floor  = floors[0]
    plane  = floor.plane()
    t      = openstudio.Transformation.alignFace(floor.vertices())
    polyg  = list(poly(floor, False, True, True, t, "ulc"))

    if not polyg:
        oslg.clean()
        return 0

    polyg.reverse()
    polyg = p3Dv(polyg)

    if len(floors) > 1:
        floors = [flr for flr in floors if plane.equal(fl.plane(), 0.001)]

        if len(floors) > 1:
            polygs = [poly(flr, False, True, True, t, "ulc") for flr in floors]
            polygs = [plg for plg in polygs if plg]

            for plg in polygs:
                plg = list(plg)
                plg.reverse()
                plg = p3Dv(plg)

            union = openstudio.joinAll(polygs, 0.01)[0]
            polyg = poly(union, False, True, True)

    box = boundedBox(polyg)
    oslg.clean()

    # A bounded box's 'height', at its narrowest, is its 'width'.
    return height(box)


def genAnchors(s=None, sset=[], tag="box") -> int:
    """Identifies 'leader line anchors', i.e. specific 3D points of a (larger)
    set (e.g. delineating a larger, parent polygon), each anchor linking the
    BLC corner of one or more (smaller) subsets (free-floating within the
    parent) - see follow-up 'genInserts'. Subsets may hold several 'tagged'
    vertices (e.g. "box", "cbox"). By default, the solution seeks to anchor
    subset "box" vertices. Users can select other tags, e.g. tag == "cbox". The
    solution minimally validates individual subsets (e.g. no self-intersecting
    polygons, coplanarity, no inter-subset conflicts, must fit within larger
    set). Potential leader lines cannot intersect each other, similarly tagged
    subsets or (parent) polygon edges. For highly-articulated cases (e.g. a
    narrow parent polygon with multiple concavities, holding multiple subsets),
    such leader line conflicts are likely unavoidable. It is recommended to
    first sort subsets (e.g. based on surface areas), given the solution's
    'first-come-first-served' policy. Subsets without valid leader lines are
    ultimately ignored (check for new set "void" keys, see error logs). The
    larger set of points is expected to be in space coordinates - not building
    or site coordinates, while subset points are expected to 'fit' in the larger
    set.

    Args:
        s (openstudio.Point3dVector):
            A (larger) parent set of points.
        sset (list):
            Subsets of (smaller) sequenced points, to 'anchor'.
        tag (str):
            Selected subset vertices to target.

    Returns:
        int: Number of successfully anchored subsets (see logs if missing).

    """
    mth = "osut.genAnchors"
    n   = 0
    ide = "%s " % s.nameString() if hasattr(s, "nameString") else ""
    ids = id(s)
    pts = poly(s)

    if not pts:
        return oslg.invalid("%s polygon" % ide, mth, 1, CN.DBG, n)

    try:
        sset = list(sset)
    except:
        return oslg.mismatch("subset", sset, list, mth, CN.DBG, n)

    origin = openstudio.Point3d(0,0,0)
    zenith = openstudio.Point3d(0,0,1)
    ray    = zenith - origin

    # Validate individual subsets. Purge surface-specific leader line anchors.
    for i, st in enumerate(sset):
        str1 = ide + "subset %d" % (i+1)
        str2 = str1 + " %s" % str(tag)

        if not isinstance(st, dict):
            return oslg.mismatch(str1, st, dict, mth, CN.DBG, n)
        if tag not in st:
            return oslg.hashkey(str1, st, tag, mth, CN.DBG, n)
        if not st[tag]:
            return oslg.empty("%s vertices" % str2, mth, CN.DBG, n)

        stt = poly(st[tag])

        if not stt:
            return oslg.invalid("%s polygon" % str2, mth, 0, CN.DBG, n)
        if not fits(stt, pts, True):
            return oslg.invalid("%s gap % str2", mth, 0, CN.DBG, n)

        if "out" in st:
            if "t" not in st:
                return oslg.hashkey(str1, st, "t", mth, CN.DBG, n)
            if "ti" not in st:
                return oslg.hashkey(str1, st, "ti", mth, CN. DBG, n)
            if "t0" not in st:
                return oslg.hashkey(str1, st, "t0", mth, CN.DBG, n)

        if "ld" in st:
            if not isinstance(st["ld"], dict):
                return oslg.invalid("%s leaders" % str1, mth, 0, CN.DBG, n)

            if ids in st["ld"]: st["ld"].pop(ids)
        else:
            st["ld"] = {}

    for i, st in enumerate(sset):
        # When a subset already holds a leader line anchor (from an initial call
        # to 'genAnchors'), it inherits key "out" - a dictionary holding (among
        # others) a 'realigned' set of points (by default a 'realigned' "box").
        # The latter is typically generated from an outdoor-facing roof.
        # Subsequent calls to 'genAnchors' may send (as first argument) a
        # corresponding ceiling below (both may be called from 'addSkylights').
        # Roof vs ceiling may neither share alignment transformation nor
        # space/site transformation identities. All subsequent calls to
        # 'genAnchors' shall recover the "out" points, apply a succession of
        # de/alignments and transformations in sync, and overwrite tagged points.
        #
        # Although 'genAnchors' and 'genInserts' have both been developed to
        # support anchor insertions in other cases (e.g. bay window in a wall),
        # variables and terminology here continue pertain to roofs, ceilings,
        # skylights and wells - less abstract, simpler to follow.
        if "out" in st:
            ti   = st["ti" ] # unoccupied attic/plenum space site transformation
            t0   = st["t0" ] # occupied space site transformation
            t    = st["t"  ] # initial alignment transformation of roof surface
            o    = st["out"]
            tpts = t0.inverse() * (ti * (t * (o["r"] * (o["t"] * o["set"]))))
            tpts = cast(tpts, pts, ray)

            st[tag] = tpts
        else:
            if "t" not in st: st["t"] = openstudio.Transformation.alignFace(pts)

            tpts = st["t"].inverse() * st[tag]
            o    = realignedFace(tpts, True)
            tpts = st["t"] * (o["r"] * (o["t"] * o["set"]))

            st["out"] = o
            st[tag  ] = tpts

    # Identify candidate leader line anchors for each subset.
    for i, st in enumerate(sset):
        candidates = []
        tpts = st[tag]

        for pt in pts:
            ld = [pt, tpts[0]]
            nb = 0

            # Intersections between leader line and polygon edges.
            for sg in segments(pts):
                if nb != 0: break
                if holds(sg, pt): continue
                if doesLineIntersect(sg, ld): nb += 1

            # Intersections between candidate leader line vs other subsets?
            for other in sset:
                if nb != 0: break
                if st == other: continue

                ost = other[tag]

                for sg in segments(ost):
                    if doesLineIntersect(ld, sg): nb += 1

            # ... and previous leader lines (first come, first serve basis).
            for other in sset:
                if nb != 0: break
                if st == other: continue
                if "ld" not in other: continue
                if ids not in other["ld"]: continue

                ost = other[tag]
                pld = other["ld"][ids]
                if areSame(pld, pt): continue
                if doesLineIntersect(ld, [pld, ost[0]]): nb += 1

            # Finally, check for self-intersections.
            for sg in segments(tpts):
                if nb != 0: break
                if holds(sg, tpts[0]): continue
                if doesLineIntersect(sg, ld): nb += 1

                if ((sg[0]-sg[-1]).cross(ld[0]-ld[-1])).length() < CN.TOL: nb += 1

            if nb == 0: candidates.append(pt)

        if candidates:
            p0 = candidates[0]
            l0 = (p0 - tpts[0]).length()

            for j, pt in enumerate(candidates):
                if j == 0: continue
                lj = (pt - tpts[0]).length()

                if lj < l0:
                    p0 = pt
                    l0 = lj

            st["ld"][ids] = p0
            n += 1
        else:
            str1 = ide + ("subset #%d" % (i+1))
            m    = "%s: unable to anchor '%s' leader line (%s)" % (str1, tag, mth)
            oslg.log(CN.WRN, m)
            st["void"] = True

    return n


def genExtendedVertices(s=None, sset=[], tag="vtx") -> openstudio.Point3dVector:
    """Extends (larger) polygon vertices to circumscribe one or more (smaller)
    subsets of vertices, based on previously-generated 'leader line' anchors.
    The solution minimally validates individual subsets (e.g. no
    self-intersecting polygons, coplanarity, no inter-subset conflicts, must fit
    within larger set). Valid leader line anchors (set key "ld") need to be
    generated prior to calling the method - see 'genAnchors'. Subsets may hold
    several 'tag'ged vertices (e.g. "box", "vtx"). By default, the solution
    seeks to anchor subset "vtx" vertices. Users can select other tags, e.g.
    tag == "box").

    Args:
        s (openstudio.Point3dVector):
            A (larger) parent set of points.
        sset (list):
            Subsets of (smaller) sequenced points.
        tag (str):
            Selected subset vertices to target.

    Returns:
        openstudio.Point3dVector: Extended vertices (see logs if empty).

    """
    mth = "osut.genExtendedVertices"
    ide = "%s " % s.nameString() if hasattr(s, "nameString") else ""
    f   = False
    ids = id(s)
    pts = poly(s)
    cl  = openstudio.Point3d
    a   = openstudio.Point3dVector()
    v   = []

    if not pts: return oslg.invalid("%s polygon" % ide, mth, 1, CN.DBG, a)

    try:
        sset = list(sset)
    except:
        return oslg.mismatch("subset", sset, list, mth, CN.DBG, a)

    # Validate individual subsets.
    for i, st in enumerate(sset):
        str1 = ide + "subset %d" % (i+1)
        str2 = str1 + " %s" % str(tag)

        if not isinstance(st, dict):
            return oslg.mismatch(str1, st, dict, mth, CN.DBG, a)

        if "void" in st and st["void"]: continue

        if tag not in st:
            return oslg.hashkey(str1, st, tag, mth, CN.DBG, a)

        if not st[tag]:
            return oslg.empty("%s vertices" % str2, mth, CN.DBG, a)

        stt = poly(st[tag])

        if not stt:
            return oslg.invalid("%s polygon" % str2, mth, 0, CN.DBG, a)

        if "ld" not in st:
            return oslg.hashkey(str1, st, "ld", mth, CN.DBG, a)

        ld = st["ld"]

        if not isinstance(st["ld"], dict):
            return oslg.invalid("%s leaders" % str2, mth, 0, CN.DBG, a)

        if ids not in st["ld"]:
            return oslg.hashkey("%s leader?" % str2, st["ld"], ide, mth, CN.DBG, a)

        if not isinstance(ld[ids], cl):
            return oslg.mismatch("%s point" % str2, st["ld"][ids], cl, mth, CN.DBG, a)

    # Re-sequence polygon vertices.
    for pt in pts:
        v.append(pt)

        # Loop through each valid subset; concatenate circumscribing vertices.
        for st in sset:
            if "void" in st and st["void"]: continue
            if not areSame(st["ld"][ids], pt): continue
            if tag not in st: continue

            v += list(st[tag])
            v.append(pt)

    return p3Dv(v)


def genInserts(s=None, sset=[]) -> openstudio.Point3dVector:
    """Generates (1D or 2D) arrays of (smaller) rectangular collection of
    points (e.g. arrays of polygon inserts) from subset parameters, within a
    (larger) set (e.g. parent polygon). If successful, each subset inherits
    additional key:value pairs: namely "vtx" (collection of circumscribing
    vertices), and "vts" (collection of individual insert vertices). Valid
    leader line anchors (set key "ld") need to be generated prior to calling
    the solution - see 'genAnchors'.

    Args:
        s (openstudio.Point3dVector):
            A (larger) parent set of points.
        sset (list):
            Subsets of (smaller) sequenced points (dictionnaries). Each
            collection shall/may hold the following key:value pairs.
            - "box" (openstudio.Point3dVector): bounding box of each subset
            - "ld" (dict): a collection of leader line anchors
            - "rows" (int): number of rows of inserts
            - "cols" (int): number of columns of inserts
            - "w0" (float): width of individual inserts (wrt cols) min 0.4
            - "d0" (float): depth of individual inserts (wrt rows) min 0.4
            - "dX" (float): optional left/right X-axis buffer
            - "dY" (float): optional top/bottom Y-axis buffer

    Returns:
        openstudio.Point3dVector: New polygon vertices (see logs if empty).

    """
    mth = "osut.genInserts"
    ide = "%s:" % s.nameString() if hasattr(s, "nameString") else ""
    ids = id(s)
    pts = poly(s)
    cl  = openstudio.Point3d
    a   = openstudio.Point3dVector()
    if not pts: return a

    try:
        sset = list(sset)
    except:
        return oslg.mismatch("subset", sset, list, mth, CN.DBG, a)

    gap  = 0.1
    gap4 = 0.4 # minimum insert width/depth

    # Validate/reset individual subset collections.
    for i, st in enumerate(sset):
        str1 = ide + "subset #%d" % (i+1)
        if "void" in st and st["void"]: continue

        if not isinstance(st, dict):
            return oslg.mismatch(str1, st, dict, mth, CN.DBG, a)
        if "box" not in st:
            return oslg.hashkey(str1, st, "box", mth, CN.DBG, a)
        if "ld" not in st:
            return oslg.hashkey(str1, st, "ld", mth, CN.DBG, a)
        if "out" not in st:
            return oslg.hashkey(str1, st, "out", mth, CN.DBG, a)

        str2 = str1 + " anchor"
        ld = st["ld"]

        if not isinstance(ld, dict):
            return oslg.mismatch(str2, "ld", dict, mth, CN.DBG, a)
        if ids not in ld:
            return oslg.hashkey(str2, ld, ide, mth, CN.DBG, a)
        if not isinstance(ld[ids], cl):
            return oslg.mismatch(str2, ld[ids], cl, mth, CN.DBG, a)

        # Ensure each subset bounding box is safely within larger polygon
        # boundaries.
        # @todo: In line with related addSkylights' @todo, expand solution to
        #        safely handle 'side' cutouts (i.e. no need for leader lines).
        #        In so doing, boxes could eventually align along surface edges.
        str3 = str1 + " box"
        bx = poly(st["box"])

        if not bx:
            return invalid(str3, mth, 0, CN.DBG, a)
        if not isRectangular(bx):
            return oslg.invalid("%s rectangle" % str3, mth, 0, CN.DBG, a)
        if not fits(bx, pts, True):
            return invalid("%s box" % str3, mth, 0, CN.DBG, a)

        if "rows" in st:
            try:
                st["rows"] = int(st["rows"])
            except:
                return oslg.invalid("%s rows" % ide, mth, 0, CN.DBG, a)

            if st["rows"] < 1:
                return oslg.zero("%s rows" % ide, mth, CN.DBG, a)
        else:
            st["rows"] = 1

        if "cols" in st:
            try:
                st["cols"] = int(st["cols"])
            except:
                return oslg.invalid("%s cols" % ide, mth, 0, CN.DBG, a)

            if st["cols"] < 1:
                return oslg.zero( "%s cols" % ide, mth, CN.DBG, a)
        else:
            st["cols"] = 1

        if "w0" in st:
            try:
                st["w0"] = float(st["w0"])
            except:
                return oslg.invalid("%s width" % ide, mth, 0, CN.DBG, a)

            if round(st["w0"], 2) < gap4:
                return oslg.zero("%s width" % ide, mth, CN.DBG, a)
        else:
            st["w0"] = 1.4

        if "d0" in st:
            try:
                st["d0"] = float(st["d0"])
            except:
                return oslg.invalid("%s depth" % ide, mth, 0, CN.DBG, a)

            if round(st["d0"], 2) < gap4:
                return oslg.zero("%s depth" % ide, mth, CN.DBG, a)
        else:
            st["d0"] = 1.4

        if "dX" in st:
            try:
                st["dX"] = float(st["dX"])
            except:
                return oslg.invalid("%s dX" % ide, mth, 0, CN.DBG, a)
        else:
            st["dX"] = None

        if "dY" in st:
            try:
                st["dY"] = float(st["dY"])
            except:
                return oslg.invalid("%s dY" % ide, mth, 0, CN.DBG, a)
        else:
            st["dY"] = None

    # Flag conflicts between subset bounding boxes. @todo: ease up for ridges.
    for i, st in enumerate(sset):
        bx = st["box"]
        if "void" in st and st["void"]: continue

        for j, other in enumerate(sset):
            if i == j: continue
            bx2 = other["box"]

            if overlapping(bx, bx2):
                str4 = ide + "subset boxes #%d:#%d" % (i+1, j+1)
                return oslg.invalid("%s (overlapping)" % str4, mth, 0, CN.DBG, a)


    t = openstudio.Transformation.alignFace(pts)
    rpts = t.inverse() * pts

    # Loop through each 'valid' subset (i.e. linking a valid leader line
    # anchor), generate subset vertex array based on user-provided specs.
    for i, st in enumerate(sset):
        str5 = ide + "subset #%d" % (i+1)
        if "void" in st and st["void"]: continue

        o    = st["out"]
        vts  = {} # collection of individual (named) polygon insert vertices
        vtx  = [] # sequence of circumscribing polygon vertices
        bx   = o["set"]
        w    = width(bx)  # overall sandbox width
        d    = height(bx) # overall sandbox depth
        dX   = st["dX"  ]  # left/right buffer (array vs bx)
        dY   = st["dY"  ]  # top/bottom buffer (array vs bx)
        cols = st["cols"]  # number of array columns
        rows = st["rows"]  # number of array rows
        x    = st["w0"  ]  # width of individual insert
        y    = st["d0"  ]  # depth of individual insert
        gX   = 0          # gap between insert columns
        gY   = 0          # gap between insert rows

        # Gap between insert columns.
        if cols > 1:
            if not dX: dX = ((w - cols * x) / cols) / 2
            gX = (w - 2 * dX - cols * x) / (cols - 1)
            if round(gX, 2) < gap: gX = gap
            dX = (w - cols * x - (cols - 1) * gX) / 2
        else:
            dX = (w - x) / 2

        if round(dX, 2) < 0:
            oslg.log(CN.ERR, "Skipping %s: Negative dX (%s)" % (str5, mth))
            continue

        # Gap between insert rows.
        if rows > 1:
            if not dY: dY = ((d - rows * y) / rows) / 2
            gY = (d - 2 * dY - rows * y) / (rows - 1)
            if round(gY, 2) < gap: gY = gap
            dY = (d - rows * y - (rows - 1) * gY) / 2
        else:
            dY = (d - y) / 2

        if round(dY, 2) < 0:
            oslg.log(CN.ERR, "Skipping %s: Negative dY (%s)" % (str5, mth))
            continue

        st["dX"] = dX
        st["gX"] = gX
        st["dY"] = dY
        st["gY"] = gY

        x0 = min([pt.x() for pt in bx]) + dX # X-axis starting point
        y0 = min([pt.y() for pt in bx]) + dY # X-axis starting point
        xC = x0 # current X-axis position
        yC = y0 # current Y-axis position

        # BLC of array.
        vtx.append(openstudio.Point3d(xC, yC, 0))

        # Move up incrementally along left side of sandbox.
        for iY in range(rows):
            if iY != 0:
                yC += gY
                vtx.append(openstudio.Point3d(xC, yC, 0))

            yC += y
            vtx.append(openstudio.Point3d(xC, yC, 0))

        # Loop through each row: left-to-right, then right-to-left.
        for iY in range(rows):
            for iX in range(cols - 1):
                xC += x
                vtx.append(openstudio.Point3d(xC, yC, 0))

                xC += gX
                vtx.append(openstudio.Point3d(xC, yC, 0))

        # Generate individual polygon inserts, left-to-right.
        for iX in range(cols):
            nom  = "%d:%d:%d" % (i, iX, iY)
            vec  = []
            vec.append(openstudio.Point3d(xC    , yC    , 0))
            vec.append(openstudio.Point3d(xC    , yC - y, 0))
            vec.append(openstudio.Point3d(xC + x, yC - y, 0))
            vec.append(openstudio.Point3d(xC + x, yC    , 0))

            # Store.
            vts[nom] = p3Dv(t * ulc(o["r"] * (o["t"] * vec)))

            # Add reverse vertices, circumscribing each insert.
            vec.reverse()
            if iX == cols - 1: vec.pop()

            vtx += vec
            if iX != cols - 1: xC -= gX + x

            if iY != rows - 1:
                yC -= gY + y
                vtx.append(openstudio.Point3d(xC, yC, 0))

        st["vts"] = vts
        st["vtx"] = p3Dv(t * (o["r"] * (o["t"] * vtx)))

    # Extended vertex sequence of the larger polygon.
    return genExtendedVertices(s, sset)


def facets(spaces=[], boundary="all", type="all", sides=[]) -> list:
    """Returns an array of OpenStudio space surfaces or subsurfaces that match
    criteria, e.g. exterior, north-east facing walls in hotel "lobby". Note
    that the 'sides' list relies on space coordinates (not building or site
    coordinates). Also, the 'sides' list is exclusive (not inclusive), e.g.
    walls strictly facing north or east would not be returned if 'sides' holds
    ["north", "east"]. No outside boundary condition filters if 'boundary'
    argument == "all". No surface type filters if 'type' argument == "all".

    Args:
        spaces (list of openstudio.model.Space):
            Target spaces.
        boundary (str):
            OpenStudio outside boundary condition.
        type (str):
            OpenStudio surface (or subsurface) type.
        sides (list):
            Direction keys, e.g. "north" (see osut.sidz())

    Returns:
        list of openstudio.model.Surface: Surfaces (may be empty, no logs).
        list of openstudio.model.SubSurface: SubSurfaces (may be empty, no logs).
    """
    mth = "osut.facets"

    spaces = [spaces] if isinstance(spaces, openstudio.model.Space) else spaces

    try:
        spaces = list(spaces)
    except:
        return []

    sides = [sides] if isinstance(sides, str) else sides

    try:
        sides = list(sides)
    except:
        return []

    faces    = []
    boundary = oslg.trim(boundary).lower()
    type     = oslg.trim(type).lower()
    if not boundary: return []
    if not type:     return []

    # Filter sides. If 'sides' is initially empty, return all surfaces of
    # matching type and outside boundary condition.
    if sides:
        sides = [side for side in sides if side in sidz()]

        if not sides: return []

    for space in spaces:
        if not isinstance(space, openstudio.model.Space): return []

        for s in space.surfaces():
            if boundary != "all":
                if s.outsideBoundaryCondition().lower() != boundary: continue

            if type != "all":
                if s.surfaceType().lower() != type: continue

            if sides:
                aims = []

                if s.outwardNormal().z() >  CN.TOL: aims.append("top")
                if s.outwardNormal().z() < -CN.TOL: aims.append("bottom")
                if s.outwardNormal().y() >  CN.TOL: aims.append("north")
                if s.outwardNormal().x() >  CN.TOL: aims.append("east")
                if s.outwardNormal().y() < -CN.TOL: aims.append("south")
                if s.outwardNormal().x() < -CN.TOL: aims.append("west")

                if all([side in aims for side in sides]):
                      faces.append(s)
            else:
                faces.append(s)

    for space in spaces:
        for s in space.surfaces():
            if boundary != "all":
                if s.outsideBoundaryCondition().lower() != boundary: continue

            for sub in s.subSurfaces():
                if type != "all":
                    if sub.subSurfaceType().lower() != type: continue

                if sides:
                    aims = []

                    if sub.outwardNormal().z() >  CN.TOL: aims.append("top")
                    if sub.outwardNormal().z() < -CN.TOL: aims.append("bottom")
                    if sub.outwardNormal().y() >  CN.TOL: aims.append("north")
                    if sub.outwardNormal().x() >  CN.TOL: aims.append("east")
                    if sub.outwardNormal().y() < -CN.TOL: aims.append("south")
                    if sub.outwardNormal().x() < -CN.TOL: aims.append("west")

                    if all([side in aims for side in sides]):
                          faces.append(sub)
                else:
                    faces.append(sub)

    return faces


def genSlab(pltz=[], z=0) -> openstudio.Point3dVector:
    """Generates an OpenStudio 3D point vector of a composite floor "slab", a
    'union' of multiple rectangular, horizontal floor "plates". Each plate
    must either share an edge with (or encompass or overlap) any of the
    preceding plates in the array. The generated slab may not be convex.

    Args:
        pltz (list):
            Collection of individual floor plates (dicts), each holding:
            - "x" (float): Left corner of plate origin (bird's eye view).
            - "y" (float): Bottom corner of plate origin (bird's eye view).
            - "dx" (float): Plate width (bird's eye view).
            - "dy" (float): Plate depth (bird's eye view)
            - "z" (float): Z-axis coordinate.

    Returns:
        openstudio.Point3dVector: Slab vertices (see logs if empty).
    """
    mth = "osut.genSlab"
    slb = openstudio.Point3dVector()
    bkp = openstudio.Point3dVector()

    # Input validation.
    if not isinstance(pltz, list):
        return oslg.mismatch("plates", pltz, list, mth, CN.DBG, slb)

    try:
        z = float(z)
    except:
        return oslg.mismatch("Z", z, float, mth, CN.DBG, slb)

    for i, plt in enumerate(pltz):
        ide = "plate # %d (index %d)" % (i+1, i)

        if not isinstance(plt, dict):
            return oslg.mismatch(ide, plt, dict, mth, CN.DBG, slb)

        if "x"  not in plt: return oslg.hashkey(ide, plt,  "x", mth, CN.DBG, slb)
        if "y"  not in plt: return oslg.hashkey(ide, plt,  "y", mth, CN.DBG, slb)
        if "dx" not in plt: return oslg.hashkey(ide, plt, "dx", mth, CN.DBG, slb)
        if "dy" not in plt: return oslg.hashkey(ide, plt, "dy", mth, CN.DBG, slb)

        x  = plt["x" ]
        y  = plt["y" ]
        dx = plt["dx"]
        dy = plt["dy"]

        try:
            x = float(x)
        except:
            oslg.mismatch("%s X" % ide, x, float, mth, CN.DBG, slb)

        try:
            y = float(y)
        except:
            oslg.mismatch("%s Y" % ide, y, float, mth, CN.DBG, slb)

        try:
            dx = float(dx)
        except:
            oslg.mismatch("%s dX" % ide, dx, float, mth, CN.DBG, slb)

        try:
            dy = float(dy)
        except:
            oslg.mismatch("%s dY" % ide, dy, float, mth, CN.DBG, slb)

        if abs(dx) < CN.TOL: return oslg.zero("%s dX" % ide, mth, CN.ERR, slb)
        if abs(dy) < CN.TOL: return oslg.zero("%s dY" % ide, mth, CN.ERR, slb)

    # Join plates.
    for i, plt in enumerate(pltz):
        ide = "plate # %d (index %d)" % (i+1, i)

        x  = plt["x" ]
        y  = plt["y" ]
        dx = plt["dx"]
        dy = plt["dy"]

        # Adjust X if dX < 0.
        if dx < 0: x -= -dx
        if dx < 0: dx = -dx

        # Adjust Y if dY < 0.
        if dy < 0: y -= -dy
        if dy < 0: dy = -dy

        vtx  = []
        vtx.append(openstudio.Point3d(x + dx, y + dy, 0))
        vtx.append(openstudio.Point3d(x + dx, y,      0))
        vtx.append(openstudio.Point3d(x,      y,      0))
        vtx.append(openstudio.Point3d(x,      y + dy, 0))

        if slb:
            slab = openstudio.join(slb, vtx, CN.TOL2)

            if slab:
                slb  = slab.get()
            else:
                return oslg.invalid(ide, mth, 0, CN.ERR, bkp)
        else:
            slb = vtx

    # Once joined, re-adjust Z-axis coordinates.
    if abs(z) > CN.TOL:
        vtx = openstudio.Point3dVector()

        for pt in slb: vtx.append(openstudio.Point3d(pt.x(), pt.y(), z))

        slb = vtx

    return slb


def roofs(spaces = []) -> list:
    """Returns outdoor-facing, space-related roof surfaces. These include
    outdoor-facing roofs of each space per se, as well as any outdoor-facing
    roof surface of unoccupied spaces immediately above (e.g. plenums, attics)
    overlapping any of the ceiling surfaces of each space. It does not include
    surfaces labelled as 'RoofCeiling', which do not comply with ASHRAE 90.1 or
    NECB tilt criteria - see 'isRoof'.

    Args:
        spaces (list):
            A collection of openstudio.model.Space instances.

    Returns:
        list of openstudio.model.Surface instances: roofs (may be empty).

    """
    mth  = "osut.getRoofs"
    up   = openstudio.Point3d(0,0,1) - openstudio.Point3d(0,0,0)
    rufs = []

    if isinstance(spaces, openstudio.model.Space): spaces = [spaces]

    try:
        spaces = list(spaces)
    except:
        spaces = []

    spaces = [s for s in spaces if isinstance(s, openstudio.model.Space)]

    # Space-specific outdoor-facing roof surfaces.
    rufs = facets(spaces, "Outdoors", "RoofCeiling")
    rufs = [roof for roof in rufs if isRoof(roof)]

    for space in spaces:
        # When unoccupied spaces are involved (e.g. plenums, attics), the
        # target space may not share the same local transformation as the
        # space(s) above. Fetching site transformation.
        t0 = transforms(space)
        if not t0["t"]: continue

        t0 = t0["t"]

        for ceiling in facets(space, "Surface", "RoofCeiling"):
            cv0 = t0 * ceiling.vertices()

            floor = ceiling.adjacentSurface()
            if not floor: continue

            other = floor.get().space()
            if not other: continue

            other = other.get()
            if other.partofTotalFloorArea(): continue

            ti = transforms(other)
            if not ti["t"]: continue

            ti = ti["t"]

            # @todo: recursive call for stacked spaces as atria (AirBoundaries).
            for ruf in facets(other, "Outdoors", "RoofCeiling"):
                if not isRoof(ruf): continue

                rvi = ti * ruf.vertices()
                cst = cast(cv0, rvi, up)
                if not overlapping(cst, rvi, False): continue

                if ruf not in rufs: rufs.append(ruf)

    return rufs


def isDaylit(space=None, sidelit=True, toplit=True, baselit=True) -> bool:
    """Validates whether space has outdoor-facing surfaces with fenestration.

    Args:
        space (openstudio.model.Space):
            An OpenStudio space.
        sidelit (bool):
            Whether to check for 'sidelighting', e.g. windows.
        toplit (bool):
            Whether to check for 'toplighting', e.g. skylights.
        baselit (bool):
            Whether to check for 'baselighting', e.g. glazed floors.

    Returns:
        bool: Whether space is daylit.
        False: If invalid inputs (see logs).

    """
    mth    = "osut.isDaylit"
    cl     = openstudio.model.Space
    walls  = []
    rufs   = []
    floors = []

    if not isinstance(space, openstudio.model.Space):
        return oslg.mismatch("space", space, cl, mth, CN.DBG, False)

    try:
        sidelit = bool(sidelit)
    except:
        return oslg.invalid("sidelit", mth, 2, CN.DBG, False)

    try:
        toplit = bool(toplit)
    except:
        return oslg.invalid("toplit", mth, 2, CN.DBG, False)

    try:
        baselit = bool(baselit)
    except:
        return oslg.invalid("baselit", mth, 2, CN.DBG, False)

    if sidelit: walls  = facets(space, "Outdoors", "Wall")
    if toplit:  rufs   = facets(space, "Outdoors", "RoofCeiling")
    if baselit: floors = facets(space, "Outdoors", "Floor")

    for surface in (walls + rufs + floors):
        for sub in surface.subSurfaces():
            # All fenestrated subsurface types are considered, as user can set
            # these explicitly (e.g. skylight in a wall) in OpenStudio.
            if isFenestrated(sub): return True

    return False


def addSubs(s=None, subs=[], clear=False, bound=False, realign=False, bfr=0.005) -> bool:
    """Adds sub surface(s) (e.g. windows, doors, skylights) to a surface.

    Args:
        s (openstudio.model.Surface):
            An OpenStudio surface.
        subs (list):
            Requested subsurface attributes (dicts):
            - "id" (str): identifier e.g. "Window 007"
            - "type" (str): OpenStudio subsurface type ("FixedWindow")
            - "count" (int): number of individual subs per array (1)
            - "multiplier" (int): OpenStudio subsurface multiplier (1)
            - "frame" (WindowPropertyFrameAndDivider): FD object (None)
            - "assembly" (ConstructionBase): OpenStudio construction (None)
            - "ratio" (float): %FWR [0.0, 1.0]
            - "head" (float): e.g. door height, incl frame (osut.CN.HEAD)
            - "sill" (float): e.g. door sill (incl frame) (osut.CN.SILL)
            - "height" (float): door sill-to-head height
            - "width" (float): e.g. door width
            - "offset" (float): left-right gap between e.g. doors
            - "centreline" (float): centreline left-right offset of subs vs base
            - "r_buffer" (float): gap between subs and right corner
            - "l_buffer" (float): gap between subs and left corner
        "clear" (bool):
            Whether to remove current sub surfaces.
        "bound" (bool):
            Whether to add subs with regards to surface's bounded box.
        "realign" (bool):
            Whether to first realign bounded box.
        "bfr" (float):
            Safety buffer, to maintain near other edges.

    Returns:
        bool: Whether addition(s) was/were successful.
        False: If invalid inputs (see logs).

    """
    mth = "osut.addSubs"
    cl1 = openstudio.model.Surface
    cl2 = openstudio.model.WindowPropertyFrameAndDivider
    cl3 = openstudio.model.ConstructionBase
    v   = int("".join(openstudio.openStudioVersion().split(".")))
    mn  = 0.050 # minimum ratio value ( 5%)
    mx  = 0.950 # maximum ratio value (95%)
    if isinstance(subs, dict): subs = [subs]

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Exit if mismatched or invalid argument classes.
    try:
        subs = list(subs)
    except:
        return oslg.mismatch("subs", subs, list, mth, CN.DBG, False)

    if len(subs) == 0:
        return oslg.empty("subs", mth, CN.DBG, False)

    if not isinstance(s, cl1):
        return oslg.mismatch("surface", s, cl1, mth, CN.DBG, False)

    if not poly(s):
        return oslg.empty("surface points", mth, CN.DBG, False)

    nom = s.nameString()
    mdl = s.model()

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Purge existing sub surfaces?
    try:
        clear = bool(clear)
    except:
        oslg.log(CN.WRN, "%s: Keeping existing sub surfaces (%s)" % (nom, mth))
        clear = False

    if clear:
        for sb in s.subSurfaces(): sb.remove()

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Add sub surfaces with respect to base surface's bounded box? This is
    # often useful (in some cases necessary) with irregular or concave surfaces.
    # If true, sub surface parameters (e.g. height, offset, centreline) no
    # longer apply to the original surface 'bounding' box, but instead to its
    # largest 'bounded' box. This can be combined with the 'realign' parameter.
    try:
        bound = bool(bound)
    except:
        oslg.log(CN.WRN, "%s: Ignoring bounded box (%s)" % (nom, mth))
        bound = False

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Force re-alignment of base surface (or its 'bounded' box)? False by
    # default (ideal for vertical/tilted walls & sloped roofs). If set to True
    # for a narrow wall for instance, an array of sub surfaces will be added
    # from bottom to top (rather from left to right).
    try:
        realign = bool(realign)
    except:
        oslg.log(CN.WRN, "%s: Ignoring realignment (%s)" % (nom, mth))
        realign = False

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Ensure minimum safety buffer.
    try:
        bfr = float(bfr)
    except:
        oslg.log(CN.ERR, "Setting safety buffer to 5mm (%s)" % mth)
        bfr = 0.005

    if round(bfr, 2) < 0:
        return oslg.negative("safety buffer", mth, CN.ERR, False)

    if round(bfr, 2) < 0.005:
        m = "Safety buffer < 5mm may generate invalid geometry (%s)" % mth
        oslg.log(CN.WRN, m)

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Allowable sub surface types   | Frame&Divider enabled?
    #   - "FixedWindow"             | True
    #   - "OperableWindow"          | True
    #   - "Door"                    | False
    #   - "GlassDoor"               | True
    #   - "OverheadDoor"            | False
    #   - "Skylight"                | False if v < 321
    #   - "TubularDaylightDome"     | False
    #   - "TubularDaylightDiffuser" | False
    type  = "FixedWindow"
    types = openstudio.model.SubSurface.validSubSurfaceTypeValues()
    stype = s.surfaceType() # Wall, RoofCeiling or Floor

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    t   = openstudio.Transformation.alignFace(s.vertices())
    s0  = poly(s, False, False, False, t, "ulc")
    s00 = None

    # Adapt sandbox if user selects to 'bound' and/or 'realign'.
    if bound:
        box = boundedBox(s0)

        if realign:
            s00 = realignedFace(box, True)

            if not s00["set"]:
                return oslg.invalid("bound realignment", mth, 0, CN.DBG, False)

    elif realign:
        s00 = realignedFace(s0, False)

        if not s00["set"]:
            return oslg.invalid("unbound realignment", mth, 0, CN.DBG, False)

    max_x = width( s00["set"]) if s00 else width(s0)
    max_y = height(s00["set"]) if s00 else height(s0)
    mid_x = max_x / 2
    mid_y = max_y / 2

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Assign default values to certain sub keys (if missing), +more validation.
    for index, sub in enumerate(subs):
        if not isinstance(sub, dict):
            return oslg.mismatch("sub", sub, dict, mth, CN.DBG, False)

        # Required key:value pairs (either set by the user or defaulted).
        if "frame"      not in sub: sub["frame"     ] = None
        if "assembly"   not in sub: sub["assembly"  ] = None
        if "count"      not in sub: sub["count"     ] = 1
        if "multiplier" not in sub: sub["multiplier"] = 1
        if "id"         not in sub: sub["id"        ] = ""
        if "type"       not in sub: sub["type"      ] = type

        sub["type"] = oslg.trim(sub["type"])
        sub["id"  ] = oslg.trim(sub["id"])

        if not sub["type"]: sub["type"] = type
        if not sub["id"  ]: sub["id"  ] = "osut:%s:%d" % (nom, index)

        try:
            sub["count"] = int(sub["count"])
        except:
            sub["count"] = 1

        try:
            sub["multiplier"] = int(sub["multiplier"])
        except:
            sub["multiplier"] = 1

        if sub["count"     ] < 1: sub["count"     ] = 1
        if sub["multiplier"] < 1: sub["multiplier"] = 1

        ide = sub["id"]

        # If sub surface type is invalid, log/reset. Additional corrections may
        # be enabled once a sub surface is actually instantiated.
        if sub["type"] not in types:
            m = "Reset invalid '%s' type to '%s' (%s)" % (ide, type, mth)
            oslg.log(CN.WRN, m)
            sub["type"] = type

        # Log/ignore (optional) frame & divider object.
        if sub["frame"]:
            if isinstance(sub["frame"], cl2):
                if sub["type"].lower() == "skylight" and v < 321:
                    sub["frame"] = None
                if sub["type"].lower() == "door":
                    sub["frame"] = None
                if sub["type"].lower() == "overheaddoor":
                    sub["frame"] = None
                if sub["type"].lower() == "tubulardaylightdome":
                    sub["frame"] = None
                if sub["type"].lower() == "tubulardaylightdiffuser":
                    sub["frame"] = None

                if sub["frame"] is None:
                    m = "Skip '%s' FrameDivider (%s)" % (ide, mth)
                    oslg.log(CN.WRN, m)
            else:
                m = "Skip '%s' invalid FrameDivider object (%s)" % (ide, mth)
                oslg.log(CN.WRN, m)
                sub["frame"] = None

        # The (optional) "assembly" must reference a valid OpenStudio
        # construction base, to explicitly assign to each instantiated sub
        # surface. If invalid, log/reset/ignore. Additional checks are later
        # activated once a sub surface is actually instantiated.
        if sub["assembly"]:
            if not isinstance(sub["assembly"], cl3):
                m = "Skip invalid '%s' construction (%s)" % (ide, mth)
                oslg.log(WRN, m)
                sub["assembly"] = None

        # Log/reset negative float values. Set ~0.0 values to 0.0.
        for key, value in sub.items():
            if key == "count":      continue
            if key == "multiplier": continue
            if key == "type":       continue
            if key == "id":         continue
            if key == "frame":      continue
            if key == "assembly":   continue

            try:
                value = float(value)
            except:
                return oslg.mismatch(key, value, float, mth, CN.DBG, False)

            if key == "centreline": continue

            if value < 0: oslg.negative(key, mth, CN.WRN)
            if abs(value) < CN.TOL: value = 0.0

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Log/reset (or abandon) conflicting user-set geometry key:value pairs:
    #   "head"       e.g. std 80" door + frame/buffers (+ m)
    #   "sill"       e.g. std 30" sill + frame/buffers (+ m)
    #   "height"     any sub surface height, below "head" (+ m)
    #   "width"      e.g. 1.2 m
    #   "offset"     if array (+ m)
    #   "centreline" left or right of base surface centreline (+/- m)
    #   "r_buffer"   buffer between sub/array and right-side corner (+ m)
    #   "l_buffer"   buffer between sub/array and left-side corner (+ m)
    #
    # If successful, this will generate sub surfaces and add them to the model.
    for sub in subs:
        # Set-up unique sub parameters:
        #   - Frame & Divider "width"
        #   - minimum "clear glazing" limits
        #   - buffers, etc.
        ide        = sub["id"]
        frame      = sub["frame"].frameWidth() if sub["frame"] else 0
        frames     = 2 * frame
        buffer     = frame + bfr
        buffers    = 2 * buffer
        dim        = 3 * frame if 3 * frame > 0.200 else 0.200
        glass      = dim - frames
        min_sill   = buffer
        min_head   = buffers + glass
        max_head   = max_y - buffer
        max_sill   = max_head - (buffers + glass)
        min_ljamb  = buffer
        max_ljamb  = max_x - (buffers + glass)
        min_rjamb  = buffers + glass
        max_rjamb  = max_x - buffer
        max_height = max_y - buffers
        max_width  = max_x - buffers

        # Default sub surface "head" & "sill" height, unless user-specified.
        typ_head = CN.HEAD
        typ_sill = CN.SILL

        if "ratio" in sub:
            if sub["ratio"] > 0.75 or stype.lower() != "wall":
                typ_head = mid_y * (1 + sub["ratio"])
                typ_sill = mid_y * (1 - sub["ratio"])

        # Log/reset "height" if beyond min/max.
        if "height" in sub:
            if (sub["height"] < glass - CN.TOL2 or
                sub["height"] > max_height + CN.TOL2):

                m = "Reset '%s' height %.3fm (%s)" % (ide, sub["height"], mth)
                oslg.log(CN.WRN, m)
                sub["height"] = clamp(sub["height"], glass, max_height)
                m = "Height '%s' reset to %.3fm (%s)" % (ide, sub["height"], mth)
                oslg.log(CN.WRN, m)

        # Log/reset "head" height if beyond min/max.
        if "head" in sub:
            if (sub["head"] < min_head - CN.TOL2 or
                sub["head"] > max_head + CN.TOL2):

                m = "Reset '%s' head %.3fm (%s)" % (ide, sub["head"], mth)
                oslg.log(CN.WRN, m)
                sub["head"] = clamp(sub["head"], min_head, max_head)
                m = "Head '%s' reset to %.3fm (%s)" % (ide, sub["head"], mth)
                oslg.log(CN.WRN, m)

        # Log/reset "sill" height if beyond min/max.
        if "sill" in sub:
            if (sub["sill"] < min_sill - CN.TOL2 or
                sub["sill"] > max_sill + CN.TOL2):

                m = "Reset '%s' sill %.3fm (%s)" % (ide, sub["sill"], mth)
                oslg.log(CN.WRN, m)
                sub["sill"] = clamp(sub["sill"], min_sill, max_sill)
                m = "Sill '%s reset to %.3fm (%s)" % (ide, sub["sill"], mth)
                oslg.log(CN.WRN, m)

        # At this point, "head", "sill" and/or "height" have been tentatively
        # validated (and/or have been corrected) independently from one another.
        # Log/reset "head" & "sill" heights if conflicting.
        if "head" in sub and "sill" in sub and sub["head"] < sub["sill"] + glass:
            sill = sub["head"] - glass

            if sill < min_sill - CN.TOL2:
                sub["count"     ] = 0
                sub["multiplier"] = 0

                if "ratio" in sub: sub["ratio"  ] = 0
                if "height" in sub: sub["height"] = 0
                if "width" in sub: sub["width"  ] = 0

                m = "Skip: invalid '%s' head/sill combo (%s)" % (ide, mth)
                oslg.log(CN.ERR, m)
                continue
            else:
                m = "Reset '%s' sill %.3fm (%s)" % (ide, sub["sill"], mth)
                oslg.log(CN.WRN, m)
                sub["sill"] = sill
                m = "Sill '%s' reset to %.3fm (%s)" % (ide, sub["sill"], mth)
                oslg.log(CN.WRN, m)

        # Attempt to reconcile "head", "sill" and/or "height". If successful,
        # all 3x parameters are set (if missing), or reset if invalid.
        if "head" in sub and "sill" in sub:
            hght = sub["head"] - sub["sill"]

            if "height" in sub and abs(sub["height"] - hght) > CN.TOL2:
                m1 = "Reset '%s' height %.3fm (%s)" % (ide, sub["height"], mth)
                m2 = "Height '%s' reset %.3fm (%s)" % (ide, hght, mth)
                oslg.log(CN.WRN, m1)
                oslg.log(CN.WRN, m2)

            sub["height"] = hght

        elif "head" in sub:# no "sill"
            if "height" in sub:
                sill = sub["head"] - sub["height"]

                if sill < min_sill - CN.TOL2:
                    sill = min_sill
                    hght = sub["head"] - sill

                    if hght < glass:
                        sub["count"     ] = 0
                        sub["multiplier"] = 0

                        if "ratio" in sub: sub["ratio"  ] = 0
                        if "height" in sub: sub["height"] = 0
                        if "width"  in sub: sub["width" ] = 0

                        m = "Skip: invalid '%s' head/height combo (%s)" % (ide, mth)
                        oslg.log(CN.ERR, m)
                        continue
                    else:
                        m = "Reset '%s' height %.3fm (%s)" % (ide, sub["height"], mth)
                        oslg.log(CN.WRN, m)
                        sub["sill"  ] = sill
                        sub["height"] = hght
                        m = "Height '%s' re(set) %.3fm (%s)" % (ide, sub["height"], mth)
                        oslg.log(CN.WRN, m)
                else:
                    sub["sill"] = sill
            else:
                sub["sill"  ] = typ_sill
                sub["height"] = sub["head"] - sub["sill"]

        elif "sill" in sub: # no "head"
            if "height" in sub:
                head = sub["sill"] + sub["height"]

                if head > max_head - CN.TOL2:
                    head = max_head
                    hght = head - sub["sill"]

                    if hght < glass:
                        sub["count"     ] = 0
                        sub["multiplier"] = 0

                        if "ratio"  in sub: sub["ratio" ] = 0
                        if "height" in sub: sub["height"] = 0
                        if "width"  in sub: sub["width" ] = 0

                        m = "Skip: invalid '%s' sill/height combo (%s)" % (ide, mth)
                        oslg.log(CN.ERR, m)
                        continue
                    else:
                        m = "Reset '%s' height %.3fm (%s)" % (ide, sub["height"], mth)
                        oslg.log(CN.WRN, m)
                        sub["head"  ] = head
                        sub["height"] = hght
                        m = "Height '%s' reset to %.3fm (%s)" % (ide, sub["height"], mth)
                        oslg.log(CN.WRN, m)
                else:
                    sub["head"] = head
            else:
                sub["head"  ] = typ_head
                sub["height"] = sub["head"] - sub["sill"]

        elif "height" in sub: # neither "head" nor "sill"
            head = mid_y + sub["height"]/2 if s00 else typ_head
            sill = head - sub["height"]

            if sill < min_sill:
                sill = min_sill
                head = sill + sub["height"]

            sub["head"] = head
            sub["sill"] = sill

        else:
            sub["head"  ] = typ_head
            sub["sill"  ] = typ_sill
            sub["height"] = sub["head"] - sub["sill"]

        # Log/reset "width" if beyond min/max.
        if "width" in sub:
            if (sub["width"] < glass - CN.TOL2 or
                sub["width"] > max_width + CN.TOL2):

                m = "Reset '%s' width %.3fm (%s)" % (ide, sub["width"], mth)
                oslg.log(CN.WRN, m)
                sub["width"] = clamp(sub["width"], glass, max_width)
                m = "Width '%s' reset to %.3fm ()%s)" % (ide, sub["width"], mth)
                oslg.log(CN.WRN, m)

        # Log/reset "count" if < 1 (or not an Integer)
        try:
            sub["count"] = int(sub["count"])
        except:
            sub["count"] = 1

        if sub["count"] < 1:
            sub["count"] = 1
            oslg.log(CN.WRN, "Reset '%s' count to min 1 (%s)" % (ide, mth))

        # Log/reset if left-sided buffer under min jamb position.
        if "l_buffer" in sub:
            if sub["l_buffer"] < min_ljamb - CN.TOL:
                m = "Reset '%s' left buffer %.3fm (%s)" % (ide, sub["l_buffer"], mth)
                oslg.log(WRN, m)
                sub["l_buffer"] = min_ljamb
                m = "Left buffer '%s' reset to %.3fm (%s)" % (ide, sub["l_buffer"], mth)
                oslg.log(WRN, m)

        # Log/reset if right-sided buffer beyond max jamb position.
        if "r_buffer" in sub:
            if sub["r_buffer"] > max_rjamb - CN.TOL:
                m = "Reset '%s' right buffer %.3fm (%s)" % (ide, sub["r_buffer"], mth)
                oslg.log(CN.WRN, m)
                sub["r_buffer"] = min_rjamb
                m = "Right buffer '%s' reset to %.3fm (%s)" % (ide, sub["r_buffer"], mth)
                oslg.log(CN.WRN, m)

        centre  = mid_x
        if "centreline" in sub: centre += sub["centreline"]

        n  = sub["count" ]
        h  = sub["height"] + frames
        w  = 0 # overall width of sub(s) bounding box (to calculate)
        x0 = 0 # left-side X-axis coordinate of sub(s) bounding box
        xf = 0 # right-side X-axis coordinate of sub(s) bounding box

        # Log/reset "offset", if conflicting vs "width".
        if "ratio" in sub:
            if sub["ratio"] < CN.TOL:
                sub["ratio"     ] = 0
                sub["count"     ] = 0
                sub["multiplier"] = 0

                if "height" in sub: sub["height"] = 0
                if "width"  in sub: sub["width" ] = 0

                oslg.log(CN.ERR, "Skip: ratio ~0 (%s)" % mth)
                continue

            # Log/reset if "ratio" beyond min/max?
            if sub["ratio"] < mn and sub["ratio"] > mx:
                m = "Reset ratio %.3f (%s)" % (sub["ratio"], mth)
                oslg.log(CN.WRN, m)
                sub["ratio"] = clamp(sub["ratio"], mn, mx)
                m = "Ratio reset to %.3f (%s)" % (sub["ratio"], mth)
                oslg.log(CN.WRN, m)

            # Log/reset "count" unless 1.
            if sub["count"] != 1:
                sub["count"] = 1
                oslg.log(CN.WRN, "Count (ratio) reset to 1 (%s)" % mth)

            area = s.grossArea() * sub["ratio"] # sub m2, incl. frames
            w    = area / h
            wdth = w - frames
            x0   = centre - w/2
            xf   = centre + w/2

            if "l_buffer" in sub:
                if "centreline" in sub:
                    m = "Skip '%s' left buffer (vs centreline) (%s)" % (ide, mth)
                    oslg.log(CN.WRN, m)
                else:
                    x0     = sub["l_buffer"] - frame
                    xf     = x0 + w
                    centre = x0 + w/2
            elif "r_buffer" in sub:
                if "centreline" in sub:
                    m = "Skip '%s' right buffer (vs centreline) (%s)" % (ide, mth)
                    oslg.log(CN.WRN, m)
                else:
                    xf     = max_x - sub["r_buffer"] + frame
                    x0     = xf - w
                    centre = x0 + w/2

            # Too wide?
            if x0 < min_ljamb - CN.TOL2 or xf > max_rjamb - CN.TOL2:
                sub["count"     ] = 0
                sub["multiplier"] = 0

                if "ratio"  in sub: sub["ratio" ] = 0
                if "height" in sub: sub["height"] = 0
                if "width"  in sub: sub["width" ] = 0

                m = "Skip '%s': invalid (ratio) width/centreline (%s)" % (ide, mth)
                oslg.log(CN.ERR, m)
                continue

            if "width" in sub and abs(sub["width"] - wdth) > CN.TOL:
                m = "Reset '%s' width (ratio) %.3fm (%s)" % (ide, sub["width"], mth)
                oslg.log(CN.WRN, m)
                sub["width"] = wdth
                m = "Width (ratio) '%s' reset to %.3fm (%s)" % (ide, sub["width"], mth)
                oslg.log(CN.WRN, m)

            if "width" not in sub: sub["width"] = wdth

        else:
            if "width" not in sub:
                sub["count"     ] = 0
                sub["multiplier"] = 0

                if "ratio"  in sub: sub["ratio" ] = 0
                if "height" in sub: sub["height"] = 0
                if "width"  in sub: sub["width" ] = 0

                oslg.log(CN.ERR, "Skip: missing '%s' width (%s})" % (ide, mth))
                continue

            wdth = sub["width"] + frames
            gap  = (max_x - n * wdth) / (n + 1)

            if "offset" in sub: gap = sub["offset"] - wdth
            if gap < buffer: gap = 0

            offst = gap + wdth

            if "offset" in sub and abs(offst - sub["offset"]) > CN.TOL:
                m = "Reset '%s' sub offset %.3fm (%s)" % (ide, sub["offset"], mth)
                oslg.log(CN.WRN, m)
                sub["offset"] = offst
                m = "Sub offset (%s) reset to %.3fm (%s)" % (ide, sub["offset"], mth)
                oslg.log(CN.WRN, m)

            if "offset" not in sub: sub["offset"] = offst

            # Overall width (including frames) of bounding box around array.
            w  = n * wdth + (n - 1) * gap
            x0 = centre - w/2
            xf = centre + w/2

            if "l_buffer" in sub:
                if "centreline" in sub:
                    m = "Skip '%s' left buffer (vs centreline) (%s)" % (ide, mth)
                    oslg.log(CN.WRN, m)
                else:
                    x0     = sub["l_buffer"] - frame
                    xf     = x0 + w
                    centre = x0 + w/2
            elif "r_buffer" in sub:
                if "centreline" in sub:
                    m = "Skip '%s' right buffer (vs centreline) (%s)" % (ide, mth)
                    oslg.log(WRN, m)
                else:
                    xf     = max_x - sub["r_buffer"] + frame
                    x0     = xf - w
                    centre = x0 + w/2

            # Too wide?
            if x0 < buffer - CN.TOL2 or xf > max_x - buffer - CN.TOL2:
                sub["count"     ] = 0
                sub["multiplier"] = 0
                if "ratio"  in sub: sub["ratio" ] = 0
                if "height" in sub: sub["height"] = 0
                if "width"  in sub: sub["width" ] = 0
                m = "Skip: invalid array width/centreline (%s)" % mth
                oslg.log(CN.ERR, m)
                continue

        # Initialize left-side X-axis coordinate of only/first sub.
        pos = x0 + frame

        # Generate sub(s).
        for i in range(sub["count"]):
            name = "%s:%d" % (ide, i)
            fr   = sub["frame"].frameWidth() if sub["frame"] else 0
            vec  = openstudio.Point3dVector()
            vec.append(openstudio.Point3d(pos,              sub["head"], 0))
            vec.append(openstudio.Point3d(pos,              sub["sill"], 0))
            vec.append(openstudio.Point3d(pos+sub["width"], sub["sill"], 0))
            vec.append(openstudio.Point3d(pos+sub["width"], sub["head"], 0))
            vec = t * (s00["r"] * (s00["t"] * vec)) if s00 else t * vec

            # Log/skip if conflict between individual sub and base surface.
            vc = offset(vec, fr, 300) if fr > 0 else p3Dv(vec)

            if not fits(vc, s):
                m = "Skip '%s': won't fit in '%s' (%s)" % (name, nom, mth)
                oslg.log(CN.ERR, m)
                break

            # Log/skip if conflicts with existing subs (even if same array).
            conflict = False

            for sb in s.subSurfaces():
                fd = sb.windowPropertyFrameAndDivider()
                fr = fd.get().frameWidth() if fd else 0
                vk = sb.vertices()
                if fr > 0: vk = offset(vk, fr, 300)

                if overlapping(vc, vk):
                    nome = sb.nameString()
                    m    = "Skip '%s': overlaps '%s' (%s)" % (name, nome, mth)
                    oslg.log(CN.ERR, m)
                    conflict = True
                    break

            if conflict: break

            sb = openstudio.model.SubSurface(vec, mdl)
            sb.setName(name)
            sb.setSubSurfaceType(sub["type"])
            if sub["assembly"]: sb.setConstruction(sub["assembly"])
            if sub["multiplier"] > 1: sb.setMultiplier(sub["multiplier"])

            if sub["frame"] and sb.allowWindowPropertyFrameAndDivider():
                sb.setWindowPropertyFrameAndDivider(sub["frame"])

            sb.setSurface(s)

            # Reset "pos" if array.
            if "offset" in sub: pos += sub["offset"]

    return True


def grossRoofArea(spaces=[]) -> float:
    """Returns the 'gross' roof surface area above selected conditioned,
    occupied spaces. This includes all roof surfaces of indirectly-conditioned,
    unoccupied spaces like plenums (if located above any of the selected
    spaces). This also includes roof surfaces of unconditioned or unenclosed
    spaces like attics, if vertically-overlapping any ceiling of occupied
    spaces below; attic roof sections above uninsulated soffits are excluded,
    for instance. It does not include surfaces labelled as 'RoofCeiling', which
    do not comply with ASHRAE 90.1 or NECB tilt criteria - see 'isRoof'.

    Args:
        spaces (list):
            A collection of openstudio.model.Space instances.

    Returns:
        float: Gross roof surface area.
        0: If invalid inputs (see logs).

    """
    mth = "osut.grossRoofArea"
    up  = openstudio.Point3d(0,0,1) - openstudio.Point3d(0,0,0)
    rm2 = 0
    rfs = {}

    if isinstance(spaces, openstudio.model.Space): spaces = [spaces]

    try:
        spaces = list(spaces)
    except:
        return oslg.invalid("spaces", mth, 1, CN.DBG, rm2)

    spaces = [s for s in spaces if isinstance(s, openstudio.model.Space)]
    spaces = [s for s in spaces if s.partofTotalFloorArea()]
    spaces = [s for s in spaces if not isUnconditioned(s)]

    # The method is very similar to OpenStudio-Standards' :
    #   find_exposed_conditioned_roof_surfaces(model)
    #
    # github.com/NREL/openstudio-standards/blob/
    # be81bd88dc55a44d8cce3ee6daf29c768032df6a/lib/openstudio-standards/
    # standards/Standards.Surface.rb#L99
    #
    # ... yet differs with regards to attics with overhangs/soffits.

    # Start with roof surfaces of occupied, conditioned spaces.
    for space in spaces:
        for roof in facets(space, "Outdoors", "RoofCeiling"):
            ide = roof.nameString()
            if ide in rfs: continue
            if not isRoof(roof): continue

            rfs[ide] = dict(m2=roof.grossArea(), m=space.multiplier())

    # Roof surfaces of unoccupied, conditioned spaces above (e.g. plenums)?
    for space in spaces:
        for ceiling in facets(space, "Surface", "RoofCeiling"):
            floor = ceiling.adjacentSurface()
            if not floor: continue

            other = floor.get().space()
            if not other: continue

            other = other.get()
            if other.partofTotalFloorArea(): continue
            if isUnconditioned(other): continue

            for roof in facets(other, "Outdoors", "RoofCeiling"):
                ide = roof.nameString()
                if ide in rfs: continue
                if not isRoof(roof): continue

                rfs[ide] = dict(m2=roof.grossArea(), m=other.multiplier())

    # Roof surfaces of unoccupied, unconditioned spaces above (e.g. attics)?
    # @todo: recursive call for stacked spaces as atria (via AirBoundaries).
    for space in spaces:
        # When taking overlaps into account, target spaces often do not share
        # the same local transformation as the space(s) above.
        t0 = transforms(space)
        if t0["t"] is None: continue

        t0 = t0["t"]

        for ceiling in facets(space, "Surface", "RoofCeiling"):
            cv0 = t0 * ceiling.vertices()

            floor = ceiling.adjacentSurface()
            if not floor: continue

            other = floor.get().space()
            if not other: continue

            other = other.get()
            if other.partofTotalFloorArea(): continue
            if not isUnconditioned(other): continue

            ti = transforms(other)
            if ti["t"] is None: continue

            ti = ti["t"]

            for roof in facets(other, "Outdoors", "RoofCeiling"):
                ide = roof.nameString()
                if not isRoof(roof): continue

                rvi  = ti * roof.vertices()
                cst  = cast(cv0, rvi, up)
                if not cst: continue

                # The overlap calculations below fail for roof and ceiling
                # surfaces holding previously-added leader lines.
                #
                # @todo: revise approach for attics ONCE skylight wells have
                # been added.
                olap = overlap(cst, rvi, False)
                if not olap: continue

                m2 = openstudio.getArea(olap)
                if not m2: continue

                m2 = m2.get()
                if m2 < CN.TOL2: continue
                if ide not in rfs: rfs[ide] = dict(m2=0, m=other.multiplier())

                rfs[ide]["m2"] += m2

    for rf in rfs.values():
        rm2 += rf["m2"] * rf["m"]

    return rm2


def horizontalRidges(rufs=[]) -> list:
    """Identifies horizontal ridges along 2x sloped 'roof' surfaces (same
    space) - see 'isRoof'. Harmonized with OpenStudio's "alignZPrime" - see
    'isSloped'.

    Args:
        rufs (list):
            A Collection of 'roof' openstudio.model.Surface instances.

    Returns:
        list: A collection of horizontal roof ridge dictionaries:
        - "edge" (openstudio.Point3dVector): both edge endpoints
        - "length" (float): individual horizontal roof ridge length
        - "roofs" (list): 2x linked roof surfaces, on either side of the edge

    """
    mth    = "osut.horizontalRidges"
    ridges = []

    try:
        rufs = list(rufs)
    except:
        return ridges

    rufs = [s for s in rufs if isinstance(s, openstudio.model.Surface)]
    rufs = [s for s in rufs if isSloped(s)]
    rufs = [s for s in rufs if isRoof(s)]

    for roof in rufs:
        if not roof.space(): continue

        space = roof.space().get()
        maxZ  = max([pt.z() for pt in roof.vertices()])

        for edge in segments(roof):
            if not shareXYZ(edge, "z", maxZ): continue

            # Skip if already tracked.
            match = False

            for ridge in ridges:
                if match: break

                edg   = list(ridge["edge"])
                edg2  = edg.reverse()
                match = areSame(edge, edg) or areSame(edge, edg2)

            if match: continue

            ridge           = {}
            ridge["edge"  ] = edge
            ridge["length"] = (edge[1] - edge[0]).length()
            ridge["roofs" ] = [roof]

            # Links another roof (same space)?
            match = False

            for ruf in rufs:
                if match: break
                if ruf == roof: continue
                if not ruf.space(): continue
                if ruf.space().get() != space: continue

                for edg in segments(ruf):
                    if match: break

                    edg1 = list(edg)
                    edg2 = list(edg)
                    edg2.reverse()

                    if areSame(edge, edg1) or areSame(edge, edg2):
                        ridge["roofs"].append(ruf)
                        ridges.append(ridge)
                        match = True

    return ridges


def toToplit(spaces=[], opts={}) -> list:
    """Preselects ideal spaces to toplight, based on 'addSkylights' options and
    key building model geometry attributes. This can be called from within
    'addSkylights' by setting opts["ration"] to True (False by default).
    Alternatively, the method can be called prior to 'addSkylights'. The
    optional filters stem from previous rounds of 'addSkylights' stress testing.
    The goal is to allow users to prune away less ideal candidate spaces
    (irregular, smaller) in favour of (larger) candidates (notably with more
    suitable roof geometries). This is key when dealing with attic and plenums,
    where 'addSkylights' seeks to add skylight wells (relying on roof cut-outs
    and leader lines). Another check/outcome is whether to prioritize skylight
    allocation in already sidelit spaces: opts["sidelit"] may be set to True.

    Args:
        spaces (list):
            A collection of openstudio.model.Space instances.
        opts (dict):
            Requested skylight attributes (similar to 'addSkylights').
            - "size" (float): Template skylight width/depth (1.22m, min 0.4m)

    Returns:
        list: Favoured openstudio.model.Space candidates (see logs if empty).

    """
    mth  = "osut.toToplit"
    gap4 = 0.4  # minimum skylight 16" width/depth (excluding frame width)
    w    = 1.22 # default 48" x 48" skylight base

    if not isinstance(opts, dict):
        return oslg.mismatch("opts", opts, dict, mth, CN.DBG, [])

    # Validate skylight size, if provided.
    if "size" in opts:
        try:
            w = float(opts["size"])
        except:
            return oslg.mismatch("size", opts["size"], float, mth, CN.DBG, [])

    if round(w, 2) < gap4: return oslg.invalid("size", mth, 0, CN.ERR, [])

    w2 = w * w

    # Accept single 'OpenStudio::Model::Space' (vs an array of spaces). Filter.
    if isinstance(spaces, openstudio.model.Space): spaces = [spaces]

    try:
        spaces = list(spaces)
    except:
        return oslg.mismatch("spaces", spaces, list, mth, CN.DBG, [])

    # Whether individual spaces are UNCONDITIONED (e.g. attics, unheated areas)
    # or flagged as NOT being part of the total floor area (e.g. unoccupied
    # plenums), should of course reflect actual design intentions. It's up to
    # modellers to correctly flag such cases - can't safely guess in lieu of
    # design/modelling team.
    #
    # A friendly reminder: 'addSkylights' should be called separately for
    # strictly SEMIHEATED spaces vs REGRIGERATED spaces vs all other CONDITIONED
    # spaces, as per 90.1 and NECB requirements.
    spaces = [s for s in spaces if isinstance(s, openstudio.model.Space)]
    spaces = [s for s in spaces if s.partofTotalFloorArea()]
    spaces = [s for s in spaces if not isUnconditioned(s)]
    spaces = [s for s in spaces if not areVestibules(s)]
    spaces = [s for s in spaces if roofs(s)]
    spaces = [s for s in spaces if s.floorArea() >= 4 * w2]
    spaces = sorted(spaces, key=lambda s: s.floorArea(), reverse=True)
    if not spaces: return oslg.empty("spaces", mth, CN.WRN, [])

    # Unfenestrated spaces have no windows, glazed doors or skylights. By
    # default, 'addSkylights' will prioritize unfenestrated spaces (over all
    # existing sidelit ones) and maximize skylight sizes towards achieving the
    # required skylight area target. This concentrates skylights for instance in
    # typical (large) core spaces, vs (narrower) perimeter spaces. However, for
    # less conventional spatial layouts, this default approach can produce less
    # optimal skylight distributions. A balance is needed to prioritize large
    # unfenestrated spaces when appropriate on one hand, while excluding smaller
    # unfenestrated ones on the other. Here, exclusion is based on the average
    # floor area of spaces to toplight.
    fm2  = sum([s.floorArea() for s in spaces])
    afm2 = fm2 / len(spaces)

    unfen = [s for s in spaces if not isDaylit(s)]
    unfen = sorted(unfen, key=lambda s: s.floorArea(), reverse=True)

    # Target larger unfenestrated spaces, if sufficient in area.
    if unfen:
        if len(spaces) > len(unfen):
            ufm2  = sum([s.floorArea() for s in unfen])
            u0fm2 = unfen[0].floorArea()

            if ufm2 > 0.33 * fm2 and u0fm2 > 3 * afm2:
                unfen  = [s for s in unfen  if s.floorArea() < 0.25 * afm2]
                spaces = [s for s in spaces if s not in unfen]
            else:
                opts["sidelit"] = True
    else:
        opts["sidelit"] = True

    espaces = {}
    rooms   = []
    toits   = []

    # Gather roof surfaces - possibly those of attics or plenums above.
    for s in spaces:
        ide = s.nameString()
        m2  = s.floorArea()

        for rf in roofs(s):
            if ide not in espaces: espaces[ide] = dict(space=s, m2=m2, roofs=[])
            if rf not in espaces[ide]["roofs"]: espaces[ide]["roofs"].append(rf)

    # Priortize larger spaces.
    espaces = dict(sorted(espaces.items(), key=lambda s: s[1]["m2"], reverse=True))

    # Prioritize larger roof surfaces.
    for s in espaces.values():
        s["roofs"] = sorted(s["roofs"], key=lambda s: s.grossArea(), reverse=True)

    # Single out largest roof in largest space, key when dealing with shared
    # attics or plenum roofs.
    for s in espaces.values():
        rfs = [ruf for ruf in s["roofs"] if ruf not in toits]
        if not rfs: continue

        rfs = sorted(rfs, key=lambda ruf: ruf.grossArea(), reverse=True)

        toits.append(rfs[0])
        rooms.append(s["space"])

    if not rooms: oslg.log(CN.INF, "No ideal toplit candidates (%s)" % mth)

    return rooms


def addSkyLights(spaces=[], opts=dict) -> float:
    """Adds skylights to toplight selected OpenStudio (occupied, conditioned)
    spaces, based on requested skylight area, or a skylight-to-roof ratio
    (SRR%). If the user selects '0' m2 as the requested "area" (or '0' as the
    requested "srr"), while setting the option "clear" as True, the method
    simply purges all pre-existing roof fenestrated subsurfaces of selected
    spaces, and exits while returning '0' (without logging an error or warning).
    Pre-existing skylight wells are not cleared however. Pre-toplit spaces are
    otherwise ignored. Boolean options "attic", "plenum", "sloped" and "sidelit"
    further restrict candidate spaces to toplight. If applicable, options
    "attic" and "plenum" add skylight wells. Option "patterns" restricts preset
    skylight allocation layouts in order of preference; if left empty, all
    preset patterns are considered, also in order of preference (see examples).

    Args:
        spaces (list of openstudio.model.Space):
            One or more spaces to toplight.
        opts (dict):
            Requested skylight attributes:
            - "area" (float): overall skylight area.
            - "srr" (float): skylight-to-roof ratio (0.00, 0.90]
            - "size" (float): template skylight width/depth (min 0.4m)
            - "frame" (openstudio.model.WindowPropertyFrameAndDivider): optional
            - "clear" (bool): whether to first purge existing skylights
            - "ration" (bool): finer selection of candidates to toplight
            - "sidelit" (bool): whether to consider sidelit spaces
            - "sloped" (bool): whether to consider sloped roof surfaces
            - "plenum" (bool): whether to consider plenum wells
            - "attic" (bool): whether to consider attic wells

    Returns:
        float: 'Gross roof area' if successful (see logs if 0 m2)

    """
    mth   = "osut.addSkyLights"
    clear = True
    srr   = None
    area  = None
    frame = None  # FrameAndDivider object
    f     = 0.0   # FrameAndDivider frame width
    gap   = 0.1   # min 2" around well (2x == 4"), as well as max frame width
    gap2  = 0.2   # 2x gap
    gap4  = 0.4   # minimum skylight 16" width/depth (excluding frame width)
    bfr   = 0.005 # minimum array perimeter buffer (no wells)
    w     = 1.22  # default 48" x 48" skylight base
    w2    = w * w # m2
    v     = int("".join(openstudio.openStudioVersion().split(".")))

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Excerpts of ASHRAE 90.1 2022 definitions:
    #
    # "ROOF":
    #
    #   "the upper portion of the building envelope, including opaque areas and
    #   fenestration, that is horizontal or tilted at an angle of less than 60
    #   degrees from horizontal. For the purposes of determining building
    #   envelope requirements, the classifications are defined as follows
    #   (inter alia):
    #
    #     - attic and other roofs: all other roofs, including roofs with
    #       insulation ENTIRELY BELOW (inside of) the roof structure (i.e.
    #       attics, cathedral ceilings, and single-rafter ceilings), roofs with
    #       insulation both above and BELOW the roof structure, and roofs
    #       without insulation but excluding metal building roofs. [...]"
    #
    # "ROOF AREA, GROSS":
    #
    #   "the area of the roof measured from the EXTERIOR faces of walls or from
    #   the centerline of party walls."
    #
    #
    # For the simple case below (steep 4-sided hip roof, UNENCLOSED ventilated
    # attic), 90.1 users typically choose between either:
    #   1. modelling the ventilated attic explicitly, or
    #   2. ignoring the ventilated attic altogether.
    #
    # If skylights were added to the model, option (1) would require one or more
    # skylight wells (light shafts leading to occupied spaces below), with
    # insulated well walls separating CONDITIONED spaces from an UNENCLOSED,
    # UNCONDITIONED space (i.e. attic).
    #
    # Determining which roof surfaces (or which portion of roof surfaces) need
    # to be considered when calculating "GROSS ROOF AREA" may be subject to some
    # interpretation. From the above definitions:
    #
    #   - the uninsulated, tilted hip-roof attic surfaces are considered "ROOF"
    #     surfaces, provided they 'shelter' insulation below (i.e. insulated
    #     attic floor).
    #   - however, only the 'projected' portion of such "ROOF" surfaces, i.e.
    #     areas between axes AA` and BB` (along exterior walls)) would be
    #     considered.
    #   - the portions above uninsulated soffits (illustrated on the right)
    #     would be excluded from the "GROSS ROOF AREA" as they are beyond the
    #     exterior wall projections.
    #
    #     A         B
    #     |         |
    #      _________
    #     /          \                  /|        |\
    #    /            \                / |        | \
    #   /_  ________  _\    = >       /_ |        | _\   ... excluded portions
    #     |          |
    #     |__________|
    #     .          .
    #     A`         B`
    #
    # If the unoccupied space (directly under the hip roof) were instead an
    # INDIRECTLY-CONDITIONED plenum (not an attic), then there would be no need
    # to exclude portions of any roof surface: all plenum roof surfaces (in
    # addition to soffit surfaces) would need to be insulated). The method takes
    # such circumstances into account, which requires vertically casting
    # surfaces onto others, as well as overlap calculations. If successful, the
    # method returns the "GROSS ROOF AREA" (in m2), based on the above rationale.
    #
    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Excerpts of similar NECB requirements (unchanged from 2011 through 2020):
    #
    #   3.2.1.4. 2). "The total skylight area shall be less than 2% of the GROSS
    #   ROOF AREA as determined in Article 3.1.1.6." (5% in earlier versions)
    #
    #   3.1.1.6. 5). "In the calculation of allowable skylight area, the GROSS
    #   ROOF AREA shall be calculated as the sum of the areas of insulated
    #   roof including skylights."
    #
    # There are NO additional details or NECB appendix notes on the matter. It
    # is unclear if the NECB's looser definition of GROSS ROOF AREA includes
    # (uninsulated) sloped roof surfaces above (insulated) flat ceilings (e.g.
    # attics), as with 90.1. It would be definitely odd if it didn't. For
    # instance, if the GROSS ROOF AREA were based on insulated ceiling surfaces,
    # there would be a topological disconnect between flat ceiling and sloped
    # skylights above. Should NECB users first 'project' (sloped) skylight rough
    # openings onto flat ceilings when calculating SRR%? Without much needed
    # clarification, the (clearer) 90.1 rules equally apply here to NECB cases.

    # If skylight wells are indeed required, well wall edges are always vertical
    # (i.e. never splayed), requiring a vertical ray.
    origin = openstudio.Point3d(0,0,0)
    zenith = openstudio.Point3d(0,0,1)
    ray    = zenith - origin

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Accept a single openStudio.model.Space (vs an array of spaces).
    if isinstance(spaces, openstudio.model.Space): spaces = [spaces]

    try:
        spaces = list(spaces)
    except:
        return oslg.mismatch("spaces", spaces, list, mth, CN.DBG, [])

    spaces = [s for s in spaces if isinstance(s, openstudio.model.Space)]
    spaces = [s for s in spaces if s.partofTotalFloorArea()]
    spaces = [s for s in spaces if not isUnconditioned(s)]

    if not spaces:
        return oslg.empty("spaces", mth, CN.DBG, 0)

    mdl = spaces[0].model()

    # Exit if mismatched or invalid options.
    if not isinstance(opts, dict):
        return oslg.mismatch("opts", opts, dict, mth, CN.DBG, 0)

    # Validate Frame & Divider object, if provided.
    if "frame" in opts:
        frame = opts["frame"]

        if isinstance(frame, openstudio.model.WindowPropertyFrameAndDivider):
            if v < 321: frame = None
            if round(frame.frameWidth(), 2) < 0: frame = None
            if round(frame.frameWidth(), 2) > gap: frame = None

            if frame:
                f = frame.frameWidth()
            else:
                oslg.log(CN.ERR, "Skip Frame&Divider object (%s)" % mth)
        else:
            frame = None
            oslg.log(CN.ERR, "Skip invalid Frame&Divider object (%s)" % mth)

    # Validate skylight size, if provided.
    if "size" in opts:
        try:
            w = float(opts["size"])
        except:
            return oslg.mismatch("size", opts["size"], float, mth, CN.DBG, 0)

        if round(w, 2) < gap4: return oslg.invalid(size, mth, 0, CN.ERR, 0)

        w2 = w * w

    f2  = 2 * f
    w0  = w + f2
    w02 = w0 * w0
    wl  = w0 + gap
    wl2 = wl * wl

    # Validate requested skylight-to-roof ratio (or overall area).
    if "area" in opts:
        try:
            area = float(opts["area"])
        except:
            return oslg.mismatch("area", opts["area"], float, mth, CN.DBG, 0)

        if area < 0: oslg.log(CN.WRN, "Area reset to 0.0 m2 (%s)" % mth)
    elif "srr" in opts:
        try:
            srr = float(opts["srr"])
        except:
            return oslg.mismatch("srr", opts["srr"], float, mth, CN.DBG, 0)

            if srr < 0:
                oslg.log(CN.WRN, "SRR (%.2f) reset to 0% (%s)" % (srr, mth))
            if srr > 0.90:
                oslg.log(CN.WRN, "SRR (%.2f) reset to 90% (%s)" % (srr, mth))

            srr = clamp(srr, 0.00, 0.10)
    else:
        return oslg.hashkey("area", opts, "area", mth, CN.ERR, 0)

    # Validate purge request, if provided.
    if "clear" in opts:
        clear = opts["clear"]

        try:
            clear = bool(clear)
        except:
            log(CN.WRN, "Purging existing skylights by default (%s)" % mth)
            clear = True

    # Purge if requested.
    if clear:
        for s in roofs(spaces):
            for sub in s.subSurfaces(): sub.remove()

    # Safely exit, e.g. if strictly called to purge existing roof subsurfaces.
    if area and round(area, 2) == 0: return 0
    if srr  and round(srr,  2) == 0: return 0

    m2  = 0 # total existing skylight rough opening area
    rm2 = grossRoofArea(spaces) # excludes e.g. overhangs

    # Tally existing skylight rough opening areas.
    for space in spaces:
        mx = space.multiplier()

        for roof in facets(space, "Outdoors", "RoofCeiling"):
            for sub in roof.subSurfaces():
                if not isFenestration(sub): continue

                ide = sub.nameString()
                xm2 = sub.grossArea()

                if sub.allowWindowPropertyFrameAndDivider():
                    fd = sub.windowPropertyFrameAndDivider()

                    if fd:
                        fd   = fd.get()
                        fw   = fd.frameWidth()
                        vec  = offset(sub.vertices(), fw, 300)
                        aire = openstudio.getArea(vec)

                        if aire:
                            xm2 = aire.get()
                        else:
                            m = "Skip '%s': Frame&Divider (%s)" % (ide, mth)
                            oslg.log(CN.ERR, m)


                m2 += xm2 * sub.multiplier() * mx

    # Required skylight area to add.
    sm2 = area if area else rm2 * srr - m2

    # Warn/skip if existing skylights exceed or ~roughly match targets.
    if round(sm2, 2) < round(w02, 2):
        if m2 > 0:
            oslg.log(CN.INF, "Skip: skylight area > request (%s)" % mth)
            return rm2
        else:
            oslg.log(CN.INF, "Requested skylight area < min size (%s)" % mth)

    elif 0.9 * round(rm2, 2) < round(sm2, 2):
        oslg.log(CN.INF, "Skip: requested skylight area > 90% of GRA (%s)" % mth)
        return rm2

    if "ration" not in opts: opts["ration"] = True

    try:
        opts["ration"] = bool(opts["ration"])
    except:
        opts["ration"] = True

    # By default, seek ideal candidate spaces/roofs. Bail out if unsuccessful.
    if opts["ration"] is True:
        spaces = toToplit(spaces, opts)
        if not spaces: return rm2

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # The method seeks to insert a skylight array within the largest rectangular
    # 'bounded box' that neatly 'fits' within a given roof surface. This equally
    # applies to any vertically-cast overlap between roof and plenum (or attic)
    # floor, which in turn generates skylight wells. Skylight arrays are
    # inserted from left-to-right & top-to-bottom (as illustrated below), once a
    # roof (or cast 3D overlap) is 'aligned' in 2D.
    #
    # Depending on geometric complexity (e.g. building/roof concavity,
    # triangulation), the total area of bounded boxes may be significantly less
    # than the calculated "GROSS ROOF AREA", which can make it challenging to
    # attain the requested skylight area. If "patterns" are left unaltered, the
    # method will select those that maximize the likelihood of attaining the
    # requested target, to the detriment of spatial daylighting distribution.
    #
    # The default skylight module size is 1.22m x 1.22m (4' x 4'), which can be
    # overridden by the user, e.g. 2.44m x 2.44m (8' x 8'). However, skylight
    # sizes usually end up either contracted or inflated to exactly meet a
    # request skylight area or SRR%,
    #
    # Preset skylight allocation patterns (in order of precedence):
    #
    #    1. "array"
    #   _____________________
    #  |   _      _      _   |  - ?x columns ("cols") >= ?x rows (min 2x2)
    #  |  |_|    |_|    |_|  |  - SRR ~5% (1.22m x 1.22m), as illustrated
    #  |                     |  - SRR ~19% (2.44m x 2.44m)
    #  |   _      _      _   |  - +suitable for wide spaces (storage, retail)
    #  |  |_|    |_|    |_|  |  - ~1.4x height + skylight width 'ideal' rule
    #  |_____________________|  - better daylight distribution, many wells
    #
    #    2. "strips"
    #   _____________________
    #  |   _      _      _   |  - ?x columns (min 2), 1x row
    #  |  | |    | |    | |  |  - ~doubles %SRR ...
    #  |  | |    | |    | |  |  - SRR ~10% (1.22m x ?1.22m), as illustrated
    #  |  | |    | |    | |  |  - SRR ~19% (2.44m x ?1.22m)
    #  |  |_|    |_|    |_|  |  - ~roof monitor layout
    #  |_____________________|  - fewer wells
    #
    #    3. "strip"
    #    ____________________
    #   |                    |  - 1x column, 1x row (min 1x)
    #   |   ______________   |  - SRR ~11% (1.22m x ?1.22m)
    #   |  | ............ |  |  - SRR ~22% (2.44m x ?1.22m), as illustrated
    #   |  |______________|  |  - +suitable for elongated bounded boxes
    #   |                    |  - 1x well
    #   |____________________|
    #
    # @todo: Support strips/strip patterns along ridge of paired roof surfaces.
    layouts  = ["array", "strips", "strip"]
    patterns = []

    # Validate skylight placement patterns, if provided.
    if "patterns" in opts:
        try:
            opts["patterns"] = list(opts["patterns"])
        except:
            oslg.mismatch("patterns", opts["patterns"], list, mth, CN.DBG)


        for i, pattern in enumerate(opts["patterns"]):
            pattern = oslg.trim(pattern).lower()

            if not pattern:
                oslg.invalid("pattern %d" % (i+1), mth, 0, CN.ERR)
                continue

            if pattern in layouts: patterns.append(pattern)

    if not patterns: patterns = layouts

    # The method first attempts to add skylights in ideal candidate spaces:
    #   - large roof surface areas (e.g. retail, classrooms ... not corridors)
    #   - not sidelit (favours core spaces)
    #   - having flat roofs (avoids sloped roofs)
    #   - neither under plenums, nor attics (avoids wells)
    #
    # This ideal (albeit stringent) set of conditions is "combo a".
    #
    # If the requested skylight area has not yet been achieved (after initially
    # applying "combo a"), the method decrementally drops selection criteria and
    # starts over, e.g.:
    #   - then considers sidelit spaces
    #   - then considers sloped roofs
    #   - then considers skylight wells
    #
    # A maximum number of skylights are allocated to roof surfaces matching a
    # given combo, all the while giving priority to larger roof areas. An error
    # message is logged if the target isn't ultimately achieved.
    #
    # Through filters, users may in advance restrict candidate roof surfaces:
    #   b. above occupied sidelit spaces (False restricts to core spaces)
    #   c. that are sloped (False restricts to flat roofs)
    #   d. above INDIRECTLY CONDITIONED spaces (e.g. plenums, uninsulated wells)
    #   e. above UNCONDITIONED spaces (e.g. attics, insulated wells)
    filters = ["a", "b", "bc", "bcd", "bcde"]

    # Prune filters, based on user-selected options.
    for opt in ["sidelit", "sloped", "plenum", "attic"]:
        if opt not in opts: continue
        if opts[opt] is True: continue

        if opt == "sidelit":
            filters = [fil for fil in filters if "b" not in fil]
        elif opt == "sloped":
            filters = [fil for fil in filters if "c" not in fil]
        elif opt == "plenum":
            filters = [fil for fil in filters if "d" not in fil]
        elif opt == "attic":
            filters = [fil for fil in filters if "e" not in fil]

    filters = [fil for fil in filters if fil] # prune out any emptied pattern
    filters = list(set(filters))              # ensure uniqueness

    # Remaining filters may be further pruned automatically after space/roof
    # processing, depending on geometry, e.g.:
    #  - if there are no sidelit spaces: filter "b" will be pruned away
    #  - if there are no sloped roofs  : filter "c" will be pruned away
    #  - if no plenums are identified  : filter "d" will be pruned away
    #  - if no attics are identified   : filter "e" will be pruned away

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
    # Break down spaces (and connected spaces) into groups.
    ssets    = [] # subset of skylight arrays to deploy
    rooms    = {} # occupied CONDITIONED spaces to toplight
    plenums  = {} # unoccupied (INDIRECTLY-) CONDITIONED spaces above rooms
    attics   = {} # unoccupied UNCONDITIONED spaces above rooms
    ceilings = {} # of occupied CONDITIONED space (if plenums/attics)

    # Candidate 'rooms' to toplit - excludes plenums/attics.
    for space in spaces:
        ide = space.nameString()

        if isDaylit(space, False, True, False):
            oslg.log(CN.WRN, "%s is already toplit, skipping (%s)" % (ide, mth))
            continue

        # When unoccupied spaces are involved (e.g. plenums, attics), the
        # occupied space (to toplight) may not share the same local
        # transformation as its unoccupied space(s) above. Fetching site
        # transformation.
        t0 = transforms(space)
        if not t0["t"]: continue

        # Calculate space height.
        h = spaceHeight(space)

        if h < CN.TOL:
            oslg.zero("%s height", mth, CN.ERR)
            continue

        rooms[ide]            = {}
        rooms[ide]["space"  ] = space
        rooms[ide]["t0"     ] = t0["t"]
        rooms[ide]["m"      ] = space.multiplier()
        rooms[ide]["h"      ] = h
        rooms[ide]["roofs"  ] = facets(space, "Outdoors", "RoofCeiling")
        rooms[ide]["sidelit"] = isDaylit(space, True, False, False)

        # Fetch and process room-specific outdoor-facing roof surfaces.
        #   e.g. the most basic 'subset' to track:
        #   - no skylight wells (i.e. no leader lines)
        #   - 1x skylight array per roof surface
        #   - no need to consider site transformation
        for roof in rooms[ide]["roofs"]:
            if not isRoof(roof): continue

            vtx = roof.vertices()
            box = boundedBox(vtx)
            if not box: continue

            bm2 = openstudio.getArea(box)
            if not bm2: continue

            bm2 = bm2.get()
            if round(bm2, 2) < round(w02, 2): continue

            width = alignedWidth(box, True)
            depth = alignedHeight(box, True)
            if width < wl * 3: continue
            if depth < wl: continue

            # A subset is 'tight' if the area of its bounded box is
            # significantly smaller than that of its roof. A subset is 'thin' if
            # the depth of its bounded box is (too) narrow. If either is True,
            # some geometry rules may be relaxed to maximize allocated skylight
            # area. Neither apply to cases with skylight wells.
            tight = True if bm2 < roof.grossArea() / 2 else False
            thin  = True if round(depth, 2) < round(1.5 * wl, 2) else False

            sset            = {}
            sset["box"    ] = box
            sset["bm2"    ] = bm2
            sset["tight"  ] = tight
            sset["thin"   ] = thin
            sset["roof"   ] = roof
            sset["space"  ] = space
            sset["m"      ] = space.multiplier()
            sset["sidelit"] = rooms[ide]["sidelit"]
            sset["sloped" ] = isSloped(roof)
            sset["t0"     ] = rooms[ide]["t0"]
            sset["t"      ] = openstudio.Transformation.alignFace(vtx)
            ssets.append(sset)

    # Process outdoor-facing roof surfaces of plenums and attics above.
    for ide, room in rooms.items():
        t0    = room["t0"]
        space = room["space"]
        rufs  = [ruf for ruf in roofs(space) if ruf not in room["roofs"]]

        for ruf in rufs:
            id0 = ruf.nameString()
            vtx = ruf.vertices()
            if not isRoof(ruf): continue

            espace = ruf.space()
            if not espace: continue

            espace = espace.get()
            if espace.partofTotalFloorArea(): continue

            idx = espace.nameString()
            mx  = espace.multiplier()

            if mx != space.multiplier():
                m = "%s vs %s - multiplier mismatch (%s)" % (ide, idx, mth)
                log(CN.ERR, m)
                continue

            ti = transforms(espace)
            if not ti["t"]: continue

            ti   = ti["t"]
            rpts = ti * vtx

            # Process occupied room ceilings, as 1x or more are overlapping roof
            # surfaces above. Vertically cast, then fetch overlap.
            for clng in facets(space, "Surface", "RoofCeiling"):
                idee = clng.nameString()
                tpts = t0 * clng.vertices()
                ci0  = cast(tpts, rpts, ray)
                if not ci0: continue

                olap = overlap(rpts, ci0)
                if not olap: continue

                om2 = openstudio.getArea(olap)
                if not om2: continue

                om2 = om2.get()
                if round(om2, 2) < round(w02, 2): continue

                box = boundedBox(olap)
                if not box: continue

                # Adding skylight wells (plenums/attics) is contingent to safely
                # linking new base roof 'inserts' (as well as new ceiling ones)
                # through 'leader lines'. This requires an offset to ensure no
                # conflicts with roof or ceiling edges.
                #
                # @todo: Expand the method to factor in cases where simple
                #        'side' cutouts can be supported (no need for leader
                #        lines), e.g. skylight strips along roof ridges.
                box = offset(box, -gap, 300)
                if not box: continue

                bm2 = openstudio.getArea(box)
                if not bm2: continue

                bm2 = bm2.get()
                if round(bm2, 2) < round(wl2, 2): continue

                width = alignedWidth(box, True)
                depth = alignedHeight(box, True)
                if width < wl * 3: continue
                if depth < wl * 2: continue

                # Vertically cast box onto ceiling below.
                cbox = cast(box, tpts, ray)
                if not cbox: continue

                cm2 = openstudio.getArea(cbox)
                if not cm2: continue

                cm2  = cm2.get()
                box  = ti.inverse() * box
                cbox = t0.inverse() * cbox

                if idee not in ceilings:
                    floor = clng.adjacentSurface()
                    if not floor:
                        oslg.log(CN.ERR, "%s adjacent floor? (%s)" % (idee, mth))
                        continue

                    floor = floor.get()
                    if not floor.space():
                        oslg.log(CN.ERR, "%s space? (%s)" % (idee, mth))
                        continue

                    espce = floor.space().get()
                    if espce != espace:
                        ido = espce.nameString()
                        oslg.log(CN.ERR, "%s != %s? (%s)" % (ido, idx, mth))
                        continue

                    ceilings[idee]          = {}    # idee: ceiling surface ID
                    ceilings[idee]["clng" ] = clng  # ceiling surface itself
                    ceilings[idee]["id"   ] = ide   # its space's ID
                    ceilings[idee]["space"] = space # its space
                    ceilings[idee]["floor"] = floor # adjacent floor
                    ceilings[idee]["roofs"] = []    # collection of roofs above

                ceilings[idee]["roofs"].append(ruf)

                # Skylight subset key:values are more detailed with suspended
                # ceilings. The overlap ("olap") remains in 'transformed' site
                # coordinates (with regards to the roof). The "box" polygon
                # reverts to attic/plenum space coordinates, while the "cbox"
                # polygon is reset with regards to the occupied space
                # coordinates.
                sset            = {}
                sset["olap"   ] = olap
                sset["box"    ] = box
                sset["cbox"   ] = cbox
                sset["om2"    ] = om2
                sset["bm2"    ] = bm2
                sset["cm2"    ] = cm2
                sset["tight"  ] = False
                sset["thin"   ] = False
                sset["roof"   ] = ruf
                sset["space"  ] = space
                sset["m"      ] = space.multiplier()
                sset["clng"   ] = clng
                sset["t0"     ] = t0
                sset["ti"     ] = ti
                sset["t"      ] = openstudio.Transformation.alignFace(vtx)
                sset["sidelit"] = room["sidelit"]
                sset["sloped" ] = isSloped(ruf)

                if isUnconditioned(espace): # e.g. attic
                    if idx not in attics:   # idx = espace.nameString()
                        attics[idx]          = {}
                        attics[idx]["space"] = espace
                        attics[idx]["ti"   ] = ti
                        attics[idx]["m"    ] = mx
                        attics[idx]["bm2"  ] = 0
                        attics[idx]["roofs"] = []

                    attics[idx]["bm2"  ] += bm2
                    attics[idx]["roofs"].append(ruf)

                    sset["attic"] = espace

                    ceilings[idee]["attic"] = espace # adjacent attic (floor)
                else: # e.g. plenum
                    if idx not in plenums:
                        plenums[idx] = {}
                        plenums[idx]["space"] = espace
                        plenums[idx]["ti"   ] = ti
                        plenums[idx]["m"    ] = mx
                        plenums[idx]["bm2"  ] = bm2
                        plenums[idx]["roofs"] = []

                    plenums[idx]["bm2"  ] += bm2
                    plenums[idx]["roofs"].append(ruf)

                    sset["plenum"] = espace

                    ceilings[idee]["plenum"] = espace # adjacent plenum (floor)

                ssets.append(sset)
                break # only 1x unique ruf/ceiling pair.

    # Ensure uniqueness of plenum roofs.
    for attic in attics.values():
        ruufs = []
        ruufs = [ruf for ruf in attic["roofs"] if ruf not in ruufs]
        attic["roofs" ] = ruufs
        attic["ridges"] = horizontalRidges(attic["roofs"]) # @todo

    for plenum in plenums.values():
        ruufs = []
        ruufs = [ruf for ruf in plenum["roofs"] if ruf not in ruufs]
        plenum["roofs" ] = ruufs
        plenum["ridges"] = horizontalRidges(plenum["roofs"]) # @todo

    # Regardless of the selected skylight arrangement pattern, the solution only
    # considers attic/plenum subsets that can be successfully linked to leader
    # line anchors, for both roof and ceiling surfaces. First, attic/plenum roofs.
    for greniers in [attics, plenums]:
        k = "attic" if greniers == attics else "plenum"

        for grenier in greniers.values():
            for roof in grenier["roofs"]:
                sts = ssets
                sts = [st for st in sts if k       in st]
                sts = [st for st in sts if "space" in st]
                sts = [st for st in sts if "box"   in st]
                sts = [st for st in sts if "bm2"   in st]
                sts = [st for st in sts if "roof"  in st]

                sts = [st for st in sts if st[k     ] == grenier["space"]]
                sts = [st for st in sts if st["roof"] == roof]
                if not sts: continue

                sts = sorted(sts, key=lambda st: st["bm2"], reverse=True)
                genAnchors(roof, sts, "box")

    # Delete voided sets.
    ssets = [sset for sset in ssets if "void" not in sset]

    # Repeat leader line loop for ceilings.
    for ceiling in ceilings.values():
        k = "attic" if "attic" in ceiling else "plenum"
        if k not in ceiling: continue

        clng   = ceiling["clng" ] # ceiling surface
        space  = ceiling["space"] # its space
        espace = ceiling[k]       # adjacent (unoccupied) space above
        if "roofs" not in ceiling: continue

        stz = []

        for roof in ceiling["roofs"]:
            sts = ssets

            sts = [st for st in sts if k       in st]
            sts = [st for st in sts if "cbox"  in st]
            sts = [st for st in sts if "cm2"   in st]
            sts = [st for st in sts if "roof"  in st]
            sts = [st for st in sts if "clng"  in st]
            sts = [st for st in sts if "space" in st]

            sts = [st for st in sts if st[k      ] == espace]
            sts = [st for st in sts if st["roof" ] == roof]
            sts = [st for st in sts if st["clng" ] == clng]
            sts = [st for st in sts if st["space"] == space]
            if len(sts) != 1: continue

            stz.append(sts[0])

        if not stz: continue

        stz = sorted(stz, key=lambda st: st["cm2"], reverse=True)
        genAnchors(clng, stz, "cbox")

    # Delete voided sets.
    ssets = [sset for sset in ssets if "void" not in sset]
    if not ssets: return oslg.empty("subsets", mth, CN.WRN, rm2)

    # Sort subsets, from largest to smallest bounded box area.
    ssets = sorted(ssets, key=lambda st: st["bm2"] * st["m"], reverse=True)

    # Any sidelit and/or sloped roofs being targeted?
    # @todo: enable double-ridged, sloped roofs have double-sloped
    #        skylights/wells (patterns "strip"/"strips").
    sidelit = any(sset["sidelit"] for sset in ssets)
    sloped  = any(sset["sloped" ] for sset in ssets)

    # Average sandbox area + revised 'working' SRR%.
    sbm2 = sum(sset.get("bm2", 0) for sset in ssets)
    avm2 = sbm2 / len(ssets)
    srr2 = sm2 / len(ssets) / avm2

    # Precalculate skylight rows + cols, for each selected pattern. In the case
    # of 'cols x rows' arrays of skylights, the method initially overshoots
    # with regards to 'ideal' skylight placement, e.g.:
    #
    #   aceee.org/files/proceedings/2004/data/papers/SS04_Panel3_Paper18.pdf
    #
    # Skylight areas are subsequently contracted to strictly meet the target.
    for i, sset in enumerate(ssets):
        thin   = sset["thin"]
        tight  = sset["tight"]
        factor = 1.75 if tight else 1.25
        well   = "clng" in sset
        space  = sset["space"]
        room   = rooms[space.nameString()]
        h      = room["h"]
        width  = alignedWidth( sset["box"], True)
        depth  = alignedHeight(sset["box"], True)
        barea  = sset["om2"] if "om2" in sset else sset["bm2"]
        rtio   = barea / avm2
        skym2  = srr2 * barea * rtio

        # Flag subset if too narrow/shallow to hold a single skylight.
        if well:
            if round(width, 2) < round(wl, 2):
                oslg.log(CN.WRN, "subset #{i+1} well: Too narrow (%s)" % mth)
                sset["void"] = True
                continue

            if round(depth, 2) < round(wl, 2):
                oslg.log(CN.WRN, "subset #{i+1} well: Too shallow (%s)" % mth)
                sset["void"] = True
                continue
        else:
            if round(width, 2) < round(w0, 2):
                oslg.log(CN.WRN, "subset #{i+1}: Too narrow (%s)" % mth)
                sset["void"] = True
                continue

            if round(depth, 2) < round(w0, 2):
                oslg.log(CN.WRN, "subset #{i+1}: Too shallow (%s)" % mth)
                sset["void"] = True
                continue

        # Estimate number of skylight modules per 'pattern'. Default spacing
        # varies based on bounded box size (i.e. larger vs smaller rooms).
        for pattern in patterns:
            cols = 1
            rows = 1
            wx   = w0
            wy   = w0
            wxl  = wl if well else None
            wyl  = wl if well else None
            dX   = None
            dY   = None

            if pattern == "array": # min 2x cols x min 2x rows
                cols = 2
                rows = 2
                if thin: continue

                if tight:
                    sp = 1.4 * h / 2
                    lx = width - cols * wx
                    ly = depth - rows * wy
                    if round(lx, 2) < round(sp, 2): continue
                    if round(ly, 2) < round(sp, 2): continue

                    cols = int(round((width - wx) / (wx + sp)), 2) + 1
                    rows = int(round((depth - wy) / (wy + sp)), 2) + 1
                    if cols < 2: continue
                    if rows < 2: continue

                    dX = bfr + f
                    dY = bfr + f
                else:
                    sp = 1.4 * h

                    if well:
                        lx = (width - cols * wxl) / cols
                        ly = (depth - rows * wyl) / rows
                    else:
                        lx = (width - cols * wx) / cols
                        ly = (depth - rows * wy) / rows

                    if round(lx, 2) < round(sp, 2): continue
                    if round(ly, 2) < round(sp, 2): continue

                    if well:
                        cols = int(round(width / (wxl + sp), 2))
                        rows = int(round(depth / (wyl + sp), 2))
                    else:
                        cols = int(round(width / (wx + sp), 2))
                        rows = int(round(depth / (wy + sp), 2))

                    if cols < 2: continue
                    if rows < 2: continue

                    if well:
                        ly = (depth - rows * wyl) / rows
                    else:
                        ly = (depth - rows * wy) / rows

                    dY = ly / 2

                # Default allocated skylight area. If undershooting, inflate
                # skylight width/depth (with reduced spacing). For geometrically
                # -constrained cases, undershooting means not reaching 1.75x the
                # required target. Otherwise, undershooting means not reaching
                # 1.25x the required target. Any consequent overshooting is
                # later corrected.
                tm2 = wx * cols * wy * rows

                # Inflate skylight width/depth (and reduce spacing) to reach
                # target.
                if round(tm2, 2) < factor * round(skym2, 2):
                    ratio2 = 1 + (factor * skym2 - tm2) / tm2
                    ratio  = math.sqrt(ratio2)

                    sp  = wl
                    wx *= ratio
                    wy *= ratio

                    if well:
                        wxl = wx + gap
                        wyl = wy + gap

                    if tight:
                        lx = (width - 2 * (bfr + f) - cols * wx) / (cols - 1)
                        ly = (depth - 2 * (bfr + f) - rows * wy) / (rows - 1)
                        lx = sp if round(lx, 2) < round(sp, 2) else lx
                        ly = sp if round(ly, 2) < round(sp, 2) else ly
                        wx = (width - 2 * (bfr + f) - (cols - 1) * lx) / cols
                        wy = (depth - 2 * (bfr + f) - (rows - 1) * ly) / rows
                    else:
                        if well:
                            lx  = (width - cols * wxl) / cols
                            ly  = (depth - rows * wyl) / rows
                            lx  = sp if round(lx, 2) < round(sp, 2) else lx
                            ly  = sp if round(ly, 2) < round(sp, 2) else ly
                            wxl = (width - cols * lx) / cols
                            wyl = (depth - rows * ly) / rows
                            wx  = wxl - gap
                            wy  = wyl - gap
                            ly  = (depth - rows * wyl) / rows
                        else:
                            lx  = (width - cols * wx) / cols
                            ly  = (depth - rows * wy) / rows
                            lx  = sp if round(lx, 2) < round(sp, 2) else lx
                            ly  = sp if round(ly, 2) < round(sp, 2) else ly
                            wx  = (width - cols * lx) / cols
                            wy  = (depth - rows * ly) / rows
                            ly  = (depth - rows * wy) / rows

                        dY = ly / 2

            elif pattern == "strips": # min 2x cols x 1x row
                cols = 2

                if tight:
                    sp = h / 2
                    dX = bfr + f
                    lx = width - cols * wx
                    if round(lx, 2) < round(sp, 2): continue

                    cols = int(round((width - wx) / (wx + sp)), 2) + 1
                    if cols < 2: continue

                    if thin:
                        dY = bfr + f
                        wy = depth - 2 * dY
                        if round(wy, 2) < gap4: continue
                    else:
                        ly = depth - wy
                        if round(ly, 2) < round(wl, 2): continue

                    dY = ly / 2
                else:
                    sp = h

                    if well:
                        lx = (width - cols * wxl) / cols
                        if round(lx, 2) < round(sp, 2): continue

                        cols = int(round(width / (wxl + sp), 2))
                        if cols < 2: continue

                        ly = depth - wyl
                        dY = ly / 2
                        if round(ly, 2) < round(wl, 2): continue
                    else:
                        lx = (width - cols * wx) / cols
                        if round(lx, 2) < round(sp, 2): continue

                        cols = int(round(width / (wx + sp), 2))
                        if cols < 2: continue

                        if thin:
                            dY = bfr + f
                            wy = depth - 2 * dY
                            if round(wy, 2) < gap4: continue
                        else:
                            ly = depth - wy
                            if round(ly, 2) < round(wl, 2): continue

                            dY = ly / 2

                tm2 = wx * cols * wy

                # Inflate skylight depth to reach target.
                if round(tm2, 2) < factor * round(skym2, 2):
                    sp = wl

                    # Skip if already thin.
                    if not thin:
                        ratio2 = 1 + (factor * skym2 - tm2) / tm2

                        wy *= ratio2

                        if well:
                            wyl = wy + gap
                            ly  = depth - wyl
                            ly  = sp if round(ly, 2) < round(sp, 2) else ly
                            wyl = depth - ly
                            wy  = wyl - gap
                        else:
                            ly = depth - wy
                            ly = sp if round(ly, 2) < round(sp, 2) else ly
                            wy = depth - ly

                        dY = ly / 2

                tm2 = wx * cols * wy

                # Inflate skylight width (and reduce spacing) to reach target.
                if round(tm2, 2) < factor * round(skym2, 2):
                    ratio2 = 1 + (factor * skym2 - tm2) / tm2

                    wx *= ratio2
                    if well: wxl = wx + gap

                    if tight:
                        lx = (width - 2 * (bfr + f) - cols * wx) / (cols - 1)
                        lx = sp if round(lx, 2) < round(sp, 2) else lx
                        wx = (width - 2 * (bfr + f) - (cols - 1) * lx) / cols
                    else:
                        if well:
                            lx  = (width - cols * wxl) / cols
                            lx  = sp if round(lx, 2) < round(sp, 2) else lx
                            wxl = (width - cols * lx) / cols
                            wx  = wxl - gap
                        else:
                            lx  = (width - cols * wx) / cols
                            lx  = sp if round(lx, 2) < round(sp, 2) else lx
                            wx  = (width - cols * lx) / cols

            else: # "strip" 1 (long?) row x 1 column
                if tight:
                    sp = gap4
                    dX = bfr + f
                    wx = width - 2 * dX
                    if round(wx, 2) < round(sp, 2): continue

                    if thin:
                        dY = bfr + f
                        wy = depth - 2 * dY
                        if round(wy, 2) < round(sp, 2): continue
                    else:
                        ly = depth - wy
                        dY = ly / 2
                        if round(ly, 2) < round(sp, 2): continue
                else:
                    sp = wl
                    lx = width - wxl if well else width - wx
                    ly = depth - wyl if well else depth - wy
                    dY = ly / 2
                    if round(lx, 2) < round(sp, 2): continue
                    if round(ly, 2) < round(sp, 2): continue

                tm2 = wx * wy

                # Inflate skylight width (and reduce spacing) to reach target.
                if round(tm2, 2) < factor * round(skym2, 2):
                    if not tight:
                        ratio2 = 1 + (factor * skym2 - tm2) / tm2

                        wx *= ratio2

                        if well:
                            wxl = wx + gap
                            lx  = width - wxl
                            lx  = sp if round(lx, 2) < round(sp, 2) else lx
                            wxl = width - lx
                            wx  = wxl - gap
                        else:
                            lx  = width - wx
                            lx  = sp if round(lx, 2) < round(sp, 2) else lx
                            wx  = width - lx

                tm2 = wx * wy

                # Inflate skylight depth to reach target. Skip if already tight thin.
                if round(tm2, 2) < factor * round(skym2, 2):
                    if not thin:
                        ratio2 = 1 + (factor * skym2 - tm2) / tm2

                        wy *= ratio2

                        if well:
                            wyl = wy + gap
                            ly  = depth - wyl
                            ly  = sp if round(ly, 2) < round(sp, 2) else ly
                            wyl = depth - ly
                            wy  = wyl - gap
                        else:
                            ly = depth - wy
                            ly = sp if round(ly, 2) < round(sp, 2) else ly
                            wy = depth - ly

                        dY = ly / 2

            st          = {}
            st["tight"] = tight
            st["cols" ] = cols
            st["rows" ] = rows
            st["wx"   ] = wx
            st["wy"   ] = wy
            st["wxl"  ] = wxl
            st["wyl"  ] = wyl

            if dX: st["dX"] = dX
            if dY: st["dY"] = dY

            sset[pattern] = st

        if not any(pattern in sset for pattern in patterns): sset["void"] = True

    # Delete voided subsets.
    ssets = [sset for sset in ssets if "void" not in sset]
    if not ssets: return oslg.empty("subsets (2)", mth, CN.WRN, rm2)

    # Final reset of filters.
    if not sidelit: filters = [fil.replace("b", "") for fil in filters]
    if not sloped:  filters = [fil.replace("c", "") for fil in filters]
    if not plenums: filters = [fil.replace("d", "") for fil in filters]
    if not attics:  filters = [fil.replace("e", "") for fil in filters]

    filters = [fil for fil in filters if fil] # remove any empty filter strings
    flters  = []
    flters  = [fil for fil in filters if fil not in flters] # ensure uniqueness
    filters = flters

    # Initialize skylight area tally (to increment).
    skm2 = 0

    # Assign skylight pattern.
    for filter in filters:
        if round(skm2, 2) >= round(sm2, 2): continue

        dm2 = sm2 - skm2 # differential (remaining skylight area to meet).
        sts = [sset for sset in ssets if "pattern" not in sset]

        if "a" in filter:
            # Start with the default (ideal) allocation selection:
            # - large roof surface areas (e.g. retail, classrooms not corridors)
            # - not sidelit (favours core spaces)
            # - having flat roofs (avoids sloped roofs)
            # - not under plenums, nor attics (avoids wells)
            sts = [st for st in sts if not st["sidelit"]]
            sts = [st for st in sts if not st["sloped" ]]
            sts = [st for st in sts if "clng" not in st]
        else:
            if "b" not in filter: sts = [st for st in sts if not st["sidelit"]]
            if "c" not in filter: sts = [st for st in sts if not st["sloped" ]]
            if "d" not in filter: sts = [st for st in sts if "plenum" not in st]
            if "e" not in filter: sts = [st for st in sts if "attic"  not in st]

        if not sts: continue

        # Tally precalculated skylights per pattern (once filtered).
        fpm2 = {}

        for pattern in patterns:
            for st in sts:
                if pattern not in st: continue

                cols = st[pattern]["cols"]
                rows = st[pattern]["rows"]
                wx   = st[pattern]["wx"  ]
                wy   = st[pattern]["wy"  ]

                if pattern not in fpm2: fpm2[pattern] = dict(m2=0, tight=False)

                fpm2[pattern]["m2"] += st["m"] * wx * wy * cols * rows
                if st["tight"]: fpm2[pattern]["tight"] = True

        pattern = None
        if not fpm2: continue

        # Favour (large) arrays if meeting residual target, unless constrained.
        if "array" in fpm2:
            if dm2 < fpm2["array"]["m2"]:
                if "tight" not in fpm2["array"] or fpm2["array"]["tight"] is False:
                    pattern = "array"

        if not pattern:
            fpm2 = dict(sorted(fpm2.items(), key=lambda f2: f2[1]["m2"]))
            mnM2 = list(fpm2.values())[ 0]["m2"]
            mxM2 = list(fpm2.values())[-1]["m2"]

            if round(mnM2, 2) >= round(dm2, 2):
                # If not large array, then retain pattern generating smallest
                # skylight area if ALL patterns >= residual target
                # (deterministic sorting).
                fpm2 = dict(fpm2.items(), key=lambda f2: round(f2, 2) == round(mnM2, 2))

                if "array" in fpm2:
                    pattern = "array"
                elif "strips" in fpm2:
                    pattern = "strips"
                else: # "strip" in fpm2
                    pattern = "strip"
            else:
                # Pick pattern offering greatest skylight area
                # (deterministic sorting).
                fpm2 = dict(fpm2.items(), key=lambda f2: round(f2, 2) == round(mxM2, 2))

                if "strip" in fpm2:
                    pattern = "strip"
                elif "strips" in fpm2:
                    pattern = "strips"
                else: # "array" in fpm2
                    pattern = "array"

        skm2 += fpm2[pattern]["m2"]

        # Update matching subsets.
        for st in sts:
            for sset in ssets:
                if pattern not in sset: continue
                if st["roof"] != sset["roof"]: continue
                if not areSame(st["box"], sset["box"]): continue

                if "clng" in st:
                    if not "clng" in sset: continue
                    if st["clng"] != sset["clng"]: continue

                sset["pattern"] = pattern
                sset["cols"   ] = sset[pattern]["cols"]
                sset["rows"   ] = sset[pattern]["rows"]
                sset["w"      ] = sset[pattern]["wx"  ]
                sset["d"      ] = sset[pattern]["wy"  ]
                sset["w0"     ] = sset[pattern]["wxl" ]
                sset["d0"     ] = sset[pattern]["wyl" ]

                if "dX" in sset[pattern] and sset[pattern]["dX"]:
                    sset["dX"] = sset[pattern]["dX"]
                if "dY" in sset[pattern] and sset[pattern]["dY"]:
                    sset["dY"] = sset[pattern]["dY"]

    # Delete incomplete sets (same as rejected if 'voided').
    ssets = [sset for sset in ssets if "void" not in sset]
    ssets = [sset for sset in ssets if "pattern"  in sset]
    if not ssets: return oslg.empty("subsets (3)", mth, CN.WRN, rm2)

    # Skylight size contraction if overshot (e.g. scale down by -13% if > +13%).
    # Applied on a surface/pattern basis: individual skylight sizes may vary
    # from one surface to the next, depending on respective patterns.

    # First, skip subsets altogether if their total m2 < (skm2 - sm2). Only
    # considered if significant discrepancies vs average subset skylight m2.
    sbm2 = 0

    for sset in ssets:
        sbm2 += sset["cols"] * sset["w"] * sset["rows"] * sset["d"] * sset["m"]

    avm2 = sbm2 / len(ssets)

    if round(skm2, 2) > round(sm2, 2):
        ssets.reverse()

        for sset in ssets:
            if round(skm2, 2) <= round(sm2, 2): break

            stm2 = sset["cols"] * sset["w"] * sset["rows"] * sset["d"] * sset["m"]
            if round(stm2, 2) >= round(0.75 * avm2, 2): continue
            if round(stm2, 2) >= round(skm2 - sm2,  2): continue

            skm2 -= stm2
            sset["void"] = True

        ssets.reverse()

    ssets = [sset for sset in ssets if "void" not in sset]
    if not ssets: return oslg.empty("subsets (4)", mth, CN.WRN, rm2)

    # Size contraction: round 1: low-hanging fruit.
    if round(skm2, 2) > round(sm2, 2):
        ratio2 = 1 - (skm2 - sm2) / skm2
        ratio  = math.sqrt(ratio2)

        for sset in ssets:
            am2 = sset["cols"] * sset["w"] * sset["rows"] * sset["d"] * sset["m"]
            xr  = sset["w"]
            yr  = sset["d"]

            if xr > w0:
                xr = w0 if xr * ratio < w0 else xr * ratio

            if yr > w0:
                yr = w0 if yr * ratio < w0 else yr * ratio

            xm2 = sset["cols"] * xr * sset["rows"] * yr * sset["m"]
            if round(xm2, 2) == round(am2, 2): continue

            sset["dY"] += (sset["d"] - yr) / 2
            if "dX" in sset: sset["dX"] += (sset["w"] - xr) / 2

            sset["w" ] = xr
            sset["d" ] = yr
            sset["w0"] = sset["w"] + gap
            sset["d0"] = sset["d"] + gap

            skm2 -= (am2 - xm2)

    # Size contraction: round 2: prioritize larger subsets.
    adm2 = 0

    for sset in ssets:
        if round(sset["w"], 2) <= w0: continue
        if round(sset["d"], 2) <= w0: continue

        adm2 += sset["cols"] * sset["w"] * sset["rows"] * sset["d"] * sset["m"]

    if round(skm2, 2) > round(sm2, 2) and round(adm2, 2) > round(sm2, 2):
        ratio2 = 1 - (adm2 - sm2) / adm2
        ratio  = math.sqrt(ratio2)

        for sset in ssets:
            if round(sset["w"], 2) <= w0: continue
            if round(sset["d"], 2) <= w0: continue

            am2 = sset["cols"] * sset["w"] * sset["rows"] * sset["d"] * sset["m"]
            xr  = sset["w"]
            yr  = sset["d"]

            if xr > w0:
                xr = w0 if xr * ratio < w0 else xr * ratio

            if yr > w0:
                yr = yw0 if r * ratio < w0 else yr * ratio

            xm2 = sset["cols"] * xr * sset["rows"] * yr * sset["m"]
            if round(xm2, 2) == round(am2, 2): continue

            sset["dY"] += (sset["d"] - yr) / 2
            if "dX" in sset: sset["dX"] += (sset["w"] - xr) / 2

            sset["w" ] = xr
            sset["d" ] = yr
            sset["w0"] = sset["w"] + gap
            sset["d0"] = sset["d"] + gap

            skm2 -= (am2 - xm2)
            adm2 -= (am2 - xm2)

    # Size contraction: round 3: Resort to sizes < requested w0.
    if round(skm2, 2) > round(sm2, 2):
        ratio2 = 1 - (skm2 - sm2) / skm2
        ratio  = math.sqrt(ratio2)

        for sset in ssets:
            if round(skm2, 2) <= round(sm2, 2): break

            am2 = sset["cols"] * sset["w"] * sset["rows"] * sset["d"] * sset["m"]
            xr  = sset["w"]
            yr  = sset["d"]

            if xr > gap4:
                xr = gap4 if xr * ratio < gap4 else xr * ratio

            if yr > gap4:
                yr = gap4 if yr * ratio < gap4 else yr * ratio

            xm2 = sset["cols"] * xr * sset["rows"] * yr * sset["m"]
            if round(xm2, 2) == round(am2, 2): continue

            sset["dY"] += (sset["d"] - yr) / 2
            if "dX" in sset: sset["dX"] += (sset["w"] - xr) / 2

            sset["w" ] = xr
            sset["d" ] = yr
            sset["w0"] = sset["w"] + gap
            sset["d0"] = sset["d"] + gap

            skm2 -= (am2 - xm2)

    # Log warning if unable to entirely contract skylight dimensions.
    if round(skm2, 2) > round(sm2, 2):
        oslg.log(CN.WRN, "Skylights slightly oversized (%s)" % (mth))

    # Generate skylight well vertices for roofs, attics & plenums.
    for greniers in [attics, plenums]:
        k = "attic" if greniers == attics else "plenum"

        for grenier in greniers.values():
            for roof in grenier["roofs"]:
                sts = ssets
                sts = [st for st in sts if "clng"        in st]
                sts = [st for st in sts if k             in st]
                sts = [st for st in sts if "ld"          in st]
                sts = [st for st in sts if "space"       in st]
                sts = [st for st in sts if "roof"        in st]
                sts = [st for st in sts if "pattern"     in st]
                sts = [st for st in sts if st["pattern"] in st]

                ide = st["space"].nameString()
                sts = [st for st in sts if ide      in rooms]
                sts = [st for st in sts if id(roof) in st["ld"]]

                sts = [st for st in sts if st[k     ] == grenier["space"]]
                sts = [st for st in sts if st["roof"] == roof]

                if not sts: continue

                # If successful, 'genInserts' returns extended ROOF surface
                # vertices, including leader lines to support cutouts. The
                # method also generates new roof inserts. See key:value pair
                # "vts". The FINAL go/no-go is contingent to successfully
                # inserting corresponding room ceiling inserts (vis-à-vis
                # attic/plenum floor below).
                vz = genInserts(roof, sts)
                if not vz: continue

                roof.setVertices(vz)

    # Repeat for ceilings below attic/plenum floors.
    for ceiling in ceilings.values():
        k = "attic" if "attic" in ceiling else "plenum"
        greniers = attics if k == "attic" else plenums

        if k       not in ceiling: continue
        if "floor" not in ceiling: continue
        if "clng"  not in ceiling: continue
        if "space" not in ceiling: continue

        espace = ceiling[k      ] # (unoccupied) space above ceiling
        floor  = ceiling["floor"] # adjacent floor above
        clng   = ceiling["clng" ] # ceiling surface
        space  = ceiling["space"] # its space
        idx    = espace.nameString()
        ide    = space.nameString()
        if ide not in rooms: continue
        if idx not in greniers: continue

        room    = rooms[ide]
        grenier = greniers[idx]
        ti      = grenier["ti"]
        t0      = room["t0"]
        stz     = []

        for roof in ceiling["roofs"]:
            sts = ssets
            sts = [st for st in sts if "clng"    in st]
            sts = [st for st in sts if k         in st]
            sts = [st for st in sts if "space"   in st]
            sts = [st for st in sts if "roof"    in st]
            sts = [st for st in sts if "pattern" in st]
            sts = [st for st in sts if "cm2"     in st]
            sts = [st for st in sts if "vts"     in st]
            sts = [st for st in sts if "vtx"     in st]
            sts = [st for st in sts if "ld"      in st]
            sts = [st for st in sts if id(roof)  in st["ld"]]
            sts = [st for st in sts if id(clng)  in st["ld"]]

            id0 = st["space"].nameString()

            sts = [st for st in sts if id0 == ide]
            sts = [st for st in sts if id0 in rooms]

            sts = [st for st in sts if st["clng"] == clng]
            sts = [st for st in sts if st["roof"] == roof]
            sts = [st for st in sts if st[k     ] == espace]
            if len(sts) != 1: continue

            stz.append(sts[0])

        if not stz: continue

        # Add new roof inserts & skylights for the (now) toplit space.
        for i, st in enumerate(stz):
            sub         = {}
            sub["type"] = "Skylight"
            sub["sill"] = gap / 2
            if frame: sub["frame"] = frame

            for ids, vt in st["vts"].items():
                vec = p3Dv(t0.inverse() * list(ti * vt))
                roof = openstudio.model.Surface(vec, mdl)
                roof.setSpace(space)
                roof.setName("%s:%s" % (ids, ide))

                # Generate well walls.
                vX = cast(roof, clng, ray)
                s0 = segments(t0 * roof.vertices())
                sX = segments(t0 * vX)

                for j, sg in enumerate(s0):
                    sg0 = list(sg)
                    sgX = list(sX[j])
                    vec = openstudio.Point3dVector()
                    vec.append(sg0[ 0])
                    vec.append(sg0[-1])
                    vec.append(sgX[-1])
                    vec.append(sgX[ 0])

                    v_grenier = ti.inverse() * vec
                    v_room    = list(t0.inverse() * vec)
                    v_room.reverse()
                    v_room    = p3Dv(v_room)

                    grenier_wall = openstudio.model.Surface(v_grenier, mdl)
                    grenier_wall.setSpace(espace)
                    grenier_wall.setName("%s:%d:%d:%s" % (ids, i, j, idx))

                    room_wall = openstudio.model.Surface(v_room, mdl)
                    room_wall.setSpace(space)
                    room_wall.setName("%s:%d:%d:%s" % (ids, i, j, ide))

                    grenier_wall.setAdjacentSurface(room_wall)
                    room_wall.setAdjacentSurface(grenier_wall)

                # Add individual skylights. Independently of the subset layout
                # (rows x cols), individual roof inserts may be deeper than
                # wider (or vice-versa). Adapt skylight width vs depth
                # accordingly.
                if round(st["d"], 2) > round(st["w"], 2):
                    sub["width" ] = st["d"] - f2
                    sub["height"] = st["w"] - f2
                else:
                    sub["width" ] = st["w"] - f2
                    sub["height"] = st["d"] - f2

                sub["id"] = roof.nameString()
                addSubs(roof, sub, False, True, True)


        # Vertically-cast subset roof "vtx" onto ceiling.
        for st in stz:
            cst = cast(ti * st["vtx"], t0 * clng.vertices(), ray)
            st["cvtx"] = t0.inverse() * cst

        # Extended ceiling vertices.
        vertices = genExtendedVertices(clng, stz, "cvtx")
        if not vertices: continue

        # Reset ceiling and adjacent floor vertices.
        clng.setVertices(vertices)
        fvtx = list(t0 * vertices)
        fvtx.reverse()
        floor.setVertices(ti.inverse() * p3Dv(fvtx))

    # Loop through 'direct' roof surfaces of rooms to toplit (no attics or
    # plenums). No overlaps, so no relative space coordinate adjustments.
    for ide, room in rooms.items():
        for roof in room["roofs"]:
            for i, st in enumerate(ssets):
                if "clng"     in st: continue
                if "box"  not in st: continue
                if "cols" not in st: continue
                if "rows" not in st: continue
                if "d"    not in st: continue
                if "w"    not in st: continue
                if "dY"   not in st: continue
                if "roof" not in st: continue

                if st["roof"] != roof: continue

                w1 = st["w" ] - f2
                d1 = st["d" ] - f2
                dY = st["dY"]

                for j in range(st["rows"]):
                    sub           = {}
                    sub["type"  ] = "Skylight"
                    sub["count" ] = st["cols"]
                    sub["width" ] = w1
                    sub["height"] = d1
                    sub["id"    ] = "%s:%d:%d" % (roof.nameString(), i, j)
                    sub["sill"  ] = dY + j * (2 * dY + d1)

                    if "dX" in st and st["dX"]: sub["r_buffer"] = st["dX"]
                    if "dX" in st and st["dX"]: sub["l_buffer"] = st["dX"]
                    if frame: sub["frame"] = frame

                    addSubs(roof, sub, False, True, True)

    return rm2
