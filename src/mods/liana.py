import sys
import os

from io import StringIO


from ..utils import valorant, blender, common
from ..utils.importer_xay import *

logger = common.setup_logger(__name__)
stdout = StringIO()

try:
    sys.dont_write_bytecode = True
    from ..tools import injector
except:
    pass

def import_valorant_map(addon_prefs):

    os.system("cls")
    liana = valorant.Liana(addon_prefs)

    if (not addon_prefs.isInjected) and addon_prefs.usePerfPatch:
        injector.inject_dll(os.getpid(), liana.prefs.dll_path.__str__())
        addon_prefs.isInjected = True

    #  Check if the game files are exported
    liana.extract_assets()

    # Clear the scene
    blender.clean_scene()

    # Import the shaders
    liana.import_shaders()

    # Start the map import
    liana.run()

    logger.info("Finished!")
