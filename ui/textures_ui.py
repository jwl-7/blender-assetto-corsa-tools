import bpy
from bpy.props import StringProperty


class TextureProperties(bpy.types.PropertyGroup):
    shaderInputName: StringProperty(
        name='Shader Input Name',
        default='txDiffuse',
        description='Name of the shader input slot the texture should be assigned to')


class KN5_PT_TexturePanel(bpy.types.Panel):
    bl_label = 'Assetto Corsa'
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Assetto Corsa'

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Checks if a single texture node is selected."""
        if len(context.selected_nodes) == 1:
            return isinstance(context.selected_nodes[0], bpy.types.ShaderNodeTexImage)
        return False

    def draw(self, context: bpy.types.Context):
        """Draws the texture assignment property."""
        ac_node: TextureProperties = context.selected_nodes[0].assettoCorsa
        self.layout.prop(ac_node, 'shaderInputName')


REGISTER_CLASSES: tuple = (
    TextureProperties,
    KN5_PT_TexturePanel,
)


def register():
    """Registers texture properties for ShaderNodeTexImage."""
    for cls in REGISTER_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.ShaderNodeTexImage.assettoCorsa = bpy.props.PointerProperty(type=TextureProperties)


def unregister():
    """Unregisters texture properties."""
    del bpy.types.ShaderNodeTexImage.assettoCorsa
    for cls in reversed(REGISTER_CLASSES):
        bpy.utils.unregister_class(cls)
