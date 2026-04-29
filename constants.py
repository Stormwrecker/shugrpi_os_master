"""Constants for the SHUGRPi OS"""

FPS = 60
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


DISPLAY_WIDTH, DISPLAY_HEIGHT = (800, 480)
screen_width, screen_height = (DISPLAY_WIDTH, DISPLAY_HEIGHT)
half_display_x = DISPLAY_WIDTH // 2
half_display_y = DISPLAY_HEIGHT // 2

GAME_PATH = "games"

DEFAULT_DISPLAY_CONFIG = {"name": "Name Not Available",
                          "thumbnail": 0,
                          "run_type": ".py",
                          "use_venv": 0,
                          "python_version": "3.13"}
