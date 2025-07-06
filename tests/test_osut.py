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
import math
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

        version = int("".join(openstudio.openStudioVersion().split(".")))
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

            self.assertFalse(osut.is_spandrel(s))

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
            self.assertTrue(wall.additionalProperties().setFeature(tag, True))
            self.assertTrue(wall.additionalProperties().hasFeature(tag))
            prop = wall.additionalProperties().getFeatureAsBoolean(tag)
            self.assertTrue(prop)
            self.assertTrue(prop.get())
            self.assertTrue(osut.is_spandrel(wall))

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

    def test18_hvac_airloops(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        msg = "'model' str? expecting Model (osut.has_airLoopsHVAC)"
        version = int("".join(openstudio.openStudioVersion().split(".")))
        translator = openstudio.osversion.VersionTranslator()

        # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- #
        path  = openstudio.path("./tests/files/osms/out/seb2.osm")
        model = translator.loadModel(path)
        self.assertTrue(model)
        model = model.get()

        self.assertEqual(o.clean(), DBG)
        self.assertTrue(osut.has_airLoopsHVAC(model))
        self.assertEqual(o.status(), 0)
        self.assertEqual(osut.has_airLoopsHVAC(""), False)
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
        self.assertFalse(osut.has_airLoopsHVAC(model))
        self.assertEqual(o.status(), 0)
        self.assertEqual(osut.has_airLoopsHVAC(""), False)
        self.assertTrue(o.is_debug())
        self.assertEqual(len(o.logs()), 1)
        self.assertEqual(o.logs()[0]["message"], msg)
        self.assertEqual(o.clean(), DBG)
        del(model)

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
        self.assertEqual(o.clean(), DBG)
        del(model)

if __name__ == "__main__":
    unittest.main()
