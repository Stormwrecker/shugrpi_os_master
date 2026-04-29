"""
The official SHUGRPi Operating System
designed specifically for the SHUGRPi

Code and Assets by Stormwrecker
All Rights Reserved
"""

# get necessary utilities
from utils import *
from constants import *
import os
import sys

# initialize Compatibilty Manager
c = CompatibilityManager()
is_shugrpi, base_path, os.environ = c.init()

# import pygame
import pygame
from pygame.locals import *

# pygame-ce check
if hasattr(pygame, "IS_CE"):
    logger.info("Successfully loaded pygame-ce")
    is_ce = True
else:
    logger.warning("SHUGRPi requires pygame-ce: got pygame instead")
    logger.warning("Certain features will be unavailable")
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

# create window
flags = NOFRAME | FULLSCREEN | SCALED if is_shugrpi else NOFRAME
screen = pygame.display.set_mode((DISPLAY_WIDTH, DISPLAY_HEIGHT), flags)

# load all images
master_images = preload_images()

# main ui group
ui_group = pygame.sprite.Group()


# generic UI element
class UiElement(pygame.sprite.Sprite):
    def __init__(self, label, x, y, row, col, padding=8):
        pygame.sprite.Sprite.__init__(self, ui_group)
        self.row = row
        self.col = col

        pre_rect = pygame.Rect((x, y, 10, 10))

        self.text = Text(label, pre_rect.centerx, pre_rect.centery, WHITE, padding, centered=True)
        r = self.text.rect
        self.rect = pygame.Rect((r.x - padding//2, r.y - padding//2, r.width + padding, r.height + padding))

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

        return self.games

    def sort_games(self, sort_type, reversed=False):
        """0 - size, 1 - last_played"""
        if sort_type <= len(self.sort_types):
            sort_key = self.sort_types[sort_type]

            temp_dict = self.games.copy()
            self.games = dict(sorted(temp_dict.items(), key=lambda game: game[1][sort_key], reverse=reversed))

        return self.games


# main SHUGRPi OS app
class ShugrPiOS:
    def __init__(self, is_shugrpi, master_images):
        """ Master class for the SHUGRPi Operating System """
        self.is_shugrpi = is_shugrpi
        logger.info(f"Running on SHUGRPi: {'yes' if is_shugrpi else 'no'}")

        """ window/display setup """
        self.screen = screen
        self.display = pygame.Surface((DISPLAY_WIDTH, DISPLAY_HEIGHT)).convert()
        pygame.display.set_icon(master_images["icon"])
        self.display_info = pygame.display.Info()
        logger.info("Video Driver: " + pygame.display.get_driver().capitalize())
        logger.info("Hardware acceleration: " + str(bool(self.display_info.hw)))
        logger.info("Video memory: " + str(self.display_info.video_mem))
        logger.info("Initialized display")

        """ time setup """
        self.clock = pygame.time.Clock()
        self.timers = {}

        """ manager setup """
        self.gm = GameManager()
        self.am = AudioManager(logger, self.is_shugrpi)

        """ asset setup """
        self.fail_image = master_images["fail_load"]

        self.original_logo_img = self.get_image("logo")
        self.logo_img = pygame.transform.scale(self.original_logo_img, (int(165 * 3), int(165 * 3)))
        self.big_logo_img = pygame.transform.scale(self.original_logo_img, (int(165 * 4), int(165 * 4)))
        self.logo_alpha = 0
        self.logo_img.set_alpha(self.logo_alpha)

        self.timers["logo"] = Timer(120)
        self.timers["start"] = Timer(180)

        """ utility setup """
        self.internet_connection = check_internet_status()
        self.stop_event = threading.Event()
        self.wifi_lock = threading.Lock()
        self.wifi_thread = threading.Thread(target=self.update_internet_connection, daemon=True)
        self.wifi_thread.start()

        """ games setup """
        self.master_games_path = os.path.join(base_path, GAME_PATH)
        self.games = self.gm.scan_games(self.master_games_path)
        self.games = self.gm.sort_games(1, True)

        """ master phase variable """
        self.master_phase = -1

        """ master running variable """
        self.running = True

    def update_internet_connection(self):
        try:
            while not self.stop_event.wait(3):
                with self.wifi_lock:
                    self.internet_connection = check_internet_status()
        except Exception as e:
            logger.error(f"Failed to update internet status: {e}")

    def check_for_updates(self):
        pass

    def run_updates(self):
        pass

    def run(self):
        while self.running:
            try:
                self.update()
                self.events()
                self.draw()
            except (Exception, KeyboardInterrupt) as e:
                if isinstance(e, Exception):
                    logger.error(f"SHUGRPi has crashed due to the following error: {e}")
                self.shutdown()

    def update(self):
        # tick clock
        dt = self.clock.tick(FPS) / 1000 * FPS

        if self.master_phase == -1:
            if not self.timers["start"].update(dt):
                if self.timers["start"].value <= 120:
                    if self.logo_alpha < 255:
                        self.logo_alpha += 5 * dt
                    else:
                        self.logo_alpha = 255
                        self.am.play_sound("logo")
            else:
                if not self.timers["logo"].update(dt):
                    if self.timers["logo"].value <= 90:
                        if self.logo_alpha > 0:
                            self.logo_alpha -= 5 * dt
                        else:
                            self.logo_alpha = 0
                else:
                    if self.logo_alpha == 0:
                        self.master_phase = 0
                        self.logo_alpha = 0
                        logger.info("Finished initializing ShugrPi OS")
                        logger.info("Running main loop")

    def events(self):
        # handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.shutdown()
            if event.type == pygame.KEYDOWN:
                # shutdown
                if event.key == pygame.K_ESCAPE:
                    self.shutdown()

    def draw(self):
        if self.master_phase == -1:
            self.display.fill(DARKER_GRAY)
            self.logo_img.set_alpha(int(self.logo_alpha))
            self.display.blit(self.logo_img, (
            half_display_x - self.logo_img.get_width() // 2, half_display_y - self.logo_img.get_height() // 2))

        elif self.master_phase == 0:
            # fill screen with dark gray
            self.display.fill(DARK_GRAY)

        self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), (0, 0))
        pygame.display.flip()

    def get_image(self, img):
        try:
            return master_images[img]
        except:
            return master_images["fail_load_alt"]

    def shutdown(self):
        logger.info("Shutting down...")
        self.running = False
        pygame.quit()
        self.stop_event.set()
        self.wifi_thread.join()
        logger.info("Shutdown complete!")
        sys.exit()


# start up SHUGRPi OS
shugrpi_os = ShugrPiOS(is_shugrpi, master_images)
shugrpi_os.run()
