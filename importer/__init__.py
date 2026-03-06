import traceback
import os
import bpy
import json
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper
from .fbxini_reader import FBXINIReader


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


class ImportFBXINI(bpy.types.Operator, ImportHelper):
    """Import FBX.INI -> Exporter settings.json"""
    bl_idname = 'importer.fbx_ini'
    bl_label = 'Import FBX.ini'
    filename_ext = '.ini'
    filter_glob: StringProperty(default='*.ini', options={'HIDDEN'})

    def execute(self, context) -> set:
        try:
            reader = FBXINIReader(self.filepath)
            reader.parse_ini()
            reader.convert_sections_to_json()

            json_path = os.path.join(os.path.dirname(self.filepath), 'settings.json')
            reader.save_json(json_path)

            bpy.ops.importer.report_message(
                'INVOKE_DEFAULT',
                is_error=False,
                title='Import Successful',
                message=(
                    f'Settings imported from:\n{self.filepath}\n'
                    f'Exported JSON to:\n{json_path}\n'
                    f'Processed {reader.applied_mats} materials and {reader.applied_nodes} nodes.'
                )
            )
        except Exception:
            import traceback
            error = traceback.format_exc()
            bpy.ops.importer.report_message(
                'INVOKE_DEFAULT',
                is_error=True,
                title='Import Failed',
                message=error
            )
            return {'CANCELLED'}

        return {'FINISHED'}


def menu_func_import(self, context: bpy.types.Context):
    self.layout.operator(
        ImportFBXINI.bl_idname,
        text='Assetto Corsa Persistence (fbx.ini) -> Settings (.json)'
    )


REGISTER_CLASSES: tuple = (
    ReportOperator,
    CopyClipboardButtonOperator,
    ImportFBXINI
)


def register():
    for cls in REGISTER_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    for cls in reversed(REGISTER_CLASSES):
        bpy.utils.unregister_class(cls)
