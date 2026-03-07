import bpy


def rename_anim_bones(find: str, replace: str) -> str:
    """Rename fcurve data paths across all actions."""
    total = 0

    for action in bpy.data.actions:
        fcurves = []

        if hasattr(action, 'fcurves'):
            fcurves.extend(action.fcurves)

        if hasattr(action, 'layers'):
            for layer in action.layers:
                for strip in layer.strips:
                    if hasattr(strip, 'channelbags'):
                        for bag in strip.channelbags:
                            fcurves.extend(bag.fcurves)

        for fc in fcurves:
            if find in fc.data_path:
                fc.data_path = fc.data_path.replace(find, replace)
                total += 1

    return f'Renamed {total} fcurve paths.\n{find} -> {replace}'
