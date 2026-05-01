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
pygame.display.set_icon(master_images["icon"])

# groups
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


# game object
class Game(pygame.sprite.Sprite):
    def __init__(self, configs, index, x, y, wheel_rect, angle):
        self._init_metadata(configs)

        self.z_depth = 0
        self.wheel_rect = wheel_rect

        self.base_angle = angle
        self.angle = angle

        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.transform.scale(self.thumbnail, (150, 200))
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

        self.index = index
        self.selected = False

    def _init_metadata(self, configs):
        self.name = configs["name"]
        self.root_path = configs["root_path"]

        self.size = configs["size"]
        self.last_played_raw = configs["last_played_raw"]
        self.last_played = configs["last_played"]

        self.exec_type = configs["exec_type"]
        self.use_venv = configs["use_venv"]
        self.python_version = configs.get("python_version")

        self.thumbnail = load_thumbnail(os.path.join(self.root_path, configs["thumbnail"]), master_images["fail_load"])

        self.executable = configs["executable"]

    def update(self, index, angle):
        current_angle = self.base_angle + math.radians(angle)

        # center rect based on wheel_ui pos
        self.rect.midbottom = (int(math.cos(current_angle) * self.wheel_rect.width) + self.wheel_rect.centerx,
                               int(math.sin(current_angle) * self.wheel_rect.height) + self.wheel_rect.centery + 40)

        self.z_depth = math.sin(current_angle) + 2

        if self.index == index:
            self.selected = True
        else:
            self.selected = False

    def execute(self):
        return self.executable

    def draw(self, display):
        display.blit(self.image, self.rect)


# game manager
class GameManager:
    def __init__(self):
        self.games = []

        self.game_titles = []
        self.sort_types = ["size", "last_played_raw"]

    @staticmethod
    def _setup_placeholder(path):
        logger.warning(f"Valid game directory does not exist in {path}")

        os.makedirs(os.path.join(path, "placeholder"))
        with open(os.path.join(path, "placeholder", "main.py"), "w") as f:
            f.write('raise Exception("not a real game")')


        with open(os.path.join(path, "placeholder", "game_config.json"), "w") as f:
            pygame.image.save(load_image("placeholder_thumb.png"), os.path.join(path, "placeholder", "thumbnail.png"))
            f.write('{"name": "Placeholder", "thumbnail": "thumbnail.png", "run_type": ".py", "use_venv": 0}')

        logger.info(f"Created game directory in {path}")

    def load_games(self, path):
        # create master games directory
        if not os.path.exists(path):
            self._setup_placeholder(path)

        # get all directories
        all_dirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        if len(all_dirs) <= 0:
            self._setup_placeholder(path)
            all_dirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]

        # temporary list for games' data
        all_games_data = []

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

            # configuration data for games
            config_data = DEFAULT_GAME_CONFIG.copy()

            # if a valid game is encountered
            if game_app:
                logger.info(f"Detected valid game: '{d}'")

                # get config file
                config_file = os.path.join(path, d, "game_config.json")

                # if file does not exist, make one
                if not os.path.exists(config_file):
                    logger.error(f"'{d}' configurations do not exist; Reverting to default")
                    with open(config_file, "w") as f:
                        json.dump(DEFAULT_GAME_CONFIG, f)

                # if file does exist, read it
                else:
                    logger.info(f"Detected configurations in '{d}'")
                    with open(config_file, "r") as f:
                        config_data = json.load(f)

                # set configurations
                config_data["root_path"] = os.path.join(path, d)
                config_data["executable"] = game_app
                game_info = get_game_info(os.path.join(path, d), game_app)

                config_data["size"] = game_info["size"]
                config_data["last_played_raw"] = game_info["last_played_raw"]
                config_data["last_played"] = game_info["last_played"]

                # add game/configuration to games
                all_games_data.append(config_data)

        return all_games_data

    def sort_games(self, sort_type, reversed=False):
        """0 - size, 1 - last_played"""
        if sort_type < len(self.sort_types):
            sort_key = self.sort_types[sort_type]

            games_copy = self.games.copy()
            self.games = sorted(games_copy, key=lambda game: game.__dict__[sort_key], reverse=reversed)

        return self.games


