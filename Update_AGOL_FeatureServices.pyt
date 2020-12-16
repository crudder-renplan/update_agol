# -*- coding: utf-8 -*-

from pathlib import Path
import sys

tool_dir = Path(__file__).parent
scripts_dir = str(Path(tool_dir, 'scripts'))
sys.path.append(scripts_dir)

# Do not compile .pyc files for the tool modules.
sys.dont_write_bytecode = True

from UpdateAGOL import UpdateAGOL

# if 'UpdateAGOL' in sys.modules:
#     import importlib
#     importlib.reload(UpdateAGOL)


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "UpdateAGOLfeatureService"
        self.alias = "Update AGOL Feature Service"

        # List of tool classes associated with this toolbox
        self.tools = [UpdateAGOL]