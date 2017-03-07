# coding=UTF-8
#
# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from __future__ import (print_function, division, absolute_import,
                        unicode_literals)

import collections
import datetime
import unittest

from defcon import Font

from fontTools.misc.loggingTools import CapturingLogHandler

from glyphsLib import builder
from glyphsLib.classes import GSFont, GSFontMaster, GSInstance, \
    GSCustomParameter, GSGlyph, GSLayer, GSPath, GSNode, GSAnchor, \
    GSComponent, GSAlignmentZone

from glyphsLib.builder import build_style_name, set_custom_params,\
    set_redundant_data, to_ufos, GLYPHS_PREFIX, PUBLIC_PREFIX, draw_paths,\
    set_default_params


class BuildStyleNameTest(unittest.TestCase):
    def _build(self, data, italic):
        return build_style_name(data, 'width', 'weight', 'custom', italic)

    def test_style_regular_weight(self):
        inst = GSInstance()
        self.assertEqual(self._build(inst, False), 'Regular')
        self.assertEqual(self._build(inst, True), 'Italic')
        inst.weight = 'Regular'
        self.assertEqual(
            self._build(inst, True), 'Italic')

    def test_style_nonregular_weight(self):
        inst = GSInstance()
        inst.weight = 'Thin'
        self.assertEqual(
            self._build(inst, False), 'Thin')
        self.assertEqual(
            self._build(inst, True), 'Thin Italic')

    def test_style_nonregular_width(self):
        inst = GSInstance()
        inst.width = 'Condensed'
        self.assertEqual(
            self._build(inst, False), 'Condensed')
        self.assertEqual(
            self._build(inst, True), 'Condensed Italic')
        inst.weight = 'Thin'
        self.assertEqual(
            self._build(inst, False),
            'Condensed Thin')
        self.assertEqual(
            self._build(inst, True),
            'Condensed Thin Italic')


class SetCustomParamsTest(unittest.TestCase):
    def setUp(self):
        self.ufo = Font()

    def test_normalizes_curved_quotes_in_names(self):
        master = GSFontMaster()
        master.customParameters = [GSCustomParameter(name='‘bad’', value=1),
                                   GSCustomParameter(name='“also bad”', value=2)]
        set_custom_params(self.ufo, data=master)
        self.assertIn(GLYPHS_PREFIX + "'bad'", self.ufo.lib)
        self.assertIn(GLYPHS_PREFIX + '"also bad"', self.ufo.lib)

    def test_set_glyphOrder(self):
        set_custom_params(self.ufo, parsed=[('glyphOrder', ['A', 'B'])])
        self.assertEqual(self.ufo.lib[PUBLIC_PREFIX + 'glyphOrder'], ['A', 'B'])

    def test_set_fsSelection_flags(self):
        self.assertEqual(self.ufo.info.openTypeOS2Selection, None)

        set_custom_params(self.ufo, parsed=[('Has WWS Names', False)])
        self.assertEqual(self.ufo.info.openTypeOS2Selection, None)

        set_custom_params(self.ufo, parsed=[('Use Typo Metrics', True)])
        self.assertEqual(self.ufo.info.openTypeOS2Selection, [7])

        self.ufo = Font()
        set_custom_params(self.ufo, parsed=[('Has WWS Names', True),
                                       ('Use Typo Metrics', True)])
        self.assertEqual(self.ufo.info.openTypeOS2Selection, [8, 7])

    def test_underlinePosition(self):
        set_custom_params(self.ufo, parsed=[('underlinePosition', -2)])
        self.assertEqual(self.ufo.info.postscriptUnderlinePosition, -2)

        set_custom_params(self.ufo, parsed=[('underlinePosition', 1)])
        self.assertEqual(self.ufo.info.postscriptUnderlinePosition, 1)

    def test_underlineThickness(self):
        set_custom_params(self.ufo, parsed=[('underlineThickness', 100)])
        self.assertEqual(self.ufo.info.postscriptUnderlineThickness, 100)
        
        set_custom_params(self.ufo, parsed=[('underlineThickness', 0)])
        self.assertEqual(self.ufo.info.postscriptUnderlineThickness, 0)

    def test_set_defaults(self):
        set_default_params(self.ufo)
        self.assertEqual(self.ufo.info.openTypeOS2Type, [3])
        self.assertEqual(self.ufo.info.postscriptUnderlinePosition, -100)
        self.assertEqual(self.ufo.info.postscriptUnderlineThickness, 50)


