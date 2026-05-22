import os
import sys

# Add parent directory to sys.path so we can import original modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydd import PyDD
from vision_core import VisionCore
from build_config import BuildConfig

# Note: In a production app, the dll path and other settings should be configurable.
# Here we initialize the global dependencies to be shared across routers.

try:
    dd_instance = PyDD("./dd.54900.dll")
except Exception as e:
    print(f"Warning: Could not initialize PyDD: {e}")
    # Dry run fallback for testing/development
    class _DryRunDD:
        def mouse_click(self, *args, **kwargs): pass
        def mouse_move_relative(self, *args, **kwargs): pass
        def key_press(self, *args, **kwargs): pass
        def key_down(self, *args, **kwargs): pass
        def key_up(self, *args, **kwargs): pass
        def key_combination(self, *args, **kwargs): pass
    dd_instance = _DryRunDD()

vision_instance = VisionCore(roi_size=315, exe_name='Calabiyau-Win64-Shipping.exe')

def get_dd():
    return dd_instance

def get_vision():
    return vision_instance
