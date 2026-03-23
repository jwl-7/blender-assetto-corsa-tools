import bpy
from bpy.props import StringProperty, BoolProperty


class ReportOperator(bpy.types.Operator):
    """Operator to display import results or errors in a popup."""
    bl_idname = 'importer.report_message'
    bl_label = 'Import report'

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
        row.operator('importer.report_clipboard').content = self.message


class CopyClipboardButtonOperator(bpy.types.Operator):
    """Utility operator to copy report text to system clipboard."""
    bl_idname = 'importer.report_clipboard'
    bl_label = 'Copy to clipboard'

    content: StringProperty()

    def execute(self, context: bpy.types.Context) -> set:
        context.window_manager.clipboard = self.content
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:
        self.execute(context)
        return {'FINISHED'}


REGISTER_CLASSES: tuple = (
    ReportOperator,
    CopyClipboardButtonOperator,
)


def register():
    for cls in REGISTER_CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(REGISTER_CLASSES):
        bpy.utils.unregister_class(cls)
