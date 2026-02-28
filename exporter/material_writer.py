import numbers
import os
import re
from typing import Dict, List, Any, Optional, Tuple, Union
import bpy
from .exporter_utils import get_texture_nodes
from .kn5_writer import KN5Writer


MATERIAL_BLEND_MODE: Dict[str, int] = {
    'Opaque': 0,
    'AlphaBlend': 1,
    'AlphaToCoverage': 2,
}

MATERIAL_DEPTH_MODE: Dict[str, int] = {
    'DepthNormal': 0,
    'DepthNoWrite': 1,
    'DepthOff': 2,
}

AC_TEXTURE_SLOT_ID: Dict[str, int] = {
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


class ShaderProperty:
    def __init__(self, name: str):
        self.name: str = name
        self.valueA: float = 0.0
        self.valueB: Union[Tuple[float, float], List[float]] = (0.0, 0.0)
        self.valueC: Union[Tuple[float, float, float], List[float]] = (0.0, 0.0, 0.0)
        self.valueD: Union[Tuple[float, float, float, float], List[float]] = (0.0, 0.0, 0.0, 0.0)

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
        self.shaderProperties: Dict[str, ShaderProperty] = self.copy_shader_properties(material)
        self.texture_mapping: Dict[str, str] = self._generate_texture_mapping(material)

    def copy_shader_properties(self, material: bpy.types.Material) -> Dict[str, ShaderProperty]:
        """Copies shader properties from Blender to internal storage."""
        ac_mat: Any = material.assettoCorsa
        properties: Dict[str, ShaderProperty] = {}
        for shader_property in ac_mat.shaderProperties:
            new_property = ShaderProperty(shader_property.name)
            new_property.fill(shader_property)
            properties[shader_property.name] = new_property

        if not properties and ac_mat.shaderName == 'ksPerPixel':
            for p_name in ['ksDiffuse', 'ksAmbient']:
                new_p = ShaderProperty(p_name)
                new_p.valueA = 0.4
                properties[p_name] = new_p
        return properties

    def _generate_texture_mapping(self, material: bpy.types.Material) -> Dict[str, str]:
        """Maps shader input names to image names."""
        mapping: Dict[str, str] = {}
        texture_nodes = get_texture_nodes(material)
        for node in texture_nodes:
            if node.image and not node.image.name.startswith('__'):
                shader_input: str = node.assettoCorsa.shaderInputName
                if shader_input and shader_input.strip():
                    mapping[shader_input] = node.image.name
        return mapping


class MaterialWriter(KN5Writer):
    def __init__(
        self,
        file: Any,
        context: bpy.types.Context,
        settings: Dict[str, Any],
        warnings: List[str]
    ):
        super().__init__(file)
        self.available_materials: Dict[str, MaterialProperties] = {}
        self.material_positions: Dict[str, int] = {}
        self.material_settings: List['MaterialSettings'] = []
        self.context: bpy.types.Context = context
        self.settings: Dict[str, Any] = settings
        self.warnings: List[str] = warnings
        self._fill_available_materials()

    def write(self):
        """Writes all materials to the binary file."""
        self.write_int(len(self.available_materials))
        for name, _ in sorted(self.material_positions.items(), key=lambda k: k[1]):
            self._write_material(self.available_materials[name])

    def _write_material(self, material: MaterialProperties):
        """Binary write for a single material."""
        self.write_string(material.name)
        self.write_string(material.shaderName)
        self.write_byte(material.alphaBlendMode)
        self.write_bool(material.alphaTested)
        self.write_int(material.depthMode)

        self.write_uint(len(material.shaderProperties))
        for prop in material.shaderProperties.values():
            self.write_string(prop.name)
            self.write_float(prop.valueA)
            self.write_vector2(prop.valueB)
            self.write_vector3(prop.valueC)
            self.write_vector4(prop.valueD)

        self.write_uint(len(material.texture_mapping))
        fallback: int = len(AC_TEXTURE_SLOT_ID)
        for slot_name, tex_name in material.texture_mapping.items():
            slot_id: int = AC_TEXTURE_SLOT_ID.get(slot_name, fallback)
            if slot_name not in AC_TEXTURE_SLOT_ID: fallback += 1
            self.write_string(slot_name)
            self.write_uint(slot_id)
            self.write_string(tex_name)

    def _fill_available_materials(self):
        """Builds the list of materials to export."""
        if MATERIALS in self.settings:
            for key in self.settings[MATERIALS]:
                self.material_settings.append(MaterialSettings(self.settings, self.warnings, key))

        pos: int = 0
        for mat in self.context.blend_data.materials:
            if mat.users == 0:
                self.warnings.append(f"Ignoring unused material '{mat.name}'")
                continue
            if not mat.name.startswith('__'):
                props = MaterialProperties(mat)
                for setting in self.material_settings:
                    setting.apply_settings_to_material(props)
                self.available_materials[mat.name] = props
                self.material_positions[mat.name] = pos
                pos += 1


class MaterialSettings:
    def __init__(
        self,
        settings: Dict[str, Any],
        warnings: List[str],
        material_settings_key: str
    ):
        self.settings = settings
        self.warnings = warnings
        self.key = material_settings_key
        self.patterns = [re.compile(f'^{re.escape(s).replace(r"\*", ".*")}$', re.IGNORECASE) for s in self.key.split('|')]

    def apply_settings_to_material(self, material: MaterialProperties):
        """Applies JSON settings overrides to a material."""
        if not any(p.match(material.name) for p in self.patterns): return
        cfg = self.settings[MATERIALS][self.key]

        if 'shaderName' in cfg: material.shaderName = cfg['shaderName']
        if 'alphaBlendMode' in cfg: material.alphaBlendMode = MATERIAL_BLEND_MODE.get(cfg['alphaBlendMode'], 0)
        if 'alphaTested' in cfg: material.alphaTested = cfg['alphaTested']
        if 'depthMode' in cfg: material.depthMode = MATERIAL_DEPTH_MODE.get(cfg['depthMode'], 0)

        if PROPERTIES in cfg:
            for p_name, vals in cfg[PROPERTIES].items():
                if p_name not in material.shaderProperties: material.shaderProperties[p_name] = ShaderProperty(p_name)
                p = material.shaderProperties[p_name]
                if 'valueA' in vals: p.valueA = vals['valueA']
                if 'valueB' in vals: p.valueB = tuple(vals['valueB'])
                if 'valueC' in vals: p.valueC = tuple(vals['valueC'])
                if 'valueD' in vals: p.valueD = tuple(vals['valueD'])

        if TEXTURES in cfg:
            for slot, t_cfg in cfg[TEXTURES].items():
                if 'textureName' in t_cfg: material.texture_mapping[slot] = t_cfg['textureName']
