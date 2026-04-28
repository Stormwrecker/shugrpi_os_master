"""
The official SHUGRPi Operating System
designed specifically for the SHUGRPi

Code and Assets by Stormwrecker
All Rights Reserved
"""
import sys

# import utilities
from utils import *
from constants import *
import os
import platform


# initialize Compatibilty Manager
c = CompatibilityManager()
is_shugrpi, base_path, os.environ = c.init()


# import pygame
import pygame
if hasattr(pygame, "IS_CE"):
    logger.info("Successfully loaded pygame-ce")
    is_ce = True
else:
    logger.warning("SHUGRPi requires pygame-ce: got pygame instead")
    logger.warning("Certain features are unavailable")
    is_ce = False

# import other modules
import subprocess
import threading
import time
import json
import math
import random
from shutil import rmtree

# initialize pygame
pygame.init()

# setup audio handler
a = AudioManager(logger, is_shugrpi)


# setup window and display sizes
display_width, display_height = (800, 480)
screen_width, screen_height = (display_width, display_height)
half_display_x = display_width // 2
half_display_y = display_height // 2
screen = pygame.display.set_mode((display_width, display_height))
display = pygame.Surface((display_width, display_height)).convert()

clock = pygame.time.Clock()


fail_image = pygame.image.load(os.path.join(base_path, "images", "fail_load.png")).convert()


# shutdown method
def shutdown():
    pygame.quit()
    sys.exit()


# main ui group
ui_group = pygame.sprite.Group()


# generic UI element
class UiElement(pygame.sprite.Sprite):
    def __init__(self, label, x, y, row, col, width=50, height=20):
        pygame.sprite.Sprite.__init__(self, ui_group)
        self.row = row
        self.col = col

        self.width = width
        self.height = height
        self.rect = pygame.Rect((x, y, width, height))

        self.text = Text(label, self.rect.centerx, self.rect.centery, WHITE, 8, centered=True)

        self.selected = False

    def update(self, col, row):
        self.selected = False
        if row == self.row and col == self.col:
            self.selected = True

    def action(self):
        pass

    def draw(self, display):
        if self.selected:
            pygame.draw.rect(display, WHITE, self.rect, 3)
        self.text.draw(display)


# UI Manager
class UiManager:
    def __init__(self, ui_group):
        """
        Manager for navigating in-game UI with keyboard input

        UI elements are organized first by row (y dimension) then column (x dimension)
        """

        self.ui_group = sorted(ui_group, key=lambda ui: [ui.row, ui.col])

        self.master_ui_dict = {}
        for ui in self.ui_group:
            if ui.row not in self.master_ui_dict:
                self.master_ui_dict[ui.row] = []
            self.master_ui_dict[ui.row].append(ui)

        self.master_ui_list = []
        for val in self.master_ui_dict.values():
            self.master_ui_list.extend(val)

        self.x_index = 0
        self.y_index = 0

    def update(self):
        for ui in self.master_ui_list:
            ui.update(self.x_index, self.y_index)

    def change_col(self, val):
        self.x_index += val
        if self.x_index >= len(self.master_ui_dict[self.y_index]):
            self.change_row(1)
            self.x_index = 0
        elif self.x_index < 0:
            self.change_row(-1)
        self.x_index %= len(self.master_ui_dict[self.y_index])

    def change_row(self, val):
        self.y_index += val
        self.y_index %= len(self.master_ui_dict)

    def draw(self, display):
        for ui in self.master_ui_list:
            ui.draw(display)


