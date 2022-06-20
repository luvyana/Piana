import sys
import os
import subprocess
import bpy

from contextlib import redirect_stdout
from sys import stdout
from io import StringIO

from ..utils.common import *
from ..utils.blender import *
from ..utils.valorant import *
from ..utils.importer_xay import *

logger = setup_logger(__name__, "liana_main.log")
stdout = StringIO()

try:
    sys.dont_write_bytecode = True
    from ..tools.injector import inject_dll
except:
    pass

class debug:
    SELECTIVE_OBJECTS = [
        # "Brick_12_CastleA5",
        # "CameraSecurity_0_A3"
    ]
    SELECTIVE_UMAP = [
        # "Pitt_Art_AtkPathMid",
        # "Pitt_Art_AtkPathB",
        # "Pitt_Art_DefPathB",
        # "Pitt_Art_DefSpawn",
        # "Pitt_Art_AtkPathA",
    ]

    COUNT = 0



BLACKLIST_objects = [
    "navmesh",
    "_breakable",
    "_collision",
    "WindStreaks_Plane",
    "SM_Port_Snowflakes_BoundMesh",
    "sm_barrierduality",
    "box_for_volumes",
    "SuperGrid",
    "_Col",
    "For_Volumes"
]

BLACKLIST_textures = [
    "Albedo_DF",
    "MRA_MRA",
    "Normal_NM",
    "Diffuse B Low",
    "Blank_M0_NM",
    "Blank_M0_Flat_00_black_white_DF",
    "Blank_M0_Flat_00_black_white_NM",
    "flatnormal",
    "flatwhite",
]

# TODO DELETE THESE


ScalarParameterValues = []
StaticParameterValues = []
TextureParameterValues = []
BasePropertyOverrides = {}
VectorParameterValues = []
OtherTypes = []
MaterialTypes = []
ObjectTypes = []


def extract_assets(settings: Settings):

    # Check if everything is exported from uModel
    if settings.assets_path.joinpath("exported.yo").exists():
        logger.info("Models are already extracted")
    else:
        logger.warning("Models are not found, starting exporting with args : \n{args}")
        args = [settings.umodel.__str__(),
                f"-path={settings.paks_path.__str__()}",
                f"-game=valorant",
                f"-aes={settings.aes}",
                "-export",
                "*.uasset",
                "-xay",
                "-noanim",
                "-nooverwrite",
                f"-{settings.texture_format.replace('.', '')}",
                f"-out={settings.assets_path.__str__()}"]


        # Export Models
        subprocess.call(args,
                        stderr=subprocess.DEVNULL)

        with open(settings.assets_path.joinpath('exported.yo').__str__(), 'w') as out_file:
            out_file.write("")


def extract_data(settings: Settings, export_directory: str, asset_list_txt: str = ""):

    args = [settings.cue4extractor.__str__(),
            "--game-directory", settings.paks_path.__str__(),
            "--aes-key", settings.aes,
            "--export-directory", export_directory.__str__(),
            "--map-name", settings.selected_map.name,
            "--file-list", asset_list_txt,
            "--game-umaps", settings.umap_list_path.__str__()
            ]

    subprocess.call(args)


def search_object(map_object, index: int, link) -> bpy.types.Object:
    for source_object in bpy.data.objects:
        if map_object.name in source_object.type == "MESH":
            logger.info(f"[{index}] | Duplicate : {shorten_path(map_object.model_path, 4)} - {map_object.uname}")

            master_object = duplicate(source_object, data=False)
            master_object.name = map_object.uname

            link(master_object)
            reset_properties(master_object)
            return master_object
    return False


def get_object(map_object, index, link) -> bpy.types.Object:

    master_object = search_object(map_object, index, link)

    if not master_object:
        logger.info(f"[{index}] | Importing : {shorten_path(map_object.model_path, 4)} - {map_object.uname}")
        with redirect_stdout(stdout):
            master_object = xay(map_object.model_path)
        master_object.name = map_object.uname

    try:
        link(master_object)
    except:
        pass

    return master_object


def get_map_assets(settings: Settings):
    umaps = []

    if not settings.selected_map.folder_path.joinpath("exported.yo").exists():
        logger.info("Extracting JSON files")

        extract_data(settings, export_directory=settings.selected_map.umaps_path)

        umaps = get_files(path=settings.selected_map.umaps_path.__str__(), extension=".json")
        umap: Path

        object_list = []
        materials_ovr_list = []
        materials_list = []

        for umap in umaps:
            umap_json, objects = filter_umap(read_json(umap))

            # Logging
            ObjectTypes.append(objects)

            # save json
            save_json(umap.__str__(), umap_json)

            # get objects
            umap_objects, umap_materials = get_objects(umap_json)

            object_list.append(umap_objects)
            materials_ovr_list.append(umap_materials)

        object_txt = save_list(filepath=settings.selected_map.folder_path.joinpath(f"_assets_objects.txt"), lines=object_list)
        mats_ovr_txt = save_list(filepath=settings.selected_map.folder_path.joinpath(f"_assets_materials_ovr.txt"), lines=materials_ovr_list)

        extract_data(settings, export_directory=settings.selected_map.objects_path, asset_list_txt=object_txt)
        extract_data(settings, export_directory=settings.selected_map.materials_ovr_path, asset_list_txt=mats_ovr_txt)

        # ---------------------------------------------------------------------------------------

        models = get_files(path=settings.selected_map.objects_path.__str__(), extension=".json")
        model: Path
        for model in models:
            model_json = read_json(model)[2]
            model_name = model.stem

            # save json
            save_json(model.__str__(), model_json)

            # get object materials
            model_materials = get_object_materials(model_json)

            # get object textures
            # ...

            materials_list.append(model_materials)

        mats_txt = save_list(filepath=settings.selected_map.folder_path.joinpath(f"_assets_materials.txt"), lines=materials_list)
        extract_data(settings, export_directory=settings.selected_map.materials_path, asset_list_txt=mats_txt)

        print(settings.selected_map.folder_path.joinpath('exported.yo').__str__())
        with open(settings.selected_map.folder_path.joinpath('exported.yo').__str__(), 'w') as out_file:
            out_file.write("")

    else:
        umaps = get_files(path=settings.selected_map.umaps_path.__str__(), extension=".json")
        logger.info("JSON files are already extracted")

    return umaps


# TODO : MATERIALS

