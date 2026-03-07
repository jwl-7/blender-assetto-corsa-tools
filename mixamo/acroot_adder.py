def add_acroot(obj) -> tuple[str, bool]:
    """Add acroot bone as parent of Hips."""
    root = next((b for b in obj.data.edit_bones if b.parent is None), None)

    acroot = obj.data.edit_bones.new('acroot')
    acroot.head = (0, 0, 0)
    acroot.tail = (0, 0.1, 0)

    if root:
        root.parent = acroot
        return f'acroot bone added and parented to: {root.name}', True

    return 'acroot bone added but no root bone found.\nPlease parent it manually.', False
