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

    id = oslg.trim(specs["id"])

    if not id:
        id = "OSut.CON." + specs["type"]
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
    c.setName(id)

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
    id    = "onoff"
    onoff = model.getScheduleTypeLimitsByName(id)

    if onoff:
        onoff = onoff.get()
    else:
      onoff = openstudio.model.ScheduleTypeLimits(model)
      onoff.setName(id)
      onoff.setLowerLimitValue(0)
      onoff.setUpperLimitValue(1)
      onoff.setNumericType("Discrete")
      onoff.setUnitType("Availability")

    # Shading schedule.
    id  = "OSut.SHADE.Ruleset"
    sch = model.getScheduleRulesetByName(id)

    if sch:
        sch = sch.get()
    else:
      sch = openstudio.model.ScheduleRuleset(model, 0)
      sch.setName(id)
      sch.setScheduleTypeLimits(onoff)
      sch.defaultDaySchedule.setName("OSut.SHADE.Ruleset.Default")

    # Summer cooling rule.
    id   = "OSut.SHADE.ScheduleRule"
    rule = model.getScheduleRuleByName(id)

    if rule:
        rule = rule.get()
    else:
      may     = openstudio.MonthOfYear("May")
      october = openstudio.MonthOfYear("Oct")
      start   = openstudio.Date(may, 1)
      finish  = openstudio.Date(october, 31)

      rule = openstudio.model.ScheduleRule(sch)
      rule.setName(id)
      rule.setStartDate(start)
      rule.setEndDate(finish)
      rule.setApplyAllDays(True)
      rule.daySchedule.setName("OSut.SHADE.Rule.Default")
      rule.daySchedule.addValue(openstudio.Time(0,24,0,0), 1)

    # Shade object.
    id  = "OSut.SHADE"
    shd = mdl.getShadeByName(id)

    if shd:
        shd = shd.get()
    else:
      shd = openstudio.model.Shade(mdl)
      shd.setName(id)

    # Shading control (unique to each call).
    id  = "OSut.ShadingControl"
    ctl = openstudio.model.ShadingControl(shd)
    ctl.setName(id)
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
    id  = "OSut.MASS.Material"
    mat = mdl.getOpaqueMaterialByName(id)

    if mat:
        mat = mat.get()
    else:
        mat = openstudio.model.StandardOpaqueMaterial(mdl)
        mat.setName(id)
        mat.setRoughness("MediumRough")
        mat.setThickness(0.15)
        mat.setConductivity(1.12)
        mat.setDensity(540)
        mat.setSpecificHeat(1210)
        mat.setThermalAbsorptance(0.9)
        mat.setSolarAbsorptance(0.7)
        mat.setVisibleAbsorptance(0.17)

    # A single, 1x layered construction.
    id  = "OSut.MASS.Construction"
    con = mdl.getConstructionByName(id)

    if con:
        con = con.get()
    else:
        con = openstudio.model.Construction(mdl)
        con.setName(id)
        layers = openstudio.model.MaterialVector()
        layers.append(mat)
        con.setLayers(layers)

    id = "OSut.InternalMassDefinition.%.2f" % ratio
    df = mdl.getInternalMassDefinitionByName(id)

    if df:
        df = df.get
    else:
        df = openstudio.model.InternalMassDefinition(mdl)
        df.setName(id)
        df.setConstruction(con)
        df.setSurfaceAreaperSpaceFloorArea(ratio)

    for sp in sps:
        mass = openstudio.model.InternalMass(df)
        mass.setName("OSut.InternalMass.%s" % sp.nameString())
        mass.setSpace(sp)

    return True


