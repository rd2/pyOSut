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

import math
import collections
import unittest
import openstudio
from src.osut import osut

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
        material = osut.mats()["material"]
        sand     = osut.mats()["sand"]
        self.assertTrue("rgh" in material)
        self.assertTrue("k"   in material)
        self.assertTrue("rho" in material)
        self.assertTrue("cp"  in material)
        self.assertTrue("thm" in sand)
        self.assertTrue("sol" in sand)
        self.assertTrue("vis" in sand)
        self.assertEqual(material["rgh"], "MediumSmooth")
        self.assertAlmostEqual(material["k"  ],    0.115, places=3)
        self.assertAlmostEqual(material["rho"],  540.000, places=3)
        self.assertAlmostEqual(material["cp" ], 1200.000, places=3)
        self.assertAlmostEqual(   sand["thm" ],    0.900, places=3)
        self.assertAlmostEqual(   sand["sol" ],    0.700, places=3)
        self.assertAlmostEqual(   sand["vis" ],    0.700, places=3)

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
        self.assertEqual(o.clean(), DBG)
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
        self.assertEqual(o.clean(), DBG)
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
        self.assertAlmostEqual(r, 1/u, places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.214, places=2)
        r = osut.rsi(c, osut.film()["partition"])
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.214, places=3)
        r = osut.rsi(c, osut.film()["wall"])
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.214, places=3)
        r = osut.rsi(c, osut.film()["wall"])
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.214, places=3)
        r = osut.rsi(c, osut.film()["wall"])
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.214, places=2)
        r = osut.rsi(c, osut.film()["roof"])
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.214, places=3)
        r = osut.rsi(c, osut.film()["roof"])
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.214, places=3)
        r = osut.rsi(c, osut.film()["roof"])
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.214, places=3)
        r = osut.rsi(c, osut.film()["floor"])
        self.assertAlmostEqual(r, 1/0.214, places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.214, places=3)
        r = osut.rsi(c, osut.film()["floor"])
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.214, places=3)
        r = osut.rsi(c, osut.film()["floor"])
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.214, places=3)
        r = osut.rsi(c, osut.film()["slab"])
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.428, places=3)
        r = osut.rsi(c, osut.film()["basement"])
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
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
        self.assertAlmostEqual(specs["uo"], osut.uo()["door"], places=3)
        r = osut.rsi(c, osut.film()["door"])
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.900, places=3)
        r = osut.rsi(c, osut.film()["door"])
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.900, places=3)
        r = osut.rsi(c) # not necessary to specify film
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
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
        self.assertAlmostEqual(specs["uo"], 0.900, places=3)
        r = osut.rsi(c) # not necessary to specify film
        self.assertAlmostEqual(r, 1/specs["uo"], places=3)
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)
        del(model)

    def test06_internal_mass(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        ratios   = dict(entrance=0.10, lobby=0.30, meeting=1.00)
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

            if round(ratio, 2) == 0.10:
                self.assertEqual(d.nameString(), m1)
                self.assertTrue("entrance" in m.nameString().lower())
            elif round(ratio, 2) == 0.30:
                self.assertEqual(d.nameString(), m2)
                self.assertTrue("lobby" in m.nameString().lower())
            elif round(ratio, 2) == 1.00:
                self.assertEqual(d.nameString(), m3)
                self.assertTrue("meeting" in m.nameString().lower())
            else:
                self.assertEqual(d.nameString(), m4)
                self.assertAlmostEqual(ratio, 2.00, places=2)

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
            self.assertAlmostEqual(plenum.volume(), 234, places=0)
        else:
            self.assertAlmostEqual(plenum.volume(), 0, places=0)

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
                self.assertTrue(osut.areSame(vtx, s.vertices()[i]))

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
                self.assertTrue(osut.areSame(vtx, s.vertices()[i]))

        # After the fix.
        if version >= 350:
            self.assertTrue(plenum.isEnclosedVolume())
            self.assertTrue(plenum.isVolumeDefaulted())
            self.assertTrue(plenum.isVolumeAutocalculated())

        self.assertAlmostEqual(plenum.volume(), 50, places=0) # right answer
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
                self.assertAlmostEqual(th, 0.00, places=2)
                continue

            self.assertTrue(th > 0)

        self.assertTrue(o.is_error())
        self.assertEqual(o.clean(), DBG)
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

        del(model)

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

        # cl1 = openstudio.model.DefaultConstructionSet
        # cl2 = openstudio.model.LayeredConstruction
        # cl2 = openstudio.model.Construction
        # id1 = cl1.__name__
        # id2 = cl2.__name__
        # id3 = cl3.__name__

        t1 = "RoofCeiling"
        t2 = "Wall"
        t3 = "Floor"
        t4 = "FixedWindow"
        n0 = "CBECS Before-1980 ClimateZone 8 (smoff) ConstSet"
        n1 = "CBECS Before-1980 ExtRoof IEAD ClimateZone 8"
        n2 = "CBECS Before-1980 ExtWall Mass ClimateZone 8"
        n3 = "000 ExtSlabCarpet 4in ClimateZone 1-8"
        n4 = "CBECS Before-1980 ExtWindow ClimateZone 5-8"
        m1 = "Invalid 'surface type' arg #5 (osut.holdsConstruction)"
        m2 = "'set' LayeredConstruction? expecting DefaultConstructionSet"
        m3 = "'set' Model? expecting DefaultConstructionSet"

        set = model.getDefaultConstructionSetByName(n0)
        c1  = model.getLayeredConstructionByName(n1)
        c2  = model.getLayeredConstructionByName(n2)
        c3  = model.getLayeredConstructionByName(n3)
        c4  = model.getLayeredConstructionByName(n4)
        self.assertTrue(set)
        self.assertTrue(c1)
        self.assertTrue(c2)
        self.assertTrue(c3)
        self.assertTrue(c4)
        set = set.get()
        c1  = c1.get()
        c2  = c2.get()
        c3  = c3.get()
        c4  = c4.get()

        # TRUE cases:
        self.assertTrue(osut.holdsConstruction(set, c1, False, True, t1))
        self.assertTrue(osut.holdsConstruction(set, c2, False, True, t2))
        self.assertTrue(osut.holdsConstruction(set, c3, True, False, t3))
        self.assertTrue(osut.holdsConstruction(set, c4, False, True, t4))

        # FALSE case: roofceiling as ground roof construction.
        self.assertFalse(osut.holdsConstruction(set, c1, True, False, t1))

        # FALSE case: ground-facing sub subsurface.
        self.assertFalse(osut.holdsConstruction(set, c4, True, False, t4))
        self.assertEqual(o.status(), 0)

        # INVALID case: arg #1 : None (instead of surface type string).
        self.assertFalse(osut.holdsConstruction(set, c1, False, True, None))
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m1)
        self.assertEqual(o.clean(), DBG)

        # INVALID case: arg #2 : empty surface type string.
        self.assertFalse(osut.holdsConstruction(set, c1, False, True, ""))
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m1)
        self.assertEqual(o.clean(), DBG)

        # INVALID case: arg #3 : construction (instead of surface type string).
        self.assertFalse(osut.holdsConstruction(set, c1, False, True, c2))
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m1)
        self.assertEqual(o.clean(), DBG)

        # INVALID case: arg #4 : construction (instead of set).
        self.assertFalse(osut.holdsConstruction(c2, c1, False, True, t1))
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertTrue(m2 in o.logs()[0]["message"])
        self.assertEqual(o.clean(), DBG)

        # INVALID case: arg #5 : model (instead of set).
        self.assertFalse(osut.holdsConstruction(mdl, c1, False, True, t1))
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertTrue(m3 in o.logs()[0]["message"])
        self.assertEqual(o.clean(), DBG)

        del(model)
        del(mdl)

    def test09_construction_set(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        version = int("".join(openstudio.openStudioVersion().split(".")))
        translator = openstudio.osversion.VersionTranslator()

        m = "construction not defaulted (osut.defaultConstructionSet)"

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        path  = openstudio.path("./tests/files/osms/in/5ZoneNoHVAC.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        for s in model.getSurfaces():
            set = osut.defaultConstructionSet(s)
            self.assertTrue(set)
            self.assertEqual(o.status(), 0)

        del(model)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        for s in model.getSurfaces():
            set = osut.defaultConstructionSet(s)
            self.assertFalse(set)
            self.assertTrue(o.is_warn())

            for l in o.logs(): self.assertEqual(l["message"], m)

        self.assertEqual(o.clean(), DBG)

        del(model)

    def test10_glazing_airfilms(self):
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

        m0 = "osut.glazingAirFilmRSi"
        m1 = "Invalid 'usi' arg #1 (%s)" % m0
        m2 = "'usi' str? expecting float (%s)" % m0
        m3 = "'usi' NoneType? expecting float (%s)" % m0

        for c in model.getConstructions():
            if not c.isFenestration(): continue

            uo = c.uFactor()
            self.assertTrue(uo)
            uo = uo.get()
            self.assertTrue(isinstance(uo, float))
            self.assertAlmostEqual(osut.glazingAirFilmRSi(uo), 0.17, places=2)
            self.assertEqual(o.status(), 0)

        # Stress tests.
        self.assertAlmostEqual(osut.glazingAirFilmRSi(9.0), 0.1216, places=4)
        self.assertTrue(o.is_warn())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m1)
        self.assertEqual(o.clean(), DBG)

        self.assertAlmostEqual(osut.glazingAirFilmRSi(""), 0.1216, places=4)
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m2)
        self.assertEqual(o.clean(), DBG)

        self.assertEqual(o.clean(), DBG)
        self.assertAlmostEqual(osut.glazingAirFilmRSi(None), 0.1216, places=4)
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m3)
        self.assertEqual(o.clean(), DBG)

        # PlanarSurface class method 'filmResistance' reports standard interior
        # or exterior air film resistances (ref: ASHRAE Fundamentals), e.g.:
        types = dict(
            StillAir_HorizontalSurface_HeatFlowsUpward=0.107,
            StillAir_45DegreeSurface_HeatFlowsUpward=0.109,
            StillAir_VerticalSurface=0.120,
            StillAir_45DegreeSurface_HeatFlowsDownward=0.134,
            StillAir_HorizontalSurface_HeatFlowsDownward=0.162,
            MovingAir_15mph=0.030,
            MovingAir_7p5mph=0.044)
            #   https://github.com/NREL/OpenStudio/blob/
            #   1c6fe48c49987c16e95e90ee3bd088ad0649ab9c/src/model/
            #   PlanarSurface.cpp#L854

        for i in openstudio.model.FilmResistanceType().getValues():
            t1 = openstudio.model.FilmResistanceType(i)
            self.assertTrue(t1.valueDescription() in types)
            r  = openstudio.model.PlanarSurface.filmResistance(t1)
            self.assertAlmostEqual(r, types[t1.valueDescription()], places=3)
            if i > 4: continue

            # PlanarSurface class method 'stillAirFilmResistance' offers a
            # tilt-dependent interior air film resistance, e.g.:
            deg = i * 45
            rad = deg * math.pi/180
            rsi = openstudio.model.PlanarSurface.stillAirFilmResistance(rad)
            # print("%i: %i: %.3f: %.3f" % (i, deg, r, rsi))
            #   0:   0: 0.107: 0.106
            #   1:  45: 0.109: 0.109 # ... OK
            #   2:  90: 0.120: 0.120 # ... OK
            #   3: 135: 0.134: 0.137
            #   4: 180: 0.162: 0.160
            if deg < 45 or deg > 90: continue

            self.assertAlmostEqual(rsi, r, places=2)
            # The method is used for (opaque) Surfaces. The correlation/
            # regression isn't perfect, yet appears fairly reliable for
            # intermediate angles between ~0° and 90°.
            #   https://github.com/NREL/OpenStudio/blob/
            #   1c6fe48c49987c16e95e90ee3bd088ad0649ab9c/src/model/
            #   PlanarSurface.cpp#L878

        del(model)

    def test11_rsi(self):
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

        m0  = "osut.rsi"
        m1 = "'lc' str? expecting LayeredConstruction (%s)" % m0
        m2 = "'lc' NoneType? expecting LayeredConstruction (%s)" % m0
        m3 = "Negative 'film' (%s)" % m0
        m4 = "'film' NoneType? expecting float (%s)" % m0
        m5 = "Negative 'temp K' (%s)" % m0
        m6 = "'temp K' NoneType? expecting float (%s)" % m0

        for s in model.getSurfaces():
            if not s.isPartOfEnvelope(): continue

            lc = s.construction()
            self.assertTrue(lc)
            lc = lc.get().to_LayeredConstruction()
            self.assertTrue(lc)
            lc = lc.get()

            if s.isGroundSurface(): # 4x slabs on grade in SEB model
                self.assertAlmostEqual(s.filmResistance(), 0.160, places=3)
                self.assertAlmostEqual(osut.rsi(lc, s.filmResistance()), 0.448, places=3)
                self.assertEqual(o.status(), 0)
            else:
                if s.surfaceType() == "Wall":
                    self.assertAlmostEqual(s.filmResistance(), 0.150, places=3)
                    self.assertAlmostEqual(osut.rsi(lc, s.filmResistance()), 2.616, places=3)
                    self.assertEqual(o.status(), 0)
                else: # RoofCeiling
                    self.assertAlmostEqual(s.filmResistance(), 0.136, places=3)
                    self.assertAlmostEqual(osut.rsi(lc, s.filmResistance()), 5.631, places=3)
                    self.assertEqual(o.status(), 0)

        # Stress tests.
        self.assertAlmostEqual(osut.rsi("", 0.150), 0, places=2)
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m1)
        self.assertEqual(o.clean(), DBG)

        self.assertAlmostEqual(osut.rsi(None, 0.150), 0, places=2)
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m2)
        self.assertEqual(o.clean(), DBG)

        lc = model.getLayeredConstructionByName("SLAB-ON-GRADE-FLOOR")
        self.assertTrue(lc)
        lc = lc.get()

        self.assertAlmostEqual(osut.rsi(lc, -1), 0, places=0)
        self.assertTrue(o.is_error())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m3)
        self.assertEqual(o.clean(), DBG)

        self.assertAlmostEqual(osut.rsi(lc, None), 0, places=0)
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m4)
        self.assertEqual(o.clean(), DBG)

        self.assertAlmostEqual(osut.rsi(lc, 0.150, -300), 0, places=0)
        self.assertTrue(o.is_error())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m5)
        self.assertEqual(o.clean(), DBG)

        self.assertAlmostEqual(osut.rsi(lc, 0.150, None), 0, places=0)
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m6)
        self.assertEqual(o.clean(), DBG)

        del(model)

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
                self.assertAlmostEqual(lyr["r"], 5.08, places=2)
            elif id == "EXTERIOR-WALL":
                self.assertEqual(lyr["index"], 2)
                self.assertAlmostEqual(lyr["r"], 1.47, places=2)
            elif id == "Default interior ceiling":
                self.assertEqual(lyr["index"], 0)
                self.assertAlmostEqual(lyr["r"], 0.12, places=2)
            elif id == "INTERIOR-WALL":
                self.assertEqual(lyr["index"], 1)
                self.assertAlmostEqual(lyr["r"], 0.24, places=2)
            else:
                self.assertEqual(lyr["index"], 0)
                self.assertAlmostEqual(lyr["r"], 0.29, places=2)

        # Final stress tests.
        lyr = osut.insulatingLayer(None)
        self.assertTrue(o.is_debug())
        self.assertFalse(lyr["index"])
        self.assertFalse(lyr["type"])
        self.assertAlmostEqual(lyr["r"], 0.00)
        self.assertEqual(len(o.logs()), 1)
        self.assertTrue(m0 in o.logs()[0]["message"])
        self.assertEqual(o.clean(), DBG)

        lyr = osut.insulatingLayer("")
        self.assertTrue(o.is_debug())
        self.assertFalse(lyr["index"])
        self.assertFalse(lyr["type"])
        self.assertAlmostEqual(lyr["r"], 0.00)
        self.assertTrue(len(o.logs()), 1)
        self.assertTrue(m0 in o.logs()[0]["message"])
        self.assertEqual(o.clean(), DBG)

        lyr = osut.insulatingLayer(model)
        self.assertTrue(o.is_debug())
        self.assertFalse(lyr["index"])
        self.assertFalse(lyr["type"])
        self.assertAlmostEqual(lyr["r"], 0.00)
        self.assertTrue(len(o.logs()), 1)
        self.assertTrue(m0 in o.logs()[0]["message"])
        self.assertEqual(o.clean(), DBG)

        del(model)

    def test13_spandrels(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        # version = int("".join(openstudio.openStudioVersion().split(".")))
        translator = openstudio.osversion.VersionTranslator()

        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        office_walls = []
        # Smalloffice 1 Wall 1
        # Smalloffice 1 Wall 2
        # Smalloffice 1 Wall 6
        plenum_walls = []
        # Level0 Small office 1 Ceiling Plenum AbvClgPlnmWall 6
        # Level0 Small office 1 Ceiling Plenum AbvClgPlnmWall 2
        # Level0 Small office 1 Ceiling Plenum AbvClgPlnmWall 1

        for s in model.getSurfaces():
            if not s.outsideBoundaryCondition().lower() == "outdoors": continue
            if not s.surfaceType().lower() == "wall": continue

            self.assertFalse(osut.areSpandrels(s))

            if "smalloffice 1" in s.nameString().lower():
                office_walls.append(s)
            elif "small office 1 ceiling plenum" in s.nameString().lower():
                plenum_walls.append(s)

        self.assertEqual(len(office_walls), 3)
        self.assertEqual(len(plenum_walls), 3)
        self.assertEqual(o.status(), 0)

        # Tag Small Office walls (& plenum walls) in SEB as 'spandrels'.
        tag = "spandrel"

        for wall in (office_walls + plenum_walls):
            # First, failed attempts:
            self.assertTrue(wall.additionalProperties().setFeature(tag, "True"))
            self.assertTrue(wall.additionalProperties().hasFeature(tag))
            prop = wall.additionalProperties().getFeatureAsBoolean(tag)
            self.assertFalse(prop)

            # Successful attempts.
            self.assertTrue(wall.additionalProperties().setFeature(tag, True))
            self.assertTrue(wall.additionalProperties().hasFeature(tag))
            prop = wall.additionalProperties().getFeatureAsBoolean(tag)
            self.assertTrue(prop)
            self.assertTrue(prop.get())
            self.assertTrue(osut.areSpandrels(wall))

        self.assertEqual(o.status(), 0)

        del(model)

    def test14_schedule_ruleset_minmax(self):
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

        cl1 = openstudio.model.ScheduleRuleset
        cl2 = openstudio.model.ScheduleConstant
        sc1 = "Space Thermostat Cooling Setpoint"
        sc2 = "Schedule Constant 1"
        mth = "osut.scheduleRulesetMinMax"
        m1  = "'sched' NoneType? expecting ScheduleRuleset (%s)" % mth
        m2  = "'sched' str? expecting ScheduleRuleset (%s)" % mth
        m3  = "'sched' ScheduleConstant? expecting ScheduleRuleset (%s)" % mth

        sched = model.getScheduleRulesetByName(sc1)
        self.assertTrue(sched)
        sched = sched.get()
        self.assertTrue(isinstance(sched, cl1))

        sch = model.getScheduleConstantByName(sc2)
        self.assertTrue(sch)
        sch = sch.get()
        self.assertTrue(isinstance(sch, cl2))

        # Valid case.
        minmax = osut.scheduleRulesetMinMax(sched)
        self.assertTrue(isinstance(minmax, dict))
        self.assertTrue("min" in minmax)
        self.assertTrue("max" in minmax)
        self.assertAlmostEqual(minmax["min"], 23.89, places=2)
        self.assertAlmostEqual(minmax["max"], 23.89, places=2)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())

        # Invalid parameter.
        minmax = osut.scheduleRulesetMinMax(None)
        self.assertTrue(isinstance(minmax, dict))
        self.assertTrue("min" in minmax)
        self.assertTrue("max" in minmax)
        self.assertFalse(minmax["min"])
        self.assertFalse(minmax["max"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m1)
        self.assertEqual(o.clean(), DBG)

        # Invalid parameter.
        minmax = osut.scheduleRulesetMinMax("")
        self.assertTrue(isinstance(minmax, dict))
        self.assertTrue("min" in minmax)
        self.assertTrue("max" in minmax)
        self.assertFalse(minmax["min"])
        self.assertFalse(minmax["max"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m2)
        self.assertEqual(o.clean(), DBG)

        # Invalid parameter (wrong schedule type).
        minmax = osut.scheduleRulesetMinMax(sch)
        self.assertTrue(isinstance(minmax, dict))
        self.assertTrue("min" in minmax)
        self.assertTrue("max" in minmax)
        self.assertFalse(minmax["min"])
        self.assertFalse(minmax["max"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m3)
        self.assertEqual(o.clean(), DBG)

        del(model)

    def test15_schedule_constant_minmax(self):
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

        cl1 = openstudio.model.ScheduleConstant
        cl2 = openstudio.model.ScheduleRuleset
        sc1 = "Schedule Constant 1"
        sc2 = "Space Thermostat Cooling Setpoint"
        mth = "osut.scheduleConstantMinMax"
        m1 = "'sched' NoneType? expecting ScheduleConstant (%s)" % mth
        m2 = "'sched' str? expecting ScheduleConstant (%s)" % mth
        m3 = "'sched' ScheduleRuleset? expecting ScheduleConstant (%s)" % mth

        sched = model.getScheduleConstantByName(sc1)
        self.assertTrue(sched)
        sched = sched.get()
        self.assertTrue(isinstance(sched, cl1))

        sch = model.getScheduleRulesetByName(sc2)
        self.assertTrue(sch)
        sch = sch.get()
        self.assertTrue(isinstance(sch, cl2))

        # Valid case.
        minmax = osut.scheduleConstantMinMax(sched)
        self.assertTrue(isinstance(minmax, dict))
        self.assertTrue("min" in minmax)
        self.assertTrue("max" in minmax)
        self.assertAlmostEqual(minmax["min"], 139.88, places=2)
        self.assertAlmostEqual(minmax["max"], 139.88, places=2)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())

        # Invalid parameter.
        minmax = osut.scheduleConstantMinMax(None)
        self.assertTrue(isinstance(minmax, dict))
        self.assertTrue("min" in minmax)
        self.assertTrue("max" in minmax)
        self.assertFalse(minmax["min"])
        self.assertFalse(minmax["max"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m1)
        self.assertEqual(o.clean(), DBG)

        # Invalid parameter.
        minmax = osut.scheduleConstantMinMax("")
        self.assertTrue(isinstance(minmax, dict))
        self.assertTrue("min" in minmax)
        self.assertTrue("max" in minmax)
        self.assertFalse(minmax["min"])
        self.assertFalse(minmax["max"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m2)
        self.assertEqual(o.clean(), DBG)

        # Invalid parameter.
        minmax = osut.scheduleConstantMinMax(sch)
        self.assertTrue(isinstance(minmax, dict))
        self.assertTrue("min" in minmax)
        self.assertTrue("max" in minmax)
        self.assertFalse(minmax["min"])
        self.assertFalse(minmax["max"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m3)
        self.assertEqual(o.clean(), DBG)

        del(model)

    def test16_schedule_compact_minmax(self):
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

        spt = 22
        sc2 = "Building HVAC Operation"
        cl1 = openstudio.model.ScheduleCompact
        cl2 = openstudio.model.Schedule
        mth = "osut.scheduleCompactMinMax"
        m1  = "'sched' NoneType? expecting ScheduleCompact (%s)" % mth
        m2  = "'sched' str? expecting ScheduleCompact (%s)" % mth
        m3  = "'sched' Schedule? expecting ScheduleCompact (%s)" % mth

        sched = openstudio.model.ScheduleCompact(model, spt)
        self.assertTrue(isinstance(sched, openstudio.model.ScheduleCompact))
        sched.setName("compact schedule")

        sch = model.getScheduleByName(sc2)
        self.assertTrue(sch)
        sch = sch.get()

        # Valid case.
        minmax = osut.scheduleCompactMinMax(sched)
        self.assertTrue(isinstance(minmax, dict))
        self.assertTrue("min" in minmax)
        self.assertTrue("max" in minmax)
        self.assertAlmostEqual(minmax["min"], spt, places=2)
        self.assertAlmostEqual(minmax["max"], spt, places=2)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())

        # Invalid parameter.
        minmax = osut.scheduleCompactMinMax(None)
        self.assertTrue(isinstance(minmax, dict))
        self.assertTrue("min" in minmax)
        self.assertTrue("max" in minmax)
        self.assertFalse(minmax["min"])
        self.assertFalse(minmax["max"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m1)
        self.assertEqual(o.clean(), DBG)

        # Invalid parameter.
        minmax = osut.scheduleCompactMinMax("")
        self.assertTrue(isinstance(minmax, dict))
        self.assertTrue("min" in minmax)
        self.assertTrue("max" in minmax)
        self.assertFalse(minmax["min"])
        self.assertFalse(minmax["max"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m2)
        self.assertEqual(o.clean(), DBG)

        # Invalid parameter.
        minmax = osut.scheduleCompactMinMax(sch)
        self.assertTrue(isinstance(minmax, dict))
        self.assertTrue("min" in minmax)
        self.assertTrue("max" in minmax)
        self.assertFalse(minmax["min"])
        self.assertFalse(minmax["max"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m3)
        self.assertEqual(o.clean(), DBG)

        del(model)

    def test17_minmax_heatcool_setpoints(self):
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

        m1 = "osut.maxHeatScheduledSetpoint"
        m2 = "osut.minCoolScheduledSetpoint"
        z1 = "Level 0 Ceiling Plenum Zone"
        z2 = "Single zone"

        mth1 = "osut.maxHeatScheduledSetpoint"
        mth2 = "osut.minCoolScheduledSetpoint"
        msg1 = "'zone' NoneType? expecting ThermalZone (%s)" % mth1
        msg2 = "'zone' NoneType? expecting ThermalZone (%s)" % mth2
        msg3 = "'zone' str? expecting ThermalZone (%s)" % mth1
        msg4 = "'zone' str? expecting ThermalZone (%s)" % mth2

        for z in model.getThermalZones():
            z0  = z.nameString()
            res = osut.maxHeatScheduledSetpoint(z)
            self.assertTrue(isinstance(res, dict))
            self.assertTrue("spt" in res)
            self.assertTrue("dual" in res)
            if z0 == z1: self.assertFalse(res["spt"])
            if z1 == z2: self.assertAlmostTrue(res["spt"], 22.11, places=2)
            if z0 == z1: self.assertFalse(res["dual"])
            if z0 == z2: self.assertTrue(res["dual"])
            self.assertEqual(o.status(), 0)

            res = osut.minCoolScheduledSetpoint(z)
            self.assertTrue(isinstance(res, dict))
            self.assertTrue("spt" in res)
            self.assertTrue("dual" in res)
            if z0 == z1: self.assertFalse(res["spt"])
            if z0 == z2: self.assertAlmostEqual(res["spt"], 22.78, places=2)
            if z0 == z1: self.assertFalse(res["dual"])
            if z0 == z2: self.assertTrue(res["dual"])
            self.assertEqual(o.status(), 0)

        # Invalid cases.
        res = osut.maxHeatScheduledSetpoint(None) # bad argument
        self.assertTrue(isinstance(res, dict))
        self.assertTrue("spt" in res)
        self.assertTrue("dual" in res)
        self.assertFalse(res["spt"])
        self.assertFalse(res["dual"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], msg1)
        self.assertEqual(o.clean(), DBG)

        res = osut.minCoolScheduledSetpoint(None) # bad argument
        self.assertTrue(isinstance(res, dict))
        self.assertTrue("spt" in res)
        self.assertTrue("dual" in res)
        self.assertFalse(res["spt"])
        self.assertFalse(res["dual"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], msg2)
        self.assertEqual(o.clean(), DBG)

        res = osut.maxHeatScheduledSetpoint("") # bad argument
        self.assertTrue(isinstance(res, dict))
        self.assertTrue("spt" in res)
        self.assertTrue("dual" in res)
        self.assertFalse(res["spt"])
        self.assertFalse(res["dual"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], msg3)
        self.assertEqual(o.clean(), DBG)

        res = osut.minCoolScheduledSetpoint("") # bad argument
        self.assertTrue(isinstance(res, dict))
        self.assertTrue("spt" in res)
        self.assertTrue("dual" in res)
        self.assertFalse(res["spt"])
        self.assertFalse(res["dual"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], msg4)
        self.assertEqual(o.clean(), DBG)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Add electric heating to 1x slab.
        entry = model.getSpaceByName("Entry way 1")
        self.assertTrue(entry)
        entry = entry.get()
        floor = [s for s in entry.surfaces() if s.surfaceType() == "Floor"]

        self.assertTrue(isinstance(floor, list))
        self.assertEqual(len(floor), 1)
        floor = floor[0]

        self.assertTrue(entry.thermalZone())
        tzone = entry.thermalZone().get()

        # Retrieve construction.
        self.assertFalse(floor.isConstructionDefaulted())
        c = floor.construction()
        self.assertTrue(c)
        c = c.get().to_LayeredConstruction()
        self.assertTrue(c)
        c = c.get()

        # Recover single construction layer (concrete slab).
        layers = openstudio.model.MaterialVector()
        layers.append(c.layers()[0])
        layers.append(c.layers()[0])
        self.assertEqual(len(c.layers()), 1)

        # Generate construction with internal heat source.
        cc = openstudio.model.ConstructionWithInternalSource(model)
        cc.setName("ihs")
        self.assertTrue(cc.setLayers(layers))
        self.assertTrue(cc.setSourcePresentAfterLayerNumber(1))
        self.assertTrue(cc.setTemperatureCalculationRequestedAfterLayerNumber(1))
        self.assertTrue(floor.setConstruction(cc))

        availability = osut.availabilitySchedule(model)
        schedule = openstudio.model.ScheduleConstant(model)
        self.assertTrue(schedule.setValue(22.78)) # reuse cooling setpoint

        # Create radiant electric heating.
        ht = (openstudio.model.ZoneHVACLowTemperatureRadiantElectric(
            model, availability, schedule))
        ht.setName("radiant electric")
        self.assertTrue(ht.setRadiantSurfaceType("Floors"))
        self.assertTrue(ht.addToThermalZone(tzone))
        self.assertTrue(tzone.setHeatingPriority(ht, 1))
        found = False

        for eq in tzone.equipment():
          if eq.nameString() == "radiant electric": found = True

        self.assertTrue(found)

        model.save("./tests/files/osms/out/seb_ihs.osm", True)

        # Regardless of the radiant electric heating installation, priority is
        # given to the zone thermostat heating setpoint.
        stpts = osut.setpoints(entry)
        self.assertAlmostEqual(stpts["heating"], 22.11, places=2)

        # Yet if one were to remove the thermostat altogether ...
        tzone.resetThermostatSetpointDualSetpoint()
        res = osut.maxHeatScheduledSetpoint(tzone)
        self.assertTrue(isinstance(res, dict))
        self.assertTrue("spt" in res)
        self.assertTrue("dual" in res)
        self.assertTrue(res["spt"])
        self.assertAlmostEqual(res["spt"], 22.78, places=2) # radiant heating
        self.assertFalse(res["dual"])

        stpts = osut.setpoints(entry)
        self.assertTrue(stpts["heating"])
        self.assertAlmostEqual(stpts["heating"], 22.78, places=2)

        del(model)

    def test18_hvac_airloops(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        msg = "'model' str? expecting Model (osut.hasAirLoopsHVAC)"
        version = int("".join(openstudio.openStudioVersion().split(".")))
        translator = openstudio.osversion.VersionTranslator()

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        self.assertEqual(o.clean(), DBG)
        self.assertTrue(osut.hasAirLoopsHVAC(model))
        self.assertEqual(o.status(), 0)
        self.assertEqual(osut.hasAirLoopsHVAC(""), False)
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], msg)
        self.assertEqual(o.clean(), DBG)

        del(model)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        path  = openstudio.path("./tests/files/osms/in/5ZoneNoHVAC.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        self.assertEqual(o.clean(), DBG)
        self.assertFalse(osut.hasAirLoopsHVAC(model))
        self.assertEqual(o.status(), 0)
        self.assertEqual(osut.hasAirLoopsHVAC(""), False)
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], msg)
        self.assertEqual(o.clean(), DBG)

        del(model)

    def test19_vestibules(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        translator = openstudio.osversion.VersionTranslator()

        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        # Tag "Entry way 1" in SEB as a vestibule.
        tag   = "vestibule"
        msg   = "Invalid 'vestibule' arg #1 (osut.areVestibules)"
        entry = model.getSpaceByName("Entry way 1")
        self.assertTrue(entry)
        entry = entry.get()
        sptype = entry.spaceType()
        self.assertTrue(sptype)
        sptype = sptype.get()
        self.assertFalse(sptype.standardsSpaceType())
        self.assertFalse(entry.additionalProperties().hasFeature(tag))
        self.assertFalse(osut.areVestibules(entry))
        self.assertEqual(o.status(), 0)

        # First, failed attempts:
        self.assertTrue(sptype.setStandardsSpaceType("vestibool"))
        self.assertFalse(osut.areVestibules(entry))
        self.assertEqual(o.status(), 0)
        sptype.resetStandardsSpaceType()

        self.assertTrue(entry.additionalProperties().setFeature(tag, False))
        self.assertTrue(entry.additionalProperties().hasFeature(tag))
        prop = entry.additionalProperties().getFeatureAsBoolean(tag)
        self.assertTrue(prop)
        self.assertFalse(prop.get())
        self.assertFalse(osut.areVestibules(entry))
        self.assertTrue(entry.additionalProperties().resetFeature(tag))
        self.assertEqual(o.status(), 0)

        self.assertTrue(entry.additionalProperties().setFeature(tag, "True"))
        self.assertTrue(entry.additionalProperties().hasFeature(tag))
        prop = entry.additionalProperties().getFeatureAsBoolean(tag)
        self.assertFalse(prop)
        self.assertFalse(osut.areVestibules(entry))
        self.assertTrue(o.is_error())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], msg)
        self.assertEqual(o.clean(), DBG)
        self.assertTrue(entry.additionalProperties().resetFeature(tag))

        # Successful attempts.
        self.assertTrue(sptype.setStandardsSpaceType("vestibule"))
        self.assertTrue(osut.areVestibules(entry))
        self.assertEqual(o.status(), 0)
        sptype.resetStandardsSpaceType()

        self.assertTrue(entry.additionalProperties().setFeature(tag, True))
        self.assertTrue(entry.additionalProperties().hasFeature(tag))
        prop = entry.additionalProperties().getFeatureAsBoolean(tag)
        self.assertTrue(prop)
        self.assertTrue(prop.get())
        self.assertTrue(osut.areVestibules(entry))
        self.assertTrue(entry.additionalProperties().resetFeature(tag))
        self.assertEqual(o.status(), 0)

        del(model)

    def test20_setpoints_plenums_attics(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        cl1 = openstudio.model.Space
        cl2 = openstudio.model.Model
        mt1 = "(osut.arePlenums)"
        mt2 = "(osut.hasHeatingTemperatureSetpoints)"
        mt3 = "(osut.setpoints)"
        ms1 = "'set' NoneType? expecting list %s" % mt1
        ms2 = "'model' NoneType? expecting %s %s" % (cl2.__name__, mt2)
        ms3 = "'space' Nonetype? expecting %s %s" % (cl1.__name__, mt3)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Stress tests.
        self.assertEqual(o.clean(), DBG)
        self.assertFalse(osut.arePlenums(None))
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], ms1)
        self.assertEqual(o.clean(), DBG)

        self.assertFalse(osut.hasHeatingTemperatureSetpoints(None))
        self.assertTrue(o.is_debug())
        self.assertTrue(len(o.logs()), 1)
        self.assertTrue(o.logs()[0]["message"], ms2)
        self.assertEqual(o.clean(), DBG)

        self.assertFalse(osut.setpoints(None)["heating"])
        self.assertTrue(o.is_debug())
        self.assertTrue(len(o.logs()), 1)
        self.assertTrue(o.logs()[0]["message"], ms3)
        self.assertEqual(o.clean(), DBG)

        translator = openstudio.osversion.VersionTranslator()

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        plenum = model.getSpaceByName("Level 0 Ceiling Plenum")
        self.assertTrue(plenum)
        plenum = plenum.get()

        for space in model.getSpaces():
            if space == plenum: continue

            self.assertTrue(space.partofTotalFloorArea())
            zone = space.thermalZone()
            self.assertTrue(zone)
            zone = zone.get()
            heat = osut.maxHeatScheduledSetpoint(zone)
            cool = osut.minCoolScheduledSetpoint(zone)
            spts = osut.setpoints(space)

            self.assertAlmostEqual(heat["spt"], 22.11, places=2)
            self.assertAlmostEqual(cool["spt"], 22.78, places=2)
            self.assertTrue(heat["dual"])
            self.assertTrue(cool["dual"])

            self.assertFalse(osut.arePlenums(space))
            self.assertFalse(osut.isUnconditioned(space))
            self.assertAlmostEqual(spts["heating"], 22.11, places=2)
            self.assertAlmostEqual(spts["cooling"], 22.78, places=2)
            self.assertEqual(o.status(), 0)

        zone = plenum.thermalZone()
        self.assertTrue(zone)
        zone = zone.get()
        heat = osut.maxHeatScheduledSetpoint(zone) # simply returns model info
        cool = osut.minCoolScheduledSetpoint(zone) # simply returns model info
        stps = osut.setpoints(plenum)

        self.assertFalse(heat["spt"])
        self.assertFalse(cool["spt"])
        self.assertFalse(heat["dual"])
        self.assertFalse(cool["dual"])

        # "Plenum" spaceType triggers an INDIRECTLYCONDITIONED status; returns
        # defaulted setpoint temperatures.
        self.assertFalse(plenum.partofTotalFloorArea())
        self.assertTrue(osut.arePlenums(plenum))
        self.assertFalse(osut.isUnconditioned(plenum))
        self.assertAlmostEqual(stps["heating"], 21.00, places=2)
        self.assertAlmostEqual(stps["cooling"], 24.00, places=2)
        self.assertEqual(o.status(), 0)

        # Tag plenum as an INDIRECTLYCONDITIONED space (linked to "Open area 1");
        # returns "Open area 1" setpoint temperatures.
        key  = "indirectlyconditioned"
        val  = "Open area 1"
        self.assertTrue(plenum.additionalProperties().setFeature(key, val))
        stps = osut.setpoints(plenum)
        self.assertTrue(osut.arePlenums(plenum))
        self.assertFalse(osut.isUnconditioned(plenum))
        self.assertAlmostEqual(stps["heating"], 22.11, places=2)
        self.assertAlmostEqual(stps["cooling"], 22.78, places=2)
        self.assertEqual(o.status(), 0)

        # Tag plenum instead as an UNCONDITIONED space.
        self.assertTrue(plenum.additionalProperties().resetFeature(key))
        key = "space_conditioning_category"
        val = "Unconditioned"
        self.assertTrue(plenum.additionalProperties().setFeature(key, val))
        self.assertTrue(osut.arePlenums(plenum))
        self.assertTrue(osut.isUnconditioned(plenum))
        self.assertFalse(osut.setpoints(plenum)["heating"])
        self.assertFalse(osut.setpoints(plenum)["cooling"])
        self.assertEqual(o.status(), 0)

        del(model)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        path  = openstudio.path("./tests/files/osms/in/warehouse.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        # Despite different heating setpoints, all 3 thermal spaces/zones have
        # some heating and some cooling, i.e. not strictly REFRIGERATED nor
        # SEMIHEATED.
        for space in model.getSpaces():
            self.assertFalse(osut.isRefrigerated(space))
            self.assertFalse(osut.isSemiheated(space))

        del(model)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        path  = openstudio.path("./tests/files/osms/in/smalloffice.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        attic = model.getSpaceByName("Attic")
        self.assertTrue(attic)
        attic = attic.get()

        for space in model.getSpaces():
            if space == attic: continue

            zone = space.thermalZone()
            self.assertTrue(zone)
            zone = zone.get()
            heat = osut.maxHeatScheduledSetpoint(zone)
            cool = osut.minCoolScheduledSetpoint(zone)
            stps = osut.setpoints(space)

            self.assertAlmostEqual(heat["spt"], 21.11, places=2)
            self.assertAlmostEqual(cool["spt"], 23.89, places=2)
            self.assertTrue(heat["dual"])
            self.assertTrue(cool["dual"])

            self.assertTrue(space.partofTotalFloorArea())
            self.assertFalse(osut.arePlenums(space))
            self.assertFalse(osut.isUnconditioned(space))
            self.assertAlmostEqual(stps["heating"], 21.11, places=2)
            self.assertAlmostEqual(stps["cooling"], 23.89, places=2)

        zone = attic.thermalZone()
        self.assertTrue(zone)
        zone = zone.get()
        heat = osut.maxHeatScheduledSetpoint(zone)
        cool = osut.minCoolScheduledSetpoint(zone)
        stps = osut.setpoints(attic)

        self.assertFalse(heat["spt"])
        self.assertFalse(cool["spt"])
        self.assertFalse(heat["dual"])
        self.assertFalse(cool["dual"])
        self.assertFalse(osut.arePlenums(attic))
        self.assertTrue(osut.isUnconditioned(attic))
        self.assertFalse(attic.partofTotalFloorArea())
        self.assertEqual(o.status(), 0)

        # Tag attic as an INDIRECTLYCONDITIONED space (linked to "Core_ZN").
        key = "indirectlyconditioned"
        val = "Core_ZN"
        self.assertTrue(attic.additionalProperties().setFeature(key, val))
        stps = osut.setpoints(attic)
        self.assertFalse(osut.arePlenums(attic))
        self.assertFalse(osut.isUnconditioned(attic))
        self.assertAlmostEqual(stps["heating"], 21.11, places=2)
        self.assertAlmostEqual(stps["cooling"], 23.89, places=2)
        self.assertEqual(o.status(), 0)
        self.assertTrue(attic.additionalProperties().resetFeature(key))

        # Tag attic instead as an SEMIHEATED space. First, test an invalid entry.
        key = "space_conditioning_category"
        val = "Demiheated"
        msg = "Invalid '%s:%s' (osut.setpoints)" % (key, val)
        self.assertTrue(attic.additionalProperties().setFeature(key, val))
        stps = osut.setpoints(attic)
        self.assertFalse(osut.arePlenums(attic))
        self.assertTrue(osut.isUnconditioned(attic))
        self.assertFalse(stps["heating"])
        self.assertFalse(stps["cooling"])
        self.assertTrue(attic.additionalProperties().hasFeature(key))
        cnd = attic.additionalProperties().getFeatureAsString(key)
        self.assertTrue(cnd)
        self.assertEqual(cnd.get(), val)
        self.assertTrue(o.is_error())

        # 3x same error, as arePlenums/isUnconditioned call setpoints(attic).
        self.assertEqual(len(o.logs()), 3)
        for l in o.logs(): self.assertEqual(l["message"], msg)

        # Now test a valid entry.
        self.assertTrue(attic.additionalProperties().resetFeature(key))
        self.assertEqual(o.clean(), DBG)
        val = "Semiheated"
        self.assertTrue(attic.additionalProperties().setFeature(key, val))
        stps = osut.setpoints(attic)
        self.assertFalse(osut.arePlenums(attic))
        self.assertFalse(osut.isUnconditioned(attic))
        self.assertTrue(osut.isSemiheated(attic))
        self.assertFalse(osut.isRefrigerated(attic))
        self.assertAlmostEqual(stps["heating"], 14.00, places=2)
        self.assertFalse(stps["cooling"])
        self.assertEqual(o.status(), 0)
        self.assertTrue(attic.additionalProperties().hasFeature(key))
        cnd = attic.additionalProperties().getFeatureAsString(key)
        self.assertTrue(cnd)
        self.assertEqual(cnd.get(), val)
        self.assertEqual(o.status(), 0)

        del(model)
        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Consider adding LargeOffice model to test SDK's "isPlenum" ... @todo

    def test21_availability_schedules(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        v = int("".join(openstudio.openStudioVersion().split(".")))
        translator = openstudio.osversion.VersionTranslator()

        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        year = model.yearDescription()
        self.assertTrue(year)
        year = year.get()

        am01 = openstudio.Time(0, 1)
        pm11 = openstudio.Time(0,23)

        jan01 = year.makeDate(openstudio.MonthOfYear("Jan"),  1)
        apr30 = year.makeDate(openstudio.MonthOfYear("Apr"), 30)
        may01 = year.makeDate(openstudio.MonthOfYear("May"),  1)
        oct31 = year.makeDate(openstudio.MonthOfYear("Oct"), 31)
        nov01 = year.makeDate(openstudio.MonthOfYear("Nov"),  1)
        dec31 = year.makeDate(openstudio.MonthOfYear("Dec"), 31)
        self.assertTrue(isinstance(oct31, openstudio.Date))

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        sch = osut.availabilitySchedule(model) # ON (default)
        self.assertTrue(isinstance(sch, openstudio.model.ScheduleRuleset))
        self.assertEqual(sch.nameString(), "ON Availability SchedRuleset")

        limits = sch.scheduleTypeLimits()
        self.assertTrue(limits)
        limits = limits.get()
        name = limits.nameString()
        self.assertEqual(name, "HVAC Operation ScheduleTypeLimits")

        default = sch.defaultDaySchedule()
        self.assertEqual(default.nameString(), "ON Availability dftDaySched")
        self.assertTrue(default.times())
        self.assertTrue(default.values())
        self.assertEqual(len(default.times()), 1)
        self.assertEqual(len(default.values()), 1)
        self.assertEqual(default.getValue(am01), 1)
        self.assertEqual(default.getValue(pm11), 1)

        self.assertTrue(sch.isWinterDesignDayScheduleDefaulted())
        self.assertTrue(sch.isSummerDesignDayScheduleDefaulted())
        self.assertTrue(sch.isHolidayScheduleDefaulted())
        if v >= 330: self.assertTrue(sch.isCustomDay1ScheduleDefaulted())
        if v >= 330: self.assertTrue(sch.isCustomDay2ScheduleDefaulted())
        self.assertEqual(sch.summerDesignDaySchedule(), default)
        self.assertEqual(sch.winterDesignDaySchedule(), default)
        self.assertEqual(sch.holidaySchedule(), default)
        if v >= 330: self.assertEqual(sch.customDay1Schedule(), default)
        if v >= 330: self.assertEqual(sch.customDay2Schedule(), default)
        self.assertFalse(sch.scheduleRules())

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        sch = osut.availabilitySchedule(model, "Off")
        self.assertTrue(isinstance(sch, openstudio.model.ScheduleRuleset))
        name = sch.nameString()
        self.assertEqual(name, "OFF Availability SchedRuleset")

        limits = sch.scheduleTypeLimits()
        self.assertTrue(limits)
        limits = limits.get()
        name = limits.nameString()
        self.assertEqual(name, "HVAC Operation ScheduleTypeLimits")

        default = sch.defaultDaySchedule()
        self.assertEqual(default.nameString(), "OFF Availability dftDaySched")
        self.assertTrue(default.times())
        self.assertTrue(default.values())
        self.assertEqual(len(default.times()), 1)
        self.assertEqual(len(default.values()), 1)
        self.assertEqual(int(default.getValue(am01)), 0)
        self.assertEqual(int(default.getValue(pm11)), 0)

        self.assertTrue(sch.isWinterDesignDayScheduleDefaulted())
        self.assertTrue(sch.isSummerDesignDayScheduleDefaulted())
        self.assertTrue(sch.isHolidayScheduleDefaulted())
        if v >= 330: self.assertTrue(sch.isCustomDay1ScheduleDefaulted())
        if v >= 330: self.assertTrue(sch.isCustomDay2ScheduleDefaulted())
        self.assertEqual(sch.summerDesignDaySchedule(), default)
        self.assertEqual(sch.winterDesignDaySchedule(), default)
        self.assertEqual(sch.holidaySchedule(), default)
        if v >= 330: self.assertEqual(sch.customDay1Schedule(), default)
        if v >= 330: self.assertEqual(sch.customDay2Schedule(), default)
        self.assertFalse(sch.scheduleRules())

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        sch = osut.availabilitySchedule(model, "Winter")
        self.assertTrue(isinstance(sch, openstudio.model.ScheduleRuleset))
        self.assertEqual(sch.nameString(), "WINTER Availability SchedRuleset")

        limits = sch.scheduleTypeLimits()
        self.assertTrue(limits)
        limits = limits.get()
        name = "HVAC Operation ScheduleTypeLimits"
        self.assertEqual(limits.nameString(), name)

        default = sch.defaultDaySchedule()
        name = "WINTER Availability dftDaySched"
        self.assertEqual(default.nameString(), name)
        self.assertTrue(default.times())
        self.assertTrue(default.values())
        self.assertEqual(len(default.times()), 1)
        self.assertEqual(len(default.values()), 1)
        self.assertEqual(int(default.getValue(am01)), 1)
        self.assertEqual(int(default.getValue(pm11)), 1)

        self.assertTrue(sch.isWinterDesignDayScheduleDefaulted())
        self.assertTrue(sch.isSummerDesignDayScheduleDefaulted())
        self.assertTrue(sch.isHolidayScheduleDefaulted())
        if v >= 330: self.assertTrue(sch.isCustomDay1ScheduleDefaulted())
        if v >= 330: self.assertTrue(sch.isCustomDay2ScheduleDefaulted())
        self.assertEqual(sch.summerDesignDaySchedule(), default)
        self.assertEqual(sch.winterDesignDaySchedule(), default)
        self.assertEqual(sch.holidaySchedule(), default)
        if v >= 330: self.assertEqual(sch.customDay1Schedule(), default)
        if v >= 330: self.assertEqual(sch.customDay2Schedule(), default)
        self.assertEqual(len(sch.scheduleRules()), 1)

        for day_schedule in sch.getDaySchedules(jan01, apr30):
            self.assertTrue(day_schedule.times())
            self.assertTrue(day_schedule.values())
            self.assertEqual(len(day_schedule.times()), 1)
            self.assertEqual(len(day_schedule.values()), 1)
            self.assertEqual(int(day_schedule.getValue(am01)), 1)
            self.assertEqual(int(day_schedule.getValue(pm11)), 1)

        for day_schedule in sch.getDaySchedules(may01, oct31):
            self.assertTrue(day_schedule.times())
            self.assertTrue(day_schedule.values())
            self.assertEqual(len(day_schedule.times()), 1)
            self.assertEqual(len(day_schedule.values()), 1)
            self.assertEqual(int(day_schedule.getValue(am01)), 0)
            self.assertEqual(int(day_schedule.getValue(pm11)), 0)

        for day_schedule in sch.getDaySchedules(nov01, dec31):
            self.assertTrue(day_schedule.times())
            self.assertTrue(day_schedule.values())
            self.assertEqual(len(day_schedule.times()), 1)
            self.assertEqual(len(day_schedule.values()), 1)
            self.assertEqual(int(day_schedule.getValue(am01)), 1)
            self.assertEqual(int(day_schedule.getValue(pm11)), 1)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        another = osut.availabilitySchedule(model, "Winter")
        self.assertEqual(another.nameString(), sch.nameString())

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        sch = osut.availabilitySchedule(model, "Summer")
        self.assertTrue(isinstance(sch, openstudio.model.ScheduleRuleset))
        self.assertEqual(sch.nameString(), "SUMMER Availability SchedRuleset")

        limits = sch.scheduleTypeLimits()
        self.assertTrue(limits)
        limits = limits.get()
        name = "HVAC Operation ScheduleTypeLimits"
        self.assertEqual(limits.nameString(), name)

        default = sch.defaultDaySchedule()
        name = "SUMMER Availability dftDaySched"
        self.assertEqual(default.nameString(), name)
        self.assertTrue(default.times())
        self.assertTrue(default.values())
        self.assertEqual(len(default.times()), 1)
        self.assertEqual(len(default.values()), 1)
        self.assertEqual(int(default.getValue(am01)), 0)
        self.assertEqual(int(default.getValue(pm11)), 0)

        self.assertTrue(sch.isWinterDesignDayScheduleDefaulted())
        self.assertTrue(sch.isSummerDesignDayScheduleDefaulted())
        self.assertTrue(sch.isHolidayScheduleDefaulted())
        if v >= 330: self.assertTrue(sch.isCustomDay1ScheduleDefaulted())
        if v >= 330: self.assertTrue(sch.isCustomDay2ScheduleDefaulted())
        self.assertEqual(sch.summerDesignDaySchedule(), default)
        self.assertEqual(sch.winterDesignDaySchedule(), default)
        self.assertEqual(sch.holidaySchedule(), default)
        if v >= 330: self.assertEqual(sch.customDay1Schedule(), default)
        if v >= 330: self.assertEqual(sch.customDay2Schedule(), default)
        self.assertEqual(len(sch.scheduleRules()), 1)

        for day_schedule in sch.getDaySchedules(jan01, apr30):
            self.assertTrue(day_schedule.times())
            self.assertTrue(day_schedule.values())
            self.assertEqual(len(day_schedule.times()), 1)
            self.assertEqual(len(day_schedule.values()), 1)
            self.assertEqual(int(day_schedule.getValue(am01)), 0)
            self.assertEqual(int(day_schedule.getValue(pm11)), 0)

        for day_schedule in sch.getDaySchedules(may01, oct31):
            self.assertTrue(day_schedule.times())
            self.assertTrue(day_schedule.values())
            self.assertEqual(len(day_schedule.times()), 1)
            self.assertEqual(len(day_schedule.values()), 1)
            self.assertEqual(int(day_schedule.getValue(am01)), 1)
            self.assertEqual(int(day_schedule.getValue(pm11)), 1)

        for day_schedule in sch.getDaySchedules(nov01, dec31):
            self.assertTrue(day_schedule.times())
            self.assertTrue(day_schedule.values())
            self.assertEqual(len(day_schedule.times()), 1)
            self.assertEqual(len(day_schedule.values()), 1)
            self.assertEqual(int(day_schedule.getValue(am01)), 0)
            self.assertEqual(int(day_schedule.getValue(pm11)), 0)

        del(model)

    def test22_model_transformation(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)
        translator = openstudio.osversion.VersionTranslator()

        # Successful test.
        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        for space in model.getSpaces():
            tr = osut.transforms(space)
            self.assertTrue(isinstance(tr, dict))
            self.assertTrue("t" in tr)
            self.assertTrue("r" in tr)
            self.assertTrue(isinstance(tr["t"], openstudio.Transformation))
            self.assertAlmostEqual(tr["r"], 0, places=2)

        # Invalid input test.
        self.assertEqual(o.status(), 0)
        m1 = "'group' NoneType? expecting PlanarSurfaceGroup (osut.transforms)"
        tr = osut.transforms(None)
        self.assertTrue(isinstance(tr, dict))
        self.assertTrue("t" in tr)
        self.assertTrue("r" in tr)
        self.assertFalse(tr["t"])
        self.assertFalse(tr["r"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m1)
        self.assertEqual(o.clean(), DBG)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Realignment of flat surfaces.
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d(  1,  4,  0))
        vtx.append(openstudio.Point3d(  2,  2,  0))
        vtx.append(openstudio.Point3d(  6,  4,  0))
        vtx.append(openstudio.Point3d(  5,  6,  0))

        origin  = vtx[1]
        hyp     = (origin - vtx[0]).length()
        hyp2    = (origin - vtx[2]).length()
        right   = openstudio.Point3d(origin.x()+10, origin.y(), origin.z()   )
        zenith  = openstudio.Point3d(origin.x(),    origin.y(), origin.z()+10)
        seg     = vtx[2] - origin
        axis    = zenith - origin
        droite  = right  - origin
        radians = openstudio.getAngle(droite, seg)
        degrees = openstudio.radToDeg(radians)
        self.assertAlmostEqual(degrees, 26.565, places=3)

        r = openstudio.Transformation.rotation(origin, axis, radians)
        a = r.inverse() * vtx

        self.assertTrue(osut.areSame(a[1], vtx[1]))
        self.assertAlmostEqual(a[0].x() - a[1].x(), 0)
        self.assertAlmostEqual(a[2].x() - a[1].x(), hyp2)
        self.assertAlmostEqual(a[3].x() - a[2].x(), 0)
        self.assertAlmostEqual(a[0].y() - a[1].y(), hyp)
        self.assertAlmostEqual(a[2].y() - a[1].y(), 0)
        self.assertAlmostEqual(a[3].y() - a[1].y(), hyp)

        pts = r * a
        self.assertTrue(osut.areSame(pts, vtx))

        # ... to be completed later.

    def test23_fits_overlaps(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        v = int("".join(openstudio.openStudioVersion().split(".")))

        p1 = openstudio.Point3dVector()
        p2 = openstudio.Point3dVector()

        p1.append(openstudio.Point3d(3.63, 0, 4.03))
        p1.append(openstudio.Point3d(3.63, 0, 2.44))
        p1.append(openstudio.Point3d(7.34, 0, 2.44))
        p1.append(openstudio.Point3d(7.34, 0, 4.03))

        t = openstudio.Transformation.alignFace(p1)

        if v < 340:
            p2.append(openstudio.Point3d(3.63, 0, 2.49))
            p2.append(openstudio.Point3d(3.63, 0, 1.00))
            p2.append(openstudio.Point3d(7.34, 0, 1.00))
            p2.append(openstudio.Point3d(7.34, 0, 2.49))
        else:
            p2.append(openstudio.Point3d(3.63, 0, 2.47))
            p2.append(openstudio.Point3d(3.63, 0, 1.00))
            p2.append(openstudio.Point3d(7.34, 0, 1.00))
            p2.append(openstudio.Point3d(7.34, 0, 2.47))

        area1 = openstudio.getArea(p1)
        area2 = openstudio.getArea(p2)
        self.assertTrue(area1)
        self.assertTrue(area2)
        area1 = area1.get()
        area2 = area2.get()

        p1a = list(t.inverse() * p1)
        p2a = list(t.inverse() * p2)
        p1a.reverse()
        p2a.reverse()

        union = openstudio.join(p1a, p2a, TOL2)
        self.assertTrue(union)
        union = union.get()
        area  = openstudio.getArea(union)
        self.assertTrue(area)
        area  = area.get()
        delta = area1 + area2 - area

        res  = openstudio.intersect(p1a, p2a, TOL)
        self.assertTrue(res)
        res  = res.get()
        res1 = res.polygon1()
        self.assertTrue(res1)

        res1_m2 = openstudio.getArea(res1)
        self.assertTrue(res1_m2)
        res1_m2 = res1_m2.get()
        self.assertAlmostEqual(res1_m2, delta, places=2)
        self.assertTrue(osut.overlapping(p1a, p2a))
        self.assertEqual(o.status(), 0)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Tests line intersecting line segments.
        sg1 = openstudio.Point3dVector()
        sg1.append(openstudio.Point3d(18, 0, 0))
        sg1.append(openstudio.Point3d( 8, 3, 0))

        sg2 = openstudio.Point3dVector()
        sg2.append(openstudio.Point3d(12, 14, 0))
        sg2.append(openstudio.Point3d(12,  6, 0))

        self.assertFalse(osut.lineIntersection(sg1, sg2))

        sg1 = openstudio.Point3dVector()
        sg1.append(openstudio.Point3d(0.60,19.06, 0))
        sg1.append(openstudio.Point3d(0.60, 0.60, 0))
        sg1.append(openstudio.Point3d(0.00, 0.00, 0))
        sg1.append(openstudio.Point3d(0.00,19.66, 0))

        sg2 = openstudio.Point3dVector()
        sg2.append(openstudio.Point3d(9.83, 9.83, 0))
        sg2.append(openstudio.Point3d(0.00, 0.00, 0))
        sg2.append(openstudio.Point3d(0.00,19.66, 0))

        self.assertTrue(osut.areSame(sg1[2], sg2[1]))
        self.assertTrue(osut.areSame(sg1[3], sg2[2]))
        self.assertTrue(osut.fits(sg1, sg2))
        self.assertFalse(osut.fits(sg2, sg1))
        self.assertTrue(osut.areSame(osut.overlap(sg1, sg2), sg1))
        self.assertTrue(osut.areSame(osut.overlap(sg2, sg1), sg1))

        for i, pt in enumerate(sg1):
            self.assertTrue(osut.isPointWithinPolygon(pt, sg2))

        # Note: As of OpenStudio v340, the following method is available as an
        # all-in-one solution to check if a polygon fits within another polygon.
        #
        # answer = OpenStudio.polygonInPolygon(aligned_door, aligned_wall, TOL)
        #
        # As with other Boost-based methods, it requires 'aligned' surfaces
        # (using OpenStudio Transformation' alignFace method), and set in a
        # clockwise sequence. OSut sticks to fits? as it executes these steps
        # behind the scenes, and is consistent for pre-v340 implementations.
        model = openstudio.model.Model()

        # 10m x 10m parent vertical (wall) surface.
        vec = openstudio.Point3dVector()
        vec.append(openstudio.Point3d(  0,  0, 10))
        vec.append(openstudio.Point3d(  0,  0,  0))
        vec.append(openstudio.Point3d( 10,  0,  0))
        vec.append(openstudio.Point3d( 10,  0, 10))
        wall = openstudio.model.Surface(vec, model)

        # Side test: point alignment detection, 'w12' == wall/floor edge.
        w1  = vec[1]
        w2  = vec[2]
        w12 = w2 - w1

        # Side test: same?
        vec2 = list(osut.p3Dv(vec))
        self.assertNotEqual(vec, vec2)
        self.assertTrue(osut.areSame(vec, vec2))

        vec2 = collections.deque(vec2)
        vec2.rotate(-2)
        vec2 = list(vec2)
        self.assertTrue(osut.areSame(vec, vec2))
        self.assertFalse(osut.areSame(vec, vec2, False))

        # 1m x 2m corner door (with 2x edges along wall edges), 4mm sill.
        vec = openstudio.Point3dVector()
        vec.append(openstudio.Point3d(  0.5,  0,  2.000))
        vec.append(openstudio.Point3d(  0.5,  0,  0.004))
        vec.append(openstudio.Point3d(  1.5,  0,  0.004))
        vec.append(openstudio.Point3d(  1.5,  0,  2.000))
        door1 = openstudio.model.SubSurface(vec, model)

        # Side test: point alignment detection:
        # 'd1_w1': vector from door sill to wall corner 1 ( 0,0,0)
        # 'd1_w2': vector from door sill to wall corner 1 (10,0,0)
        d1 = vec[1]
        d2 = vec[2]
        d1_w1 = w1 - d1
        d1_w2 = w2 - d1
        self.assertTrue(osut.isPointAlongSegments(d1, [w1, w2]))

        # Order of arguments matter.
        self.assertTrue(osut.fits(door1, wall))
        self.assertTrue(osut.overlapping(door1, wall))
        self.assertFalse(osut.fits(wall, door1))
        self.assertTrue(osut.overlapping(wall, door1))

        # The method 'fits' offers an optional 3rd argument: whether a smaller
        # polygon (e.g. door1) needs to 'entirely' fit within the larger
        # polygon. Here, door1 shares its sill with the host wall (as its
        # within 10mm of the wall bottom edge).
        self.assertFalse(osut.fits(door1, wall, True))

        # Another 1m x 2m corner door, yet entirely beyond the wall surface.
        vec = openstudio.Point3dVector()
        vec.append(openstudio.Point3d( 16,  0,  2))
        vec.append(openstudio.Point3d( 16,  0,  0))
        vec.append(openstudio.Point3d( 17,  0,  0))
        vec.append(openstudio.Point3d( 17,  0,  2))
        door2 = openstudio.model.SubSurface(vec, model)

        # Door2 fits?, overlaps? Order of arguments doesn't matter.
        self.assertFalse(osut.fits(door2, wall))
        self.assertFalse(osut.overlapping(door2, wall))
        self.assertFalse(osut.fits(wall, door2))
        self.assertFalse(osut.overlapping(wall, door2))

        # Top-right corner 2m x 2m window, overlapping top-right corner of wall.
        vec = openstudio.Point3dVector()
        vec.append(openstudio.Point3d(  9,  0, 11))
        vec.append(openstudio.Point3d(  9,  0,  9))
        vec.append(openstudio.Point3d( 11,  0,  9))
        vec.append(openstudio.Point3d( 11,  0, 11))
        window = openstudio.model.SubSurface(vec, model)

        # Window fits?, overlaps?
        self.assertFalse(osut.fits(window, wall))
        olap = osut.overlap(window, wall)
        self.assertEqual(len(olap), 4)
        self.assertTrue(osut.fits(olap, wall))
        self.assertTrue(osut.overlapping(window, wall))
        self.assertFalse(osut.fits(wall, window))
        self.assertTrue(osut.overlapping(wall, window))

        # A glazed surface, entirely encompassing the wall.
        vec = openstudio.Point3dVector()
        vec.append(openstudio.Point3d(  0,  0, 10))
        vec.append(openstudio.Point3d(  0,  0,  0))
        vec.append(openstudio.Point3d( 10,  0,  0))
        vec.append(openstudio.Point3d( 10,  0, 10))
        glazing = openstudio.model.SubSurface(vec, model)

        # Glazing fits?, overlaps? parallel?
        self.assertTrue(osut.areParallel(glazing, wall))
        self.assertTrue(osut.fits(glazing, wall))
        self.assertTrue(osut.overlapping(glazing, wall))
        self.assertTrue(osut.areParallel(wall, glazing))
        self.assertTrue(osut.fits(wall, glazing))
        self.assertTrue(osut.overlapping(wall, glazing))

        del(model)
        self.assertEqual(o.clean(), DBG)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Checks overlaps when 2 surfaces don't share the same plane equation.
        translator = openstudio.osversion.VersionTranslator()

        path  = openstudio.path("./tests/files/osms/in/smalloffice.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        ceiling = model.getSurfaceByName("Core_ZN_ceiling")
        floor   = model.getSurfaceByName("Attic_floor_core")
        roof    = model.getSurfaceByName("Attic_roof_east")
        soffit  = model.getSurfaceByName("Attic_soffit_east")
        south   = model.getSurfaceByName("Attic_roof_south")
        self.assertTrue(ceiling)
        self.assertTrue(floor)
        self.assertTrue(roof)
        self.assertTrue(soffit)
        self.assertTrue(south)
        ceiling = ceiling.get()
        floor   = floor.get()
        roof    = roof.get()
        soffit  = soffit.get()
        south   = south.get()

        # Side test: triad, medial and bounded boxes.
        # pts   = mod1.getNonCollinears(ceiling.vertices, 3)
        # box01 = mod1.triadBox(pts)
        # box11 = mod1.boundedBox(ceiling)
        # self.asserTrue(mod1.areSame(box01, box11)
        # self.asserTrue(mod1.fits(box01, ceiling)

        del(model)
        self.assertEqual(o.clean(), DBG)

    def test24_triangulation(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        holes = openstudio.Point3dVectorVector()

        # Regular polygon, counterclockwise yet not UpperLeftCorner (ULC).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d(20, 0, 10))
        vtx.append(openstudio.Point3d( 0, 0, 10))
        vtx.append(openstudio.Point3d( 0, 0,  0))

        # Polygons must be 'aligned', and in a clockwise sequence.
        t = openstudio.Transformation.alignFace(vtx)
        a_vtx = list(t.inverse() * vtx)
        a_vtx.reverse()
        results = openstudio.computeTriangulation(a_vtx, holes)
        self.assertEqual(len(results), 1)
        # vtx0 = list(results[0])
        # vtx0.reverse()
        # for vt0 in vtx0: print(vt0) # == initial triangle, yet flat.
        # [20, 10, 0]
        # [ 0, 10, 0]
        # [ 0,  0, 0]

        vtx.append(openstudio.Point3d(20, 0,  0))
        t = openstudio.Transformation.alignFace(vtx)
        a_vtx = list(t.inverse() * vtx)
        a_vtx.reverse()
        results = openstudio.computeTriangulation(a_vtx, holes)
        self.assertEqual(len(results), 2)
        # for vt0 in list(results[0]): print(vt0)
        # [ 0, 10, 0]
        # [20, 10, 0]
        # [20,  0, 0]
        # for vt1 in list(results[1]): print(vt1)
        # [ 0,  0, 0]
        # [ 0, 10, 0]
        # [20,  0, 0]

    def test25_segments_triads_orientation(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        # Enclosed polygon.
        p0 = openstudio.Point3d(-5, -5, -5)
        p1 = openstudio.Point3d( 5,  5, -5)
        p2 = openstudio.Point3d(15, 15, -5)
        p3 = openstudio.Point3d(15, 25, -5)

        # Independent line segment.
        p4 = openstudio.Point3d(10,-30, -5)
        p5 = openstudio.Point3d(10, 10, -5)
        p6 = openstudio.Point3d(10, 40, -5)

        # Independent points.
        p7 = openstudio.Point3d(14, 20, -5)
        p8 = openstudio.Point3d(-9, -9, -5)

        # Stress tests.
        m1 = "Invalid '+n collinears' (osut.collinears)"
        m2 = "Invalid '-n collinears' (osut.collinears)"

        collinears = osut.collinears([p0, p1, p3, p8])
        self.assertEqual(len(collinears), 1)
        self.assertTrue(osut.areSame(collinears[0], p0))

        collinears = osut.collinears([p0, p1, p2, p3, p8])
        self.assertEqual(len(collinears), 2)
        self.assertTrue(osut.areSame(collinears[0], p0))
        self.assertTrue(osut.areSame(collinears[1], p1))

        collinears = osut.collinears([p0, p1, p2, p3, p8], 3)
        self.assertEqual(len(collinears), 2)
        self.assertTrue(osut.areSame(collinears[0], p0))
        self.assertTrue(osut.areSame(collinears[1], p1))

        collinears = osut.collinears([p0, p1, p2, p3, p8], 1)
        self.assertEqual(len(collinears), 1)
        self.assertTrue(osut.areSame(collinears[0], p0))

        collinears = osut.collinears([p0, p1, p2, p3, p8], -1)
        self.assertEqual(len(collinears), 1)
        self.assertTrue(osut.areSame(collinears[0], p1))

        collinears = osut.collinears([p0, p1, p2, p3, p8], -2)
        self.assertEqual(len(collinears), 2)
        self.assertTrue(osut.areSame(collinears[0], p0))
        self.assertTrue(osut.areSame(collinears[1], p1))

        collinears = osut.collinears([p0, p1, p2, p3, p8], 6)
        self.assertTrue(o.is_error())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m1)
        self.assertEqual(o.clean(), DBG)

        collinears = osut.collinears([p0, p1, p2, p3, p8], -6)
        self.assertTrue(o.is_error())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m2)
        self.assertEqual(o.clean(), DBG)

        # CASE a1: 2x end-to-end line segments (returns matching endpoints).
        self.assertTrue(osut.doesLineIntersect([p0, p1], [p1, p2]))
        pt = osut.lineIntersection([p0, p1], [p1, p2])
        self.assertTrue(osut.areSame(pt, p1))
        #
        # # CASE a2: as a1, sequence of line segment endpoints doesn't matter.
        self.assertTrue(osut.doesLineIntersect([p1, p0], [p1, p2]))
        pt = osut.lineIntersection([p1, p0], [p1, p2])
        self.assertTrue(osut.areSame(pt, p1))
        #
        # # CASE b1: 2x right-angle line segments, with 1x matching at corner.
        self.assertTrue(osut.doesLineIntersect([p1, p2], [p1, p3]))
        pt = osut.lineIntersection([p1, p2], [p2, p3])
        self.assertTrue(osut.areSame(pt, p2))
        #
        # # CASE b2: as b1, sequence of segments doesn't matter.
        self.assertTrue(osut.doesLineIntersect([p2, p3], [p1, p2]))
        pt = osut.lineIntersection([p2, p3], [p1, p2])
        self.assertTrue(osut.areSame(pt, p2))

        # CASE c: 2x right-angle line segments, yet disconnected.
        self.assertFalse(osut.doesLineIntersect([p0, p1], [p2, p3]))
        pt = osut.lineIntersection([p0, p1], [p2, p3])
        self.assertFalse(pt)

        # CASE d: 2x connected line segments, acute angle.
        self.assertTrue(osut.doesLineIntersect([p0, p2], [p3, p0]))
        pt = osut.lineIntersection([p0, p2], [p3, p0])
        self.assertTrue(osut.areSame(pt, p0))
        #
        # # CASE e1: 2x disconnected line segments, right angle.
        self.assertTrue(osut.doesLineIntersect([p0, p2], [p4, p6]))
        pt = osut.lineIntersection([p0, p2], [p4, p6])
        self.assertTrue(osut.areSame(pt, p5))
        #
        # # CASE e2: as e1, sequence of line segment endpoints doesn't matter.
        self.assertTrue(osut.doesLineIntersect([p0, p2], [p6, p4]))
        pt = osut.lineIntersection([p0, p2], [p6, p4])
        self.assertTrue(osut.areSame(pt, p5))

    def test26_ulc_blc(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Regular polygon, counterclockwise yet not UpperLeftCorner (ULC).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d(20, 0, 10))
        vtx.append(openstudio.Point3d( 0, 0, 10))
        vtx.append(openstudio.Point3d( 0, 0,  0))
        vtx.append(openstudio.Point3d(20, 0,  0))

        t = openstudio.Transformation.alignFace(vtx)
        a_vtx = t.inverse() * vtx

        # 1. Native ULC reordering.
        ulc_a_vtx = openstudio.reorderULC(a_vtx)
        ulc_vtx = t * ulc_a_vtx
        # for vt in ulc_vtx: print(vt)
        # [20, 0,  0]
        # [20, 0, 10]
        # [ 0, 0, 10]
        # [ 0, 0,  0]
        self.assertAlmostEqual(ulc_vtx[3].x(), 0, places=2)
        self.assertAlmostEqual(ulc_vtx[3].y(), 0, places=2)
        self.assertAlmostEqual(ulc_vtx[3].z(), 0, places=2)
        # ... counterclockwise, yet ULC?

        # 2. OSut ULC reordering.
        ulc_a_vtx = osut.ulc(a_vtx)
        blc_a_vtx = osut.blc(a_vtx)
        ulc_vtx   = t * ulc_a_vtx
        blc_vtx   = t * blc_a_vtx
        self.assertAlmostEqual(ulc_vtx[1].x(), 0, places=2)
        self.assertAlmostEqual(ulc_vtx[1].y(), 0, places=2)
        self.assertAlmostEqual(ulc_vtx[1].z(), 0, places=2)
        self.assertAlmostEqual(blc_vtx[0].x(), 0, places=2)
        self.assertAlmostEqual(blc_vtx[0].y(), 0, places=2)
        self.assertAlmostEqual(blc_vtx[0].z(), 0, places=2)
        # for vt in ulc_vtx: print(vt)
        # [ 0, 0, 10]
        # [ 0, 0,  0]
        # [20, 0,  0]
        # [20, 0, 10]
        # for vt in blc_vtx: print(vt)
        # [ 0, 0,  0]
        # [20, 0,  0]
        # [20, 0, 10]
        # [ 0, 0, 10]

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Same, yet (0,0,0) is at index == 0.
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 0, 0,  0))
        vtx.append(openstudio.Point3d(20, 0,  0))
        vtx.append(openstudio.Point3d(20, 0, 10))
        vtx.append(openstudio.Point3d( 0, 0, 10))

        t = openstudio.Transformation.alignFace(vtx)
        a_vtx = t.inverse() * vtx

        # 1. Native ULC reordering.
        ulc_a_vtx = openstudio.reorderULC(a_vtx)
        ulc_vtx   = t * ulc_a_vtx
        # for vt in ulc_vtx: print(vt)
        # [20, 0,  0]
        # [20, 0, 10]
        # [ 0, 0, 10]
        # [ 0, 0,  0] # ... consistent with first case.

        # 2. OSut ULC reordering.
        ulc_a_vtx = osut.ulc(a_vtx)
        blc_a_vtx = osut.blc(a_vtx)
        ulc_vtx   = t * ulc_a_vtx
        blc_vtx   = t * blc_a_vtx
        self.assertAlmostEqual(ulc_vtx[1].x(), 0, places=2)
        self.assertAlmostEqual(ulc_vtx[1].y(), 0, places=2)
        self.assertAlmostEqual(ulc_vtx[1].z(), 0, places=2)
        self.assertAlmostEqual(blc_vtx[0].x(), 0, places=2)
        self.assertAlmostEqual(blc_vtx[0].y(), 0, places=2)
        self.assertAlmostEqual(blc_vtx[0].z(), 0, places=2)
        # for vt in ulc_vtx: print(vt)
        # [ 0, 0, 10]
        # [ 0, 0,  0]
        # [20, 0,  0]
        # [20, 0, 10]
        # for vt in blc_vtx: print(vt)
        # [ 0, 0,  0]
        # [20, 0,  0]
        # [20, 0, 10]
        # [ 0, 0, 10]

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Irregular polygon, no point at 0,0,0.
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d(18, 0, 10))
        vtx.append(openstudio.Point3d( 2, 0, 10))
        vtx.append(openstudio.Point3d( 0, 0,  6))
        vtx.append(openstudio.Point3d( 0, 0,  4))
        vtx.append(openstudio.Point3d( 2, 0,  0))
        vtx.append(openstudio.Point3d(18, 0,  0))
        vtx.append(openstudio.Point3d(20, 0,  4))
        vtx.append(openstudio.Point3d(20, 0,  6))

        t = openstudio.Transformation.alignFace(vtx)
        a_vtx = t.inverse() * vtx

        # 1. Native ULC reordering.
        ulc_a_vtx = openstudio.reorderULC(a_vtx)
        ulc_vtx   = t * ulc_a_vtx
        # for vt in ulc_vtx: print(vt)
        # [18, 0,  0]
        # [20, 0,  4]
        # [20, 0,  6]
        # [18, 0, 10]
        # [ 2, 0, 10]
        # [ 0, 0,  6]
        # [ 0, 0,  4]
        # [ 2, 0,  0] ... consistent pattern with previous cases, yet ULC?

        # 2. OSut ULC reordering.
        ulc_a_vtx = osut.ulc(a_vtx)
        blc_a_vtx = osut.blc(a_vtx)
        iN = osut.nearest(ulc_a_vtx)
        iF = osut.farthest(ulc_a_vtx)
        self.assertEqual(iN, 2)
        self.assertEqual(iF, 6)
        ulc_vtx   = t * ulc_a_vtx
        blc_vtx   = t * blc_a_vtx
        self.assertTrue(osut.areSame(ulc_vtx[2], ulc_vtx[iN]))
        self.assertTrue(osut.areSame(blc_vtx[1], ulc_vtx[iN]))
        # for vt in ulc_vtx: print(vt)
        # [ 0, 0,  6]
        # [ 0, 0,  4]
        # [ 2, 0,  0]
        # [18, 0,  0]
        # [20, 0,  4]
        # [20, 0,  6]
        # [18, 0, 10]
        # [ 2, 0, 10]
        # for vt in blc_vtx: print(vt)
        # [ 0, 0,  4]
        # [ 2, 0,  0]
        # [18, 0,  0]
        # [20, 0,  4]
        # [20, 0,  6]
        # [18, 0, 10]
        # [ 2, 0, 10]
        # [ 0, 0,  6]

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d(70, 45,  0))
        vtx.append(openstudio.Point3d( 0, 45,  0))
        vtx.append(openstudio.Point3d( 0,  0,  0))
        vtx.append(openstudio.Point3d(70,  0,  0))

        ulc_vtx = osut.ulc(vtx)
        blc_vtx = osut.blc(vtx)
        self.assertEqual(o.status(), 0)
        # for vt in ulc_vtx: print(vt)
        # [ 0, 45, 0]
        # [ 0,  0, 0]
        # [70,  0, 0]
        # [70, 45, 0]
        # for vt in blc_vtx: print(vt)
        # [ 0,  0, 0]
        # [70,  0, 0]
        # [70, 45, 0]
        # [ 0, 45, 0]

    # def test27_polygon_attributes(self):

    # def test28_subsurface_insertions(self):

    # def test29_surface_width_height(self):

    # def test30_wwr_insertions(self):

    # def test31_convexity(self):

    # def test32_outdoor_roofs(self):

    # def test33_leader_line_anchors_inserts(self):

    # def test34_generated_skylight_wells(self):

    def test35_facet_retrieval(self):
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
        surfs  = model.getSurfaces()
        subs   = model.getSubSurfaces()
        self.assertEqual(len(surfs), 56)
        self.assertEqual(len(subs), 8)

        # The solution is similar to:
        #   OpenStudio::Model::Space::findSurfaces(minDegreesFromNorth,
        #                                          maxDegreesFromNorth,
        #                                          minDegreesTilt,
        #                                          maxDegreesTilt,
        #                                          tol)
        #   https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/
        #   OpenStudio-3.6.1-doc/model/html/classopenstudio_1_1model_1_1_space.html
        #   #a0cf3c265ac314c1c846ee4962e852a3e
        #
        # ... yet it offers filters, e.g. surface type and boundary conditions.
        windows    = osut.facets(spaces, "Outdoors", "FixedWindow")
        skylights  = osut.facets(spaces, "Outdoors", "Skylight")
        walls      = osut.facets(spaces, "Outdoors", "Wall")
        northsouth = osut.facets(spaces, "Outdoors", "Wall", ["north", "south"])
        northeast  = osut.facets(spaces, "Outdoors", "Wall", ["north", "east"])
        north      = osut.facets(spaces, "Outdoors", "Wall", "north")
        floors1a   = osut.facets(spaces, "Ground", "Floor", "bottom")
        floors1b   = osut.facets(spaces, "Surface", "Floor") # plenum
        roofs1     = osut.facets(spaces, "Outdoors", "RoofCeiling", "top")
        roofs2     = osut.facets(spaces, "Outdoors", "RoofCeiling", "foo")

        self.assertEqual(len(windows), 8)
        self.assertEqual(len(skylights), 0)
        self.assertEqual(len(walls), 26)
        self.assertFalse(northsouth)
        self.assertEqual(len(northeast), 8)
        self.assertEqual(len(north), 14)
        self.assertEqual(len(floors1a), 4)
        self.assertEqual(len(floors1b), 4)
        self.assertEqual(len(roofs1), 4)
        self.assertFalse(roofs2)

        # Concise variants, same output. In the SEB model, floors face "Ground".
        floors2 = osut.facets(spaces, "Ground", "Floor")
        floors3 = osut.facets(spaces, "Ground")
        roofs3  = osut.facets(spaces, "Outdoors", "RoofCeiling")
        self.assertEqual(floors2, floors1a)
        self.assertEqual(floors3, floors1a)
        self.assertEqual(roofs3, roofs1)

        # Dropping filters, 'envelope' includes all above-grade envelope.
        nb       = len(walls) + len(roofs3) + len(windows) + len(skylights)
        floors4  = osut.facets(spaces, "ALL", "Floor")
        envelope = osut.facets(spaces, "Outdoors", "ALL")

        for fl in floors1a: self.assertTrue(fl in floors4)
        for fl in floors1b: self.assertTrue(fl in floors4)
        self.assertEqual(len(envelope), nb)

        # Without arguments, the method returns ALL surfaces and subsurfaces.
        self.assertEqual(len(osut.facets(spaces)), len(surfs) + len(subs))

        del(model)

    def test36_slab_generation(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)
        model = openstudio.model.Model()

        x0 = 1
        y0 = 2
        z0 = 3
        w1 = 4
        w2 = w1 * 2
        d1 = 5
        d2 = d1 * 2

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # 1x valid 'floor' plate.
        #        ____
        #       |    |
        #       |    |
        #       |  1 |
        #       |____|
        #
        plates = []
        plates.append(dict(x=x0, y=y0, dx=w1, dy=d2)) # bottom-left XY origin
        slab = osut.genSlab(plates, z0)
        self.assertEqual(o.status(), 0)
        self.assertTrue(isinstance(slab, openstudio.Point3dVector))
        self.assertEqual(len(slab), 4)

        surface = openstudio.model.Surface(slab, model)
        self.assertTrue(isinstance(surface, openstudio.model.Surface))
        self.assertEqual(len(surface.vertices()), 4)
        self.assertAlmostEqual(surface.grossArea(),        2 * 20, places=2)
        self.assertAlmostEqual(surface.vertices()[0].x(), x0 + w1, places=2)
        self.assertAlmostEqual(surface.vertices()[0].y(), y0 + d2, places=2)
        self.assertAlmostEqual(surface.vertices()[0].z(),      z0, places=2)
        self.assertAlmostEqual(surface.vertices()[2].x(),      x0, places=2)
        self.assertAlmostEqual(surface.vertices()[2].y(),      y0, places=2)
        self.assertAlmostEqual(surface.vertices()[2].z(),      z0, places=2)
        self.assertAlmostEqual(surface.vertices()[3].x(),      x0, places=2)
        self.assertAlmostEqual(surface.vertices()[3].y(), y0 + d2, places=2)
        self.assertAlmostEqual(surface.vertices()[3].z(),      z0, places=2)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # 2x valid 'floor' plates.
        #        ____ ____
        #       |    |  2 |
        #       |    |____|
        #       |  1 |
        #       |____|
        #
        plates = []
        plates.append(dict(x=x0,    y=y0,    dx=w1, dy=d2))
        plates.append(dict(x=x0+w1, y=y0+d1, dx=w1, dy=d1))

        slab = osut.genSlab(plates, z0)
        self.assertEqual(o.status(), 0)
        self.assertTrue(isinstance(slab, openstudio.Point3dVector))
        self.assertEqual(len(slab), 6)

        surface = openstudio.model.Surface(slab, model)
        self.assertTrue(isinstance(surface, openstudio.model.Surface))
        self.assertEqual(len(surface.vertices()), 6)
        self.assertAlmostEqual(surface.grossArea(), 3 * 20, places=2)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # 3x valid 'floor' plates.
        #        ____ ____
        #       |    |  2 |
        #   ____|    |____|
        #  |   3|  1 |
        #  |____|____|
        #
        plates = []
        plates.append(dict(x=x0,    y=y0,    dx=w1, dy=d2))
        plates.append(dict(x=x0+w1, y=y0+d1, dx=w1, dy=d1))
        plates.append(dict(x=x0-w1, y=y0,    dx=w1, dy=d1)) # X origin < 0

        slab = osut.genSlab(plates, z0)
        self.assertEqual(o.status(), 0)
        self.assertTrue(isinstance(slab, openstudio.Point3dVector))
        self.assertEqual(len(slab), 8)

        surface = openstudio.model.Surface(slab, model)
        self.assertTrue(isinstance(surface, openstudio.model.Surface))
        self.assertEqual(len(surface.vertices()), 8)
        self.assertAlmostEqual(surface.grossArea(), 4 * 20, places=2)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # 3x 'floor' plates + 1x unconnected 'plate'.
        #        ____ ____   ____
        #       |    |  2 | |  4 |
        #   ____|    |____| |____|
        #  |   3|  1 |
        #  |____|____|
        #
        plates = []
        plates.append(dict(x=x0,      y=y0,    dx=w1, dy=d2)) # index 0, #1
        plates.append(dict(x=x0+w1,   y=y0+d1, dx=w1, dy=d1)) # index 1, #2
        plates.append(dict(x=x0-w1,   y=y0,    dx=w1, dy=d1)) # index 2, #3
        plates.append(dict(x=x0+w2+1, y=y0+d1, dx=w1, dy=d1)) # index 3, #4

        slab = osut.genSlab(plates, z0)
        self.assertTrue(o.is_error())
        msg = o.logs()[0]["message"]
        self.assertEqual(msg, "Invalid 'plate # 4 (index 3)' (osut.genSlab)")
        self.assertEqual(o.clean(), DBG)
        self.assertTrue(isinstance(slab, openstudio.Point3dVector))
        self.assertFalse(slab)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # 3x 'floor' plates + 1x overlapping 'plate'.
        #        ____ ____
        #       |    |  2 |__
        #   ____|    |____| 4|
        #  |   3|  1 |  |____|
        #  |____|____|
        #
        plates = []
        plates.append(dict(x=x0,      y=y0,    dx=w1, dy=d2))
        plates.append(dict(x=x0+w1,   y=y0+d1, dx=w1, dy=d1))
        plates.append(dict(x=x0-w1,   y=y0,    dx=w1, dy=d1))
        plates.append(dict(x=x0+w2-1, y=y0+1,  dx=w1, dy=d1))

        slab = osut.genSlab(plates, z0)
        self.assertEqual(o.status(), 0)
        self.assertTrue(isinstance(slab, openstudio.Point3dVector))
        self.assertEqual(len(slab), 12)

        surface = openstudio.model.Surface(slab, model)
        self.assertTrue(isinstance(surface, openstudio.model.Surface))
        self.assertEqual(len(surface.vertices()), 12)
        self.assertAlmostEqual(surface.grossArea(), 5 * 20 - 1, places=2)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Same as previous, yet overlapping 'plate' has a negative dX while X
        # origin is set at right (not left) corner.
        #        ____ ____
        #       |    |  2 |__
        #   ____|    |____| 4|
        #  |   3|  1 |  |____|
        #  |____|____|
        #
        plates = []
        plates.append(dict(x=x0,        y=y0,    dx= w1, dy=d2))
        plates.append(dict(x=x0+w1,     y=y0+d1, dx= w1, dy=d1))
        plates.append(dict(x=x0-w1,     y=y0,    dx= w1, dy=d1))
        plates.append(dict(x=x0+3*w1-1, y=y0+1,  dx=-w1, dy=d1))

        slab = osut.genSlab(plates, z0)
        self.assertEqual(o.status(), 0)
        self.assertTrue(isinstance(slab, openstudio.Point3dVector))
        self.assertEqual(len(slab), 12)

        surface = openstudio.model.Surface(slab, model)
        self.assertTrue(isinstance(surface, openstudio.model.Surface))
        self.assertEqual(len(surface.vertices()), 12)
        self.assertAlmostEqual(surface.grossArea(), 5 * 20 - 1, places=2)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Same as previous, yet overlapping 'plate' has both negative dX & dY,
        # while XY origin is set at top-right (not bottom-left) corner.
        #        ____ ____
        #       |    |  2 |__
        #   ____|    |____| 4|
        #  |   3|  1 |  |____|
        #  |____|____|
        #
        plates = []
        plates.append(dict(x=x0,        y=y0,      dx= w1, dy= d2))
        plates.append(dict(x=x0+w1,     y=y0+d1,   dx= w1, dy= d1))
        plates.append(dict(x=x0-w1,     y=y0,      dx= w1, dy= d1))
        plates.append(dict(x=x0+3*w1-1, y=y0+1+d1, dx=-w1, dy=-d1))

        slab = osut.genSlab(plates, z0)
        self.assertEqual(o.status(), 0)
        self.assertTrue(isinstance(slab, openstudio.Point3dVector))
        self.assertEqual(len(slab), 12)

        surface = openstudio.model.Surface(slab, model)
        self.assertTrue(isinstance(surface, openstudio.model.Surface))
        self.assertEqual(len(surface.vertices()), 12)
        self.assertAlmostEqual(surface.grossArea(), 5 * 20 - 1, places=2)

        self.assertEqual(o.status(), 0)
        del(model)

    # def test37_roller_shades(self):

if __name__ == "__main__":
    unittest.main()