def set_materials(settings: Settings, byo: bpy.types.Object, map_object: MapObject, decal: bool = False):
    if decal:
        if "DecalMaterial" in map_object["Properties"]:

            yoyo = map_object["Properties"]["DecalMaterial"]

            mat_name = get_object_name(data=yoyo, mat=True)
            mat_json = read_json(settings.selected_map.materials_ovr_path.joinpath(f"{mat_name}.json"))

            mat = bpy.data.materials.new(name="Material")
            byo.data.materials.append(mat)

            byoMAT = byo.material_slots[0].material
            set_material(settings=settings, mat=byoMAT, mat_data=mat_json[0], object=map_object, decal=True)

            return
    else:
        object_properties_OG = map_object.json["Properties"]
        object_properties = map_object.data["Properties"]

        if "StaticMaterials" in object_properties_OG:
            for index, mat in enumerate(object_properties_OG["StaticMaterials"]):
                if type(mat["MaterialInterface"]) is dict:
                    mat_name = get_object_name(data=mat["MaterialInterface"], mat=True)
                    if "WorldGridMaterial" not in mat_name:
                        mat_json = read_json(settings.selected_map.materials_path.joinpath(f"{mat_name}.json"))
                        try:
                            obj_data = byo.data
                            mat_data = mat_json[0]

                            if obj_data.vertex_colors:
                                mat_name = mat_data["Name"] + "_V"
                            else:
                                mat_name = mat_data["Name"] + "_NV"

                            byoMAT = bpy.data.materials.get(mat_name)
                            if byoMAT is None:
                                byoMAT = bpy.data.materials.new(name=mat_name)
                                set_material(
                                    settings=settings, mat=byoMAT, mat_data=mat_json[0], object_cls=map_object, object_byo=byo)

                            byo.material_slots[index].material = byoMAT
                            # byoMAT = bpy.data.materials.new(name=mat_name)
                            # byo.material_slots[index].material = byoMAT
                            # set_material(settings=settings, mat=byoMAT, mat_data=mat_json[0], object_cls=map_object, object_byo=byo)
                        except IndexError:
                            pass

        if "OverrideMaterials" in object_properties:
            for index, mat in enumerate(object_properties["OverrideMaterials"]):
                if type(mat) is dict:
                    mat_name = get_object_name(data=mat, mat=True)
                    mat_json = read_json(settings.selected_map.materials_ovr_path.joinpath(f"{mat_name}.json"))
                    try:
                        obj_data = byo.data
                        mat_data = mat_json[0]

                        if obj_data.vertex_colors:
                            mat_name = mat_data["Name"] + "_V"
                        else:
                            mat_name = mat_data["Name"] + "_NV"

                        byoMAT = bpy.data.materials.get(mat_name)
                        if byoMAT is None:
                            byoMAT = bpy.data.materials.new(name=mat_name)
                            set_material(
                                settings=settings, mat=byoMAT, mat_data=mat_json[0], object_cls=map_object, object_byo=byo)

                        byo.material_slots[index].material = byoMAT
                        # byoMAT = bpy.data.materials.new(name=mat_name)
                        # byo.material_slots[index].material = byoMAT
                        # if byoMAT is not None:
                        #     set_material(settings=settings, mat=byoMAT, mat_data=mat_json[0], override=True, object_cls=map_object, object_byo=byo)
                    except IndexError:
                        pass

# SECTION : Set Material


