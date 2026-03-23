"""Fixes a KsEditor FBX INI file with correct AC character material properties."""

import re

TARGET_VALUES = {
    'ksAmbient':     '0.3',
    'ksDiffuse':     '0.2',
    'ksSpecular':    '0.1',
    'ksSpecularEXP': '10',
}


def fix_ini(input_path: str) -> tuple[bool, str]:
    """Rewrites character material properties in the given KsEditor INI file."""
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if not any(line.strip().startswith('[MATERIAL_') for line in lines):
        return False, 'This does not appear to be a KsEditor material INI file.\nNo [MATERIAL_] sections found.'

    output = []
    current_material_name = None
    current_var_name = None

    for line in lines:
        stripped = line.rstrip('\r\n')

        if stripped.startswith('NAME='):
            current_material_name = stripped[5:].strip()
            current_var_name = None
            output.append(line)
            continue

        if stripped.startswith('ALPHABLEND='):
            output.append('ALPHABLEND=0\n')
            continue

        if stripped.startswith('ALPHATEST='):
            output.append('ALPHATEST=0\n')
            continue

        var_name_match = re.match(r'^(VAR_\d+_NAME)=(.+)', stripped)
        if var_name_match:
            current_var_name = var_name_match.group(2).strip()
            output.append(line)
            continue

        float1_match = re.match(r'^(VAR_\d+_FLOAT1)=(.+)', stripped)
        if float1_match and current_var_name in TARGET_VALUES:
            key = float1_match.group(1)
            output.append(f'{key}={TARGET_VALUES[current_var_name]}\n')
            continue

        res_name_match = re.match(r'^(RES_\d+_NAME)=(.+)', stripped)
        if res_name_match:
            current_var_name = res_name_match.group(2).strip()
            output.append(line)
            continue

        res_tex_match = re.match(r'^(RES_\d+_TEXTURE)=(.+)', stripped)
        if res_tex_match:
            key = res_tex_match.group(1)
            if current_var_name == 'txDiffuse':
                tex = f'{current_material_name}.dds' if current_material_name else 'NULL.dds'
                output.append(f'{key}={tex}\n')
            elif current_var_name in ('txNormal', 'txMaps', 'txDetail'):
                output.append(f'{key}=NULL.dds\n')
            else:
                output.append(line)
            continue

        output.append(line)

    with open(input_path, 'w', encoding='utf-8') as f:
        f.writelines(output)

    return True, f'File updated successfully:\n{input_path}\n\nNOTE: txDiffuse is set to <MATERIAL_NAME>.dds\nReplace with your actual texture filenames if needed.'
