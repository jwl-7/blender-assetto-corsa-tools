import os
import re
import bmesh
from typing import Any
from mathutils import Matrix, Vector
from .exporter_utils import (
    convert_matrix,
    convert_vector3,
    get_active_material_texture_slot,
)
from .kn5_writer import KN5Writer
from ..utils.constants import ASSETTO_CORSA_OBJECTS


NODES: str = 'nodes'

NODE_CLASS: dict[str, int] = {
    'Node': 1,
    'Mesh': 2,
    'SkinnedMesh': 3,
}

NODE_SETTINGS: tuple = (
    'lodIn',
    'lodOut',
    'layer',
    'castShadows',
    'visible',
    'transparent',
    'renderable',
)


class NodeWriter(KN5Writer):
    def __init__(
        self,
        file: Any,
        context: Any,
        settings: dict[str, Any],
        warnings: list[str],
        material_writer: Any
    ):
        super().__init__(file)
        self.context: Any = context
        self.settings: dict[str, Any] = settings
        self.warnings: list[str] = warnings
        self.material_writer: Any = material_writer
        self.scene: Any = self.context.scene
        self.node_settings: list['NodeSettings'] = []
        self.ac_objects: list[re.Pattern] = []
        self._init_assetto_corsa_objects()
        self._init_node_settings()

    def _init_node_settings(self):
        self.node_settings = []
        if NODES in self.settings:
            for node_key in self.settings[NODES]:
                self.node_settings.append(NodeSettings(self.settings, node_key))

    def _init_assetto_corsa_objects(self):
        for obj_name in ASSETTO_CORSA_OBJECTS:
            self.ac_objects.append(re.compile(f'^{obj_name}$'))

    def _is_ac_object(self, name: str) -> bool:
        for regex in self.ac_objects:
            if regex.match(name):
                return True
        return False

    def write(self):
        self._write_base_node(None, 'BlenderFile')
        for obj in sorted(self.context.blend_data.objects, key=lambda k: len(k.children)):
            if not obj.parent:
                self._write_object(obj)

    def _write_object(self, obj: Any):
        if not obj.name.startswith('__'):
            if obj.type == 'MESH':
                if obj.children:
                    raise Exception(f"A mesh cannot contain children ('{obj.name}')")
                self._write_mesh_node(obj)
            else:
                self._write_base_node(obj, obj.name)
            for child in obj.children:
                self._write_object(child)

    def _any_child_is_mesh(self, obj: Any) -> bool:
        for child in obj.children:
            if child.type in ['MESH', 'CURVE'] or self._any_child_is_mesh(child):
                return True
        return False

    def _write_base_node(self, obj: Any | None, node_name: str):
        node_data: dict[str, Any] = {}
        matrix: Matrix | None = None
        num_children: int = 0
        if not obj:
            matrix = Matrix()
            for obj in self.context.blend_data.objects:
                if not obj.parent and not obj.name.startswith('__'):
                    num_children += 1
        else:
            if not self._is_ac_object(obj.name) and not self._any_child_is_mesh(obj):
                msg: str = f"Unknown logical object '{obj.name}' might prevent other objects from loading.{os.linesep}"
                msg += f"\tRename it to '__{obj.name}' if you do not want to export it."
                self.warnings.append(msg)
            matrix = convert_matrix(obj.matrix_local)
            for child in obj.children:
                if not child.name.startswith('__'):
                    num_children += 1

        node_data['name'] = node_name
        node_data['childCount'] = num_children
        node_data['active'] = True
        node_data['transform'] = matrix
        self._write_base_node_data(node_data)

    def _write_base_node_data(self, node_data: dict[str, Any]):
        self._write_node_class('Node')
        self.write_string(node_data['name'])
        self.write_uint(node_data['childCount'])
        self.write_bool(node_data['active'])
        self.write_matrix(node_data['transform'])

    def _write_mesh_node(self, obj: Any):
        divided_meshes: list['Mesh'] = self._split_object_by_materials(obj)
        divided_meshes = self._split_meshes_for_vertex_limit(divided_meshes)
        if obj.parent or len(divided_meshes) > 1:
            node_data: dict[str, Any] = {}
            node_data['name'] = obj.name
            node_data['childCount'] = len(divided_meshes)
            node_data['active'] = True
            transform_matrix: Matrix = Matrix()
            if obj.parent:
                transform_matrix = convert_matrix(obj.parent.matrix_world.inverted())
            node_data['transform'] = transform_matrix
            self._write_base_node_data(node_data)
        node_properties: 'NodeProperties' = NodeProperties(obj)
        for node_setting in self.node_settings:
            node_setting.apply_settings_to_node(node_properties)
        for mesh in divided_meshes:
            self._write_mesh(obj, mesh, node_properties)

    def _write_node_class(self, node_class: str):
        self.write_uint(NODE_CLASS[node_class])

    def _write_mesh(
        self,
        obj: Any,
        mesh: 'Mesh',
        node_properties: 'NodeProperties'
    ):
        self._write_node_class('Mesh')
        self.write_string(obj.name)
        self.write_uint(0)
        is_active: bool = True
        self.write_bool(is_active)
        self.write_bool(node_properties.castShadows)
        self.write_bool(node_properties.visible)
        self.write_bool(node_properties.transparent)
        if len(mesh.vertices) > 2**16:
            raise Exception(f"Only {2**16} vertices per mesh allowed. ('{obj.name}')")
        self.write_uint(len(mesh.vertices))
        for vertex in mesh.vertices:
            self.write_vector3(vertex.co)
            self.write_vector3(vertex.normal)
            self.write_vector2(vertex.uv)
            self.write_vector3(vertex.tangent)
        self.write_uint(len(mesh.indices))
        for i in mesh.indices:
            self.write_ushort(i)
        if mesh.material_id is None:
            self.warnings.append(f"No material to mesh '{obj.name}' assigned")
            self.write_uint(0)
        else:
            self.write_uint(mesh.material_id)
        self.write_uint(node_properties.layer)
        self.write_float(node_properties.lodIn)
        self.write_float(node_properties.lodOut)
        self._write_bounding_sphere(mesh.vertices)
        self.write_bool(node_properties.renderable)

    def _write_bounding_sphere(self, vertices: list['UvVertex']):
        if not vertices:
            self.write_vector3((0, 0, 0))
            self.write_float(0)
            return

        min_v: list[float] = [min(v.co[i] for v in vertices) for i in range(3)]
        max_v: list[float] = [max(v.co[i] for v in vertices) for i in range(3)]

        center: list[float] = [
            (min_v[0] + max_v[0]) / 2,
            (min_v[1] + max_v[1]) / 2,
            (min_v[2] + max_v[2]) / 2
        ]

        max_dist_sq: float = 0
        for v in vertices:
            dist_sq: float = sum((v.co[i] - center[i])**2 for i in range(3))
            if dist_sq > max_dist_sq:
                max_dist_sq = dist_sq

        radius: float = max_dist_sq**0.5

        self.write_vector3(center)
        self.write_float(radius)

    def _split_object_by_materials(self, obj: Any) -> list['Mesh']:
        meshes: list['Mesh'] = []
        mesh_copy: Any = obj.to_mesh()

        bm: Any = bmesh.new()
        bm.from_mesh(mesh_copy)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(mesh_copy)
        bm.free()

        try:
            mesh_copy.calc_loop_triangles()
            mesh_copy.calc_tangents()
            mesh_vertices: list[Any] = mesh_copy.vertices[:]
            mesh_loops: list[Any] = mesh_copy.loops[:]
            mesh_triangles: list[Any] = mesh_copy.loop_triangles[:]
            uv_layer: Any = mesh_copy.uv_layers.active
            matrix: Matrix = obj.matrix_world

            if not mesh_copy.materials:
                raise Exception(f"Object '{obj.name}' has no material assigned")

            used_materials: set[int] = set([triangle.material_index for triangle in mesh_triangles])
            for material_index in used_materials:
                if not mesh_copy.materials[material_index]:
                    raise Exception(f"Material slot {material_index} for object '{obj.name}' has no material assigned")
                material_name: str = mesh_copy.materials[material_index].name
                if material_name.startswith('__'):
                    raise Exception(f"Material '{material_name}' is ignored but is used by object '{obj.name}'")

                vertices: dict['UvVertex', int] = {}
                indices: list[int] = []
                for triangle in mesh_triangles:
                    if material_index != triangle.material_index:
                        continue
                    vertex_index_for_face: int = 0
                    face_indices: list[int] = []
                    for loop_index in triangle.loops:
                        loop: Any = mesh_loops[loop_index]
                        local_position: Vector = matrix @ mesh_vertices[loop.vertex_index].co
                        converted_position: Vector = convert_vector3(local_position)
                        converted_normal: Vector = convert_vector3(loop.normal)
                        converted_tangent: Vector = convert_vector3(loop.tangent)

                        uv: tuple = (0, 0)
                        if uv_layer:
                            uv = uv_layer.data[loop_index].uv
                            uv = (uv[0], -uv[1])
                        else:
                            uv = self._calculate_uvs(obj, mesh_copy, material_index, local_position)

                        vertex: 'UvVertex' = UvVertex(converted_position, converted_normal, uv, converted_tangent)
                        if vertex not in vertices:
                            new_index: int = len(vertices)
                            vertices[vertex] = new_index
                        face_indices.append(vertices[vertex])
                        vertex_index_for_face += 1
                    indices.extend((face_indices[1], face_indices[2], face_indices[0]))
                    if len(face_indices) == 4:
                        indices.extend((face_indices[2], face_indices[3], face_indices[0]))
                vertices_list: list['UvVertex'] = [v for v, index in sorted(vertices.items(), key=lambda k: k[1])]
                material_id: int = self.material_writer.material_positions[material_name]
                meshes.append(Mesh(material_id, vertices_list, indices))
        finally:
            obj.to_mesh_clear()
        return meshes

    def _split_meshes_for_vertex_limit(self, divided_meshes: list['Mesh']) -> list['Mesh']:
        new_meshes: list['Mesh'] = []
        limit: int = 2**16
        for mesh in divided_meshes:
            if len(mesh.vertices) > limit:
                start_index: int = 0
                while start_index < len(mesh.indices):
                    vertex_index_mapping: dict[int, int] = {}
                    new_indices: list[int] = []
                    for i in range(start_index, len(mesh.indices), 3):
                        start_index += 3
                        face: list[int] = mesh.indices[i:i+3]
                        for face_index in face:
                            if face_index not in vertex_index_mapping:
                                new_index: int = len(vertex_index_mapping)
                                vertex_index_mapping[face_index] = new_index
                            new_indices.append(vertex_index_mapping[face_index])
                        if len(vertex_index_mapping) >= limit - 3:
                            break
                    verts: list['UvVertex'] = [mesh.vertices[v] for v, index in sorted(vertex_index_mapping.items(), key=lambda k: k[1])]
                    new_meshes.append(Mesh(mesh.material_id, verts, new_indices))
            else:
                new_meshes.append(mesh)
        return new_meshes

    def _calculate_uvs(
        self,
        obj: Any,
        mesh: Any,
        material_id: int,
        co: Vector
    ) -> tuple:
        size: Vector = obj.dimensions
        x: float = co[0] / size[0]
        y: float = co[1] / size[1]
        mat: Any = mesh.materials[material_id]
        texture_node: Any = get_active_material_texture_slot(mat)
        if texture_node:
            x *= texture_node.texture_mapping.scale[0]
            y *= texture_node.texture_mapping.scale[1]
            x += texture_node.texture_mapping.translation[0]
            y += texture_node.texture_mapping.translation[1]
        return (x, y)