def set_material(settings: Settings, mat: bpy.types.Material, mat_data: dict, override: bool = False, decal: bool = False, object_cls: MapObject = None, object_byo: bpy.types.Object = None):

    mat.use_nodes = True

    # define shits
    nodes = mat.node_tree.nodes
    link = mat.node_tree.links.new
    create_node = nodes.new

    obj_data = object_byo.data

    # if obj_data.vertex_colors:
    #     mat.name = mat_data["Name"] + "_V"
    # else:
    #     mat.name = mat_data["Name"] + "_NV"

    if "Properties" not in mat_data:
        return

    mat_props = mat_data["Properties"]

    if "Parent" in mat_props:
        mat_type = get_name(mat_props["Parent"]["ObjectPath"])
    else:
        mat_type = "NO PARENT"

    if "PhysMaterial" in mat_props:
        mat_phys = get_name(mat_props["PhysMaterial"]["ObjectPath"])
        if "M_Glass" == mat_phys and "Emissive" not in mat.name:
            mat_type = "Glass"
    else:
        mat_phys = False

    # Clear Nodes
    clear_nodes(nodes)

    N_NOTE = create_node_note(nodes, mat_type)
    N_OUTPUT = nodes['Material Output']

    # EnvCollision
    if "EnvCollision_MAT" in mat_type:
        bpy.data.objects.remove(object_byo)

    # if obj_data.vertex_colors:
    if "Vertex Color" in nodes:
        N_VERTEX = nodes['Vertex Color']
    else:
        N_VERTEX = create_node(type='ShaderNodeVertexColor')
        nodes["Vertex Color"].layer_name = "Col"

    note_textures_normal = create_node_note(nodes, "Textures : Normal")
    note_textures_override = create_node_note(nodes, "Textures : Override")
    note_textures_cached = create_node_note(nodes, "Textures : Cached")

    note_textures_normal.width = 240
    note_textures_override.width = 240
    note_textures_cached.width = 240

    note_textures_normal.label_size = 15
    note_textures_override.label_size = 15
    note_textures_cached.label_size = 15

    set_node_position(note_textures_normal, -700, 60)
    set_node_position(note_textures_override, -1000, 60)
    set_node_position(note_textures_cached, -1300, 60)

    set_node_position(N_NOTE, -350, 230)
    set_node_position(N_OUTPUT, 300, 0)
    set_node_position(N_VERTEX, -600, 180)

    N_SHADER = nodes.new("ShaderNodeGroup")
    N_SHADER.width = 200
    N_MAPPING = None

    # Pre Overrides

    types_base = [
        "BaseEnv_MAT_V4",
        "BaseEnv_MAT_V4_Fins",
        "BaseEnv_MAT_V4_Inst",
        "BaseEnvUBER_MAT_V3_NonshinyWall",
        "BaseEnv_MAT_V4_Foliage",
        "BaseEnv_MAT_V4_VFX",
        "BaseEnv_MAT",
        "BaseEnv_MAT_V4_ShadowAsTranslucent",
        "Mat_BendingRope",
        "FoliageEnv_MAT",
        "BaseOpacitySpecEnv_MAT",
        "BaseEnv_ClothMotion_MAT",
        "BaseEnvVertexAlpha_MAT",
        "Wood_M6_MoroccanTrimA_MI",
        "Stone_M0_SquareTiles_MI",
        "BaseEnv_MAT_V4_Rotating",
        "HorizontalParallax",
        "TileScroll_Mat",
        "BasaltEnv_MAT",
        "BaseEnvEmissive_MAT",
        "BaseEnvEmissiveUnlit_MAT",
        "BaseEnv_Unlit_MAT_V4"
    ]

    types_blend = [
        "BaseEnv_Blend_UV1_MAT_V4",
        "BaseEnv_Blend_UV2_MAT_V4",
        "BaseEnv_Blend_UV3_MAT_V4",
        "BaseEnv_Blend_UV4_MAT_V4",
        "BaseEnv_Blend_MAT_V4_V3Compatibility",
        "BaseEnv_Blend_MAT_V4",
        "BaseEnv_BlendNormalPan_MAT_V4",
        "BaseEnv_Blend_UV2_Masked_MAT_V4",
        "BlendEnv_MAT"
    ]

    types_glass = [
        "Glass"
    ]

    types_emissive = [
        "BaseEnv_Unlit_Texture_MAT_V4",
    ]

    types_emissive_scroll = [
        "BaseEnvEmissiveScroll_MAT",
    ]

    types_screen = [
        "BaseEnvEmissiveLCDScreen_MAT"
    ]

    types_hologram = [
        "BaseEnv_HologramA"
    ]

    types_decal = [
        "BaseOpacity_RGB_Env_MAT"
    ]

    types_lightshift = [
        "0_GeoLightShaft",
        "0_GenericA01_MAT",
        "MI_OrangeKingdom_LightShaft"
    ]

    types_spriteglow = [
        "0_Sprite_GlowLight"
    ]

    types_waterfallvista = [
        "0_Waterfall_Base1"
    ]

    types_ventsmoke = [
        "0_VentSmoke_Duo",
        "0_VentSmoke"
    ]

    MaterialTypes.append(mat_type)

    # nodes_textures = get_textures(settings=settings, mat=mat, override=override, mat_props=mat_props, shader=N_SHADER) MOVED DOWN

    blend_mode = BlendMode.OPAQUE

    mat_switches = []
    mat_colors = {}
    mat_shading_model = "MSM_AresEnvironment"

    # SECTION : Select Shader

    user_mat_type = mat_type

    if mat_type in types_decal:
        N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Decal")
        link(N_SHADER.outputs["BSDF"], N_OUTPUT.inputs["Surface"])

    elif mat_type in types_hologram:
        N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Hologram")
        link(N_SHADER.outputs["Emission"], N_OUTPUT.inputs["Surface"])

    elif mat_type in types_lightshift:
        N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Lightshift")
        link(N_SHADER.outputs["BSDF"], N_OUTPUT.inputs["Surface"])
        N_MAPPING = nodes.new("ShaderNodeGroup")
        N_MAPPING.width = 200
        N_MAPPING.node_tree = get_valorant_shader(group_name="VALORANT_W/V_Mapping")
        set_node_position(N_MAPPING, -1600, 0)

    elif mat_type in types_screen or "LCD" in mat.name or "Terminal" in mat.name:
        N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Screen")
        N_SHADER.inputs["Emission Strength"].default_value = 5
        link(N_SHADER.outputs["Shader"], N_OUTPUT.inputs["Surface"])

    # elif mat_type in types_glass or "Glass" in mat.name:
    #     N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Base")
    #     link(N_SHADER.outputs["BSDF"], N_OUTPUT.inputs["Surface"])
    #     if "GlassShardGlowMint" not in mat.name:
    #         user_mat_type = "Glass"

    elif"Blend" in mat_type:
        N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Blend")

        N_SHADER.inputs["Vertex Controls"].display_shape = "DIAMOND_DOT"
        N_SHADER.inputs["A - Value Inputs"].display_shape = "DIAMOND_DOT"
        N_SHADER.inputs["A - Texture Inputs"].display_shape = "DIAMOND_DOT"
        N_SHADER.inputs["A - Color Inputs"].display_shape = "DIAMOND_DOT"
        N_SHADER.inputs["B - Value Inputs"].display_shape = "DIAMOND_DOT"
        N_SHADER.inputs["B - Texture Inputs"].display_shape = "DIAMOND_DOT"
        N_SHADER.inputs["B - Color Inputs"].display_shape = "DIAMOND_DOT"

        link(N_SHADER.outputs["BSDF"], N_OUTPUT.inputs["Surface"])
        user_mat_type = "Blend"

    elif mat_type in types_glass:
        N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Base")
        N_SHADER.inputs["Roughness"].default_value = 0.2
        N_SHADER.inputs["Specular"].default_value = 0.2
        link(N_SHADER.outputs["BSDF"], N_OUTPUT.inputs["Surface"])
        mat.use_screen_refraction = True

    elif mat_type in types_emissive:
        N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Base")
        N_SHADER.inputs["Emission Strength"].default_value = 3
        link(N_SHADER.outputs["BSDF"], N_OUTPUT.inputs["Surface"])

    elif mat_type in types_emissive_scroll:
        N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Emissive_Scroll")
        N_SHADER.inputs["Emission Strength"].default_value = 5
        link(N_SHADER.outputs["Shader"], N_OUTPUT.inputs["Surface"])

    elif mat_type in types_spriteglow:
        N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_SpriteGlow")
        link(N_SHADER.outputs["BSDF"], N_OUTPUT.inputs["Surface"])

    elif mat_type in types_waterfallvista:
        N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Waterfall")
        link(N_SHADER.outputs["BSDF"], N_OUTPUT.inputs["Surface"])
        N_MAPPING = nodes.new("ShaderNodeGroup")
        N_MAPPING.width = 200
        N_MAPPING.node_tree = get_valorant_shader(group_name="VALORANT_Waterfall_Mapping")
        set_node_position(N_MAPPING, -1600, 0)
        user_mat_type = "Waterfallvista"

    elif mat_type in types_ventsmoke:
        N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Ventsmoke")
        link(N_SHADER.outputs["BSDF"], N_OUTPUT.inputs["Surface"])
        N_MAPPING = nodes.new("ShaderNodeGroup")
        N_MAPPING.width = 200
        N_MAPPING.node_tree = get_valorant_shader(group_name="VALORANT_Ventsmoke_Mapping")
        set_node_position(N_MAPPING, -1600, 0)

    elif mat_type == "NO PARENT":
        if "Sky" not in mat.name:
            N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Base")
            link(N_SHADER.outputs["BSDF"], N_OUTPUT.inputs["Surface"])
        elif "Sky" in mat.name:
            N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Skybox")
            link(N_SHADER.outputs["Shader"], N_OUTPUT.inputs["Surface"])

    elif mat_type in types_base:
        N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Base")
        link(N_SHADER.outputs["BSDF"], N_OUTPUT.inputs["Surface"])

    else:
        N_SHADER.node_tree = get_valorant_shader(group_name="VALORANT_Base")
        N_SHADER.inputs["DF"].default_value = (1, 0, 0, 1)
        link(N_SHADER.outputs["BSDF"], N_OUTPUT.inputs["Surface"])
        return

    nodes_textures = get_textures(settings=settings, mat=mat, override=override, mat_props=mat_props, shader=N_SHADER, mapping=N_MAPPING)
    # !SECTION

    if "BasePropertyOverrides" in mat_props:
        for prop_name, prop_value in mat_props["BasePropertyOverrides"].items():

            # ANCHOR Shading Model
            if "ShadingModel" == prop_name:
                if "MSM_AresEnvironment" in prop_value:
                    pass
                if "MSM_Unlit" in prop_value:
                    pass

            # ANCHOR Blend Mode
            if "BlendMode" == prop_name:
                if "BLEND_Translucent" in prop_value:
                    blend_mode = BlendMode.BLEND
                elif "BLEND_Masked" in prop_value:
                    blend_mode = BlendMode.CLIP
                elif "BLEND_Additive" in prop_value:
                    blend_mode = BlendMode.BLEND
                elif "BLEND_Modulate" in prop_value:
                    blend_mode = BlendMode.BLEND
                elif "BLEND_AlphaComposite" in prop_value:
                    blend_mode = BlendMode.BLEND
                elif "BLEND_AlphaHoldout" in prop_value:
                    blend_mode = BlendMode.CLIP

            if "OpacityMaskClipValue" == prop_name:
                mat.alpha_threshold = prop_value
                pass

            # -----------------------------------------------
            # LOGGING
            if prop_name not in BasePropertyOverrides:
                BasePropertyOverrides[prop_name] = []
            BasePropertyOverrides[prop_name].append(mat_props["BasePropertyOverrides"][prop_name])
            BasePropertyOverrides[prop_name] = list(dict.fromkeys(BasePropertyOverrides[prop_name]))

    if "StaticParameters" in mat_props:
        if "StaticSwitchParameters" in mat_props["StaticParameters"]:
            for param in mat_props["StaticParameters"]["StaticSwitchParameters"]:
                param_name = param["ParameterInfo"]["Name"].lower()

                if "use min light brightness color" in param_name and "Use MLB Color" in N_SHADER.inputs:
                    if param["Value"]:
                        N_SHADER.inputs["Use MLB Color"].default_value = 1

                if "blend tint only" in param_name and "Blend Tint Only" in N_SHADER.inputs:
                    if param["Value"]:
                        N_SHADER.inputs["Blend Tint Only"].default_value = 1

                if "use 2 diffuse maps" in param_name and "Use 2 DF Maps" in N_SHADER.inputs:
                    if param["Value"]:
                        N_SHADER.inputs["Use 2 DF Maps"].default_value = 1
                    else:
                        N_SHADER.inputs["Use 2 DF Maps"].default_value = 0

                if "use 2 normal maps" in param_name and "Use 2 NM Maps" in N_SHADER.inputs:
                    if param["Value"]:
                        N_SHADER.inputs["Use 2 NM Maps"].default_value = 1
                    else:
                        N_SHADER.inputs["Use 2 NM Maps"].default_value = 0

                if "invert alpha (texture)" in param_name and "Invert Alpha" in N_SHADER.inputs:
                    if param["Value"]:
                        N_SHADER.inputs["Invert Alpha"].default_value = 1

                if "use vertex color" in param_name:
                    if obj_data.vertex_colors:
                        mat_switches.append(param_name)
                        if "Vertex Color" in N_SHADER.inputs:
                            link(N_VERTEX.outputs["Color"], N_SHADER.inputs["Vertex Color"])
                        if "Use Vertex Color" in N_SHADER.inputs:
                            N_SHADER.inputs["Use Vertex Color"].default_value = 1

                if "use vertex alpha" in param_name:
                    if obj_data.vertex_colors:
                        mat_switches.append(param_name)
                        if "Vertex Alpha" in N_SHADER.inputs:
                            link(N_VERTEX.outputs["Alpha"], N_SHADER.inputs["Vertex Alpha"])
                        if "Use Vertex Alpha" in N_SHADER.inputs:
                            N_SHADER.inputs["Use Vertex Alpha"].default_value = 1

                if "use alpha as emissive" in param_name:
                    mat_switches.append("use alpha as emissive")
                    if "Use Alpha as Emissive" in N_SHADER.inputs:
                        N_SHADER.inputs["Use Alpha as Emissive"].default_value = 1
                    else:
                        pass
                # LOGGING
                StaticParameterValues.append(param['ParameterInfo']['Name'].lower())

        if "StaticComponentMaskParameters" in mat_props["StaticParameters"]:
            for param in mat_props["StaticParameters"]["StaticComponentMaskParameters"]:
                param_name = param["ParameterInfo"]["Name"].lower()
                if param_name == "mask":
                    # MASK = "R"
                    colors = {"R", "G", "B", "A"}
                    for color in colors:
                        if color in param:
                            if param[color]:
                                if f"Use {color}" in N_SHADER.inputs:
                                    N_SHADER.inputs[f"Use {color}"].default_value = 1

    if "ScalarParameterValues" in mat_props:
        for param in mat_props["ScalarParameterValues"]:
            param_name = param['ParameterInfo']['Name'].lower()

            if "metallic" in param_name and "Metallic Strength" in N_SHADER.inputs:
                N_SHADER.inputs["Metallic Strength"].default_value = param["ParameterValue"]

            if "alpha" in param_name and "Alpha Strength" in N_SHADER.inputs:
                N_SHADER.inputs["Alpha Strength"].default_value = param["ParameterValue"]

            if "emissive_base_power" in param_name and "Emissive_Base_Power" in N_SHADER.inputs:
                N_SHADER.inputs["Emissive_Base_Power"].default_value = param["ParameterValue"]

            if "mask blend power" in param_name and "Vertex Blend" in N_SHADER.inputs:
                N_SHADER.inputs["Vertex Blend"].default_value = param["ParameterValue"]

            if "disolve_u_scale" in param_name and "U" in N_MAPPING.inputs:
                N_MAPPING.inputs["U"].default_value = param["ParameterValue"]

            if "disolve_v_scale" in param_name and "V" in N_MAPPING.inputs:
                N_MAPPING.inputs["V"].default_value = param["ParameterValue"]

            if "opacity (main)" in param_name and "Opacity (Main)" in N_SHADER.inputs:
                N_SHADER.inputs["Opacity (Main)"].default_value = param["ParameterValue"]

            if "alpha1_power" in param_name and "Alpha1_Power" in N_SHADER.inputs:
                N_SHADER.inputs["Alpha1_Power"].default_value = param["ParameterValue"]

            if "alpha_colormult" in param_name and "Alpha_ColorMult" in N_SHADER.inputs:
                N_SHADER.inputs["Alpha_ColorMult"].default_value = param["ParameterValue"]

            if "alpha_base_power" in param_name and "Alpha_Base_Power" in N_SHADER.inputs:
                N_SHADER.inputs["Alpha_Base_Power"].default_value = param["ParameterValue"]

            if N_MAPPING:
                if "alpha_offsetv" in param_name and "Offset V" in N_MAPPING.inputs:
                    N_MAPPING.inputs["Offset V"].default_value = param["ParameterValue"]

            if N_MAPPING:
                if "alpha_scalev" in param_name and "Size V" in N_MAPPING.inputs:
                    N_MAPPING.inputs["Size V"].default_value = param["ParameterValue"]

            # if "roughness mult" in param_name and "Roughness Strength" in N_SHADER.inputs:
            #     # print(param_name, param["ParameterValue"] * 0.1)
            #     N_SHADER.inputs["Roughness Strength"].default_value = param["ParameterValue"]
            if "min light brightness" in param_name:
                pass
                # print(param["ParameterValue"])
                # print()
                # N_SHADER.inputs["Emission Strength"].default_value = param["ParameterValue"]

            if "normal" in param_name and "Normal Strength" in N_SHADER.inputs:
                N_SHADER.inputs["Normal Strength"].default_value = param["ParameterValue"]

            # LOGGING
            ScalarParameterValues.append(param_name)

    if "VectorParameterValues" in mat_props:
        color_pos_x = -700
        color_pos_y = 470
        for param in mat_props["VectorParameterValues"]:
            param_name = param['ParameterInfo']['Name'].lower()
            param_value = param["ParameterValue"]

            yo = create_node_color(nodes, param_name, get_rgb(param_value), color_pos_x, color_pos_y)
            color_pos_x += 200

            if "color" in param_name:
                if "Color" in N_SHADER.inputs:
                    N_SHADER.inputs["Color"].default_value = get_rgb(param_value)

            if "diffusecolor" in param_name:
                if "Diffuse Color" in N_SHADER.inputs:
                    N_SHADER.inputs["Diffuse Color"].default_value = get_rgb(param_value)

            if "color mult" in param_name:
                if "Tint" in N_SHADER.inputs:
                    N_SHADER.inputs["Tint"].default_value = get_rgb(param_value)

            if "ao color" in param_name:
                if "AO Color" in N_SHADER.inputs:
                    N_SHADER.inputs["AO Color"].default_value = get_rgb(param_value)

            if "lightmass-only vertex color" in param_name:
                if "VC" in N_SHADER.inputs:
                    N_SHADER.inputs["VC"].default_value = get_rgb(param_value)

            if "emissive mult" in param_name:
                if "Emissive Mult" in N_SHADER.inputs:
                    N_SHADER.inputs["Emissive Mult"].default_value = get_rgb(param_value)

            if "min light brightness color" in param_name:
                if "ML Brightness" in N_SHADER.inputs:
                    N_SHADER.inputs["ML Brightness"].default_value = get_rgb(param_value)
                if "MLB" in N_SHADER.inputs:
                    N_SHADER.inputs["MLB"].default_value = get_rgb(param_value)

            if "color_1" in param_name:
                if "Color 1" in N_SHADER.inputs:
                    N_SHADER.inputs["Color 1"].default_value = get_rgb(param_value)

            if "color_2" in param_name:
                if "Color 2" in N_SHADER.inputs:
                    N_SHADER.inputs["Color 2"].default_value = get_rgb(param_value)
            if "line color" in param_name:
                if "line color" in N_SHADER.inputs:
                    N_SHADER.inputs["line color"].default_value = get_rgb(param_value)
            if "layer a tint" in param_name:
                if "Tint" in N_SHADER.inputs:
                    N_SHADER.inputs["Tint"].default_value = get_rgb(param_value)
            if "layer b tint" in param_name:
                if "Tint B" in N_SHADER.inputs:
                    N_SHADER.inputs["Tint B"].default_value = get_rgb(param_value)
            VectorParameterValues.append(param['ParameterInfo']['Name'].lower())

    # --------------------------------------------
    # Set up material using the datas

    mat.blend_method = blend_mode.name
    mat.shadow_method = 'OPAQUE' if blend_mode.name == 'OPAQUE' else 'HASHED'

    if obj_data.vertex_colors:
        # mat_switches.append(param_name)
        # if "Use Vertex Color" in N_SHADER.inputs:
        #     link(N_VERTEX.outputs["Color"], N_SHADER.inputs["Vertex Color"])
        # mat.name = mat.name + "_V"
        if "Vertex Color" in N_SHADER.inputs:
            link(N_VERTEX.outputs["Color"], N_SHADER.inputs["Vertex Color"])

        if "Vertex" in N_SHADER.inputs:
            link(N_VERTEX.outputs["Color"], N_SHADER.inputs["Vertex"])

        if mat_type == "NO PARENT":
            if "DF" in N_SHADER.inputs:
                link(N_VERTEX.outputs["Color"], N_SHADER.inputs["DF"])

        if user_mat_type == "Blend":
            if "Vertex Color" in N_SHADER.inputs:
                link(N_VERTEX.outputs["Color"], N_SHADER.inputs["Vertex Color"])
            if "Vertex Alpha" in N_SHADER.inputs:
                link(N_VERTEX.outputs["Alpha"], N_SHADER.inputs["Vertex Alpha"])

        if user_mat_type in "Waterfallvista":
            link(N_VERTEX.outputs["Alpha"], N_SHADER.inputs["Vertex_Alpha"])
    else:
        pass
        # mat.name = mat.name + "_NV"

    # ANCHOR Set up Textures!
    node_tex: bpy.types.Node
    for key, node_tex in nodes_textures.items():
        # print(key, node_tex)
        if key == "diffuse":
            if "DF" in N_SHADER.inputs:
                link(node_tex.outputs["Color"], N_SHADER.inputs["DF"])
                if blend_mode == BlendMode.CLIP or blend_mode == BlendMode.BLEND:
                    if "Alpha" in N_SHADER.inputs and user_mat_type != "Glass":
                        link(node_tex.outputs["Alpha"], N_SHADER.inputs["Alpha"])
                    if "Glass" in user_mat_type:
                        N_SHADER.inputs["Alpha"].default_value = 0.5

            if "DF Alpha" in N_SHADER.inputs:
                link(node_tex.outputs["Alpha"], N_SHADER.inputs["DF Alpha"])

            if "Diffuse" in N_SHADER.inputs:
                if user_mat_type == "Blend":
                    link(node_tex.outputs["Color"], N_SHADER.inputs["Diffuse"])
                    link(node_tex.outputs["Alpha"], N_SHADER.inputs["Diffuse Alpha"])
                # if blend_mode == BlendMode.CLIP or blend_mode == BlendMode.BLEND:
                #     if "Alpha" in N_SHADER.inputs and user_mat_type != "Glass":
                #         link(node_tex.outputs["Alpha"], N_SHADER.inputs["Alpha"])

        if key == "diffuse b":
            if "DF B" in N_SHADER.inputs and "DF B Alpha" in N_SHADER.inputs:
                link(node_tex.outputs["Color"], N_SHADER.inputs["DF B"])
                link(node_tex.outputs["Alpha"], N_SHADER.inputs["DF B Alpha"])

        if key == "mra":
            if "MRA" in N_SHADER.inputs:
                link(node_tex.outputs["Color"], N_SHADER.inputs["MRA"])
        if key == "mra b":
            if "MRA B" in N_SHADER.inputs:
                link(node_tex.outputs["Color"], N_SHADER.inputs["MRA B"])
        if key == "normal":
            if "NM" in N_SHADER.inputs:
                link(node_tex.outputs["Color"], N_SHADER.inputs["NM"])
            if "Normal" in N_SHADER.inputs:
                link(node_tex.outputs["Color"], N_SHADER.inputs["Normal"])

        if key == "mask":
            if "RGBA Color" in N_SHADER.inputs:
                link(node_tex.outputs["Color"], N_SHADER.inputs["RGBA Color"])
                link(node_tex.outputs["Alpha"], N_SHADER.inputs["RGBA Alpha"])
            if "Mask" in N_SHADER.inputs:
                link(node_tex.outputs["Color"], N_SHADER.inputs["Mask"])

        if key == "normal b" and "NM B" in N_SHADER.inputs:
            link(node_tex.outputs["Color"], N_SHADER.inputs["NM B"])

        if key == "emissive_base":
            if "LS_Color" in N_SHADER.inputs:
                link(node_tex.outputs["Color"], N_SHADER.inputs["LS_Color"])

        if key == "alpha_base":
            if "LS_Alpha" in N_SHADER.inputs:
                link(node_tex.outputs["Color"], N_SHADER.inputs["LS_Alpha"])
                node_tex.extension = "EXTEND"
                N_SHADER.inputs["Cache Switch"].default_value = 1
                if N_MAPPING:
                    link(N_MAPPING.outputs["Mapping"], node_tex.inputs["Vector"])

        # if key == "mask" or key == "rgba":
        #     pass
            # if decal:
            #     link(node.outputs["Color"], N_SHADER.inputs["Mask"])
            #     link(node.outputs["Alpha"], N_SHADER.inputs["Alpha"])
            # elif "Mask" in N_SHADER.inputs and mat_type == "BaseEnvEmissiveLCDScreen_MAT":
            #     link(node.outputs["Alpha"], N_SHADER.inputs["Mask"])

            #     node_rgb_mapping = nodes.new(type="ShaderNodeMapping")
            #     node_rgb_uv = nodes.new(type="ShaderNodeUVMap")

            #     blender.set_node_position(node_rgb_mapping, node.location.x - 200, node.location.y)
            #     blender.set_node_position(node_rgb_uv, node.location.x - 400, node.location.y)

            #     link(node_rgb_uv.outputs["UV"], node_rgb_mapping.inputs["Vector"])
            #     link(node_rgb_mapping.outputs["Vector"], node.inputs["Vector"])

            #     ut = get_scalar_value(mat_props, "U Tile")
            #     vt = get_scalar_value(mat_props, "V Tile")
            #     if ut is not None and vt is not None:
            #         node_rgb_mapping.inputs["Scale"].default_value = [ut, vt, 1]

            # else:
            #     # link(node.outputs["Color"], N_SHADER.inputs["Diffuse"])
            #     if "Alpha" in N_SHADER.inputs:
            #         link(node.outputs["Alpha"], N_SHADER.inputs["Alpha"])

        # if key == "LCDScreenRGB_TEX":
        #     if "RGB Texture" in N_SHADER.inputs:
        #         # Link to
        #         link(node_tex.outputs["Color"], N_SHADER.inputs["RGB Texture"])

        #         node_rgb_mapping = nodes.new(type="ShaderNodeMapping")
        #         node_rgb_uv = nodes.new(type="ShaderNodeUVMap")

        #         blender.set_node_position(node_rgb_mapping, node_tex.location.x - 200, node_tex.location.y)
        #         blender.set_node_position(node_rgb_uv, node_tex.location.x - 400, node_tex.location.y)

        #         link(node_rgb_uv.outputs["UV"], node_rgb_mapping.inputs["Vector"])
        #         link(node_rgb_mapping.outputs["Vector"], node_tex.inputs["Vector"])

        #         sv = get_scalar_value(mat_props, "RGB Scale")
        #         if sv is not None:
        #             node_rgb_mapping.inputs["Scale"].default_value = [sv, sv, sv]

        # if key == "mask" and "Alpha" in N_SHADER.inputs:
        #     link(node.outputs["Color"], N_SHADER.inputs["Alpha"])
        # if key == "normal b":
        #     link(node.outputs["Color"], N_SHADER.inputs["NM_B"])
        # if key == "albedo":
        #     link(node.outputs["Color"], N_SHADER.inputs["DF_A"])
        #     if BLEND_Masked:
        #         link(node.outputs["Alpha"], N_SHADER.inputs["Alpha"])

    # !SECTION
    # Custom Overrides
    if "GlassShardGlow" in mat.name:
        N_SHADER.inputs["Only Glow"].default_value = 1
        N_SHADER.inputs["Emission Strength"].default_value = 15


