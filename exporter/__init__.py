import traceback
import os
import bpy
from typing import Any
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy_extras.io_utils import ExportHelper
from .exporter_utils import read_settings
from .kn5_writer import KN5Writer
from .texture_writer import TextureWriter
from .material_writer import MaterialWriter
from .node_writer import NodeWriter
from .ksanim_writer import KSAnimWriter, KNHWriter
from ..utils.constants import KN5_HEADER_BYTES


class ReportOperator(bpy.types.Operator):
    """Operator to display export results or errors in a popup."""
    bl_idname = 'kn5.report_message'
    bl_label = 'Export report'

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
        row.operator('kn5.report_clipboard').content = self.message


class CopyClipboardButtonOperator(bpy.types.Operator):
    """Utility operator to copy report text to system clipboard."""
    bl_idname = 'kn5.report_clipboard'
    bl_label = 'Copy to clipboard'

    content: StringProperty()

    def execute(self, context: bpy.types.Context) -> set:
        context.window_manager.clipboard = self.content
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:
        self.execute(context)
        return {'FINISHED'}


class KN5FileWriter(KN5Writer):
    def __init__(
        self,
        file: Any,
        context: bpy.types.Context,
        settings: dict[str, Any],
        filepath: str,
        warnings: list[str]
    ):
        super().__init__(file)
        self.context: bpy.types.Context = context
        self.settings: dict[str, Any] = settings
        self.warnings: list[str] = warnings
        self.filepath: str = filepath
        self.file_version: int = 5

    def write(self):
        self.file.write(KN5_HEADER_BYTES)
        self.write_uint(self.file_version)
        TextureWriter(
            self.file,
            self.context,
            self.settings,
            self.filepath,
            self.warnings
        ).write()

        material_writer: MaterialWriter = MaterialWriter(
            self.file,
            self.context,
            self.settings,
            self.warnings
        )
        material_writer.write()

        NodeWriter(
            self.file,
            self.context,
            self.settings,
            self.warnings,
            material_writer
        ).write()


class ExportKN5(bpy.types.Operator, ExportHelper):
    """Export to Assetto Corsa 3D object format (.kn5)"""
    bl_idname = 'exporter.kn5'
    bl_label = 'Export KN5'
    filename_ext = '.kn5'

    def execute(self, context: bpy.types.Context) -> set:
        warnings: list[str] = []
        try:
            with open(self.filepath, 'wb') as f:
                settings: dict[str, Any] = read_settings(self.filepath)
                KN5FileWriter(
                    f,
                    context,
                    settings,
                    self.filepath,
                    warnings
                ).write()
                bpy.ops.kn5.report_message(
                    'INVOKE_DEFAULT',
                    is_error=False,
                    title='Exported successfully',
                    message=os.linesep.join(warnings)
                )
        except:
            error: str = traceback.format_exc()
            try:
                os.remove(self.filepath)
            except Exception as _:
                pass
            bpy.ops.kn5.report_message(
                'INVOKE_DEFAULT',
                is_error=True,
                title='Export failed',
                message=error
            )
        return {'FINISHED'}


class ExportKSAnim(bpy.types.Operator, ExportHelper):
    """Export selection to Assetto Corsa animation format (.ksanim)"""
    bl_idname = 'exporter.ksanim'
    bl_label = 'Export KSANIM'
    filename_ext = '.ksanim'
    filter_glob: StringProperty(default='*.ksanim;*.knh', options={'HIDDEN'})

    selection_type: EnumProperty(
        items=(
            ('use_all', 'All Objects', 'Export all visible objects'),
            ('use_selection', 'Selected Objects', 'Export selected objects'),
            ('use_pose_bones', 'Selected Bones', 'Export selected bones'),
        ),
        name='Use',
        default='use_all'
    )
    reverse_animation: BoolProperty(name='Reverse Animation', default=False)
    export_base_pos: BoolProperty(name='Export driver_base_pos.knh', default=False)

    def draw(self, context: bpy.types.Context):
        layout: bpy.types.UILayout = self.layout
        layout.prop(self, 'selection_type')
        layout.prop(self, 'reverse_animation')
        layout.prop(self, 'export_base_pos')

    def execute(self, context: bpy.types.Context) -> set:
        warnings: list[str] = []
        try:
            with open(self.filepath, 'wb') as f:
                if self.export_base_pos:
                    KNHWriter(
                        f,
                        context,
                        self.filepath,
                        self.selection_type,
                        warnings
                    ).write()
                else:
                    KSAnimWriter(
                        f,
                        context,
                        self.filepath,
                        self.selection_type,
                        self.reverse_animation,
                        warnings
                    ).write()
            bpy.ops.kn5.report_message(
                'INVOKE_DEFAULT',
                is_error=False,
                title='Exported successfully',
                message=os.linesep.join(warnings)
            )
        except:
            error: str = traceback.format_exc()
            try:
                os.remove(self.filepath)
            except Exception as _:
                pass
            bpy.ops.kn5.report_message(
                'INVOKE_DEFAULT',
                is_error=True,
                title='Export failed',
                message=error
            )
        return {'FINISHED'}


def menu_func(self, context: bpy.types.Context):
    """Adds Assetto Corsa options to the File > Export menu."""
    self.layout.operator(ExportKN5.bl_idname, text='Assetto Corsa 3D (.kn5)')
    self.layout.operator(ExportKSAnim.bl_idname, text='Assetto Corsa Animation (.ksanim)')


REGISTER_CLASSES: tuple = (
    ReportOperator,
    CopyClipboardButtonOperator,
    ExportKN5,
    ExportKSAnim
)


def register():
    """Register all classes and add export menu items."""
    for cls in REGISTER_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)


def unregister():
    """Unregister all classes and remove export menu items."""
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)
    for cls in reversed(REGISTER_CLASSES):
        bpy.utils.unregister_class(cls)
