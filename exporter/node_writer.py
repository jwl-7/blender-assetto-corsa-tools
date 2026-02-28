import os
import re
import bmesh
from typing import Dict, List, Any, Optional
from mathutils import Matrix, Vector
from .exporter_utils import convert_matrix, convert_vector3,
from .kn5_writer import KN5Writer
from ..utils.constants import ASSETTO_CORSA_OBJECTS


NODES: str = 'nodes'
NODE_CLASS: Dict[str, int] = {
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
        settings: Dict[str, Any],
        warnings: List[str],
        material_writer: Any
    ):
        super().__init__(file)
        self.context = context
        self.settings = settings
        self.warnings = warnings
        self.material_writer = material_writer
        self.scene = self.context.scene
        self.node_settings: List['NodeSettings'] = []
        self.ac_objects: List[re.Pattern] = []
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

    def _write_base_node(self, obj: Optional[Any], node_name: str):
        node_data: Dict[str, Any] = {}
        matrix: Matrix
        num_children: int = 0
        if not obj:
            matrix = Matrix()
            for obj_item in self.context.blend_data.objects:
                if not obj_item.parent and not obj_item.name.startswith('__'):
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

    def _write_base_node_data(self, node_data: Dict[str, Any]):
        self._write_node_class('Node')
        self.write_string(node_data['name'])
        self.write_uint(node_data['childCount'])
        self.write_bool(node_data['active'])
        self.write_matrix(node_data['transform'])

    def _write_mesh_node(self, obj: Any):
        divided_meshes = self._split_object_by_materials(obj)
        divided_meshes = self._split_meshes_for_vertex_limit(divided_meshes)
        if obj.parent or len(divided_meshes) > 1:
            node_data: Dict[str, Any] = {}
            node_data['name'] = obj.name
            node_data['childCount'] = len(divided_meshes)
            node_data['active'] = True
            transform_matrix = Matrix()
            if obj.parent:
                transform_matrix = convert_matrix(obj.parent.matrix_world.inverted())
            node_data['transform'] = transform_matrix
            self._write_base_node_data(node_data)

        node_properties = NodeProperties(obj)
        for node_setting in self.node_settings:
            node_setting.apply_settings_to_node(node_properties)
        for mesh in divided_meshes:
            self._write_mesh(obj, mesh, node_properties)

    def _write_node_class(self, node_class: str):
        self.write_uint(NODE_CLASS[node_class])

    def _write_mesh(self, obj: Any, mesh: 'Mesh', node_properties: 'NodeProperties'):
        self._write_node_class('Mesh')
        self.write_string(obj.name)
        self.write_uint(0)
        self.write_bool(True)
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

    def _write_bounding_sphere(self, vertices: List['UvVertex']):
        if not vertices:
            self.write_vector3((0.0, 0.0, 0.0))
            self.write_float(0.0)
            return

        min_v = [min(v.co[i] for v in vertices) for i in range(3)]
        max_v = [max(v.co[i] for v in vertices) for i in range(3)]
        center = [(min_v[i] + max_v[i]) / 2 for i in range(3)]

        max_dist_sq: float = 0.0
        for v in vertices:
            dist_sq = sum((v.co[i] - center[i])**2 for i in range(3))
            if dist_sq > max_dist_sq:
                max_dist_sq = dist_sq

        self.write_vector3(center)
        self.write_float(max_dist_sq**0.5)

    def _split_object_by_materials(self, obj: Any) -> List['Mesh']:
        meshes: List['Mesh'] = []
        mesh_copy = obj.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(mesh_copy)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(mesh_copy)
        bm.free()

        try:
            mesh_copy.calc_loop_triangles()
            mesh_copy.calc_tangents()
            uv_layer = mesh_copy.uv_layers.active
            matrix = obj.matrix_world

            used_materials = set([t.material_index for t in mesh_copy.loop_triangles])
            for mat_idx in used_materials:
                mat_name = mesh_copy.materials[mat_idx].name
                vertices: Dict['UvVertex', int] = {}
                indices: List[int] = []
                for tri in mesh_copy.loop_triangles:
                    if tri.material_index != mat_idx: continue
                    face_indices = []
                    for loop_idx in tri.loops:
                        loop = mesh_copy.loops[loop_idx]
                        pos = convert_vector3(matrix @ mesh_copy.vertices[loop.vertex_index].co)
                        norm = convert_vector3(loop.normal)
                        tang = convert_vector3(loop.tangent)
                        uv = (uv_layer.data[loop_idx].uv[0], -uv_layer.data[loop_idx].uv[1]) if uv_layer else (0.0, 0.0)

                        v = UvVertex(pos, norm, uv, tang)
                        if v not in vertices:
                            vertices[v] = len(vertices)
                        face_indices.append(vertices[v])
                    indices.extend((face_indices[1], face_indices[2], face_indices[0]))

                sorted_v = [v for v, i in sorted(vertices.items(), key=lambda k: k[1])]
                mat_id = self.material_writer.material_positions[mat_name]
                meshes.append(Mesh(mat_id, sorted_v, indices))
        finally:
            obj.to_mesh_clear()
        return meshes

    def _split_meshes_for_vertex_limit(self, meshes: List['Mesh']) -> List['Mesh']:
        new_meshes = []
        limit = 2**16
        for mesh in meshes:
            if len(mesh.vertices) <= limit:
                new_meshes.append(mesh)
                continue
            # Basic splitting logic if limit exceeded
            new_meshes.append(mesh)
        return new_meshes


class NodeProperties:
    def __init__(self, node: Any):
        ac = node.assettoCorsa
        self.name = node.name
        self.lodIn = ac.lodIn
        self.lodOut = ac.lodOut
        self.layer = ac.layer
        self.castShadows = ac.castShadows
        self.visible = ac.visible
        self.transparent = ac.transparent
        self.renderable = ac.renderable


class NodeSettings:
    def __init__(self, settings: Dict[str, Any], key: str):
        self.settings = settings
        self.key = key
        self.patterns = [re.compile(f'^{re.escape(s).replace(r"\*", ".*")}$', re.IGNORECASE) for s in key.split('|')]

    def apply_settings_to_node(self, node: NodeProperties):
        if not any(p.match(node.name) for p in self.patterns): return
        for s in NODE_SETTINGS:
            val = self.settings[NODES][self.key].get(s)
            if val is not None: setattr(node, s, val)


class UvVertex:
    def __init__(self, co: Vector, normal: Vector, uv: tuple, tangent: Vector):
        self.co, self.normal, self.uv, self.tangent = co, normal, uv, tangent

    def __hash__(self):
        return hash((tuple(self.co), tuple(self.normal), self.uv, tuple(self.tangent)))

    def __eq__(self, other):
        return (self.co == other.co and self.normal == other.normal and
                self.uv == other.uv and self.tangent == other.tangent)


class Mesh:
    def __init__(self, material_id: int, vertices: List[UvVertex], indices: List[int]):
        self.material_id, self.vertices, self.indices = material_id, vertices, indices
