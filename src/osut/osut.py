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

import openstudio
from oslg import oslg
from dataclasses import dataclass

@dataclass(frozen=True)
class _CN:
    DBG = oslg.CN.DEBUG
    INF = oslg.CN.INFO
    WRN = oslg.CN.WARN
    ERR = oslg.CN.ERROR
    FTL = oslg.CN.FATAL
    NS  = "nameString"
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

def genConstruction(model=None, specs=dict()):
    mth = "osut.genConstruction"

    if not isinstance(model, openstudio.model.Model):
        oslg.mismatch("model", model, openstudio.model.Model, mth, CN.DBG)
        return None
    if not isinstance(specs, dict):
        oslg.mismatch("specs", specs, dict, mth, CN.DBG)
        return None

    if "type" not in specs: specs["type"] = "wall"
    if "id"   not in specs: specs["id"  ] = ""

    id = oslg.trim(specs["id"])
    if not id: id = "OSut.CON." + specs["type"]

    if specs["type"] not in uo():
        return oslg.invalid("surface type", mth, 2, CN.ERR)

    if "uo" not in specs: specs["uo"] = uo()[ specs["type"] ]
    u = specs["uo"]

    if u:
        try:
            u = float(u)
        except ValueError as e:
            return oslg.mismatch(id + " Uo", u, float, mth, CN.ERR)

        if u < 0:
            return oslg.negative(id + " Uo", mth, CN.ERR)
        if u > 5.678:
            return oslg.invalid(id + " Uo (> 5.678)", mth, 2, CN.ERR)

    # Optional specs. Log/reset if invalid.
    if "clad"   not in specs: specs["clad"  ] = "light" # exterior
    if "frame"  not in specs: specs["frame" ] = "light"
    if "finish" not in specs: specs["finish"] = "light" # interior
    if specs["clad"  ] not in mass(): oslg.log(CN.WRN, "Reset to light cladding")
    if specs["frame" ] not in mass(): oslg.log(CN.WRN, "Reset to light framing")
    if specs["finish"] not in mass(): oslg.log(CN.WRN, "Reset to light finish")
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
        if not specs["clad"]:
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

        if not specs["finish"]:
            mt = "drywall"
            d  = 0.015
            a["finish"]["mat"] = mats()[mt]
            a["finish"]["d"  ] = d
            a["finish"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

    elif specs["type"] == "wall":
        if not specs["clad"]:
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

        if not specs["finish"]:
            mt = "concrete"
            d  = 0.015
            if specs["finish"] == "light":  mt = "drywall"
            if specs["finish"] == "medium":  d = 0.100
            if specs["finish"] == "heavy":   d = 0.200
            a["finish"]["mat"] = mats()[mt]
            a["finish"]["d"  ] = d
            a["finish"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

    elif specs["type"] == "roof":
        if not specs["clad"]:
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
        a["compo"][:"mat"] = mats()[mt]
        a["compo"][:"d"  ] = d
        a["compo"][:"id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

        if not specs["finish"]:
            mt = "concrete"
            d  = 0.015
            if specs["finish"] == "light":  mt = "drywall"
            if specs["finish"] == "medium":  d = 0.100 # proxy for steel decking
            if specs["finish"] == "heavy":   d = 0.200
            a["finish"]["mat"] = mats()[mt]
            a["finish"]["d"  ] = d
            a["finish"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

    elif specs["type"] == "floor":
        if not specs["clad"]:
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

        if not specs["finish"]:
            mt = "concrete"
            d  = 0.015
            if specs["finish"] == "light": mt = "material"
            if specs["finish"] == "medium": d = 0.100
            if specs["finish"] == "heavy":  d = 0.200
            a["finish"][:"mat"] = mats()[mt]
            a["finish"][:"d"  ] = d
            a["finish"][:"id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

    elif specs["type"] == "slab":
        mt = "sand"
        d  = 0.100
        a["clad"]["mat"] = mats()[mt]
        a["clad"]["d"  ] = d
        a["clad"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

        if not specs["frame"]:
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

        if not specs["finish"]:
            mt = "material"
            d  = 0.015
            a["finish"]["mat"] = mats()[mt]
            a["finish"]["d"  ] = d
            a["finish"]["id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

    elif specs["type"] == "basement":
        if not specs["clad"]:
            mt = "concrete"
            d  = 0.100
            if specs["clad"] == "light": mt = "material"
            if specs["clad"] == "light":  d = 0.015
            a["clad"][:"mat"] = mats[mt]
            a["clad"][:"d"  ] = d
            a["clad"][:"id" ] = "OSut." + mt + ".%03d" % int(d * 1000)

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

            if not specs["finish"]:
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
        a["glazing"]["id"  ]  = "OSut.window"
        a["glazing"]["id"  ] += ".U%.1f"  % a["glazing"]["u"]
        a["glazing"]["id"  ] += ".SHGC%d" % a["glazing"]["shgc"]*100
        a["glazing"]["shgc"]  = 0.450
        if "shgc" in specs: a["glazing"]["shgc"] = specs["shgc"]

    elif specs["type"] == "skylight":
        a["glazing"]["u"   ]  = specs["uo"]
        a["glazing"]["id"  ]  = "OSut.skylight"
        a["glazing"]["id"  ] += ".U%.1f"  % a["glazing"]["u"]
        a["glazing"]["id"  ] += ".SHGC%d" % a["glazing"]["shgc"]*100
        a["glazing"]["shgc"]  = 0.450
        if "shgc" in specs: a["glazing"]["shgc"] = specs["shgc"]

    if bool(a["glazing"]):
        layers = openstudio.model.FenestrationMaterialVector()

        u    = a["glazing"]["u"   ]
        shgc = a["glazing"]["shgc"]
        lyr  = model.getSimpleGlazingByName(a["glazing"]["id"])

        # if lyr.empty?
        #     lyr = OpenStudio::Model::SimpleGlazing.new(model, u, shgc)
        #     lyr.setName(a[:glazing][:id])
        #     else
        #     lyr = lyr.get
        #
        #     layers << lyr
    else:
        layers = openstudio.model.OpaqueMaterialVector()

        # Loop through each layer spec, and generate construction.
        # a.each do |i, l|
        #     next if l.empty?
        #
        #     lyr = model.getStandardOpaqueMaterialByName(l["id"])
        #
        #     if lyr.empty?
        #         lyr = OpenStudio::Model::StandardOpaqueMaterial.new(model)
        #         lyr.setName(l[:id])
        #         lyr.setThickness(l[:d])
        #         lyr.setRoughness(         l[:mat][:rgh]) if l[:mat].key?(:rgh)
        #         lyr.setConductivity(      l[:mat][:k  ]) if l[:mat].key?(:k  )
        #         lyr.setDensity(           l[:mat][:rho]) if l[:mat].key?(:rho)
        #         lyr.setSpecificHeat(      l[:mat][:cp ]) if l[:mat].key?(:cp )
        #         lyr.setThermalAbsorptance(l[:mat][:thm]) if l[:mat].key?(:thm)
        #         lyr.setSolarAbsorptance(  l[:mat][:sol]) if l[:mat].key?(:sol)
        #         lyr.setVisibleAbsorptance(l[:mat][:vis]) if l[:mat].key?(:vis)
        #     else:
        #         lyr = lyr.get
        #
        #     layers << lyr


    return None