def get_scalar_value(mat_props, s_param_name):
    if "ScalarParameterValues" in mat_props:
        for param in mat_props["ScalarParameterValues"]:
            param_name = param['ParameterInfo']['Name'].lower()
            if s_param_name.lower() in param_name:
                return param["ParameterValue"]

# SECTION Get Textures
# NOTE: Might be tuned bit more


def get_image(tex_name, tex_local_path):
    img = bpy.data.images.get(tex_name + ".png")
    if img is None:
        img = bpy.data.images.load(tex_local_path)
    return img


def get_textures(settings: Settings, mat: bpy.types.Material, override: bool, mat_props: dict, shader, mapping):
    nodes_texture = {}
    if "TextureParameterValues" in mat_props:
        pos = [-700, 0]
        if override:
            pos = [-1000, 0]
        index = 0
        for param in mat_props["TextureParameterValues"]:

            tex_game_path = get_texture_path(s=param, f=settings.texture_format)
            tex_local_path = settings.assets_path.joinpath(tex_game_path).__str__()
            param_name = param['ParameterInfo']['Name'].lower()
            tex_name = Path(tex_local_path).stem

            if "diffuse b low" not in param_name:
                if Path(tex_local_path).exists() and tex_name not in BLACKLIST_textures:
                    pos[1] = index * -270
                    index += 1
                    tex_image_node: bpy.types.Node
                    tex_image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                    tex_image_node.image = get_image(tex_name, tex_local_path)  # bpy.data.images.load(tex_local_path)
                    tex_image_node.image.alpha_mode = "CHANNEL_PACKED"
                    tex_image_node.label = param["ParameterInfo"]["Name"]
                    tex_image_node.location[0] = pos[0]
                    tex_image_node.location[1] = pos[1]

                    if "diffuse" == param_name or "diffuse a" == param_name or "albedo" == param_name or "texture a" == param_name:
                        nodes_texture["diffuse"] = tex_image_node
                    if "mra" == param_name or "mra a" == param_name:
                        tex_image_node.image.colorspace_settings.name = "Non-Color"
                        nodes_texture["mra"] = tex_image_node
                    if "normal" == param_name or "texture a normal" == param_name or "normal a" == param_name:
                        tex_image_node.image.colorspace_settings.name = "Non-Color"
                        nodes_texture["normal"] = tex_image_node
                    if "normal b" == param_name or "texture b normal" == param_name:
                        tex_image_node.image.colorspace_settings.name = "Non-Color"
                        nodes_texture["normal b"] = tex_image_node
                    if "mask" in param_name or "rgba" in param_name:
                        tex_image_node.image.colorspace_settings.name = "Raw"
                        nodes_texture["mask"] = tex_image_node

                    else:
                        nodes_texture[param_name] = tex_image_node
                        # LOGGING
                    TextureParameterValues.append(param['ParameterInfo']['Name'].lower())

    if "CachedReferencedTextures" in mat_props:
        pos = [-1300, 0]
        if override:
            pos = [-1300, 0]
        i = 0
        textures = mat_props["CachedReferencedTextures"]
        for index, param, in enumerate(textures):
            if param is not None:

                texture_name_raw = param["ObjectName"].replace("Texture2D ", "")
                if texture_name_raw not in BLACKLIST_textures:
                    texture_path_raw = param["ObjectPath"]

                    tex_game_path = get_texture_path_yo(s=texture_path_raw, f=settings.texture_format)
                    tex_local_path = settings.assets_path.joinpath(tex_game_path).__str__()

                    if Path(tex_local_path).exists():
                        pos[1] = i * -270
                        i += 1
                        tex_image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                        tex_image_node.image = get_image(Path(tex_local_path).stem, tex_local_path)  # bpy.data.images.load(tex_local_path)
                        tex_image_node.image.alpha_mode = "CHANNEL_PACKED"
                        tex_image_node.label = texture_name_raw
                        tex_image_node.location = [pos[0], pos[1]]

                        if shader.node_tree == get_valorant_shader(group_name="VALORANT_Ventsmoke"):
                            if texture_name_raw == "SmokeGradient_TFX":
                                mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["Smoke_Gradient"])
                                tex_image_node.image.colorspace_settings.name = "Non-Color"

                            if texture_name_raw == "VentSmoke_Mask":
                                mat.node_tree.links.new(mapping.outputs["Mapping"], tex_image_node.inputs["Vector"])
                                mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["Ventsmoke"])
                                tex_image_node.image.colorspace_settings.name = "Non-Color"

                        if shader.node_tree == get_valorant_shader(group_name="VALORANT_Waterfall"):
                            if texture_name_raw == "Waterfall_Disolve_Blur_TFX":
                                mat.node_tree.links.new(mapping.outputs["UV"], tex_image_node.inputs["Vector"])
                                mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["Waterfall_Disolve_Blur"])

                            elif texture_name_raw == "Waterfall_Wave_TFX":
                                mat.node_tree.links.new(mapping.outputs["UV"], tex_image_node.inputs["Vector"])
                                mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["Waterfall_Wave"])

                            elif texture_name_raw == "Waterfall_BaseMask_TFX":
                                mat.node_tree.links.new(mapping.outputs["UV"], tex_image_node.inputs["Vector"])
                                mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["Waterfall_BaseMask"])

                            elif texture_name_raw == "Waterfall_Ripples_TFX":
                                mat.node_tree.links.new(mapping.outputs["Vector"], tex_image_node.inputs["Vector"])
                                mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["Waterfall_Ripples"])
                                tex_image_node.extension = "EXTEND"

                        if texture_name_raw == "GlowA01_DIFF":
                            if "Alpha" in shader.inputs:
                                mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["Alpha"])
                                tex_image_node.extension = "EXTEND"

                        if texture_name_raw == "GradientVertB_TEX":
                            if "Gradient_Cache" in shader.inputs:
                                mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["Gradient_Cache"])
                                tex_image_node.extension = "EXTEND"

                        if "_DF" in texture_name_raw:
                            nodes_texture["diffuse"] = tex_image_node

                        else:
                            nodes_texture[texture_name_raw] = tex_image_node

                        TextureParameterValues.append(texture_name_raw.lower())

    elif "CachedExpressionData" in mat_props:
        pos = [-1300, 0]
        i = 0
        if "ReferencedTextures" in mat_props["CachedExpressionData"]:
            textures = mat_props["CachedExpressionData"]["ReferencedTextures"]
            for index, param, in enumerate(textures):
                if param is not None:

                    texture_name_raw = param["ObjectName"].replace("Texture2D ", "")
                    if texture_name_raw not in BLACKLIST_textures:
                        texture_path_raw = param["ObjectPath"]

                        tex_game_path = get_texture_path_yo(s=texture_path_raw, f=settings.texture_format)
                        tex_local_path = settings.assets_path.joinpath(tex_game_path).__str__()

                        if Path(tex_local_path).exists():
                            pos[1] = i * -270
                            i += 1
                            tex_image_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                            tex_image_node.image = get_image(Path(tex_local_path).stem, tex_local_path)
                            tex_image_node.image.alpha_mode = "CHANNEL_PACKED"
                            tex_image_node.label = texture_name_raw
                            tex_image_node.location = [pos[0], pos[1]]

                            if "_mk" in texture_name_raw:
                                if "MRA" in shader.inputs:
                                    mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["MRA"])
                                    shader.inputs["Metallic"].default_value = -1
                                    shader.inputs["Roughness"].default_value = -1
                                    shader.inputs["AO Strength"].default_value = 0.15

                            if "_DF" in texture_name_raw and "Edging_DF" not in texture_name_raw and "Blank" not in texture_name_raw:
                                if "DF" in shader.inputs:
                                    mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["DF"])
                                    mat.node_tree.links.new(tex_image_node.outputs["Alpha"], shader.inputs["Alpha"])
                                    mat.node_tree.links.new(tex_image_node.outputs["Alpha"], shader.inputs["DF Alpha"])

                            if "_NM" in texture_name_raw:
                                if "NM" in shader.inputs:
                                    mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["NM"])

                            if "_MRA" in texture_name_raw:
                                if "MRA" in shader.inputs:
                                    mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["MRA"])

                            if "T_CGSkies_0091_ascent_DF" in texture_name_raw:
                                if "Light" in shader.inputs:
                                    mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["Light"])

                                    world_nodes = bpy.context.scene.world.node_tree.nodes
                                    world_nodes.clear()

                                    node_background = world_nodes.new(type='ShaderNodeBackground')
                                    node_output = world_nodes.new(type='ShaderNodeOutputWorld')
                                    node_output.location = 200, 0

                                    node_environment = world_nodes.new('ShaderNodeTexEnvironment')
                                    node_environment.image = bpy.data.images.load(tex_local_path)
                                    node_environment.label = texture_name_raw
                                    node_environment.location = -300, 0

                                    links = bpy.context.scene.world.node_tree.links
                                    links.new(node_environment.outputs["Color"], node_background.inputs["Color"])
                                    links.new(node_background.outputs["Background"], node_output.inputs["Surface"])

                            if "Skybox" in texture_name_raw:
                                if "Background" in shader.inputs:
                                    mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["Background"])

    return nodes_texture
