
import enum
import itertools
from re import T
import bpy
import subprocess

from pathlib import Path
from enum import Enum
from contextlib import redirect_stdout
from io import StringIO
from src.utils import blender
from bpy.types import Mesh, ShaderNodeVertexColor


from ..utils import common, blender, importer_xay, valorant
from ..utils.importer_xay import VCOL_ATTR_NAME, unpack_4uint8, set_vcols_on_layer
import sys
import os

from itertools import islice

from . import liana

from ..utils import blender, common
from ..utils.importer_xay import *

logger = common.setup_logger(__name__)
stdout = StringIO()

try:
    sys.dont_write_bytecode = True
    from ..tools import injector
except:
    pass


MESH_TYPES = ["StaticMesh", "StaticMeshComponent", "InstancedStaticMeshComponent", "HierarchicalInstancedStaticMeshComponent"]
LIGHT_TYPES = ["PointLightComponent", "RectLightcomponent", "SpotLightComponent"]

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

stdout = StringIO()

logger = common.setup_logger(__name__)


class BlendMode(Enum):
    OPAQUE = 0
    CLIP = 1
    BLEND = 2
    HASHED = 3


class ValorantShaders(Enum):
    base = "VALORANT_Base"
    decal = "VALORANT_Decal"
    emissive = "VALORANT_Emissive"
    emissive_scroll = "VALORANT_Emissive_Scroll"
    hologram = "VALORANT_Hologram"
    glass = "VALORANT_Glass"
    blend = "VALORANT_Blend"
    mra_splitter = "VALORANT_MRA_Splitter"
    normal_fix = "VALORANT_Normal_Fix"
    screen = "VALORANT_Screen"
    lightshift = "VALORANT_Lightshift"
    wv_mapping = "VALORANT_W/V_Mapping"
    spriteglow = "VALORANT_SpriteGlow"
    waterfall = "VALORANT_Waterfall"
    waterfall_mapping = "VALORANT_Waterfall_Mapping"
    ventsmoke = "VALORANT_Ventsmoke"
    ventsmoke_mapping = "VALORANT_Ventsmoke_Mapping"
    skybox = "VALORANT_Skybox"


class MaterialTypes:
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
        "MaskTintEnv_MAT"
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
        "0_Sprite_GlowLight",
    ]

    types_waterfallvista = [
        "0_Waterfall_Base1"
    ]

    types_ventsmoke = [
        "0_VentSmoke_Duo",
        "0_VentSmoke"
    ]


# ANCHOR : Helper Functions


def duplicate_object(bobject: bpy.types.Object, vdata: bool = False):
    obj_copy = bobject.copy()

    if vdata and obj_copy.data:
        obj_copy.data = obj_copy.data.copy()

    return obj_copy


def get_filename(object_path: str):
    return object_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]


def get_mesh_name(mesh_data: dict):
    return get_filename(mesh_data["Properties"]["StaticMesh"]["ObjectPath"])


# ANCHOR : Material Functions

def get_valorant_shader(group_name: str):
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]
    else:
        logger.info(f"Shader group {group_name} not found")


class Prefs:
    def __init__(self, addon_prefs):
        self.aes = "0x4BE71AF2459CF83899EC9DC2CB60E22AC4B3047E0211034BBABE9D174C069DD6"
        self.texture_format = ".png"

        self.export_path = Path(addon_prefs.exportPath)
        self.script_root = Path(addon_prefs.scriptPath)
        self.tools = self.script_root.joinpath("tools")
        self.resources = self.script_root.joinpath("assets")
        self.umodel = self.tools.joinpath("umodel.exe").__str__()
        self.siana = self.tools.joinpath("siana.exe").__str__()
        self.dll_path = self.tools.joinpath("BlenderPerfPatch.dll")
        self.paks_path = addon_prefs.paksPath

        self.debug = addon_prefs.debug
        self.use_perfpatch = addon_prefs.usePerfPatch
        self.selected_map = addon_prefs.selectedMap
        self.import_decals = addon_prefs.importDecals
        self.import_lights = addon_prefs.importLights
        self.combine_umaps = addon_prefs.combineUmaps
        self.combine_method = addon_prefs.combineMethod
        self.texture_control = addon_prefs.textureControl
        self.selected_map = addon_prefs.selectedMap


class Paths:
    def __init__(self, prefs):
        self.export_path = prefs.export_path
        self.assets_path = self.export_path.joinpath("export")
        self.maps_path = self.export_path.joinpath("maps")
        self.map_folder = self.maps_path.joinpath(prefs.selected_map)
        self.umaps = self.map_folder.joinpath("umaps")
        self.materials = self.map_folder.joinpath("materials")
        self.materials_ovr = self.map_folder.joinpath("materials_ovr")
        self.materials_parent = self.map_folder.joinpath("parent_materials")
        self.objects = self.map_folder.joinpath("objects")

        self.create_folders()

    def create_folders(self):
        for attr, value in self.__dict__.items():
            if "path" in attr:
                f = Path(value)
                if not f.exists():
                    print(f"Creating folder {f}")
                    f.mkdir(parents=True)


