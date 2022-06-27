
import bpy
import os
import json
from pathlib import Path
from subprocess import run
from shutil import rmtree
from collections.abc import Iterable
from enum import Enum
import requests


FILEBROWSER_PATH = os.path.join(os.getenv('WINDIR'), 'explorer.exe')


# ANCHOR: Functions
# -------------------------- #


def open_folder(path):
    """
    Open a file explorer to a path
    :param path: path to folder
    :return:
    """
    path = os.path.normpath(path)

    if os.path.isdir(path):
        run([FILEBROWSER_PATH, path])


def get_files(path: str, extension: str = "") -> list:
    """
    Get all files in a directory
    :param path: path to directory
    :param extension: extension of files to get
    :return: list of files
    """
    files = list()
    for file in os.listdir(path):
        if extension in file:
            files.append(Path(os.path.join(path, file)))
    return files


def remove_file(path: str):
    """
    Remove a file
    """
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)  # remove the file
    elif os.path.isdir(path):
        rmtree(path)  # remove dir and all contains
    else:
        raise ValueError("file {} is not a file or dir.".format(path))


def open_folder(path):
    """
    Open a file explorer to a path
    :param path: path to folder
    :return:
    """
    path = os.path.normpath(path)

    if os.path.isdir(path):
        run([FILEBROWSER_PATH, path])


def save_list(filepath: Path, lines: list):
    """
    Save a list to a file
    :param filepath: path to file
    :param lines: list of lines
    :return:
    """

    # Flatten umap objects
    lines = list(flatten_list(lines))

    # Remove Duplicates
    lines = list(dict.fromkeys(lines))

    with open(filepath.__str__(), 'w') as f:
        f.write('\n'.join(lines))
    return filepath.__str__()


def save_json(p: str, d):
    """
    Save a dictionary to a json file
    :param p: path to file
    :param d: dictionary
    :return:
    """
    with open(p, 'w') as jsonfile:
        json.dump(d, jsonfile, indent=4)


def read_json(p: str) -> dict:
    """
    Read a json file and return a dictionary
    :param p: path to file
    :return:
    """
    with open(p) as json_file:
        return json.load(json_file)


def shorten_path(file_path, length) -> str:
    """
    Shorten a path to a given length
    :param file_path: path to shorten
    :param length: length to shorten to
    :return: shortened path
    """
    return f"..\{os.sep.join(file_path.split(os.sep)[-length:])}"


def flatten_list(collection):
    """
    Flatten a list of lists
    :param collection: list of lists
    :return: list
    """

    for x in collection:
        if isinstance(x, Iterable) and not isinstance(x, str):
            yield from flatten_list(x)
        else:
            yield x


def reset_properties(byo: bpy.types.ObjectModifiers):
    byo.location = [0, 0, 0]
    byo.rotation_euler = [0, 0, 0]
    byo.scale = [1, 1, 1]
    byo.parent = None


def create_folders(self):
    for attr, value in self.__dict__.items():
        if "path" in attr:
            f = Path(value)
            if not f.exists():
                print(f"Creating folder {f}")
                f.mkdir(parents=True)


# ANCHOR: Classes
# -------------------------- #


class BlendMode(Enum):
    OPAQUE = 0
    CLIP = 1
    BLEND = 2
    HASHED = 3


def get_umap_list() -> list:
    script_path = os.path.dirname(os.path.abspath(__file__))
    umap_list_path = Path(script_path).joinpath("assets").joinpath("umaps.json")
    umap_list = read_json(umap_list_path)
    return umap_list




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
