from pathlib import Path
import os
import bpy


def get_texture_path(path: str, extension: str):
    return fix_path(path=Path(os.path.splitext(path)[0].strip("/")).__str__()) + extension


def fix_path(path: str):
    return path.replace("ShooterGame", "Game").replace("/Content", "").replace("\Content", "")

def import_texture(texture_path:str):

    stem = Path(texture_path).stem

    img = bpy.data.images.get(stem + ".png")
    if img is None:
        img = bpy.data.images.load(texture_path)
    return img

def get_scalar_value(mat_props, s_param_name):
    if "ScalarParameterValues" in mat_props:
        for param in mat_props["ScalarParameterValues"]:
            param_name = param['ParameterInfo']['Name'].lower()
            if s_param_name.lower() in param_name:
                return param["ParameterValue"]


def get_rgb(pv: dict) -> tuple:
    return (
        pv["R"],
        pv["G"],
        pv["B"],
        pv["A"])