class NodeProperties:
    def __init__(self, node: Any):
        ac_node: Any = node.assettoCorsa
        self.name: str = node.name
        self.lodIn: float = ac_node.lodIn
        self.lodOut: float = ac_node.lodOut
        self.layer: int = ac_node.layer
        self.castShadows: bool = ac_node.castShadows
        self.visible: bool = ac_node.visible
        self.transparent: bool = ac_node.transparent
        self.renderable: bool = ac_node.renderable


class NodeSettings:
    def __init__(
        self,
        settings: dict[str, Any],
        node_settings_key: str
    ):
        self._settings: dict[str, Any] = settings
        self._node_settings_key: str = node_settings_key
        self._node_name_matches: list[re.Pattern] = self._convert_to_matches_list(node_settings_key)

    def apply_settings_to_node(self, node: NodeProperties):
        if not self._does_node_name_match(node.name):
            return
        for setting in NODE_SETTINGS:
            setting_val: Any = self._get_node_setting(setting)
            if setting_val is not None:
                setattr(node, setting, setting_val)

    def _does_node_name_match(self, node_name: str) -> bool:
        for regex in self._node_name_matches:
            if regex.match(node_name):
                return True
        return False

    def _convert_to_matches_list(self, key: str) -> list[re.Pattern]:
        matches: list[re.Pattern] = []
        for subkey in key.split('|'):
            matches.append(re.compile(f'^{self._escape_match_key(subkey)}$', re.IGNORECASE))
        return matches

    def _escape_match_key(self, key: str) -> str:
        wildcard_replacement: str = '__WILDCARD__'
        key = key.replace('*', wildcard_replacement)
        key = re.escape(key)
        key = key.replace(wildcard_replacement, '.*')
        return key

    def _get_node_setting(self, setting: str) -> Any | None:
        if setting in self._settings[NODES][self._node_settings_key]:
            return self._settings[NODES][self._node_settings_key][setting]
        return None


