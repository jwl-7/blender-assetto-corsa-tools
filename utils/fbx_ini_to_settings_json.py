"""FBX [INI] -> [JSON]

Converts fbx.ini file in ksEditor persistence format for cars -> JSON settings file.
This provides the configuration for assetto corsa tools to apply all the correct material settings.
"""

import json
import os
import re
import tkinter as tk
from tkinter import filedialog
from typing import Any, Dict, Tuple

def _parse_ini(filepath: str) -> Dict[str, Dict[str, str]]:
    """Parses an INI file into a nested dictionary structure."""
    sections = {}
    current = None
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith(';') or line.startswith('//'):
                continue
            if line.startswith('[') and line.endswith(']'):
                current = line[1:-1]
                sections.setdefault(current, {})
            elif '=' in line and current is not None:
                key, _, value = line.partition('=')
                sections[current][key.strip()] = value.strip()
    return sections

def parse_float(s: Any) -> float:
    """Converts a string or object to a float, returning 0.0 on failure."""
    try:
        return float(str(s).strip())
    except (ValueError, AttributeError):
        return 0.0

def parse_floatn(s: str, n: int) -> Tuple[float, ...]:
    """Parses a comma-separated string into a tuple of n floats."""
    parts = [p.strip() for p in s.split(',')]
    result = []
    for i in range(n):
        try:
            result.append(float(parts[i]))
        except (IndexError, ValueError):
            result.append(0.0)
    return tuple(result)

def get_bool(data: Dict[str, str], key: str, default: bool) -> bool:
    """Extracts a boolean value from a dictionary based on common string representations."""
    return data.get(key, str(default)).lower() in ('1', 'true', 'yes')

def convert_sections_to_json(sections: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    """Converts INI section data into a structured dictionary for JSON export."""
    data = {'materials': {}, 'nodes': {}}
    applied_mats = 0
    applied_nodes = 0

    for section_name, section_data in sections.items():
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
                        'valueA': parse_float(section_data.get(f'{p}FLOAT1', '0')),
                        'valueB': list(parse_floatn(section_data.get(f'{p}FLOAT2', '0, 0'), 2)),
                        'valueC': list(parse_floatn(section_data.get(f'{p}FLOAT3', '0, 0, 0'), 3)),
                        'valueD': list(parse_floatn(section_data.get(f'{p}FLOAT4', '0, 0, 0, 0'), 4))
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
            applied_mats += 1

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
                'castShadows': get_bool(section_data, 'CAST_SHADOWS', True),
                'renderable':  get_bool(section_data, 'RENDERABLE', True),
                'transparent': get_bool(section_data, 'TRANSPARENT', False),
                'visible':     get_bool(section_data, 'VISIBLE', True),
                'layer':       int(parse_float(section_data.get('PRIORITY', '0'))),
                'lodIn':       parse_float(section_data.get('LOD_IN', '0')),
                'lodOut':      parse_float(section_data.get('LOD_OUT', '0'))
            }

    print(f'Success! Processed {applied_mats} materials and {applied_nodes} nodes.')
    return data

def run_interface():
    """Opens a file dialog to select an INI file and saves the converted JSON."""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title='Open .fbx.ini', filetypes=[('INI files', '*.ini')])

    if file_path:
        dest_path = os.path.join(os.path.dirname(file_path), 'settings.json')
        sections = _parse_ini(file_path)
        final_json = convert_sections_to_json(sections)
        with open(dest_path, 'w', encoding='utf-8') as f:
            json.dump(final_json, f, indent=4)
        print(f'Saved: {dest_path}')

if __name__ == '__main__':
    run_interface()
