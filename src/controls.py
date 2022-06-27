import bpy
from .ui.funcs import *


logger = setup_logger(__name__)


# ANCHOR: main()
# -------------------------- #

def main(context):
    sc = bpy.context.scene

# ANCHOR: UI
# -------------------------- #

class VIEW3D_PT_Piana(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Piana"
    bl_idname = "PIANA_PT_panel"
    bl_label = "Settings"

    

    def draw(self, context):
        layout = self.layout
        addon_prefs = context.preferences.addons[__package__].preferences

        main_column = layout.column()
        s_column_1 = main_column.column(align=False)

        s_column_1.label(text="Export Folder")
        s_column_1.prop(addon_prefs, "exportPath", text="")

        s_column_1.label(text="PAKs Folder")
        s_column_1.prop(addon_prefs, "paksPath", text="")
        
        s_column_1.prop(addon_prefs, "debug", text="Debug Mode")

        row = s_column_1.row()
        row.prop(addon_prefs, "usePerfPatch", text="Use PerfPatch")
        row.enabled = not addon_prefs.isInjected

class VIEW3D_PT_MapImporter(bpy.types.Panel):
    """Creates a Panel in Properties(N)"""
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Piana"
    bl_idname = "PIANA_PT_Piana"
    bl_label = "Map Importer"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        addon_prefs = context.preferences.addons[__package__].preferences

        main_column = layout.column()

        if addon_prefs.paths:

            s_column_2 = main_column.column()
            s_column_2.label(text="Map :")
            s_column_2.prop(addon_prefs, "selectedMap", text="")
            s_column_2.separator()

            # TODO
            # s_column_2.prop(addon_prefs, "importDecals", text="Import Decals")
            s_column_2.prop(addon_prefs, "importLights", text="Import Lights")
            s_column_2.prop(addon_prefs, "combineUmaps", text="Combine UMAPs")

            if addon_prefs.combineUmaps:
                s_column_2.label(text="Combine Method :")
                s_column_2.prop(addon_prefs, "combineMethod", text="")

            s_column_2.label(text="Textures :")
            s_column_2.prop(addon_prefs, "textureControl", text="")

            s_column_2.separator()

            split = main_column.split(align=True)
            colL = split.column(align=True)
            colL.scale_y = 1.25
            colL.operator("object.import_valorant_map", icon='IMPORT', text="Import Map!")

class VIEW3D_PT_Animation(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Piana"
    bl_idname = "PIANA_PT_animation_panel"
    bl_label = "Animation Tools"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        r1 = layout.row()
        r1.operator("val.ubbutton", icon='SORT_DESC', text="UB Setup")
        r1.operator("val.lbbutton", icon='SORT_ASC', text="LB Setup")
        layout.operator("val.facebutton", icon='MONKEY', text="Face Setup")

        ehe = layout.row()
        ehe.operator("val.twistfix", text="Twist Fix")
        ehe.operator("val.facefix", text="Face Fix")
        layout.label(text="Credits : twitter/r4tasan")

class VIEW3D_PT_Others(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Piana"
    bl_idname = "PIANA_PT_Others"
    bl_label = "Other"

    def draw(self, context):
        layout = self.layout
        addon_prefs = context.preferences.addons[__package__].preferences

        scene = context.scene

        layout.operator("piana.support", icon='FUND', text="Donate", text_ctxt="Donate")
        if addon_prefs.paths:
            layout.operator("piana.runumodel", icon='SCRIPT', text="Start UModel")