import bpy
from bpy.props import (
    BoolProperty,
    FloatProperty,
    IntProperty,
)


class NodeProperties(bpy.types.PropertyGroup):
    lodIn: FloatProperty(
        name='LOD In',
        min=0.0,
        unit='LENGTH',
        subtype='DISTANCE',
        description='Nearest distance to the object until it disappears')
    lodOut: FloatProperty(
        name='LOD Out',
        min=0.0,
        unit='LENGTH',
        subtype='DISTANCE',
        description='Farthest distance to the object until it disappears')
    layer: IntProperty(
        name='Layer',
        default=0,
        description='Unknown behaviour')
    castShadows: BoolProperty(
        name='Cast Shadows',
        default=True)
    visible: BoolProperty(
        name='Visible',
        default=True,
        description='Unknown behaviour')
    transparent: BoolProperty(
        name='Transparent',
        default=False)
    renderable: BoolProperty(
        name='Renderable',
        default=True,
        description='Toggles if the object should be rendered or not')


class KN5_PT_NodePanel(bpy.types.Panel):
    bl_label = 'Assetto Corsa'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Determines if the object panel should be shown."""
        return context.object and context.object.type in ['MESH', 'CURVE']

    def draw(self, context: bpy.types.Context):
        """Draws the Assetto Corsa object properties."""
        ac_obj: NodeProperties = context.object.assettoCorsa
        self.layout.prop(ac_obj, 'renderable')
        self.layout.prop(ac_obj, 'castShadows')
        self.layout.prop(ac_obj, 'transparent')
        self.layout.prop(ac_obj, 'lodIn')
        self.layout.prop(ac_obj, 'lodOut')
        self.layout.prop(ac_obj, 'layer')
        self.layout.prop(ac_obj, 'visible')


REGISTER_CLASSES: tuple = (
    NodeProperties,
    KN5_PT_NodePanel,
)


def register():
    """Registers the node properties and panel."""
    for cls in REGISTER_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Object.assettoCorsa = bpy.props.PointerProperty(type=NodeProperties)


def unregister():
    """Unregisters the node properties and panel."""
    del bpy.types.Object.assettoCorsa
    for cls in reversed(REGISTER_CLASSES):
        bpy.utils.unregister_class(cls)
