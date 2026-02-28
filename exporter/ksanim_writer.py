import bpy
import mathutils
import math
import re
from typing import Dict, List, Set, Any, Optional, Union, Tuple
from .exporter_utils import convert_vector3, convert_quaternion
from .kn5_writer import KN5Writer


NEGABONES: Set[str] = {
    # ks driver
    'DRIVER_RIG_Leg_L',
    'DRIVER_RIG_Shin_L',
    'DRIVER_RIG_Hill_L',
    'DRIVER_RIG_Leg_R',
    'DRIVER_RIG_Shin_R',
    'DRIVER_RIG_Hill_R',
    'DRIVER_RIG_Arm_L',
    'DRIVER_RIG_Shoulder_L',
    'DRIVER_RIG_ForeArm_L',
    'DRIVER_RIG_Arm_R',
    'DRIVER_RIG_Shoulder_R',
    'DRIVER_RIG_ForeArm_R',
    'DRIVER_RIG_ForeArm_END_L',
    'DRIVER_RIG_ForeArm_END_R',
    'DRIVER_HAND_L_Thumb1',
    'DRIVER_HAND_L_Thumb2',
    'DRIVER_HAND_R_Thumb1',
    'DRIVER_HAND_R_Thumb2',
    'DRIVER_HAND_Index1',
    'DRIVER_HAND_Index2',
    'DRIVER_HAND_Middle1',
    'DRIVER_HAND_Middle2',
    'DRIVER_HAND_Ring1',
    'DRIVER_HAND_Ring2',
    'DRIVER_HAND_Pinkie1',
    'DRIVER_HAND_Pinkie2',
    'DRIVER_HAND_Index4',
    'DRIVER_HAND_Index5',
    'DRIVER_HAND_Middle4',
    'DRIVER_HAND_Middle5',
    'DRIVER_HAND_Ring4',
    'DRIVER_HAND_Ring5',
    'DRIVER_HAND_Pinkie4',
    'DRIVER_HAND_Pinkie5',

    # mixamo
    'mixamorig:LeftUpLeg',
    'mixamorig:LeftLeg',
    'mixamorig:LeftFoot',
    'mixamorig:RightUpLeg',
    'mixamorig:RightLeg',
    'mixamorig:RightFoot',
    'mixamorig:LeftArm',
    'mixamorig:LeftShoulder',
    'mixamorig:LeftForeArm',
    'mixamorig:RightArm',
    'mixamorig:RightShoulder',
    'mixamorig:RightForeArm',
    'mixamorig:LeftHand',
    'mixamorig:RightHand'
}

# 180-degree flip matrix
HALF_ROT_MAT: mathutils.Matrix = mathutils.Matrix.Rotation(math.pi, 4, 'X')


