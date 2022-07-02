import bpy
import os
import logging
from math import radians
from ..utils.common import setup_logger

logger = setup_logger(__name__)

def clean_scene(debug: bool = False):
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)

    for block in bpy.data.materials:
        bpy.data.materials.remove(block)

    for block in bpy.data.collections:
        bpy.data.collections.remove(block)

    for block in bpy.data.objects:
        bpy.data.objects.remove(block)

    for block in bpy.data.textures:
        bpy.data.images.remove(block)

    for block in bpy.data.images:
        if ".hdr" not in block.name and "Skies" not in block.name:
            bpy.data.images.remove(block)
        
    for block in bpy.data.lights:
        bpy.data.lights.remove(block)


    if debug:
        for block in bpy.data.node_groups:
            if "VALORANT_" in block.name:
                bpy.data.node_groups.remove(block)


def clear_duplicate_node_groups():
    """
    Clear the duplicate node groups
    """

    # --- Search for duplicates in actual node groups
    node_groups = bpy.data.node_groups

    for group in node_groups:
        for node in group.nodes:
            if node.type == 'GROUP':
                clear_node_group(node)

    # --- Search for duplicates in materials
    mats = list(bpy.data.materials)
    worlds = list(bpy.data.worlds)

    for mat in mats + worlds:
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP':
                    clear_node_group(node)

    for block in bpy.data.node_groups:
        if ".00" in block.name:
            bpy.data.node_groups.remove(block)


def clear_node_group(node):
    """
    Clear the node group
    Args:
        node (bpy.types.Node): Node to clear
    """

    node_groups = bpy.data.node_groups

    # Get the node group name as 3-tuple (base, separator, extension)
    (base, sep, ext) = node.node_tree.name.rpartition('.')

    # Replace the numeric duplicate
    if ext.isnumeric():
        if base in node_groups:
            # print("  Replace '%s' with '%s'" % (node.node_tree.name, base))
            node.node_tree.use_fake_user = False
            node.node_tree = node_groups.get(base)


def import_shaders(settings):
    shaders_blend_file = settings.importer_assets_path.joinpath("VALORANT_Map.blend")
    nodegroups_folder = shaders_blend_file.joinpath("NodeTree")
    for shader in settings.shaders:
        if shader not in bpy.data.node_groups.keys():
            bpy.ops.wm.append(filename=shader, directory=nodegroups_folder.__str__())

# ANCHOR : Property Controls

def fx(yo):
    return radians(yo)

def set_properties(byo: bpy.types.Object, object: dict, is_instanced: bool = False, is_light: bool = False):
    if is_instanced:
        if "OffsetLocation" in object:
            byo.location = [
                byo.location[0] + (object["OffsetLocation"]["X"] * 0.01),
                byo.location[1] + (object["OffsetLocation"]["Y"] * -0.01),
                byo.location[2] + (object["OffsetLocation"]["Z"] * 0.01)
            ]
    else:
        if "RelativeLocation" in object:
            byo.location = [
                object["RelativeLocation"]["X"] * 0.01,
                object["RelativeLocation"]["Y"] * -0.01,
                object["RelativeLocation"]["Z"] * 0.01
            ]

    if "RelativeRotation" in object:
        byo.rotation_mode = 'XYZ'
        byo.rotation_euler = [
            fx(object["RelativeRotation"]["Roll"]),
            fx(-object["RelativeRotation"]["Pitch"]),
            fx(-object["RelativeRotation"]["Yaw"])
        ]

    if "RelativeScale3D" in object:
        byo.scale = [
            object["RelativeScale3D"]["X"],
            object["RelativeScale3D"]["Y"],
            object["RelativeScale3D"]["Z"]
        ]

    if is_light:
        if "RelativeRotation" in object:
            byo.rotation_mode = 'XYZ'
            byo.rotation_euler = [
                # abs(n)
                fx(object["RelativeRotation"]["Roll"]),
                fx(object["RelativeRotation"]["Pitch"]),
                fx(-object["RelativeRotation"]["Yaw"])
            ]

        if "RelativeScale3D" in object:
            byo.scale = [
                object["RelativeScale3D"]["X"],
                object["RelativeScale3D"]["Y"],
                object["RelativeScale3D"]["Z"]
            ]

