import os
import bpy
from asyncio.log import logger
from pathlib import Path
from enum import Enum

from .common import *

MESH_TYPES = ["staticmesh", "staticmeshcomponent", "instancedstaticmeshcomponent", "hierarchicalinstancedstaticmeshcomponent"]
GEN_TYPES = ["decalcomponent", "pointlightcomponent", "rectlightcomponent", "spotlightcomponent"]


def get_umap_list() -> list:
    script_path = os.path.dirname(os.path.abspath(__file__))
    umap_list_path = Path(script_path).joinpath("assets").joinpath("umaps.json")
    umap_list = read_json(umap_list_path)
    return umap_list


def filter_umap(umap_data: dict) -> list:
    """
    Filter umap data to only include objects that are meshes, lights, or decals
    :param umap_data:
    :return:
    """
    umap_filtered = list()
    object_types = []

    for obj in umap_data:
        object_types.append(obj["Type"])

        if obj["Type"].lower() in MESH_TYPES:
            if "Properties" not in obj:
                continue
            if "StaticMesh" not in obj["Properties"]:
                continue
            if obj["Properties"]["StaticMesh"] is None:
                continue
            if "bVisible" not in obj["Properties"]:
                umap_filtered.append(obj)

        if obj["Type"].lower() in GEN_TYPES:
            umap_filtered.append(obj)

    return umap_filtered, object_types


def get_objects(umap_data):
    umap_objects = []
    umap_materials = []

    for obj in umap_data:
        if "StaticMesh" in obj["Properties"]:
            obj_path = get_object_path(data=obj, mat=False)
            umap_objects.append(obj_path)

            if "OverrideMaterials" in obj["Properties"]:
                for mat in obj["Properties"]["OverrideMaterials"]:
                    if mat is None:
                        continue
                    umap_materials.append(get_object_path(data=mat, mat=True))

        elif "DecalMaterial" in obj["Properties"]:
            mat = obj["Properties"]["DecalMaterial"]
            if mat is None:
                continue
            umap_materials.append(get_object_path(data=mat, mat=True))
    return umap_objects, umap_materials


def get_object_path(data: dict, mat: bool):
    if mat:
        s = data["ObjectPath"]
    else:
        s = data["Properties"]["StaticMesh"]["ObjectPath"]

    s = s.split(".", 1)[0].replace('/', '\\')
    return s


def get_object_type(model_data: dict) -> str:

    lights = ["PointLightComponent", "RectLightComponent", "SpotLightComponent"]
    meshes = ["StaticMeshComponent", "InstancedStaticMeshComponent", "HierarchicalInstancedStaticMeshComponent"]
    decals = ["DecalComponent"]

    if model_data["Type"] in meshes:
        return "mesh"
    if model_data["Type"] in lights:
        return "light"
    if model_data["Type"] in decals:
        return "decal"


def get_object_materials(model_json: dict):
    # model_json = _common.read_json(model)
    model_materials = list()

    if "Properties" in model_json:
        if "StaticMaterials" in model_json["Properties"]:
            for mat in model_json["Properties"]["StaticMaterials"]:
                if mat is not None and "MaterialInterface" in mat:
                    if mat["MaterialInterface"] is not None:
                        material = mat["MaterialInterface"]
                        model_materials.append(get_object_path(data=material, mat=True))

    return model_materials


def fix_path(a: str):
    b = a.replace("ShooterGame\\Content", "Game")
    c = b.replace("Engine\\Content", "Engine")
    return c


def get_light_type(object):
    if "Point" in object["Type"]:
        return "POINT"
    if "Spot" in object["Type"]:
        return "SPOT"
    if "RectLightComponent" in object["Type"]:
        return "AREA"


def get_name(s: str) -> str:
    return Path(s).stem


def get_object_name(data: dict, mat: bool):
    if mat:
        s = data["ObjectPath"]
    else:
        if "StaticMesh" in data["Properties"]:
            s = data["Properties"]["StaticMesh"]["ObjectPath"]
        else:
            s = data["Outer"]
    k = get_name(s)
    return k


# ANCHOR Shaders

def get_valorant_shader(group_name: str):
    if group_name in bpy.data.node_groups:
        return bpy.data.node_groups[group_name]
    else:
        logger.info(f"Shader group {group_name} not found")


# ANCHOR Getters

def get_rgb_255(pv: dict) -> tuple:
    return (
        pv["R"] / 255,
        pv["G"] / 255,
        pv["B"] / 255,
        pv["A"] / 255
    )


def get_rgb(pv: dict) -> tuple:
    return (
        pv["R"],
        pv["G"],
        pv["B"],
        pv["A"])


def get_texture_path(s: dict, f: str):
    a = Path(os.path.splitext(s["ParameterValue"]["ObjectPath"])[0].strip("/")).__str__()
    b = fix_path(a=a) + f
    return b


