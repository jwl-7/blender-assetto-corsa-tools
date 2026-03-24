from . import exporter, importer, mixamo, character, ui
from .utils import register_recursive, unregister_recursive


bl_info = {
    'name':        'Assetto Corsa (.kn5) (.ksanim)',
    'version':     (1, 0, 5),
    'author':      'Thomas Hagnhofer, Paul Greveson, N Murdoch, JWL',
    'blender':     (3, 0, 0),
    'description': 'Export to Assetto Corsa KN5 and KSANIM formats',
    'location':    'File Export menu, Object properties, Material properties',
    'support':     'COMMUNITY',
    'category':    'Import-Export',
    'doc_url':     'https://github.com/jwl-7/blender-assetto-corsa-tools#readme',
    'tracker_url': 'https://github.com/jwl-7/blender-assetto-corsa-tools/issues',
}

REGISTER_CLASSES = (
    exporter,
    importer,
    mixamo,
    character,
    ui
)


def register():
    """Register all of the addon's classes."""
    register_recursive(REGISTER_CLASSES)

def unregister():
    """Unregister all of the addon's classes."""
    unregister_recursive(REGISTER_CLASSES)


if __name__ == '__main__':
    register()