# !SECTION


# ANCHOR : IMPORTERS


def filter_objects(umap_DATA, settings) -> list:

    objects = umap_DATA
    filtered_list = []

    # if settings.debug.SELECTIVE_OBJECTS:

    # Debug check
    if debug.SELECTIVE_OBJECTS:
        for filter_model_name in debug.SELECTIVE_OBJECTS:
            for og_model in objects:
                object_type = get_object_type(og_model)
                if object_type == "mesh":
                    if filter_model_name in og_model["Properties"]["StaticMesh"]["ObjectPath"]:
                        og_model["Name"] = og_model["Properties"]["StaticMesh"]["ObjectPath"]
                        filtered_list.append(og_model)

                elif object_type == "decal":
                    if filter_model_name in og_model["Outer"]:
                        og_model["Name"] = og_model["Outer"]
                        filtered_list.append(og_model)

                elif object_type == "light":
                    if filter_model_name in og_model["Outer"]:
                        og_model["Name"] = og_model["Outer"]
                        filtered_list.append(og_model)

    else:
        filtered_list = objects

    new_list = []

    def is_blacklisted(object_name: str) -> bool:
        for blocked in BLACKLIST_objects:
            if blocked.lower() in object_name.lower():
                return True
        return False

    # Check for settings.debug.BLACKLISTed items
    for og_model in filtered_list:
        model_name_lower = get_object_name(data=og_model, mat=False).lower()

        if is_blacklisted(model_name_lower):
            continue
        else:
            new_list.append(og_model)

    return new_list


