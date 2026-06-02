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
screen_width, screen_height = (DISPLAY_WIDTH, DISPLAY_HEIGHT)
half_display_x = DISPLAY_WIDTH // 2
half_display_y = DISPLAY_HEIGHT // 2

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