class World:
    def __init__(self, prefs: Prefs, paths: Paths):
        self.__prefs = prefs
        self.paths = paths

        self.name = prefs.selected_map
        self.umaps = []

        self.__umap_list = common.read_json(prefs.resources.joinpath("umaps.json"))[self.name]

        # Extract .json files
        for umap_path in self.__umap_list:
            self.extract_datas(umap_path)

        # Load JSONs Files
        self.objects = common.read_files(self.paths.objects)
        self.materials = common.read_files(self.paths.materials, use_lower=True)
        self.materials_ovr = common.read_files(self.paths.materials_ovr, use_lower=True)
        self.materials_parent = common.read_files(self.paths.materials_parent, use_lower=True)
        self.umaps = common.read_files(self.paths.umaps)

        # self.res1 = dict(list(self.materials_ovr.items())[len(self.materials_ovr)//2:])
        # self.res2 = dict(list(self.materials_ovr.items())[:len(self.materials_ovr)//2])

    def chunks(data, SIZE=10000):
        it = iter(data)
        for i in range(0, len(data), SIZE):
            yield {k: data[k] for k in islice(it, SIZE)}

    def get_umap_name(self, umap_name: str):
        return umap_name.split("/")[-1]

    def extract_datas(self, umap_path: str):
        umap_name = self.get_umap_name(umap_path)
        umap_json_file = self.paths.umaps.joinpath(umap_name + ".json")
        if not umap_json_file.exists():
            self.extract_data(umap_path)

    def extract_data(self, game_object_path: str):
        args = [
            self.__prefs.siana.__str__(),
            self.__prefs.paks_path.__str__(),
            self.paths.map_folder.__str__(),
            game_object_path,
        ]

        subprocess.call(args)


class UMap:
    def __init__(self, umap_name: str, umap_data: dict):
        self.name = umap_name
        self.data = umap_data


