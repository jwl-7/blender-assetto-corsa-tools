import bpy
from bpy.props import BoolProperty, StringProperty
from . import acroot_adder, bone_renamer, scale_fixer


class ReportOperator(bpy.types.Operator):
    """Operator to display results or errors in a popup."""
    bl_idname = 'mixamo.report_message'
    bl_label = 'Mixamo report'

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
        row = self.layout.row()
        row.operator('mixamo.report_clipboard').content = self.message


class CopyClipboardButtonOperator(bpy.types.Operator):
    """Utility operator to copy report text to system clipboard."""
    bl_idname = 'mixamo.report_clipboard'
    bl_label = 'Copy to clipboard'

    content: StringProperty()

    def execute(self, context: bpy.types.Context) -> set:
        context.window_manager.clipboard = self.content
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:
        self.execute(context)
        return {'FINISHED'}


class AddAcroot(bpy.types.Operator):
    """Adds an acroot bone as parent of Hips/"""
    bl_idname = 'mixamo.add_acroot'
    bl_label = 'Add acroot Bone'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set:
        obj = context.active_object

        if not obj or obj.type != 'ARMATURE':
            bpy.ops.mixamo.report_message(
                'INVOKE_DEFAULT',
                is_error=True,
                title='Add acroot failed',
                message='No armature selected. Please select an armature and try again.'
            )
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='EDIT')

        if obj.data.edit_bones.get('acroot'):
            bpy.ops.mixamo.report_message(
                'INVOKE_DEFAULT',
                is_error=True,
                title='Add acroot failed',
                message='acroot bone already exists.'
            )
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'CANCELLED'}

        msg, success = acroot_adder.add_acroot(obj)
        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.mixamo.report_message(
            'INVOKE_DEFAULT',
            is_error=not success,
            title='Add acroot',
            message=msg
        )
        return {'FINISHED'}


class RenameMixamoBones(bpy.types.Operator):
    """Renames armature bones from find to replace."""
    bl_idname = 'mixamo.rename_rig_bones'
    bl_label = 'Rename Mixamo Rig Bones'
    bl_options = {'REGISTER', 'UNDO'}

    find: StringProperty(name='Find', default='mixamorig')
    replace: StringProperty(name='Replace', default='mixamorig')

    def execute(self, context: bpy.types.Context) -> set:
        obj = context.active_object

        if not obj or obj.type != 'ARMATURE':
            bpy.ops.mixamo.report_message(
                'INVOKE_DEFAULT',
                is_error=True,
                title='Rename bones failed',
                message='No armature selected. Please select an armature and try again.'
            )
            return {'CANCELLED'}

        msg = bone_renamer.rename_bones(obj, self.find, self.replace)
        bpy.ops.mixamo.report_message(
            'INVOKE_DEFAULT',
            is_error=False,
            title='Rename bones',
            message=msg
        )
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context: bpy.types.Context):
        self.layout.prop(self, 'find')
        self.layout.prop(self, 'replace')


class FixMixamoScale(bpy.types.Operator):
    """Apply scale of 1.000 to armature without messing up animation."""
    bl_idname = 'mixamo.fix_scale'
    bl_label = 'Fix Mixamo Scale'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set:
        obj = context.active_object

        if not obj or obj.type != 'ARMATURE':
            bpy.ops.mixamo.report_message(
                'INVOKE_DEFAULT',
                is_error=True,
                title='Fix scale failed',
                message='No armature selected. Please select an armature and try again.'
            )
            return {'CANCELLED'}

        msg = scale_fixer.fix_scale(obj)
        bpy.ops.mixamo.report_message(
            'INVOKE_DEFAULT',
            is_error=False,
            title='Fix scale success',
            message=msg
        )
        return {'FINISHED'}


REGISTER_CLASSES: tuple = (
    ReportOperator,
    CopyClipboardButtonOperator,
    AddAcroot,
    RenameMixamoBones,
    FixMixamoScale
)


def register():
    for cls in REGISTER_CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(REGISTER_CLASSES):
        bpy.utils.unregister_class(cls)
