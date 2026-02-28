from typing import Dict, Any
import bpy


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
        self.valueB: tuple = (0.0, 0.0)
        self.valueC: tuple = (0.0, 0.0, 0.0)
        self.valueD: tuple = (0.0, 0.0, 0.0, 0.0)

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
        self.shaderProperties: Dict[str, ShaderProperty] = self.copy_
