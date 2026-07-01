"""
The official SHUGRPi Operating System
designed specifically for the SHUGRPi

Code and Assets by Stormwrecker
All Rights Reserved
"""

# get necessary utilities
from utils import *
from constants import *
from linux_api import *
from installation_api import *
from virtual_keyboard import *
import os
import sys

# startup meesage
logger.info(f"SHUGRPi Operating System v{VERSION}")

# initialize Compatibilty Manager
c = CompatibilityManager(logger)
is_shugrpi, base_path, os.environ = c.init()

# initialize Linux API
linux = Linux(is_shugrpi, logger)

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

# initialize pygame with necessary setups
def init_pygame():
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    logger.info("Initialized pygame-ce")
    active_driver = None

    # setup audio
    try:
        pygame.mixer.init()
        active_driver = pygame.mixer.get_driver()
        logger.info(f"Using audio driver: {active_driver}")
        return active_driver

    except Exception as e:
        drivers = ["wasapi", "alsa", "dummy"]
        for driver in drivers:
            try:
                os.environ["SDL_AUDIODRIVER"] = driver
                pygame.mixer.quit()
                pygame.mixer.init()
                active_driver = driver
                logger.info(f"Trying audio driver: {active_driver}")
                break
            except Exception as e:
                active_driver = None
                logger.error(f"Driver not available: {driver}")

    if active_driver:
        logger.info(f"Using audio driver: {active_driver}")
    else:
        logger.error("No audio drivers available")

    return active_driver


# initialize pygame
audio_driver = init_pygame()

# create window
flags = NOFRAME | FULLSCREEN | SCALED if is_shugrpi else NOFRAME
screen = pygame.display.set_mode((DISPLAY_WIDTH, DISPLAY_HEIGHT), flags)

window_title = f"SHUGRPi Operating System v{VERSION}"
pygame.display.set_caption(window_title)
pygame.display.set_allow_screensaver(False)

# load all images
master_images = preload_images()
pygame.display.set_icon(master_images["icon"])

# current time
current_time = time.strftime("%H:%M")


