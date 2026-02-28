from inspect import isclass
from typing import Iterable, Any
import bpy


def register_recursive(objects: Iterable[Any]):
    """Registers classes with Blender recursively from modules."""
    for obj in objects:
        if isclass(obj):
            bpy.utils.register_class(obj)
        elif hasattr(obj, 'register'):
            obj.register()
        elif hasattr(obj, 'REGISTER_CLASSES'):
            register_recursive(obj.REGISTER_CLASSES)
        else:
            print(f"Warning: Failed to find anything to register for '{obj}'")

def unregister_recursive(objects: Iterable[Any]):
    """Unregisters classes from Blender recursively from modules."""
    for obj in reversed(list(objects)):
        if isclass(obj):
            bpy.utils.unregister_class(obj)
        elif hasattr(obj, 'unregister'):
            obj.unregister()
        elif hasattr(obj, 'REGISTER_CLASSES'):
            unregister_recursive(obj.REGISTER_CLASSES)
        else:
            print(f"Warning: Failed to find anything to unregister for '{obj}'")