# game manager
class GameManager:
    def __init__(self):
        self.games = {}
        self.game_titles = []

        self.sort_types = ["size", "last_played_raw"]

    def setup_placeholder(self, path):
        logger.warning(f"Valid game directory does not exist in {path}")

        os.makedirs(os.path.join(path, "placeholder"))
        with open(os.path.join(path, "placeholder", "main.py"), "w") as f:
            f.write('raise Exception("not a real game")')
            f.close()

        with open(os.path.join(path, "placeholder", "game_config.json"), "w") as f:
            pygame.image.save(load_image("placeholder_thumb.png"), os.path.join(path, "placeholder", "thumbnail.png"))
            f.write('{"name": "Placeholder", "thumbnail": "thumbnail.png", "run_type": ".py", "use_venv": 0}')
            f.close()

        logger.info(f"Created game directory in {path}")

    def scan_games(self, path):
        # create master games directory
        if not os.path.exists(path):
            self.setup_placeholder(path)

        # get all directories
        all_dirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        if len(all_dirs) <= 0:
            self.setup_placeholder(path)
            all_dirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]

        # get all valid games
        for d in all_dirs:
            # possible game paths
            main_game_py = os.path.join(path, d, "main.py")
            main_game_bin = os.path.join(path, d, "main.bin")

            # get game app type
            game_app = None
            if os.path.exists(main_game_py):
                game_app = main_game_py
            elif os.path.exists(main_game_bin):
                game_app = main_game_bin
            else:
                continue

            # configuration data for displaying games in UI
            config_data = DEFAULT_DISPLAY_CONFIG

            # if a valid game is encountered
            if game_app:
                logger.info(f"Detected valid game: '{d}'")

                # get config file
                config_file = os.path.join(path, d, "game_config.json")

                # if file does not exist, make one
                if not os.path.exists(config_file):
                    logger.error(f"'{d}' configurations do not exist; Reverting to default")
                    with open(config_file, "w") as f:
                        json.dump(DEFAULT_DISPLAY_CONFIG, f)

                # if file does exist, read it
                else:
                    logger.info(f"Detected configurations in '{d}'")
                    with open(config_file, "r") as f:
                        config_data = json.load(f)

                    # if thumbnail exists, load it
                    if config_data["thumbnail"] != DEFAULT_DISPLAY_CONFIG["thumbnail"]:
                        thumb_img = load_thumbnail(os.path.join(path, d, config_data["thumbnail"]))
                        logger.info(f"Valid thumbnail detected in '{d}'")
                    else:
                        thumb_img = fail_image
                        logger.error(f"No thumbnail detected in '{d}'. Revert to default")
                    config_data["thumbnail"] = thumb_img

                # add game/configuration to games
                self.games[d] = config_data
                self.game_titles.append(d)

                game_info = get_game_info(os.path.join(path, d), game_app)

                self.games[d]["size"] = game_info["size"]
                self.games[d]["last_played_raw"] = game_info["last_played_raw"]
                self.games[d]["last_played"] = game_info["last_played"]

    def sort_games(self, sort_type, reversed=False):
        sort_key = self.sort_types[sort_type]

        temp_dict = self.games.copy()
        temp_list = []
        sorted_games = sorted(temp_dict, key=lambda game: temp_dict[game][sort_key], reverse=reversed)
        print(sorted_games)


# test
text = Text("Hello World", 100, 100, GREEN, 10, centered=True)

game_manager = GameManager()
game_manager.scan_games("games")

game_manager.sort_games(1)
print(game_manager.games)


# make buttons
count = 0
for y in range(5):
    for x in range(4):
        UiElement(f"Btn {count}", x * 50, y * 50, y, x)
        count += 1

# ui group management
ui_manager = UiManager(ui_group)

# main loop
run = True
while run:
    # fill screen
    screen.fill(BLACK)
    display.fill(BLACK)

    """update stuff here..."""
    ui_manager.update()

    """draw stuff here..."""
    text.draw(display)
    ui_manager.draw(display)

    # handle events
    all_events = pygame.event.get()
    for event in all_events:
        if event.type == pygame.QUIT:
            run = False
            break
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                ui_manager.change_col(-1)
            if event.key == pygame.K_RIGHT:
                ui_manager.change_col(1)
            if event.key == pygame.K_UP:
                ui_manager.change_row(-1)
            if event.key == pygame.K_DOWN:
                ui_manager.change_row(1)

    # render display
    screen.blit(pygame.transform.scale(display, screen.get_size()), (0, 0))
    pygame.display.flip()

    # tick clock
    clock.tick(FPS)

# quit pygame
shutdown()