def import_umap(settings: Settings, umap_data: dict, umap_name: str):
    logger.info(f"Processing : {umap_name}")

    main_scene = bpy.data.scenes["Scene"]
    map_name = settings.selected_map.name.capitalize() 

    if map_name not in bpy.data.collections:
        map_collection = bpy.data.collections.new(map_name)
        main_scene.collection.children.link(map_collection)
    else:
        map_collection = bpy.data.collections.get(map_name)

    

    # import_collection = bpy.data.collections.get(umap_name)
    import_collection = bpy.data.collections.new(umap_name)
    map_collection.children.link(import_collection)

    objectsToImport = filter_objects(umap_data, settings)
    decals_collection = bpy.data.collections.new(umap_name + "_Decals")
    lights_collection = bpy.data.collections.new(umap_name + "_Lights")

    import_collection.children.link(decals_collection)
    import_collection.children.link(lights_collection)

    if debug.COUNT != 0:
        objectsToImport = objectsToImport[:debug.COUNT]

    for object_index, object_data in enumerate(objectsToImport):
        object_index = f"{object_index:03}"
        object_type = get_object_type(object_data)

        if object_type == "mesh":
            if "EMPTY" in umap_name:
                continue

            map_object = MapObject(settings=settings, data=object_data, umap_name=umap_name)
            imported_object = import_object(map_object=map_object, target_collection=import_collection, object_index=object_index)
            if imported_object:
                set_materials(settings=settings, byo=imported_object, map_object=map_object)

        if object_type == "decal" and settings.import_decals:

            if "DecalSize" in object_data["Properties"]:
                size = object_data["Properties"]["DecalSize"]
                decal_size = (size["X"] * 0.01, size["Y"] * 0.01, size["Z"] * 0.01)
            else:
                decal_size = (1, 1, 1)
            bpy.ops.mesh.primitive_cube_add(size=2, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=decal_size)
            decal_object = bpy.context.active_object
            decal_object.name = object_data["Outer"]
            set_properties(byo=decal_object, object=object_data["Properties"], is_instanced=False)

            set_materials(settings=settings, byo=decal_object, map_object=object_data, decal=True)

            decals_collection.objects.link(decal_object)
            main_scene.collection.objects.unlink(decal_object)

        if object_type == "light" and settings.import_lights:
            # Set variables
            light_type = get_light_type(object_data)
            light_name = object_data["Outer"]
            light_props = object_data["Properties"]

            logger.info(f"[{object_index}] | Lighting : {light_name}")

            light_data = bpy.data.lights.new(name=light_name, type=light_type)
            light_object = bpy.data.objects.new(name=light_name, object_data=light_data)
            lights_collection.objects.link(light_object)

            for prop_name, prop_value in light_props.items():
                OtherTypes.append(prop_name)

                if "Intensity" == prop_name:
                    if light_type == "POINT":
                        light_object.data.energy = prop_value * 10
                    if light_type == "AREA":
                        light_object.data.energy = prop_value * 10
                    if light_type == "SPOT":
                        light_object.data.energy = prop_value * 10
                if "LightColor" == prop_name:
                    light_object.data.color = get_rgb_255(prop_value)[:-1]
                if "SourceRadius" == prop_name:
                    if light_type == "SPOT":
                        light_object.data.shadow_soft_size = prop_value * 0.01
                    else:
                        light_object.data.shadow_soft_size = prop_value * 0.1

                if light_type == "AREA":
                    light_object.data.shape = 'RECTANGLE'
                    if "SourceWidth" == prop_name:
                        light_object.data.size = prop_value * 0.01
                    if "SourceHeight" == prop_name:
                        light_object.data.size_y = prop_value * 0.01

                if light_type == "SPOT":
                    if "InnerConeAngle" == prop_name:
                        light_object.data.spot_blend = 1
                    if "OuterConeAngle" == prop_name:
                        light_object.data.spot_size = prop_value * 0.01

                set_properties(byo=light_object, object=light_props, is_light=True)

    if len(decals_collection.objects) <= 0:
        bpy.data.collections.remove(decals_collection)
    if len(lights_collection.objects) <= 0:
        bpy.data.collections.remove(lights_collection)

    with redirect_stdout(stdout):
        if not settings.debug:
            if settings.textures == "pack":
                bpy.ops.file.pack_all()
            if settings.textures == "local":
                bpy.ops.file.pack_all()
                bpy.ops.file.unpack_all(method='WRITE_LOCAL')
                bpy.ops.file.make_paths_relative()
                logger.info(f"Extracted : {umap_name}'s textures to {shorten_path(settings.selected_map.scenes_path.joinpath('textures').__str__(), 4)}")

            map_path = settings.selected_map.scenes_path.joinpath(umap_name).__str__()
            bpy.ops.wm.save_as_mainfile(filepath=map_path + ".blend", compress=True)
            logger.info(f"Saved : {umap_name}.blend to {shorten_path(map_path.__str__(), 4)}")


