"""FBX [INI] -> [JSON]

Converts fbx.ini file in ksEditor persistence format for cars -> JSON settings file.
This provides the configuration for assetto corsa tools to apply all the correct material settings.
"""

import json
import re
import bpy
from typing import Any
from ..ui.materials_ui import MaterialProperties


class FBXINIReader:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.sections: dict[str, dict[str, str]] = {}
        self.json_data: dict[str, Any] = {}
        self.applied_mats: int = 0
        self.applied_nodes: int = 0

    def parse_ini(self):
        """Parses an INI file into a nested dictionary structure."""
        current = None
        with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith(';') or line.startswith('//'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    current = line[1:-1]
                    self.sections.setdefault(current, {})
                elif '=' in line and current is not None:
                    key, _, value = line.partition('=')
                    self.sections[current][key.strip()] = value.strip()

    def parse_float(self, s: Any) -> float:
        """Converts a string or object to a float, returning 0.0 on failure."""
        try:
            return float(str(s).strip())
        except (ValueError, AttributeError):
            return 0.0

    def parse_floatn(self, s: str, n: int) -> tuple[float, ...]:
        """Parses a comma-separated string into a tuple of n floats."""
        parts = [p.strip() for p in s.split(',')]
        result = []
        for i in range(n):
            try:
                result.append(float(parts[i]))
            except (IndexError, ValueError):
                result.append(0.0)
        return tuple(result)

    def get_bool(self, data: dict[str, str], key: str, default: bool) -> bool:
        """Extracts a boolean value from a dictionary based on common string representations."""
        return data.get(key, str(default)).lower() in ('1', 'true', 'yes')

    def convert_sections_to_json(self):
        """Converts INI section data into a structured dictionary for JSON export."""
        data = {'materials': {}, 'nodes': {}}

        for section_name, section_data in self.sections.items():
            # materials
            m = re.fullmatch(r'MATERIAL_(\d+)', section_name, re.IGNORECASE)
            if m and section_name != 'MATERIAL_LIST':
                mat_name = section_data.get('NAME', section_name)
                mat_data = {
                    'alphaBlendMode': 'AlphaBlend' if section_data.get('ALPHABLEND') == '1' else 'Opaque',
                    'alphaTested': section_data.get('ALPHATEST') == '1',
                    'depthMode': {'0': 'DepthNormal', '1': 'DepthNoWrite', '2': 'DepthOff'}.get(
                        section_data.get('DEPTHMODE', '0'), 'DepthNormal'
                    ),
                    'properties': {},
                    'shaderName': section_data.get('SHADER', 'ksPerPixel'),
                    'textures': {}
                }

                var_count = int(section_data.get('VARCOUNT', '0'))
                for i in range(var_count):
                    p = f'VAR_{i}_'
                    prop_name = section_data.get(f'{p}NAME')
                    if prop_name:
                        mat_data['properties'][prop_name] = {
                            'valueA': self.parse_float(section_data.get(f'{p}FLOAT1', '0')),
                            'valueB': list(self.parse_floatn(section_data.get(f'{p}FLOAT2', '0, 0'), 2)),
                            'valueC': list(self.parse_floatn(section_data.get(f'{p}FLOAT3', '0, 0, 0'), 3)),
                            'valueD': list(self.parse_floatn(section_data.get(f'{p}FLOAT4', '0, 0, 0, 0'), 4))
                        }

                res_count = int(section_data.get('RESCOUNT', '0'))
                for i in range(res_count):
                    p = f'RES_{i}_'
                    res_name = section_data.get(f'{p}NAME')
                    if res_name:
                        mat_data['textures'][res_name] = {
                            'slot': int(section_data.get(f'{p}SLOT', str(i))),
                            'textureName': section_data.get(f'{p}TEXTURE', '')
                        }

                data['materials'][mat_name] = mat_data
                self.applied_mats += 1

            # nodes
            elif section_name.startswith('model_FBX'):
                raw_path = section_name.split('.fbx_')[-1].strip(' ]')
                essential_keys = {'VISIBLE', 'TRANSPARENT', 'CAST_SHADOWS', 'RENDERABLE'}
                has_real_data = any(key in section_data for key in essential_keys)

                if has_real_data:
                    parts = raw_path.split('_')
                    seen = []
                    for p in parts:
                        if not (p.isupper() and p.isalpha()):
                            if p not in seen:
                                seen.append(p)
                    clean_name = '_'.join(seen)
                else:
                    continue

                data['nodes'][clean_name] = {
                    'castShadows': self.get_bool(section_data, 'CAST_SHADOWS', True),
                    'renderable':  self.get_bool(section_data, 'RENDERABLE', True),
                    'transparent': self.get_bool(section_data, 'TRANSPARENT', False),
                    'visible':     self.get_bool(section_data, 'VISIBLE', True),
                    'layer':       int(self.parse_float(section_data.get('PRIORITY', '0'))),
                    'lodIn':       self.parse_float(section_data.get('LOD_IN', '0')),
                    'lodOut':      self.parse_float(section_data.get('LOD_OUT', '0'))
                }
                self.applied_nodes += 1

        # print(f'Success! Processed {applied_mats} materials and {applied_nodes} nodes.')
        self.json_data = data

    def apply_to_scene(self) -> int:
        """Applies parsed material settings directly to matching Blender materials.

        Matches by material name. Returns the number of materials applied.
        """
        applied = 0
        for mat_name, mat_data in self.json_data.get('materials', {}).items():
            bl_mat = bpy.data.materials.get(mat_name)
            if bl_mat is None:
                continue

            ac_mat: MaterialProperties = bl_mat.assettoCorsa
            ac_mat.shaderName = mat_data.get('shaderName', 'ksPerPixel')
            ac_mat.alphaBlendMode = str({'Opaque': 0, 'AlphaBlend': 1, 'AlphaToCoverage': 2}.get(
                mat_data.get('alphaBlendMode', 'Opaque'), 0))
            ac_mat.alphaTested = mat_data.get('alphaTested', False)
            ac_mat.depthMode = str({'DepthNormal': 0, 'DepthNoWrite': 1, 'DepthOff': 2}.get(
                mat_data.get('depthMode', 'DepthNormal'), 0))

            ac_mat.shaderProperties.clear()
            for prop_name, prop_vals in mat_data.get('properties', {}).items():
                item = ac_mat.shaderProperties.add()
                item.name = prop_name
                item.valueA = prop_vals.get('valueA', 0.0)
                item.valueB = prop_vals.get('valueB', [0.0, 0.0])
                item.valueC = prop_vals.get('valueC', [0.0, 0.0, 0.0])
                item.valueD = prop_vals.get('valueD', [0.0, 0.0, 0.0, 0.0])

            applied += 1

        return applied

    def save_json(self, json_path: str):
        """Saves the converted JSON data to a file."""
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.json_data, f, indent=4)
