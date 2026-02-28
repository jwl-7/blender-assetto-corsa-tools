import bpy
from typing import Any, List
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty,
)
from ..exporter import material_writer


def convert_dict_to_blender_enum(dictionary: dict) -> List[tuple]:
    """Converts a dictionary into a list of tuples for Blender EnumProperty."""
    items = []
    for key in dictionary:
        val: str = str(dictionary[key])
        items.append((val, key, val))
    return items


class ShaderPropertyItem(bpy.types.PropertyGroup):
    name: StringProperty(name='Property name', default='ksDiffuse')
    valueA: FloatProperty(name='Value A')
    valueB: FloatVectorProperty(name='Value B', size=2)
    valueC: FloatVectorProperty(name='Value C', size=3)
    valueD: FloatVectorProperty(name='Value D', size=4)


class MaterialProperties(bpy.types.PropertyGroup):
    shaderName: StringProperty(
        name='Shader Name',
        default='ksPerPixel')
    alphaBlendMode: EnumProperty(
        name='Alpha Blend Mode',
        items=convert_dict_to_blender_enum(material_writer.MATERIAL_BLEND_MODE),
        default=str(material_writer.MATERIAL_BLEND_MODE['Opaque']))
    alphaTested: BoolProperty(
        name='Alpha Tested',
        default=False)
    depthMode: EnumProperty(
        name='Depth Mode',
        items=convert_dict_to_blender_enum(material_writer.MATERIAL_DEPTH_MODE),
        default=str(material_writer.MATERIAL_DEPTH_MODE['DepthNormal']))
    shaderProperties: CollectionProperty(
        type=ShaderPropertyItem)
    shaderPropertiesActive: IntProperty(
        name='Active Shader Property',
        default=-1)


class KN5_UL_ShaderPropertiesList(bpy.types.UIList):
    def draw_item(self, context: bpy.types.Context, layout: bpy.types.UILayout, _data: Any, item: ShaderPropertyItem, _icon: int, _active_data: Any, _active_propname: str, _index: int):
        """Draws the individual items in the shader properties list."""
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, 'name', text='', emboss=False)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.prop(item, 'name', text='', emboss=False)


class KN5_PT_MaterialPanel(bpy.types.Panel):
    bl_label = 'Assetto Corsa'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'material'

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Determines if the panel should be displayed."""
        return context.material is not None

    def draw(self, context: bpy.types.Context):
        """Draws the layout of the material panel."""
        ac_mat: MaterialProperties = context.material.assettoCorsa
        self.layout.prop(ac_mat, 'shaderName')
        self.layout.prop(ac_mat, 'alphaBlendMode')
        self.layout.prop(ac_mat, 'alphaTested')
        self.layout.prop(ac_mat, 'depthMode')

        shader_box: bpy.types.UILayout = self.layout.box()
        shader_box.label(text='Shader Properties')

        if ac_mat.shaderProperties:
            shader_box.template_list(
                'KN5_UL_ShaderPropertiesList',
                '',
                ac_mat,
                'shaderProperties',
                ac_mat,
                'shaderPropertiesActive',
                rows=1
            )

            if 0 <= ac_mat.shaderPropertiesActive < len(ac_mat.shaderProperties):
                active_prop: ShaderPropertyItem = ac_mat.shaderProperties[ac_mat.shaderPropertiesActive]
                row: bpy.types.UILayout = shader_box.row()

                col_a: bpy.types.UILayout = row.column()
                col_a.label(text=ShaderPropertyItem.valueA[1]['name'])
                col_a.prop(active_prop, 'valueA', text='')
                col_a.prop(active_prop, 'valueD')

                col_b: bpy.types.UILayout = row.column()
                col_b.prop(active_prop, 'valueB')
                col_b.prop(active_prop, 'valueC')

        row: bpy.types.UILayout = shader_box.row()
        row.operator('acmaterialshaderproperties.add')
        row.operator('acmaterialshaderproperties.remove')


class MaterialShaderPropertyAddButton(bpy.types.Operator):
    """Operator to add a new shader property to the material."""
    bl_idname = 'acmaterialshaderproperties.add'
    bl_label = 'Add Shader Property'

    def execute(self, context: bpy.types.Context) -> set:
        ac_mat: MaterialProperties = context.material.assettoCorsa
        ac_mat.shaderProperties.add()
        return {'FINISHED'}


class MaterialShaderPropertyRemoveButton(bpy.types.Operator):
    """Operator to remove the selected shader property from the material."""
    bl_idname = 'acmaterialshaderproperties.remove'
    bl_label = 'Remove Shader Property'

    def execute(self, context: bpy.types.Context) -> set:
        ac_mat: MaterialProperties = context.material.assettoCorsa
        ac_mat.shaderProperties.remove(ac_mat.shaderPropertiesActive)
        return {'FINISHED'}


REGISTER_CLASSES: tuple = (
    ShaderPropertyItem,
    MaterialProperties,
    KN5_UL_ShaderPropertiesList,
    KN5_PT_MaterialPanel,
    MaterialShaderPropertyAddButton,
    MaterialShaderPropertyRemoveButton,
)


def register():
    """Registers the material UI classes and properties."""
    for cls in REGISTER_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Material.assettoCorsa = bpy.props.PointerProperty(type=MaterialProperties)


def unregister():
    """Unregisters the material UI classes and properties."""
    del bpy.types.Material.assettoCorsa
    for cls in reversed(REGISTER_CLASSES):
        bpy.utils.unregister_class(cls)
