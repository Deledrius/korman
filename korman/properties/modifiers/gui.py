#    This file is part of Korman.
#
#    Korman is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Korman is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Korman.  If not, see <http://www.gnu.org/licenses/>.

import bpy
import math
import bmesh
import mathutils
from itertools import count, filterfalse
from bpy.props import *
from PyHSPlasma import *

from .base import PlasmaModifierProperties, PlasmaModifierLogicWiz
from .logic import game_versions
from ... import idprops


journal_pfms = {
    pvPrime : {
        "filename": "xJournalBookGUIPopup.py",
        "attribs": (
            { 'id':  1, 'type': "ptAttribActivator", "name": "actClickableBook" },
            { 'id':  3, 'type': "ptAttribString",    "name": "JournalName" },
            { 'id': 10, 'type': "ptAttribBoolean",   'name': "StartOpen" },
        )
    },
    pvPots : {
        # Supplied by the OfflineKI script:
        # https://gitlab.com/diafero/offline-ki/blob/master/offlineki/xSimpleJournal.py
        "filename": "xSimpleJournal.py",
        "attribs": (
            { 'id':  1, 'type': "ptAttribActivator", "name": "bookClickable" },
            { 'id':  2, 'type': "ptAttribString",    "name": "journalFileName" },
            { 'id':  3, 'type': "ptAttribBoolean",   "name": "isNotebook" },
            { 'id':  4, 'type': "ptAttribFloat",     "name": "BookWidth" },
            { 'id':  5, 'type': "ptAttribFloat",     "name": "BookHeight" },
        )
    },
    pvMoul : {
        "filename": "xJournalBookGUIPopup.py",
        "attribs": (
            { 'id':  1, 'type': "ptAttribActivator", 'name': "actClickableBook" },
            { 'id': 10, 'type': "ptAttribBoolean",   'name': "StartOpen" },
            { 'id': 11, 'type': "ptAttribFloat",     'name': "BookWidth" },
            { 'id': 12, 'type': "ptAttribFloat",     'name': "BookHeight" },
            { 'id': 13, 'type': "ptAttribString",    'name': "LocPath" },
            { 'id': 14, 'type': "ptAttribString",    'name': "GUIType" },
        )
    },
}


class PlasmaGUIColorScheme(bpy.types.PropertyGroup):
    pl_id = "guicolorscheme"

    font_face = StringProperty(name="Font Face")
    font_size = IntProperty(name="Font Size")
    transparent = BoolProperty(name="Transparent")

    foreground_color = FloatVectorProperty(name="Shore Tint",
                                     subtype="COLOR",
                                     min=0.0, max=1.0)
    background_color = FloatVectorProperty(name="Shore Tint",
                                     subtype="COLOR",
                                     min=0.0, max=1.0)
    sel_foreground_color = FloatVectorProperty(name="Shore Tint",
                                     subtype="COLOR",
                                     min=0.0, max=1.0)
    sel_background_color = FloatVectorProperty(name="Shore Tint",
                                     subtype="COLOR",
                                     min=0.0, max=1.0)


class PlasmaGUIDialogModifier(PlasmaModifierProperties):
    pl_id = "guidialogmod"

    bl_category = "GUI"
    bl_label = "Dialog"
    bl_description = "Dialog Box containing GUI Controls"
    bl_icon = "MENU_PANEL"

    #controls = CollectionProperty(name="Controls")
    #PFM - ProcReceiver
    #renderMod - Camera (plPostEffectMod)
    camera = PointerProperty(name="Camera", type=bpy.types.Camera)
    color_scheme = PointerProperty(type=PlasmaGUIColorScheme)

    def export(self, exporter, bo, so):
        # Create the dialog modifier
        mod = exporter.mgr.find_create_object(pfGUIDialogMod, so=so, name=self.key_name)


class PlasmaGUIButtonModifier(PlasmaModifierProperties):
    pl_id = "guibuttonmod"

    bl_category = "GUI"
    bl_label = "Button"
    bl_description = "GUI Button Control"
    bl_icon = "UI"

    def export(self, exporter, bo, so):
        # Create the button modifier
        mod = exporter.mgr.find_create_object(pfGUIButtonMod, so=so, name=self.key_name)

    @property
    def requires_actor(self):
        return True