class UObject:
    def __init__(self, world: World, paths: Paths, data: str, collection: bpy.types.Collection):

        self.data = data
        self.world = world

        self.name = self.get_object_name()
        self.instanced = self.is_instanced()
        self.meshfile = self.get_mesh_path(paths.assets_path)
        self.static_mesh = self.world.objects[self.name]

        self.sm_materials = []
        self.om_materials = []

        self.collection = collection

        self.meshfile: str
        self.bmesh: bpy.types.Object
        self.bgroup: bpy.types.Object
        self.instances: list

        self.setup()
        self.get_materials()
        self.set_materials()

    def setup(self):
        self.bmesh = self.get_object()

        if "LODData" in self.data:
            lod_data = self.data["LODData"][0]

            if "OverrideVertexColors" in lod_data:
                # print(lod_data)
                # print(f"{self.name} has override vertex colors")
                if "Data" in lod_data["OverrideVertexColors"]:
                    vertex_colors_hex = lod_data["OverrideVertexColors"]["Data"]
                    mo: Mesh = self.bmesh.data
                    vertex_colors = [
                        [
                            x / 255
                            for x in unpack_4uint8(bytes.fromhex(rgba_hex))
                        ]
                        for rgba_hex in vertex_colors_hex
                    ]
                    set_vcols_on_layer(mo, vertex_colors)

        if self.instanced:
            self.bgroup = bpy.data.objects.new(self.name + "-GRP", None)
            self.collection.objects.link(self.bgroup)

            self.reset_properties(self.bgroup)
            self.set_properties(bobject=self.bgroup, properties=self.data["Properties"])

            instances = self.data["PerInstanceSMData"]

            for index, instance_data in enumerate(instances):

                # logger.info(f"[{index}] | Instancing : {common.shorten_path(self.meshfile, 4)}")
                # self.reset_properties(instance)

                if index == 0:
                    instance = self.bmesh
                else:
                    instance = self.bmesh.copy()
                    self.collection.objects.link(instance)

                instance.parent = self.bgroup
                self.set_properties(bobject=instance, properties=instance_data)
        else:
            self.set_properties(bobject=self.bmesh, properties=self.data["Properties"])

    def get_materials(self):

        # print(self.static_mesh["Properties"]["StaticMaterials"])

        if "StaticMaterials" in self.static_mesh["Properties"]:
            sm_materials = self.static_mesh["Properties"]["StaticMaterials"]
            for m in sm_materials:

                if m is None:
                    self.sm_materials.append(None)
                    continue
                else:
                    if m['MaterialInterface'] is None:
                        self.sm_materials.append(None)
                        continue
                    mat_name = self.get_name_a(m['MaterialInterface']['ObjectPath'])
                    self.sm_materials.append(self.world.materials[mat_name.lower()])

        if "OverrideMaterials" in self.data["Properties"]:
            om_materials = self.data["Properties"]["OverrideMaterials"]
            for m in om_materials:
                if m == None:
                    self.om_materials.append(None)
                else:
                    mat_name = self.get_name_a(m['ObjectPath'])
                    try:
                        self.om_materials.append(self.world.materials_ovr[mat_name.lower()])
                    except KeyError:
                        mat_name_fix = mat_name.rstrip("1")
                        self.om_materials.append(self.world.materials_ovr[mat_name_fix.lower()])

    def set_materials(self):

        zipped = itertools.zip_longest(self.sm_materials, self.om_materials)

        for i, (sm, om) in enumerate(zipped):

            if sm is not None:
                self.set_material(material=sm, slot=i)

            if om is not None:
                self.set_material(material=om, slot=i, override=True)

    # ANCHOR : Set Material

    def set_material(self, material: dict, slot: int, override: bool = False):

        name = material["Name"]

        properties = material["Properties"]


        # Check if its a collision Mesh
        if "EnvCollision_MAT" in material["Name"]:
            bpy.data.objects.remove(self.bmesh, do_unlink=True)
            return


        has_vc = False
        if getattr(self.bmesh.data, VCOL_ATTR_NAME):
            name = name + "_V"
            has_vc = True

        bMaterial = bpy.data.materials.get(name)
        if bMaterial is not None and bMaterial.use_nodes:
            self.assign_material(material=bMaterial, slot=slot)
            # logger.info(f"Material found, using existing : {name}")
            return
        else:
            bMaterial = bpy.data.materials.new(name=name)
            # logger.info(f"Material not found, creating : {name}")

        # Return if the material exists

        bMaterial.name = name
        bMaterial.use_nodes = True

        # Setup Nodes

        nodes = bMaterial.node_tree.nodes
        create_node = bMaterial.node_tree.nodes.new
        link = bMaterial.node_tree.links.new

        blender.clear_nodes(nodes)

        mat_type, mat_phys = self.get_material_type(properties, name)

        N_NOTE = blender.create_node_note(nodes, mat_type)
        N_OUTPUT = nodes['Material Output']
        N_SHADER = nodes.new("ShaderNodeGroup")
        N_MAPPING = None

        blender.set_node_position(N_NOTE, -350, 230)

        # ANCHOR Material
        N_VERTEX: ShaderNodeVertexColor = nodes.get("Vertex Color")

        if N_VERTEX is None:
            N_VERTEX = create_node(type="ShaderNodeVertexColor")
            N_VERTEX.layer_name = "Col"
            N_VERTEX.name = "Vertex Color"

        note_textures_normal = blender.create_node_note(nodes, "Textures : Normal")
        note_textures_override = blender.create_node_note(nodes, "Textures : Override")
        note_textures_cached = blender.create_node_note(nodes, "Textures : Cached")

        note_textures_normal.width = 240
        note_textures_override.width = 240
        note_textures_cached.width = 240

        note_textures_normal.label_size = 15
        note_textures_override.label_size = 15
        note_textures_cached.label_size = 15

        blender.set_node_position(note_textures_normal, -700, 60)
        blender.set_node_position(note_textures_override, -1000, 60)
        blender.set_node_position(note_textures_cached, -1300, 60)

        blender.set_node_position(N_NOTE, -350, 230)
        blender.set_node_position(N_OUTPUT, 300, 0)
        blender.set_node_position(N_VERTEX, -600, 180)

        blend_mode = BlendMode.OPAQUE

        # Default Material
        N_SHADER.node_tree, user_mat_type = self.select_shader(mat_type, name)

        nodes_textures = self.import_textures(material_data=material, b_material=bMaterial, override=override)
        # N_SHADER.inputs["DF"].default_value = (0.6, 0.6, 0.6, 1)

        link(N_SHADER.outputs[0], N_OUTPUT.inputs["Surface"])

        # Set up material using the datas


        if getattr(self.bmesh.data, VCOL_ATTR_NAME):
            if "Vertex Color" in N_SHADER.inputs:
                link(N_VERTEX.outputs["Color"], N_SHADER.inputs["Vertex Color"])

            if "Vertex" in N_SHADER.inputs:
                link(N_VERTEX.outputs["Color"], N_SHADER.inputs["Vertex"])

            if mat_type == "NO PARENT":
                if "DF" in N_SHADER.inputs:
                    link(N_VERTEX.outputs["Color"], N_SHADER.inputs["DF"])

            if "Blend" in mat_type:
                if "Vertex Color" in N_SHADER.inputs:
                    link(N_VERTEX.outputs["Color"], N_SHADER.inputs["Vertex Color"])
                if "Vertex Alpha" in N_SHADER.inputs:
                    link(N_VERTEX.outputs["Alpha"], N_SHADER.inputs["Vertex Alpha"])

        # ANCHOR : Material : Base Property Overrides
        if "BasePropertyOverrides" in properties:
                for prop_name, prop_value in properties["BasePropertyOverrides"].items():

                    # ANCHOR Shading Model
                    if "ShadingModel" == prop_name:
                        if "MSM_AresEnvironment" in prop_value:
                            pass
                        if "MSM_Unlit" in prop_value:
                            pass

                    # ANCHOR Blend Mode
                    if "BlendMode" == prop_name:
                        if "Use Alpha" in N_SHADER.inputs:
                            N_SHADER.inputs["Use Alpha"].default_value = 1
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
                        bMaterial.alpha_threshold = prop_value
                        pass

                    # -----------------------------------------------
                    # LOGGING
                    # if prop_name not in BasePropertyOverrides:
                    #     BasePropertyOverrides[prop_name] = []
                    # BasePropertyOverrides[prop_name].append(mat_props["BasePropertyOverrides"][prop_name])
                    # BasePropertyOverrides[prop_name] = list(dict.fromkeys(BasePropertyOverrides[prop_name]))


        bMaterial.blend_method = blend_mode.name
        bMaterial.shadow_method = 'OPAQUE' if blend_mode.name == 'OPAQUE' else 'HASHED'

        # ANCHOR : Material : Static Parameters
        if "StaticParameters" in properties:
            if "StaticSwitchParameters" in properties["StaticParameters"]:
                for param in properties["StaticParameters"]["StaticSwitchParameters"]:
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

                    if "use alpha power" in param_name and "Use Alpha Power" in N_SHADER.inputs:
                        if param["Value"]:
                            N_SHADER.inputs["Use Alpha Power"].default_value = 1

                    if "invert alpha (texture)" in param_name and "Invert Alpha" in N_SHADER.inputs:
                        if param["Value"]:
                            N_SHADER.inputs["Invert Alpha"].default_value = 1

                    if "use vertex color" in param_name:
                        if getattr(self.bmesh.data, VCOL_ATTR_NAME):
                            # mat_switches.append(param_name)
                            if "Vertex Color" in N_SHADER.inputs:
                                link(N_VERTEX.outputs["Color"], N_SHADER.inputs["Vertex Color"])
                            if "Use Vertex Color" in N_SHADER.inputs:
                                N_SHADER.inputs["Use Vertex Color"].default_value = 1

                    if "use vertex alpha" in param_name:
                        if getattr(self.bmesh.data, VCOL_ATTR_NAME):
                            # mat_switches.append(param_name)
                            if "Vertex Alpha" in N_SHADER.inputs:
                                link(N_VERTEX.outputs["Alpha"], N_SHADER.inputs["Vertex Alpha"])
                            if "Use Vertex Alpha" in N_SHADER.inputs:
                                N_SHADER.inputs["Use Vertex Alpha"].default_value = 1
                                # TODO : What is this?
                                # N_SHADER.inputs["Use Alpha Power"].default_value = 0

                    if "use alpha as emissive" in param_name:
                        # mat_switches.append("use alpha as emissive")
                        if "Use Alpha as Emissive" in N_SHADER.inputs:
                            N_SHADER.inputs["Use Alpha as Emissive"].default_value = 1
                        else:
                            pass
                    # LOGGING
                    # StaticParameterValues.append(param['ParameterInfo']['Name'].lower())
            if "StaticComponentMaskParameters" in properties["StaticParameters"]:
                for param in properties["StaticParameters"]["StaticComponentMaskParameters"]:
                    param_name = param["ParameterInfo"]["Name"].lower()
                    if param_name == "mask":
                        # MASK = "R"
                        colors = {"R", "G", "B", "A"}
                        for color in colors:
                            if color in param:
                                if param[color]:
                                    if f"Use {color}" in N_SHADER.inputs:
                                        N_SHADER.inputs[f"Use {color}"].default_value = 1
        # ANCHOR : Material : Scalar Parameters
        if "ScalarParameterValues" in properties:
            for param in properties["ScalarParameterValues"]:
                param_name = param['ParameterInfo']['Name'].lower()

                if "metallic" in param_name and "Metallic Strength" in N_SHADER.inputs:
                    N_SHADER.inputs["Metallic Strength"].default_value = param["ParameterValue"]

                if "alpha" in param_name and "Alpha Strength" in N_SHADER.inputs:
                    N_SHADER.inputs["Alpha Strength"].default_value = param["ParameterValue"]

                if "emissive_base_power" in param_name and "Emissive_Base_Power" in N_SHADER.inputs:
                    N_SHADER.inputs["Emissive_Base_Power"].default_value = param["ParameterValue"]

                if "mask blend power" in param_name and "Vertex Blend" in N_SHADER.inputs:
                    N_SHADER.inputs["Vertex Blend"].default_value = param["ParameterValue"]


                # VFX Shit
                if N_MAPPING is not None:
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
                # ScalarParameterValues.append(param_name)

        # ANCHOR : Material : Vector Parameters
        if "VectorParameterValues" in properties:
            color_pos_x = -700
            color_pos_y = 470
            for param in properties["VectorParameterValues"]:
                param_name = param['ParameterInfo']['Name'].lower()
                param_value = param["ParameterValue"]

                yo = blender.create_node_color(nodes, param_name, valorant.get_rgb(param_value), color_pos_x, color_pos_y)
                color_pos_x += 200

                if "color" in param_name:
                    if "Color" in N_SHADER.inputs:
                        N_SHADER.inputs["Color"].default_value = valorant.get_rgb(param_value)

                if "diffusecolor" in param_name:
                    if "Diffuse Color" in N_SHADER.inputs:
                        N_SHADER.inputs["Diffuse Color"].default_value = valorant.get_rgb(param_value)

                if "ao color" in param_name:
                    if "AO Color" in N_SHADER.inputs:
                        N_SHADER.inputs["AO Color"].default_value = valorant.get_rgb(param_value)

                if "lightmass-only vertex color" in param_name:
                    if "VC" in N_SHADER.inputs:
                        N_SHADER.inputs["VC"].default_value = valorant.get_rgb(param_value)

                if "emissive mult" in param_name:
                    if "Emissive Mult" in N_SHADER.inputs:
                        N_SHADER.inputs["Emissive Mult"].default_value = valorant.get_rgb(param_value)

                if "min light brightness color" in param_name:
                    if "ML Brightness" in N_SHADER.inputs:
                        N_SHADER.inputs["ML Brightness"].default_value = valorant.get_rgb(param_value)
                    if "MLB" in N_SHADER.inputs:
                        N_SHADER.inputs["MLB"].default_value = valorant.get_rgb(param_value)

                if "color_1" in param_name:
                    if "Color 1" in N_SHADER.inputs:
                        N_SHADER.inputs["Color 1"].default_value = valorant.get_rgb(param_value)

                if "color_2" in param_name:
                    if "Color 2" in N_SHADER.inputs:
                        N_SHADER.inputs["Color 2"].default_value = valorant.get_rgb(param_value)
                if "line color" in param_name:
                    if "line color" in N_SHADER.inputs:
                        N_SHADER.inputs["line color"].default_value = valorant.get_rgb(param_value)
                if "layer a tint" in param_name or "color mult" in param_name or "texture tint a" in param_name:
                    if "Tint" in N_SHADER.inputs:
                        N_SHADER.inputs["Tint"].default_value = valorant.get_rgb(param_value)
                if "layer b tint" in param_name or "texture tint b" in param_name:
                    if "Tint B" in N_SHADER.inputs:
                        N_SHADER.inputs["Tint B"].default_value = valorant.get_rgb(param_value)

                # Logging
                # VectorParameterValues.append(param['ParameterInfo']['Name'].lower())



        # ANCHOR : Material : Textures
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

            if key == "diffuse b" or key == "texture b" or key == "albedo b":
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
        

            if key == "LCDScreenRGB_TEX":
                if "RGB Texture" in N_SHADER.inputs:
                    # Link to
                    link(node_tex.outputs["Color"], N_SHADER.inputs["RGB Texture"])

                    node_rgb_mapping = nodes.new(type="ShaderNodeMapping")
                    node_rgb_uv = nodes.new(type="ShaderNodeUVMap")

                    blender.set_node_position(node_rgb_mapping, node_tex.location.x - 200, node_tex.location.y)
                    blender.set_node_position(node_rgb_uv, node_tex.location.x - 400, node_tex.location.y)

                    link(node_rgb_uv.outputs["UV"], node_rgb_mapping.inputs["Vector"])
                    link(node_rgb_mapping.outputs["Vector"], node_tex.inputs["Vector"])

                    sv = valorant.get_scalar_value(properties, "RGB Scale")
                    if sv is not None:
                        node_rgb_mapping.inputs["Scale"].default_value = [sv, sv, sv]
        try:
            if mat_phys == "M_EtherGlass":
                N_SHADER.inputs["Emission Strength"].default_value = 10
            if "screen" in bMaterial.name.lower():
                N_SHADER.inputs["Emission Strength"].default_value = 10
            
        except Exception as e:
            logger.info(e)
        
        self.assign_material(material=bMaterial, slot=slot)

    def select_shader(self, mat_type: str, mat_name):

        def_user_mat_type = mat_type

        if "lcd" in mat_name.lower() or "terminal" in mat_name.lower() or "screen" in mat_name.lower():
            return get_valorant_shader(group_name="VALORANT_Screen"), def_user_mat_type
        if mat_type in MaterialTypes.types_blend:
            return get_valorant_shader(group_name="VALORANT_Blend"), "Blend"
        elif mat_type in MaterialTypes.types_hologram:
            return get_valorant_shader(group_name="VALORANT_Hologram"), def_user_mat_type
        elif mat_type in MaterialTypes.types_emissive_scroll:
            return get_valorant_shader(group_name="VALORANT_Emissive_Scroll"), def_user_mat_type
        elif mat_type in MaterialTypes.types_glass:
            return get_valorant_shader(group_name="VALORANT_Base"), def_user_mat_type
        elif mat_type in MaterialTypes.types_emissive:
            return get_valorant_shader(group_name="VALORANT_Base"), def_user_mat_type
        elif mat_type in MaterialTypes.types_base:
            return get_valorant_shader(group_name="VALORANT_Base"), def_user_mat_type
        else:
            return get_valorant_shader(group_name="VALORANT_Base"), def_user_mat_type

    def import_textures(self, material_data: dict, b_material: bpy.types.Material, override: bool = False) -> dict:

        nodes = b_material.node_tree.nodes

        texture_nodes = {}

        properties = material_data["Properties"]

        if "TextureParameterValues" in properties:
            pos = [-700, 0]

            if override:
                pos = [-1000, 0]

            index = 0

            for param in properties["TextureParameterValues"]:
                param_name = param['ParameterInfo']['Name'].lower()

                # if "diffuse b low" in param_name:
                #     continue

                tex_game_path_a = param["ParameterValue"]["ObjectPath"]
                tex_game_path = valorant.get_texture_path(path=tex_game_path_a, extension=".png")
                tex_local_path = self.world.paths.assets_path.joinpath(tex_game_path).__str__()
                tex_name = Path(tex_local_path).stem

                # logger.info(f"Importing texture {tex_local_path}")

                if Path(tex_local_path).exists() and tex_name not in BLACKLIST_textures:
                    pos[1] = index * -300
                    index += 1
                    tex_image_node: bpy.types.Node
                    tex_image_node = nodes.new('ShaderNodeTexImage')
                    tex_image_node.image = valorant.import_texture(texture_path=tex_local_path) 

                    tex_image_node.image.alpha_mode = "CHANNEL_PACKED"
                    tex_image_node.label = param["ParameterInfo"]["Name"]
                    tex_image_node.location[0] = pos[0]
                    tex_image_node.location[1] = pos[1]

                    if "diffuse" == param_name or "diffuse a" == param_name or "albedo" == param_name or "texture a" == param_name or "albedo a" == param_name:
                        texture_nodes["diffuse"] = tex_image_node
                    if "mra" == param_name or "mra a" == param_name:
                        tex_image_node.image.colorspace_settings.name = "Non-Color"
                        texture_nodes["mra"] = tex_image_node
                    if "normal" == param_name or "texture a normal" == param_name or "normal a" == param_name:
                        tex_image_node.image.colorspace_settings.name = "Non-Color"
                        texture_nodes["normal"] = tex_image_node
                    if "normal b" == param_name or "texture b normal" == param_name:
                        tex_image_node.image.colorspace_settings.name = "Non-Color"
                        texture_nodes["normal b"] = tex_image_node
                    if "mask" in param_name or "rgba" in param_name:
                        tex_image_node.image.colorspace_settings.name = "Raw"
                        texture_nodes["mask"] = tex_image_node

                    # Other Textures
                    else:
                        texture_nodes[param_name] = tex_image_node

        if "CachedReferencedTextures" in properties:
                pos = [-1300, 0]
                if override:
                    pos = [-1300, 0]
                i = 0
                textures = properties["CachedReferencedTextures"]
                logger.info(f"CachedReferencedTextures")
                for index, param, in enumerate(textures):
                    if param is not None:

                        texture_name_raw = param["ObjectName"].replace("Texture2D ", "")
                        if texture_name_raw not in BLACKLIST_textures:
                            texture_path_raw = param["ObjectPath"]

                            tex_game_path = valorant.get_texture_path(path=texture_path_raw, extension=".png")
                            tex_local_path = self.world.paths.assets_path.joinpath(tex_game_path).__str__()

                            if Path(tex_local_path).exists():
                                pos[1] = i * -300
                                i += 1
                                tex_image_node = nodes.new('ShaderNodeTexImage')
                                tex_image_node.image = valorant.import_texture(texture_path=tex_local_path) 
                                tex_image_node.image.alpha_mode = "CHANNEL_PACKED"
                                tex_image_node.label = texture_name_raw
                                tex_image_node.location = [pos[0], pos[1]]

                                logger.info(f"Importing texture {tex_local_path}")

                                if "_DF" in texture_name_raw:
                                    texture_nodes["diffuse"] = tex_image_node
                                else:
                                    texture_nodes[texture_name_raw] = tex_image_node    
                                                     # TextureParameterValues.append(texture_name_raw.lower())
        if "CachedExpressionData"in properties:
            pos = [-1300, 0]
            i = 0
            if "ReferencedTextures" in properties["CachedExpressionData"]:
                textures = properties["CachedExpressionData"]["ReferencedTextures"] 
                for index, param, in enumerate(textures):
                    if param is not None:
                        texture_name_raw = param["ObjectName"].replace("Texture2D ", "")
                        if texture_name_raw not in BLACKLIST_textures:
                            texture_path_raw = param["ObjectPath"]


                            
                            tex_game_path = valorant.get_texture_path(path=texture_path_raw, extension=".png")
                            tex_local_path = self.world.paths.assets_path.joinpath(tex_game_path).__str__()

                            if Path(tex_local_path).exists():
                                pos[1] = i * -300
                                i += 1
                                tex_image_node = nodes.new('ShaderNodeTexImage')
                                tex_image_node.image = valorant.import_texture(texture_path=tex_local_path) 
                                tex_image_node.image.alpha_mode = "CHANNEL_PACKED"
                                tex_image_node.label = texture_name_raw
                                tex_image_node.location = [pos[0], pos[1]]


                                if "asdasdasd" in texture_name_raw:
                                    texture_nodes["diffuse"] = tex_image_node
                                else:
                                    texture_nodes[texture_name_raw] = tex_image_node

                                # if "_mk" in texture_name_raw:
                                #     if "MRA" in shader.inputs:
                                #         mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["MRA"])
                                #         shader.inputs["Metallic"].default_value = -1
                                #         shader.inputs["Roughness"].default_value = -1
                                #         shader.inputs["AO Strength"].default_value = 0.15

                                # if "_DF" in texture_name_raw:
                                #     if "DF" in shader.inputs:
                                #         mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["DF"])
                                #         mat.node_tree.links.new(tex_image_node.outputs["Alpha"], shader.inputs["Alpha"])
                                #         mat.node_tree.links.new(tex_image_node.outputs["Alpha"], shader.inputs["DF Alpha"])

                                # if "_NM" in texture_name_raw:
                                #     if "NM" in shader.inputs:
                                #         mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["NM"])

                                # if "_MRA" in texture_name_raw:
                                #     if "MRA" in shader.inputs:
                                #         mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["MRA"])

                                # if "T_CGSkies_0091_ascent_DF" in texture_name_raw:
                                #     if "Light" in shader.inputs:
                                #         mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["Light"])

                                #         world_nodes = bpy.context.scene.world.node_tree.nodes
                                #         world_nodes.clear()

                                #         node_background = world_nodes.new(type='ShaderNodeBackground')
                                #         node_output = world_nodes.new(type='ShaderNodeOutputWorld')   
                                #         node_output.location = 200,0

                                #         node_environment = world_nodes.new('ShaderNodeTexEnvironment')
                                #         node_environment.image = bpy.data.images.load(tex_local_path)
                                #         node_environment.label = texture_name_raw
                                #         node_environment.location = -300,0
                            
                                #         links = bpy.context.scene.world.node_tree.links
                                #         links.new(node_environment.outputs["Color"], node_background.inputs["Color"])
                                #         links.new(node_background.outputs["Background"], node_output.inputs["Surface"])

                                # if "Skybox" in texture_name_raw:
                                #     if "Background" in shader.inputs:
                                #         mat.node_tree.links.new(tex_image_node.outputs["Color"], shader.inputs["Background"])

        return texture_nodes

    def get_material_type(self, properties: dict, name: str):

        mat_type, mat_phys = False, False

        if "Parent" in properties:
            mat_type = get_filename(properties["Parent"]["ObjectPath"])
        else:
            mat_type = "NO PARENT"

        if "PhysMaterial" in properties:
            mat_phys = get_filename(properties["PhysMaterial"]["ObjectPath"])
            if "M_Glass" == mat_phys and "Emissive" not in name:
                mat_type = "Glass"
        else:
            mat_phys = False

        return mat_type, mat_phys

    def assign_material(self, material: bpy.types.Material, slot: int):
        # Assign the Material
        try:
            self.bmesh.material_slots[slot].material = material
        except:
            pass

    def get_name(self, mat_path: str):
        return mat_path.split(" ")[-1]

    def get_name_a(self, mat_path: str):
        return mat_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]

    def get_object_name(self):
        return self.data["Properties"]["StaticMesh"]["ObjectPath"].rsplit("/", 1)[-1].rsplit(".", 1)[0]

    def get_mesh_path(self, path: Path):
        am = valorant.fix_path(self.data["Properties"]["StaticMesh"]["ObjectPath"])
        bm = am.rsplit(".", 1)[0]
        cm = path.joinpath(bm).__str__() + ".xay"
        return cm

    def is_instanced(self):
        if "PerInstanceSMData" in self.data:
            return True
        else:
            return False

    def set_properties(self, bobject: bpy.types.Object, properties: dict):
        if "OffsetLocation" in properties:
            bobject.location = [
                properties["OffsetLocation"]["X"] * 0.01,
                properties["OffsetLocation"]["Y"] * -0.01,
                properties["OffsetLocation"]["Z"] * 0.01
            ]

        if "RelativeLocation" in properties:
            bobject.location = [
                properties["RelativeLocation"]["X"] * 0.01,
                properties["RelativeLocation"]["Y"] * -0.01,
                properties["RelativeLocation"]["Z"] * 0.01
            ]

        if "RelativeRotation" in properties:
            bobject.rotation_mode = 'XYZ'
            bobject.rotation_euler = [
                blender.fx(properties["RelativeRotation"]["Roll"]),
                blender.fx(-properties["RelativeRotation"]["Pitch"]),
                blender.fx(-properties["RelativeRotation"]["Yaw"])
            ]

        if "RelativeScale3D" in properties:
            bobject.scale = [
                properties["RelativeScale3D"]["X"],
                properties["RelativeScale3D"]["Y"],
                properties["RelativeScale3D"]["Z"]
            ]

    def get_object(self):

        # Check for duplicate
        ob = bpy.data.objects.get(self.name)
        if ob is not None and ob.type == "MESH":
            # logger.info("Duplicate object: " + ob.name)
            a = duplicate_object(ob)
            self.collection.objects.link(a)
            self.reset_properties(a)
            return a

        # Import object if it doesn't exist
        else:
            with redirect_stdout(stdout):
                # logger.info("Importing object: " + self.meshfile)
                a = importer_xay.xay(self.meshfile)
                self.collection.objects.link(a)
                return a

    def reset_properties(self, bobject: bpy.types.Object):
        bobject.location = [0, 0, 0]
        bobject.rotation_euler = [0, 0, 0]
        bobject.scale = [1, 1, 1]
        bobject.parent = None


