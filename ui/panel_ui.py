import bpy


class ACPanelMixamo(bpy.types.Panel):
    """N panel for Mixamo rigging tools."""
    bl_label = 'Mixamo Tools'
    bl_idname = 'ACPanelMixamo'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Assetto Corsa'

    def draw(self, context: bpy.types.Context):
        self.layout.operator('mixamo.add_acroot', text='Add acroot Bone')
        self.layout.operator('mixamo.rename_rig_bones', text='Rename Rig Bones')
        self.layout.operator('mixamo.fix_scale', text='Fix Scale')


class ACPanelCharacter(bpy.types.Panel):
    """N panel for character tools."""
    bl_label = 'Character Tools'
    bl_idname = 'ACPanelCharacter'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Assetto Corsa'

    def draw(self, context: bpy.types.Context):
        self.layout.operator('character.rotate_armature', text='Add 90° rotation to armature')
        self.layout.operator('character.fbx_ini', text='Configure Persistence File (fbx.ini)')
        self.layout.operator('character.texture_report', text='Log texture mapping')


class ACPanelExport(bpy.types.Panel):
    """N panel for export tools."""
    bl_label = 'Export Tools'
    bl_idname = 'ACPanelExport'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Assetto Corsa'

    def draw(self, context: bpy.types.Context):
        self.layout.operator('exporter.kn5', text='Export KN5')
        self.layout.operator('exporter.ksanim', text='Export KSANIM')


REGISTER_CLASSES: tuple = (
    ACPanelMixamo,
    ACPanelCharacter,
    ACPanelExport
)


def register():
    for cls in REGISTER_CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(REGISTER_CLASSES):
        bpy.utils.unregister_class(cls)