class SetRedundantDataTest(unittest.TestCase):
    def _run_on_ufo(self, family_name, style_name):
        ufo = Font()
        ufo.info.familyName = family_name
        ufo.info.styleName = style_name
        set_redundant_data(ufo)
        return ufo

    def test_sets_regular_weight_class_for_missing_weight(self):
        reg_ufo = self._run_on_ufo('MyFont', 'Regular')
        italic_ufo = self._run_on_ufo('MyFont', 'Italic')
        self.assertEqual(
            reg_ufo.info.openTypeOS2WeightClass,
            italic_ufo.info.openTypeOS2WeightClass)

    def test_sets_weight_lib_entry_only_nonregular(self):
        reg_ufo = self._run_on_ufo('MyFont', 'Regular')
        italic_ufo = self._run_on_ufo('MyFont', 'Italic')
        thin_ufo = self._run_on_ufo('MyFont', 'Thin')
        self.assertFalse(reg_ufo.lib)
        self.assertFalse(italic_ufo.lib)
        self.assertTrue(thin_ufo.lib)

    def test_sets_width_lib_entry_only_condensed(self):
        reg_ufo = self._run_on_ufo('MyFont', 'Regular')
        italic_ufo = self._run_on_ufo('MyFont', 'Italic')
        cond_ufo = self._run_on_ufo('MyFont', 'Condensed')
        cond_italic_ufo = self._run_on_ufo('MyFont', 'Condensed Italic')
        self.assertFalse(reg_ufo.lib)
        self.assertFalse(italic_ufo.lib)
        self.assertTrue(cond_ufo.lib)
        self.assertTrue(cond_italic_ufo.lib)

    def _run_style_map_names_test(self, args):
        for family, style, expected_family, expected_style in args:
            ufo = self._run_on_ufo(family, style)
            self.assertEqual(ufo.info.styleMapFamilyName, expected_family)
            self.assertEqual(ufo.info.styleMapStyleName, expected_style)

    def test_sets_legal_style_map_names(self):
        self._run_style_map_names_test((
            ('MyFont', '', 'MyFont', 'regular'),
            ('MyFont', 'Regular', 'MyFont', 'regular'),
            ('MyFont', 'Bold', 'MyFont', 'bold'),
            ('MyFont', 'Italic', 'MyFont', 'italic'),
            ('MyFont', 'Bold Italic', 'MyFont', 'bold italic')))

    def test_moves_width_to_family(self):
        self._run_style_map_names_test((
            ('MyFont', 'Condensed', 'MyFont Condensed', 'regular'),
            ('MyFont', 'Condensed Bold', 'MyFont Condensed', 'bold'),
            ('MyFont', 'Condensed Italic', 'MyFont Condensed', 'italic'),
            ('MyFont', 'Condensed Bold Italic', 'MyFont Condensed',
             'bold italic')))

    def test_moves_nonbold_weight_to_family(self):
        self._run_style_map_names_test((
            ('MyFont', 'Thin', 'MyFont Thin', 'regular'),
            ('MyFont', 'Thin Italic', 'MyFont Thin', 'italic'),
            ('MyFont', 'Condensed Thin', 'MyFont Condensed Thin', 'regular'),
            ('MyFont', 'Condensed Thin Italic', 'MyFont Condensed Thin',
             'italic')))


