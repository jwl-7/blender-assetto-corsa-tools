import bpy
from math import radians
from typing import Any


def add_armature_rotation(context: Any) -> tuple[bool, str]:
    """Corrects armature orientation using the rotation 'sandwich' method."""
    obj = context.active_object

    if not obj or obj.type != 'ARMATURE':
        return False, 'No armature found or selected.'

    if context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    context.view_layer.objects.active = obj

    obj.rotation_euler[0] -= radians(90)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    obj.rotation_euler[0] += radians(90)

    return True, 'Added 90° rotation to armature.'