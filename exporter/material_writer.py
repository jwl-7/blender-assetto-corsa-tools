import numbers
import os
import re
import bpy
from typing import Any
from .exporter_utils import get_texture_nodes
from .kn5_writer import KN5Writer


MATERIAL_BLEND_MODE: dict[str, int] = {
    'Opaque': 0,
    'AlphaBlend': 1,
    'AlphaToCoverage': 2,
}

MATERIAL_DEPTH_MODE: dict[str, int] = {
    'DepthNormal': 0,
    'DepthNoWrite': 1,
    'DepthOff': 2,
}

AC_TEXTURE_SLOT_ID: dict[str, int] = {
    'txDiffuse': 0,
    'txNormal': 1,
    'txMaps': 2,
    'txDetail': 3,
    'txDetailNM': 4,
    'txEmissive': 5,
    'txEnvironment': 6,
}

MATERIALS: str = 'materials'
PROPERTIES: str = 'properties'
TEXTURES: str = 'textures'


class MaterialWriter(KN5Writer):
    def __init__(
        self,
        file: Any,
        context: bpy.types.Context,
        settings: dict[str, Any],
        warnings: list[str]
    ):
        super().__init__(file)

        self.available_materials: dict[str, MaterialProperties] = {}
        self.material_positions: dict[str, int] = {}
        self.material_settings: list[MaterialSettings] = []
        self.context: bpy.types.Context = context
        self.settings: dict[str, Any] = settings
        self.warnings: list[str] = warnings
        self._fill_available_materials()

    def write(self):
        """Writes all materials to the binary file."""
        self.write_int(len(self.available_materials))
        for material_name, _position in sorted(self.material_positions.items(), key=lambda k: k[1]):
            material = self.available_materials[material_name]
            self._write_material(material)

    def _write_material(self, material: 'MaterialProperties'):
        """Binary write for a single material."""
        self.write_string(material.name)
        self.write_string(material.shaderName)
        self.write_byte(material.alphaBlendMode)
        self.write_bool(material.alphaTested)
        self.write_int(material.depthMode)
        self.write_uint(len(material.shaderProperties))
        for property_name in material.shaderProperties:
            self._write_material_property(material.shaderProperties[property_name])
        self.write_uint(len(material.texture_mapping))
        fallback_slot: int = len(AC_TEXTURE_SLOT_ID)
        for mapping_name in material.texture_mapping:
            slot_id: int = AC_TEXTURE_SLOT_ID.get(mapping_name, fallback_slot)
            if mapping_name not in AC_TEXTURE_SLOT_ID:
                fallback_slot += 1
            self.write_string(mapping_name)
            self.write_uint(slot_id)
            self.write_string(material.texture_mapping[mapping_name])

    def _write_material_property(self, prop: 'ShaderProperty'):
        """Writes a shader property to binary."""
        self.write_string(prop.name)
        self.write_float(prop.valueA)
        self.write_vector2(prop.valueB)
        self.write_vector3(prop.valueC)
        self.write_vector4(prop.valueD)

    def _fill_available_materials(self):
        """Builds the dictionary of materials to be exported."""
        self.available_materials = {}
        self.material_positions = {}
        self.material_settings = []
        if MATERIALS in self.settings:
            for material_key in self.settings[MATERIALS]:
                self.material_settings.append(MaterialSettings(self.settings, self.warnings, material_key))
        position: int = 0
        for material in self.context.blend_data.materials:
            if material.users == 0:
                self.warnings.append(f"Ignoring unused material '{material.name}'")
            elif not material.name.startswith('__'):
                material_properties = MaterialProperties(material)
                for setting in self.material_settings:
                    setting.apply_settings_to_material(material_properties)
                if not material_properties.texture_mapping:
                    warning_message: str = f"No active texture for material '{material.name}' found.{os.linesep}"
                    warning_message += '\tUsing default UV scaling for objects without UV maps.'
                    self.warnings.append(warning_message)
                self.available_materials[material.name] = material_properties
                self.material_positions[material.name] = position
                position += 1


class ShaderProperty:
    def __init__(self, name: str):
        self.name: str = name
        self.valueA: float = 0.0
        self.valueB: tuple[float, float] = (0.0, 0.0)
        self.valueC: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.valueD: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    def fill(self, prop: Any):
        """Fills property values from a Blender property group."""
        self.valueA = prop.valueA
        self.valueB = prop.valueB
        self.valueC = prop.valueC
        self.valueD = prop.valueD