class PlasmaGUIPopupModifier(PlasmaModifierProperties):
    pl_id = "guipopupmod"

    bl_category = "GUI"
    bl_label = "PopUp"
    bl_description = "GUI Simple PopUp"
    bl_icon = "MENU_PANEL"

    def next_unsused_page(self, pages):
        page_nums = {pages[page_name].page for page_name in pages}
        return next(filterfalse(page_nums.__contains__, count(1)))

    def export(self, exporter, bo, so):
        new_page = self.next_unsused_page(exporter.mgr._pages)
        so.key.location.page = new_page
        print(so.key.location)
        exporter.mgr.create_page(exporter.age_name, "GUIDialog{}".format(self.key_name), new_page)

        # Create clickoff button
        #button = exporter.mgr.find_create_object(pfGUIButtonMod, so=so, name=self.key_name)
        button = exporter.mgr.add_object(pfGUIButtonMod, name=self.key_name, loc=so.key.location, so=so)
        # Create camera
        pem = exporter.mgr.find_create_object(plPostEffectMod, so=so, name=self.key_name)
        # Create the dialog modifier
        mod = exporter.mgr.find_create_object(pfGUIDialogMod, so=so, name=self.key_name)
        mod.setFlag(0, True) #kModal
        mod.addControl(button.key)


