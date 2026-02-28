class MaterialSettings:
    def __init__(
        self,
        settings: Dict[str, Any],
        warnings: List[str],
        material_settings_key: str
    ):
        self.settings: Dict[str, Any] = settings
        self.warnings: List[str] = warnings
        self.material_settings_key: str = material_settings_key
        self.material_name_matches: List[re.Pattern] = self._convert_to_matches_list(material_settings_key)

    def apply_settings_to_material(self, material: 'MaterialProperties'):
        """Applies JSON settings overrides to a material."""
        if not self._does_material_name_match(material.name):
            return
        shader_name: Optional[str] = self._get_material_shader()
        if shader_name:
            material.shaderName = shader_name

        alpha_blend_mode: Optional[int] = self._get_material_blend_mode()
        if alpha_blend_mode:
            material.alphaBlendMode = alpha_blend_mode
        alpha_tested: Optional[bool] = self._get_material_alpha_tested()
        if alpha_tested:
            material.alphaTested = alpha_tested
        depth_mode: Optional[int] = self._get_material_depth_mode()
        if depth_mode:
            material.depthMode = depth_mode

        property_names: List[str] = self._get_material_property_names()
        if property_names:
            material.shaderProperties.clear()
        for property_name in property_names:
            shader_property: Optional[ShaderProperty] = None
            if property_name in material.shaderProperties:
                shader_property = material.shaderProperties[property_name]
            else:
                shader_property = ShaderProperty(property_name)
                material.shaderProperties[property_name] = shader_property

            value_a: Optional[float] = self._get_material_property_value_a(property_name)
            if value_a:
                shader_property.valueA = value_a
            value_b: Optional[Any] = self._get_material_property_value_b(property_name)
            if value_b:
                shader_property.valueB = value_b
            value_c: Optional[Any] = self._get_material_property_value_c(property_name)
            if value_c:
                shader_property.valueC = value_c
            value_d: Optional[Any] = self._get_material_property_value_d(property_name)
            if value_d:
                shader_property.valueD = value_d

        texture_mapping_names: List[str] = self._get_material_texture_mapping_names()
        if texture_mapping_names:
            material.texture_mapping.clear()
        for texture_mapping_name in texture_mapping_names:
            texture_name: Optional[str] = self._get_material_texture_mapping_name(texture_mapping_name)
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

    def _convert_to_matches_list(self, key: str) -> List[re.Pattern]:
        """Converts pipe-separated keys into regex patterns."""
        matches: List[re.Pattern] = []
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

    def _get_material_shader(self) -> Optional[str]:
        if 'shaderName' in self.settings[MATERIALS][self.material_settings_key]:
            return self.settings[MATERIALS][self.material_settings_key]['shaderName']
        return None

    def _get_material_blend_mode(self) -> Optional[int]:
        if 'alphaBlendMode' in self.settings[MATERIALS][self.material_settings_key]:
            mode_name: str = self.settings[MATERIALS][self.material_settings_key]['alphaBlendMode']
            return MATERIAL_BLEND_MODE[mode_name]
        return None

    def _get_material_depth_mode(self) -> Optional[int]:
        if 'depthMode' in self.settings[MATERIALS][self.material_settings_key]:
            mode_name: str = self.settings[MATERIALS][self.material_settings_key]['depthMode']
            return MATERIAL_DEPTH_MODE[mode_name]
        return None

    def _get_material_alpha_tested(self) -> Optional[bool]:
        if 'alphaTested' in self.settings[MATERIALS][self.material_settings_key]:
            return self.settings[MATERIALS][self.material_settings_key]['alphaTested']
        return None

    def _get_material_property_names(self) -> List[str]:
        if PROPERTIES in self.settings[MATERIALS][self.material_settings_key]:
            return list(self.settings[MATERIALS][self.material_settings_key][PROPERTIES].keys())
        return []

    def _get_material_property_value(
        self,
        property_name: str,
        value_name: str
    ) -> Optional[Any]:
        if value_name in self.settings[MATERIALS][self.material_settings_key][PROPERTIES][property_name]:
            return self.settings[MATERIALS][self.material_settings_key][PROPERTIES][property_name][value_name]
        return None

    def _get_material_texture_mapping_names(self) -> List[str]:
        if TEXTURES in self.settings[MATERIALS][self.material_settings_key]:
            return list(self.settings[MATERIALS][self.material_settings_key][TEXTURES].keys())
        return []

    def _get_material_texture_mapping_name(self, mapping_name: str) -> Optional[str]:
        if TEXTURES in self.settings[MATERIALS][self.material_settings_key]:
            return self.settings[MATERIALS][self.material_settings_key][TEXTURES][mapping_name]['textureName']
        return None

    def _get_material_property_value_a(self, property_name: str) -> Optional[float]:
        value_a = self._get_material_property_value(property_name, 'valueA')
        if value_a is None:
            return None
        if not isinstance(value_a, numbers.Number):
            raise Exception('valueA must be a float')
        return float(value_a)

    def _get_material_property_value_b(self, property_name: str) -> Optional[Any]:
        value_b = self._get_material_property_value(property_name, 'valueB')
        if value_b is None:
            return None
        if not self._is_list_of_numbers_valid(value_b, 2):
            raise Exception('valueB must be a list of two floats')
        return value_b

    def _get_material_property_value_c(self, property_name: str) -> Optional[Any]:
        value_c = self._get_material_property_value(property_name, 'valueC')
        if value_c is None:
            return None
        if not self._is_list_of_numbers_valid(value_c, 3):
            raise Exception('valueC must be a list of three floats')
        return value_c

    def _get_material_property_value_d(self, property_name: str) -> Optional[Any]:
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
