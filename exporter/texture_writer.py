# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2014  Thomas Hagnhofer


import os
from .kn5_writer import KN5Writer
from .exporter_utils import get_all_texture_nodes


DDS_HEADER_BYTES = b"DDS"


class TextureWriter(KN5Writer):
    def __init__(self, file, context, settings, filepath, warnings):
        super().__init__(file)

        self.available_textures = {}
        self.texture_positions = {}
        self.warnings = warnings
        self.context = context
        self.settings = settings
        self.textures_dir = os.path.join(os.path.dirname(os.path.abspath(filepath)), "texture")
        self._fill_available_image_textures()
        self._fill_textures_from_settings()

    def write(self):
        self.write_int(len(self.available_textures))
        for texture_name, _position in sorted(self.texture_positions.items(), key=lambda k: k[1]):
            entry = self.available_textures[texture_name]
            if isinstance(entry, dict):
                self._write_texture_from_disk(texture_name, entry["path"])
            else:
                self._write_texture(entry)

    def _write_texture(self, texture):
        is_active = 1
        self.write_int(is_active)
        self.write_string(texture.image.name)
        image_data = self._get_image_data_from_texture(texture)
        self.write_blob(image_data)

    def _write_texture_from_disk(self, texture_name, path):
        self.write_int(1)
        self.write_string(texture_name)
        with open(path, "rb") as f:
            image_data = f.read()
        self.write_blob(image_data)

    def _fill_available_image_textures(self):
        self.available_textures = {}
        self.texture_positions = {}
        position = 0

        all_texture_nodes = get_all_texture_nodes(self.context)
        for texture_node in all_texture_nodes:
            if texture_node.name.startswith("__"):
                continue
            if not texture_node.image:
                self.warnings.append(f"Ignoring texture node without image '{texture_node.name}'")
                continue
            image_name = texture_node.image.name
            if image_name in self.available_textures:
                continue
            if not texture_node.image.pixels:
                self.warnings.append(f"Ignoring texture node without image data '{texture_node.name}'")
                continue
            self.available_textures[image_name] = texture_node
            self.texture_positions[image_name] = position
            position += 1

    def _fill_textures_from_settings(self):
        if "materials" not in self.settings:
            return
        position = len(self.texture_positions)
        for material_key, material_data in self.settings["materials"].items():
            for slot_name, texture_info in material_data.get("textures", {}).items():
                texture_name = texture_info.get("textureName")
                if not texture_name or texture_name in self.available_textures:
                    continue
                texture_path = os.path.join(self.textures_dir, texture_name)
                if os.path.exists(texture_path):
                    self.available_textures[texture_name] = {"path": texture_path}
                    self.texture_positions[texture_name] = position
                    position += 1
                else:
                    self.warnings.append(f"Texture '{texture_name}' referenced in settings but not found at {texture_path}")

    def _get_image_data_from_texture(self, texture):
        image_copy = texture.image.copy()
        try:
            if image_copy.file_format in ("PNG", "DDS", ""):
                if not image_copy.packed_file:
                    image_copy.pack()
                image_data = image_copy.packed_file.data
                image_header_magic_bytes = image_data[:3]
                if image_copy.file_format != "" or image_header_magic_bytes == DDS_HEADER_BYTES:
                    return image_data
            return self._convert_image_to_png(image_copy)
        finally:
            self.context.blend_data.images.remove(image_copy)

    def _convert_image_to_png(self, image):
        if not image.packed_file:
            image.unpack(method="WRITE_LOCAL")
        image.pack()
        return image.packed_file.data
