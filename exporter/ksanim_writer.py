import bpy
import mathutils
import math
import re
from typing import Any
from .exporter_utils import convert_vector3, convert_quaternion
from .kn5_writer import KN5Writer


MAT_ROTATE_X_180 = mathutils.Matrix.Rotation(math.pi, 4, 'X')
MAT_ROTATE_X_90 = mathutils.Matrix.Rotation(-math.pi / 2, 4, 'X')


class KSAnimWriter(KN5Writer):
    """Writer for AC Anim (.ksanim) files."""

    def __init__(
        self,
        file: Any,
        context: bpy.types.Context,
        filepath: str,
        selection_type: str,
        reverse_animation: bool,
        warnings: list[str]
    ):
        super().__init__(file)
        self.context: bpy.types.Context = context
        self.filepath: str = filepath
        self.selection_type: str = selection_type
        self.reverse_animation: bool = reverse_animation
        self.warnings: list[str] = warnings
        self.objects: dict[str, dict[str, Any]] = {}
        self.draw_order: list[str] = []

    def _add_obj(self, obj: bpy.types.Object | bpy.types.PoseBone):
        name = obj.name
        self.objects[name] = {'name': name, 'frames': []}
        self.draw_order.append(name)

    def _add_frame(self, obj: bpy.types.Object):
        if obj.rotation_mode == 'QUATERNION':
            rotation = list(obj.rotation_quaternion)
        else:
            rotation = list(obj.matrix_parent_inverse.to_quaternion() @ obj.rotation_euler.to_quaternion())

        rotation = rotation[1:4] + rotation[0:1]

        if obj.parent:
            p = list(obj.matrix_parent_inverse @ obj.location)
            position = p
        else:
            p = list(obj.location)
            position = [p[0], p[2], -p[1]]

        scale = list(obj.scale)
        self.objects[obj.name]['frames'].append(rotation + position + scale)

    def _add_bone_frame(self, obj: bpy.types.PoseBone):
        rotation = obj.matrix.copy()
        rotation = rotation @ MAT_ROTATE_X_180
        rotation = rotation.to_quaternion()

        if obj.parent:
            pmat = obj.parent.matrix @ MAT_ROTATE_X_180
            pmat = pmat.inverted()
            p = list(pmat @ obj.head)
            prot = pmat.to_quaternion()
            rotation = list(prot @ rotation)
        else:
            p = list(obj.head)

        rotation = list(rotation[1:4] + rotation[0:1])
        position = p
        scale = list(obj.scale)

        self.objects[obj.name]['frames'].append(rotation + position + scale)

    def write(self):
        scene: bpy.types.Scene = self.context.scene
        layer: bpy.types.ViewLayer = self.context.view_layer
        context_objects: list[bpy.types.Object] = []
        context_bones: list[bpy.types.PoseBone] = []

        if self.selection_type == 'use_pose_bones':
            context_bones = list(self.context.selected_pose_bones) if self.context.selected_pose_bones else []
        elif self.selection_type == 'use_selection':
            context_objects = list(self.context.selected_objects)
        else:
            context_objects = list(layer.objects)

        for obj in context_objects:
            if obj.type == 'ARMATURE' and obj.pose:
                for bone in obj.pose.bones:
                    self._add_obj(bone)
            else:
                self._add_obj(obj)

        for bone in context_bones:
            self._add_obj(bone)

        original_actions: dict[bpy.types.Object, bpy.types.Action | None] = {}
        for obj in context_objects:
            if obj.type == 'ARMATURE':
                if not obj.animation_data:
                    obj.animation_data_create()
                original_actions[obj] = obj.animation_data.action
                for action in bpy.data.actions:
                    obj.animation_data.action = action

        frame_start: int = scene.frame_start
        frame_end: int = scene.frame_end
        for action in bpy.data.actions:
            if action.frame_range[1] > 0:
                frame_start, frame_end = int(action.frame_range[0]), int(action.frame_range[1])
                break

        rnge: range = range(frame_end, frame_start - 1, -1) if self.reverse_animation else range(frame_start, frame_end + 1)

        for f in rnge:
            scene.frame_set(f)
            layer.update()
            for obj in context_objects:
                if obj.type == 'ARMATURE' and obj.pose:
                    for bone in obj.pose.bones:
                        self._add_bone_frame(bone)
                else:
                    self._add_frame(obj)
            for bone in context_bones:
                self._add_bone_frame(bone)

        for obj, action in original_actions.items():
            obj.animation_data.action = action

        self.write_uint(2)
        self.write_uint(len(self.objects))
        for o in self.draw_order:
            obj_data: dict[str, Any] = self.objects[o]
            self.write_string(obj_data['name'])
            self.write_uint(len(obj_data['frames']))
            for frame in obj_data['frames']:
                self.write_list(frame)


class KNHWriter(KN5Writer):
    """Writer for AC 3D Pose (.knh) files."""

    def __init__(
        self,
        file: Any,
        context: bpy.types.Context,
        filepath: str,
        selection_type: str,
        warnings: list[str]
    ):
        super().__init__(file)
        self.context: bpy.types.Context = context
        self.filepath: str = filepath
        self.selection_type: str = selection_type
        self.warnings: list[str] = warnings

    def write(self):
        objs: list[bpy.types.Object] = list(self.context.selected_objects) if self.selection_type == 'use_selection' else list(self.context.view_layer.objects)
        for o in objs:
            if not o.parent:
                self._write_recursive_knh_obj(o)

    def _write_recursive_knh_obj(self, obj: bpy.types.Object):
        self.write_string(obj.name)

        if obj.parent:
            mat = obj.matrix_local.transposed()
        else:
            mat = (obj.matrix_local @ MAT_ROTATE_X_90).transposed()

        self.write_matrix(mat)
        children = list(obj.children)

        if obj.type == 'ARMATURE' and obj.pose:
            rootbones: list[bpy.types.PoseBone] = [b for b in obj.pose.bones if not b.parent]
            self.write_uint(len(rootbones) + len(children))
            for b in rootbones:
                self._write_recursive_knh_bone(b)
        else:
            self.write_uint(len(children))

        for o in children:
            self._write_recursive_knh_obj(o)

    def _write_recursive_knh_bone(self, bone: bpy.types.PoseBone):
        self.write_string(bone.name)

        bmat = bone.matrix @ MAT_ROTATE_X_180
        if bone.parent:
            pmat = bone.parent.matrix @ MAT_ROTATE_X_180
            mat = (pmat.inverted() @ bmat).transposed()
        else:
            mat = bmat.transposed()

        self.write_matrix(mat)
        bone_children = list(bone.children)
        self.write_uint(len(bone_children))

        for b in bone_children:
            self._write_recursive_knh_bone(b)