class MaterialProperties:
    def __init__(self, material: bpy.types.Material):
        self.name: str = material.name
        ac_mat: Any = material.assettoCorsa
        self.shaderName: str = ac_mat.shaderName
        self.alphaBlendMode: int = int(ac_mat.alphaBlendMode)
        self.alphaTested: bool = ac_mat.alphaTested
        self.depthMode: int = int(ac_mat.depthMode)
        self.shaderProperties: dict[str, ShaderProperty] = self.copy_shader_properties(material)
        self.texture_mapping: dict[str, str] = self._generate_texture_mapping(material)

    def copy_shader_properties(self, material: bpy.types.Material) -> dict[str, ShaderProperty]:
        """Copies shader properties from Blender to internal storage."""
        ac_mat: Any = material.assettoCorsa
        properties: dict[str, ShaderProperty] = {}
        for shader_property in ac_mat.shaderProperties:
            new_property = ShaderProperty(shader_property.name)
            new_property.fill(shader_property)
            properties[shader_property.name] = new_property

        if not properties and ac_mat.shaderName == 'ksPerPixel':
            new_property = ShaderProperty('ksDiffuse')
            new_property.valueA = 0.4
            properties[new_property.name] = new_property
            new_property = ShaderProperty('ksAmbient')
            new_property.valueA = 0.4
            properties[new_property.name] = new_property
        return properties

    def _generate_texture_mapping(self, material: bpy.types.Material) -> dict[str, str]:
        """Maps shader input names to image names."""
        mapping: dict[str, str] = {}
        texture_nodes = get_texture_nodes(material)
        for texture_node in texture_nodes:
            if not texture_node.image:
                continue
            if texture_node.image.name.startswith('__'):
                continue
            shader_input: str = texture_node.assettoCorsa.shaderInputName
            if not shader_input or not shader_input.strip():
                continue
            mapping[shader_input] = texture_node.image.name
        return mapping