class KSAnimWriter(KN5Writer):
    """Writer for AC Anim (.ksanim) files."""

    def __init__(
        self,
        file: Any,
        context: bpy.types.Context,
        filepath: str,
        selection_type: str,
        reverse_animation: bool,
        add_colons: bool,
        warnings: List[str]
    ):
        super().__init__(file)
        self.context: bpy.types.Context = context
        self.filepath: str = filepath
        self.selection_type: str = selection_type
        self.reverse_animation: bool = reverse_animation
        self.add_colons: bool = add_colons
        self.warnings: List[str] = warnings
        self.objects: Dict[str, Dict[str, Any]] = {}
        self.draw_order: List[str] = []

    def _add_obj(self, obj: Union[bpy.types.Object, bpy.types.PoseBone]) -> None:
        name: str = obj.name
        if self.add_colons and name.startswith('DRIVER_'):
            name = 'DRIVER:' + name[7:]
        self.objects[obj.name] = {'name': name, 'frames': []}
        self.draw_order.append(obj.name)

    def _add_frame(self, obj: bpy.types.Object) -> None:
        co: mathutils.Vector
        rot: mathutils.Quaternion
        scale: mathutils.Vector
        co, rot, scale = obj.matrix_local.decompose()

        rotation: List[float] = list(convert_quaternion(rot))[1:4] + list(convert_quaternion(rot))[0:1]
        position: List[float] = list(convert_vector3(co))
        self.objects[obj.name]['frames'].append(rotation + position + [scale[0], scale[2], scale[1]])

    def _add_bone_frame(self, obj: bpy.types.PoseBone) -> None:
        mat: mathutils.Matrix = obj.matrix @ HALF_ROT_MAT if self.is_negabone(obj.name) else obj.matrix
        if obj.parent:
            pmat: mathutils.Matrix = obj.parent.matrix @ HALF_ROT_MAT if self.is_negabone(obj.parent.name) else obj.parent.matrix
            local_mat: mathutils.Matrix = pmat.inverted() @ mat
        else:
            local_mat = mat

        co: mathutils.Vector
        rot: mathutils.Quaternion
        scale: mathutils.Vector
        co, rot, scale = local_mat.decompose()

        rotation: List[float] = list(convert_quaternion(rot))[1:4] + list(convert_quaternion(rot))[0:1]
        position: List[float] = list(convert_vector3(co))
        self.objects[obj.name]['frames'].append(rotation + position + [scale[0], scale[2], scale[1]])

    def is_negabone(self, name: str) -> bool:
        """Checks if bone needs orientation fix."""
        if name in NEGABONES:
            return True

        # check for mixamorig + any number affix that may follow | ex: mixamorig7
        if name.startswith('mixamorig'):
            normalized_name: str = re.sub(r'mixamorig\d*:', 'mixamorig:', name)
            return normalized_name in NEGABONES

        return False

    def write(self) -> None:
        scene: bpy.types.Scene = self.context.scene
        layer: bpy.types.ViewLayer = self.context.view_layer
        context_objects: List[bpy.types.Object] = []
        context_bones: List[bpy.types.PoseBone] = []

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

        original_actions: Dict[bpy.types.Object, Optional[bpy.types.Action]] = {}
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
            obj_data: Dict[str, Any] = self.objects[o]
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
        add_colons: bool,
        warnings: List[str]
    ):
        super().__init__(file)
        self.context: bpy.types.Context = context
        self.filepath: str = filepath
        self.selection_type: str = selection_type
        self.add_colons: bool = add_colons
        self.warnings: List[str] = warnings

    def is_negabone(self, name: str) -> bool:
        """Checks if bone needs orientation fix."""
        if name in NEGABONES:
            return True

        # check for mixamorig + any number affix that may follow | ex: mixamorig7
        if name.startswith('mixamorig'):
            normalized_name: str = re.sub(r'mixamorig\d*:', 'mixamorig:', name)
            return normalized_name in NEGABONES

        return False

    def write(self) -> None:
        objs: List[bpy.types.Object] = list(self.context.selected_objects) if self.selection_type == 'use_selection' else list(self.context.view_layer.objects)
        for o in objs:
            if not o.parent:
                self._write_recursive_knh_obj(o)

    def _write_recursive_knh_obj(self, obj: bpy.types.Object) -> None:
        name: str = 'DRIVER:' + obj.name[7:] if self.add_colons and obj.name.startswith('DRIVER_') else obj.name
        self.write_string(name)

        mat: mathutils.Matrix = obj.matrix_local if obj.parent else (obj.matrix_local @ mathutils.Matrix.Rotation(-math.pi/2, 4, 'X'))
        self.write_matrix(mat)

        children: List[bpy.types.Object] = list(obj.children)
        if obj.type == 'ARMATURE' and obj.pose:
            rootbones: List[bpy.types.PoseBone] = [b for b in obj.pose.bones if not b.parent]
            self.write_uint(len(rootbones) + len(children))
            for b in rootbones:
                self._write_recursive_knh_bone(b)
        else:
            self.write_uint(len(children))

        for o in children:
            self._write_recursive_knh_obj(o)

    def _write_recursive_knh_bone(self, bone: bpy.types.PoseBone) -> None:
        name: str = 'DRIVER:' + bone.name[7:] if self.add_colons and bone.name.startswith('DRIVER_') else bone.name
        self.write_string(name)

        mat: mathutils.Matrix = bone.matrix @ HALF_ROT_MAT if self.is_negabone(bone.name) else bone.matrix
        if bone.parent:
            pmat: mathutils.Matrix = bone.parent.matrix @ HALF_ROT_MAT if self.is_negabone(bone.parent.name) else bone.parent.matrix
            self.write_matrix(pmat.inverted() @ mat)
        else:
            self.write_matrix(mat)

        bone_children: List[bpy.types.PoseBone] = list(bone.children)
        self.write_uint(len(bone_children))
        for b in bone_children:
            self._write_recursive_knh_bone(b)
