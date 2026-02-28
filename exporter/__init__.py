# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import traceback
import os
import bpy
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
    bl_idname = "kn5.report_message"
    bl_label = "Export report"

    is_error: BoolProperty()
    title: StringProperty()
    message: StringProperty()

    def execute(self, context):
        if self.is_error:
            self.report({'WARNING'}, self.message)
        else:
            self.report({'INFO'}, self.message)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.execute(context)
        return context.window_manager.invoke_popup(self, width=600)

    def draw(self, context):
        if self.is_error:
            self.layout.alert = True
        row = self.layout.row()
        row.alignment = "CENTER"
        row.label(text=self.title)
        for line in self.message.splitlines():
            row = self.layout.row()
            line = line.replace("\t", " " * 4)
            row.label(text=line)
        row = self.layout.row()
        row.operator("kn5.report_clipboard").content = self.message


class CopyClipboardButtonOperator(bpy.types.Operator):
    bl_idname = "kn5.report_clipboard"
    bl_label = "Copy to clipboard"

    content: StringProperty()

    def execute(self, context):
        context.window_manager.clipboard = self.content
        return {'FINISHED'}

    def invoke(self, context, event):
        self.execute(context)
        return {'FINISHED'}


class KN5FileWriter(KN5Writer):
    def __init__(self, file, context, settings, filepath, warnings):
        super().__init__(file)
        self.context, self.settings, self.warnings, self.filepath = context, settings, warnings, filepath
        self.file_version = 5

    def write(self):
        self.file.write(KN5_HEADER_BYTES)
        self.write_uint(self.file_version)
        TextureWriter(self.file, self.context, self.settings, self.filepath, self.warnings).write()
        material_writer = MaterialWriter(self.file, self.context, self.settings, self.warnings)
        material_writer.write()
        NodeWriter(self.file, self.context, self.settings, self.warnings, material_writer).write()


class ExportKN5(bpy.types.Operator, ExportHelper):
    """Export to Assetto Corsa 3D object format (.kn5)"""

    bl_idname = "exporter.kn5"
    bl_label = "Export KN5"
    filename_ext = ".kn5"

    def execute(self, context):
        warnings = []
        try:
            with open(self.filepath, "wb") as f:
                settings = read_settings(self.filepath)
                KN5FileWriter(f, context, settings, self.filepath, warnings).write()
                bpy.ops.kn5.report_message('INVOKE_DEFAULT', is_error=False, title="Exported successfully", message=os.linesep.join(warnings))
        except:
            error = traceback.format_exc()
            try: os.remove(self.filepath)
            except: pass
            bpy.ops.kn5.report_message('INVOKE_DEFAULT', is_error=True, title="Export failed", message=error)
        return {'FINISHED'}


class ExportKSAnim(bpy.types.Operator, ExportHelper):
    """Export to Assetto Corsa animation format (.ksanim)"""

    bl_idname = "exporter.ksanim"
    bl_label = "Export KSANIM"
    filename_ext = ".ksanim"
    filter_glob: StringProperty(default="*.ksanim;*.knh", options={"HIDDEN"})

    selection_type: EnumProperty(
        items=(
            ("use_all", "All Objects", "Export all visible objects"),
            ("use_selection", "Selected Objects", "Export selected objects"),
            ("use_pose_bones", "Selected Bones", "Export selected bones"),
        ),
        name="Use", default="use_all"
    )
    reverse_animation: BoolProperty(name="Reverse Animation", default=False)
    add_colons: BoolProperty(name="Fix DRIVER: Objects", default=False)
    export_base_pos: BoolProperty(name="Export driver_base_pos.knh", default=False)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "selection_type")
        layout.prop(self, "reverse_animation")
        layout.prop(self, "add_colons")
        layout.prop(self, "export_base_pos")

    def execute(self, context):
        warnings = []
        try:
            with open(self.filepath, "wb") as f:
                if self.export_base_pos:
                    KNHWriter(f, context, self.filepath, self.selection_type, self.add_colons, warnings).write()
                else:
                    KSAnimWriter(f, context, self.filepath, self.selection_type, self.reverse_animation, self.add_colons, warnings).write()
            bpy.ops.kn5.report_message('INVOKE_DEFAULT', is_error=False, title="Exported successfully", message=os.linesep.join(warnings))
        except:
            error = traceback.format_exc()
            try: os.remove(self.filepath)
            except: pass
            bpy.ops.kn5.report_message('INVOKE_DEFAULT', is_error=True, title="Export failed", message=error)
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(ExportKN5.bl_idname, text="AC 3D (.kn5)")
    self.layout.operator(ExportKSAnim.bl_idname, text="AC Anim (.ksanim)")


REGISTER_CLASSES = (ReportOperator, CopyClipboardButtonOperator, ExportKN5, ExportKSAnim)


def register():
    for cls in REGISTER_CLASSES: bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)
    for cls in reversed(REGISTER_CLASSES): bpy.utils.unregister_class(cls)