class MaterialSettings:
    def __init__(
        self,
        settings: dict[str, Any],
        warnings: list[str],
        material_settings_key: str
    ):
        self.settings: dict[str, Any] = settings
        self.warnings: list[str] = warnings
        self.material_settings_key: str = material_settings_key
        self.material_name_matches: list[re.Pattern] = self._convert_to_matches_list(material_settings_key)

    def apply_settings_to_material(self, material: MaterialProperties):
        """Applies JSON settings overrides to a material."""
        if not self._does_material_name_match(material.name):
            return
        shader_name: str | None = self._get_material_shader()
        if shader_name:
            material.shaderName = shader_name

        alpha_blend_mode: int | None = self._get_material_blend_mode()
        if alpha_blend_mode:
            material.alphaBlendMode = alpha_blend_mode
        alpha_tested: bool | None = self._get_material_alpha_tested()
        if alpha_tested:
            material.alphaTested = alpha_tested
        depth_mode: int | None = self._get_material_depth_mode()
        if depth_mode:
            material.depthMode = depth_mode

        property_names: list[str] = self._get_material_property_names()
        if property_names:
            material.shaderProperties.clear()
        for property_name in property_names:
            shader_property: ShaderProperty | None = None
            if property_name in material.shaderProperties:
                shader_property = material.shaderProperties[property_name]
            else:
                shader_property = ShaderProperty(property_name)
                material.shaderProperties[property_name] = shader_property

            value_a: float | None = self._get_material_property_value_a(property_name)
            if value_a:
                shader_property.valueA = value_a
            value_b: Any | None = self._get_material_property_value_b(property_name)
            if value_b:
                shader_property.valueB = value_b
            value_c: Any | None = self._get_material_property_value_c(property_name)
            if value_c:
                shader_property.valueC = value_c
            value_d: Any | None = self._get_material_property_value_d(property_name)
            if value_d:
                shader_property.valueD = value_d

        texture_mapping_names: list[str] = self._get_material_texture_mapping_names()
        if texture_mapping_names:
            material.texture_mapping.clear()
        for texture_mapping_name in texture_mapping_names:
            texture_name: str | None = self._get_material_texture_mapping_name(texture_mapping_name)
            if not texture_name:
                msg: str = f"Ignoring texture mapping '{texture_name}' for material '{material.name}' without texture name"
                self.warnings.append(msg)
            else:
                material.texture_mapping[texture_mapping_name] = texture_name

    def _does_material_name_match(self, material_name: str) -> bool:
        """Checks if the material name matches any defined patterns."""
        for regex in self.material_name_matches:
            if regex.match(material_name):
                return True
        return False

    def _convert_to_matches_list(self, key: str) -> list[re.Pattern]:
        """Converts pipe-separated keys into regex patterns."""
        matches: list[re.Pattern] = []
        for subkey in key.split('|'):
            matches.append(re.compile(f'^{self._escape_match_key(subkey)}$', re.IGNORECASE))
        return matches

    def _escape_match_key(self, key: str) -> str:
        """Escapes keys for regex while preserving wildcards."""
        wildcard_replacement: str = '__WILDCARD__'
        key = key.replace('*', wildcard_replacement)
        key = re.escape(key)
        key = key.replace(wildcard_replacement, '.*')
        return key

    def _get_material_shader(self) -> str | None:
        if 'shaderName' in self.settings[MATERIALS][self.material_settings_key]:
            return self.settings[MATERIALS][self.material_settings_key]['shaderName']
        return None

    def _get_material_blend_mode(self) -> int | None:
        if 'alphaBlendMode' in self.settings[MATERIALS][self.material_settings_key]:
            mode_name: str = self.settings[MATERIALS][self.material_settings_key]['alphaBlendMode']
            return MATERIAL_BLEND_MODE[mode_name]
        return None

    def _get_material_depth_mode(self) -> int | None:
        if 'depthMode' in self.settings[MATERIALS][self.material_settings_key]:
            mode_name: str = self.settings[MATERIALS][self.material_settings_key]['depthMode']
            return MATERIAL_DEPTH_MODE[mode_name]
        return None

    def _get_material_alpha_tested(self) -> bool | None:
        if 'alphaTested' in self.settings[MATERIALS][self.material_settings_key]:
            return self.settings[MATERIALS][self.material_settings_key]['alphaTested']
        return None

    def _get_material_property_names(self) -> list[str]:
        if PROPERTIES in self.settings[MATERIALS][self.material_settings_key]:
            return list(self.settings[MATERIALS][self.material_settings_key][PROPERTIES].keys())
        return []

    def _get_material_property_value(
        self,
        property_name: str,
        value_name: str
    ) -> Any | None:
        """Retrieves a specific property value from settings."""
        if value_name in self.settings[MATERIALS][self.material_settings_key][PROPERTIES][property_name]:
            return self.settings[MATERIALS][self.material_settings_key][PROPERTIES][property_name][value_name]
        return None

    def _get_material_texture_mapping_names(self) -> list[str]:
        if TEXTURES in self.settings[MATERIALS][self.material_settings_key]:
            return list(self.settings[MATERIALS][self.material_settings_key][TEXTURES].keys())
        return []

    def _get_material_texture_mapping_name(self, mapping_name: str) -> str | None:
        if TEXTURES in self.settings[MATERIALS][self.material_settings_key]:
            return self.settings[MATERIALS][self.material_settings_key][TEXTURES][mapping_name]['textureName']
        return None

    def _get_material_property_value_a(self, property_name: str) -> float | None:
        value_a = self._get_material_property_value(property_name, 'valueA')
        if value_a is None:
            return None
        if not isinstance(value_a, numbers.Number):
            raise Exception('valueA must be a float')
        return float(value_a)

    def _get_material_property_value_b(self, property_name: str) -> Any | None:
        value_b = self._get_material_property_value(property_name, 'valueB')
        if value_b is None:
            return None
        if not self._is_list_of_numbers_valid(value_b, 2):
            raise Exception('valueB must be a list of two floats')
        return value_b

    def _get_material_property_value_c(self, property_name: str) -> Any | None:
        value_c = self._get_material_property_value(property_name, 'valueC')
        if value_c is None:
            return None
        if not self._is_list_of_numbers_valid(value_c, 3):
            raise Exception('valueC must be a list of three floats')
        return value_c

    def _get_material_property_value_d(self, property_name: str) -> Any | None:
        value_d = self._get_material_property_value(property_name, 'valueD')
        if value_d is None:
            return None
        if not self._is_list_of_numbers_valid(value_d, 4):
            raise Exception('valueD must be a list of four floats')
        return value_d

    @staticmethod
    def _is_list_of_numbers_valid(
        number_list: Any,
        count: int
    ) -> bool:
        """Validates that a list contains the correct number of numeric elements."""
        if not (not hasattr(number_list, 'strip')
                and (hasattr(number_list, '__getitem__') or hasattr(number_list, '__iter__'))):
            return False
        elif len(number_list) != count:
            return False
        return all([isinstance(x, numbers.Number) for x in number_list])