class Debug:
    def __init__(self, prefs: Prefs, paths: Paths) -> None:

        self.__prefs = prefs
        self.__paths = paths

        self.active = prefs.debug
        self.objects = []
        self.umaps = []
        self.count = 0

        self.setup()

    def setup(self):
        self.__debug_json = common.read_json(self.__prefs.resources.joinpath("debug.json"))
        # print(self.__debug_json)
        self.objects = self.__debug_json["objects"]
        self.umaps = self.__debug_json["umaps"]
        self.count = self.__debug_json["count"]


class Material:
    def __init__(self, data: dict, index: int):

        self.setup()

    def setup(self):
        pass

    def get_bmaterial():
        pass


class Liana:
    def __init__(self, addon_prefs):
        self.prefs = Prefs(addon_prefs)
        self.paths = Paths(self.prefs)
        self.debug = Debug(self.prefs, self.paths)
        self.world = World(self.prefs, self.paths)

    def run(self):
        self.extract_assets()

        # Clear the scene
        blender.clean_scene()

        # Import the shaders
        self.import_shaders()

        self.import_umaps()

    def import_umaps(self):
        # print("asfdfads")

        self.world.collection = self.create_collection(self.world.name.capitalize())

        for umap_name, umap_data in self.world.umaps.items():
            if not self.debug.active:
                blender.clean_scene()

            if self.debug.active and any(umap_name in x for x in self.debug.umaps):
                self.import_umap(umap_name, umap_data)

            if len(self.debug.umaps) == 0 or not self.debug.active:
                self.import_umap(umap_name, umap_data)

    def extract_assets(self):
        if self.paths.assets_path.joinpath("exported.yo").exists():
            logger.info("Models are already extracted")
        else:
            logger.warning("Models are not found, starting exporting with args : \n{args}")
            args = [self.prefs.umodel.__str__(),
                    f"-path={self.prefs.paks_path.__str__()}",
                    f"-game=valorant",
                    f"-aes={self.prefs.aes}",
                    "-export",
                    "*.uasset",
                    "-xay",
                    "-noanim",
                    "-nooverwrite",
                    f"-{self.prefs.texture_format.replace('.', '')}",
                    f"-out={self.paths.assets_path.__str__()}"]

            # Export Models
            subprocess.call(args,
                            stderr=subprocess.DEVNULL)

            with open(self.paths.assets_path.joinpath('exported.yo').__str__(), 'w') as out_file:
                out_file.write("")

    def import_shaders(self):
        shaders_blend_file = self.prefs.resources.joinpath("VALORANT_Map.blend")
        nodegroups_folder = shaders_blend_file.joinpath("NodeTree")
        for shader in ValorantShaders:
            if shader not in bpy.data.node_groups.keys():
                logger.info(f"Importing shader: {shader.value}")
                bpy.ops.wm.append(filename=shader.value, directory=nodegroups_folder.__str__())
        blender.clear_duplicate_node_groups()

    def get_mesh_path(self, mesh: dict):
        # mesh_name = get_mesh_name(mesh)
        gm = valorant.fix_path(mesh["Properties"]["StaticMesh"]["ObjectPath"])
        to = get_filename(self.paths.assets_path.joinpath(gm).__str__()) + ".xay"
        return to

    def import_umap(self, umap_name, umap_data):
        umap = UMap(umap_name, umap_data)
        if self.debug.active:
            umap.collection = self.create_collection(name=umap_name, parent=self.world.collection)
        else:
            umap.collection = self.create_collection(name=umap_name)

        for object_data in umap.data:
            object_name = get_filename(object_data["Properties"]["StaticMesh"]["ObjectPath"])

            if not any(ext in object_name.lower() for ext in BLACKLIST_objects):

                # if "Shelf_1_Storage" in object_name:
                uobject = UObject(self.world, self.paths, object_data, umap.collection)
                logger.info(f"Set object: {uobject.name}")

    def create_collection(self, name: str, parent: bpy.types.Collection = None):

        collection = bpy.data.collections.new(name)

        if parent is None:
            scene = bpy.data.scenes["Scene"]
            scene.collection.children.link(collection)
        else:
            parent.children.link(collection)

        return collection


# ANCHOR : Map Import Main

def import_valorant_map(addon_prefs):

    os.system("cls")

    liana = Liana(addon_prefs)

    if (not addon_prefs.isInjected) and addon_prefs.usePerfPatch:
        injector.inject_dll(os.getpid(), liana.prefs.dll_path.__str__())
        addon_prefs.isInjected = True

    # Start the map import
    liana.run()

    # bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    for mat in bpy.data.materials:
        if not mat.users:
            bpy.data.materials.remove(mat)

    logger.info("Finished!")