class ToUfosTest(unittest.TestCase):
    def generate_minimal_font(self):
        font = GSFont()
        font.appVersion = '895'
        font.date = datetime.datetime.today()
        font.familyName = 'MyFont'
        
        master = GSFontMaster()
        master.ascender = 0
        master.capHeight = 0
        master.descender = 0
        master.id = 'id'
        master.xHeight = 0
        font.masters = [master]
        
        font.glyphs = []
        font.unitsPerEm = 1000
        font.versionMajor = 1
        font.versionMinor = 0
        
        return font

    def add_glyph(self, font, glyphname):
        glyph = GSGlyph()
        glyph.name = glyphname
        font.glyphs.append(glyph)
        layer = GSLayer()
        glyph.layers.append(layer)
        layer.layerId = font.masters[0].id
        layer.associatedMasterId = font.masters[0].id
        layer.width = 0
        
        
        return glyph

    def add_anchor(self, font, glyphname, anchorname, x, y):
        for glyph in font.glyphs:
            if glyph.name == glyphname:
                for layer in glyph.layers.values():
                    layer.anchors = getattr(layer, 'anchors', [])
                    anchor = GSAnchor()
                    anchor.name = anchorname
                    anchor.position = (x, y)
                    layer.anchors.append(anchor)

    def add_component(self, font, glyphname, componentname,
                      transform):
        for glyph in font.glyphs:
            if glyph.name == glyphname:
                for layer in glyph.layers.values():
                    component = GSComponent()
                    component.name = componentname
                    component.transform = transform
                    layer.components.append(component)

    def test_minimal_data(self):
        """Test the minimal data that must be provided to generate UFOs, and in
        some cases that additional redundant data is not set.
        """

        font = self.generate_minimal_font()
        family_name = font.familyName
        ufos = to_ufos(font)
        self.assertEqual(len(ufos), 1)

        ufo = ufos[0]
        self.assertEqual(len(ufo), 0)
        self.assertEqual(ufo.info.familyName, family_name)
        # self.assertEqual(ufo.info.styleName, 'Regular')
        self.assertEqual(ufo.info.versionMajor, 1)
        self.assertEqual(ufo.info.versionMinor, 0)
        self.assertIsNone(ufo.info.openTypeNameVersion)
        #TODO(jamesgk) try to generate minimally-populated UFOs in glyphsLib,
        # assert that more fields are empty here (especially in name table)

    def test_warn_no_version(self):
        """Test that a warning is printed when app version is missing."""

        font = self.generate_minimal_font()
        font.appVersion = '0'
        with CapturingLogHandler(builder.logger, "WARNING") as captor:
            to_ufos(font)
        self.assertEqual(len([r for r in captor.records
                              if "outdated version" in r.msg]), 1)

    def test_load_kerning(self):
        """Test that kerning conflicts are resolved correctly.

        Correct resolution is defined as such: the last time a pair is found in
        a kerning rule, that rule is used for the pair.
        """

        font = self.generate_minimal_font()

        # generate classes 'A': ['A', 'a'] and 'V': ['V', 'v']
        for glyph_name in ('A', 'a', 'V', 'v'):
            glyph = self.add_glyph(font, glyph_name)
            glyph.rightKerningGroup = glyph_name.upper()
            glyph.leftKerningGroup = glyph_name.upper()

        # classes are referenced in Glyphs kerning using old MMK names
        font.kerning = {
            font.masters[0].id: collections.OrderedDict((
                ('@MMK_L_A', collections.OrderedDict((
                    ('@MMK_R_V', -250),
                    ('v', -100),
                ))),
                ('a', collections.OrderedDict((
                    ('@MMK_R_V', 100),
                ))),
            ))}

        ufos = to_ufos(font)
        ufo = ufos[0]

        # these rules should be obvious
        self.assertEqual(ufo.kerning['public.kern1.A', 'public.kern2.V'], -250)
        self.assertEqual(ufo.kerning['a', 'public.kern2.V'], 100)

        # this rule results from breaking up (kern1.A, v, -100)
        # due to conflict with (a, kern2.V, 100)
        self.assertEqual(ufo.kerning['A', 'v'], -100)

    def test_propagate_anchors(self):
        """Test anchor propagation for some relatively complicated cases."""

        font = self.generate_minimal_font()

        glyphs = (
            ('sad', [], [('bottom', 50, -50), ('top', 50, 150)]),
            ('dotabove', [], [('top', 0, 150), ('_top', 0, 100)]),
            ('dotbelow', [], [('bottom', 0, -50), ('_bottom', 0, 0)]),
            ('dad', [('sad', 0, 0), ('dotabove', 50, 50)], []),
            ('dadDotbelow', [('dad', 0, 0), ('dotbelow', 50, -50)], []),
            ('yod', [], [('bottom', 50, -50)]),
            ('yodyod', [('yod', 0, 0), ('yod', 100, 0)], []),
        )
        for name, component_data, anchor_data in glyphs:
            components = [{'name': n, 'transform': (1, 0, 0, 1, x, y)}
                          for n, x, y in component_data]
            glyph = self.add_glyph(font, name)
            for n, x, y, in anchor_data:
                self.add_anchor(font, name, n, x, y)
            for n, x, y in component_data:
                self.add_component(font, name, n, (1, 0, 0, 1, x, y))

        ufos = to_ufos(font)
        ufo = ufos[0]

        glyph = ufo['dadDotbelow']
        self.assertEqual(len(glyph.anchors), 2)
        for anchor in glyph.anchors:
            self.assertEqual(anchor.x, 50)
            if anchor.name == 'bottom':
                self.assertEqual(anchor.y, -100)
            else:
                self.assertEqual(anchor.name, 'top')
                self.assertEqual(anchor.y, 200)

        glyph = ufo['yodyod']
        self.assertEqual(len(glyph.anchors), 2)
        for anchor in glyph.anchors:
            self.assertEqual(anchor.y, -50)
            if anchor.name == 'bottom_1':
                self.assertEqual(anchor.x, 50)
            else:
                self.assertEqual(anchor.name, 'bottom_2')
                self.assertEqual(anchor.x, 150)

    def test_postscript_name_from_data(self):
        font = self.generate_minimal_font()
        self.add_glyph(font, 'foo')['production'] = 'f_o_o.alt1'
        ufo = to_ufos(font)[0]
        postscriptNames = ufo.lib.get('public.postscriptNames')
        self.assertEqual(postscriptNames, {'foo': 'f_o_o.alt1'})

    def test_postscript_name_from_glyph_name(self):
        font = self.generate_minimal_font()
        self.add_glyph(font, 'C-fraktur')
        ufo = to_ufos(font)[0]
        postscriptNames = ufo.lib.get('public.postscriptNames')
        self.assertEqual(postscriptNames, {'C-fraktur': 'uni212D'})

    def test_weightClass_default(self):
        font = self.generate_minimal_font()
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo.info.openTypeOS2WeightClass, 400)

    def test_weightClass_from_customParameter_weightClass(self):
        # In the test input, the weight is specified twice: once as weight,
        # once as customParameters.weightClass. We expect that the latter wins
        # because the Glyphs handbook documents that the weightClass value
        # overrides the setting in the Weight drop-down list.
        # https://glyphsapp.com/content/1-get-started/2-manuals/1-handbook-glyphs-2-0/Glyphs-Handbook-2.3.pdf#page=202
        font = self.generate_minimal_font()
        master = font.masters[0]
        master.weight = 'Bold'  # 700
        master.customParameters = [GSCustomParameter(
            name='weightClass', value=698)]
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo.info.openTypeOS2WeightClass, 698)  # 698, not 700

    def test_weightClass_from_weight(self):
        font = self.generate_minimal_font()
        font.masters[0].weight = 'Bold'
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo.info.openTypeOS2WeightClass, 700)

    def test_widthClass_default(self):
        font = self.generate_minimal_font()
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo.info.openTypeOS2WidthClass, 5)

    def test_widthClass_from_customParameter_widthClass(self):
        # In the test input, the width is specified twice: once as width,
        # once as customParameters.widthClass. We expect that the latter wins
        # because the Glyphs handbook documents that the widthClass value
        # overrides the setting in the Width drop-down list.
        # https://glyphsapp.com/content/1-get-started/2-manuals/1-handbook-glyphs-2-0/Glyphs-Handbook-2.3.pdf#page=203
        font = self.generate_minimal_font()
        master = font.masters[0]
        master.width = 'Extra Condensed'  # 2
        master.customParameters = [GSCustomParameter(
            name='widthClass', value=7)]
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo.info.openTypeOS2WidthClass, 7)  # 7, not 2

    def test_widthClass_from_width(self):
        font = self.generate_minimal_font()
        font.masters[0].width = 'Extra Condensed'
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo.info.openTypeOS2WidthClass, 2)

    def test_GDEF(self):
        font = self.generate_minimal_font()
        for glyph in ('space', 'A', 'A.alt',
                      'wigglylinebelowcomb', 'wigglylinebelowcomb.alt',
                      'fi', 'fi.alt', 't_e_s_t', 't_e_s_t.alt'):
            self.add_glyph(font, glyph)
        self.add_anchor(font, 'A', 'bottom', 300, -10)
        self.add_anchor(font, 'wigglylinebelowcomb', '_bottom', 100, 40)
        self.add_anchor(font, 'fi', 'caret_1', 150, 0)
        self.add_anchor(font, 't_e_s_t.alt', 'caret_1', 200, 0)
        self.add_anchor(font, 't_e_s_t.alt', 'caret_2', 400, 0)
        self.add_anchor(font, 't_e_s_t.alt', 'caret_3', 600, 0)
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo.features.text.splitlines(), [
            'table GDEF {',
            '  # automatic',
            '  GlyphClassDef',
            '    [A], # Base',
            '    [fi t_e_s_t.alt], # Liga',
            '    [wigglylinebelowcomb wigglylinebelowcomb.alt], # Mark',
            '    ;',
            '  LigatureCaretByPos fi 150;',
            '  LigatureCaretByPos t_e_s_t.alt 200 400 600;',
            '} GDEF;',
        ])

    def test_GDEF_base_with_attaching_anchor(self):
        font = self.generate_minimal_font()
        self.add_glyph(font, 'A.alt')
        self.add_anchor(font, 'A.alt', 'top', 400, 1000)
        self.assertIn('[A.alt], # Base', to_ufos(font)[0].features.text)

    def test_GDEF_base_with_nonattaching_anchor(self):
        font = self.generate_minimal_font()
        self.add_glyph(font, 'A.alt')
        self.add_anchor(font, 'A.alt', '_top', 400, 1000)
        self.assertEqual('', to_ufos(font)[0].features.text)

    def test_GDEF_ligature_with_attaching_anchor(self):
        font = self.generate_minimal_font()
        self.add_glyph(font, 'fi')
        self.add_anchor(font, 'fi', 'top', 400, 1000)
        self.assertIn('[fi], # Liga', to_ufos(font)[0].features.text)

    def test_GDEF_ligature_with_nonattaching_anchor(self):
        font = self.generate_minimal_font()
        self.add_glyph(font, 'fi')
        self.add_anchor(font, 'fi', '_top', 400, 1000)
        self.assertEqual('', to_ufos(font)[0].features.text)

    def test_GDEF_mark(self):
        font = self.generate_minimal_font()
        self.add_glyph(font, 'eeMatra-gurmukhi')
        self.assertIn('[eeMatra-gurmukhi], # Mark',
                      to_ufos(font)[0].features.text)

    def test_GDEF_fractional_caret_position(self):
        # Some Glyphs sources happen to contain fractional caret positions.
        # In the Adobe feature file syntax (and binary OpenType GDEF tables),
        # caret positions must be integers.
        font = self.generate_minimal_font()
        self.add_glyph(font, 'fi')
        self.add_anchor(font, 'fi', 'caret_1', 499.9876, 0)
        self.assertIn('LigatureCaretByPos fi 500;',
                      to_ufos(font)[0].features.text)

    def test_set_blue_values(self):
        """Test that blue values are set correctly from alignment zones."""

        font_in = []
        for data in [(500, 15), (400, -15), (0, -15), (-200, 15), (-300, -15)]:
            az = GSAlignmentZone()
            az.position, az.size = data
            font_in.append(az)
        expected_blue_values = [-200, -185, -15, 0, 500, 515]
        expected_other_blues = [-315, -300, 385, 400]

        font = self.generate_minimal_font()
        font.masters[0].alignmentZones = font_in
        ufo = to_ufos(font)[0]

        self.assertEqual(ufo.info.postscriptBlueValues, expected_blue_values)
        self.assertEqual(ufo.info.postscriptOtherBlues, expected_other_blues)

    def test_set_glyphOrder_no_custom_param(self):
        font = self.generate_minimal_font()
        self.add_glyph(font, 'C')
        self.add_glyph(font, 'B')
        self.add_glyph(font, 'A')
        self.add_glyph(font, 'Z')
        glyphOrder = to_ufos(font)[0].lib[PUBLIC_PREFIX + 'glyphOrder']
        self.assertEqual(glyphOrder, ['C', 'B', 'A', 'Z'])

    def test_set_glyphOrder_with_custom_param(self):
        font = self.generate_minimal_font()
        font['customParameters'] = [GSCustomParameter(
            name='glyphOrder', value=['A', 'B', 'C'])]
        self.add_glyph(font, 'C')
        self.add_glyph(font, 'B')
        self.add_glyph(font, 'A')
        # glyphs outside glyphOrder are appended at the end
        self.add_glyph(font, 'Z')
        glyphOrder = to_ufos(font)[0].lib[PUBLIC_PREFIX + 'glyphOrder']
        self.assertEqual(glyphOrder, ['A', 'B', 'C', 'Z'])

    def test_missing_date(self):
        font = self.generate_minimal_font()
        font.date = None
        ufo = to_ufos(font)[0]
        self.assertIsNone(ufo.info.openTypeHeadCreated)

    def _run_guideline_test(self, data_in, expected):
        font = self.generate_minimal_font()
        font['glyphs'].append({
            'glyphname': 'a',
            'layers': [{'layerId': font.masters[0].id, 'width': 0,
                        'guideLines': data_in}]})
        ufo = to_ufos(font)[0]
        self.assertEqual(ufo['a'].guidelines, expected)

    #TODO enable these when we switch to loading UFO3 guidelines
    #def test_set_guidelines(self):
    #    """Test that guidelines are set correctly."""

    #    self._run_guideline_test(
    #        [{'position': (1, 2), 'angle': 270}],
    #        [{str('x'): 1, str('y'): 2, str('angle'): 90}])

    #def test_set_guidelines_duplicates(self):
    #    """Test that duplicate guidelines are accepted."""

    #    self._run_guideline_test(
    #        [{'position': (1, 2), 'angle': 270},
    #         {'position': (1, 2), 'angle': 270}],
    #        [{str('x'): 1, str('y'): 2, str('angle'): 90},
    #         {str('x'): 1, str('y'): 2, str('angle'): 90}])


