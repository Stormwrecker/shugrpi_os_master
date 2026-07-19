"""Constants for the SHUGRPi OS"""

# version (major.minor)
VERSION = "0.9"

# frame rate
FPS = 60
SPEED = 1

# colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
ORANGE = (230, 80, 60)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (70, 70, 70)
DARK_GRAY = (40, 40, 40)
DARKER_GRAY = (30, 30, 30)
DARK_BLUE = (28, 89, 152)

# display
DISPLAY_WIDTH, DISPLAY_HEIGHT = (800, 480)
SCREEN_WIDTH, SCREEN_HEIGHT = (DISPLAY_WIDTH, DISPLAY_HEIGHT)
HALF_DISPLAY_WIDTH = DISPLAY_WIDTH // 2
HALF_DISPLAY_HEIGHT = DISPLAY_HEIGHT // 2

# main directory to house all games
GAME_PATH = "games"

"""
Game configurations (DEFAULT_GAME_CONFIG)

-- Base keys --
``name`` is the title that is displayed in the UI
``thumbnail`` is the path to the image that is displayed in the UI
``executable`` is the path to the actual executable that gets launched

-- Automatic keys (set by OS) --
``root_path`` is the main game directory
``exec_type`` is how the game will be executed (py -> Python, bin -> direct execution, etc.)
``size`` is the size of the game folder calculated in megabytes (MB)
``last_played_raw`` is the last access time of the game (in seconds)
``last_played`` is the last access time of the game (in local time)

-- Extra keys --
``use_venv`` tells the OS whether the game needs to run in its own virtual environment (Python-only)
``python_version`` is what version of Python the game requires (Python-only)
"""
DEFAULT_GAME_CONFIG = {"name": "Unknown Game",
                       "thumbnail": None,
                       "executable": None}

"""
SHUGRPi OS save data

-- Values --
``sort`` is how games were last sorted in the UI
``loaded_games`` is all the games and whether they are installed or not
``last_timestamp`` is the time when the SHUGRPi last shut off
``network`` is the network that was last connected to
"""
DEFAULT_SAVE = {"sort":0.0,
                "num_games":0,
                "loaded_games":[],
                "last_timestamp":None,
                "network":{"ssid":None, "psk-key":None}}

# messages
WELCOME_MSG = "Welcome to the SHUGRPi!"
INSTALLATION_MSG = " must be fully installed before playing. Continue? ^(this requires an internet connection)^"


# get pygame for necessary values
from pygame.locals import *

# available inputs for the SHUGRPi
INPUT_BINDINGS = {"UP":    [K_UP, HAT_UP, CONTROLLER_BUTTON_DPAD_UP],
                  "DOWN":  [K_DOWN, HAT_DOWN, CONTROLLER_BUTTON_DPAD_DOWN],
                  "LEFT":  [K_LEFT, HAT_LEFT, CONTROLLER_BUTTON_DPAD_LEFT],
                  "RIGHT": [K_RIGHT, HAT_RIGHT, CONTROLLER_BUTTON_DPAD_RIGHT],
                  "A":     [K_a, CONTROLLER_BUTTON_A],
                  "B":     [K_b, CONTROLLER_BUTTON_B],
                  "X":     [K_x, CONTROLLER_BUTTON_X],
                  "Y":     [K_y, CONTROLLER_BUTTON_Y],
                  "SELECT":[K_RSHIFT, CONTROLLER_AXIS_TRIGGERLEFT],
                  "START": [K_RETURN, CONTROLLER_BUTTON_START],
                  "POWER": [K_ESCAPE, CONTROLLER_AXIS_TRIGGERRIGHT]}