def import_object(map_object: MapObject, target_collection: bpy.types.Collection, object_index: int):
    scene = bpy.data.scenes["Scene"]

    link = target_collection.objects.link
    scene_unlink = scene.collection.objects.unlink
    collection_unlink = target_collection.objects.unlink
    master_object = None

    if not Path(map_object.model_path).exists():
        return False

    master_object: bpy.types.Object
    master_object = get_object(map_object, object_index, link)

    if "LODData" in map_object.data:
        lod_data = map_object.data["LODData"][0]
        # Vertex colors
        if "OverrideVertexColors" in lod_data:
            if "Data" in lod_data["OverrideVertexColors"]:
                vertex_colors_hex = lod_data["OverrideVertexColors"]["Data"]

                mo = master_object.data
                #vertex_color_layer_name = "OverrideVertexColors"

                if not mo.vertex_colors:
                    mo.vertex_colors.new(name="Col", do_init=False)

                color_layer = mo.vertex_colors["Col"]  # !TODO: #2 use umap name instead and rework the way vertex colors are handled

                # this should be cleaned up a bit.. later..
                # unpack_4uint8 = unpack_4uint8
                for idx, loop in enumerate(mo.loops):
                    vertex_color_hex = vertex_colors_hex[loop.vertex_index]
                    r, g, b, a = unpack_4uint8(bytes.fromhex(vertex_color_hex))
                    color_layer.data[idx].color = (color_linear_to_srgb(r / 255),
                                                   color_linear_to_srgb(g / 255),
                                                   color_linear_to_srgb(b / 255),
                                                   a / 255)

    # Let's goooooooo!
    if map_object.is_instanced():

        instance_data = map_object.data["PerInstanceSMData"]

        # bpy.ops.object.empty_add(type='PLAIN_AXES')
        # instance_group = bpy.context.active_object
        instance_group = bpy.data.objects.new(map_object.name + "-GRP", None)
        # instance_group.name = map_object.name + "-GRP"

        link(instance_group)
        # scene_unlink(instance_group)

        master_object.parent = instance_group

        # move_collection(instanced_collection, instance_group, scene)
        reset_properties(instance_group)
        set_properties(byo=instance_group, object=map_object.data["Properties"], is_instanced=False)

        master_object.hide_viewport = True
        master_object.hide_render = True

        for index, instance_data in enumerate(instance_data):
            instance_object = master_object.copy()
            instance_object.hide_viewport = False
            instance_object.hide_render = False
            link(instance_object)

            set_properties(instance_object, instance_data, is_instanced=True)
            logger.info(f"[{object_index}] | Instancing : {shorten_path(map_object.model_path, 4)}")

        master_object.hide_viewport = True
        master_object.hide_render = True

    else:
        master_object.hide_viewport = False
        master_object.hide_render = False

    set_properties(byo=master_object, object=map_object.data["Properties"], is_instanced=False)

    return master_object