class PlasmaJournalBookModifier(PlasmaModifierProperties, PlasmaModifierLogicWiz):
    pl_id = "journalbookmod"

    bl_category = "GUI"
    bl_label = "Journal"
    bl_description = "Journal Book"
    bl_icon = "WORDWRAP_ON"

    versions = EnumProperty(name="Export Targets",
                            description="Plasma versions for which this journal exports",
                            items=game_versions,
                            options={"ENUM_FLAG"},
                            default={"pvMoul"})
    start_state = EnumProperty(name="Start",
                               description="State of journal when activated",
                               items=[("OPEN", "Open", "Journal will start opened to first page"),
                                      ("CLOSED", "Closed", "Journal will start closed showing cover")],
                               default="CLOSED")
    book_type = EnumProperty(name="Book Type",
                             description="GUI type to be used for the journal",
                             items=[("bkBook", "Book", "A journal written on worn, yellowed paper"),
                                    ("bkNotebook", "Notebook", "A journal written on white, lined paper")],
                             default="bkBook")
    book_scale_w = IntProperty(name="Book Width Scale",
                               description="Width scale",
                               default=100, min=0, max=100,
                               subtype="PERCENTAGE")
    book_scale_h = IntProperty(name="Book Height Scale",
                               description="Height scale",
                               default=100, min=0, max=100,
                               subtype="PERCENTAGE")
    book_source_locpath = StringProperty(name="Book Source LocPath",
                                         description="LocPath for book's text (MO:UL)",
                                         default="Global.Journals.Empty")
    book_source_filename = StringProperty(name="Book Source Filename",
                                          description="Filename for book's text (Uru:CC)",
                                          default="")
    book_source_name = StringProperty(name="Book Source Name",
                                      description="Name of xJournalBookDefs.py entry for book's text (Uru:ABM)",
                                      default="Dummy")
    clickable_region = PointerProperty(name="Region",
                                       description="Region inside which the avatar must stand to be able to open the journal (optional)",
                                       type=bpy.types.Object,
                                       poll=idprops.poll_mesh_objects)

    def export(self, exporter, bo, so):
        our_versions = [globals()[j] for j in self.versions]
        version = exporter.mgr.getVer()
        if version not in our_versions:
            # We aren't needed here
            exporter.report.port("Object '{}' has a JournalMod not enabled for export to the selected engine.  Skipping.".format(bo.name, version), indent=2)
            return

        if self.clickable_region is None:
            # Create a region for the clickable's condition
            rgn_mesh = bpy.data.meshes.new("{}_Journal_ClkRgn".format(self.key_name))
            self.temp_rgn = bpy.data.objects.new("{}_Journal_ClkRgn".format(self.key_name), rgn_mesh)
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=(6.0))
            bmesh.ops.transform(bm, matrix=mathutils.Matrix.Translation(bo.location - self.temp_rgn.location), space=self.temp_rgn.matrix_world, verts=bm.verts)
            bm.to_mesh(rgn_mesh)
            bm.free()

            # No need to enable the object as a Plasma object; we're exported automatically as part of the node tree.
            # It does need a page, however, so we'll put it in the same place as the journal object itself.
            self.temp_rgn.plasma_object.page = bo.plasma_object.page
            bpy.context.scene.objects.link(self.temp_rgn)
        else:
            # Use the region provided
            self.temp_rgn = self.clickable_region

        # Generate the logic nodes
        self.logicwiz(bo, version)

        # Export the node tree
        self.node_tree.export(exporter, bo, so)

        # Get rid of our temporary clickable region
        if self.clickable_region is None:
            bpy.context.scene.objects.unlink(self.temp_rgn)

    def logicwiz(self, bo, version):
        tree = self.node_tree
        nodes = tree.nodes
        nodes.clear()

        # Assign journal script based on target version
        journal_pfm = journal_pfms[version]
        journalnode = nodes.new("PlasmaPythonFileNode")
        journalnode.filename = journal_pfm["filename"]

        # Manually add required attributes to the PFM
        journal_attribs = journal_pfm["attribs"]
        for attr in journal_attribs:
            new_attr = journalnode.attributes.add()
            new_attr.attribute_id = attr["id"]
            new_attr.attribute_type = attr["type"]
            new_attr.attribute_name = attr["name"]
        journalnode.update()

        if version == pvPrime:
            self.create_prime_nodes(bo, nodes, journalnode)
        elif version == pvPots:
            self.create_pots_nodes(bo, nodes, journalnode)
        elif version == pvMoul:
            self.create_moul_nodes(bo, nodes, journalnode)

    def create_prime_nodes(self, clickable_object, nodes, journalnode):
        clickable_region = nodes.new("PlasmaClickableRegionNode")
        clickable_region.region_object = self.temp_rgn

        facing_object = nodes.new("PlasmaFacingTargetNode")
        facing_object.directional = False
        facing_object.tolerance = math.degrees(-1)

        clickable = nodes.new("PlasmaClickableNode")
        clickable.link_input(clickable_region, "satisfies", "region")
        clickable.link_input(facing_object, "satisfies", "facing")
        clickable.link_output(journalnode, "satisfies", "actClickableBook")
        clickable.clickable_object = clickable_object

        start_open = nodes.new("PlasmaAttribBoolNode")
        start_open.link_output(journalnode, "pfm", "StartOpen")
        start_open.value = self.start_state == "OPEN"

        journal_name = nodes.new("PlasmaAttribStringNode")
        journal_name.link_output(journalnode, "pfm", "JournalName")
        journal_name.value = self.book_source_name

    def create_pots_nodes(self, clickable_object, nodes, journalnode):
        clickable_region = nodes.new("PlasmaClickableRegionNode")
        clickable_region.region_object = self.temp_rgn

        facing_object = nodes.new("PlasmaFacingTargetNode")
        facing_object.directional = False
        facing_object.tolerance = math.degrees(-1)

        clickable = nodes.new("PlasmaClickableNode")
        clickable.link_input(clickable_region, "satisfies", "region")
        clickable.link_input(facing_object, "satisfies", "facing")
        clickable.link_output(journalnode, "satisfies", "bookClickable")
        clickable.clickable_object = clickable_object

        srcfile = nodes.new("PlasmaAttribStringNode")
        srcfile.link_output(journalnode, "pfm", "journalFileName")
        srcfile.value = self.book_source_filename

        guitype = nodes.new("PlasmaAttribBoolNode")
        guitype.link_output(journalnode, "pfm", "isNotebook")
        guitype.value = self.book_type == "bkNotebook"

        width = nodes.new("PlasmaAttribIntNode")
        width.link_output(journalnode, "pfm", "BookWidth")
        width.value_float = self.book_scale_w / 100.0

        height = nodes.new("PlasmaAttribIntNode")
        height.link_output(journalnode, "pfm", "BookHeight")
        height.value_float = self.book_scale_h / 100.0

    def create_moul_nodes(self, clickable_object, nodes, journalnode):
        clickable_region = nodes.new("PlasmaClickableRegionNode")
        clickable_region.region_object = self.temp_rgn

        facing_object = nodes.new("PlasmaFacingTargetNode")
        facing_object.directional = False
        facing_object.tolerance = math.degrees(-1)

        clickable = nodes.new("PlasmaClickableNode")
        clickable.link_input(clickable_region, "satisfies", "region")
        clickable.link_input(facing_object, "satisfies", "facing")
        clickable.link_output(journalnode, "satisfies", "actClickableBook")
        clickable.clickable_object = clickable_object

        start_open = nodes.new("PlasmaAttribBoolNode")
        start_open.link_output(journalnode, "pfm", "StartOpen")
        start_open.value = self.start_state == "OPEN"

        width = nodes.new("PlasmaAttribIntNode")
        width.link_output(journalnode, "pfm", "BookWidth")
        width.value_float = self.book_scale_w / 100.0

        height = nodes.new("PlasmaAttribIntNode")
        height.link_output(journalnode, "pfm", "BookHeight")
        height.value_float = self.book_scale_h / 100.0

        locpath = nodes.new("PlasmaAttribStringNode")
        locpath.link_output(journalnode, "pfm", "LocPath")
        locpath.value = self.book_source_locpath

        guitype = nodes.new("PlasmaAttribStringNode")
        guitype.link_output(journalnode, "pfm", "GUIType")
        guitype.value = self.book_type

    @property
    def requires_actor(self):
        # We are too late in the export to be harvested automatically, so let's be explicit
        return True
