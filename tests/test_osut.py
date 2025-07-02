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

import sys
sys.path.append("./src/osut")

import os
import unittest
import openstudio
import osut

DBG  = osut.CN.DBG
INF  = osut.CN.INF
WRN  = osut.CN.WRN
ERR  = osut.CN.ERR
FTL  = osut.CN.FTL
TOL  = osut.CN.TOL
TOL2 = osut.CN.TOL2

class TestOSutModuleMethods(unittest.TestCase):
    def test00_oslg_constants(self):
        self.assertEqual(DBG, 1)

    def test01_osm_instantiation(self):
        model = openstudio.model.Model()
        self.assertTrue(isinstance(model, openstudio.model.Model))
        del(model)

    def test02_tuples(self):
        self.assertEqual(len(osut.sidz()), 6)
        self.assertEqual(len(osut.mass()), 4)
        self.assertEqual(osut.sidz()[5], "west")
        self.assertEqual(osut.mass()[1], "light")

    def test03_dictionaries(self):
        self.assertEqual(len(osut.mats()),9)
        self.assertEqual(len(osut.film()),10)
        self.assertEqual(len(osut.uo()),10)
        self.assertTrue("concrete" in osut.mats())
        self.assertTrue("skylight" in osut.film())
        self.assertTrue("skylight" in osut.uo())
        self.assertEqual(osut.film().keys(), osut.uo().keys())

    def test04_materials(self):
        self.assertTrue("rgh" in osut.mats()["material"])
        self.assertTrue("k"   in osut.mats()["material"])
        self.assertTrue("rho" in osut.mats()["material"])
        self.assertTrue("cp"  in osut.mats()["material"])
        self.assertTrue("thm" in osut.mats()["sand"])
        self.assertTrue("sol" in osut.mats()["sand"])
        self.assertTrue("vis" in osut.mats()["sand"])
        self.assertEqual(osut.mats()["material"]["rgh"], "MediumSmooth")
        self.assertEqual(round(osut.mats()["material"]["k"   ], 3),    0.115)
        self.assertEqual(round(osut.mats()["material"]["rho" ], 3),  540.000)
        self.assertEqual(round(osut.mats()["material"]["cp"  ], 3), 1200.000)
        self.assertEqual(round(osut.mats()["sand"    ]["thm" ], 3),    0.900)
        self.assertEqual(round(osut.mats()["sand"    ]["sol" ], 3),    0.700)
        self.assertEqual(round(osut.mats()["sand"    ]["vis" ], 3),    0.700)

    def test05_construction_generation(self):
        m1 = "'specs' list? expecting dict (osut.genConstruction)"
        m2 = "'model' str? expecting Model (osut.genConstruction)"
        o  = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        # Unsuccessful try: 2nd argument not a 'dict' (see 'm1').
        model = openstudio.model.Model()
        self.assertEqual(osut.genConstruction(model, []), None)
        self.assertEqual(o.status(), DBG)
        self.assertEqual(len(o.logs()),1)
        self.assertEqual(o.logs()[0]["level"], DBG)
        self.assertEqual(o.logs()[0]["message"], m1)
        self.assertTrue(o.clean(), DBG)
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Unsuccessful try: 1st argument not a model (see 'm2').
        model = openstudio.model.Model()
        self.assertEqual(osut.genConstruction("model", dict()), None)
        self.assertEqual(o.status(), DBG)
        self.assertEqual(len(o.logs()),1)
        self.assertEqual(o.logs()[0]["level"], DBG)
        self.assertTrue(o.logs()[0]["message"], m2)
        self.assertTrue(o.clean(), DBG)
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Defaulted specs (2nd argument).
        specs = dict()
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.wall")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 4)
        self.assertEqual(c.layers()[0].nameString(), "OSut.material.015")
        self.assertEqual(c.layers()[1].nameString(), "OSut.drywall.015")
        self.assertEqual(c.layers()[2].nameString(), "OSut.mineral.106")
        self.assertEqual(c.layers()[3].nameString(), "OSut.drywall.015")
        r = osut.rsi(c, osut.film()["wall"])
        u = osut.uo()["wall"]
        self.assertEqual(round(r, 3), round(1/u, 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Typical uninsulated, framed cavity wall - suitable for light
        # interzone assemblies (i.e. symmetrical, 3-layer construction).
        specs = dict(type="partition")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.partition")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 3)
        self.assertEqual(c.layers()[0].nameString(), "OSut.drywall.015")
        self.assertEqual(c.layers()[1].nameString(), "OSut.material.015")
        self.assertEqual(c.layers()[2].nameString(), "OSut.drywall.015")
        self.assertTrue("uo" in specs)
        self.assertEqual(specs["uo"], None)
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Alternative to (uninsulated) partition (more inputs, same outcome).
        specs = dict(type="wall", clad="none", uo=None)
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.wall")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 3)
        self.assertEqual(c.layers()[0].nameString(), "OSut.drywall.015")
        self.assertEqual(c.layers()[1].nameString(), "OSut.material.015")
        self.assertEqual(c.layers()[2].nameString(), "OSut.drywall.015")
        self.assertTrue("uo" in specs)
        self.assertEqual(specs["uo"], None)
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Insulated partition variant.
        specs = dict(type="partition", uo=0.214)
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.partition")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 3)
        self.assertEqual(c.layers()[0].nameString(), "OSut.drywall.015")
        self.assertEqual(c.layers()[1].nameString(), "OSut.mineral.216")
        self.assertEqual(c.layers()[2].nameString(), "OSut.drywall.015")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.214)
        r = osut.rsi(c, osut.film()["partition"])
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Alternative to (insulated) partition (more inputs, similar outcome).
        specs = dict(type="wall", uo=0.214, clad="none")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.wall")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 3)
        self.assertEqual(c.layers()[0].nameString(), "OSut.drywall.015")
        self.assertEqual(c.layers()[1].nameString(), "OSut.mineral.216")
        self.assertEqual(c.layers()[2].nameString(), "OSut.drywall.015")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.214)
        r = osut.rsi(c, osut.film()["wall"])
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # A wall inherits a 4th (cladding) layer, by default.
        specs = dict(type="wall", uo=0.214)
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.wall")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 4)
        self.assertEqual(c.layers()[0].nameString(), "OSut.material.015")
        self.assertEqual(c.layers()[1].nameString(), "OSut.drywall.015")
        self.assertEqual(c.layers()[2].nameString(), "OSut.mineral.210")
        self.assertEqual(c.layers()[3].nameString(), "OSut.drywall.015")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.214)
        r = osut.rsi(c, osut.film()["wall"])
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Otherwise, a wall has a minimum of 2 layers.
        specs = dict(type="wall", uo=0.214, clad="none", finish="none")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.wall")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 2)
        self.assertEqual(c.layers()[0].nameString(), "OSut.drywall.015")
        self.assertEqual(c.layers()[1].nameString(), "OSut.mineral.221")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.214)
        r = osut.rsi(c, osut.film()["wall"])
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Default shading material.
        specs = dict(type="shading")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.shading")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 1)
        self.assertEqual(c.layers()[0].nameString(), "OSut.material.015")
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # A single-layered, 5/8" partition (alternative: "shading").
        specs = dict(type="partition", clad="none", finish="none")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.partition")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 1)
        self.assertEqual(c.layers()[0].nameString(), "OSut.material.015")
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # A single-layered 4" concrete partition.
        specs = dict(type="partition", clad="none", finish="none", frame="medium")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.partition")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 1)
        self.assertEqual(c.layers()[0].nameString(), "OSut.concrete.100")
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # A single-layered 8" concrete partition.
        specs = dict(type="partition", clad="none", finish="none", frame="heavy")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.partition")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 1)
        self.assertEqual(c.layers()[0].nameString(), "OSut.concrete.200")
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # A light (1x layer), uninsulated attic roof (alternative: "shading").
        specs = dict(type="roof", uo=None, clad="none", finish="none")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.roof")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 1)
        self.assertEqual(c.layers()[0].nameString(), "OSut.material.015")
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Insulated, cathredral ceiling construction.
        specs = dict(type="roof", uo=0.214)
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.roof")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 3)
        self.assertEqual(c.layers()[0].nameString(), "OSut.material.015")
        self.assertEqual(c.layers()[1].nameString(), "OSut.mineral.215")
        self.assertEqual(c.layers()[2].nameString(), "OSut.drywall.015")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.214)
        r = osut.rsi(c, osut.film()["roof"])
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Insulated, unfinished outdoor-facing plenum roof (polyiso + 4" slab).
        specs = dict(type="roof", uo=0.214, frame="medium", finish="medium")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.roof")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 3)
        self.assertEqual(c.layers()[0].nameString(), "OSut.material.015")
        self.assertEqual(c.layers()[1].nameString(), "OSut.polyiso.108")
        self.assertEqual(c.layers()[2].nameString(), "OSut.concrete.100")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.214)
        r = osut.rsi(c, osut.film()["roof"])
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Insulated (conditioned), parking garage roof (polyiso under 8" slab).
        specs = dict(type="roof", uo=0.214, clad="heavy", frame="medium", finish="none")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.roof")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 2)
        self.assertEqual(c.layers()[0].nameString(), "OSut.concrete.200")
        self.assertEqual(c.layers()[1].nameString(), "OSut.polyiso.110")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.214)
        r = osut.rsi(c, osut.film()["roof"])
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Uninsulated plenum ceiling tiles (alternative: "shading").
        specs = dict(type="roof", uo=None, clad="none", finish="none")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.roof")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 1)
        self.assertEqual(c.layers()[0].nameString(), "OSut.material.015")
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Unfinished, insulated, framed attic floor (blown cellulose).
        specs = dict(type="floor", uo=0.214, frame="heavy", finish="none")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.floor")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 2)
        self.assertEqual(c.layers()[0].nameString(), "OSut.material.015")
        self.assertEqual(c.layers()[1].nameString(), "OSut.cellulose.217")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.214)
        r = osut.rsi(c, osut.film()["floor"])
        self.assertEqual(round(r, 3), round(1/0.214, 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Finished, insulated exposed floor (e.g. wood-framed, residential).
        specs = dict(type="floor", uo=0.214)
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.floor")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 3)
        self.assertEqual(c.layers()[0].nameString(), "OSut.material.015")
        self.assertEqual(c.layers()[1].nameString(), "OSut.mineral.211")
        self.assertEqual(c.layers()[2].nameString(), "OSut.material.015")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.214)
        r = osut.rsi(c, osut.film()["floor"])
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Finished, insulated exposed floor (e.g. 4" slab, steel web joists).
        specs = dict(type="floor", uo=0.214, finish="medium")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.floor")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 3)
        self.assertEqual(c.layers()[0].nameString(), "OSut.material.015")
        self.assertEqual(c.layers()[1].nameString(), "OSut.mineral.214")
        self.assertEqual(c.layers()[2].nameString(), "OSut.concrete.100")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.214)
        r = osut.rsi(c, osut.film()["floor"])
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Uninsulated slab-on-grade.
        specs = dict(type="slab", frame="none", finish="none")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.slab")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 2)
        self.assertEqual(c.layers()[0].nameString(), "OSut.sand.100")
        self.assertEqual(c.layers()[1].nameString(), "OSut.concrete.100")
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Insulated slab-on-grade.
        specs = dict(type="slab", uo=0.214, finish="none")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.slab")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 3)
        self.assertEqual(c.layers()[0].nameString(), "OSut.sand.100")
        self.assertEqual(c.layers()[1].nameString(), "OSut.polyiso.109")
        self.assertEqual(c.layers()[2].nameString(), "OSut.concrete.100")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.214)
        r = osut.rsi(c, osut.film()["slab"])
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # 8" uninsulated basement wall.
        specs = dict(type="basement", clad="none", finish="none")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.basement")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 1)
        self.assertEqual(c.layers()[0].nameString(), "OSut.concrete.200")
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # 8" interior-insulated, finished basement wall.
        specs = dict(type="basement", uo=0.428, clad="none")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.basement")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 3)
        self.assertEqual(c.layers()[0].nameString(), "OSut.concrete.200")
        self.assertEqual(c.layers()[1].nameString(), "OSut.mineral.100")
        self.assertEqual(c.layers()[2].nameString(), "OSut.drywall.015")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.428)
        r = osut.rsi(c, osut.film()["basement"])
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Standard, insulated steel door (default Uo = 1.8 W/K•m).
        specs = dict(type="door")
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.door")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 1)
        self.assertEqual(c.layers()[0].nameString(), "OSut.door.045")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), osut.uo()["door"])
        r = osut.rsi(c, osut.film()["door"])
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        # Better-insulated door, window & skylight.
        specs = dict(type="door", uo=0.900)
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.door")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 1)
        self.assertEqual(c.layers()[0].nameString(), "OSut.door.045")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.900)
        r = osut.rsi(c, osut.film()["door"])
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        specs = dict(type="window", uo=0.900, shgc=0.35)
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.window")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 1)
        self.assertEqual(c.layers()[0].nameString(), "OSut.window.U0.9.SHGC35")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.900)
        r = osut.rsi(c) # not necessary to specify film
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

        specs = dict(type="skylight", uo=0.900)
        model = openstudio.model.Model()
        c = osut.genConstruction(model, specs)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(c)
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.skylight")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 1)
        self.assertEqual(c.layers()[0].nameString(), "OSut.skylight.U0.9.SHGC45")
        self.assertTrue("uo" in specs)
        self.assertEqual(round(specs["uo"], 3), 0.900)
        r = osut.rsi(c) # not necessary to specify film
        self.assertEqual(round(r, 3), round(1/specs["uo"], 3))
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

    def test06_internal_mass(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        ratios   = dict(entrance=0.1, lobby=0.3, meeting=1.0)
        model    = openstudio.model.Model()
        entrance = openstudio.model.Space(model)
        lobby    = openstudio.model.Space(model)
        meeting  = openstudio.model.Space(model)
        offices  = openstudio.model.Space(model)

        entrance.setName("Entrance")
        lobby.setName("Lobby")
        meeting.setName("Meeting")
        offices.setName("Offices")

        m1 = "OSut.InternalMassDefinition.0.10"
        m2 = "OSut.InternalMassDefinition.0.30"
        m3 = "OSut.InternalMassDefinition.1.00"
        m4 = "OSut.InternalMassDefinition.2.00"

        for space in model.getSpaces():
            name  = space.nameString().lower()
            ratio = ratios[name] if name in ratios else None
            sps   = openstudio.model.SpaceVector()
            sps.append(space)

            if ratio:
                self.assertTrue(osut.genMass(sps, ratio))
            else:
                self.assertTrue(osut.genMass(sps))

            self.assertEqual(o.status(), 0)

        construction = None
        material     = None

        for m in model.getInternalMasss():
            d = m.internalMassDefinition()
            self.assertTrue(d.designLevelCalculationMethod(), "SurfaceArea/Area")

            ratio = d.surfaceAreaperSpaceFloorArea()
            self.assertTrue(ratio)
            ratio = ratio.get()

            if round(ratio, 1) == 0.1:
                self.assertEqual(d.nameString(), m1)
                self.assertTrue("entrance" in m.nameString().lower())
            elif round(ratio, 1) == 0.3:
                self.assertEqual(d.nameString(), m2)
                self.assertTrue("lobby" in m.nameString().lower())
            elif round(ratio, 1) == 1.0:
                self.assertEqual(d.nameString(), m3)
                self.assertTrue("meeting" in m.nameString().lower())
            else:
                self.assertEqual(d.nameString(), m4)
                self.assertEqual(round(ratio, 1), 2.00)

            c = d.construction()
            self.assertTrue(c)
            c = c.get().to_Construction()
            self.assertTrue(c)
            c = c.get()

            if not construction: construction = c
            self.assertEqual(construction, c)
            self.assertTrue("OSut.MASS.Construction" in c.nameString())
            self.assertEqual(c.numLayers(), 1)
            m = c.layers()[0]

            if not material: material = m
            self.assertEqual(material, m)

        del(model)

    def test07_construction_thickness(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        version = int("".join(openstudio.openStudioVersion().split(".")))
        translator = openstudio.osversion.VersionTranslator()

        # The v1.11.5 (2016) seb.osm, shipped with OpenStudio, holds (what
        # would now be considered as deprecated) a definition of plenum floors
        # (i.e. ceiling tiles) generating several warnings with more recent
        # OpenStudio versions.
        path  = openstudio.path("./tests/files/osms/in/seb.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        # "Shading Surface 4" is overlapping with a plenum exterior wall.
        sh4 = model.getShadingSurfaceByName("Shading Surface 4")
        self.assertTrue(sh4)
        sh4 = sh4.get()
        sh4.remove()

        plenum = model.getSpaceByName("Level 0 Ceiling Plenum")
        self.assertTrue(plenum)
        plenum = plenum.get()

        thzone = plenum.thermalZone()
        self.assertTrue(thzone)
        thzone = thzone.get()

        # Before the fix.
        if version >= 350:
            self.assertTrue(plenum.isEnclosedVolume())
            self.assertTrue(plenum.isVolumeDefaulted())
            self.assertTrue(plenum.isVolumeAutocalculated())

        if 350 < version < 370:
            self.assertEqual(round(plenum.volume(), 0), 234)
        else:
            self.assertEqual(round(plenum.volume(), 0), 0)

        self.assertTrue(thzone.isVolumeDefaulted())
        self.assertTrue(thzone.isVolumeAutocalculated())
        self.assertFalse(thzone.volume())

        for s in plenum.surfaces():
            if s.outsideBoundaryCondition().lower() == "outdoors": continue

            # If a SEB plenum surface isn't facing outdoors, it's 1 of 4 "floor"
            # surfaces (each facing a ceiling surface below).
            adj = s.adjacentSurface()
            self.assertTrue(adj)
            adj = adj.get()
            self.assertEqual(len(adj.vertices()), len(s.vertices()))

            # Same vertex sequence? Should be in reverse order.
            for i, vtx in enumerate(adj.vertices()):
                self.assertTrue(osut.is_same_vtx(vtx, s.vertices()[i]))

            self.assertEqual(adj.surfaceType(), "RoofCeiling")
            self.assertEqual(s.surfaceType(), "RoofCeiling")
            self.assertTrue(s.setSurfaceType("Floor"))
            vtx = list(s.vertices())
            vtx.reverse()
            self.assertTrue(s.setVertices(vtx))

            # Vertices now in reverse order.
            rvtx = list(adj.vertices())
            rvtx.reverse()

            for i, vtx in enumerate(rvtx):
                self.assertTrue(osut.is_same_vtx(vtx, s.vertices()[i]))

        # After the fix.
        if version >= 350:
            self.assertTrue(plenum.isEnclosedVolume())
            self.assertTrue(plenum.isVolumeDefaulted())
            self.assertTrue(plenum.isVolumeAutocalculated())

        self.assertEqual(round(plenum.volume(), 0), 50) # right answer
        self.assertTrue(thzone.isVolumeDefaulted())
        self.assertTrue(thzone.isVolumeAutocalculated())
        self.assertFalse(thzone.volume())

        model.save("./tests/files/osms/out/seb2.osm", True)
        # End of cleanup.

        for c in model.getConstructions():
            if not c.to_LayeredConstruction(): continue

            c  = c.to_LayeredConstruction().get()
            id = c.nameString()

            # OSut 'thickness' method can only process layered constructions
            # built up with standard opaque layers, which exclude:
            #
            #   - "Air Wall"-based construction
            #   - "Double pane"-based construction
            #
            # The method returns '0' in such cases, logging ERROR messages.
            th = osut.thickness(c)

            if "Air Wall" in id or "Double pane" in id:
                self.assertEqual(round(th, 0), 0)
                continue

            self.assertTrue(th > 0)

        self.assertTrue(o.is_error())
        self.assertTrue(o.clean(), DBG)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())

        for c in model.getConstructions():
            if c.to_LayeredConstruction(): continue

            c  = c.to_LayeredConstruction().get()
            id = c.nameString()
            if "Air Wall" in id or "Double pane" in id: continue

            th = osut.thickness(c)
            self.assertTrue(th > 0)

        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())

    def test08_holds_constructions(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        version = int("".join(openstudio.openStudioVersion().split(".")))
        translator = openstudio.osversion.VersionTranslator()

        path  = openstudio.path("./tests/files/osms/in/5ZoneNoHVAC.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()
        mdl   = openstudio.model.Model()

        t1  = "roofceiling"
        t2  = "wall"
        cl1 = openstudio.model.DefaultConstructionSet
        cl2 = openstudio.model.LayeredConstruction
        id1 = cl1.__name__
        id2 = cl2.__name__
        n1  = "CBECS Before-1980 ClimateZone 8 (smoff) ConstSet"
        n2  = "CBECS Before-1980 ExtRoof IEAD ClimateZone 8"
        m5  = "Invalid 'surface type' arg #5 (osut.holdsConstruction)"
        m6  = "Invalid 'set' arg #1 (osut.holdsConstruction)"
        set = model.getDefaultConstructionSetByName(n1)
        c   = model.getLayeredConstructionByName(n2)
        self.assertTrue(set)
        self.assertTrue(c)
        set = set.get()
        c   = c.get()

        # TRUE case: 'set' holds 'c' (exterior roofceiling construction).
        self.assertTrue(osut.holdsConstruction(set, c, False, True, t1))
        self.assertEqual(o.status(), 0)

        # FALSE case: not ground construction.
        self.assertFalse(osut.holdsConstruction(set, c, True, True, t1))
        self.assertEqual(o.status(), 0)

        # INVALID case: arg #5 : None (instead of surface type string).
        self.assertFalse(osut.holdsConstruction(set, c, True, True, None))
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m5)
        self.assertEqual(o.clean(), DBG)

        # INVALID case: arg #5 : empty surface type string.
        self.assertFalse(osut.holdsConstruction(set, c, True, True, ""))
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m5)
        self.assertEqual(o.clean(), DBG)

        # INVALID case: arg #5 : c construction (instead of surface type string).
        self.assertFalse(osut.holdsConstruction(set, c, True, True, c))
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m5)
        self.assertEqual(o.clean(), DBG)

        # INVALID case: arg #1 : c construction (instead of surface type string).
        self.assertFalse(osut.holdsConstruction(c, c, True, True, c))
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m6)
        self.assertEqual(o.clean(), DBG)

        # INVALID case: arg #1 : model (instead of surface type string).
        self.assertFalse(osut.holdsConstruction(mdl, c, True, True, t1))
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m6)
        self.assertEqual(o.clean(), DBG)

    # def test09_construction_set(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test10_glazing_airfilms(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test11_rsi(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    def test12_insulating_layer(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        version = int("".join(openstudio.openStudioVersion().split(".")))
        translator = openstudio.osversion.VersionTranslator()

        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        m0 = " expecting LayeredConstruction (osut.insulatingLayer)"

        for lc in model.getLayeredConstructions():
            id = lc.nameString()
            lyr = osut.insulatingLayer(lc)

            self.assertTrue(isinstance(lyr, dict))
            self.assertTrue("index" in lyr)
            self.assertTrue("type" in lyr)
            self.assertTrue("r" in lyr)

            if lc.isFenestration():
                self.assertEqual(o.status(), 0)
                self.assertFalse(lyr["index"])
                self.assertFalse(lyr["type"])
                self.assertEqual(lyr["r"], 0)
                continue

            if lyr["type"] not in ["standard", "massless"]: # air wall material
                self.assertEqual(o.status(), 0)
                self.assertFalse(lyr["index"])
                self.assertFalse(lyr["type"])
                self.assertEqual(lyr["r"], 0)
                continue

            self.assertTrue(lyr["index"] < lc.numLayers())

            if id == "EXTERIOR-ROOF":
                self.assertEqual(lyr["index"], 2)
                self.assertEqual(round(lyr["r"], 2), 5.08)
            elif id == "EXTERIOR-WALL":
                self.assertEqual(lyr["index"], 2)
                self.assertEqual(round(lyr["r"], 2), 1.47)
            elif id == "Default interior ceiling":
                self.assertEqual(lyr["index"], 0)
                self.assertEqual(round(lyr["r"], 2), 0.12)
            elif id == "INTERIOR-WALL":
                self.assertEqual(lyr["index"], 1)
                self.assertEqual(round(lyr["r"], 2), 0.24)
            else:
                self.assertEqual(lyr["index"], 0)
                self.assertEqual(round(lyr["r"], 2), 0.29)

        # Final stress tests.
        lyr = osut.insulatingLayer(None)
        self.assertTrue(o.is_debug())
        self.assertFalse(lyr["index"])
        self.assertFalse(lyr["type"])
        self.assertEqual(round(lyr["r"], 2), 0.00)
        self.assertEqual(len(o.logs()), 1)
        self.assertTrue(m0 in o.logs()[0]["message"])
        self.assertEqual(o.clean(), DBG)

        lyr = osut.insulatingLayer("")
        self.assertTrue(o.is_debug())
        self.assertFalse(lyr["index"])
        self.assertFalse(lyr["type"])
        self.assertEqual(round(lyr["r"], 2), 0.00)
        self.assertTrue(len(o.logs()), 1)
        self.assertTrue(m0 in o.logs()[0]["message"])
        self.assertEqual(o.clean(), DBG)

        lyr = osut.insulatingLayer(model)
        self.assertTrue(o.is_debug())
        self.assertFalse(lyr["index"])
        self.assertFalse(lyr["type"])
        self.assertEqual(round(lyr["r"], 2), 0.00)
        self.assertTrue(len(o.logs()), 1)
        self.assertTrue(m0 in o.logs()[0]["message"])
        self.assertEqual(o.clean(), DBG)

    # def test13_spandrels(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test14_schedule_ruleset_minmax(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test15_schedule_constant_minmax(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test16_schedule_comapct_minmax(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test17_minmax_heatcool_setpoints(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test18_hvac_airloops(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test19_vestibules(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test20_setpoints_plenums_attics(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test21_availability_schedules(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test22_model_transformation(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test23_fits_overlaps(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test24_triangulation(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test25_segments_triads_orientation(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test26_ulc_blc(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test27_polygon_attributes(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test28_subsurface_insertions(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test29_surface_width_height(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test30_wwr_insertions(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test31_convexity(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test32_outdoor_roofs(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test33_leader_line_anchors_inserts(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test34_generated_skylight_wells(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    # def test35_facet_retrieval(self):
    #     o = osut.oslg
    #     self.assertEqual(o.status(), 0)
    #     self.assertEqual(o.reset(DBG), DBG)
    #     self.assertEqual(o.level(), DBG)
    #     self.assertEqual(o.status(), 0)

    def test36_roller_shades(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        version = int("".join(openstudio.openStudioVersion().split(".")))
        translator = openstudio.osversion.VersionTranslator()

        path   = openstudio.path("./tests/files/osms/out/seb2.osm")
        model  = translator.loadModel(path)
        self.assertTrue(model)
        model  = model.get()
        spaces = model.getSpaces()

        # file   = File.join(__dir__, "files/osms/out/seb_ext4.osm")
        # path   = OpenStudio::Path.new(file)
        # model  = translator.loadModel(path)
        # self.assertTrue(model).to_not be_empty
        # model  = model.get
        # spaces = model.getSpaces

        # slanted = osut.facets(spaces, "Outdoors", "RoofCeiling", ["top", "north"])
        # self.assertEqual(len(slanted), 1)

        # slanted   = slanted.first
        # self.assertTrue(slanted.nameString).to eq("Openarea slanted roof")
        # skylights = slanted.subSurfaces
        #
        # tilted  = mod1.facets(spaces, "Outdoors", "Wall", :bottom)
        # self.assertTrue(tilted.size).to eq(1)
        # tilted  = tilted.first
        # self.assertTrue(tilted.nameString).to eq("Openarea tilted wall")
        # windows = tilted.subSurfaces
        #
        # # 2x control groups:
        # #   - 3x windows as a single control group
        # #   - 3x skylight as another single control group
        # skies = OpenStudio::Model::SubSurfaceVector.new
        # wins  = OpenStudio::Model::SubSurfaceVector.new
        # skylights.each { |sub| skies << sub }
        # windows.each   { |sub| wins  << sub }
        #
        # if OpenStudio.openStudioVersion.split(".").join.to_i < 321
        #   self.assertTrue(mod1.genShade(skies)).to be false
        #   self.assertTrue(mod1.status).to be_zero
        # else
        #   self.assertTrue(mod1.genShade(skies)).to be true
        #   self.assertTrue(mod1.genShade(wins)).to be true
        #   self.assertTrue(mod1.status).to be_zero
        #   ctls = model.getShadingControls
        #   self.assertTrue(ctls.size).to eq(2)
        #
        #   ctls.each do |ctl|
        #     self.assertTrue(ctl.shadingType).to eq("InteriorShade")
        #     type = "OnIfHighOutdoorAirTempAndHighSolarOnWindow"
        #     self.assertTrue(ctl.shadingControlType).to eq(type)
        #     self.assertTrue(ctl.isControlTypeValueNeedingSetpoint1).to be true
        #     self.assertTrue(ctl.isControlTypeValueNeedingSetpoint2).to be true
        #     self.assertTrue(ctl.isControlTypeValueAllowingSchedule).to be true
        #     self.assertTrue(ctl.isControlTypeValueRequiringSchedule).to be false
        #     spt1 = ctl.setpoint
        #     spt2 = ctl.setpoint2
        #     self.assertTrue(spt1).to_not be_empty
        #     self.assertTrue(spt2).to_not be_empty
        #     spt1 = spt1.get
        #     spt2 = spt2.get
        #     self.assertTrue(spt1).to be_within(TOL).of(18)
        #     self.assertTrue(spt2).to be_within(TOL).of(100)
        #     self.assertTrue(ctl.multipleSurfaceControlType).to eq("Group")
        #
        #     ctl.subSurfaces.each do |sub|
        #       surface = sub.surface
        #       self.assertTrue(surface).to_not be_empty
        #       surface = surface.get
        #       self.assertTrue([slanted, tilted]).to include(surface)
        #     end
        #   end
        # end
        #
        # file = File.join(__dir__, "files/osms/out/seb_ext5.osm")
        # model.save(file, true)





if __name__ == "__main__":
    unittest.main()