class _PointDataPen(object):

    def __init__(self):
        self.contours = []

    def addPoint(self, pt, segmentType=None, smooth=False, **kwargs):
        self.contours[-1].append((pt[0], pt[1], segmentType, smooth))

    def beginPath(self):
        self.contours.append([])

    def endPath(self):
        if not self.contours[-1]:
            self.contours.pop()

    def addComponent(self, *args, **kwargs):
        pass


class DrawPathsTest(unittest.TestCase):

    def test_draw_paths_empty_nodes(self):
        contours = [GSPath()]

        pen = _PointDataPen()
        draw_paths(pen, contours)

        self.assertEqual(pen.contours, [])

    def test_draw_paths_open(self):
        contours = [{
            'closed': False,
            'nodes': [
                (0, 0, 'line', False),
                (1, 1, 'offcurve', False),
                (2, 2, 'offcurve', False),
                (3, 3, 'curve', True),
            ]}]
        
        path = GSPath()
        path.nodes = [
            GSNode(position=(0, 0), nodetype='line'),
            GSNode(position=(1, 1), nodetype='offcurve'),
            GSNode(position=(2, 2), nodetype='offcurve'),
            GSNode(position=(3, 3), nodetype='curve', smooth=True),
        ]
        path.closed = False
        pen = _PointDataPen()
        draw_paths(pen, [path])

        self.assertEqual(pen.contours, [[
            (0, 0, 'move', False),
            (1, 1, None, False),
            (2, 2, None, False),
            (3, 3, 'curve', True),
        ]])

    def test_draw_paths_closed(self):
        path = GSPath()
        path.nodes = [
            GSNode(position=(0, 0), nodetype='offcurve'),
            GSNode(position=(1, 1), nodetype='offcurve'),
            GSNode(position=(2, 2), nodetype='curve', smooth=True),
            GSNode(position=(3, 3), nodetype='offcurve'),
            GSNode(position=(4, 4), nodetype='offcurve'),
            GSNode(position=(5, 5), nodetype='curve', smooth=True),
        ]
        path.closed = True
        contours = [{
            'closed': True,
            'nodes': [
                (0, 0, 'offcurve', False),
                (1, 1, 'offcurve', False),
                (2, 2, 'curve', True),
                (3, 3, 'offcurve', False),
                (4, 4, 'offcurve', False),
                (5, 5, 'curve', True),
            ]}]

        pen = _PointDataPen()
        draw_paths(pen, [path])

        points = pen.contours[0]

        first_x, first_y = points[0][:2]
        self.assertEqual((first_x, first_y), (5, 5))

        first_segment_type = points[0][2]
        self.assertEqual(first_segment_type, 'curve')


if __name__ == '__main__':
    unittest.main()
