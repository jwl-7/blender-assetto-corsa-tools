def add_acroot(obj) -> tuple[str, bool]:
    """Add acroot bone as parent of Hips. Returns (message, success)."""
    hips = (
        obj.data.edit_bones.get('mixamorig:Hips') or
        obj.data.edit_bones.get('mixamorig7:Hips') or
        obj.data.edit_bones.get('Hips')
    )

    acroot = obj.data.edit_bones.new('acroot')
    acroot.head = (0, 0, 0)
    acroot.tail = (0, 0.1, 0)

    if hips:
        hips.parent = acroot
        return f'acroot bone added and parented to: {hips.name}', True

    return 'acroot bone added but Hips bone not found.\nPlease parent it manually.', False
