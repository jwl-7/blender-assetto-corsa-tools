"""Character, Mixamo, and Export tools for Assetto Corsa."""

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ImportHelper
from . import ini_fixer, texture_reporter


class CharacterProcessFBXINI(bpy.types.Operator, ImportHelper):
    """Set texture properties in a KsEditor FBX INI persistence file."""
    bl_idname = 'character.fbx_ini'
    bl_label = 'Configure Persistence File (fbx.ini)'
    filename_ext = '.ini'
    filter_glob: StringProperty(default='*.ini', options={'HIDDEN'})

    def execute(self, context: bpy.types.Context) -> set:
        success, msg = ini_fixer.fix_ini(self.filepath)
        bpy.ops.character.report_message(
            'INVOKE_DEFAULT',
            is_error=not success,
            title='Set Texture Properties',
            message=msg
        )
        return {'FINISHED'} if success else {'CANCELLED'}


class TextureReportOperator(bpy.types.Operator):
    """Print a mesh -> material -> texture report to the system console."""
    bl_idname = 'character.texture_report'
    bl_label = 'Print Texture Report'

    def execute(self, context: bpy.types.Context) -> set:
        report = texture_reporter.build_report()
        print('\n' + '=' * 60)
        print('  MESH -> MATERIAL -> TEXTURE REPORT')
        print('=' * 60)
        print(report)
        bpy.ops.character.report_message(
            'INVOKE_DEFAULT',
            is_error=False,
            title='Texture Report',
            message=report
        )
        return {'FINISHED'}


class ReportOperator(bpy.types.Operator):
    """Operator to display results or errors in a popup."""
    bl_idname = 'character.report_message'
    bl_label = 'character report'

    is_error: BoolProperty()
    title: StringProperty()
    message: StringProperty()

    def execute(self, context: bpy.types.Context) -> set:
        if self.is_error:
            self.report({'WARNING'}, self.message)
        else:
            self.report({'INFO'}, self.message)
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:
        self.execute(context)
        return context.window_manager.invoke_popup(self, width=600)

    def draw(self, context: bpy.types.Context):
        if self.is_error:
            self.layout.alert = True
        row: bpy.types.UILayout = self.layout.row()
        row.alignment = 'CENTER'
        row.label(text=self.title)
        for line in self.message.splitlines():
            row = self.layout.row()
            line = line.replace('\t', ' ' * 4)
            row.label(text=line)


class AC_PT_MixamoPanel(bpy.types.Panel):
    """N panel for Mixamo rigging tools."""
    bl_label = 'Mixamo Tools'
    bl_idname = 'AC_PT_mixamo'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Assetto Corsa'

    def draw(self, context: bpy.types.Context):
        self.layout.operator('mixamo.add_acroot', text='Add acroot Bone')
        self.layout.operator('mixamo.rename_rig_bones', text='Rename Rig Bones')
        self.layout.operator('mixamo.rename_anim_bones', text='Rename Animation Bones')


class AC_PT_CharacterPanel(bpy.types.Panel):
    """N panel for character tools."""
    bl_label = 'Character Tools'
    bl_idname = 'AC_PT_character'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Assetto Corsa'

    def draw(self, context: bpy.types.Context):
        self.layout.operator(CharacterProcessFBXINI.bl_idname, text='Configure Persistence File (fbx.ini)')
        self.layout.operator(TextureReportOperator.bl_idname, text='Log texture mapping')


class AC_PT_ExportPanel(bpy.types.Panel):
    """N panel for export tools."""
    bl_label = 'Export Tools'
    bl_idname = 'AC_PT_export'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Assetto Corsa'

    def draw(self, context: bpy.types.Context):
        self.layout.operator('exporter.kn5', text='Export KN5')
        self.layout.operator('exporter.ksanim', text='Export KSANIM')


REGISTER_CLASSES: tuple = (
    ReportOperator,
    CharacterProcessFBXINI,
    TextureReportOperator,
    AC_PT_MixamoPanel,
    AC_PT_CharacterPanel,
    AC_PT_ExportPanel,
)


def register():
    for cls in REGISTER_CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(REGISTER_CLASSES):
        bpy.utils.unregister_class(cls)