def holdsConstruction(set=None, base=None, gr=False, ex=False, type=""):
    """Validates whether a default construction set holds a base construction.

    Args:
        set (openstudio.model.DefaultConstructionSet):
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

    if not isinstance(set, cl1):
        return oslg.mismatch("set", set, cl1, mth, CN.DBG, False)
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
            if set.defaultGroundContactSurfaceConstructions():
                c = set.defaultGroundContactSurfaceConstructions().get()
        elif ex:
            if set.defaultExteriorSurfaceConstructions():
                c = set.defaultExteriorSurfaceConstructions().get()
        else:
            if set.defaultInteriorSurfaceConstructions():
                c = set.defaultInteriorSurfaceConstructions().get()
    elif type in t2:
        if gr:
            return False
        if ex:
            if set.defaultExteriorSubSurfaceConstructions():
                c = set.defaultExteriorSubSurfaceConstructions().get()
        else:
            if set.defaultInteriorSubSurfaceConstructions():
                c = set.defaultInteriorSubSurfaceConstructions().get()
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
        set = space.defaultConstructionSet().get()

        if holdsConstruction(set, base, ground, exterior, type): return set

    if space.spaceType():
        spacetype = space.spaceType().get()

        if spacetype.defaultConstructionSet():
            set = spacetype.defaultConstructionSet().get()

            if holdsConstruction(set, base, ground, exterior, type):
                return set

    if space.buildingStory():
        story = space.buildingStory().get()

        if story.defaultConstructionSet():
            set = story.defaultConstructionSet().get()

            if holdsConstruction(set, base, ground, exterior, type):
                return set


    building = mdl.getBuilding()

    if building.defaultConstructionSet():
        set = building.defaultConstructionSet().get()

        if holdsConstruction(set, base, ground, exterior, type):
            return set

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

    for m in lc.layers():
        if m.to_MasslessOpaqueMaterial():
            m = m.to_MasslessOpaqueMaterial().get()

            if m.thermalResistance() < 0.001 or m.thermalResistance() < res["r"]:
                i += 1
                continue
            else:
                res["r"    ] = m.thermalResistance()
                res["index"] = i
                res["type" ] = "massless"

        if m.to_StandardOpaqueMaterial():
            m = m.to_StandardOpaqueMaterial().get()
            k = m.thermalConductivity()
            d = m.thickness()

            if (d < 0.003) or (k > 3.0) or (d / k < res["r"]):
                i += 1
                continue
            else:
                res["r"    ] = d / k
                res["index"] = i
                res["type" ] = "standard"

        i += 1

    return res


def areSpandrels(set=None) -> bool:
    """Validates whether one or more opaque surface(s) can be considered as
    curtain wall (or similar technology) spandrels, regardless of construction
    layers, by looking up AdditionalProperties or identifiers.

    Args:
        set (list):
            One or more openstudio.model.Surface instances.

    Returns:
        bool: Whether surface(s) can be considered 'spandrels'.
        False: If invalid input (see logs).
    """
    mth = "osut.areSpandrels"
    cl  = openstudio.model.Surface

    if isinstance(set, cl):
        set = [set]
    else:
        try:
            set = list(set)
        except:
            return oslg.mismatch("set", set, list, mth, CN.DBG, False)

    for i, s in enumerate(set):
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
    """Confirms if model has zones with valid heating temperature setpoints.

    Args:
        model (openstudio.model.Model):
            An OpenStudio model.

    Returns:
        bool: Whether model holds valid heating temperature setpoints.
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
                minimum = scheduleConstantMinMax(sched)[:min]

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
    """Confirms if model has zones with valid cooling temperature setpoints.

    Args:
        model (openstudio.model.Model):
            An OpenStudio model.

    Returns:
        bool: Whether model holds valid cooling temperature setpoints.
        False: If invalid inputs (see logs).
    """
    mth = "osut.hasCoolingTemperatureSetpoints"
    cl  = openstudio.model.Model

    if not isinstance(model, cl):
        return oslg.mismatch("model", model, cl, mth, CN.DBG, False)

    for zone in model.getThermalZones():
        if minCoolScheduledSetpoint(zone)["spt"]: return True

    return False


def areVestibules(set=None):
    """Validates whether one or more spaces can be considered vestibules(s).

    Args:
        set (list):
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

    if isinstance(set, cl):
        set = [set]
    elif not isinstance(set, list):
        return oslg.mismatch("set", set, list, mth, CN.DBG, False)

    for space in set:
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


def arePlenums(set=None):
    """Validates whether one or more spaces can be considered
    indirectly-conditioned plenum(s).

    Args:
        set (list):space (openstudio.model.Space):
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
    # ceiling tiles, and any other UNOCCUPIED space in a model. The term
    # "plenum" in this context is more of a catch-all shorthand - to be used
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
    # CASE B: "isPlenum" == TRUE in an OpenStudio model WITH HVAC airloops; OR
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

    if isinstance(set, cl):
        set = [set]
    elif not isinstance(set, list):
        return oslg.mismatch("set", set, list, mth, CN.DBG, False)

    for space in set:
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

        # CASE B: "isPlenum" == TRUE if airloops.
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
        id = space.additionalProperties().getFeatureAsString(tg2)

        if id:
            id  = id.get()
            dad = space.model().getSpaceByName(id)

            if dad:
                # Now focus on 'parent' space of INDIRECTLYCONDITIONED space.
                space = dad.get()
                cnd   = tg2
            else:
                log(ERR, "Unknown space %s (%s)" % (id, mth))

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

    id = space.nameString()

    # 1. First check OSut's REFRIGERATED status.
    status = space.additionalProperties().getFeatureAsString(tg0)

    if status:
        status = status.get()
        if isinstance(status, bool): return status
        log(ERR, "Unknown %s REFRIGERATED %s (%s)" % (id, status, mth))

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
        id = l.nameString().lower()

        if limits: break
        if not l.lowerLimitValue(): continue
        if not l.upperLimitValue(): continue
        if not l.numericType(): continue
        if not int(l.lowerLimitValue().get()) == 0: continue
        if not int(l.upperLimitValue().get()) == 1: continue
        if not l.numericType().get().lower() == "discrete": continue
        if not l.unitType().lower() == "availability": continue
        if id != "hvac operation scheduletypelimits": continue

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


