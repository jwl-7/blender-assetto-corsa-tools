import bpy
import mathutils, math
from .exporter_utils import convert_vector3, convert_quaternion
from .kn5_writer import KN5Writer

negabones = [
    'DRIVER_RIG_Leg_L', 'DRIVER_RIG_Shin_L', 'DRIVER_RIG_Hill_L',
    'DRIVER_RIG_Leg_R', 'DRIVER_RIG_Shin_R', 'DRIVER_RIG_Hill_R',
    'DRIVER_RIG_Arm_L', 'DRIVER_RIG_Shoulder_L', 'DRIVER_RIG_ForeArm_L',
    'DRIVER_RIG_Arm_R', 'DRIVER_RIG_Shoulder_R', 'DRIVER_RIG_ForeArm_R',
    'DRIVER_RIG_ForeArm_END_L', 'DRIVER_HAND_L_Thumb1', 'DRIVER_HAND_L_Thumb2',
    'DRIVER_RIG_ForeArm_END_R', 'DRIVER_HAND_R_Thumb1', 'DRIVER_HAND_R_Thumb2',
    'DRIVER_HAND_Index1', 'DRIVER_HAND_Index2',
    'DRIVER_HAND_Middle1', 'DRIVER_HAND_Middle2',
    'DRIVER_HAND_Ring1', 'DRIVER_HAND_Ring2',
    'DRIVER_HAND_Pinkie1', 'DRIVER_HAND_Pinkie2',
    'DRIVER_HAND_Index4', 'DRIVER_HAND_Index5',
    'DRIVER_HAND_Middle4', 'DRIVER_HAND_Middle5',
    'DRIVER_HAND_Ring4', 'DRIVER_HAND_Ring5',
    'DRIVER_HAND_Pinkie4', 'DRIVER_HAND_Pinkie5'
]

halfrotmat = mathutils.Matrix.Rotation(math.pi, 4, 'X')

class KSAnimWriter(KN5Writer):
    def __init__(self, file, context, filepath, selection_type, reverse_animation, add_colons, warnings):
        super().__init__(file)
        self.context = context
        self.filepath = filepath
        self.selection_type = selection_type
        self.reverse_animation = reverse_animation
        self.add_colons = add_colons
        self.warnings = warnings
        self.objects = {}
        self.draw_order = []

    def _add_obj(self, obj):
        name = obj.name
        if self.add_colons and name.startswith("DRIVER_"):
            name = "DRIVER:" + name[7:]
        self.objects[obj.name] = {"name": name, "frames": []}
        self.draw_order.append(obj.name)

    def _add_frame(self, obj):
        co, rot, scale = obj.matrix_local.decompose()
        rotation = list(convert_quaternion(rot))[1:4] + list(convert_quaternion(rot))[0:1]
        position = list(convert_vector3(co))
        self.objects[obj.name]["frames"].append(rotation + position + [scale[0], scale[2], scale[1]])

    def _add_bone_frame(self, obj):
        mat = obj.matrix @ halfrotmat if obj.name in negabones else obj.matrix
        if obj.parent:
            pmat = obj.parent.matrix @ halfrotmat if obj.parent.name in negabones else obj.parent.matrix
            local_mat = pmat.inverted() @ mat
        else:
            local_mat = mat
        co, rot, scale = local_mat.decompose()
        rotation = list(convert_quaternion(rot))[1:4] + list(convert_quaternion(rot))[0:1]
        position = list(convert_vector3(co))
        self.objects[obj.name]["frames"].append(rotation + position + [scale[0], scale[2], scale[1]])

    def write(self):
        scene = self.context.scene
        layer = self.context.view_layer
        context_objects, context_bones = [], []

        if self.selection_type == "use_pose_bones":
            context_bones = self.context.selected_pose_bones or []
        elif self.selection_type == "use_selection":
            context_objects = self.context.selected_objects
        else:
            context_objects = self.context.view_layer.objects

        for obj in context_objects:
            if obj.type == "ARMATURE":
                for bone in obj.pose.bones: self._add_obj(bone)
            else: self._add_obj(obj)
        for bone in context_bones: self._add_obj(bone)

        original_actions = {}
        for obj in context_objects:
            if obj.type == "ARMATURE":
                if not obj.animation_data: obj.animation_data_create()
                original_actions[obj] = obj.animation_data.action
                for action in bpy.data.actions: obj.animation_data.action = action

        frame_start, frame_end = scene.frame_start, scene.frame_end
        for action in bpy.data.actions:
            if action.frame_range[1] > 0:
                frame_start, frame_end = int(action.frame_range[0]), int(action.frame_range[1])
                break

        rnge = range(frame_end, frame_start - 1, -1) if self.reverse_animation else range(frame_start, frame_end + 1)
        for f in rnge:
            scene.frame_set(f)
            layer.update()
            for obj in context_objects:
                if obj.type == "ARMATURE":
                    for bone in obj.pose.bones: self._add_bone_frame(bone)
                else: self._add_frame(obj)
            for bone in context_bones: self._add_bone_frame(bone)

        for obj, action in original_actions.items(): obj.animation_data.action = action

        self.write_uint(2)
        self.write_uint(len(self.objects))
        for o in self.draw_order:
            obj_data = self.objects[o]
            self.write_string(obj_data["name"])
            self.write_uint(len(obj_data["frames"]))
            for frame in obj_data["frames"]: self.write_list(frame)

class KNHWriter(KN5Writer):
    def __init__(self, file, context, filepath, selection_type, add_colons, warnings):
        super().__init__(file)
        self.context, self.filepath, self.selection_type = context, filepath, selection_type
        self.add_colons, self.warnings = add_colons, warnings

    def write(self):
        objs = self.context.selected_objects if self.selection_type == "use_selection" else self.context.view_layer.objects
        for o in objs:
            if not o.parent: self._write_recursive_knh_obj(o)

    def _write_recursive_knh_obj(self, obj):
        name = "DRIVER:" + obj.name[7:] if self.add_colons and obj.name.startswith("DRIVER_") else obj.name
        self.write_string(name)
        self.write_matrix(obj.matrix_local if obj.parent else (obj.matrix_local @ mathutils.Matrix.Rotation(-math.pi/2, 4, 'X')))

        children = obj.children
        if obj.type == "ARMATURE":
            rootbones = [b for b in obj.pose.bones if not b.parent]
            self.write_uint(len(rootbones) + len(children))
            for b in rootbones: self._write_recursive_knh_bone(b)
        else:
            self.write_uint(len(children))
        for o in children: self._write_recursive_knh_obj(o)

    def _write_recursive_knh_bone(self, bone):
        name = "DRIVER:" + bone.name[7:] if self.add_colons and bone.name.startswith("DRIVER_") else bone.name
        self.write_string(name)
        mat = bone.matrix @ halfrotmat if bone.name in negabones else bone.matrix
        if bone.parent:
            pmat = bone.parent.matrix @ halfrotmat if bone.parent.name in negabones else bone.parent.matrix
            self.write_matrix(pmat.inverted() @ mat)
        else:
            self.write_matrix(mat)
        self.write_uint(len(bone.children))
        for b in bone.children: self._write_recursive_knh_bone(b)
