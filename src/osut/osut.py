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

def sidz():
    """Returns available 'sidz' keyword tuple."""
    return _sidz

def mass():
    """Returns available 'mass' keyword tuple."""
    return _mass

def mats():
    """Returns stored materials dictionary."""
    return _mats

def film():
    """Returns inside + outside air film resistance dictionary."""
    return _film

def uo():
    """Returns (surface type-specific) Uo dictionary."""
    return _uo

def instantiate_new_osm():
    return openstudio.model.Model()