class UvVertex:
    def __init__(self, co: Vector, normal: Vector, uv: tuple, tangent: Vector):
        self.co: Vector = co
        self.normal: Vector = normal
        self.uv: tuple = uv
        self.tangent: Vector = tangent
        self.hash: int | None = None

    def __hash__(self) -> int:
        if not self.hash:
            self.hash = hash(
                hash(self.co[0]) ^
                hash(self.co[1]) ^
                hash(self.co[2]) ^
                hash(self.normal[0]) ^
                hash(self.normal[1]) ^
                hash(self.normal[2]) ^
                hash(self.uv[0]) ^
                hash(self.uv[1]) ^
                hash(self.tangent[0]) ^
                hash(self.tangent[1]) ^
                hash(self.tangent[2])
            )
        return self.hash

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, UvVertex):
            return False
        if self.co[0] != other.co[0] or self.co[1] != other.co[1] or self.co[2] != other.co[2]:
            return False
        if self.normal[0] != other.normal[0] or self.normal[1] != other.normal[1] or self.normal[2] != other.normal[2]:
            return False
        if self.uv[0] != other.uv[0] or self.uv[1] != other.uv[1]:
            return False
        if (self.tangent[0] != other.tangent[0]
                or self.tangent[1] != other.tangent[1]
                or self.tangent[2] != other.tangent[2]):
            return False
        return True


class Mesh:
    def __init__(
        self,
        material_id: int,
        vertices: list[UvVertex],
        indices: list[int]
    ):
        self.material_id: int = material_id
        self.vertices: list[UvVertex] = vertices
        self.indices: list[int] = indices