from bpy.types import AddonPreferences
from .utils.common import setup_logger, read_json
from .ui.funcs import has_paks


import bpy
import os
from pathlib import Path

logger = setup_logger(__name__)


def get_map_list():

    script_path = os.path.dirname(os.path.abspath(__file__))
    umap_list_path = Path(script_path).joinpath("assets").joinpath("umaps.json")
    umap_list = read_json(umap_list_path)

    maps: list = []
    name: str
    n: int = 0
    for name, value in umap_list.items():
        maps.append(
            (name, name.capitalize(), "", "", n)
        )
        n += 1

    return maps


def update_paks_path(self, context):
    addon_prefs = context.preferences.addons[__package__].preferences

    if has_paks(addon_prefs.paksPath) and os.path.isdir(addon_prefs.exportPath):
        addon_prefs.paths = True
    else:
        addon_prefs.paths = False


class PianaPreferences(AddonPreferences):
    # this must match the add-on name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __package__

    debug: bpy.props.BoolProperty(
        name='Debug',
        default=True,
        description="Debug mode"
    )

    paksPath: bpy.props.StringProperty(
        name='Paks Path',
        default="D:\\games\\Riot Games\\VALORANT\\live\\ShooterGame\\Content\\Paks\\",
        description="Path to your paks folder",
        subtype='DIR_PATH',
        update=update_paks_path,
    )

    exportPath: bpy.props.StringProperty(
        name='Export Path',
        default="",
        description="Path to your export folder",
        subtype='DIR_PATH',
    )

    paths: bpy.props.BoolProperty(
        name='Check for Paths',
        default=False,
        description="Path check"
    )

    # Map Importer Settings

    importDecals: bpy.props.BoolProperty(
        name='Import Decals',
        default=False,
        description="Import decals",
        # is_readonly=True
    )

    importLights: bpy.props.BoolProperty(
        name='Import Lights',
        default=False,
        description="Import lights",
        # is_readonly=True

    )

    combineUmaps: bpy.props.BoolProperty(
        name='Combine Umaps',
        default=True,
        description="Combine umaps"
    )

    combineMethod: bpy.props.EnumProperty(
        name='Combine Method',
        default='append',
        items=[
            ('append', 'Append', 'Append makes a full copy of the data into your blend-file, without keeping any reference to the original one.', 'APPEND_BLEND', 0),
            ('link', 'Link', 'Link creates a reference to the data in the source file such that changes made there will be reflected in the referencing file the next time it is reloaded.', "LINK_BLEND", 1)
        ]
    )

    textureControl: bpy.props.EnumProperty(
        name='Texture Control',
        default='pack',
        items=[
            ('pack', 'Pack', 'Packs the textures to the .blend file.', '', 0),
            ('local', 'Local', 'Moves the textures to a new "Textures" folder.', '', 1)
        ]
    )

    selectedMap: bpy.props.EnumProperty(
        name='Selected Map',
        # default="bind",
        items=get_map_list()
    )

    scriptPath: bpy.props.StringProperty(
        name='Script Path',
        default=os.path.dirname(os.path.abspath(__file__)),
        description="Path to your script folder",
        subtype='DIR_PATH'
    )

    usePerfPatch: bpy.props.BoolProperty(
        name='Use PerfPatch',
        default=True,
        description="Huge speed-up, but use it with caution. A restart is recommended after."
    )

    isInjected: bpy.props.BoolProperty(
        name='Is Injected',
        default=False,
        description="IsDLLInjected"
    )

    def draw(self, context):
        layout = self.layout

        main_column = layout.column()
        s_column_1 = main_column.column(align=False)

        s_column_1.prop(self, "exportPath")
        s_column_1.prop(self, "paksPath")
        s_column_1.prop(self, "debug")