def reset_properties(byo: bpy.types.ObjectModifiers):
    byo.location = [0, 0, 0]
    byo.rotation_euler = [0, 0, 0]
    byo.scale = [1, 1, 1]
    byo.parent = None

def set_min_max_default(inp, min, max, default):
    """
    Sets the min, max and default values of a node socket.
    :param inp:
    :param min:
    :param max:
    :param default:
    :return:"""
    inp.min_value = min
    inp.max_value = max
    inp.default_value = default


# ANCHOR : Nodes


def create_node_note(nodes: bpy.types.Nodes, msg) -> bpy.types.Node:
    N_Note = nodes.new("NodeFrame")
    N_Note.label = msg
    N_Note.width = 320
    N_Note.height = 30
    return N_Note

def clear_nodes(nodes):
    nn: bpy.types.Node
    for nn in nodes:
        if nn.type != "OUTPUT_MATERIAL" and nn.type != "VERTEX_COLOR":
            nodes.remove(nn)

def set_node_position(node: bpy.types.Node, x: int, y: int):
    node.location.x = x
    node.location.y = y

def create_node_color(nodes, param_name, rgb, x, y):
    node = nodes.new("ShaderNodeRGB")
    node.label = param_name
    node.name = param_name
    node.location.x = x
    node.location.y = y
    node.outputs[0].default_value = rgb
    return node


def clear_duplicate_node_groups():
    """
    Clear the duplicate node groups
    """

    # --- Search for duplicates in actual node groups
    node_groups = bpy.data.node_groups

    for group in node_groups:
        for node in group.nodes:
            if node.type == 'GROUP':
                clear_node_group(node)

    # --- Search for duplicates in materials
    mats = list(bpy.data.materials)
    worlds = list(bpy.data.worlds)

    for mat in mats + worlds:
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'GROUP':
                    clear_node_group(node)

    for block in bpy.data.node_groups:
        if ".00" in block.name:
            bpy.data.node_groups.remove(block)

def remove_master_objects():
    for block in bpy.data.objects:
        if block.hide_viewport == True and block.hide_render == True:
            bpy.data.objects.remove(block)

def remove_duplicate_mats():
    # --- Search for mat. slots in all objects
    mats = bpy.data.materials

    logger.info(f"Material Count :  {len(bpy.data.materials)}")
    logger.info(f"Image Count :  {len(bpy.data.images)}")

    for obj in bpy.data.objects:
        for slot in obj.material_slots:

            # Get the material name as 3-tuple (base, separator, extension)
            (base, sep, ext) = slot.name.rpartition('.')

            # Replace the numbered duplicate with the original if found
            if ext.isnumeric():
                mat = mats.get(base)
                if mat is not None:
                    slot.material = mats.get(base)
                # if base in mats:
                #     # print("  For object '%s' replace '%s' with '%s'" % (obj.name, slot.name, base))
                #     slot.material = mats.get(base)
                    
                if not slot.material.users:
                    bpy.data.materials.remove(slot.material)


    # for material check for texture nodes
    # if it has a digit check if the original exists
    # if original has also digits remove

    for mat in bpy.data.materials:
        if mat.node_tree:
            for n in mat.node_tree.nodes:
                if n.type == 'TEX_IMAGE':
                    if n.image is None:
                        print(mat.name,'has an image node with no image')
                    elif n.image.name[-3:].isdigit():
                        name = n.image.name[:-4]
                        img = bpy.data.images.get(name)
                        if img is not None:
                            n.image = img
                        else:
                            n.image.name = name

    for material in bpy.data.materials:
        if not material.users:
            bpy.data.materials.remove(material)

    for image in bpy.data.images:
        if not image.users:
            bpy.data.images.remove(image)

    logger.info(f"New Material Count :  {len(bpy.data.materials)}")
    logger.info(f"New Image Count :  {len(bpy.data.images)}")

