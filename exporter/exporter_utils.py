import json
import os
from typing import Any
import bpy
from mathutils import Matrix, Quaternion, Vector


def convert_matrix(in_matrix: Matrix) -> Matrix:
    """Converts a Blender matrix to Assetto Corsa coordinate system."""
    co: Vector
    rotation: Quaternion
    scale: Vector
    co, rotation, scale = in_matrix.decompose()

    co = convert_vector3(co)
    rotation = convert_quaternion(rotation)

    mat_loc: Matrix = Matrix.Translation(co)
    mat_scale_1: Matrix = Matrix.Scale(scale[0], 4, (1, 0, 0))
    mat_scale_2: Matrix = Matrix.Scale(scale[2], 4, (0, 1, 0))
    mat_scale_3: Matrix = Matrix.Scale(scale[1], 4, (0, 0, 1))
    mat_scale: Matrix = mat_scale_1 @ mat_scale_2 @ mat_scale_3
    mat_rot: Matrix = rotation.to_matrix().to_4x4()

    return mat_loc @ mat_rot @ mat_scale


def convert_vector3(in_vec: Vector) -> Vector:
    """Swaps Y and Z axes and negates Y for Assetto Corsa."""
    return Vector((in_vec[0], in_vec[2], -in_vec[1]))


def convert_quaternion(in_quat: Quaternion) -> Quaternion:
    """Converts quaternion rotation for Assetto Corsa."""
    axis: Vector
    angle: float
    axis, angle = in_quat.to_axis_angle()
    axis = convert_vector3(axis)
    return Quaternion(axis, angle)


def get_texture_nodes(material: bpy.types.Material) -> list[bpy.types.ShaderNodeTexImage]:
    """Retrieves all image texture nodes from a material."""
    texture_nodes: list[bpy.types.ShaderNodeTexImage] = []
    if material.node_tree:
        for node in material.node_tree.nodes:
            if isinstance(node, bpy.types.ShaderNodeTexImage):
                texture_nodes.append(node)
    return texture_nodes


def get_all_texture_nodes(context: bpy.types.Context) -> list[bpy.types.ShaderNodeTexImage]:
    """Aggregates all texture nodes used by meshes in the blend data."""
    scene_texture_nodes: list[bpy.types.ShaderNodeTexImage] = []
    for obj in context.blend_data.objects:
        if obj.type != 'MESH':
            continue
        for slot in obj.material_slots:
            if slot.material:
                scene_texture_nodes.extend(get_texture_nodes(slot.material))
    return scene_texture_nodes


def get_active_material_texture_slot(material: bpy.types.Material) -> bpy.types.ShaderNodeTexImage | None:
    """Returns the first visible texture node in a material."""
    texture_nodes: list[bpy.types.ShaderNodeTexImage] = get_texture_nodes(material)
    for texture_node in texture_nodes:
        if texture_node.show_texture:
            return texture_node
    return None


def read_settings(file: str) -> dict[str, Any]:
    """Reads settings.json relative to the export file path."""
    full_path: str = os.path.abspath(file)
    dir_name: str = os.path.dirname(full_path)
    settings_path: str = os.path.join(dir_name, 'settings.json')
    if not os.path.exists(settings_path):
        return {}
    return json.loads(open(settings_path, 'r').read())