# screen-size curtain for transitions
class Curtain(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.color = BLACK

        self.image = pygame.Surface((1, 1)).convert_alpha()
        self.image = pygame.transform.scale(self.image, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
        self.rect = self.image.get_rect()
        self.rect.topleft = (0, 0)

        self.image.fill(self.color)

        self.alpha = 255
        self.image.set_alpha(self.alpha)

        self.flip = False
        self.target_alpha = 255

    def update(self, dt):
        if self.alpha != self.target_alpha:
            if self.alpha > self.target_alpha:
                self.alpha = max(int(self.alpha - (20 * dt)), self.target_alpha)
                self.flip = False
            elif self.alpha < self.target_alpha:
                self.alpha = min(int(self.alpha + (20 * dt)), self.target_alpha)
                self.flip = False
        else:
            if self.alpha == 255:
                self.flip = True
        self.image.set_alpha(self.alpha)

    def set_color(self, new_color):
        if self.color != new_color:
            self.image.fill(new_color)
            self.color = new_color

    def draw(self, display):
        if self.alpha:
            display.blit(self.image, self.rect)


# floating logo in background
class FloatingLogo(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.original_image = pygame.transform.scale(master_images["logo"], (int(165 * 4), int(165 * 4))).convert_alpha()
        self.start_timer = Timer(120)
        self.timer = Timer(240)
        self.wait_timer = Timer(random.randint(180, 240))
        self.reset()

    def reset(self):
        self.image = self.original_image.copy()
        self.image = pygame.transform.rotate(self.image, random.randint(-20, 20))

        self.rect = self.image.get_rect()
        self.rect.center = (random.randint(100, DISPLAY_WIDTH - 100),
                            random.randint(60, DISPLAY_HEIGHT - 60))
        self.floating_x = self.rect.x
        self.floating_y = self.rect.y

        if self.rect.centerx >= half_display_x:
            self.dx = -random.randint(5, 25) / 100
        else:
            self.dx = random.randint(5, 25) / 100

        if self.rect.centery >= half_display_y:
            self.dy = -random.randint(5, 25) / 100
        else:
            self.dy = random.randint(5, 25) / 100

        self.alpha = 0
        self.max_alpha = 30

        self.toggled = False

        self.image.set_alpha(self.alpha)

        self.timer.reset()
        self.wait_timer.reset()

    def update(self, dt):
        if self.start_timer.update(dt):
            if self.alpha < self.max_alpha and not self.toggled:
                self.alpha += dt
            else:
                self.toggled = True

        if self.toggled:
            if self.timer.update(dt):
                if self.alpha > 0:
                    self.alpha -= dt
                else:
                    self.alpha = 0
                    if self.wait_timer.update(dt):
                        self.reset()

        self.image.set_alpha(self.alpha)

        self.floating_x += self.dx * dt
        self.floating_y += self.dy * dt
        self.rect.topleft = (self.floating_x, self.floating_y)

    def draw(self, display):
        if self.alpha:
            display.blit(self.image, self.rect)


# game menu
class GameMenu(pygame.sprite.Sprite):
    def __init__(self, am, start_game_action):
        pygame.sprite.Sprite.__init__(self)
        self.height = 380
        self.width = int(self.height * 4 // 3)

        self.image = pygame.Surface((self.width, self.height)).convert()
        self.image.fill((50, 50, 50))

        self.x = DISPLAY_WIDTH + 10
        self.y = half_display_y
        self.main_rect = self.image.get_rect()
        self.main_rect.midleft = (self.x, self.y)

        self.page_image = pygame.Surface((self.width * 2, self.height // 2 + 40)).convert()
        self.page_image.fill((60, 60, 60))
        self.page_image.set_colorkey(BLACK)
        pygame.draw.polygon(self.page_image, BLACK, [[0, 0], [70, 0], [0, self.height // 2 - 30]])

        self.page_rect = self.page_image.get_rect()
        self.page_rect.topleft = (self.main_rect.x + 40, self.main_rect.y + self.height // 2 + 40)

        self.page_shadow = pygame.Surface((self.width * 2, self.height // 2 + 40)).convert()
        self.page_shadow.fill((30, 30, 30))
        self.page_shadow.set_colorkey(BLACK)
        pygame.draw.polygon(self.page_shadow, BLACK, [[0, 0], [70, 0], [0, self.height // 2 - 30]])

        self.page_shadow_rect = self.page_shadow.get_rect()
        self.page_shadow_rect.topleft = self.page_rect.topleft

        self.game = None
        self.label = Text("", 0, 0, WHITE, 0)

        self.selected = False
        self.scroll = [0, 0]
        self.target_scroll = [0, 0]

        self.x_scroll_bounds = [0, -300]
        self.toggled = False

        self.am = am

        self.ui_group = pygame.sprite.Group()
        self.options = {"Start Game":start_game_action, "Settings":None, "Back": self.toggle}
        self.all_option_data = zip(range(len(self.options)), self.options.keys(), self.options.values())

        for index, option, action in list(self.all_option_data):
            UiElement(option, self.page_rect.x, self.page_rect.y - 65 + (index * 70),
                      index, 0, size=14, group=self.ui_group, func=action)

        self.um = UiManager(self.ui_group)
        self.start_game_ui = self.um.get_ui(0, 0)
        self.status = None

    def _get_label(self, game):
        display_name = game.name or ""
        default_name = DEFAULT_GAME_CONFIG["name"]
        if len(display_name.split()) > 2:
            if display_name != default_name:
                target_character = display_name.find(" ", 9)
            else:
                target_character = display_name.find(" ", 7)
            display_name = display_name[0:target_character] + "\n" + display_name[target_character + 1:]
        temp_size = 30 if len(display_name) <= 10 else 20

        return Text(display_name, self.main_rect.x + 40, self.main_rect.top + 30, WHITE, temp_size)

    def update(self, dt):
        diff = (self.target_scroll[0] - self.scroll[0])
        if abs(diff) > 1:
            self.scroll[0] += diff * 0.15 * dt
        else:
            self.scroll[0] = self.target_scroll[0]

        self.main_rect.x = self.x + self.scroll[0]
        self.main_rect.centery = self.y + self.scroll[1]

        self.page_rect.x = self.main_rect.x + 80 + self.scroll[0] // 3
        self.page_rect.y = self.main_rect.y + self.height // 3

        self.page_shadow_rect.x = self.main_rect.x + 84 + self.scroll[0] // 3
        self.page_shadow_rect.y = self.main_rect.y + 4 + self.height // 3

        for index, ui in enumerate(self.um.ui_group):
            ui.rect.x = self.page_rect.x + 120 - (index * 30)

        self.um.update(dt)

        self.label.rect.topleft = (self.main_rect.x + 35, self.main_rect.top + 30)

    def toggle(self):
        self.toggled = not self.toggled
        if self.toggled:
            self.am.play_sound("menu_up")
            self.label = self._get_label(self.game)
            self.um.x_index = 0
            self.um.y_index = 0

            status = self._get_status()
            self.update_start_game_ui(status)

        else:
            self.am.play_sound("menu_down")
        self.target_scroll[0] = self.x_scroll_bounds[self.toggled]

    def _get_status(self):
        status = None
        if self.game.installed:
            status = 0
        elif not self.game.installed and not self.game.install_in_progress:
            status = 1
        elif not self.game.installed and self.game.install_in_progress:
            status = 2
        return status

    def update_start_game_ui(self, status):
        if self.status != status:
            # already playable
            if status == 0:
                self.start_game_ui.available = True
                self.start_game_ui.change_label("Start Game", default_font)
                self.start_game_ui.rect.x = self.page_rect.x + 120
                self.um.update(1)

            # not installed, but not installing either
            elif status == 1:
                self.start_game_ui.available = True
                self.start_game_ui.change_label("Install Game", default_font)
                self.start_game_ui.rect.x = self.page_rect.x + 120
                self.um.update(1)

            # not installed, but already installing
            elif status == 2:
                self.start_game_ui.available = False
                self.um.update(1)

            self.status = status

    def action(self):
        if self.um.active:
            ui = self.um.action()
            toggled = False
            if ui.row == 2:
                toggled = True
            return toggled

    def draw(self, display):
        display.blit(self.image, self.main_rect)
        display.blit(self.page_shadow, self.page_shadow_rect)
        display.blit(self.page_image, self.page_rect)

        self.label.draw(display)

        self.um.draw(display)


# game object
class Game(pygame.sprite.Sprite):
    def __init__(self, configs, index, x, y, wheel_rect, angle):
        self._init_metadata(configs)

        self.z_depth = 0
        self.wheel_rect = wheel_rect

        self.base_angle = angle
        self.angle = angle

        pygame.sprite.Sprite.__init__(self)
        self.original_image = pygame.transform.smoothscale(self.thumbnail, (225, 300))
        self.image = pygame.transform.scale(self.original_image, (150, 200))
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

        self.grow = self.image.get_width() - self.original_image.get_width()

        self.index = index
        self.selected = False

        self.original_gray_surf = pygame.Surface((300, 300)).convert_alpha()
        self.original_gray_surf.set_colorkey(BLACK)
        self.gray_surf = self.original_gray_surf.copy()
        self.gray_surf.fill(DARK_GRAY)
        self.gray_alpha = 150
        self.gray_surf.set_alpha(self.gray_alpha)

        self.warning_image = master_images["warning"]
        self.warning_image = pygame.transform.smoothscale_by(self.warning_image, .5)

        self.installed = self.check_install()
        self.install_in_progress = False
        self.install_step = 0
        self.status_label = Text("", self.rect.centerx, self.rect.centery, WHITE, 8, retro_font, True)

        self.update(1, self.index, self.angle, True, [0, 0])

    def _init_metadata(self, configs):
        self.name = configs["name"]
        self.root_path = configs["root_path"]

        self.size = configs["size"]
        self.last_played_raw = configs["last_played_raw"]
        self.last_played = configs["last_played"]

        self.executable = configs["executable"]
        self.exec_type = self.executable.split(".")[1]

        self.use_venv = configs.get("use_venv")
        self.python_version = configs.get("python_version")
        self.requirements = configs.get("requirements")

        if self.use_venv:
            self.python_exec = os.path.join(self.root_path, ".venv", "Scripts" if not is_shugrpi else "bin", "python.exe" if not is_shugrpi else "python")
        else:
            self.python_exec = "python"

        temp_thumb = os.path.join(self.root_path, configs["thumbnail"]) if configs.get("thumbnail") else None
        self.thumbnail = load_thumbnail(temp_thumb, master_images["fail_load"])

    def reset(self, configs, index, x, y, wheel_rect, angle):
        self._init_metadata(configs)

        self.z_depth = 0
        self.wheel_rect = wheel_rect

        self.base_angle = angle
        self.angle = angle

        self.original_image = pygame.transform.smoothscale(self.thumbnail, (225, 300))
        self.image = pygame.transform.scale(self.original_image, (150, 200))
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

        self.grow = self.image.get_width() - self.original_image.get_width()

        self.index = index
        self.selected = False

        self.update(1, self.index, self.angle, True, [0, 0])

    def update(self, dt, index, angle, wheel_selected, scroll):
        current_angle = self.base_angle + math.radians(angle)

        # center rect based on wheel_ui pos
        self.rect.midbottom = (int(math.cos(current_angle) * self.wheel_rect.width) + self.wheel_rect.centerx + scroll[0],
                               int(math.sin(current_angle) * self.wheel_rect.height) + self.wheel_rect.centery + 40 + scroll[1])

        self.z_depth = math.sin(current_angle) + 2

        if self.index == index and wheel_selected:
            self.selected = True
        else:
            self.selected = False

        self.scale_image(self.selected, dt)

        if self.install_in_progress:
            self.status_label.rect.center = self.rect.center

    def update_before_install(self):
        self.install_in_progress = True

    def update_during_install(self, step):
        if step != self.install_step:
            msg = f"Installing ({step}/3)..."
            self.status_label.set_text(msg)
            self.status_label.rect.center = self.rect.center
            self.install_step = step

    def update_after_install(self, success):
        self.install_in_progress = False
        if success:
            self.installed = True

    def scale_image(self, selected, dt):
        current_width = self.image.get_width()

        if selected:
            target_width = self.original_image.get_width()
        else:
            target_width = int(self.original_image.get_width() * 2/3)

        orig_x, orig_y = self.original_image.get_size()

        diff = abs(current_width - target_width)

        if int(diff) != 0:
            if diff > 1:
                if current_width < target_width:
                    self.grow += diff * 0.15 * dt
                else:
                    self.grow -= diff * 0.15 * dt
                size_x = orig_x + round(self.grow)
                size_y = int(size_x * 4 // 3)
            else:
                size_x = target_width
                size_y = int(size_x * 4 // 3)
            self.image = pygame.transform.smoothscale(self.original_image, (size_x, size_y))
            self.image.set_colorkey(WHITE)
            self.rect = self.image.get_rect(center=self.rect.center)
            self.gray_surf = pygame.transform.scale(self.original_gray_surf, self.rect.size)

    def check_install(self):
        return (os.path.exists(self.python_exec) and self.use_venv) or not self.use_venv

    def prepare_executable(self):
        if self.exec_type == "py":
            processes = [self.python_exec, self.executable]
            return processes, self.root_path, os.environ.copy()
        else:
            return self.executable, self.root_path, os.environ.copy()

    def draw(self, display, toggle):
        if self.selected and not toggle:
            pygame.draw.rect(display, WHITE,
                             (self.rect.x - 3, self.rect.y - 3, self.rect.width + 6, self.rect.height + 6), 6)
        display.blit(self.image, self.rect)
        if self.install_in_progress:
            self.gray_surf.fill(DARK_GRAY)
            self.gray_surf.set_alpha(self.gray_alpha)
            display.blit(self.gray_surf, self.rect)
            self.status_label.draw(display)

        if not self.install_in_progress and not self.installed:
            display.blit(self.warning_image, (self.rect.right - 35, self.rect.top + 5))


# game manager
class GameManager:
    def __init__(self):
        self.all_games_data = []
        self.log_data = []

    def reset(self):
        self.all_games_data = []
        self.log_data = []

    def _setup_placeholder(self, path):
        logger.warning(f"Valid game directory does not exist in {path}")

        os.makedirs(os.path.join(path, "placeholder"))
        with open(os.path.join(path, "placeholder", "main.py"), "w") as f:
            f.write('raise Exception("not a real game")')

        with open(os.path.join(path, "placeholder", "game_config.json"), "w") as f:
            pygame.image.save(load_image("placeholder_thumb.png"), os.path.join(path, "placeholder", "thumbnail.png"))
            f.write(json.dumps(DEFAULT_GAME_CONFIG))

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

        # padding
        self.padding = 0
        self.paddings = []

        # get all valid games
        for d in all_dirs:

            # flags for logging
            is_valid = False
            is_config = False
            is_installed = False

            # configuration data for games
            config_data = DEFAULT_GAME_CONFIG.copy()

            # get config file
            config_file = os.path.join(path, d, "game_config.json")

            # pre-read configuration file if existing
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    config_data = json.load(f)

            # possible game paths
            if config_data.get("executable"):
                main_game = os.path.join(path, d, *os.path.split(config_data["executable"]))
            else:
                for i in ["py", "bin"]:
                    main_game = os.path.join(path, d, f"main.{i}")
                    if os.path.exists(main_game):
                        break

            # get game app type
            game_app = None
            if os.path.exists(main_game):
                game_app = main_game
                # set config name to whatever the folder name is
                if config_data["name"] == DEFAULT_GAME_CONFIG["name"]:
                    config_data["name"] = d.title()
            else:
                # set padding
                self.padding = max(self.padding, len(d))
                self.paddings.append(len(d))

                # add folder to log
                self.log_data.append(
                    f"|  {d}^{is_valid}+N/A    +N/A        |")
                continue

            # if a valid game is encountered
            if game_app:
                is_valid = True

                # if file does not exist, make one
                if not os.path.exists(config_file):
                    with open(config_file, "w") as f:
                        json.dump(config_data, f)

                # check if configurations are custom
                for k, v in DEFAULT_GAME_CONFIG.items():
                    if k != "name":
                        if config_data[k] != v:
                            is_config = True

                # set necessary configurations
                config_data["root_path"] = os.path.join(path, d)
                config_data["executable"] = game_app
                game_info = get_game_info(os.path.join(path, d), game_app)

                # check if game has been installed based on venv's presence
                venv_path = os.path.join(path, d, ".venv")
                requirements_path = os.path.join(path, d, "requirements.txt")
                if os.path.exists(venv_path) or not config_data.get("use_venv"):
                    is_installed = True
                elif not os.path.exists(venv_path) and config_data.get("use_venv"):
                    if os.path.exists(requirements_path):
                        config_data["requirements"] = requirements_path

                # set unneccessary configurations
                config_data["size"] = game_info["size"]
                config_data["last_played_raw"] = game_info["last_played_raw"]
                config_data["last_played"] = game_info["last_played"]

                # set padding
                self.padding = max(self.padding, len(d))
                self.paddings.append(len(d))

                # add game/configuration to games
                self.all_games_data.append(config_data)

            # add data to log table
            self.log_data.append(f"|  {d}^{is_valid} +{is_config}  +" + (" " if is_config else "") + f"{is_installed}" + (" " if is_installed else "") + "      |")

        # generate summary table in logging
        self._generate_log_table()

        return self.all_games_data

    def _generate_log_table(self):
        for i, log in enumerate(self.log_data.copy()):
            step_0 = log
            step_1 = step_0.replace("^", " " * (26 - self.paddings[i]))
            self.log_data[i] = step_1.replace("+", " " * 8)

        header = "*---Folder" + "-" * (self.padding - 2) + "Game" + "-" * 8 + "Config" + "-" * 8 + "Installed" + "-" * 4 + "*"
        logger.info("Detected the folders listed below:".center(len(header)))
        logger.info(header)

        for log in self.log_data:
            logger.info(log)

        logger.info("*" + "-" * (len(header) - 2) + "*")


# game wheel object
class GameWheelUi(UiElement):
    def __init__(self, x, y, w, h, games, group):
        UiElement.__init__(self, None, x, y, 1, 0, group=group)

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
        self.lowest_game = None

        # get games' data
        self.all_games_data = games

        # all games
        self.games = []
        self.sort_types = ["name", "size", "last_played_raw"]
        self.sort_names = {"name":"Name", "size":"Size", "last_played_raw":"Last Played"}
        self.sort_index = 0
        self.reverse_sort = False

        # get angles for even spacing
        self.item_angle = 0
        self.num_items = len(self.all_games_data)
        self.angle_increment = 360 / self.num_items if self.num_items > 0 else 0

        self.first_load = True
        self.reload_games()

        # scroll values
        self.scroll = [0, 0]
        self.target_scroll = [0, 0]

        self.setup_ellipses()

        self.game_label = Text(str(self.games[self.master_index].name), half_display_x,
                               DISPLAY_HEIGHT - 13, WHITE, 12, centered=True)

        self.selected = [True, True]

        self.curtain = pygame.Surface((1, 1)).convert_alpha()
        self.curtain = pygame.transform.scale(self.curtain, (DISPLAY_WIDTH, DISPLAY_HEIGHT - 60))
        self.curtain_rect = self.curtain.get_rect()
        self.curtain_rect.topleft = (0, 30)

        self.curtain.fill(DARKER_GRAY)

        self.curtain_alpha = 0
        self.curtain.set_alpha(self.curtain_alpha)

        self.game_menu_toggled = False

    def setup_ellipses(self):
        self.shadow_image = pygame.Surface(self.shadow_rect.size).convert_alpha()
        temp_rect = self.shadow_image.get_rect()
        self.shadow_image.set_colorkey(WHITE)
        self.shadow_image.fill(WHITE)
        pygame.draw.ellipse(self.shadow_image, (10, 10, 10), (0, 0, temp_rect.width, temp_rect.height))
        self.shadow_image.set_alpha(40)

        self.ellipse_image = pygame.Surface(self.shadow_rect.size).convert()
        self.ellipse_image.set_colorkey((69, 69, 69))
        self.ellipse_image.fill((69, 69, 69))

        ellipse_rect = self.ellipse_image.get_rect()

        for i in range(60):
            temp_rect = (i*3, i, ellipse_rect.width - i*6, ellipse_rect.height - i*2)
            pygame.draw.ellipse(self.ellipse_image, (i + 70, i + 70, i + 70), temp_rect, 3)

    def reload_games(self):
        # reset angles and indices
        self.master_index = 0
        self.target_index = 0
        self.master_angle = 0
        self.target_angle = 0
        self.lowest_game = None

        # first time loading games
        if self.first_load:
            # add games to wheel
            self.games = []
            for index, data in enumerate(self.all_games_data):
                self.item_angle = math.radians(self.angle_increment * -index + 90)
                x = int(math.cos(self.item_angle) * self.rect.width) + self.rect.centerx
                y = int(math.sin(self.item_angle) * self.rect.height) + self.rect.centery
                self.games.append(Game(data, index, x, y, self.rect, self.item_angle))
            self.first_load = False

        # do an actual reload
        else:
            temp_games = []
            for index, data in enumerate(self.all_games_data):
                self.item_angle = math.radians(self.angle_increment * -index + 90)
                x = int(math.cos(self.item_angle) * self.rect.width) + self.rect.centerx
                y = int(math.sin(self.item_angle) * self.rect.height) + self.rect.centery

                current_name = self.all_games_data[index]["name"]
                current_game = [g for g in self.games if g.name == current_name][0]
                current_game.reset(data, index, x, y, self.rect, self.item_angle)
                temp_games.append(current_game)

            self.games = temp_games

    def sort_games(self, am):
        """0 - name, 1 - size, 2 - last_played"""
        self.sort_index += .5
        self.reverse_sort = not self.reverse_sort
        self.sort_index %= len(self.sort_types)

        sort_key = self.sort_types[int(self.sort_index)]

        games_data_copy = self.all_games_data.copy()
        self.all_games_data = sorted(games_data_copy, key=lambda game: game[sort_key], reverse=self.reverse_sort)

        self.reload_games()
        self.game_label.set_text(self.games[self.master_index].name)

        am.play_sound("menu_swish")

    def prepare_game(self):
        proc, path, env = self.games[self.master_index].prepare_executable()
        return proc, path, env

    def get_lowest_game(self):
        # Find which item is currently closest to bottom position
        closest_game = None
        min_diff = float('inf')

        for game in self.games:
            # Calculate angle difference from bottom position
            game_angle = (game.angle + math.radians(self.master_angle)) % (2 * math.pi)
            diff = abs(game_angle - self.bottom_angle)

            # Take shortest path around circle
            if diff > math.pi:
                diff = 2 * math.pi - diff

            if diff < min_diff:
                min_diff = diff
                closest_game = game

        return closest_game

    def check_selected(self, col, row, dt):
        if not self.selected[0]:
            diff = abs(self.curtain_alpha - 200)
            if int(diff) >= 1:
                self.curtain_alpha += diff * 0.15 * dt
            else:
                self.curtain_alpha = 200
        else:
            diff = abs(self.curtain_alpha - 0)
            if int(diff) >= 1:
                self.curtain_alpha -= diff * 0.15 * dt
            else:
                self.curtain_alpha = 0

        self.selected[1] = False
        if row == self.row and col == self.col:
            self.selected[1] = True

    def check_game_menu_toggled(self, toggled):
        self.game_menu_toggled = toggled

    def update(self, dt, col, row):
        # check if selected
        self.check_selected(col, row, dt)
        self.curtain.set_alpha(self.curtain_alpha)

        self.update_scroll(self.selected, dt)

        # adjust target values
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

        # update games
        for game in self.games:
            game.update(dt, self.master_index, self.master_angle, self.selected[1], self.scroll)

        # get closest game
        self.lowest_game = self.get_lowest_game()

    def update_scroll(self, selected, dt):
        # x selection
        if not selected[0]:
            self.target_scroll[0] = -150
        else:
            self.target_scroll[0] = 0

        # y selection
        if not selected[1]:
            self.target_scroll[1] = 15
        else:
            self.target_scroll[1] = 0

        # x scroll
        if self.scroll[0] != self.target_scroll[0]:
            diff = (self.target_scroll[0] - self.scroll[0])
            if abs(diff) > 1:
                self.scroll[0] += diff * 0.15 * dt
            else:
                self.scroll[0] = self.target_scroll[0]

        # y scroll
        if self.scroll[1] != self.target_scroll[1]:
            diff = (self.target_scroll[1] - self.scroll[1])
            if abs(diff) > 1:
                self.scroll[1] += diff * 0.15 * dt
            else:
                self.scroll[1] = self.target_scroll[1]

    def update_index(self, delta, audio_manager):
        self.target_index += delta
        self.target_index %= self.num_items
        self.master_index = self.target_index
        audio_manager.play_sound("menu_swish", False)
        self.game_label.set_text(self.games[self.master_index].name)

    def draw(self, display):
        display.blit(self.shadow_image, (self.shadow_rect.x + self.scroll[0], self.shadow_rect.y + 15))
        for i in range(15):
            temp_rect = (self.shadow_rect.x + self.scroll[0] + i*2 + 1, min(self.shadow_rect.y + i + self.scroll[1] + 1, self.shadow_rect.y + 16),
                         self.shadow_rect.width - i*4 - 2, self.shadow_rect.height - 2)
            pygame.draw.ellipse(display, (60, 60, 60), temp_rect, 1)

        display.blit(self.ellipse_image, (self.shadow_rect.x + self.scroll[0], self.shadow_rect.y + self.scroll[1]))

        sorted_games = sorted(self.games, key=lambda x: x.z_depth)
        for game in [s for s in sorted_games if s.z_depth < 2.0]:
            game.draw(display, self.game_menu_toggled)
        for game in [s for s in sorted_games if s.z_depth >= 2.0]:
            game.draw(display, self.game_menu_toggled)

        display.blit(self.curtain, self.curtain_rect)

        for game in [s for s in sorted_games if s == self.lowest_game]:
            game.draw(display, self.game_menu_toggled)

        if False not in self.selected:
            self.game_label.draw(display)


# main SHUGRPi OS app
class ShugrPiOS:
    def __init__(self, is_shugrpi, linux, master_images):
        """ Master class for the SHUGRPi Operating System """
        self.is_shugrpi = is_shugrpi
        self.linux = linux

        # window/display setup
        self.screen = screen
        self.display = pygame.Surface((DISPLAY_WIDTH, DISPLAY_HEIGHT)).convert()
        self.display_info = pygame.display.Info()
        logger.info("Using video driver: " + pygame.display.get_driver())

        # time setup
        self.clock = pygame.time.Clock()
        self.timers = {}
        self.pause = False
        self.current_time = current_time
        self.sys_clock = SystemClock(self.linux, self.current_time)

        # timers setup
        self.timers["pre_init"] = Timer(60)
        self.timers["logo"] = Timer(120)
        self.timers["start"] = Timer(180)

        # manager setup
        self.am = AudioManager(logger, self.is_shugrpi)
        self.gm = GameManager()
        self.nm = NetworkManager(self.linux)

        # games setup
        self.master_games_path = os.path.join(base_path, GAME_PATH)

        # images setup
        self.battery_image = pygame.transform.scale(self.get_image("battery"), (30, 30))
        self.fail_image = master_images["fail_load"]
        self.original_logo_img = self.get_image("logo")
        self.logo_img = pygame.transform.scale(self.original_logo_img, (int(165 * 3), int(165 * 3)))
        self.big_logo_img = pygame.transform.scale(self.original_logo_img, (int(165 * 4), int(165 * 4)))
        self.logo_alpha = 0
        self.logo_img.set_alpha(self.logo_alpha)

        # utility setup
        self.internet_connection = check_internet_status()
        self.stop_event = threading.Event()
        self.wifi_lock = threading.Lock()
        self.wifi_thread = threading.Thread(name="SHUGRPi Internet Updater", target=self.update_internet_connection, daemon=True)
        self.wifi_thread.start()

        # virtual keyboard
        self.virtual_keyboard = VirtualKeyboard()

        # text field UI setup
        self.text_fields = {}

        # room setup
        self.rooms = {}
        self.ui_managers = {}

        # setup UI for rooms
        self.setup_game_room()
        self.setup_clock_room()
        self.setup_network_room()
        self.setup_power_room()

        # universal UI setup
        self.banner_top = pygame.Surface((DISPLAY_WIDTH, 60)).convert()
        self.banner_top.fill(GRAY)
        self.banner_top_rect = self.banner_top.get_rect()
        self.banner_top_rect.midtop = (half_display_x, -30)

        self.banner_bottom = pygame.Surface((DISPLAY_WIDTH, 30)).convert()
        self.banner_bottom.fill(GRAY)
        self.banner_bottom_rect = self.banner_bottom.get_rect()
        self.banner_bottom_rect.midbottom = (half_display_x, DISPLAY_HEIGHT)

        self.dialog_menu = DialogMenu(self.screen, "Welcome to the SHUGRPi!", has_ui=True)
        self.notification = Notification(None)

        # effects setup
        self.curtain = Curtain()
        self.curtain.set_color(DARKER_GRAY)
        self.floating_logo = FloatingLogo()

        # create rooms
        self.create_room("games", 0, 0, self.ui_managers["games"])
        self.create_room("clock", 0, -1, self.ui_managers["clock"])
        self.create_room("network", 0, -1, self.ui_managers["network"])
        self.create_room("power", 0, -1, self.ui_managers["power"])

        self.rm = RoomManager(self.rooms)
        self.current_room = self.rm.current_room

        # installation setup
        self.installations = {}

        # master phase variable
        self.master_phase = -2

        # master running variable
        self.running = True
        self.running_game = [None, None]
        self.start_game = False

        logger.info("Initialized SHUGRPi Operating System")

    """ room ui setup """
    def setup_game_room(self):
        ui_group = pygame.sprite.Group()

        all_games_data = self.gm.load_games(self.master_games_path)
        self.game_wheel = GameWheelUi(half_display_x, half_display_y + 60, 180, 60, all_games_data, ui_group)

        self.clock_ui = UiElement(self.current_time, 30, 10, 0, 0, size=10, font=retro_font, group=ui_group, func= lambda: self.switch_room("clock"))
        self.network_ui = UiElement("Wifi", DISPLAY_WIDTH - 100, 10, 0, 1, size=10, font=retro_font, group=ui_group, func= lambda: self.switch_room("network"))
        self.power_ui = UiElement("Power", DISPLAY_WIDTH - 50, 10, 0, 2, size=10, font=retro_font, group=ui_group, func= lambda: self.switch_room("power"))

        self.game_menu = GameMenu(self.am, self.fade_to_game)

        self.create_ui_manager("games", ui_group)
        self.ui_managers["games"].y_index = 1

    def setup_clock_room(self):
        ui_group = pygame.sprite.Group()
        self.set_time_ui = UiElement("Set Time", half_display_x, half_display_y - 50, 0, 0, size=10, font=retro_font, group=ui_group, func= lambda: self.set_time())
        self.hour_ui = UiElement(self.sys_clock.hour, half_display_x - 120, half_display_y - 50, 0, 1, size=10, font=retro_font, group=ui_group, func= lambda: self.rooms["clock"][2].change_col(1))
        self.minute_ui = UiElement(self.sys_clock.minute, half_display_x - 80, half_display_y - 50, 0, 2, size=10, font=retro_font, group=ui_group, func= lambda: self.rooms["clock"][2].change_col(1))
        self.round_clock_ui = UiElement(self.sys_clock.round_clock_labels[int(self.sys_clock.round_clock)], half_display_x, half_display_y + 50, 1, 0, size=10, font=retro_font, group=ui_group, func=self.switch_time_format)
        back_btn = self.add_back_button(ui_group)

        self.colon = Text(":", half_display_x - 100, half_display_y - 50, WHITE, 10, retro_font)

        self.create_ui_manager("clock", ui_group)

    def setup_network_room(self):
        ui_group = pygame.sprite.Group()
        self.connect_ui = UiElement("Connect", half_display_x, 100, 0, 0, size=10, font=retro_font, group=ui_group, func=lambda: self.nm.connect_to_wifi(self.text_fields["ssid"], self.text_fields["psk_key"]))
        self.text_fields["ssid"] = TextField(half_display_x - 125, 200, 1, 0, 200, 30, "Enter your SSID here", group=ui_group, keyboard=self.virtual_keyboard)
        self.text_fields["psk_key"] = TextField(half_display_x + 125, 200, 1, 1, 200, 30, "Enter your password here", group=ui_group, keyboard=self.virtual_keyboard)
        back_btn = self.add_back_button(ui_group)

        self.create_ui_manager("network", ui_group)

    def setup_power_room(self):
        ui_group = pygame.sprite.Group()
        self.power_ui = UiElement("Power Off", 100, 100, 0, 0, size=10, font=retro_font, group=ui_group, func=self.linux.power_off)
        self.reboot_ui = UiElement("Reboot", 100, 200, 1, 0, size=10, font=retro_font, group=ui_group, func=self.linux.reboot)
        back_btn = self.add_back_button(ui_group)

        self.create_ui_manager("power", ui_group)

    def add_back_button(self, ui_group):
        back_button = UiElement("Back", DISPLAY_WIDTH - 50, DISPLAY_HEIGHT - 20, 2, 0, group=ui_group, func=lambda: self.switch_room("games"))
        return back_button

    """ main runner """
    def run(self):
        global window_title

        time_accum = 0
        step = 0
        try:
            while self.running:
                self.current_time = time.strftime("%H:%M") if self.sys_clock.round_clock else time.strftime("%I:%M")

                if not self.pause:
                    # tick clock
                    dt = self.clock.tick(FPS) / 1000.0 * 60
                    time_accum += dt
                    step = 0

                    # update curtain first
                    self.curtain.update(dt)

                    # run main loop (delta time)
                    while time_accum >= 1 and step <= 50:
                        self.update(SPEED)
                        time_accum -= 1
                        step += 1

                    # check on installations
                    self.check_installations()

                    # rest of main loop
                    self.events(self.master_phase)
                    self.draw()

                # while game is running
                if self.running_game[1] is not None:
                    # keep app minimally responsive to avoid breakage
                    pygame.event.get()

                    if self.running_game[1].poll() is not None:
                        self.handle_game_output()

                        self.resume_menu()

        # handle crashes and keyboard interrupts
        except (Exception, KeyboardInterrupt) as e:
            if isinstance(e, Exception):
                error_msg = f"SHUGRPi has crashed due to the following error: {e}"
                logger.error(error_msg)
                pygame.display.message_box(window_title, error_msg, "error")
                raise
                self.shutdown(1)
            self.shutdown(-1)

    """ main loop """
    def update(self, dt):
        # dummy screen (to absorb initial dt spikes)
        if self.master_phase == -2:
            if self.timers["pre_init"].update(dt) or dt < 1:
                self.switch_phase(-1, dt)

        # logo screen
        if self.master_phase == -1:
            if not self.timers["start"].update(dt):
                if self.logo_alpha < 255:
                    self.logo_alpha += 5 * dt
                else:
                    self.logo_alpha = 255
                    self.am.play_sound("logo", in_loop=True)
            else:
                if not self.timers["logo"].update(dt):
                    if self.logo_alpha > 0:
                        self.logo_alpha -= 5 * dt
                    else:
                        self.logo_alpha = 0
                else:
                    if self.logo_alpha == 0:
                        self.switch_phase(0, dt, True)
                        self.logo_alpha = 0
                        logger.info("Running main loop")

        # main menu
        elif self.master_phase == 0:
            self.floating_logo.update(dt)

            self.dialog_menu.update(dt)

            self.virtual_keyboard.update(dt)

            self.rm.update(dt)

            if (self.dialog_menu.showing and self.dialog_menu.has_ui) or self.virtual_keyboard.toggled:
                self.rm.current_room[2].active = False
                self.game_menu.um.active = False
                self.game_wheel.selected[1] = False
            else:
                self.rm.current_room[2].active = True
                self.game_menu.um.active = True

            for _, room in self.rooms.items():
                room[2].update(dt)

            self.game_menu.update(dt)

            self.game_wheel.check_game_menu_toggled(self.game_menu.toggled)

            self.notification.update(dt)

            self.clock_ui.change_label(self.current_time)

            if self.current_room[3] != "clock":
                self.hour_ui.change_label(self.current_time.split(":")[0])
                self.minute_ui.change_label(self.current_time.split(":")[1])

            if self.start_game:
                if self.curtain.flip:
                    self.execute_game()

    def events(self, phase):
        # handle events
        for event in pygame.event.get():

            # shutdown
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.shutdown()

            if event.type == pygame.KEYDOWN:
                if phase == -2:
                    phase = -1
                    self.timers["start"].finished = True

                if phase == -1:
                    self.timers["start"].finished = True

                elif phase == 0:
                    # virtual keyboard
                    if event.key == pygame.K_SPACE:
                        self.virtual_keyboard.toggle()

                    if self.virtual_keyboard.toggled:
                        self.virtual_keyboard.handle_event(event, self.text_fields)
                        return

                    # dialog menu
                    if self.dialog_menu.showing and self.dialog_menu.has_ui:
                        if event.key in [pygame.K_UP, pygame.K_LEFT]:
                            self.dialog_menu.um.change_col(-1)
                        if event.key in [pygame.K_DOWN, pygame.K_RIGHT]:
                            self.dialog_menu.um.change_col(1)
                        if event.key == pygame.K_RETURN:
                            self.dialog_menu.um.action()
                            self.handle_dialog_output()

                    # dialog menu cancel
                    if not self.dialog_menu.has_ui:
                        self.dialog_menu.fade_out()

                    if self.current_room[3] == "games":

                        # game wheel
                        if self.game_wheel.selected[1] and not self.game_menu.toggled:
                            # navigation
                            if event.key == pygame.K_UP:
                                self.ui_managers["games"].change_row(-1)
                            if event.key == pygame.K_DOWN:
                                self.ui_managers["games"].change_row(1)
                            if event.key == pygame.K_LEFT:
                                self.game_wheel.update_index(-1, self.am)
                            if event.key == pygame.K_RIGHT:
                                self.game_wheel.update_index(1, self.am)

                            # functions
                            if event.key == pygame.K_RSHIFT:
                                gw = self.game_wheel
                                gw.sort_games(self.am)
                                title = f"Sort By: {gw.sort_names[gw.sort_types[int(gw.sort_index)]]}\nAscending: {not gw.reverse_sort}"
                                self.dialog_menu.reset(title, True)
                            if event.key == pygame.K_RETURN:
                                self.game_menu.game = self.game_wheel.games[self.game_wheel.master_index]
                                self.game_wheel.selected[0] = False
                                self.game_menu.toggle()

                        # game menu
                        elif self.game_menu.toggled:
                            # navigation
                            if event.key == pygame.K_UP:
                                self.game_menu.um.change_row(-1)
                            if event.key == pygame.K_DOWN:
                                self.game_menu.um.change_row(1)

                            # functions
                            if event.key == pygame.K_RETURN:
                                self.game_wheel.selected[0] = self.game_menu.action()
                            if event.key == pygame.K_BACKSPACE:
                                self.game_wheel.selected[0] = True
                                self.game_menu.toggle()

                        # normal
                        else:
                            self.default_ui_nav(event)

                    elif self.current_room[3] == "clock":
                        if self.hour_ui.selected:
                            if event.key == pygame.K_UP:
                                if self.sys_clock.round_clock:
                                    label = (int(self.hour_ui.label) + 1) % 24
                                else:
                                    label = int(self.hour_ui.label) + 1
                                    if label > 12:
                                        label = 1
                                self.hour_ui.change_label(("0" if label < 10 else "") + str(label))
                            if event.key == pygame.K_DOWN:
                                if self.sys_clock.round_clock:
                                    label = (int(self.hour_ui.label) - 1) % 24
                                else:
                                    label = int(self.hour_ui.label) - 1
                                    if label < 1:
                                        label = 12
                                self.hour_ui.change_label(("0" if label < 10 else "") + str(label))
                        elif self.minute_ui.selected:
                            if event.key == pygame.K_UP:
                                label = str((int(self.minute_ui.label) + 1) % 60)
                                self.minute_ui.change_label(("0" if int(label) < 10 else "") + label)
                            if event.key == pygame.K_DOWN:
                                label = str((int(self.minute_ui.label) - 1) % 60)
                                self.minute_ui.change_label(("0" if int(label) < 10 else "") + label)
                        else:
                            if event.key == pygame.K_UP:
                                self.current_room[2].change_row(-1)
                            if event.key == pygame.K_DOWN:
                                self.current_room[2].change_row(1)

                        if event.key == pygame.K_LEFT:
                            self.current_room[2].change_col(-1)
                        if event.key == pygame.K_RIGHT:
                            self.current_room[2].change_col(1)
                        if event.key == pygame.K_RETURN:
                            self.current_room[2].action()
                        if event.key == pygame.K_BACKSPACE:
                            self.switch_room("games")

                    else:
                        self.default_ui_nav(event)

    def draw(self):
        self.screen.fill(DARKER_GRAY)

        # dummy screen
        if self.master_phase == -2:
            self.display.fill(DARKER_GRAY)

        # logo screen
        elif self.master_phase == -1:
            self.display.fill(DARKER_GRAY)
            self.logo_img.set_alpha(int(self.logo_alpha))
            self.display.blit(self.logo_img, (
            half_display_x - self.logo_img.get_width() // 2, half_display_y - self.logo_img.get_height() // 2))

        # main menu
        elif self.master_phase == 0:
            self.display.fill(DARK_GRAY)

            self.rm.clear()

            self.floating_logo.draw(self.display)

            for _, room in self.rooms.items():
                room[1].blit(self.banner_top, (self.banner_top_rect.x, self.banner_top_rect.y))
                room[1].blit(self.banner_bottom, (self.banner_bottom_rect.x, self.banner_bottom_rect.y))

            for _, room in self.rooms.items():
                room[2].draw(room[1])

            self.game_menu.draw(self.rooms["games"][1])
            self.colon.draw(self.rooms["clock"][1])

            self.rm.draw(self.display)

            self.dialog_menu.draw(self.display)

            self.notification.draw(self.display)

            self.virtual_keyboard.draw(self.display)

            draw_text(self.display, str(round(self.clock.get_fps())), 30, 50, WHITE, 10, retro_font)

            self.curtain.draw(self.display)

        # stretch display to fit screen
        if self.display.get_size() != self.screen.get_size():
            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), (0, 0))
        else:
            self.screen.blit(self.display, (0, 0))

        # flip screen
        pygame.display.flip()

    """ game utilities """
    def fade_to_game(self):
        current_game = self.game_wheel.lowest_game
        if current_game.installed:
            self.curtain.set_color(DARK_GRAY)
            self.curtain.target_alpha = 255
            self.start_game = True
            self.am.stop_music()
        else:
            self.dialog_menu.reset("Install?", has_ui=True, options=["Yes", "No"], dialog_type=0)

    def execute_game(self):
        proc, path, env = self.game_wheel.prepare_game()
        if audio_driver:
            pygame.mixer.pause()
        self.running_game[0] = self.game_wheel.lowest_game.name

        try:
            self.running_game[1] = subprocess.Popen(proc, cwd=path, env=env, stderr=subprocess.PIPE, text=True)
            self.start_game = False
            self.pause = True
        except Exception as e:
            logger.error(f"Failed to launch {self.running_game[0]}")
            self.resume_menu()

    def handle_game_output(self):
        ignored_errors = ["libpng"]

        stderr = self.running_game[1].stderr.read()
        is_error = False
        simple_error = None
        for err in ignored_errors:
            if err not in stderr and len(stderr.splitlines()) > 1:
                is_error = True
                simple_error = stderr.splitlines()[-1]

        if simple_error is not None:
            title = self.running_game[0]
            if len(title) > 13:
                title = title[:13] + "..."
            self.notification.reset(f"`{title}` crashed due to: `{simple_error}`")

        if is_error:
            logger.error(f"`{self.game_wheel.lowest_game.name}` has crashed due to the following error:\n" + stderr.strip())

        else:
            logger.info(f"`{self.game_wheel.lowest_game.name}` has terminated successfully")

    def resume_menu(self):
        self.running_game = [None, None]
        self.pause = False

        self.curtain.target_alpha = 0
        self.game_wheel.selected[0] = True

        if audio_driver:
            pygame.mixer.unpause()
        self.am.play_music("shugrpi_bg")
        self.game_menu.toggle()

        self.clock.tick(FPS)

    """ installation utilities"""
    def install_game(self):
        current_game = self.game_wheel.lowest_game
        if current_game.name not in self.installations:
            current_game.update_before_install()
            self.installations[current_game.name] = Installation(current_game, logger, self.internet_connection)
            self.installations[current_game.name].start()
            self.game_menu.update_start_game_ui(2)

    def check_installations(self):
        for installation in list(self.installations.values()).copy():
            if installation.complete:
                current_game = [g for g in self.game_wheel.games if g.name == installation.name][0]
                current_game.update_after_install(installation.ready)
                if installation.ready:
                    self.dialog_menu.reset(f"Successfully installed {current_game.name}!", instant=False, has_ui=True, options=["OK"])
                    self.game_menu.update_start_game_ui(0)
                else:
                    self.dialog_menu.reset(f"Failed to install {current_game.name}!", instant=False, has_ui=True, options=["OK"])
                    self.game_menu.update_start_game_ui(1)
                del self.installations[installation.name]
            else:
                current_game = [g for g in self.game_wheel.games if g.name == installation.name][0]
                current_game.update_during_install(installation.step)

    """ various utilities """
    def get_image(self, img):
        try:
            return master_images[img]
        except:
            return master_images["fail_load_alt"]

    def switch_phase(self, new_phase, dt, fade=False):
        if fade:
            if self.master_phase != new_phase:
                self.curtain.target_alpha = 255
                if self.curtain.flip:
                    self.master_phase = new_phase
                    self.am.reset_sounds()
                    self.am.play_music("shugrpi_bg")
                    self.curtain.target_alpha = 0
        else:
            if self.master_phase != new_phase:
                self.master_phase = new_phase
                self.am.reset_sounds()

    def default_ui_nav(self, event):
        if event.key == pygame.K_UP:
            self.current_room[2].change_row(-1)
        if event.key == pygame.K_DOWN:
            self.current_room[2].change_row(1)
        if event.key == pygame.K_LEFT:
            self.current_room[2].change_col(-1)
        if event.key == pygame.K_RIGHT:
            self.current_room[2].change_col(1)
        if event.key == pygame.K_RETURN:
            self.current_room[2].action()
        if event.key == pygame.K_BACKSPACE:
            self.switch_room("games")

    def handle_dialog_output(self):
        if self.dialog_menu.dialog_type == 0:
            if self.dialog_menu.choice == 1:
                self.install_game()
            elif self.dialog_menu.choice == 0:
                self.game_menu.update_start_game_ui(1)

    """time utilities"""
    def set_time(self):
        self.sys_clock.set_time(self.hour_ui.label + ":" + self.minute_ui.label)

    def switch_time_format(self):
        self.sys_clock.switch_format()
        if not self.sys_clock.round_clock:
            if int(self.hour_ui.label) > 12:
                label = str(int(self.hour_ui.label) % 12)
                self.hour_ui.change_label(("0" if int(label) < 10 else "") + label)
            elif int(self.hour_ui.label) < 1:
                label = "12"
                self.hour_ui.change_label(("0" if int(label) < 10 else "") + label)

        self.round_clock_ui.change_label(self.sys_clock.round_clock_labels[self.sys_clock.round_clock])

    """ room utilities """
    def create_ui_manager(self, name, ui_group):
        self.ui_managers[name] = UiManager(ui_group)

    def create_room(self, name, x, y, um=UiManager([UiElement("", 0, 0, 0, 0, group=[])])):
        new_room = Room(x, y)
        self.rooms[name] = [new_room, new_room.surf, um, name]

    def switch_room(self, name):
        self.current_room = self.rm.switch_to(name)
        if name == "games":
            self.current_room[2].y_index = 1

    """ threaded utilities """
    def update_internet_connection(self):
        try:
            while not self.stop_event.wait(3):
                with self.wifi_lock:
                    self.internet_connection = check_internet_status()
        except Exception as e:
            logger.error(f"Failed to update internet status: {e}")

    """ main shutdown """
    def shutdown(self, code=0, system=False):
        logger.info("Shutting down...")

        # shutdown any running game
        if self.running_game[1] is not None:
            self.running_game.terminate()

        # cancel any ongoing game installations
        for installation in self.installations.values():
            if not installation.complete:
                installation.bailout()

        # quit pygame
        self.running = False
        pygame.quit()

        # stop threads
        self.stop_event.set()
        self.wifi_thread.join()

        # final exit
        logger.info("Shutdown complete!")
        sys.exit(code)


# start up SHUGRPi OS
shugrpi_os = ShugrPiOS(is_shugrpi, linux, master_images)
shugrpi_os.run()
