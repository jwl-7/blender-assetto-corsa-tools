import os
from typing import Any, Dict, List
import bpy
from .kn5_writer import KN5Writer
from .exporter_utils import get_all_texture_nodes


DDS_HEADER_BYTES: bytes = b'DDS'


class TextureWriter(KN5Writer):
    def __init__(
        self,
        file: Any,
        context: bpy.types.Context,
        settings: Dict[str, Any],
        filepath: str,
        warnings: List[str]
    ):
        super().__init__(file)

        self.available_textures: Dict[str, Any] = {}
        self.texture_positions: Dict[str, int] = {}
        self.warnings: List[str] = warnings
        self.context: bpy.types.Context = context
        self.settings: Dict[str, Any] = settings
        self.textures_dir: str = os.path.join(os.path.dirname(os.path.abspath(filepath)), 'texture')
        self._fill_available_image_textures()
        self._fill_textures_from_settings()

    def write(self):
        """Writes all available textures to the KN5 file."""
        self.write_int(len(self.available_textures))
        for texture_name, _position in sorted(self.texture_positions.items(), key=lambda k: k[1]):
            entry: Any = self.available_textures[texture_name]
            if isinstance(entry, dict):
                self._write_texture_from_disk(texture_name, entry['path'])
            else:
                self._write_texture(entry)

    def _write_texture(self, texture: bpy.types.ShaderNodeTexImage):
        """Writes a texture node directly from the Blender data."""
        is_active: int = 1
        self.write_int(is_active)
        self.write_string(texture.image.name)
        image_data: bytes = self._get_image_data_from_texture(texture)
        self.write_blob(image_data)

    def _write_texture_from_disk(self, texture_name: str, path: str):
        """Writes a texture file read from the disk."""
        self.write_int(1)
        self.write_string(texture_name)
        with open(path, 'rb') as f:
            image_data: bytes = f.read()
        self.write_blob(image_data)

    def _fill_available_image_textures(self):
        """Scans the scene for used texture nodes."""
        self.available_textures = {}
        self.texture_positions = {}
        position: int = 0

        all_texture_nodes: List[bpy.types.ShaderNodeTexImage] = get_all_texture_nodes(self.context)
        for texture_node in all_texture_nodes:
            if texture_node.name.startswith('__'):
                continue
            if not texture_node.image:
                self.warnings.append(f"Ignoring texture node without image '{texture_node.name}'")
                continue
            image_name: str = texture_node.image.name
            if image_name in self.available_textures:
                continue
            if not texture_node.image.pixels:
                self.warnings.append(f"Ignoring texture node without image data '{texture_node.name}'")
                continue
            self.available_textures[image_name] = texture_node
            self.texture_positions[image_name] = position
            position += 1

    def _fill_textures_from_settings(self):
        """Loads additional textures defined in the settings.json."""
        if 'materials' not in self.settings:
            return
        position: int = len(self.texture_positions)
        for material_key, material_data in self.settings['materials'].items():
            for slot_name, texture_info in material_data.get('textures', {}).items():
                texture_name: str = texture_info.get('textureName')
                if not texture_name or texture_name in self.available_textures:
                    continue
                texture_path: str = os.path.join(self.textures_dir, texture_name)
                if os.path.exists(texture_path):
                    self.available_textures[texture_name] = {'path': texture_path}
                    self.texture_positions[texture_name] = position
                    position += 1
                else:
                    self.warnings.append(f"Texture '{texture_name}' referenced in settings but not found at {texture_path}")

    def _get_image_data_from_texture(self, texture: bpy.types.ShaderNodeTexImage) -> bytes:
        """Retrieves raw image bytes, converting to PNG if necessary."""
        image_copy: bpy.types.Image = texture.image.copy()
        try:
            if image_copy.file_format in ('PNG', 'DDS', ''):
                if not image_copy.packed_file:
                    image_copy.pack()
                image_data: bytes = image_copy.packed_file.data
                image_header_magic_bytes: bytes = image_data[:3]
                if image_copy.file_format != '' or image_header_magic_bytes == DDS_HEADER_BYTES:
                    return image_data
            return self._convert_image_to_png(image_copy)
        finally:
            self.context.blend_data.images.remove(image_copy)

    def _convert_image_to_png(self, image: bpy.types.Image) -> bytes:
        """Forces a Blender image into a PNG byte stream."""
        if not image.packed_file:
            image.unpack(method='WRITE_LOCAL')
        image.pack()
        return image.packed_file.data