def get_texture_path_yo(s: str, f: str):
    a = Path(os.path.splitext(s)[0].strip("/")).__str__()
    b = fix_path(a=a) + f
    return b


class BlendMode(Enum):
    OPAQUE = 0
    CLIP = 1
    BLEND = 2
    HASHED = 3


class Settings:
    def __init__(self, addon_prefs):

        self.aes = "0x4BE71AF2459CF83899EC9DC2CB60E22AC4B3047E0211034BBABE9D174C069DD6"
        self.texture_format = ".png"
        self.script_root = Path(addon_prefs.scriptPath)
        self.tools_path = self.script_root.joinpath("tools")
        self.importer_assets_path = self.script_root.joinpath("assets")
        # self.game_path = Path(settings.gamePath)
        self.paks_path = Path(addon_prefs.paksPath)
        self.import_decals = addon_prefs.importDecals
        self.import_lights = addon_prefs.importLights
        self.combine_umaps = addon_prefs.combineUmaps
        self.combine_method = addon_prefs.combineMethod
        self.textures = addon_prefs.textureControl
        self.export_path = Path(addon_prefs.exportPath)
        self.assets_path = self.export_path.joinpath("export")
        self.maps_path = self.export_path.joinpath("maps")
        self.umodel = self.script_root.joinpath("tools", "umodel.exe")
        self.cue4extractor = self.script_root.joinpath("tools", "cue4extractor.exe")
        self.log = self.export_path.joinpath("import.log")
        self.umap_list_path = self.importer_assets_path.joinpath("umaps.json")
        self.umap_list = read_json(self.umap_list_path)
        self.debug = addon_prefs.debug
        self.use_perfpatch = addon_prefs.usePerfPatch
        self.dll_path = self.tools_path.joinpath("BlenderPerfPatch.dll")

        self.selected_map = Map(addon_prefs.selectedMap, self.maps_path, self.umap_list)

        self.shaders = [
            "VALORANT_Base",
            "VALORANT_Decal",
            "VALORANT_Emissive",
            "VALORANT_Emissive_Scroll",
            "VALORANT_Hologram",
            "VALORANT_Glass",
            "VALORANT_Blend",
            "VALORANT_Decal",
            "VALORANT_MRA_Splitter",
            "VALORANT_Normal_Fix",
            "VALORANT_Screen",
            "VALORANT_Lightshift",
            "VALORANT_W/V_Mapping",
            "VALORANT_SpriteGlow",
            "VALORANT_Waterfall",
            "VALORANT_Waterfall_Mapping",
            "VALORANT_Ventsmoke",
            "VALORANT_Ventsmoke_Mapping",
            "VALORANT_Skybox"
        ]

        create_folders(self)


class Map:
    def __init__(self, selected_map_name: str, maps_path: Path, all_umaps: list):

        self.name = selected_map_name
        # print(maps_path, self.name)
        self.folder_path = maps_path.joinpath(self.name)

        self.umaps = all_umaps[self.name]
        # print(self)
        self.materials_path = self.folder_path.joinpath("materials")
        self.materials_ovr_path = self.folder_path.joinpath("materials_ovr")
        self.objects_path = self.folder_path.joinpath("objects")
        self.scenes_path = self.folder_path.joinpath("scenes")
        self.umaps_path = self.folder_path.joinpath("umaps")
        create_folders(self)


class MapObject(object):
    def __init__(self, settings: Settings, data: dict, umap_name: str):
        self.umap = umap_name
        self.map_folder = settings.selected_map.folder_path
        self.objects_folder = settings.selected_map.objects_path
        self.data = data
        self.name = self.get_object_name()
        self.uname = self.get_object_game_name()
        self.object_path = self.get_object_path()
        self.json = self.get_object_data_OG()
        self.model_path = self.get_local_model_path(p=settings.assets_path)

    def get_local_model_path(self, p: Path) -> str:
        a = p.joinpath(os.path.splitext(self.data["Properties"]["StaticMesh"]["ObjectPath"])[0].strip("/")).__str__()
        return fix_path(a) + ".xay"

    def get_object_name(self) -> str:
        s = self.data["Properties"]["StaticMesh"]["ObjectPath"]
        k = Path(s).stem
        return k

    def get_object_game_name(self) -> str:
        s = self.data["Outer"]
        return s

    def get_object_path(self, fix: bool = False) -> str:
        s = self.data["Properties"]["StaticMesh"]["ObjectPath"]
        s = s.split(".", 1)[0].replace('/', '\\')
        if fix:
            return fix_path(s)
        else:
            return s

    def is_instanced(self) -> bool:
        if "PerInstanceSMData" in self.data and "Instanced" in self.data["Type"]:
            return True
        else:
            return False

    def get_object_data_OG(self) -> dict:
        return read_json(self.objects_folder.joinpath(f"{self.name}.json"))