# ANCHOR Post Processing

def combine_umaps(settings: Settings):

    # ! Import other .blend files back!
    # a = settings.debug.SELECTIVE_UMAP or settings.selected_map.umaps
    # print(settings.selected_map)

    logger.info(f"Combining : {settings.selected_map.name.capitalize()}'s parts to a single blend file...")

    for umap in settings.selected_map.umaps:
        umap_name = os.path.splitext(os.path.basename(umap))[0]
        umap_blend_file = settings.selected_map.scenes_path.joinpath(umap_name).__str__() + ".blend"

        # logger.info(settings.combine_method)
        sec = "\\Collection\\"
        obj = umap_name

        fp = umap_blend_file + sec + obj
        dr = umap_blend_file + sec

        if Path(umap_blend_file).exists():

            if settings.combine_method == "append":
                bpy.ops.wm.append(filepath=fp, filename=obj, directory=dr)
            if settings.combine_method == "link":
                bpy.ops.wm.link(filepath=fp, filename=obj, directory=dr)


def post_import(settings: Settings):
    with redirect_stdout(stdout):
        
        map_path = settings.selected_map.scenes_path.joinpath(settings.selected_map.name.capitalize()).__str__()
        bpy.ops.wm.save_as_mainfile(filepath=map_path + ".blend", compress=True)

        # ! Clear everything
        clean_scene()

        combine_umaps(settings=settings)

        # eliminate_materials()
        remove_duplicate_mats()
        clear_duplicate_node_groups()

        # ! Utility to pack
        if settings.textures == "pack":
            bpy.ops.file.pack_all()
        if settings.textures == "local":
            bpy.ops.file.unpack_all(method='WRITE_LOCAL')
            logger.info("Unpacked local textures")

        bpy.ops.wm.save_as_mainfile(filepath=map_path + ".blend", compress=True)
        logger.info(f"Saved Combined : '{settings.selected_map.name.capitalize()}.blend' to {shorten_path(map_path, 4)}")


# ANCHOR MAIN FUNCTION

def import_map(addon_prefs):
    """
    Main function
    Args:
        settings (dict): Settings to usePath
    """

    os.system("cls")
    settings = Settings(addon_prefs)

    logger = setup_logger(__name__, settings.maps_path.joinpath("import.log").__str__())

    if (not addon_prefs.isInjected) and addon_prefs.usePerfPatch:
        inject_dll(os.getpid(), settings.dll_path.__str__())
        addon_prefs.isInjected = True

    #  Check if the game files are exported
    extract_assets(settings)

    # Clear the scene
    clean_scene()

    # Import the shaders
    import_shaders(settings)
    clear_duplicate_node_groups()

    umap_json_paths = get_map_assets(settings)

    # if settings.debug and debug.SELECTIVE_UMAP:
    #     settings.selected_map.umaps = debug.SELECTIVE_UMAP
    #     umap_json_paths = []
    #     for umap in debug.SELECTIVE_UMAP:
    #         umap_json_paths.append(settings.selected_map.umaps_path.joinpath(f"{umap}.json"))

    # # Process each umaps
    # umap_json_path: Path
    # for umap_json_path in umap_json_paths:


    #     # clean the scene if the debug mode is not enabled
    #     if not settings.debug:
    #         clean_scene()

    #     umap_data = read_json(umap_json_path)
    #     umap_name = umap_json_path.stem

    #     import_umap(settings=settings, umap_data=umap_data, umap_name=umap_name)
    #     remove_master_objects()
    #     clear_duplicate_node_groups()

    # # Final
    # if settings.debug:
    #     PROPS = {

    #         "ScalarParameterValues": list(dict.fromkeys(ScalarParameterValues)),
    #         "StaticParameterValues": list(dict.fromkeys(StaticParameterValues)),
    #         "TextureParameterValues": list(dict.fromkeys(TextureParameterValues)),
    #         "BasePropertyOverrides": BasePropertyOverrides,
    #         "VectorParameterValues": list(dict.fromkeys(VectorParameterValues)),
    #         "MaterialTypes": list(dict.fromkeys(MaterialTypes)),
    #         "OtherTypes": list(dict.fromkeys(OtherTypes))
    #     }

    #     save_json(settings.selected_map.folder_path.joinpath("props.json"), PROPS)
    #     save_json(settings.selected_map.folder_path.joinpath("material_types.json"), list(dict.fromkeys(MaterialTypes)))
    #     save_json(settings.selected_map.folder_path.joinpath("object_types.json"), list(dict.fromkeys(flatten_list(ObjectTypes))))

    # else:
    #     if settings.combine_umaps:
    #         post_import(settings=settings)
    #     if settings.open_folder:
    #         open_folder(settings.selected_map.scenes_path.__str__())

        

    logger.info("Finished!")
