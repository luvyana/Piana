import bpy
from .ui.funcs import *
from .mods.anims import *
from .mods.liana import *
from .utils.common import setup_logger

import webbrowser
import time

import subprocess

logger = setup_logger(__name__)


class ImportMap(bpy.types.Operator):
    bl_idname = "object.import_map"
    bl_label = "Import Map"

    def execute(self, context):
        start = time.perf_counter()
        addon_prefs = context.preferences.addons[__package__].preferences
        import_map(addon_prefs)
        end = time.perf_counter()
        logger.info(f"Import time:{end-start}")
        return {'FINISHED'}


# ANCHOR Animations

class VALOANIM_OT_UBbutton(bpy.types.Operator):
    bl_idname = "val.ubbutton"
    bl_label = "UBanim preparation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        amt = bpy.context.object
        if amt.type != 'ARMATURE':
            alert('Select an armature')
            return {'CANCELLED'}

        reset_childs(amt, 'Pelvis')
        reset_twst(amt)
        reset_childs(amt, 'Head')

        refresh_screen()
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}


class VALOANIM_OT_LBbutton(bpy.types.Operator):
    bl_idname = "val.lbbutton"
    bl_label = "LBanim preparation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        amt = bpy.context.object
        if amt.type != 'ARMATURE':
            alert('Select an armature')
            return {'CANCELLED'}

        reset_childs(amt, 'Spine1')
        reset_childs(amt, 'MasterWeaponAim')
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')
        amt.data.bones['MasterWeaponAim'].select = True
        bpy.ops.anim.keyframe_clear_v3d()
        bpy.ops.pose.transforms_clear()
        bpy.ops.anim.keyframe_insert_menu(type='LocRotScale')
        bpy.ops.object.mode_set(mode='OBJECT')
        reset_twst(amt)

        refresh_screen()
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}


class VALOANIM_OT_Facebutton(bpy.types.Operator):
    bl_idname = "val.facebutton"
    bl_label = "Faceanim preparation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        amt = bpy.context.object
        if amt.type != 'ARMATURE':
            alert('Select an armature')
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')
        selectallchilds(amt, amt.data.bones['Head'])
        bpy.ops.pose.select_all(action='INVERT')
        bpy.ops.anim.keyframe_clear_v3d()
        bpy.ops.pose.transforms_clear()
        bpy.ops.anim.keyframe_insert_menu(type='LocRotScale')
        bpy.ops.object.mode_set(mode='OBJECT')
        refresh_screen()
        return {'FINISHED'}


class VALOANIM_OT_Twistbutton(bpy.types.Operator):
    bl_idname = "val.twistfix"
    bl_label = "Twist Fix"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        amt = bpy.context.object
        if amt.type != 'ARMATURE':
            alert('Select an armature')
            return {'CANCELLED'}

        reset_twst(amt)
        refresh_screen()
        return {'FINISHED'}


class VALOANIM_OT_FaceFixbutton(bpy.types.Operator):
    bl_idname = "val.facefix"
    bl_label = "Face Fix"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        amt = bpy.context.object
        if amt.type != 'ARMATURE':
            alert('Select an armature')
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')
        # amt.data.bones[bone].select = True
        selectallchilds(amt, amt.data.bones['Head'])
        amt.data.bones['Head'].select = False
        bpy.ops.anim.keyframe_clear_v3d()
        bpy.ops.pose.transforms_clear()  # bpy.ops.pose.loc_clear() 位置のみ
        bpy.ops.anim.keyframe_insert_menu(type='Location')
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.update()

        refresh_screen()
        return {'FINISHED'}


# ANCHOR General

class PIANA_OT_Message(bpy.types.Operator):
    bl_idname = "piana.message"
    bl_label = "VALORANT Animation"
    bl_options = {'REGISTER', 'INTERNAL'}

    message: bpy.props.StringProperty(default='Message')

    lines = []
    line0 = None

    def execute(self, context):
        self.lines = self.message.split("\n")
        maxlen = 0
        for line in self.lines:
            if len(line) > maxlen:
                maxlen = len(line)

        print(self.message)

        self.report({'WARNING'}, self.message)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.lines = self.message.split("\n")
        maxlen = 0
        for line in self.lines:
            if len(line) > maxlen:
                maxlen = len(line)

        self.line0 = self.lines.pop(0)

        return context.window_manager.invoke_props_dialog(self, width=100 + 6*maxlen)

    def cancel(self, context):
        # print('cancel')
        self.execute(self)

    def draw(self, context):
        layout = self.layout
        sub = layout.column()
        sub.label(text=self.line0, icon='ERROR')

        for line in self.lines:
            sub.label(text=line)


class PIANA_OT_OpenUModel(bpy.types.Operator):
    bl_idname = "piana.runumodel"
    bl_label = "Run UModel UI"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        sc = context.scene

        addon_prefs = context.preferences.addons[__package__].preferences
        addon_path = Path(bpy.utils.user_resource('SCRIPTS')
                          ).joinpath('addons', __package__)
        umodel_path = addon_path.joinpath(
            "tools", "umodel.exe").__str__()

        subprocess.Popen(
            [umodel_path,
             f"-path={addon_prefs.paksPath}",
             f"-game=valorant",
             f"-aes=0x4BE71AF2459CF83899EC9DC2CB60E22AC4B3047E0211034BBABE9D174C069DD6"]
        )

        return {'FINISHED'}


class PIANA_OT_Donate(bpy.types.Operator):
    """You can buy me a coffee if you like this addon ^^ """

    bl_idname = "piana.support"
    bl_label = "All the support is appreciated <3"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        patreon_url = "https://www.patreon.com/luviana"
        webbrowser.open(patreon_url, new=0, autoraise=True)

        return {'FINISHED'}
