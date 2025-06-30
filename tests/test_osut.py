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

DBG = osut.CN.DBG
INF = osut.CN.INF
WRN = osut.CN.WRN
ERR = osut.CN.ERR
FTL = osut.CN.FTL
NS  = osut.CN.NS

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

    def test05_construction_thickness(self):
        o = osut.oslg
        v = int("".join(openstudio.openStudioVersion().split(".")))
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.level(), INF)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

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
        if v >= 350:
            self.assertTrue(plenum.isEnclosedVolume())
            self.assertTrue(plenum.isVolumeDefaulted())
            self.assertTrue(plenum.isVolumeAutocalculated())

        if 350 < v < 370:
            self.assertEqual(round(plenum.volume(), 0), 234)
        else:
            self.assertEqual(round(plenum.volume(), 0), 0)


    def test06_insulatingLayer(self):
        o = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)
        # it "checks (opaque) insulating layers within a layered construction" do
        # translator = OpenStudio::OSVersion::VersionTranslator.new
        # expect(mod1.clean!).to eq(DBG)
        #
        # file  = File.join(__dir__, "files/osms/out/seb2.osm")
        # path  = OpenStudio::Path.new(file)
        # model = translator.loadModel(path)
        # expect(model).to_not be_empty
        # model = model.get
        #
        # m  = "OSut::insulatingLayer"
        # m1 = "Invalid 'lc' arg #1 (#{m})"
        #
        # model.getLayeredConstructions.each do |lc|
        #   lyr = mod1.insulatingLayer(lc)
        #   expect(lyr).to be_a(Hash)
        #   expect(lyr).to have_key(:index)
        #   expect(lyr).to have_key(:type )
        #   expect(lyr).to have_key(:r)
        #
        #   if lc.isFenestration
        #     expect(mod1.status).to be_zero
        #     expect(lyr[:index]).to be_nil
        #     expect(lyr[:type ]).to be_nil
        #     expect(lyr[:r    ]).to be_zero
        #     next
        #   end
        #
        #   unless [:standard, :massless].include?(lyr[:type]) # air wall mat
        #     expect(mod1.status).to be_zero
        #     expect(lyr[:index]).to be_nil
        #     expect(lyr[:type ]).to be_nil
        #     expect(lyr[:r    ]).to be_zero
        #     next
        #   end
        #
        #   expect(lyr[:index] < lc.numLayers).to be true
        #
        #   case lc.nameString
        #   when "EXTERIOR-ROOF"
        #     expect(lyr[:index]).to eq(2)
        #     expect(lyr[:r    ]).to be_within(TOL).of(5.08)
        #   when "EXTERIOR-WALL"
        #     expect(lyr[:index]).to eq(2)
        #     expect(lyr[:r    ]).to be_within(TOL).of(1.47)
        #   when "Default interior ceiling"
        #     expect(lyr[:index]).to be_zero
        #     expect(lyr[:r    ]).to be_within(TOL).of(0.12)
        #   when "INTERIOR-WALL"
        #     expect(lyr[:index]).to eq(1)
        #     expect(lyr[:r    ]).to be_within(TOL).of(0.24)
        #   else
        #     expect(lyr[:index]).to be_zero
        #     expect(lyr[:r    ]).to be_within(TOL).of(0.29)
        #   end
        # end
        #
        # lyr = mod1.insulatingLayer(nil)
        # expect(mod1.debug?).to be true
        # expect(lyr[:index]).to be_nil
        # expect(lyr[:type ]).to be_nil
        # expect(lyr[:r    ]).to be_zero
        # expect(mod1.debug?).to be true
        # expect(mod1.logs.size).to eq(1)
        # expect(mod1.logs.first[:message]).to eq(m1)
        #
        # expect(mod1.clean!).to eq(DBG)
        # lyr = mod1.insulatingLayer("")
        # expect(mod1.debug?).to be true
        # expect(lyr[:index]).to be_nil
        # expect(lyr[:type ]).to be_nil
        # expect(lyr[:r    ]).to be_zero
        # expect(mod1.debug?).to be true
        # expect(mod1.logs.size).to eq(1)
        # expect(mod1.logs.first[:message]).to eq(m1)
        #
        # expect(mod1.clean!).to eq(DBG)
        # lyr = mod1.insulatingLayer(model)
        # expect(mod1.debug?).to be true
        # expect(lyr[:index]).to be_nil
        # expect(lyr[:type ]).to be_nil
        # expect(lyr[:r    ]).to be_zero
        # expect(mod1.debug?).to be true
        # expect(mod1.logs.size).to eq(1)
        # expect(mod1.logs.first[:message]).to eq(m1)

    def test07_genConstruction(self):
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

    def test08_genShade(self):
        o  = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)

        translator = openstudio.osversion.VersionTranslator()

        # file   = File.join(__dir__, "files/osms/out/seb_ext4.osm")
        # path   = OpenStudio::Path.new(file)
        # model  = translator.loadModel(path)
        # expect(model).to_not be_empty
        # model  = model.get
        # spaces = model.getSpaces
        #
        # slanted   = mod1.facets(spaces, "Outdoors", "RoofCeiling", [:top, :north])
        # expect(slanted.size).to eq(1)
        # slanted   = slanted.first
        # expect(slanted.nameString).to eq("Openarea slanted roof")
        # skylights = slanted.subSurfaces
        #
        # tilted  = mod1.facets(spaces, "Outdoors", "Wall", :bottom)
        # expect(tilted.size).to eq(1)
        # tilted  = tilted.first
        # expect(tilted.nameString).to eq("Openarea tilted wall")
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
        #   expect(mod1.genShade(skies)).to be false
        #   expect(mod1.status).to be_zero
        # else
        #   expect(mod1.genShade(skies)).to be true
        #   expect(mod1.genShade(wins)).to be true
        #   expect(mod1.status).to be_zero
        #   ctls = model.getShadingControls
        #   expect(ctls.size).to eq(2)
        #
        #   ctls.each do |ctl|
        #     expect(ctl.shadingType).to eq("InteriorShade")
        #     type = "OnIfHighOutdoorAirTempAndHighSolarOnWindow"
        #     expect(ctl.shadingControlType).to eq(type)
        #     expect(ctl.isControlTypeValueNeedingSetpoint1).to be true
        #     expect(ctl.isControlTypeValueNeedingSetpoint2).to be true
        #     expect(ctl.isControlTypeValueAllowingSchedule).to be true
        #     expect(ctl.isControlTypeValueRequiringSchedule).to be false
        #     spt1 = ctl.setpoint
        #     spt2 = ctl.setpoint2
        #     expect(spt1).to_not be_empty
        #     expect(spt2).to_not be_empty
        #     spt1 = spt1.get
        #     spt2 = spt2.get
        #     expect(spt1).to be_within(TOL).of(18)
        #     expect(spt2).to be_within(TOL).of(100)
        #     expect(ctl.multipleSurfaceControlType).to eq("Group")
        #
        #     ctl.subSurfaces.each do |sub|
        #       surface = sub.surface
        #       expect(surface).to_not be_empty
        #       surface = surface.get
        #       expect([slanted, tilted]).to include(surface)
        #     end
        #   end
        # end
        #
        # file = File.join(__dir__, "files/osms/out/seb_ext5.osm")
        # model.save(file, true)

    def test09_internal_mass(self):
        o  = osut.oslg
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

        for space in model.getSpaces():
            name  = space.nameString().lower()
            ratio = None

            if name in ratios:
                ratio = ratios[name]
                sps   = openstudio.model.SpaceVector()
                sps.append(space)
                # if ratio:
                #     self.assertTrue(osut.genMass(sps, ratio))
                # else:
                #     self.assertTrue(osut.genMass(sps))

        # construction = nil
        # material     = nil
        #
        # model.getInternalMasss.each do |m|
        #   d = m.internalMassDefinition
        #   expect(d.designLevelCalculationMethod).to eq("SurfaceArea/Area")
        #
        #   ratio = d.surfaceAreaperSpaceFloorArea
        #   expect(ratio).to_not be_empty
        #   ratio = ratio.get
        #
        #   case ratio
        #   when 0.1
        #     expect(d.nameString).to eq("OSut|InternalMassDefinition|0.10")
        #     expect(m.nameString.downcase).to include("entrance")
        #   when 0.3
        #     expect(d.nameString).to eq("OSut|InternalMassDefinition|0.30")
        #     expect(m.nameString.downcase).to include("lobby")
        #   when 1.0
        #     expect(d.nameString).to eq("OSut|InternalMassDefinition|1.00")
        #     expect(m.nameString.downcase).to include("meeting")
        #   else
        #     expect(d.nameString).to eq("OSut|InternalMassDefinition|2.00")
        #     expect(ratio).to eq(2.0)
        #   end
        #
        #   c = d.construction
        #   expect(c).to_not be_empty
        #   c = c.get.to_Construction
        #   expect(c).to_not be_empty
        #   c = c.get
        #
        #   construction = c if construction.nil?
        #   expect(construction).to eq(c)
        #   expect(c.nameString).to eq("OSut|MASS|Construction")
        #   expect(c.numLayers).to eq(1)
        #
        #   m = c.layers.first
        #
        #   material = m if material.nil?
        #   expect(material).to eq(m)
        del(model)


if __name__ == "__main__":
    unittest.main()
