import struct
from typing import List, Optional, Tuple, Union

import bpy
from bpy import app
from bpy.types import AttributeGroup, LoopColors, Mesh, Object

unpack_uint8 = struct.Struct("<B").unpack
unpack_4uint8 = struct.Struct("<4B").unpack
unpack_2floats = struct.Struct("<2f").unpack
unpack_8floats = struct.Struct("<8f").unpack
unpack_3uint16 = struct.Struct("<3H").unpack
unpack_2uint32 = struct.Struct("<2I").unpack
unpack_3uint32 = struct.Struct("<3I").unpack
unpack_header1 = struct.Struct("<B?H").unpack
unpack_magicver = struct.Struct("<IB").unpack

VCOL_ATTR_NAME = "vertex_colors"
VCOL_LAYER_KWARGS = {"do_init": False}

if app.version >= (3, 2, 0):
    VCOL_ATTR_NAME = "color_attributes"
    VCOL_LAYER_KWARGS = {"type": "BYTE_COLOR", "domain": "CORNER"}


def set_vcols_on_layer(
    mesh: Mesh,
    vertex_colors: List[Tuple[int, int, int, int]],
    color_layer_name: str = "Col",
) -> None:
    mesh_cols: Union[AttributeGroup, LoopColors]
    mesh_cols = getattr(mesh, VCOL_ATTR_NAME)

    if len(mesh_cols):
        color_layer = mesh_cols[color_layer_name]
    else:
        color_layer = mesh_cols.new(name=color_layer_name, **VCOL_LAYER_KWARGS)

    if VCOL_ATTR_NAME == "vertex_colors":
        vertex_colors = [
            (*map(color_linear_to_srgb, rgb), a) for *rgb, a in vertex_colors
        ]

    color_layer.data.foreach_set(
        "color",
        [
            c
            for e in [vertex_colors[loop.vertex_index] for loop in mesh.loops]
            for c in e
        ],
    )


def color_linear_to_srgb(c: float) -> float:
    """
    Convert from linear to sRGB color space.
    Source: Cycles addon implementation, node_color.h.
    """
    if c < 0.0031308:
        return 0.0 if c < 0.0 else c * 12.92
    else:
        return 1.055 * c ** (1.0 / 2.4) - 0.055


def xay(xay_path: str) -> Optional[Object]:
    """
    XAY only supports static meshes.
    XAY was implemented because we needed a simple and 'cheap' format that doesn't dedupe verts.
    Source: (as documentation is non-existent)
    https://github.com/floxay/UEViewer/blob/master/Exporters/ExportXAY.cpp
    """
    with open(xay_path, "rb") as f:
        magic, version = unpack_magicver(f.read(5))
        if magic != 0x02594158:
            print("Not a XAY file.")
            return

        f.seek(f.tell() + 3)  # unused/reserved bytes

        vertex_count, face_count = unpack_2uint32(f.read(8))
        uv_count, has_vcols, section_count = unpack_header1(f.read(4))

        materials = []

        for section in range(section_count):
            (str_len,) = unpack_uint8(f.read(1))
            # null terminated string, so yea, lol
            sec_name, sec_first_idx = struct.unpack(
                f"<{str_len-1}sxI", f.read(str_len + 4)
            )
            materials.append((str(sec_name, "utf8"), sec_first_idx))
        positions = []
        normals = []
        uvs = [[]]

        for vert in range(vertex_count):
            floats = unpack_8floats(f.read(32))
            positions.append((floats[0], floats[2], floats[4]))
            normals.append((floats[1], floats[3], floats[5]))
            uvs[0].append((floats[6], floats[7]))

        faces = []

        if vertex_count > 0xFFFF + 1:
            [faces.append(unpack_3uint32(f.read(12))) for _ in range(face_count)]
        else:
            [faces.append(unpack_3uint16(f.read(6))) for _ in range(face_count)]

        for extra_uv_idx in range(1, uv_count):
            uvs.append([])
            for vert in range(vertex_count):
                uv = unpack_2floats(f.read(8))
                uvs[extra_uv_idx].append(uv)

        vertex_colors = []

        if has_vcols:
            for vert in range(vertex_count):
                r, g, b, a = unpack_4uint8(f.read(4))
                vertex_colors.append((r / 255, g / 255, b / 255, a / 255))

        # filename from path without extension
        fn = xay_path.rsplit("\\", 1)[-1][:-4]
        # creating mesh
        mesh = bpy.data.meshes.new(fn)
        mesh.from_pydata(positions, [], faces)
        obj = bpy.data.objects.new(fn, mesh)

        # setting uvs
        for uv_idx in range(uv_count):
            mesh.uv_layers.new(name=f"UVMap_{uv_idx}")
            mesh.uv_layers[uv_idx].data.foreach_set(
                "uv",
                [
                    uv
                    for p in [uvs[uv_idx][loop.vertex_index] for loop in mesh.loops]
                    for uv in p
                ],
            )

        # appending mats to mesh
        for material in materials:
            mat = bpy.data.materials.new(material[0])
            mesh.materials.append(mat)

        # setting mats
        for mat_idx in range(len(materials) - 1):
            for face_idx in range(materials[mat_idx][1], materials[mat_idx + 1][1]):
                mesh.polygons[face_idx].material_index = mat_idx + 1

        # setting vertex colors
        if has_vcols:
            set_vcols_on_layer(mesh, vertex_colors)

        mesh.validate()
        mesh.update()

        # setting normals
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        mesh.create_normals_split()
        mesh.normals_split_custom_set_from_vertices(normals)
        mesh.use_auto_smooth = True
        # bpy.data.scenes[0].collection.objects.link(obj)

        # bpy.context.view_layer.objects.active = obj

        return obj
