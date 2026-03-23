"""Builds a mesh -> material -> texture report from the current Blender scene."""

import bpy


def get_textures_from_material(mat: bpy.types.Material) -> list[tuple[str, str, str]]:
    """Returns a list of (shader_input_name, image_name, filepath) tuples from a material."""
    results = []
    if mat is None or not mat.use_nodes:
        return results
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            shader_input = getattr(node, 'assettoCorsa', None)
            slot_name = shader_input.shaderInputName if shader_input else (node.label or node.name)
            filepath = node.image.filepath if node.image.filepath else '(packed)'
            results.append((slot_name, node.image.name, filepath))
    return results


def build_report() -> str:
    """Generates a full mesh -> material -> texture report string."""
    lines = []
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']

    if not mesh_objects:
        return 'No mesh objects found in scene.'

    for obj in mesh_objects:
        lines.append(f'MESH: {obj.name}')

        if not obj.material_slots:
            lines.append('  (no materials)')
            lines.append('')
            continue

        for slot_idx, slot in enumerate(obj.material_slots):
            mat = slot.material
            if mat is None:
                lines.append(f'  Slot {slot_idx}: (empty)')
                continue

            lines.append(f'  Slot {slot_idx}: {mat.name}')
            textures = get_textures_from_material(mat)

            if not textures:
                lines.append('    No image textures found')
            else:
                for slot_name, img_name, filepath in textures:
                    lines.append(f'    [{slot_name}]  {img_name}  ->  {filepath}')

        lines.append('')

    lines.append('─' * 60)
    lines.append('All unique images in scene:')
    for img in bpy.data.images:
        fp = img.filepath if img.filepath else '(packed)'
        lines.append(f'  {img.name}  ->  {fp}')

    return '\n'.join(lines)
