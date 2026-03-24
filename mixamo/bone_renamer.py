import bpy
from typing import Any

def rename_rig_bones(obj: Any, find: str, replace: str) -> str:
    """Renames rig bones.."""
    total = 0

    for bone in obj.data.bones:
        if find in bone.name:
            bone.name = bone.name.replace(find, replace)
            total += 1

    return f'Bones: {total}'

def rename_anim_bones(obj: Any, find: str, replace: str) -> str:
    """Renames animation/action references."""
    if not (obj.animation_data and obj.animation_data.action):
        return 'Animation: None'

    act = obj.animation_data.action
    g_total = 0
    f_total = 0

    for layer in act.layers:
        for strip in layer.strips:
            if hasattr(strip, 'channelbags'):
                for bag in strip.channelbags:
                    if hasattr(bag, 'groups'):
                        for grp in bag.groups:
                            if find in grp.name:
                                grp.name = grp.name.replace(find, replace)
                                g_total += 1
                    if hasattr(bag, 'fcurves'):
                        for fc in bag.fcurves:
                            if find in fc.data_path:
                                fc.data_path = fc.data_path.replace(find, replace)
                                f_total += 1

    return f'Action: {act.name}\nGroups: {g_total}\nF-Curves: {f_total}'

def rename_bones(obj: Any, find: str, replace: str) -> str:
    """Master function to rename bones and update animation data."""
    bone_report = rename_rig_bones(obj, find, replace)
    anim_report = rename_anim_bones(obj, find, replace)

    bpy.context.view_layer.update()

    return f'Changed: {find} -> {replace}\n{bone_report}\n{anim_report}'
