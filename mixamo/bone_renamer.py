def rename_bones(obj, find: str, replace: str) -> str:
    """Renames rig bones from find to replace."""
    total = 0

    for bone in obj.data.bones:
        if find in bone.name:
            bone.name = bone.name.replace(find, replace)
            total += 1

    return f'Renamed {total} bones.\n{find} -> {replace}'