# game wheel object
class GameWheelUi:
    def __init__(self, x, y, w, h, g):
        self.rect = pygame.Rect((x, y, w, h))
        self.rect.center = (x, y)

        self.shadow_rect = pygame.Rect((self.rect.centerx - (w * 1.5),
                                        self.rect.centery - 20, w * 3, h * 2))

        # angles and indices
        self.master_index = 0
        self.target_index = 0
        self.master_angle = 0
        self.target_angle = 0
        self.bottom_angle = math.radians(90)

        # get games' data
        self.all_games_data = g

        # all games
        self.games = []

        # get angles for even spacing
        self.item_angle = 0
        self.num_items = len(self.all_games_data)
        self.angle_increment = 360 / self.num_items if self.num_items > 0 else 0

        # add games to wheel
        for index, data in enumerate(self.all_games_data):
            self.item_angle = math.radians(self.angle_increment * index + 90)
            x = int(math.cos(self.item_angle) * self.rect.width) + self.rect.centerx
            y = int(math.sin(self.item_angle) * self.rect.height) + self.rect.centery
            self.games.append(Game(data, index, x, y, self.rect, self.item_angle))

    def get_games(self):
        return self.games

    def update(self, dt):
        # adjust target values
        self.master_index = self.target_index
        self.target_angle = self.angle_increment * self.target_index

        # normalize target_angle to prevent floating-point overflow
        self.target_angle %= 360

        # smoothly interpolate towards target_angle
        angle_diff = (self.target_angle - self.master_angle) % 360
        if angle_diff > 180:
            angle_diff -= 360

        if abs(angle_diff) > dt * 0.15:
            self.master_angle += (angle_diff * 0.15) * dt
        else:
            self.master_angle = self.target_angle

        # Keep master_angle normalized
        self.master_angle %= 360

        for game in self.games:
            game.update(self.master_index, self.master_angle)

    def update_index(self, delta, audio_manager):
        self.target_index += delta
        self.target_index %= self.num_items
        audio_manager.play_sound("menu_swish", False)

    def draw(self, display):
        pygame.draw.ellipse(display, GRAY, self.shadow_rect)
        sorted_sprites = sorted(self.games, key=lambda x: x.z_depth)
        for sprite in [s for s in sorted_sprites if s.z_depth < 2.0]:
            display.blit(sprite.image, sprite.rect)
        for sprite in [s for s in sorted_sprites if s.z_depth >= 2.0]:
            display.blit(sprite.image, sprite.rect)


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
        logger.info("Initialized display")

        """ time setup """
        self.clock = pygame.time.Clock()
        self.timers = {}

        """ manager setup """
        self.am = AudioManager(logger, self.is_shugrpi)
        self.gm = GameManager()

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
        self.wifi_thread = threading.Thread(name="SHUGRPi Internet Updater", target=self.update_internet_connection, daemon=True)
        self.wifi_thread.start()

        """ games setup """
        self.master_games_path = os.path.join(base_path, GAME_PATH)
        all_games_data = self.gm.load_games(self.master_games_path)
        self.game_wheel = GameWheelUi(half_display_x, half_display_y + 60, 175, 55, all_games_data)

        """ master phase variable """
        self.master_phase = -1
        self.dt = 1

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

    def sort_games(self, sort_type, reversed=False):
        self.games = self.gm.sort_games(sort_type, reversed)

    def run(self):
        while self.running:
            self.update()
            self.events()
            self.draw()

            try:
                pass
            except (Exception, KeyboardInterrupt) as e:
                if isinstance(e, Exception):
                    logger.error(f"SHUGRPi has crashed due to the following error: {e}")
                self.shutdown()

    def update(self):
        # tick clock
        raw_dt = self.clock.tick(FPS) / 1000.0 * 60

        self.dt = self.dt * 0.9 + raw_dt * 0.1
        dt = self.dt

        if self.master_phase == -1:
            if not self.timers["start"].update(dt):
                if self.logo_alpha < 255:
                    self.logo_alpha += 5 * min(dt, 1)
                else:
                    self.logo_alpha = 255
                    self.am.play_sound("logo")
            else:
                if not self.timers["logo"].update(dt):
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

        elif self.master_phase == 0:
            self.game_wheel.update(dt)

    def events(self):
        global FPS
        # handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.shutdown()
            if event.type == pygame.KEYDOWN:
                # shutdown
                if event.key == pygame.K_ESCAPE:
                    self.shutdown()
                if event.key == pygame.K_SPACE:
                    self.test()
                if event.key == pygame.K_RETURN:
                    FPS = 30
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_RETURN:
                    FPS = 60

    def draw(self):
        if self.master_phase == -1:
            self.display.fill(DARKER_GRAY)
            self.logo_img.set_alpha(int(self.logo_alpha))
            self.display.blit(self.logo_img, (
            half_display_x - self.logo_img.get_width() // 2, half_display_y - self.logo_img.get_height() // 2))

        elif self.master_phase == 0:
            # fill screen with dark gray
            self.display.fill(DARK_GRAY)

            self.game_wheel.draw(self.display)

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

    def test(self):
        self.game_wheel.update_index(1, self.am)


# start up SHUGRPi OS
shugrpi_os = ShugrPiOS(is_shugrpi, master_images)
shugrpi_os.run()
