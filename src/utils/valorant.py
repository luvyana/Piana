

from distutils.log import debug
from gc import get_objects
from os import dup
import bpy
import subprocess

from pathlib import Path
from enum import Enum
from contextlib import redirect_stdout
from io import StringIO
from src.utils import blender

from . import common, blender, importer_xay




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


def fix_path(a: str):
    b = a.replace("ShooterGame/Content", "Game")
    c = b.replace("Engine/Content", "Engine")
    return c


class BlendMode(Enum):
    OPAQUE = 0
    CLIP = 1
    BLEND = 2
    HASHED = 3


SHADERS = [
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


class Liana:
    def __init__(self, addon_prefs):
        self.prefs = Prefs(addon_prefs)
        self.paths = Paths(self.prefs)
        self.debug = Debug(self.prefs, self.paths)
        self.world = World(self.prefs, self.paths)

        # self.run()

    def run(self):
        self.import_umaps()

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
        for shader in SHADERS:
            if shader not in bpy.data.node_groups.keys():
                bpy.ops.wm.append(filename=shader, directory=nodegroups_folder.__str__())
        blender.clear_duplicate_node_groups()

    def import_umaps(self):
        world_collection = self.create_collection(self.world.name.capitalize())

        for umap_name, umap_data in self.world.umaps.items():
            if not self.debug.active:
                blender.clean_scene()

            collection = self.create_collection(name=umap_name, parent=world_collection)
            umap = Map(self, umap_name, umap_data, collection)
            umap.import_objects()


    def create_collection(self, name: str, parent: bpy.types.Collection = None):

        collection = bpy.data.collections.new(name)
        if parent is None:
            main_scene = bpy.data.scenes["Scene"]
            main_scene.collection.children.link(collection)
        else:
            parent.children.link(collection)

        return collection

    def get_mesh_path(self, mesh: dict):
        # mesh_name = get_mesh_name(mesh)
        gm = fix_path(mesh["Properties"]["StaticMesh"]["ObjectPath"])
        to = get_filename(self.paths.assets_path.joinpath(gm).__str__()) + ".xay"
        return to


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
        self.__paths = paths

        self.name = prefs.selected_map
        self.umaps = []

        self.__umap_list = common.read_json(prefs.resources.joinpath("umaps.json"))[self.name]

        # Extract .json files
        for umap_path in self.__umap_list:
            self.extract_datas(umap_path)

        # Load JSONs Files
        self.objects = common.read_files(self.__paths.objects)
        self.materials = common.read_files(self.__paths.materials)
        self.materials_ovr = common.read_files(self.__paths.materials_ovr)
        self.materials_parent = common.read_files(self.__paths.materials_parent)
        self.umaps = common.read_files(self.__paths.umaps)

    def get_umap_name(self, umap_name: str):
        return umap_name.split("/")[-1]

    def extract_datas(self, umap_path: str):
        umap_name = self.get_umap_name(umap_path)
        umap_json_file = self.__paths.umaps.joinpath(umap_name + ".json")
        if not umap_json_file.exists():
            self.extract_data(umap_path)

    def extract_data(self, game_object_path: str):
        args = [
            self.__prefs.siana.__str__(),
            self.__prefs.paks_path.__str__(),
            self.__paths.map_folder.__str__(),
            game_object_path,
        ]

        subprocess.call(args)


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

        self.setupObject()
        self.setupMaterials()

    def setupObject(self):
        self.bmesh = self.get_object()

        if self.instanced:
            self.bgroup = bpy.data.objects.new(self.name + "-GRP", None)
            self.collection.objects.link(self.bgroup)

            self.reset_properties(self.bgroup)
            self.set_properties(bobject=self.bgroup, properties=self.data["Properties"])

            instances = self.data["PerInstanceSMData"]

            for index, instance_data in enumerate(instances):

                logger.info(f"[{index}] | Instancing : {common.shorten_path(self.meshfile, 4)}")
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

    def setupMaterials(self):

        if "StaticMaterials" in self.data["Properties"]:
            sm_materials = self.static_mesh["Properties"]["StaticMaterials"]
            for m in sm_materials:
                if m == None:
                    self.sm_materials.append(None)
                else:
                    mat_name = self.get_mat_name(m['MaterialInterface']['ObjectName'])
                    self.sm_materials.append(self.world.materials[mat_name])

        if "OverrideMaterials" in self.data["Properties"]:
            om_materials = self.data["Properties"]["OverrideMaterials"]
            for m in om_materials:
                if m == None:
                    self.om_materials.append(None)
                else:
                    self.om_materials.append(self.world.materials_ovr[self.get_name(m['ObjectName'])])

        self.loopMaterials()

    def loopMaterials(self):
        for index, material in enumerate(self.sm_materials):
            if material == None:
                continue

            self.set_material(material=material, slot=index)

        for index, material in enumerate(self.om_materials):
            if material == None:
                continue
            self.set_material(material=material, slot=index)

    def set_material(self, material: dict, slot: int):
        mat_name = material["Name"]

        bMaterial = bpy.data.materials.get(mat_name)
        if bMaterial is None:
            bMaterial = bpy.data.materials.new(name=mat_name)

        bMaterial.name = mat_name
        bMaterial.use_nodes = True


        # Setup Nodes

        nodes = bMaterial.node_tree.nodes
        create_node = bMaterial.node_tree.nodes.new
        link = bMaterial.node_tree.links.new


        blender.clear_nodes(nodes)


        if "Parent" in material["Properties"]:
            mat_type = get_filename(material["Properties"]["Parent"]["ObjectPath"])
        else:
            mat_type = "NO PARENT"

        N_NOTE = blender.create_node_note(nodes, mat_type)
        N_OUTPUT = nodes['Material Output']

        blender.set_node_position(N_NOTE, -350, 230)





















        # Assign the Material
        try:
            self.bmesh.material_slots[slot].material = bMaterial
        except:
            pass
        


    def get_name(self, mat_path: str):
        return mat_path.split(" ")[-1]

    def import_object(self):
        print(self.name)

    def get_object_name(self):
        return self.data["Properties"]["StaticMesh"]["ObjectPath"].rsplit("/", 1)[-1].rsplit(".", 1)[0]

    def get_mesh_path(self, path: Path):
        am = fix_path(self.data["Properties"]["StaticMesh"]["ObjectPath"])
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
            logger.info("Duplicate object: " + ob.name)
            a = duplicate_object(ob)
            self.collection.objects.link(a)
            self.reset_properties(a)
            return a

        # Import object if it doesn't exist
        else:
            with redirect_stdout(stdout):
                logger.info("Importing object: " + self.meshfile)
                a = importer_xay.xay(self.meshfile)
                self.collection.objects.link(a)
                return a

    def reset_properties(self, bobject: bpy.types.Object):
        bobject.location = [0, 0, 0]
        bobject.rotation_euler = [0, 0, 0]
        bobject.scale = [1, 1, 1]
        bobject.parent = None


class Map:
    def __init__(self, liana: Liana, umap_name: str, umap_data: dict, collection: bpy.types.Collection):
        self.prefs = liana.prefs
        self.paths = liana.paths

        self.world = liana.world
        self.collection = collection
        self.name = umap_name
        self.data = umap_data

    def import_objects(self):
        for object_data in self.data:
            object_name = get_filename(object_data["Properties"]["StaticMesh"]["ObjectPath"])
            # if object_name in 
            if not any(ext in object_name.lower() for ext in BLACKLIST_objects):
                uobject = UObject(self.world, self.paths, object_data, self.collection)


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
        self.objects = self.__debug_json["objects"]
        self.umaps = self.__debug_json["umaps"]
        self.count = self.__debug_json["count"]


def duplicate_object(bobject: bpy.types.Object, vdata: bool = False):
    obj_copy = bobject.copy()

    if vdata and obj_copy.data:
        obj_copy.data = obj_copy.data.copy()

    return obj_copy


def get_filename(object_path: str):
    return object_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]


def get_mesh_name(mesh_data: dict):
    return get_filename(mesh_data["Properties"]["StaticMesh"]["ObjectPath"])
