import bpy
from typing import Any

obj = bpy.context.object

def fix_scale(obj: Any) -> str:
    """Fixes mixamo scale from 0.010 -> 1.000 with moving character mesh around during the animation."""
    if obj and obj.animation_data and obj.animation_data.action:
        # initial scale
        action = obj.animation_data.action
        initial_scale = obj.scale.copy()

        # apply transforms
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        scaled_count = 0

        # scale
        for layer in getattr(action, 'layers', []):
            for strip in getattr(layer, 'strips', []):
                for bag in getattr(strip, 'channelbags', []):
                    for fc in getattr(bag, 'fcurves', []):
                        if 'location' in fc.data_path:
                            axis = fc.array_index
                            factor = initial_scale[axis]
                            for kp in fc.keyframe_points:
                                kp.co[1] *= factor
                                kp.handle_left[1] *= factor
                                kp.handle_right[1] *= factor
                                scaled_count += 1

        msg = f'Scaled {scaled_count} location keyframes for {obj.name}.'
    else:
        msg = 'Ensure an animated armature is selected.'

    return msg
