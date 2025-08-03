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
HEAD = osut.CN.HEAD
SILL = osut.CN.SILL

class TestOSutModuleMethods(unittest.TestCase):
    def test00_oslg_constants(self):
        self.assertEqual(DBG, 1)

    def test01_osm_instantiation(self):
        model = openstudio.model.Model()
        self.assertTrue(isinstance(model, openstudio.model.Model))
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

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
        del model

    def test06_internal_mass(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

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

        del model

    def test07_construction_thickness(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.level(), DBG)

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

            c   = c.to_LayeredConstruction().get()
            ide = c.nameString()

            # OSut 'thickness' method can only process layered constructions
            # built up with standard opaque layers, which exclude:
            #
            #   - "Air Wall"-based construction
            #   - "Double pane"-based construction
            #
            # The method returns '0' in such cases, logging ERROR messages.
            th = osut.thickness(c)

            if "Air Wall" in ide or "Double pane" in ide:
                self.assertAlmostEqual(th, 0.00, places=2)
                continue

            self.assertTrue(th > 0)

        self.assertTrue(o.is_error())
        self.assertEqual(o.clean(), DBG)
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())

        for c in model.getConstructions():
            if c.to_LayeredConstruction(): continue

            c   = c.to_LayeredConstruction().get()
            ide = c.nameString()
            if "Air Wall" in ide or "Double pane" in id: continue

            th = osut.thickness(c)
            self.assertTrue(th > 0)

        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())

        del model

    def test08_holds_constructions(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

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

        del model
        del mdl

    def test09_construction_set(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

        version = int("".join(openstudio.openStudioVersion().split(".")))
        translator = openstudio.osversion.VersionTranslator()

        m = "construction not defaulted (osut.defaultConstructionSet)"

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        path  = openstudio.path("./tests/files/osms/in/5ZoneNoHVAC.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        for s in model.getSurfaces():
            cset = osut.defaultConstructionSet(s)
            self.assertTrue(cset)
            self.assertEqual(o.status(), 0)

        del model

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        for s in model.getSurfaces():
            cset = osut.defaultConstructionSet(s)
            self.assertFalse(cset)
            self.assertTrue(o.is_warn())

            for l in o.logs(): self.assertEqual(l["message"], m)

        self.assertEqual(o.clean(), DBG)

        del model

    def test10_glazing_airfilms(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

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

        del model

    def test11_rsi(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

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

        del model

    def test12_insulating_layer(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

        version = int("".join(openstudio.openStudioVersion().split(".")))
        translator = openstudio.osversion.VersionTranslator()

        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        m0 = " expecting LayeredConstruction (osut.insulatingLayer)"

        for lc in model.getLayeredConstructions():
            ide = lc.nameString()
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

            if ide == "EXTERIOR-ROOF":
                self.assertEqual(lyr["index"], 2)
                self.assertAlmostEqual(lyr["r"], 5.08, places=2)
            elif ide == "EXTERIOR-WALL":
                self.assertEqual(lyr["index"], 2)
                self.assertAlmostEqual(lyr["r"], 1.47, places=2)
            elif ide == "Default interior ceiling":
                self.assertEqual(lyr["index"], 0)
                self.assertAlmostEqual(lyr["r"], 0.12, places=2)
            elif ide == "INTERIOR-WALL":
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

        del model

    def test13_spandrels(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

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

        del model

    def test14_schedule_ruleset_minmax(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

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

        del model

    def test15_schedule_constant_minmax(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

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

        del model

    def test16_schedule_compact_minmax(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

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

        del model

    def test17_minmax_heatcool_setpoints(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

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
        m1   = "'zone' NoneType? expecting ThermalZone (%s)" % mth1
        m2   = "'zone' NoneType? expecting ThermalZone (%s)" % mth2
        m3   = "'zone' str? expecting ThermalZone (%s)" % mth1
        m4   = "'zone' str? expecting ThermalZone (%s)" % mth2

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
        self.assertEqual(o.logs()[0]["message"], m1)
        self.assertEqual(o.clean(), DBG)

        res = osut.minCoolScheduledSetpoint(None) # bad argument
        self.assertTrue(isinstance(res, dict))
        self.assertTrue("spt" in res)
        self.assertTrue("dual" in res)
        self.assertFalse(res["spt"])
        self.assertFalse(res["dual"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m2)
        self.assertEqual(o.clean(), DBG)

        res = osut.maxHeatScheduledSetpoint("") # bad argument
        self.assertTrue(isinstance(res, dict))
        self.assertTrue("spt" in res)
        self.assertTrue("dual" in res)
        self.assertFalse(res["spt"])
        self.assertFalse(res["dual"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m3)
        self.assertEqual(o.clean(), DBG)

        res = osut.minCoolScheduledSetpoint("") # bad argument
        self.assertTrue(isinstance(res, dict))
        self.assertTrue("spt" in res)
        self.assertTrue("dual" in res)
        self.assertFalse(res["spt"])
        self.assertFalse(res["dual"])
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], m4)
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

        del model

    def test18_hvac_airloops(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        translator = openstudio.osversion.VersionTranslator()

        m = "'model' str? expecting Model (osut.hasAirLoopsHVAC)"

        version = int("".join(openstudio.openStudioVersion().split(".")))

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
        self.assertEqual(o.logs()[0]["message"], m)
        self.assertEqual(o.clean(), DBG)

        del model

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
        self.assertEqual(o.logs()[0]["message"], m)
        self.assertEqual(o.clean(), DBG)

        del model

    def test19_vestibules(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

        translator = openstudio.osversion.VersionTranslator()

        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        # Tag "Entry way 1" in SEB as a vestibule.
        tag   = "vestibule"
        m     = "Invalid 'vestibule' arg #1 (osut.areVestibules)"
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
        self.assertEqual(o.logs()[0]["message"], m)
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

        del model

    def test20_setpoints_plenums_attics(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

        cl1 = openstudio.model.Space
        cl2 = openstudio.model.Model
        mt1 = "(osut.arePlenums)"
        mt2 = "(osut.hasHeatingTemperatureSetpoints)"
        mt3 = "(osut.setpoints)"
        ms1 = "'spaces' NoneType? expecting list %s" % mt1
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

        del model

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

        del model

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
        m   = "Invalid '%s:%s' (osut.setpoints)" % (key, val)
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
        for l in o.logs(): self.assertEqual(l["message"], m)

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

        del model
        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Consider adding LargeOffice model to test SDK's "isPlenum" ... @todo

    def test21_availability_schedules(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

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

        del model

    def test22_model_transformation(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
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

        output1 = osut.realignedFace(vtx)
        self.assertEqual(o.status(), 0)
        self.assertTrue(isinstance(output1, dict))
        self.assertTrue("set" in output1)
        self.assertTrue("box" in output1)
        self.assertTrue("bbox" in output1)
        self.assertTrue("t" in output1)
        self.assertTrue("r" in output1)
        self.assertTrue("o" in output1)

        ubox1  = output1[ "box"]
        ubbox1 = output1["bbox"]

        # Realign a previously realigned surface?
        output2 = osut.realignedFace(ubox1)
        ubox2   = output1[ "box"]
        ubbox2  = output1["bbox"]

        # Realigning a previously realigned polygon has no effect (== safe).
        self.assertTrue(osut.areSame(ubox1, ubox2, False))
        self.assertTrue(osut.areSame(ubbox1, ubbox2, False))

        bounded_area  = openstudio.getArea(ubox1)
        bounding_area = openstudio.getArea(ubbox1)
        self.assertTrue(bounded_area)
        self.assertTrue(bounding_area)
        bounded_area  = bounded_area.get()
        bounding_area = bounding_area.get()
        self.assertAlmostEqual(bounded_area, bounding_area, places=2)

        bounded_area  = openstudio.getArea(ubox2)
        bounding_area = openstudio.getArea(ubbox2)
        self.assertTrue(bounded_area)
        self.assertTrue(bounding_area)
        bounded_area  = bounded_area.get()
        bounding_area = bounding_area.get()
        self.assertAlmostEqual(bounded_area, bounding_area, places=2)
        self.assertEqual(o.status(), 0)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Repeat with slight change in orientation.
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d(  2,  6,  0))
        vtx.append(openstudio.Point3d(  1,  4,  0))
        vtx.append(openstudio.Point3d(  5,  2,  0))
        vtx.append(openstudio.Point3d(  6,  4,  0))

        output3 = osut.realignedFace(vtx)
        ubox3   = output3[ "box"]
        ubbox3  = output3["bbox"]

        # Realign a previously realigned surface?
        output4 = osut.realignedFace(ubox3)
        ubox4   = output4[ "box"]
        ubbox4  = output4["bbox"]

        # Realigning a previously realigned polygon has no effect (== safe).
        self.assertTrue(osut.areSame(ubox1, ubox3, False))
        self.assertTrue(osut.areSame(ubbox1, ubbox3, False))
        self.assertTrue(osut.areSame(ubox1, ubox4, False))
        self.assertTrue(osut.areSame(ubbox1, ubbox4, False))

        bounded_area  = openstudio.getArea(ubox3)
        bounding_area = openstudio.getArea(ubbox3)
        self.assertTrue(bounded_area)
        self.assertTrue(bounding_area)
        bounded_area  = bounded_area.get()
        bounding_area = bounding_area.get()
        self.assertAlmostEqual(bounded_area, bounding_area, places=2)

        bounded_area  = openstudio.getArea(ubox4)
        bounding_area = openstudio.getArea(ubbox4)
        self.assertTrue(bounded_area)
        self.assertTrue(bounding_area)
        bounded_area  = bounded_area.get()
        bounding_area = bounding_area.get()
        self.assertAlmostEqual(bounded_area, bounding_area, places=2)
        self.assertEqual(o.status(), 0)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Repeat with changes in vertex sequence.
        # Repeat with slight change in orientation.
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d(  6,  4,  0))
        vtx.append(openstudio.Point3d(  5,  6,  0))
        vtx.append(openstudio.Point3d(  1,  4,  0))
        vtx.append(openstudio.Point3d(  2,  2,  0))

        output5 = osut.realignedFace(vtx)
        ubox5   = output5[ "box"]
        ubbox5  = output5["bbox"]

        # Realign a previously realigned surface?
        output6 = osut.realignedFace(ubox5)
        ubox6   = output6[ "box"]
        ubbox6  = output6["bbox"]

        # Realigning a previously realigned polygon has no effect (== safe).
        self.assertTrue(osut.areSame(ubox1, ubox5))
        self.assertTrue(osut.areSame(ubox1, ubox6))
        self.assertTrue(osut.areSame(ubbox1, ubbox5))
        self.assertTrue(osut.areSame(ubbox1, ubbox6))
        self.assertTrue(osut.areSame(ubox5, ubox6, False))
        self.assertTrue(osut.areSame(ubox5, ubbox5, False))
        self.assertTrue(osut.areSame(ubbox5, ubox6, False))
        self.assertTrue(osut.areSame(ubox6, ubbox6, False))

        bounded_area  = openstudio.getArea(ubox5)
        bounding_area = openstudio.getArea(ubbox5)
        self.assertTrue(bounded_area)
        self.assertTrue(bounding_area)
        bounded_area  = bounded_area.get()
        bounding_area = bounding_area.get()
        self.assertAlmostEqual(bounded_area, bounding_area, places=2)

        bounded_area  = openstudio.getArea(ubox6)
        bounding_area = openstudio.getArea(ubbox6)
        self.assertTrue(bounded_area)
        self.assertTrue(bounding_area)
        bounded_area  = bounded_area.get()
        bounding_area = bounding_area.get()
        self.assertAlmostEqual(bounded_area, bounding_area, places=2)
        self.assertEqual(o.status(), 0)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Repeat with slight change in orientation (vertices resequenced).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d(  5,  2,  0))
        vtx.append(openstudio.Point3d(  6,  4,  0))
        vtx.append(openstudio.Point3d(  2,  6,  0))
        vtx.append(openstudio.Point3d(  1,  4,  0))

        output7 = osut.realignedFace(vtx)
        ubox7   = output7[ "box"]
        ubbox7  = output7["bbox"]

        # Realign a previously realigned surface?
        output8 = osut.realignedFace(ubox7)
        ubox8   = output8[ "box"]
        ubbox8  = output8["bbox"]

        # Realigning a previously realigned polygon has no effect (== safe).
        self.assertTrue(osut.areSame(ubox1, ubox7))
        self.assertTrue(osut.areSame(ubox1, ubox8))
        self.assertTrue(osut.areSame(ubbox1, ubbox7))
        self.assertTrue(osut.areSame(ubbox1, ubbox8))
        self.assertTrue(osut.areSame(ubox5, ubox7, False))
        self.assertTrue(osut.areSame(ubbox5, ubbox7, False))
        self.assertTrue(osut.areSame(ubox5, ubox5, False))
        self.assertTrue(osut.areSame(ubbox5, ubbox8, False))

        bounded_area  = openstudio.getArea(ubox7)
        bounding_area = openstudio.getArea(ubbox7)
        self.assertTrue(bounded_area)
        self.assertTrue(bounding_area)
        bounded_area  = bounded_area.get()
        bounding_area = bounding_area.get()
        self.assertAlmostEqual(bounded_area, bounding_area, places=2)

        bounded_area  = openstudio.getArea(ubox8)
        bounding_area = openstudio.getArea(ubbox8)
        self.assertTrue(bounded_area)
        self.assertTrue(bounding_area)
        bounded_area  = bounded_area.get()
        bounding_area = bounding_area.get()
        self.assertAlmostEqual(bounded_area, bounding_area, places=2)
        self.assertEqual(o.status(), 0)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Aligned box (wide).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d(  2,  4,  0))
        vtx.append(openstudio.Point3d(  2,  2,  0))
        vtx.append(openstudio.Point3d(  6,  2,  0))
        vtx.append(openstudio.Point3d(  6,  4,  0))

        output9 = osut.realignedFace(vtx)
        ubox9   = output9[ "box"]
        ubbox9  = output9["bbox"]

        output10 = osut.realignedFace(vtx, True) # no impact
        ubox10   = output10[ "box"]
        ubbox10  = output10["bbox"]
        self.assertTrue(osut.areSame(ubox9, ubox10))
        self.assertTrue(osut.areSame(ubbox9, ubbox10))

        # ... vs aligned box (narrow).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d(  2,  6,  0))
        vtx.append(openstudio.Point3d(  2,  2,  0))
        vtx.append(openstudio.Point3d(  4,  2,  0))
        vtx.append(openstudio.Point3d(  4,  6,  0))

        output11 = osut.realignedFace(vtx)
        ubox11   = output11[ "box"]
        ubbox11  = output11["bbox"]

        output12 = osut.realignedFace(vtx, True) # narrow, now wide
        ubox12   = output12[ "box"]
        ubbox12  = output12["bbox"]
        self.assertFalse(osut.areSame(ubox11, ubox12))
        self.assertFalse(osut.areSame(ubbox11, ubbox12))
        self.assertTrue(osut.areSame(ubox12, ubox10))
        self.assertTrue(osut.areSame(ubbox12, ubbox10))

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Irregular surface (parallelogram).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d(  4,  0,  0))
        vtx.append(openstudio.Point3d(  6,  4,  0))
        vtx.append(openstudio.Point3d(  3,  8,  0))
        vtx.append(openstudio.Point3d(  1,  4,  0))

        output13 = osut.realignedFace(vtx)
        uset13   = output13[ "set"]
        ubox13   = output13[ "box"]
        ubbox13  = output13["bbox"]

        # Pre-isolate bounded box (preferable with irregular surfaces).
        box      = osut.boundedBox(vtx)
        output14 = osut.realignedFace(box)
        uset14   = output14[ "set"]
        ubox14   = output14[ "box"]
        ubbox14  = output14["bbox"]
        self.assertTrue(osut.areSame(uset14, ubox14))
        self.assertTrue(osut.areSame(uset14, ubbox14))
        self.assertFalse(osut.areSame(uset13, uset14))
        self.assertFalse(osut.areSame(ubox13, ubox14))
        self.assertFalse(osut.areSame(ubbox13, ubbox14))

        rset14 = output14["r"] * (output14["t"] * uset14)
        self.assertTrue(osut.areSame(box, rset14))

        #  --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Bounded box from an irregular, non-convex, "J"-shaped corridor roof.
        # This is a VERY EXPENSIVE method when dealing with such HIGHLY
        # CONVOLUTED polygons !
        # vtx = openstudio.Point3dVector()
        # vtx.append(openstudio.Point3d(  0.0000000,  0.0000, 3.658))
        # vtx.append(openstudio.Point3d(  0.0000000, 35.3922, 3.658))
        # vtx.append(openstudio.Point3d(  7.4183600, 35.3922, 3.658))
        # vtx.append(openstudio.Point3d(  7.8150800, 35.2682, 3.658))
        # vtx.append(openstudio.Point3d( 13.8611000, 35.2682, 3.658))
        # vtx.append(openstudio.Point3d( 13.8611000, 38.9498, 3.658))
        # vtx.append(openstudio.Point3d(  7.8150800, 38.9498, 3.658))
        # vtx.append(openstudio.Point3d(  7.8150800, 38.6275, 3.658))
        # vtx.append(openstudio.Point3d( -0.0674713, 38.6275, 3.658))
        # vtx.append(openstudio.Point3d( -0.0674713, 48.6247, 3.658))
        # vtx.append(openstudio.Point3d( -2.5471900, 48.6247, 3.658))
        # vtx.append(openstudio.Point3d( -2.5471900, 38.5779, 3.658))
        # vtx.append(openstudio.Point3d( -6.7255500, 38.5779, 3.658))
        # vtx.append(openstudio.Point3d( -2.5471900,  2.7700, 3.658))
        # vtx.append(openstudio.Point3d(-14.9024000,  2.7700, 3.658))
        # vtx.append(openstudio.Point3d(-14.9024000,  0.0000, 3.658))
        #
        # bbx = osut.boundedBox(vtx)
        # self.assertTrue(osut.fits(bbx, vtx))
        # if o.logs(): print(mod1.logs())
        self.assertEqual(o.status(), 0)

    def test23_fits_overlaps(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

        version = int("".join(openstudio.openStudioVersion().split(".")))

        p1 = openstudio.Point3dVector()
        p2 = openstudio.Point3dVector()

        p1.append(openstudio.Point3d(3.63, 0, 4.03))
        p1.append(openstudio.Point3d(3.63, 0, 2.44))
        p1.append(openstudio.Point3d(7.34, 0, 2.44))
        p1.append(openstudio.Point3d(7.34, 0, 4.03))

        t = openstudio.Transformation.alignFace(p1)

        if version < 340:
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

        del model
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
        pts   = osut.nonCollinears(ceiling.vertices(), 3)
        box01 = osut.triadBox(pts)
        box11 = osut.boundedBox(ceiling)
        self.assertTrue(osut.areSame(box01, box11))
        self.assertTrue(osut.fits(box01, ceiling))

        pts   = osut.nonCollinears(roof.vertices(), 3)
        box02 = osut.medialBox(pts)
        box12 = osut.boundedBox(roof)
        self.assertTrue(osut.areSame(box02, box12))
        self.assertTrue(osut.fits(box02, roof))

        box03 = osut.triadBox(pts)
        self.assertFalse(osut.areSame(box03, box12))
        self.assertEqual(o.status(), 0)

        # For parallel surfaces, OSut's 'overlap' output is consistent
        # regardless of the sequence of arguments. Here, floor and ceiling are
        # mirrored - the former counterclockwise, the latter clockwise. The
        # returned overlap conserves the vertex winding of the first surface.
        self.assertTrue(osut.areParallel(floor, ceiling))
        olap1 = osut.overlap(floor, ceiling)
        olap2 = osut.overlap(ceiling, floor)
        self.assertTrue(osut.areSame(floor.vertices(), olap1))
        self.assertTrue(osut.areSame(ceiling.vertices(), olap2))

        # When surfaces aren't parallel, 'overlap' remains somewhat consistent
        # if both share a common edge. Here, the flat soffit shares an edge
        # with the sloped roof. The projection of the soffit neatly fits onto
        # the roof, yet the generated overlap will obviously be distorted with
        # respect to the original soffit vertices. Nonetheless, the shared
        # vertices/edge(s) would be preserved.
        olap1 = osut.overlap(soffit, roof, True)
        olap2 = osut.overlap(roof, soffit, True)
        self.assertTrue(osut.areParallel(olap1, soffit))
        self.assertFalse(osut.areParallel(olap1, roof))
        self.assertTrue(osut.areParallel(olap2, roof))
        self.assertFalse(osut.areParallel(olap2, soffit))
        self.assertEqual(len(olap1), 4)
        self.assertEqual(len(olap2), 4)
        area1 = openstudio.getArea(olap1)
        area2 = openstudio.getArea(olap2)
        self.assertTrue(area1)
        self.assertTrue(area2)
        area1 = area1.get()
        area2 = area2.get()
        self.assertGreater(abs(area1 - area2), TOL)
        pl1 = openstudio.Plane(olap1)
        pl2 = openstudio.Plane(olap2)
        n1  = pl1.outwardNormal()
        n2  = pl2.outwardNormal()
        dt1 = soffit.plane().outwardNormal().dot(n1)
        dt2 = roof.plane().outwardNormal().dot(n2)
        self.assertAlmostEqual(dt1, 1, places=2)
        self.assertAlmostEqual(dt2, 1, places=2)

        # When surfaces are neither parallel nor share any edges (e.g. sloped roof
        # vs horizontal floor), the generated overlap is more likely to hold extra
        # vertices, depending on which surface it is cast onto.
        olap1 = osut.overlap(floor, roof, True)
        olap2 = osut.overlap(roof, floor, True)
        self.assertTrue(osut.areParallel(olap1, floor))
        self.assertFalse(osut.areParallel(olap1, roof))
        self.assertTrue(osut.areParallel(olap2, roof))
        self.assertFalse(osut.areParallel(olap2, floor))
        self.assertEqual(len(olap1), 3)
        self.assertEqual(len(olap2), 5)
        area1 = openstudio.getArea(olap1)
        area2 = openstudio.getArea(olap2)
        self.assertTrue(area1)
        self.assertTrue(area2)
        area1 = area1.get()
        area2 = area2.get()
        self.assertGreater(area2 - area1, TOL)
        pl1 = openstudio.Plane(olap1)
        pl2 = openstudio.Plane(olap2)
        n1  = pl1.outwardNormal()
        n2  = pl2.outwardNormal()
        dt1 = floor.plane().outwardNormal().dot(n1)
        dt2 = roof.plane().outwardNormal().dot(n2)
        self.assertAlmostEqual(dt1, 1, places=2)
        self.assertAlmostEqual(dt2, 1, places=2)

        # Alternative: first 'cast' vertically one polygon onto the other.
        pl1    = openstudio.Plane(ceiling.vertices())
        pl2    = openstudio.Plane(roof.vertices())
        up     = openstudio.Point3d(0, 0, 1) - openstudio.Point3d(0, 0, 0)
        down   = openstudio.Point3d(0, 0,-1) - openstudio.Point3d(0, 0, 0)
        cast00 = osut.cast(roof, ceiling, down)
        cast01 = osut.cast(roof, ceiling, up)
        cast02 = osut.cast(ceiling, roof, up)
        self.assertTrue(osut.areParallel(cast00, ceiling))
        self.assertTrue(osut.areParallel(cast01, ceiling))
        self.assertTrue(osut.areParallel(cast02, roof))
        self.assertFalse(osut.areParallel(cast00, roof))
        self.assertFalse(osut.areParallel(cast01, roof))
        self.assertFalse(osut.areParallel(cast02, ceiling))

        # As the cast ray is vertical, only the Z-axis coordinate changes.
        for i, pt in enumerate(cast00):
            self.assertTrue(pl1.pointOnPlane(pt))
            self.assertAlmostEqual(pt.x(), roof.vertices()[i].x(), places=2)
            self.assertAlmostEqual(pt.y(), roof.vertices()[i].y(), places=2)

        # The direction of the cast ray doesn't matter (e.g. up or down).
        for i, pt in enumerate(cast01):
            self.assertTrue(pl1.pointOnPlane(pt))
            self.assertAlmostEqual(pt.x(), cast00[i].x(), places=2)
            self.assertAlmostEqual(pt.y(), cast00[i].y(), places=2)

        # The sequence of arguments matters: 1st polygon is cast onto 2nd.
        for i, pt in enumerate(cast02):
            self.assertTrue(pl2.pointOnPlane(pt))
            self.assertAlmostEqual(pt.x(), ceiling.vertices()[i].x())
            self.assertAlmostEqual(pt.y(), ceiling.vertices()[i].y())

        # Overlap between roof and vertically-cast ceiling onto roof plane.
        olap02 = osut.overlap(roof, cast02)
        self.assertEqual(len(olap02), 3) # not 5
        self.assertTrue(osut.fits(olap02, roof))

        for pt in olap02: self.assertTrue(pl2.pointOnPlane(pt))

        vtx1 = openstudio.Point3dVector()
        vtx1.append(openstudio.Point3d(17.69, 0.00, 0))
        vtx1.append(openstudio.Point3d(13.46, 4.46, 0))
        vtx1.append(openstudio.Point3d( 4.23, 4.46, 0))
        vtx1.append(openstudio.Point3d( 0.00, 0.00, 0))

        vtx2 = openstudio.Point3dVector()
        vtx2.append(openstudio.Point3d( 8.85, 0.00, 0))
        vtx2.append(openstudio.Point3d( 8.85, 4.46, 0))
        vtx2.append(openstudio.Point3d( 4.23, 4.46, 0))
        vtx2.append(openstudio.Point3d( 4.23, 0.00, 0))

        self.assertTrue(osut.isPointAlongSegment(vtx2[1], [vtx1[1], vtx1[2]]))
        self.assertTrue(osut.isPointAlongSegments(vtx2[1], vtx1))
        self.assertTrue(osut.isPointWithinPolygon(vtx2[1], vtx1))
        self.assertTrue(osut.fits(vtx2, vtx1))

        # Bounded box test.
        cast03 = osut.cast(ceiling, south, down)
        self.assertTrue(osut.isRectangular(cast03))
        olap03 = osut.overlap(south, cast03)
        self.assertTrue(osut.areParallel(south, olap03))
        self.assertFalse(osut.isRectangular(olap03))
        box = osut.boundedBox(olap03)
        self.assertTrue(osut.isRectangular(box))
        self.assertTrue(osut.areParallel(olap03, box))

        area1 = openstudio.getArea(olap03)
        area2 = openstudio.getArea(box)
        self.assertTrue(area1)
        self.assertTrue(area2)
        area1 = area1.get()
        area2 = area2.get()
        self.assertEqual(int(100 * area2 / area1), 68) # %
        self.assertEqual(o.status(), 0)

        del model

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Testing more complex cases, e.g. triangular windows, irregular 4-side
        # windows, rough opening edges overlapping parent surface edges. These
        # tests were initially part of the TBD Tests repository:
        #
        #   github.com/rd2/tbd_tests
        #
        # ... yet have been upgraded and are now tested here.
        model = openstudio.model.Model()
        space = openstudio.model.Space(model)
        space.setName("Space")

        # Windows are SimpleGlazing constructions.
        fen     = openstudio.model.Construction(model)
        glazing = openstudio.model.SimpleGlazing(model)
        layers  = openstudio.model.MaterialVector()
        fen.setName("FD fen")
        glazing.setName("FD glazing")
        self.assertTrue(glazing.setUFactor(2.0))
        layers.append(glazing)
        self.assertTrue(fen.setLayers(layers))

        # Frame & Divider object.
        w000 = 0.000
        w200 = 0.200 # 0mm to 200mm (wide!) around glazing
        fd   = openstudio.model.WindowPropertyFrameAndDivider(model)
        fd.setName("FD")
        self.assertTrue(fd.setFrameConductance(0.500))
        self.assertTrue(fd.isFrameWidthDefaulted())
        self.assertAlmostEqual(fd.frameWidth(), w000, places=2)

        # A square base wall surface:
        v0 = openstudio.Point3dVector()
        v0.append(openstudio.Point3d( 0.00, 0.00, 10.00))
        v0.append(openstudio.Point3d( 0.00, 0.00,  0.00))
        v0.append(openstudio.Point3d(10.00, 0.00,  0.00))
        v0.append(openstudio.Point3d(10.00, 0.00, 10.00))

        # A first triangular window:
        v1 = openstudio.Point3dVector()
        v1.append(openstudio.Point3d( 2.00, 0.00, 8.00))
        v1.append(openstudio.Point3d( 1.00, 0.00, 6.00))
        v1.append(openstudio.Point3d( 4.00, 0.00, 9.00))

        # A larger, irregular window:
        v2 = openstudio.Point3dVector()
        v2.append(openstudio.Point3d( 7.00, 0.00, 4.00))
        v2.append(openstudio.Point3d( 4.00, 0.00, 1.00))
        v2.append(openstudio.Point3d( 8.00, 0.00, 2.00))
        v2.append(openstudio.Point3d( 9.00, 0.00, 3.00))

        # A final triangular window, near the wall's upper right corner:
        v3 = openstudio.Point3dVector()
        v3.append(openstudio.Point3d( 9.00, 0.00, 9.80))
        v3.append(openstudio.Point3d( 9.80, 0.00, 9.00))
        v3.append(openstudio.Point3d( 9.80, 0.00, 9.80))

        w0 = openstudio.model.Surface(v0, model)
        w1 = openstudio.model.SubSurface(v1, model)
        w2 = openstudio.model.SubSurface(v2, model)
        w3 = openstudio.model.SubSurface(v3, model)
        w0.setName("w0")
        w1.setName("w1")
        w2.setName("w2")
        w3.setName("w3")
        self.assertTrue(w0.setSpace(space))
        sub_gross = 0

        for w in [w1, w2, w3]:
            self.assertTrue(w.setSubSurfaceType("FixedWindow"))
            self.assertTrue(w.setSurface(w0))
            self.assertTrue(w.setConstruction(fen))
            self.assertTrue(w.uFactor())
            self.assertAlmostEqual(w.uFactor().get(), 2.0, places=1)
            self.assertTrue(w.allowWindowPropertyFrameAndDivider())
            self.assertTrue(w.setWindowPropertyFrameAndDivider(fd))
            width = w.windowPropertyFrameAndDivider().get().frameWidth()
            self.assertAlmostEqual(width, w000, places=2)

            sub_gross += w.grossArea()

        self.assertAlmostEqual(w1.grossArea(), 1.50, places=2)
        self.assertAlmostEqual(w2.grossArea(), 6.00, places=2)
        self.assertAlmostEqual(w3.grossArea(), 0.32, places=2)
        self.assertAlmostEqual(w0.grossArea(), 100.00, places=2)
        self.assertAlmostEqual(w1.netArea(), w1.grossArea(), places=2)
        self.assertAlmostEqual(w2.netArea(), w2.grossArea(), places=2)
        self.assertAlmostEqual(w3.netArea(), w3.grossArea(), places=2)
        self.assertAlmostEqual(w0.netArea(), w0.grossArea()-sub_gross, places=2)

        # Applying 2 sets of alterations:
        #   - WITHOUT, then WITH Frame & Dividers (F&D)
        #   - 3 successive 20° rotations around:
        angle  = math.pi / 9
        origin = openstudio.Point3d(0, 0, 0)
        east   = openstudio.Point3d(1, 0, 0) - origin
        up     = openstudio.Point3d(0, 0, 1) - origin
        north  = openstudio.Point3d(0, 1, 0) - origin

        for i in range(4): # successive rotations
            if i != 0:
                if i == 1: r = openstudio.createRotation(origin, east, angle)
                if i == 2: r = openstudio.createRotation(origin, up, angle)
                if i == 3: r = openstudio.createRotation(origin, north, angle)
                self.assertTrue(w0.setVertices(r.inverse() * w0.vertices()))
                self.assertTrue(w1.setVertices(r.inverse() * w1.vertices()))
                self.assertTrue(w2.setVertices(r.inverse() * w2.vertices()))
                self.assertTrue(w3.setVertices(r.inverse() * w3.vertices()))

            for j in range(2): # F&D
                if j == 0:
                    wx = w000
                    if i != 0: fd.resetFrameWidth()
                else:
                    wx = w200
                    self.assertTrue(fd.setFrameWidth(wx))

                    for w in [w1, w2, w3]:
                        wfd = w.windowPropertyFrameAndDivider().get()
                        width = wfd.frameWidth()
                        self.assertAlmostEqual(width, wx, places=2)

                # F&D widths offset window vertices.
                w1o = osut.offset(w1.vertices(), wx, 300)
                w2o = osut.offset(w2.vertices(), wx, 300)
                w3o = osut.offset(w3.vertices(), wx, 300)

                w1o_m2 = openstudio.getArea(w1o)
                w2o_m2 = openstudio.getArea(w2o)
                w3o_m2 = openstudio.getArea(w3o)
                self.assertTrue(w1o_m2)
                self.assertTrue(w2o_m2)
                self.assertTrue(w3o_m2)
                w1o_m2 = w1o_m2.get()
                w2o_m2 = w2o_m2.get()
                w3o_m2 = w3o_m2.get()

                if j == 0:
                    # w1 == 1.50m2; w2 == 6.00 m2; w3 == 0.32m2
                    self.assertAlmostEqual(w1o_m2, w1.grossArea(), places=2)
                    self.assertAlmostEqual(w2o_m2, w2.grossArea(), places=2)
                    self.assertAlmostEqual(w3o_m2, w3.grossArea(), places=2)
                else:
                    self.assertAlmostEqual(w1o_m2, 3.75, places=2)
                    self.assertAlmostEqual(w2o_m2, 8.64, places=2)
                    self.assertAlmostEqual(w3o_m2, 1.10, places=2)

                # All windows entirely fit within the wall (without F&D).
                for w in [w1, w2, w3]: self.assertTrue(osut.fits(w, w0, True))

                # All windows fit within the wall (with F&D).
                for w in [w1o, w2o]: self.assertTrue(osut.fits(w, w0))

                # If F&D frame width == 200mm, w3o aligns along the wall top &
                # side, so not entirely within wall polygon.
                self.assertTrue(osut.fits(w3, w0, True))
                self.assertTrue(osut.fits(w3o, w0))
                if j == 0: self.assertTrue(osut.fits(w3o, w0, True))
                if j != 0: self.assertFalse(osut.fits(w3o, w0, True))

                # None of the windows conflict with each other.
                self.assertFalse(osut.overlapping(w1o, w2o))
                self.assertFalse(osut.overlapping(w1o, w3o))
                self.assertFalse(osut.overlapping(w2o, w3o))

        del model
        self.assertEqual(o.clean(), DBG)

    def test24_triangulation(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

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

        # Point ENTIRELY within (vs outside) a polygon.
        self.assertFalse(osut.isPointWithinPolygon(p0, [p0, p1, p2, p3], True))
        self.assertFalse(osut.isPointWithinPolygon(p1, [p0, p1, p2, p3], True))
        self.assertFalse(osut.isPointWithinPolygon(p2, [p0, p1, p2, p3], True))
        self.assertFalse(osut.isPointWithinPolygon(p3, [p0, p1, p2, p3], True))
        self.assertFalse(osut.isPointWithinPolygon(p4, [p0, p1, p2, p3]))
        self.assertTrue(osut.isPointWithinPolygon(p5, [p0, p1, p2, p3]))
        self.assertFalse(osut.isPointWithinPolygon(p6, [p0, p1, p2, p3]))
        self.assertTrue(osut.isPointWithinPolygon(p7, [p0, p1, p2, p3]))
        self.assertEqual(o.status(), 0)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Test invalid plane.
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d(20, 0, 10))
        vtx.append(openstudio.Point3d( 0, 0, 10))
        vtx.append(openstudio.Point3d( 0, 0,  0))
        vtx.append(openstudio.Point3d(20, 1,  0))

        self.assertEqual(len(osut.poly(vtx)), 0)
        self.assertTrue(o.is_error())
        self.assertEqual(len(o.logs()), 1)
        self.assertTrue("Empty 'plane'" in o.logs()[0]["message"])
        self.assertEqual(o.clean(), DBG)

        # Self-intersecting polygon. If reactivated, OpenStudio logs to stdout:
        #   [utilities.Transformation]
        #   <1> Cannot compute outward normal for vertices
        # vtx = openstudio.Point3dVector()
        # vtx.append(openstudio.Point3d(20, 0, 10))
        # vtx.append(openstudio.Point3d( 0, 0, 10))
        # vtx.append(openstudio.Point3d(20, 0,  0))
        # vtx.append(openstudio.Point3d( 0, 0,  0))
        #
        # Original polygon remains unaltered.
        # self.assertEqual(len(osut.poly(vtx)), 4)
        # self.assertEqual(o.status(), 0)
        # self.assertEqual(o.clean(), DBG)

        # Regular polygon, counterclockwise yet not UpperLeftCorner (ULC).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d(20,  0, 10))
        vtx.append(openstudio.Point3d( 0,  0, 10))
        vtx.append(openstudio.Point3d( 0,  0,  0))

        sgs = osut.segments(vtx)
        self.assertTrue(isinstance(sgs, openstudio.Point3dVectorVector))
        self.assertEqual(len(sgs), 3)

        for i, sg in enumerate(sgs):
            if not osut.shareXYZ(sg, "x", sg[0].x()):
                vplane = osut.verticalPlane(sg[0], sg[1])
                self.assertTrue(isinstance(vplane, openstudio.Plane))

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Test when alignFace switches solution when surfaces are nearly flat,
        # i.e. when dot product of surface normal vs zenith > 0.99.
        #   (see openstudio.Transformation.alignFace)
        origin  = openstudio.Point3d(0,0,0)
        originZ = openstudio.Point3d(0,0,1)
        zenith  = originZ - origin

        # 1st surface, nearly horizontal.
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 2,10, 0.0))
        vtx.append(openstudio.Point3d( 6, 4, 0.0))
        vtx.append(openstudio.Point3d( 8, 8, 0.5))
        normal = openstudio.getOutwardNormal(vtx).get()
        self.assertGreater(abs(zenith.dot(normal)), 0.99)
        self.assertTrue(osut.facingUp(vtx))

        aligned = list(osut.poly(vtx, False, False, False, True, "ulc"))
        matches = []

        for pt in aligned:
            if osut.areSame(pt, origin): matches.append(pt)

        self.assertEqual(len(matches), 0)

        # 2nd surface (nearly identical, yet too slanted to be flat.
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 2,10, 0.0))
        vtx.append(openstudio.Point3d( 6, 4, 0.0))
        vtx.append(openstudio.Point3d( 8, 8, 0.6))
        normal = openstudio.getOutwardNormal(vtx).get()
        self.assertLess(abs(zenith.dot(normal)), 0.99)
        self.assertFalse(osut.facingUp(vtx))

        aligned = list(osut.poly(vtx, False, False, False, True, "ulc"))
        matches = []

        for pt in aligned:
            if osut.areSame(pt, origin): matches.append(pt)

        self.assertEqual(len(matches), 1)

    def test26_ulc_blc(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

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

    def test27_polygon_attributes(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(INF), INF)
        self.assertEqual(o.level(), INF)

        # 2x points (not a polygon).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 0, 0,10))
        vtx.append(openstudio.Point3d( 0, 0,10))

        v = osut.poly(vtx)
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertFalse(v)
        self.assertTrue(o.is_error())
        self.assertEqual(len(o.logs()), 1)
        self.assertTrue("non-collinears < 3" in o.logs()[0]["message"])
        self.assertEqual(o.clean(), INF)

        # 3x non-unique points (not a polygon).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 0, 0,10))
        vtx.append(openstudio.Point3d( 0, 0,10))
        vtx.append(openstudio.Point3d( 0, 0,10))

        v = osut.poly(vtx)
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertFalse(v)
        self.assertTrue(o.is_error())
        self.assertEqual(len(o.logs()), 1)
        self.assertTrue("non-collinears < 3" in o.logs()[0]["message"])
        self.assertEqual(o.clean(), INF)

        # 4th non-planar point (not a polygon).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 0, 0,10))
        vtx.append(openstudio.Point3d( 0, 0, 0))
        vtx.append(openstudio.Point3d(10, 0,10))
        vtx.append(openstudio.Point3d( 0,10,10))

        v = osut.poly(vtx)
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertFalse(v)
        self.assertTrue(o.is_error())
        self.assertEqual(len(o.logs()), 1)
        self.assertTrue("plane" in o.logs()[0]["message"])
        self.assertEqual(o.clean(), INF)

        # 3x unique points (a valid polygon).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 0, 0,10))
        vtx.append(openstudio.Point3d( 0, 0, 0))
        vtx.append(openstudio.Point3d(10, 0, 0))

        v = osut.poly(vtx)
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertEqual(len(v), 3)
        self.assertEqual(o.status(), 0)

        # 4th collinear point (collinear permissive).
        vtx.append(openstudio.Point3d(20, 0, 0))
        v = osut.poly(vtx)
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertEqual(len(v), 4)
        self.assertEqual(o.status(), 0)

        # Intersecting points, e.g. a 'bowtie' (not a valid Openstudio polygon).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 0, 0,10))
        vtx.append(openstudio.Point3d( 0, 0, 0))
        vtx.append(openstudio.Point3d(10, 0,10))
        vtx.append(openstudio.Point3d( 0,10, 0))

        v = osut.poly(vtx)
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertFalse(v)
        self.assertTrue(o.is_error())
        self.assertEqual(len(o.logs()), 1)
        self.assertTrue("Empty 'plane' (osut.poly)" in o.logs()[0]["message"])
        self.assertEqual(o.clean(), INF)

        # Ensure uniqueness & OpenStudio's counterclockwise ULC sequence.
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 0, 0,10))
        vtx.append(openstudio.Point3d( 0, 0, 0))
        vtx.append(openstudio.Point3d(10, 0, 0))
        vtx.append(openstudio.Point3d(10, 0, 0))

        v = osut.poly(vtx, False, True, False, False, "ulc")
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertEqual(len(v), 3)
        self.assertTrue(osut.areSame(vtx[0], v[0]))
        self.assertTrue(osut.areSame(vtx[1], v[1]))
        self.assertTrue(osut.areSame(vtx[2], v[2]))
        self.assertEqual(o.status(), 0)

        # Ensure strict non-collinearity (ULC).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 0, 0,10))
        vtx.append(openstudio.Point3d( 0, 0, 0))
        vtx.append(openstudio.Point3d(10, 0, 0))
        vtx.append(openstudio.Point3d(20, 0, 0))

        v = osut.poly(vtx, False, False, True, False, "ulc")
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertEqual(len(v), 3)
        self.assertTrue(osut.areSame(vtx[0], v[0]))
        self.assertTrue(osut.areSame(vtx[1], v[1]))
        self.assertTrue(osut.areSame(vtx[3], v[2]))
        self.assertEqual(o.status(), 0)

        # Ensuring strict non-collinearity also ensures uniqueness (ULC).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 0, 0,10))
        vtx.append(openstudio.Point3d( 0, 0, 0))
        vtx.append(openstudio.Point3d( 0, 0, 0))
        vtx.append(openstudio.Point3d(10, 0, 0))
        vtx.append(openstudio.Point3d(20, 0, 0))

        v = osut.poly(vtx, False, False, True, False, "ulc")
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertEqual(len(v), 3)
        self.assertTrue(osut.areSame(vtx[0], v[0]))
        self.assertTrue(osut.areSame(vtx[1], v[1]))
        self.assertTrue(osut.areSame(vtx[4], v[2]))
        self.assertEqual(o.status(), 0)

        # Check for (valid) convexity.
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 0, 0,10))
        vtx.append(openstudio.Point3d( 0, 0, 0))
        vtx.append(openstudio.Point3d(20, 0, 0))

        v = osut.poly(vtx, True)
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertEqual(len(v), 3)
        self.assertEqual(o.status(), 0)

        # Check for (invalid) convexity.
        vtx.append(openstudio.Point3d(1, 0, 1))
        v = osut.poly(vtx, True)
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertFalse(v)
        self.assertEqual(o.status(), 0)

        # 2nd check for (valid) convexity (with collinear points).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 0, 0,10))
        vtx.append(openstudio.Point3d( 0, 0, 0))
        vtx.append(openstudio.Point3d(10, 0, 0))
        vtx.append(openstudio.Point3d(20, 0, 0))

        v = osut.poly(vtx, True, False, False, False, "ulc")
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertEqual(len(v), 4)
        self.assertTrue(osut.areSame(vtx[0], v[0]))
        self.assertTrue(osut.areSame(vtx[1], v[1]))
        self.assertTrue(osut.areSame(vtx[2], v[2]))
        self.assertTrue(osut.areSame(vtx[3], v[3]))
        self.assertEqual(o.status(), 0)

        # 2nd check for (invalid) convexity (with collinear points).
        vtx.append(openstudio.Point3d( 1, 0, 1))
        v = osut.poly(vtx, True, False, False, False, "ulc")
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertFalse(v)
        self.assertEqual(o.status(), 0)

        # 3rd check for (valid) convexity (with collinear points), yet returned
        # 3D points vector become 'aligned' & clockwise.
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 0, 0,10))
        vtx.append(openstudio.Point3d( 0, 0, 0))
        vtx.append(openstudio.Point3d(10, 0, 0))
        vtx.append(openstudio.Point3d(20, 0, 0))

        v = osut.poly(vtx, True, False, False, True, "cw")
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertEqual(len(v), 4)
        self.assertTrue(osut.shareXYZ(v, "z", 0))
        self.assertTrue(osut.isClockwise(v))
        self.assertEqual(o.status(), 0)

        # Ensure returned vector remains in original sequence (if unaltered).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 0, 0,10))
        vtx.append(openstudio.Point3d( 0, 0, 0))
        vtx.append(openstudio.Point3d(10, 0, 0))
        vtx.append(openstudio.Point3d(20, 0, 0))

        v = osut.poly(vtx, True, False, False, False, "no")
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertEqual(len(v), 4)
        self.assertTrue(osut.areSame(vtx[0], v[0]))
        self.assertTrue(osut.areSame(vtx[1], v[1]))
        self.assertTrue(osut.areSame(vtx[2], v[2]))
        self.assertTrue(osut.areSame(vtx[3], v[3]))
        self.assertFalse(osut.isClockwise(v))
        self.assertEqual(o.status(), 0)

         # Sequence of returned vector if altered (avoid collinearity).
        vtx = openstudio.Point3dVector()
        vtx.append(openstudio.Point3d( 0, 0,10))
        vtx.append(openstudio.Point3d( 0, 0, 0))
        vtx.append(openstudio.Point3d(10, 0, 0))
        vtx.append(openstudio.Point3d(20, 0, 0))

        v = osut.poly(vtx, True, False, True, False, "no")
        self.assertTrue(isinstance(v, openstudio.Point3dVector))
        self.assertEqual(len(v), 3)
        self.assertTrue(osut.areSame(vtx[0], v[0]))
        self.assertTrue(osut.areSame(vtx[1], v[1]))
        self.assertTrue(osut.areSame(vtx[3], v[2]))
        self.assertFalse(osut.isClockwise(v))
        self.assertEqual(o.status(), 0)

    def test28_subsurface_insertions(self):
        # Examples of how to harness OpenStudio's Boost geometry methods to
        # safely insert subsurfaces along rotated/tilted/slanted base surfaces.
        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        translator = openstudio.osversion.VersionTranslator()

        v = int("".join(openstudio.openStudioVersion().split(".")))

        # Successful test.
        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        openarea = model.getSpaceByName("Open area 1")
        self.assertTrue(openarea)
        openarea = openarea.get()

        if v >= 350:
            self.assertTrue(openarea.isEnclosedVolume())
            self.assertTrue(openarea.isVolumeDefaulted())
            self.assertTrue(openarea.isVolumeAutocalculated())

        w5 = model.getSurfaceByName("Openarea 1 Wall 5")
        self.assertTrue(w5)
        w5 = w5.get()

        w5_space = w5.space()
        self.assertTrue(w5_space)
        w5_space = w5_space.get()
        self.assertEqual(w5_space, openarea)
        self.assertEqual(len(w5.vertices()), 4)

        # Delete w5, and replace with 1x slanted roof + 3x walls (1x tilted).
        # Keep w5 coordinates in memory (before deleting), as anchor points for
        # the 4x new surfaces.
        w5_0 = w5.vertices()[0]
        w5_1 = w5.vertices()[1]
        w5_2 = w5.vertices()[2]
        w5_3 = w5.vertices()[3]

        w5.remove()

        # 2x new points.
        roof_left  = openstudio.Point3d( 0.2166, 12.7865, 2.3528)
        roof_right = openstudio.Point3d(-5.4769, 11.2626, 2.3528)
        length     = (roof_left - roof_right).length()

        # New slanted roof.
        vec = openstudio.Point3dVector()
        vec.append(w5_0)
        vec.append(roof_left)
        vec.append(roof_right)
        vec.append(w5_3)
        roof = openstudio.model.Surface(vec, model)
        roof.setName("Openarea slanted roof")
        self.assertTrue(roof.setSurfaceType("RoofCeiling"))
        self.assertTrue(roof.setSpace(openarea))

        # Side-note test: genConstruction --- --- --- --- --- --- --- --- --- #
        self.assertTrue(roof.isConstructionDefaulted())
        lc = roof.construction()
        self.assertTrue(lc)
        lc = lc.get().to_LayeredConstruction()
        self.assertTrue(lc)
        lc = lc.get()
        c  = osut.genConstruction(model, dict(type="roof", uo=1/5.46))
        self.assertEqual(o.status(), 0)
        self.assertTrue(isinstance(c, openstudio.model.LayeredConstruction))
        self.assertTrue(roof.setConstruction(c))
        self.assertFalse(roof.isConstructionDefaulted())
        r1 = osut.rsi(lc)
        r2 = osut.rsi(c)
        d1 = osut.rsi(lc)
        d2 = osut.rsi(c)
        self.assertTrue(abs(r1 - r2) > 0)
        self.assertTrue(abs(d1 - d2) > 0)
        # ... end of genConstruction test --- --- --- --- --- --- --- --- --- #

        # New, inverse-tilted wall (i.e. cantilevered), under new slanted roof.
        vec = openstudio.Point3dVector()
        # vec.append(roof_left)  # TOPLEFT
        # vec.append(w5_1)       # BOTTOMLEFT
        # vec.append(w5_2)       # BOTTOMRIGHT
        # vec.append(roof_right) # TOPRIGHT

        # Test if starting instead from BOTTOMRIGHT (i.e. upside-down "U").
        vec.append(w5_2)       # BOTTOMRIGHT
        vec.append(roof_right) # TOPRIGHT
        vec.append(roof_left)  # TOPLEFT
        vec.append(w5_1)       # BOTTOMLEFT

        tilt_wall = openstudio.model.Surface(vec, model)
        tilt_wall.setName("Openarea tilted wall")
        self.assertTrue(tilt_wall.setSurfaceType("Wall"))
        self.assertTrue(tilt_wall.setSpace(openarea))

        # New, left side wall.
        vec = openstudio.Point3dVector()
        vec.append(w5_0)
        vec.append(w5_1)
        vec.append(roof_left)
        left_wall = openstudio.model.Surface(vec, model)
        left_wall.setName("Openarea left side wall")
        self.assertTrue(left_wall.setSpace(openarea))

        # New, right side wall.
        vec = openstudio.Point3dVector()
        vec.append(w5_3)
        vec.append(roof_right)
        vec.append(w5_2)
        right_wall = openstudio.model.Surface(vec, model)
        right_wall.setName("Openarea right side wall")
        self.assertTrue(right_wall.setSpace(openarea))

        if v >= 350:
            self.assertTrue(openarea.isEnclosedVolume)
            self.assertTrue(openarea.isVolumeDefaulted)
            self.assertTrue(openarea.isVolumeAutocalculated)

        model.save("./tests/files/osms/out/seb_mod.osm", True)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---  #
        # Fetch transform if tilted wall vertices were to "align", i.e.:
        #   - rotated/tilted
        #   - then flattened along XY plane
        #   - all Z-axis coordinates == ~0
        #   - vertices with the lowest X-axis values are aligned along X-axis (0)
        #   - vertices with the lowest Z-axis values ares aligned along Y-axis (0)
        #   - Z-axis values are represented as Y-axis values
        tr = openstudio.Transformation.alignFace(tilt_wall.vertices())
        aligned_tilt_wall = tr.inverse() * tilt_wall.vertices()
        # for pt in aligned_tilt_wall: print(pt)
        #   [4.89, 0.00, 0.00] # if BOTTOMRIGHT, i.e. upside-down "U"
        #   [5.89, 3.09, 0.00]
        #   [0.00, 3.09, 0.00]
        #   [1.00, 0.00, 0.00]
        # ... no change in results (once sub surfaces are added below), as
        # 'addSubs' does not rely 'directly' on World or Relative XYZ
        # coordinates of the base surface. It instead relies on base surface
        # width/height (once 'aligned'), regardless of the user-defined
        # sequence of vertices.

        # Find centerline along "aligned" X-axis, and upper Y-axis limit.
        min_x = 0
        max_x = 0
        max_y = 0

        for vec in aligned_tilt_wall:
            if vec.x() < min_x: min_x = vec.x()
            if vec.x() > max_x: max_x = vec.x()
            if vec.y() > max_y: max_y = vec.y()

        centerline = (max_x - min_x) / 2
        self.assertAlmostEqual(centerline * 2, length, places=2)

        # Subsurface dimensions (e.g. window/skylight).
        width  = 0.5
        height = 1.0

        # Add 3x new, tilted windows along the tilted wall upper horizontal edge
        # (i.e. max_Y), then realign with original tilted wall. Insert using 5mm
        # buffer, IF inserted along any host/parent/base surface edge, e.g. door
        # sill. Boost-based alignement/realignment does introduce small errors,
        # and EnergyPlus may raise warnings of overlaps between host/base/parent
        # surface and any of its new subsurface(s). Why 5mm (vs 25mm)? Keeping
        # buffer under 10mm, see: https://rd2.github.io/tbd/pages/subs.html.
        y = max_y - 0.005

        x   = centerline - width / 2 # center window
        vec = openstudio.Point3dVector()
        vec.append(openstudio.Point3d(x,         y,          0))
        vec.append(openstudio.Point3d(x,         y - height, 0))
        vec.append(openstudio.Point3d(x + width, y - height, 0))
        vec.append(openstudio.Point3d(x + width, y,          0))

        tilt_window1 = openstudio.model.SubSurface(tr * vec, model)
        tilt_window1.setName("Tilted window (center)")
        self.assertTrue(tilt_window1.setSubSurfaceType("FixedWindow"))
        self.assertTrue(tilt_window1.setSurface(tilt_wall))

        x   = centerline - 3*width/2 - 0.15 # window to the left of the first one
        vec = openstudio.Point3dVector()
        vec.append(openstudio.Point3d(x,         y,          0))
        vec.append(openstudio.Point3d(x,         y - height, 0))
        vec.append(openstudio.Point3d(x + width, y - height, 0))
        vec.append(openstudio.Point3d(x + width, y,          0))

        tilt_window2 = openstudio.model.SubSurface(tr * vec, model)
        tilt_window2.setName("Tilted window (left)")
        self.assertTrue(tilt_window2.setSubSurfaceType("FixedWindow"))
        self.assertTrue(tilt_window2.setSurface(tilt_wall))

        x   = centerline + width/2 + 0.15 # window to the right of the first one
        vec = openstudio.Point3dVector()
        vec.append(openstudio.Point3d(x,         y,          0))
        vec.append(openstudio.Point3d(x,         y - height, 0))
        vec.append(openstudio.Point3d(x + width, y - height, 0))
        vec.append(openstudio.Point3d(x + width, y,          0))

        tilt_window3 = openstudio.model.SubSurface(tr * vec, model)
        tilt_window3.setName("Tilted window (right)")
        self.assertTrue(tilt_window3.setSubSurfaceType("FixedWindow"))
        self.assertTrue(tilt_window3.setSurface(tilt_wall))

        # model.save("./tests/files/osms/out/seb_fen.osm", True)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Repeat for 3x skylights. Fetch transform if slanted roof vertices were
        # also to "align". Recover the (default) window construction.
        self.assertTrue(tilt_window1.isConstructionDefaulted())
        construction = tilt_window1.construction()
        self.assertTrue(construction)
        construction = construction.get()

        tr = openstudio.Transformation.alignFace(roof.vertices())
        aligned_roof = tr.inverse() * roof.vertices()

        # Find centerline along "aligned" X-axis, and lower Y-axis limit.
        min_x = 0
        max_x = 0
        min_y = 0

        for vec in aligned_tilt_wall:
            if vec.x() < min_x: min_x = vec.x()
            if vec.x() > max_x: max_x = vec.x()
            if vec.y() < min_y: min_y = vec.y()

        centerline = (max_x - min_x) / 2
        self.assertAlmostEqual(centerline * 2, length, places=2)

        # Add 3x new, slanted skylights aligned along upper horizontal edge of
        # roof (i.e. min_Y), then realign with original roof.
        y = min_y + 0.005

        x   = centerline - width / 2 # center skylight
        vec = openstudio.Point3dVector()
        vec.append(openstudio.Point3d(x,         y + height, 0))
        vec.append(openstudio.Point3d(x,         y,          0))
        vec.append(openstudio.Point3d(x + width, y,          0))
        vec.append(openstudio.Point3d(x + width, y + height, 0))

        skylight1 = openstudio.model.SubSurface(tr * vec, model)
        skylight1.setName("Skylight (center)")
        self.assertTrue(skylight1.setSubSurfaceType("Skylight"))
        self.assertTrue(skylight1.setConstruction(construction))
        self.assertTrue(skylight1.setSurface(roof))

        x   = centerline - 3*width/2 - 0.15 # skylight to the left of center
        vec = openstudio.Point3dVector()
        vec.append(openstudio.Point3d(x,         y + height, 0))
        vec.append(openstudio.Point3d(x,         y         , 0))
        vec.append(openstudio.Point3d(x + width, y         , 0))
        vec.append(openstudio.Point3d(x + width, y + height, 0))

        skylight2 = openstudio.model.SubSurface(tr * vec, model)
        skylight2.setName("Skylight (left)")
        self.assertTrue(skylight2.setSubSurfaceType("Skylight"))
        self.assertTrue(skylight2.setConstruction(construction))
        self.assertTrue(skylight2.setSurface(roof))

        x   = centerline + width/2 + 0.15 # skylight to the right of center
        vec = openstudio.Point3dVector()
        vec.append(openstudio.Point3d(x,         y + height, 0))
        vec.append(openstudio.Point3d(x,         y         , 0))
        vec.append(openstudio.Point3d(x + width, y         , 0))
        vec.append(openstudio.Point3d(x + width, y + height, 0))

        skylight3 = openstudio.model.SubSurface(tr * vec, model)
        skylight3.setName("Skylight (right)")
        self.assertTrue(skylight3.setSubSurfaceType("Skylight"))
        self.assertTrue(skylight3.setConstruction(construction))
        self.assertTrue(skylight3.setSurface(roof))

        model.save("./tests/files/osms/out/seb_ext1.osm", True)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Now test the same result when relying on osut.addSub:
        path  = openstudio.path("./tests/files/osms/out/seb_mod.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        roof = model.getSurfaceByName("Openarea slanted roof")
        self.assertTrue(roof)
        roof = roof.get()

        tilt_wall = model.getSurfaceByName("Openarea tilted wall")
        self.assertTrue(tilt_wall)
        tilt_wall = tilt_wall.get()

        head   = max_y - 0.005
        offset = width + 0.15

        # Add array of 3x windows to tilted wall.
        sub           = {}
        sub["id"    ] = "Tilted window"
        sub["height"] = height
        sub["width" ] = width
        sub["head"  ] = head
        sub["count" ] = 3
        sub["offset"] = offset

        # The simplest argument set for 'addSubs' is:
        self.assertTrue(osut.addSubs(tilt_wall, sub))
        self.assertEqual(o.status(), 0)

        # As the base surface is tilted, OpenStudio's 'alignFace' and
        # 'alignZPrime' behave in a very intuitive manner: there is no point
        # requesting 'addSubs' first realigns and/or concentrates on the
        # polygon's bounded box - the outcome would be the same in all cases:
        #
        # self.assertTrue(osut.addSubs(tilt_wall, sub, False, False, True))
        # self.assertTrue(osut.addSubs(tilt_wall, sub, False, True))
        tilted = model.getSubSurfaceByName("Tilted window:0")
        self.assertTrue(tilted)
        tilted = tilted.get()

        construction = tilted.construction()
        self.assertTrue(construction)
        construction = construction.get()
        sub["assembly"] = construction

        del sub["head"]
        self.assertFalse("head" in sub)
        sub["id"  ] = ""
        sub["sill"] = 0.0 # will be reset to 5mm
        sub["type"] = "Skylight"
        self.assertTrue(osut.addSubs(roof, sub))
        self.assertTrue(o.is_warn())
        self.assertEqual(len(o.logs()), 2)

        for lg in o.logs():
            self.assertTrue("reset" in lg["message"].lower())
            self.assertTrue("sill"  in lg["message"].lower())

        model.save("./tests/files/osms/out/seb_ext2.osm", True)

        del model
        self.assertEqual(o.clean(), DBG)

    def test29_surface_width_height(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        translator = openstudio.osversion.VersionTranslator()

        # Successful test.
        path  = openstudio.path("./tests/files/osms/out/seb_ext2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        # Extension holds:
        #   - 2x vertical side walls
        #   - tilted (cantilevered) wall
        #   - sloped roof
        tilted = model.getSurfaceByName("Openarea tilted wall")
        left   = model.getSurfaceByName("Openarea left side wall")
        right  = model.getSurfaceByName("Openarea right side wall")
        self.assertTrue(tilted)
        self.assertTrue(left)
        self.assertTrue(right)
        tilted = tilted.get()
        left   = left.get()
        right  = right.get()

        self.assertFalse(osut.facingUp(tilted))
        self.assertFalse(osut.shareXYZ(tilted))

        # Neither wall has coordinates that align with the model grid. Without
        # some transformation (eg alignFace), OSut's 'width' of a given surface
        # is of limited utility. A vertical surface's 'height' is also somewhat
        # valid/useful.
        w1 = osut.width(tilted)
        h1 = osut.height(tilted)
        self.assertAlmostEqual(w1, 5.69, places=2)
        self.assertAlmostEqual(h1, 2.35, places=2)

        # Aligned, a vertical or sloped (or tilted) surface's 'width' and
        # 'height' correctly report what a tape measurement would reveal
        # (from left to right, when looking at the surface perpendicularly).
        t = openstudio.Transformation.alignFace(tilted.vertices())
        tilted_aligned = t.inverse() * tilted.vertices()
        w01 = osut.width(tilted_aligned)
        h01 = osut.height(tilted_aligned)
        self.assertTrue(osut.facingUp(tilted_aligned))
        self.assertTrue(osut.shareXYZ(tilted_aligned))
        self.assertAlmostEqual(w01, 5.89, places=2)
        self.assertAlmostEqual(h01, 3.09, places=2)

        w2 = osut.width(left)
        h2 = osut.height(left)
        self.assertAlmostEqual(w2, 0.45, places=2)
        self.assertAlmostEqual(h2, 3.35, places=2)
        t = openstudio.Transformation.alignFace(left.vertices())
        left_aligned = t.inverse() * left.vertices()
        w02 = osut.width(left_aligned)
        h02 = osut.height(left_aligned)
        self.assertAlmostEqual(w02, 2.24, places=2)
        self.assertAlmostEqual(h02, h2, places=2) # 'height' based on Y-axis (vs Z-axis)

        w3 = osut.width(right)
        h3 = osut.height(right)
        self.assertAlmostEqual(w3, 1.48, places=2)
        self.assertAlmostEqual(h3, h2) # same as left
        t = openstudio.Transformation.alignFace(right.vertices())
        right_aligned = t.inverse() * right.vertices()
        w03 = osut.width(right_aligned)
        h03 = osut.height(right_aligned)
        self.assertAlmostEqual(w03, w02, places=2) # same as aligned left
        self.assertAlmostEqual(h03, h02, places=2) # same as aligned left

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # What if wall vertex sequences were no longer ULC (e.g. URC)?
        vec = openstudio.Point3dVector()
        vec.append(tilted.vertices()[3])
        vec.append(tilted.vertices()[0])
        vec.append(tilted.vertices()[1])
        vec.append(tilted.vertices()[2])
        self.assertTrue(tilted.setVertices(vec))
        self.assertAlmostEqual(osut.width(tilted), w1, places=2)  # same result
        self.assertAlmostEqual(osut.height(tilted), h1, places=2) # same result

        model.save("./tests/files/osms/out/seb_ext4.osm", True)

        del model
        self.assertEqual(o.status(), 0)

    def test30_wwr_insertions(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        translator = openstudio.osversion.VersionTranslator()

        path  = openstudio.path("./tests/files/osms/out/seb_ext2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()
        wwr   = 0.10

        # Fetch "Openarea Wall 3".
        wall3 = model.getSurfaceByName("Openarea 1 Wall 3")
        self.assertTrue(wall3)
        wall3 = wall3.get()
        area  = wall3.grossArea() * wwr

        # Fetch "Openarea Wall 4".
        wall4 = model.getSurfaceByName("Openarea 1 Wall 4")
        self.assertTrue(wall4)
        wall4 = wall4.get()

        # Fetch transform if wall3 vertices were to 'align'.
        tr      = openstudio.Transformation.alignFace(wall3.vertices())
        a_wall3 = tr.inverse() * wall3.vertices()
        ymax    = max([pt.y() for pt in a_wall3])
        xmax    = max([pt.x() for pt in a_wall3])
        xmid    = xmax / 2 # centreline

        # Fetch 'head'/'sill' heights of nearby "Sub Surface 1".
        sub1 = model.getSubSurfaceByName("Sub Surface 1")
        self.assertTrue(sub1)
        sub1 = sub1.get()

        sub1_min = min([pt.z() for pt in sub1.vertices()])
        sub1_max = max([pt.z() for pt in sub1.vertices()])

        # Add 2x window strips, each representing 10% WWR of wall3 (20% total).
        #   - 1x constrained to sub1 'head' & 'sill'
        #   - 1x contrained only to 2nd 'sill' height
        wwr1         = {}
        wwr1["id"   ] = "OA1 W3 wwr1|10"
        wwr1["ratio"] = 0.1
        wwr1["head" ] = sub1_max
        wwr1["sill" ] = sub1_min

        wwr2         = {}
        wwr2["id"   ] = "OA1 W3 wwr2|10"
        wwr2["ratio"] = 0.1
        wwr2["sill" ] = wwr1["head"] + 0.1

        sbz = [wwr1, wwr2]
        self.assertTrue(osut.addSubs(wall3, sbz))
        self.assertEqual(o.status(), 0)
        sbz = wall3.subSurfaces()
        self.assertEqual(len(sbz), 2)

        for sb in sbz:
            self.assertAlmostEqual(sb.grossArea(), area, places=2)
            sb_sill = min([pt.z() for pt in sb.vertices()])
            sb_head = max([pt.z() for pt in sb.vertices()])

            if "wwr1" in sb.nameString():
                self.assertAlmostEqual(sb_sill, wwr1["sill"], places=2)
                self.assertAlmostEqual(sb_head, wwr1["head"], places=2)
                self.assertNotEqual(sb_head, HEAD)
            else:
                self.assertAlmostEqual(sb_sill, wwr2["sill"], places=2)
                self.assertAlmostEqual(sb_head, HEAD, places=2) # defaulted

        self.assertAlmostEqual(wall3.windowToWallRatio(), wwr * 2, places=2)

        # Fetch transform if wall4 vertices were to 'align'.
        tr      = openstudio.Transformation.alignFace(wall4.vertices())
        a_wall4 = tr.inverse() * wall4.vertices()
        ymax    = max([pt.y() for pt in a_wall4])
        xmax    = max([pt.x() for pt in a_wall4])
        xmid    = xmax / 2 # centreline

        # Add 4x sub surfaces (with frame & dividers) to wall4:
        #   1. w1: 0.8m-wide opening (head defaulted to HEAD, sill @0m)
        #   2. w2: 0.4m-wide sidelite, to the immediate right of w2 (HEAD, sill@0)
        #   3. t1: 0.8m-wide transom above w1 (0.4m in height)
        #   4. t2: 0.5m-wide transom above w2 (0.4m in height)
        #
        # All 4x sub surfaces are intended to share frame edges (once frame &
        # divider frame widths are taken into account). Postulating a 50mm frame,
        # meaning 100mm between w1, w2, t1 vs t2 vertices. In addition, all 4x
        # openings (grouped together) should align towards the left of wall4,
        # leaving a 200mm gap between the left vertical wall edge and the left
        # frame jamb edge of w1 & t1. First initialize Frame & Divider object.
        gap    = 0.200
        frame  = 0.050
        frames = 2 * frame

        fd = openstudio.model.WindowPropertyFrameAndDivider(model)
        self.assertTrue(fd.setFrameWidth(frame))
        self.assertTrue(fd.setFrameConductance(2.500))

        w1              = {}
        w1["id"        ] = "OA1 W4 w1"
        w1["frame"     ] = fd
        w1["width"     ] = 0.8
        w1["head"      ] = HEAD
        w1["sill"      ] = 0.005 + frame # to avoid generating a warning
        w1["centreline"] = -xmid + gap + frame + w1["width"]/2

        w2              = {}
        w2["id"        ] = "OA1 W4 w2"
        w2["frame"     ] = fd
        w2["width"     ] = w1["width"     ]/2
        w2["head"      ] = w1["head"      ]
        w2["sill"      ] = w1["sill"      ]
        w2["centreline"] = w1["centreline"] + w1["width"]/2 + frames + w2["width"]/2

        t1              = {}
        t1["id"        ] = "OA1 W4 t1"
        t1["frame"     ] = fd
        t1["width"     ] = w1["width"     ]
        t1["height"    ] = w2["width"     ]
        t1["sill"      ] = w1["head"      ] + frames
        t1["centreline"] = w1["centreline"]

        t2              = {}
        t2["id"        ] = "OA1 W4 t2"
        t2["frame"     ] = fd
        t2["width"     ] = w2["width"     ]
        t2["height"    ] = t1["height"    ]
        t2["sill"      ] = t1["sill"      ]
        t2["centreline"] = w2["centreline"]

        sbz = [w1, w2, t1, t2]
        self.assertTrue(osut.addSubs(wall4, sbz))
        if o.status() > 0: print(o.logs())
        self.assertEqual(o.status(), 0)

        # Add another 5x (frame&divider-enabled) fixed windows, from either
        # left- or right-corner of base surfaces. Fetch "Openarea Wall 6".
        wall6 = model.getSurfaceByName("Openarea 1 Wall 6")
        self.assertTrue(wall6)
        wall6 = wall6.get()

        # Fetch "Openarea Wall 7".
        wall7 = model.getSurfaceByName("Openarea 1 Wall 7")
        self.assertTrue(wall7)
        wall7 = wall7.get()

        # Fetch 'head'/'sill' heights of nearby "Sub Surface 6".
        sub6 = model.getSubSurfaceByName("Sub Surface 6")
        self.assertTrue(sub6)
        sub6 = sub6.get()

        sub6_min = min([pt.z() for pt in sub6.vertices()])
        sub6_max = max([pt.z() for pt in sub6.vertices()])

        # 1x Array of 3x windows, 8" from the left corner of wall6.
        a6             = {}
        a6["id"      ] = "OA1 W6 a6"
        a6["count"   ] = 3
        a6["frame"   ] = fd
        a6["head"    ] = sub6_max
        a6["sill"    ] = sub6_min
        a6["width"   ] = a6["head" ] - a6["sill"]
        a6["offset"  ] = a6["width"] + gap
        a6["l_buffer"] = gap

        self.assertTrue(osut.addSubs(wall6, a6))

        # 1x Array of 2x square windows, 8" from the right corner of wall7.
        a7             = {}
        a7["id"      ] = "OA1 W6 a7"
        a7["count"   ] = 2
        a7["frame"   ] = fd
        a7["head"    ] = sub6_max
        a7["sill"    ] = sub6_min
        a7["width"   ] = a7["head" ] - a7["sill"]
        a7["offset"  ] = a7["width"] + gap
        a7["r_buffer"] = gap

        self.assertTrue(osut.addSubs(wall7, a7))

        model.save("./tests/files/osms/out/seb_ext3.osm", True)

        # Fetch a (flat) plenum roof surface, and add a single skylight.
        ide  = "Level 0 Open area 1 ceiling Plenum RoofCeiling"
        ruf1 = model.getSurfaceByName(ide)
        self.assertTrue(ruf1)
        ruf1 = ruf1.get()

        construction = [cc for cc in model.getConstructions() if cc.isFenestration()]
        self.assertEqual(len(construction), 1)
        construction = construction[0]

        a8            = {}
        a8["id"      ] = "ruf skylight"
        a8["type"    ] = "Skylight"
        a8["count"   ] = 1
        a8["width"   ] = 1.2
        a8["height"  ] = 1.2
        a8["assembly"] = construction

        self.assertTrue(osut.addSubs(ruf1, a8))

        # The plenum roof inherits a single skylight (without any skylight well).
        # See "checks generated skylight wells": "seb_ext3a" vs "seb_sky"
        #   - more sensible alignment of skylight(s) wrt to roof geometry
        #   - automated skylight well generation
        model.save("./tests/files/osms/out/seb_ext3a.osm", True)

        del model
        self.assertEqual(o.status(), 0)

    def test31_convexity(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(INF), INF)
        self.assertEqual(o.level(), INF)

        translator = openstudio.osversion.VersionTranslator()
        version = int("".join(openstudio.openStudioVersion().split(".")))

        # Successful test.
        path  = openstudio.path("./tests/files/osms/in/smalloffice.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()
        core  = None
        attic = None

        for space in model.getSpaces():
            ide = space.nameString()

            if version >= 350:
                self.assertTrue(space.isVolumeAutocalculated)
                self.assertTrue(space.isCeilingHeightAutocalculated)
                self.assertTrue(space.isFloorAreaDefaulted)
                self.assertTrue(space.isFloorAreaAutocalculated)

            if ide == "Attic":
                self.assertFalse(space.partofTotalFloorArea())
                attic = space
                continue

            # Isolate core as being part of the total floor area (occupied zone)
            # and not having sidelighting.
            self.assertTrue(space.partofTotalFloorArea())
            if space.exteriorWallArea() > TOL: continue

            core = space

        srfs = core.surfaces()
        core_floor   = [s for s in srfs if s.surfaceType() == "Floor"]
        core_ceiling = [s for s in srfs if s.surfaceType() == "RoofCeiling"]

        self.assertEqual(len(core_floor), 1)
        self.assertEqual(len(core_ceiling), 1)
        core_floor   = core_floor[0]
        core_ceiling = core_ceiling[0]
        attic_floor  = core_ceiling.adjacentSurface()
        self.assertTrue(attic_floor)
        attic_floor  = attic_floor.get()

        self.assertTrue("Core" in core.nameString())
        # 22.69, 13.46, 0,                        !- X,Y,Z Vertex 1 {m}
        # 22.69,  5.00, 0,                        !- X,Y,Z Vertex 2 {m}
        #  5.00,  5.00, 0,                        !- X,Y,Z Vertex 3 {m}
        #  5.00, 13.46, 0;                        !- X,Y,Z Vertex 4 {m}
        # -----,------,--
        # 17.69 x 8.46 = 149.66 m2
        self.assertAlmostEqual(core.floorArea(), 149.66, places=2)
        core_volume = core.floorArea() * 3.05
        self.assertAlmostEqual(core_volume, core.volume(), places=2)

        # OpenStudio versions prior to v351 overestimate attic volume
        # (798.41 m3), as they resort to floor area x height.
        if version < 350:
            self.assertAlmostEqual(attic.volume(), 798.41, places=2)
        else:
            self.assertAlmostEqual(attic.volume(), 720.19, places=2)

        # Attic floor area includes overhang 'floor' surfaces (i.e. soffits).
        self.assertAlmostEqual(attic.floorArea(), 567.98, places=2)
        self.assertTrue(osut.poly(core_floor, True))   # convex
        self.assertTrue(osut.poly(core_ceiling, True)) # convex
        self.assertTrue(osut.poly(attic_floor, True))  # convex
        self.assertEqual(o.status(), 0)

        # Insert new 'mini' (2m x 2m) floor/ceiling at the centre of the
        # existing core space. Initial insertion resorting strictly to adding
        # leader lines from the initial core floor/ceiling vertices to the new
        # 'mini' floor/ceiling.
        centre = openstudio.getCentroid(core_floor.vertices())
        self.assertTrue(centre)
        centre = centre.get()
        mini_w = centre.x() - 1 # 12.845
        mini_e = centre.x() + 1 # 14.845
        mini_n = centre.y() + 1 # 10.230
        mini_s = centre.y() - 1 #  8.230

        mini_floor_vtx = openstudio.Point3dVector()
        mini_floor_vtx.append(openstudio.Point3d(mini_e, mini_n, 0))
        mini_floor_vtx.append(openstudio.Point3d(mini_e, mini_s, 0))
        mini_floor_vtx.append(openstudio.Point3d(mini_w, mini_s, 0))
        mini_floor_vtx.append(openstudio.Point3d(mini_w, mini_n, 0))
        mini_floor = openstudio.model.Surface(mini_floor_vtx, model)
        mini_floor.setName("Mini floor")
        self.assertEqual(mini_floor.outsideBoundaryCondition(), "Ground")
        self.assertTrue(mini_floor.setSpace(core))

        mini_ceiling_vtx = openstudio.Point3dVector()
        mini_ceiling_vtx.append(openstudio.Point3d(mini_w, mini_n, 3.05))
        mini_ceiling_vtx.append(openstudio.Point3d(mini_w, mini_s, 3.05))
        mini_ceiling_vtx.append(openstudio.Point3d(mini_e, mini_s, 3.05))
        mini_ceiling_vtx.append(openstudio.Point3d(mini_e, mini_n, 3.05))
        mini_ceiling = openstudio.model.Surface(mini_ceiling_vtx, model)
        mini_ceiling.setName("Mini ceiling")
        self.assertTrue(mini_ceiling.setSpace(core))

        mini_attic_vtx = openstudio.Point3dVector()
        mini_attic_vtx.append(openstudio.Point3d(mini_e, mini_n, 3.05))
        mini_attic_vtx.append(openstudio.Point3d(mini_e, mini_s, 3.05))
        mini_attic_vtx.append(openstudio.Point3d(mini_w, mini_s, 3.05))
        mini_attic_vtx.append(openstudio.Point3d(mini_w, mini_n, 3.05))
        mini_attic = openstudio.model.Surface(mini_attic_vtx, model)
        mini_attic.setName("Mini attic")
        self.assertTrue(mini_attic.setSpace(attic))

        self.assertTrue(mini_ceiling.setAdjacentSurface(mini_attic))
        self.assertEqual(mini_ceiling.outsideBoundaryCondition(), "Surface")
        self.assertEqual(mini_attic.outsideBoundaryCondition(), "Surface")
        self.assertEqual(mini_ceiling.outsideBoundaryCondition(), "Surface")
        self.assertEqual(mini_ceiling.outsideBoundaryCondition(), "Surface")
        self.assertTrue(mini_ceiling.adjacentSurface())
        self.assertTrue(mini_attic.adjacentSurface())
        self.assertEqual(mini_ceiling.adjacentSurface().get(), mini_attic)
        self.assertEqual(mini_attic.adjacentSurface().get(), mini_ceiling)

        # Reset existing core floor, core ceiling & attic floor vertices to
        # accommodate 3x new mini 'holes' (filled in by the 3x new 'mini'
        # surfaces). 'Hole' vertices are defined in the opposite 'winding' of
        # their 'mini' counterparts (e.g. clockwise if the initial vertex
        # sequence is counterclockwise). To ensure valid (core and attic) area
        # & volume calculations (and avoid OpenStudio stdout errors/warnings),
        # append the last vertex of the original surface: each EnergyPlus edge
        # must be referenced (at least) twice (i.e. the 'leader line' between
        # each of the 3x original surfaces and each of the 'mini' holes must
        # be doubled).
        vtx = openstudio.Point3dVector()
        for v in core_floor.vertices(): vtx.append(v)
        vtx.append(mini_floor_vtx[3])
        vtx.append(mini_floor_vtx[2])
        vtx.append(mini_floor_vtx[1])
        vtx.append(mini_floor_vtx[0])
        vtx.append(mini_floor_vtx[3])
        vtx.append(vtx[3])
        self.assertTrue(core_floor.setVertices(vtx))

        vtx = openstudio.Point3dVector()
        for v in core_ceiling.vertices(): vtx.append(v)
        vtx.append(mini_ceiling_vtx[1])
        vtx.append(mini_ceiling_vtx[0])
        vtx.append(mini_ceiling_vtx[3])
        vtx.append(mini_ceiling_vtx[2])
        vtx .append(mini_ceiling_vtx[1])
        vtx.append(vtx[3])
        self.assertTrue(core_ceiling.setVertices(vtx))

        vtx = openstudio.Point3dVector()
        for v in attic_floor.vertices(): vtx.append(v)
        vtx .append(mini_attic_vtx[3])
        vtx.append(mini_attic_vtx[2])
        vtx.append(mini_attic_vtx[1])
        vtx.append(mini_attic_vtx[0])
        vtx.append(mini_attic_vtx[3])
        vtx.append(vtx[3])
        self.assertTrue(attic_floor.setVertices(vtx))

        # Generate (temporary) OSM & IDF:
        model.save("./tests/files/osms/out/miniX.osm", True)

        # ft  = openstudio.energyplus.ForwardTranslator()
        # idf = ft.translateModel(model)
        # idf.save("./tests/files/osms/out/miniX.idf", True)

        # Add 2x skylights to attic.
        attic_south = model.getSurfaceByName("Attic_roof_south")
        self.assertTrue(attic_south)
        attic_south = attic_south.get()

        aligned = osut.poly(attic_south, False, False, True, True, "ulc")
        side    = 1.2
        offset  = side + 1
        head    = osut.height(aligned) - 0.2
        self.assertAlmostEqual(head, 10.16, places=2)

        del model
        self.assertEqual(o.status(), 0)

    def test32_outdoor_roofs(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(INF), INF)
        self.assertEqual(o.level(), INF)
        translator = openstudio.osversion.VersionTranslator()

        path  = openstudio.path("./tests/files/osms/in/5ZoneNoHVAC.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        spaces = {}
        roofs  = {}

        for space in model.getSpaces():
            for s in space.surfaces():
                if s.surfaceType().lower() != "roofceiling": continue
                if s.outsideBoundaryCondition().lower() != "outdoors": continue

                self.assertFalse(space.nameString() in spaces)
                spaces[space.nameString()] = s.nameString()

        self.assertEqual(len(spaces), 5)

        # for key, value in spaces.items(): print(key, value)
        # "Story 1 East Perimeter Space"  "Surface 18"
        # "Story 1 North Perimeter Space" "Surface 12"
        # "Story 1 Core Space"            "Surface 30"
        # "Story 1 South Perimeter Space" "Surface 24"
        # "Story 1 West Perimeter Space"  "Surface 6"

        for space in model.getSpaces():
            rufs = osut.roofs(space)
            self.assertEqual(len(rufs), 1)
            ruf = rufs[0]
            self.assertTrue(isinstance(ruf, openstudio.model.Surface))
            roofs[space.nameString()] = ruf.nameString()

        self.assertEqual(len(roofs), len(spaces))

        for ide, surface in spaces.items():
            self.assertTrue(ide in roofs)
            self.assertEqual(roofs[ide], surface)

        del model

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # CASE 2: None of the occupied spaces have outdoor-facing roofs, yet
        # plenum above has 4 outdoor-facing roofs (each matches a space ceiling).
        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        occupied = []
        spaces   = {}
        roofs    = {}

        for space in model.getSpaces():
            if not space.partofTotalFloorArea(): continue

            occupied.append(space.nameString())

            for s in space.surfaces():
                if s.surfaceType().lower() != "roofceiling": continue
                if s.outsideBoundaryCondition().lower() != "outdoors": continue

                self.assertFalse(space.nameString() in spaces)
                spaces[space.nameString()] = s.nameString()

        self.assertEqual(len(occupied), 4)
        self.assertFalse(spaces)

        for space in model.getSpaces():
            if not space.partofTotalFloorArea(): continue

            rufs = osut.roofs(space)
            self.assertEqual(len(rufs), 1)
            ruf = rufs[0]
            self.assertTrue(isinstance(ruf, openstudio.model.Surface))
            roofs[space.nameString()] = ruf.nameString()

        self.assertEqual(len(roofs), 4)
        self.assertEqual(o.status(), 0)

        for occ in occupied:
            self.assertTrue(occ in roofs)
            self.assertTrue("plenum" in roofs[occ].lower())

        del model
        self.assertEqual(o.status(), 0)

    def test33_leader_line_anchors_inserts(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        translator = openstudio.osversion.VersionTranslator()

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        o0 = openstudio.Point3d( 0, 0, 0)

        # A larger polygon (s0, an upside-down "U"), defined ULC.
        s0 = openstudio.Point3dVector()
        s0.append(openstudio.Point3d( 2, 16, 20))
        s0.append(openstudio.Point3d( 2,  2, 20))
        s0.append(openstudio.Point3d( 8,  2, 20))
        s0.append(openstudio.Point3d( 8, 10, 20))
        s0.append(openstudio.Point3d(16, 10, 20))
        s0.append(openstudio.Point3d(16,  2, 20))
        s0.append(openstudio.Point3d(20,  2, 20))
        s0.append(openstudio.Point3d(20, 16, 20))

        # Polygon s0 entirely encompasses 4x smaller  polygons, s1 to s4.
        s1 = openstudio.Point3dVector()
        s1.append(openstudio.Point3d( 7,  3, 20))
        s1.append(openstudio.Point3d( 7,  7, 20))
        s1.append(openstudio.Point3d( 5,  7, 20))
        s1.append(openstudio.Point3d( 5,  3, 20))

        s2 = openstudio.Point3dVector()
        s2.append(openstudio.Point3d( 3, 11, 20))
        s2.append(openstudio.Point3d(10, 11, 20))
        s2.append(openstudio.Point3d(10, 15, 20))
        s2.append(openstudio.Point3d( 3, 15, 20))

        s3 = openstudio.Point3dVector()
        s3.append(openstudio.Point3d(12, 13, 20))
        s3.append(openstudio.Point3d(16, 11, 20))
        s3.append(openstudio.Point3d(17, 13, 20))
        s3.append(openstudio.Point3d(13, 15, 20))

        s4 = openstudio.Point3dVector()
        s4.append(openstudio.Point3d(19,  3, 20))
        s4.append(openstudio.Point3d(19,  6, 20))
        s4.append(openstudio.Point3d(17,  6, 20))
        s4.append(openstudio.Point3d(17,  3, 20))

        area0 = openstudio.getArea(s0)
        area1 = openstudio.getArea(s1)
        area2 = openstudio.getArea(s2)
        area3 = openstudio.getArea(s3)
        area4 = openstudio.getArea(s4)
        self.assertTrue(area0)
        self.assertTrue(area1)
        self.assertTrue(area2)
        self.assertTrue(area3)
        self.assertTrue(area4)
        area0 = area0.get()
        area1 = area1.get()
        area2 = area2.get()
        area3 = area3.get()
        area4 = area4.get()
        self.assertAlmostEqual(area0, 188, places=2)
        self.assertAlmostEqual(area1, 8, places=2)
        self.assertAlmostEqual(area2, 28, places=2)
        self.assertAlmostEqual(area3, 10, places=2)
        self.assertAlmostEqual(area4, 6, places=2)

        # Side tests: index of nearest/farthest box coordinate to grid origin.
        self.assertEqual(osut.nearest(s1), 3)
        self.assertEqual(osut.nearest(s2), 0)
        self.assertEqual(osut.nearest(s3), 0)
        self.assertEqual(osut.nearest(s4), 3)
        self.assertEqual(osut.farthest(s1), 1)
        self.assertEqual(osut.farthest(s2), 2)
        self.assertEqual(osut.farthest(s3), 2)
        self.assertEqual(osut.farthest(s4), 1)

        self.assertEqual(osut.nearest(s1, o0), 3)
        self.assertEqual(osut.nearest(s2, o0), 0)
        self.assertEqual(osut.nearest(s3, o0), 0)
        self.assertEqual(osut.nearest(s4, o0), 3)
        self.assertEqual(osut.farthest(s1, o0), 1)
        self.assertEqual(osut.farthest(s2, o0), 2)
        self.assertEqual(osut.farthest(s3, o0), 2)
        self.assertEqual(osut.farthest(s4, o0), 1)

        # Box-specific grid instructions, i.e. 'subsets'.
        set = []
        set.append(dict(box=s1, rows=1, cols=2, w0=1.4, d0=1.4, dX=0.2, dY=0.2))
        set.append(dict(box=s2, rows=2, cols=3, w0=1.4, d0=1.4, dX=0.2, dY=0.2))
        set.append(dict(box=s3, rows=1, cols=1, w0=2.6, d0=1.4, dX=0.2, dY=0.2))
        set.append(dict(box=s4, rows=1, cols=1, w0=2.6, d0=1.4, dX=0.2, dY=0.2))

        area_s1 = set[0]["rows"] * set[0]["cols"] * set[0]["w0"] * set[0]["d0"]
        area_s2 = set[1]["rows"] * set[1]["cols"] * set[1]["w0"] * set[1]["d0"]
        area_s3 = set[2]["rows"] * set[2]["cols"] * set[2]["w0"] * set[2]["d0"]
        area_s4 = set[3]["rows"] * set[3]["cols"] * set[3]["w0"] * set[3]["d0"]
        area_s  = area_s1 + area_s2 + area_s3 + area_s4
        self.assertAlmostEqual(area_s1, 3.92, places=2)
        self.assertAlmostEqual(area_s2, 11.76, places=2)
        self.assertAlmostEqual(area_s3, 3.64, places=2)
        self.assertAlmostEqual(area_s4, 3.64, places=2)
        self.assertAlmostEqual(area_s, 22.96, places=2)

        # Side test.
        ld1 = openstudio.Point3d(18,  0, 0)
        ld2 = openstudio.Point3d( 8,  3, 0)
        sg1 = openstudio.Point3d(12, 14, 0)
        sg2 = openstudio.Point3d(12,  6, 0)
        self.assertFalse(osut.lineIntersection([sg1, sg2], [ld1, ld2]))

        # To support multiple polygon inserts within a larger polygon, subset
        # boxes must be first 'aligned' (along a temporary XY plane) in a
        # systematic way to ensure consistent treatment between sequential
        # methods, e.g.:
        t = openstudio.Transformation.alignFace(s0)
        s00 = t.inverse() * s0
        s01 = t.inverse() * s4

        for pt in s01: self.assertTrue(osut.isPointWithinPolygon(pt, s00, True))

        # Reiterating that if one simply 'aligns' an already flat surface, what
        # ends up being considered a BottomLeftCorner (BLC) vs ULC is contingent
        # on how OpenStudio's 'alignFace' rotates the original surface. Although
        # 'alignFace' operates in a systematic and reliable way, its output
        # isn't always intuitive when dealing with flat surfaces. Here, instead
        # of the original upside-down "U" shape of s0, an aligned s00 presents a
        # conventional "U" shape (i.e. 180° rotation).
        #
        # for sv in s00: print(sv)
        #   [18,  0, 0] ... vs [ 2, 16, 20]
        #   [18, 14, 0] ... vs [ 2,  2, 20]
        #   [12, 14, 0] ... vs [ 8,  2, 20]
        #   [12,  6, 0] ... vs [ 8, 10, 20]
        #   [ 4,  6, 0] ... vs [16, 10, 20]
        #   [ 4, 14, 0] ... vs [16,  2, 20]
        #   [ 0, 14, 0] ... vs [20,  2, 20]
        #   [ 0,  0, 0] ... vs [20, 16, 20]

    def test34_generated_skylight_wells(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

        version = int("".join(openstudio.openStudioVersion().split(".")))
        translator = openstudio.osversion.VersionTranslator()

        path  = openstudio.path("./tests/files/osms/in/smalloffice.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        srr = 0.05
        core  = []
        attic = []

        # Fetch default construction sets.
        oID = "90.1-2010 - SmOffice - ASHRAE 169-2013-3B" # building
        aID = "90.1-2010 -  - Attic - ASHRAE 169-2013-3B" # attic spacetype level
        o_set = model.getDefaultConstructionSetByName(oID)
        a_set = model.getDefaultConstructionSetByName(oID)
        self.assertTrue(o_set)
        self.assertTrue(a_set)
        o_set = o_set.get()
        a_set = a_set.get()
        self.assertTrue(o_set.defaultInteriorSurfaceConstructions())
        self.assertTrue(a_set.defaultInteriorSurfaceConstructions())
        io_set = o_set.defaultInteriorSurfaceConstructions().get()
        ia_set = a_set.defaultInteriorSurfaceConstructions().get()
        self.assertTrue(io_set.wallConstruction())
        self.assertTrue(ia_set.wallConstruction())
        io_wall = io_set.wallConstruction().get().to_LayeredConstruction()
        ia_wall = ia_set.wallConstruction().get().to_LayeredConstruction()
        self.assertTrue(io_wall)
        self.assertTrue(ia_wall)
        io_wall = io_wall.get()
        ia_wall = ia_wall.get()
        self.assertEqual(io_wall, ia_wall) # 2x drywall layers
        self.assertAlmostEqual(osut.rsi(io_wall, 0.150), 0.31, places=2)

        for space in model.getSpaces():
            ide = space.nameString()

            if not space.partofTotalFloorArea():
                attic.append(space)
                continue

            sidelit = osut.isDaylit(space, True, False)
            toplit  = osut.isDaylit(space, False)
            self.assertFalse(toplit)

            if "Perimeter" in ide:
                self.assertTrue(sidelit)
            elif "Core" in ide:
                self.assertFalse(sidelit)
                core.append(space)

        self.assertEqual(len(core), 1)
        self.assertEqual(len(attic), 1)
        core  = core[0]
        attic = attic[0]
        self.assertFalse(osut.arePlenums(attic))
        self.assertTrue(osut.isUnconditioned(attic))

        # TOTAL attic roof area, including overhangs.
        roofs  = osut.facets(attic, "Outdoors", "RoofCeiling")
        rufs   = osut.roofs(model.getSpaces())
        total1 = sum([roof.grossArea() for roof in roofs])
        total2 = sum([roof.grossArea() for roof in rufs])
        self.assertAlmostEqual(total1, total2, places=2)
        self.assertAlmostEqual(total2, 598.76, places=2)

        # "GROSS ROOF AREA" (GRA), as per 90.1/NECB - excludes overhangs (60m2)
        gra1 = osut.grossRoofArea(model.getSpaces())
        self.assertAlmostEqual(gra1, 538.86, places=2)

        # Unless model geometry is too granular (e.g. finely tessellated), the
        # method 'addSkyLights' generates skylight/wells achieving user-required
        # skylight-to-roof ratios (SRR%). The distinction between TOTAL vs GRA
        # is obviously key for SRR% calculations (i.e. denominators).

        # 2x test CASES:
        #   1. UNCONDITIONED (attic, as is)
        #   2. INDIRECTLY-CONDITIONED (e.g. plenum)
        #
        # For testing purposes, only the core zone here is targeted for skylight
        # wells. Context: NECBs and 90.1 require separate SRR% calculations for
        # differently conditioned spaces (SEMI-CONDITIONED vs CONDITIONED).
        # Consider this as practice - see 'addSkyLights' doc.

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # CASE 1:
        # Retrieve core GRA. As with overhangs, only the attic roof 'sections'
        # directly-above the core are retained for SRR% calculations. Here, the
        # GRA is substantially lower (than previously-calculated gra1). For now,
        # calculated GRA is only valid BEFORE adding skylight wells.
        gra_attic = osut.grossRoofArea(core)
        self.assertAlmostEqual(gra_attic, 157.77, places=2)

        # The method returns the GRA, calculated BEFORE adding skylights/wells.
        rm2 = osut.addSkyLights(core, dict(srr=srr))
        self.assertAlmostEqual(rm2, gra_attic, places=2)

        # New core skylight areas. Successfully achieved SRR%.
        core_skies = osut.facets(core, "Outdoors", "Skylight")
        sky_area1  = sum([sk.grossArea() for sk in core_skies])
        self.assertAlmostEqual(round(sky_area1, 2), 7.89)
        ratio = sky_area1 / rm2
        self.assertAlmostEqual(round(ratio, 2), srr)

        # Reset attic default construction set for insulated interzone walls.
        opts = dict(type="partition", uo=0.3)
        construction = osut.genConstruction(model, opts)
        self.assertAlmostEqual(osut.rsi(construction, 0.150), 1/0.3, places=2)
        self.assertTrue(ia_set.setWallConstruction(construction))
        if o.logs(): print(o.logs())

        model.save("./tests/files/osms/out/office_attic.osm", True)

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # Side test/comment: Why is it necessary to have 'addSkylights' return
        # gross roof area (see 'rm2' above)?
        #
        # First, retrieving (newly-added) core roofs (i.e. skylight base
        # surfaces).
        rfs1 = osut.facets(core, "Outdoors", "RoofCeiling")
        tot1 = sum([sk.grossArea() for sk in rfs1])
        net  = sum([sk.netArea()   for sk in rfs1])
        self.assertEqual(len(rfs1), 4)
        self.assertAlmostEqual(tot1, 9.06, places=2) # 4x 2.265 m2
        self.assertAlmostEqual(tot1 - net, sky_area1, places=2)

        # In absence of skylight wells (more importantly, in absence of leader
        # lines anchoring skylight base surfaces), OSut's 'roofs' &
        # 'grossRoofArea' report not only on newly-added base surfaces (or
        # their areas), but also overalpping areas of attic roofs above.
        # Unfortunately, these become unreliable with newly-added skylight wells.
        rfs2 = osut.roofs(core)
        tot2 = sum([sk.grossArea() for sk in rfs2])
        self.assertAlmostEqual(tot2, tot1, places=2)
        self.assertAlmostEqual(tot2, osut.grossRoofArea(core), places=2)

        # Fortunately, the addition of leader lines does not affect how
        # OpenStudio reports surface areas.
        rfs3 = osut.facets(attic, "Outdoors", "RoofCeiling")
        tot3 = sum([sk.grossArea() for sk in rfs3])
        self.assertAlmostEqual(tot3 + tot2, total2, places=2) # 598.76

        # However, as discussed elsewhere (see 'addSkylights' doctring and
        # inline comments), these otherwise valid areas are often overestimated
        # for SRR% calculations (e.g. when overhangs and soffits are explicitely
        # modelled). It is for this reason 'addSkylights' reports gross roof
        # area BEFORE adding skylight wells. For higher-level applications
        # relying on 'addSkylights' (e.g. an OpenStudio measure), it is better
        # to store returned gross roof areas for subsequent reporting purposes.

        # Deeper dive: Why are OSut's 'roofs' and 'grossRoofArea' unreliable
        # with leader lines? Both rely on OSut's 'overlapping', itself relying
        # on OpenStudio's 'join' and 'intersect': if neither are successful in
        # joining (or intersecting) 2x polygons (e.g. attic roof vs cast core
        # ceiling), there can be no identifiable overlap. In such cases, both
        # 'roofs' and 'grossRoofArea' ignore overlapping attic roofs. A demo:
        roof_north   = model.getSurfaceByName("Attic_roof_north")
        core_ceiling = model.getSurfaceByName("Core_ZN_ceiling")
        self.assertTrue(roof_north)
        self.assertTrue(core_ceiling)
        roof_north   = roof_north.get()
        core_ceiling = core_ceiling.get()

        t  = openstudio.Transformation.alignFace(roof_north.vertices())
        up = openstudio.Point3d(0,0,1) - openstudio.Point3d(0,0,0)

        a_roof_north   = t.inverse() * roof_north.vertices()
        a_core_ceiling = t.inverse() * core_ceiling.vertices()
        c_core_ceiling = osut.cast(a_core_ceiling, a_roof_north, up)

        north_m2   = openstudio.getArea(a_roof_north)
        ceiling_m2 = openstudio.getArea(c_core_ceiling)
        self.assertTrue(north_m2)
        self.assertTrue(ceiling_m2)
        self.assertAlmostEqual(north_m2.get(), 192.98, places=2)
        self.assertAlmostEqual(ceiling_m2.get(), 133.81, places=2)

        # So far so good. Ensure clockwise winding.
        a_roof_north   = list(a_roof_north)
        c_core_ceiling = list(c_core_ceiling)
        a_roof_north.reverse()
        c_core_ceiling.reverse()
        self.assertFalse(openstudio.join(a_roof_north, c_core_ceiling, TOL2))
        self.assertFalse(openstudio.intersect(a_roof_north, c_core_ceiling, TOL))

        # A future revision of OSut's 'roofs' and 'grossRoofArea' would require:
        # - a new method identifying leader lines amongst surface vertices
        # - a new method identifying surface cutouts amongst surface vertices
        # - a method to prune both leader lines and cutouts from surface vertices
        # - have 'roofs' & 'grossRoofArea' rely on the remaining outer vertices
        #   ... @todo?
        self.assertEqual(o.status(), 0)
        del model

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # CASE 2:
        path  = openstudio.path("./tests/files/osms/in/smalloffice.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        core  = model.getSpaceByName("Core_ZN")
        attic = model.getSpaceByName("Attic")
        self.assertTrue(core)
        self.assertTrue(attic)
        core  = core.get()
        attic = attic.get()

        # Tag attic as an INDIRECTLY-CONDITIONED space.
        key = "indirectlyconditioned"
        val = core.nameString()
        self.assertTrue(attic.additionalProperties().setFeature(key, val))
        self.assertFalse(osut.arePlenums(attic))
        self.assertFalse(osut.isUnconditioned(attic))
        self.assertAlmostEqual(osut.setpoints(attic)["heating"], 21.11, places=2)
        self.assertAlmostEqual(osut.setpoints(attic)["cooling"], 23.89, places=2)

        # Here, GRA includes ALL plenum roof surfaces (not just vertically-cast
        # roof areas onto the core ceiling). More roof surfaces == greater
        # skylight areas to meet the SRR% of 5%.
        gra_plenum = osut.grossRoofArea(core)
        self.assertAlmostEqual(gra_plenum, total1, places=2)

        rm2 = osut.addSkyLights(core, dict(srr=srr))
        if o.logs(): print(o.logs())
        self.assertAlmostEqual(rm2, total1, places=2)

        # The total skylight area is greater than in CASE 1. Nonetheless, the
        # method is able to meet the requested SRR 5%. This may not be
        # achievable in other circumstances, given the constrained roof/core
        # overlap. Although a plenum vastly larger than the room(s) it serves is
        # rare, it remains certainly problematic for the application of the
        # Canadian NECB reference building skylight requirements.
        core_skies = osut.facets(core, "Outdoors", "Skylight")
        sky_area2  = sum([sk.grossArea() for sk in core_skies])
        self.assertAlmostEqual(sky_area2, 29.94, places=2)
        ratio2     = sky_area2 / rm2
        self.assertAlmostEqual(ratio2, srr, places=2)

        model.save("./tests/files/osms/out/office_plenum.osm", True)

        self.assertEqual(o.status(), 0)
        del model

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # CASE 2b:
        path  = openstudio.path("./tests/files/osms/in/smalloffice.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        core  = model.getSpaceByName("Core_ZN")
        attic = model.getSpaceByName("Attic")
        self.assertTrue(core)
        self.assertTrue(attic)
        core  = core.get()
        attic = attic.get()

        # Again, tagging attic as an INDIRECTLY-CONDITIONED space.
        key = "indirectlyconditioned"
        val = core.nameString()
        self.assertTrue(attic.additionalProperties().setFeature(key, val))
        self.assertFalse(osut.arePlenums(attic))
        self.assertFalse(osut.isUnconditioned(attic))
        self.assertAlmostEqual(osut.setpoints(attic)["heating"], 21.11, places=2)
        self.assertAlmostEqual(osut.setpoints(attic)["cooling"], 23.89, places=2)

        gra_plenum = osut.grossRoofArea(core)
        self.assertAlmostEqual(gra_plenum, total1, places=2)

        # Conflicting argument case: Here, skylight wells must traverse plenums
        # (in this context, "plenum" is an all encompassing keyword for any
        # INDIRECTLY-CONDITIONED, unoccupied space). Yet by passing option
        # "plenum: False", the method is instructed to skip "plenum" skylight
        # wells altogether.
        rm2 = osut.addSkyLights(core, dict(srr=srr, plenum=False))
        self.assertTrue(o.is_warn())
        self.assertEqual(len(o.logs()), 1)
        msg = o.logs()[0]["message"]
        self.assertTrue("Empty 'subsets (3)' (osut.addSkyLights)" in msg)
        self.assertAlmostEqual(rm2, total1, places=2)

        core_skies = osut.facets(core, "Outdoors", "Skylight")
        sky_area2  = sum([sk.grossArea() for sk in core_skies])
        self.assertAlmostEqual(sky_area2, 0.00, places=2)
        self.assertEqual(o.clean(), DBG)

        self.assertEqual(o.status(), 0)
        del model

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        # SEB case (flat ceiling plenum).
        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        entry   = model.getSpaceByName("Entry way 1")
        office  = model.getSpaceByName("Small office 1")
        open    = model.getSpaceByName("Open area 1")
        utility = model.getSpaceByName("Utility 1")
        plenum  = model.getSpaceByName("Level 0 Ceiling Plenum")
        self.assertTrue(entry)
        self.assertTrue(office)
        self.assertTrue(open)
        self.assertTrue(utility)
        self.assertTrue(plenum)
        entry   = entry.get()
        office  = office.get()
        open    = open.get()
        utility = utility.get()
        plenum  = plenum.get()
        self.assertFalse(plenum.partofTotalFloorArea())
        self.assertFalse(osut.isUnconditioned(plenum))

        # TOTAL plenum roof area (4x surfaces), no overhangs.
        roofs = osut.facets(plenum, "Outdoors", "RoofCeiling")
        total = sum([ruf.grossArea() for ruf in roofs])
        self.assertAlmostEqual(total, 82.21, places=2)

        # A single plenum above all 4 occupied rooms. Reports same GRA.
        gra_seb1 = osut.grossRoofArea(model.getSpaces())
        gra_seb2 = osut.grossRoofArea(entry)
        self.assertAlmostEqual(gra_seb1, gra_seb2, places=2)
        self.assertAlmostEqual(gra_seb1, total, places=2)

        sky_area = srr * total

        # Before adding skylight wells.
        if version >= 350:
            for sp in [plenum, entry, office, open, utility]:
                self.assertTrue(sp.isEnclosedVolume())
                self.assertTrue(sp.isVolumeDefaulted())
                self.assertTrue(sp.isVolumeAutocalculated())
                self.assertGreater(sp.volume(), 0)

                zn = sp.thermalZone()
                self.assertTrue(zn)
                zn = zn.get()
                self.assertTrue(zn.isVolumeDefaulted())
                self.assertTrue(zn.isVolumeAutocalculated())
                self.assertFalse(zn.volume())

        # The method returns the GRA, calculated BEFORE adding skylights/wells.
        rm2 = osut.addSkyLights(model.getSpaces(), dict(area=sky_area))
        if o.logs(): print(o.logs())
        self.assertAlmostEqual(rm2, total, places=2)

        entry_skies   = osut.facets(entry, "Outdoors", "Skylight")
        office_skies  = osut.facets(office, "Outdoors", "Skylight")
        utility_skies = osut.facets(utility, "Outdoors", "Skylight")
        open_skies    = osut.facets(open, "Outdoors", "Skylight")

        self.assertFalse(entry_skies)
        self.assertFalse(office_skies)
        self.assertFalse(utility_skies)
        self.assertEqual(len(open_skies), 1)
        open_sky = open_skies[0]

        skm2 = open_sky.grossArea()
        self.assertAlmostEqual(skm2 / rm2, srr, places=2)

        # Assign construction to new skylights.
        construction = osut.genConstruction(model, dict(type="skylight", uo=2.8))
        self.assertTrue(open_sky.setConstruction(construction))

        # No change after adding skylight wells.
        if version >= 350:
            for sp in [plenum, entry, office, open, utility]:
                self.assertTrue(sp.isEnclosedVolume())
                self.assertTrue(sp.isVolumeDefaulted())
                self.assertTrue(sp.isVolumeAutocalculated())
                self.assertGreater(sp.volume(), 0)

                zn = sp.thermalZone()
                self.assertTrue(zn)
                zn = zn.get()
                self.assertTrue(zn.isVolumeDefaulted())
                self.assertTrue(zn.isVolumeAutocalculated())
                self.assertFalse(zn.volume())

        model.save("./tests/files/osms/out/seb_sky.osm", True)

        self.assertEqual(o.status(), 0)
        del model

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        path  = openstudio.path("./tests/files/osms/in/warehouse.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        for space in model.getSpaces():
            ide = space.nameString()
            if not space.partofTotalFloorArea(): continue

            sidelit = osut.isDaylit(space, True, False)
            toplit  = osut.isDaylit(space, False)
            if "Office"  in ide: self.assertTrue(sidelit)
            if "Storage" in ide: self.assertFalse(sidelit)
            if "Office"  in ide: self.assertFalse(toplit)
            if "Storage" in ide: self.assertTrue(toplit)

        bulk = model.getSpaceByName("Zone3 Bulk Storage")
        fine = model.getSpaceByName("Zone2 Fine Storage")
        self.assertTrue(bulk)
        self.assertTrue(fine)
        bulk = bulk.get()
        fine = fine.get()

        # No overhangs/attics. Calculation of roof area for SRR% is more intuitive.
        gra_bulk = osut.grossRoofArea(bulk)
        gra_fine = osut.grossRoofArea(fine)

        bulk_roof_m2 = sum([ruf.grossArea() for ruf in osut.roofs(bulk)])
        fine_roof_m2 = sum([ruf.grossArea() for ruf in osut.roofs(fine)])
        self.assertAlmostEqual(gra_bulk, bulk_roof_m2, places=2)
        self.assertAlmostEqual(gra_fine, fine_roof_m2, places=2)

        # Initial SSR%.
        bulk_skies = osut.facets(bulk, "Outdoors", "Skylight")
        sky_area1  = sum([sk.grossArea() for sk in bulk_skies])
        ratio1     = sky_area1 / bulk_roof_m2
        self.assertAlmostEqual(sky_area1, 47.57, places=2)
        self.assertAlmostEqual(ratio1, 0.01, places=2)

        srr  = 0.04
        opts = {}
        opts["srr"  ] = srr
        opts["size" ] = 2.4
        opts["clear"] = True
        rm2 = osut.addSkyLights(bulk, opts)

        bulk_skies = osut.facets(bulk, "Outdoors", "Skylight")
        sky_area2  = sum([sk.grossArea() for sk in bulk_skies])
        self.assertAlmostEqual(sky_area2, 128.19, places=2)
        ratio2     = sky_area2 / rm2
        self.assertAlmostEqual(ratio2, srr, places=2)

        model.save("./tests/files/osms/out/warehouse_sky.osm", True)

        self.assertEqual(o.status(), 0)
        del model

    def test35_facet_retrieval(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)

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

        del model

    def test36_slab_generation(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
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
        m = o.logs()[0]["message"]
        self.assertEqual(m, "Invalid 'plate # 4 (index 3)' (osut.genSlab)")
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
        del model

    def test37_roller_shades(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        translator = openstudio.osversion.VersionTranslator()
        version = int("".join(openstudio.openStudioVersion().split(".")))

        path = openstudio.path("./tests/files/osms/out/seb_ext4.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()
        spaces = model.getSpaces()

        slanted = osut.facets(spaces, "Outdoors", "RoofCeiling", ["top", "north"])
        self.assertEqual(len(slanted), 1)
        slanted = slanted[0]
        self.assertEqual(slanted.nameString(), "Openarea slanted roof")
        skylights = slanted.subSurfaces()

        tilted = osut.facets(spaces, "Outdoors", "Wall", "bottom")
        self.assertEqual(len(tilted), 1)
        tilted = tilted[0]
        self.assertEqual(tilted.nameString(), "Openarea tilted wall")
        windows = tilted.subSurfaces()

        # 2x control groups:
        #   - 3x windows as a single control group
        #   - 3x skylight as another single control group
        skies = openstudio.model.SubSurfaceVector()
        wins  = openstudio.model.SubSurfaceVector()
        for sub in skylights: skies.append(sub)
        for sub in windows: wins.append(sub)

        if version < 321:
            self.assertFalse(osut.genShade(skies))
        else:
            self.assertTrue(osut.genShade(skies))
            self.assertTrue(osut.genShade(wins))
            ctls = model.getShadingControls()
            self.assertEqual(len(ctls), 2)

            for ctl in ctls:
                self.assertEqual(ctl.shadingType(), "InteriorShade")
                type = "OnIfHighOutdoorAirTempAndHighSolarOnWindow"
                self.assertEqual(ctl.shadingControlType(), type)
                self.assertTrue(ctl.isControlTypeValueNeedingSetpoint1())
                self.assertTrue(ctl.isControlTypeValueNeedingSetpoint2())
                self.assertTrue(ctl.isControlTypeValueAllowingSchedule())
                self.assertFalse(ctl.isControlTypeValueRequiringSchedule())
                spt1 = ctl.setpoint()
                spt2 = ctl.setpoint2()
                self.assertTrue(spt1)
                self.assertTrue(spt2)
                spt1 = spt1.get()
                spt2 = spt2.get()
                self.assertAlmostEqual(spt1, 18, places=2)
                self.assertAlmostEqual(spt2, 100, places=2)
                self.assertEqual(ctl.multipleSurfaceControlType(), "Group")

                for sub in ctl.subSurfaces():
                    surface = sub.surface()
                    self.assertTrue(surface)
                    surface = surface.get()
                    self.assertTrue(surface in [slanted, tilted])

        model.save("./tests/files/osms/out/seb_ext5.osm", True)

        del model
        self.assertEqual(o.status(), 0)

if __name__ == "__main__":
    unittest.main()
