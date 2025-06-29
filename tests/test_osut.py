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

import openstudio
import unittest
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

    def test05_genConstruction(self):
        m1 = "'specs' list? expecting dict (osut.genConstruction)"
        m2 = "'model' str? expecting Model (osut.genConstruction)"
        o  = osut.oslg
        self.assertEqual(o.status(), 0)
        self.assertEqual(o.level(), INF)
        self.assertEqual(o.reset(DBG), DBG)
        self.assertEqual(o.level(), DBG)
        self.assertEqual(o.status(), 0)
        model = openstudio.model.Model()

        # 1. Unsuccessful try: 2nd argument not a 'dict' (see 'm1').
        self.assertEqual(osut.genConstruction(model, []), None)
        self.assertEqual(o.status(), DBG)
        self.assertEqual(len(o.logs()),1)
        self.assertEqual(o.logs()[0]["level"], DBG)
        self.assertEqual(o.logs()[0]["message"], m1)
        self.assertTrue(o.clean(), DBG)
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)

        # 2. Unsuccessful try: 1st argument not a model (see 'm2').
        self.assertEqual(osut.genConstruction("model", dict()), None)
        self.assertEqual(o.status(), DBG)
        self.assertEqual(len(o.logs()),1)
        self.assertEqual(o.logs()[0]["level"], DBG)
        self.assertTrue(o.logs()[0]["message"], m2)
        self.assertTrue(o.clean(), DBG)
        self.assertFalse(o.logs())
        self.assertEqual(o.status(), 0)

        # 3. Successful try: defaulted specs (2nd argument).
        c = osut.genConstruction(model, dict())
        self.assertEqual(o.status(), 0)
        self.assertFalse(o.logs())
        self.assertTrue(isinstance(c, openstudio.model.Construction))
        self.assertEqual(c.nameString(), "OSut.CON.wall")
        self.assertTrue(c.layers())
        self.assertEqual(len(c.layers()), 2)
        l1 = c.layers()[0]
        l2 = c.layers()[1]
        print(l1)
        print(l2)
        del(model)

        # OS:Construction,
        #   {118a4bad-fe74-4e7e-a2fa-65fe40af04e1}, !- Handle
        #   OSut.CON.wall,                          !- Name
        #   ,                                       !- Surface Rendering Name
        #   {a654be16-2b34-4a85-9a56-0f4cf98e6045}, !- Layer 1
        #   {d2b0c635-bacf-41c1-871f-4e5092e83266}; !- Layer 2


if __name__ == "__main__":
    unittest.main()