def scalar(v=None, m=0) -> openstudio.Vector3d:
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
        m = float(m)
    except:
        return oslg.mismatch("scalar", m, float, mth, CN.DBG, v0)

    v0 = openstudio.Vector3d(m * v.x(), m * v.y(), m * v.z())

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
    dx = max(xs) - min(xs)

    return dx


def height(pts=None) -> float:
    """Returns 'width' of a set of OpenStudio 3D points.

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

    for i1, pts in enumerate(pts):
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
    t    = None
    face = openstudio.Point3dVector()
    p01  = poly(p1)
    p02  = poly(p2)
    if not p01: return oslg.empty("points 1", mth, CN.DBG, face)
    if not p02: return oslg.empty("points 2", mth, CN.DBG, face)
    if fits(p01, p02): return p01
    if fits(p02, p01): return p02
    if not isinstance(flat, bool): flat = False

    if shareXYZ(p01, "z"):
        a1 = list(p01)
        a2 = list(p02)
        if isClockwise(p01): a1.reverse()
    else:
        t   = openstudio.Transformation.alignFace(p01)
        cw1 = False
        a1  = list(t.inverse() * p01)
        a2  = list(t.inverse() * p02)

    if flat: a2 = list(flatten(a2))

    if not shareXYZ(a2, "z"):
        return invalid("points 2", mth, 2, CN.DBG, face)

    if isClockwise(a2): a2.reverse()

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
        if round(area,  2) == round(area2, 2): return face
        if round(delta, 2) == 0: return face

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
        face.append(pt) + scalar(ray, length)

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
        offset = openstudio.buffer(pts, w, CN.TOL)
        if not offset: return p1

        offset = offset.get()
        offset.reverse()
        return p3Dv(list(t * offset))
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
    if abs(xMIN - xMAX) < TOL:
        return oslg.zero("outline width", mth, CN.DBG, out)
    if abs(yMIN - yMAX) < TOL:
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
    if box.size != 4: return bkp

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

        for seg in getSegments(pts):
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


def genSlab(pltz=[], z=0):
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
        openstudio.point3dVector: Slab vertices (see logs if empty).
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
        id = "plate # %d (index %d)" % (i+1, i)

        if not isinstance(plt, dict):
            return oslg.mismatch(id, plt, dict, mth, CN.DBG, slb)

        if "x"  not in plt: return oslg.hashkey(id, plt,  "x", mth, CN.DBG, slb)
        if "y"  not in plt: return oslg.hashkey(id, plt,  "y", mth, CN.DBG, slb)
        if "dx" not in plt: return oslg.hashkey(id, plt, "dx", mth, CN.DBG, slb)
        if "dy" not in plt: return oslg.hashkey(id, plt, "dy", mth, CN.DBG, slb)

        x  = plt["x" ]
        y  = plt["y" ]
        dx = plt["dx"]
        dy = plt["dy"]

        try:
            x = float(x)
        except:
            oslg.mismatch("%s X" % id, x, float, mth, CN.DBG, slb)

        try:
            y = float(y)
        except:
            oslg.mismatch("%s Y" % id, y, float, mth, CN.DBG, slb)

        try:
            dx = float(dx)
        except:
            oslg.mismatch("%s dX" % id, dx, float, mth, CN.DBG, slb)

        try:
            dy = float(dy)
        except:
            oslg.mismatch("%s dY" % id, dy, float, mth, CN.DBG, slb)

        if abs(dx) < CN.TOL: return oslg.zero("%s dX" % id, mth, CN.ERR, slb)
        if abs(dy) < CN.TOL: return oslg.zero("%s dY" % id, mth, CN.ERR, slb)

    # Join plates.
    for i, plt in enumerate(pltz):
        id = "plate # %d (index %d)" % (i+1, i)

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
                return oslg.invalid(id, mth, 0, CN.ERR, bkp)
        else:
            slb = vtx

    # Once joined, re-adjust Z-axis coordinates.
    if abs(z) > CN.TOL:
        vtx = openstudio.Point3dVector()

        for pt in slb: vtx.append(openstudio.Point3d(pt.x(), pt.y(), z))

        slb = vtx

    return slb
