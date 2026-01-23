"""
The official SHUGR PI Operating System
designed specifically for the SHUGR PI

Code and Assets by Stormwrecker
All Rights Reserved
"""

# import setup modules
import os
import platform
import sys
from shutil import rmtree
from py_finder import *

# the operating system
master_platform = platform.system().lower()
master_machine = platform.machine().lower()
is_shugr_pi = True if master_machine == "aarch64" else False

# set necessary environment variables
if is_shugr_pi:
    os.environ["DISPLAY"] = ":0"
    os.environ['AUDIODEV'] = 'hdmi:CARD=vc4hdmi0,DEV=0'
    os.environ["SDL_VIDEO_ALLOW_SCREENSAVER"] = "0"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

# master directory
base_path = os.path.abspath(".")
PATH = os.path.join(base_path, "games")

# setup logging
import logging
logging.basicConfig(
    level="INFO",
    format="%(levelname)s - %(message)s",
    handlers=[logging.FileHandler(os.path.join(base_path, "session.log"), "w"),
              logging.StreamHandler()]
)
logger = logging.getLogger("ShugrPiOS")

# import pygame-ce
import pygame
if hasattr(pygame, "IS_CE"):
    logger.info("Successfully loaded pygame-ce")
    is_ce = True
else:
    logger.warning("ShugrPi OS requires pygame-ce: got pygame instead")
    is_ce = False

# import other modules
import subprocess
import threading
import random
import time
import json
import math
from socket import gethostbyname, gethostname

# import RPi.GPIO if available
try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

# set up pygame
pygame.init()
sound_working = True
try:
    pygame.mixer.init(frequency=48000, size=-16, channels=1, buffer=512)
    logger.info("Initialized pygame.mixer")
except pygame.error as e:
    sound_working = False
    logger.error(f"Initializing pygame.mixer failed; No sound available; {e}")

# setup window and display sizes
display_width, display_height = (800, 480)
screen_width, screen_height = (display_width, display_height)
half_display_x = display_width // 2
half_display_y = display_height // 2

# constants
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
DARK_BLUE = (28, 89, 152)


# handy tools
def load_asset(kind, path, flag=False):
    global logger
    """0: image, 1: sound, 2: font, 3: music, 4: other"""
    try:
        # image
        if kind == 0:
            if not flag:
                return pygame.image.load(os.path.join(base_path, path)).convert()
            else:
                return pygame.image.load(os.path.join(base_path, path)).convert_alpha()
        # sound
        elif kind == 1:
            return pygame.mixer.Sound(os.path.join(base_path, path))
        # font
        elif kind == 2:
            return pygame.font.Font(os.path.join(base_path, path), flag if type(flag) == int else 30)
        # music
        elif kind == 3:
            pygame.mixer.music.load(os.path.join(base_path, path))
        # other
        elif kind == 4:
            return os.path.join(base_path, path)
    except:
        logger.warning(f"unable to locate '{path}'")
        if kind == 0:
            return pygame.image.load(os.path.join(base_path, "images", "fail_load.png")).convert()
        return None


internet_connection = False
def check_internet_status():
    global internet_connection
    my_ip = gethostbyname(gethostname())
    internet_connection = False
    if my_ip != "127.0.0.1":
        internet_connection = True
    return internet_connection


# font handling
font_cache = {}
all_fonts = []
default_font = os.path.join(base_path, "fonts/PressStart2P.ttf")
def get_font(font, size):
    actual_font = str(font) + str(size)
    if actual_font not in font_cache:
        font_cache[actual_font] = pygame.font.Font(font, size)

    return font_cache[actual_font]


# text renderer
def draw_text(display, text, x, y, color, size, font=default_font, centered=False):
    font = get_font(font, size)
    text_surface = font.render(str(text), False, color)
    text_rect = text_surface.get_rect()
    if centered:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    display.blit(text_surface, text_rect)


"""Base Entity sprite"""
class Entity(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)

    def draw(self, display):
        display.blit(self.image, self.rect)


"""Logo for floating in the BG"""
class BGLogo(Entity):
    def __init__(self, img):
        Entity.__init__(self)
        self.original_image = img
        self.reset()
        self.start_timer = 120

    def reset(self):
        self.image = self.original_image.copy()
        self.image = pygame.transform.rotate(self.image, random.randint(-20, 20))
        self.rect = self.image.get_rect()
        self.rect.center = (random.randint(100, display_width - 100), random.randint(60, display_height - 60))
        self.floating_x = self.rect.x
        self.floating_y = self.rect.y
        if self.rect.centerx >= half_display_x:
            self.dx = -random.randint(1, 3) / 10
        else:
            self.dx = random.randint(1, 3) / 10
        if self.rect.centery >= half_display_y:
            self.dy = -random.randint(1, 3) / 10
        else:
            self.dy = random.randint(1, 3) / 10
        self.alpha = 0
        self.max_alpha = 30
        self.timer = 240
        self.wait_timer = random.randint(180, 240)
        self.toggled = False
        self.image.set_alpha(self.alpha)

    def update(self):
        self.image.set_alpha(self.alpha)
        if self.start_timer:
            self.start_timer -= 1
        else:
            if self.alpha < self.max_alpha and not self.toggled:
                self.alpha += 1
            else:
                self.toggled = True

        if self.toggled:
            if self.timer:
                self.timer -= 1
            else:
                if self.alpha > 0:
                    self.alpha -= 1
                else:
                    self.alpha = 0
                    if self.wait_timer:
                        self.wait_timer -= 1
                    else:
                        self.reset()

        self.floating_x += self.dx
        self.floating_y += self.dy
        self.rect.topleft = (self.floating_x, self.floating_y)

    def draw(self, display):
        display.blit(self.image, self.rect)


"""Wheel UI Element"""
class WheelUI:
    def __init__(self, x, y, width, height, games, fail_image):
        # positioning
        self.width = width
        self.height = height
        self.centerx = x
        self.centery = y

        # angles and indices
        self.master_index = 0
        self.target_index = 0
        self.master_angle = 0
        self.target_angle = 0
        self.bottom_angle = math.radians(90)

        # get games
        self.games = games
        self.item_group = pygame.sprite.Group()
        self.thumbnails = []

        # get angles for even spacing
        self.item_angle = 0
        self.num_items = len(self.games)
        self.angle_increment = 360 / self.num_items if self.num_items > 0 else 0

        # add thumbnails and wheel-items
        for index, key in enumerate(self.games):
            temp_thumb = self.games[key]["thumbnail"] if self.games[key]["thumbnail"] != 0 else fail_image
            if temp_thumb.get_size() != (150, 200):
                temp_thumb = pygame.transform.scale(temp_thumb, (150, 200))
            self.thumbnails.append(temp_thumb)
            self.item_angle = math.radians(self.angle_increment * index + 90)
            x = int(math.cos(self.item_angle) * self.width) + self.centerx
            y = int(math.sin(self.item_angle) * self.height) + self.centery
            wheel_item = WheelItem(index, self.games[key]["name"], temp_thumb, x, y, self.item_angle)
            self.item_group.add(wheel_item)

    def update(self, scroll_x, scroll_y, master_index):
        # normalize target index to stay in range
        self.target_index %= self.num_items

        # adjust target values
        self.master_index = self.target_index
        self.target_angle = self.angle_increment * self.target_index

        # normalize target_angle to prevent floating-point overflow
        self.target_angle %= 360

        # smoothly interpolate towards target_angle
        angle_diff = (self.target_angle - self.master_angle) % 360
        if angle_diff > 180:
            angle_diff -= 360

        if abs(angle_diff) > 1:
            self.master_angle += angle_diff * 0.15
        else:
            self.master_angle = self.target_angle

        # Keep master_angle normalized
        self.master_angle %= 360

        # update items
        self.item_group.update(self, scroll_x, scroll_y, master_index)

    def get_bottom_item(self):
        # Find which item is currently closest to bottom position
        closest_item = None
        min_diff = float('inf')

        for item in self.item_group:
            # Calculate angle difference from bottom position
            item_angle = (item.angle + math.radians(self.master_angle)) % (2 * math.pi)
            diff = abs(item_angle - self.bottom_angle)

            # Take shortest path around circle
            if diff > math.pi:
                diff = 2 * math.pi - diff

            if diff < min_diff:
                min_diff = diff
                closest_item = item

        return closest_item

    def draw(self, display, scroll_x, scroll_y):
        pygame.draw.ellipse(display, GRAY, pygame.Rect((self.centerx - (self.width * 1.5) + scroll_x,
                                                        self.centery - 20 + scroll_y, self.width * 3,
                                                        self.height * 2)))
        sorted_sprites = sorted(self.item_group.sprites(), key=lambda x: x.z_depth)
        for sprite in [s for s in sorted_sprites if s.z_depth < 2.0]:
            display.blit(sprite.image, sprite.rect)
        for sprite in [s for s in sorted_sprites if s.z_depth >= 2.0]:
            display.blit(sprite.image, sprite.rect)


"""Item to be placed on Wheel UI Element"""
class WheelItem(pygame.sprite.Sprite):
    def __init__(self, index, label, image, x, y, angle):
        pygame.sprite.Sprite.__init__(self)
        self.index = index
        self.x = x
        self.y = y
        self.original_image = image
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.base_angle = angle
        self.angle = angle
        self.depth = 0
        self.label = label.title()
        self.original_scale = 1
        self.grow = 0

    def update(self, wheel, scroll_x, scroll_y, master_index):
        # get wheel_ui values for positioning
        self.w_width = wheel.width
        self.w_height = wheel.height
        self.w_centerx = wheel.centerx
        self.w_centery = wheel.centery

        current_angle = self.base_angle + math.radians(wheel.master_angle)

        # center rect based on wheel_ui pos
        self.rect.midbottom = (int(math.cos(current_angle) * self.w_width) + self.w_centerx + scroll_x,
                            int(math.sin(current_angle) * self.w_height) + self.w_centery + 40 + scroll_y)

        self.z_depth = math.sin(current_angle) + 2

        # Draw selection frame if this is the selected item
        bottom_item = wheel.get_bottom_item()
        if bottom_item and self.index == bottom_item.index and master_index == 1:
            if abs(wheel.master_angle - wheel.target_angle) < 6:
                self.zoom_in(1.5)
        else:
            self.zoom_out()

    def zoom_in(self, zoom_factor):
        diff = abs(self.image.get_width() - int(self.original_image.get_width() * zoom_factor))
        if diff != 0:
            orig_x, orig_y = self.original_image.get_size()
            if diff > 1:
                self.grow += diff * 0.2
                size_x = orig_x + round(self.grow)
                size_y = int(size_x * 4 // 3)
            else:
                size_x = int(self.original_image.get_width() * zoom_factor)
                size_y = int(self.original_image.get_height() * zoom_factor)
            self.image = pygame.transform.smoothscale(self.original_image, (size_x, size_y))
            self.image.set_colorkey(WHITE)
            self.rect = self.image.get_rect(midbottom=self.rect.midbottom)

    def zoom_out(self):
        diff = abs(self.image.get_width() - self.original_image.get_width())
        if diff != 0:
            orig_x, orig_y = self.original_image.get_size()
            if diff > 1:
                self.grow -= diff * 0.2
                size_x = orig_x + round(self.grow)
                size_y = int(size_x * 4 // 3)
            else:
                size_x = self.original_image.get_width()
                size_y = self.original_image.get_height()
            self.image = pygame.transform.scale(self.original_image, (size_x, size_y))
            self.image.set_colorkey(WHITE)
            self.rect = self.image.get_rect(midbottom=self.rect.midbottom)


"""Sub-menu for executing a game"""
class SubMenu:
    def __init__(self, game):
        self.index = 0
        self.display_game = game
        if len(self.display_game.split()) > 2:
            target_character = self.display_game.find(" ", 9)
            self.display_game = self.display_game[0:target_character] + "\n" + self.display_game[target_character + 1:]
        self.game = game
        self.x = display_width + 10
        self.y = half_display_y
        self.height = display_height - 100
        self.width = int(self.height * 4 // 3)
        self.rect = pygame.Rect((self.x, self.y, self.width, self.height))
        self.options = ["Start Game", "Back"]

    def render(self, display, scroll, game):
        if game != self.game:
            self.display_game = game
            if len(self.display_game.split()) > 2:
                target_character = self.display_game.find(" ", 9)
                self.display_game = self.display_game[0:target_character] + "\n" + self.display_game[target_character + 1:]
            self.game = game
        self.rect.x = self.x + (scroll * 2)
        self.rect.centery = half_display_y
        pygame.draw.rect(display, (50, 50, 50), self.rect)
        temp_size = 30 if len(self.display_game) <= 10 else 20
        for index, line in enumerate(self.display_game.splitlines()):
            draw_text(display, line, self.rect.x + 30, self.rect.top + 30 + ((temp_size + 10) * index), WHITE, temp_size)
        for index, option in enumerate(self.options):
            color = YELLOW if index == self.index else WHITE
            draw_text(display, option, self.rect.x + 30, self.rect.centery + (index * 60), color, 20)


"""Install-menu for installing game"""
class InstallMenu:
    def __init__(self, game):
        self.game = game
        self.index = 0
        self.x = half_display_x
        self.y = half_display_y
        self.width = 0
        self.height = 0
        self.target_width = 550
        self.target_height = 250
        self.rect = pygame.Rect((self.x, self.y, self.width, self.height))
        self.text_ready = False
        self.original_prompt = [f"{self.game} must be", "fully installed to play. Continue?"]
        self.prompt = self.original_prompt
        self.options = ["Install", "Cancel"]
        self.opt_x = [0, 0]
        self.activate = False

    def render(self, display, game, sub_phase):
        if game != self.game:
            self.prompt = [f"{game} must be", "fully installed to play. Continue?"]
            self.game = game
        self.original_prompt = [f"{self.game} must be", "fully installed to play. Continue?"]
        if sub_phase == 2:
            if abs(int(self.target_width - self.width)) >= 1:
                self.width += (self.target_width - self.width) * .15
            else:
                self.width = self.target_width
            if abs(int(self.target_height - self.height)) >= 1:
                self.height += (self.target_height - self.height) * .15
            else:
                self.height = self.target_height
        else:
            if abs(int(0 - self.width)) >= 1:
                self.width += (0 - self.width) * .15
            else:
                self.width = 0
            if abs(int(0 - self.height)) >= 1:
                self.height += (0 - self.height) * .15
            else:
                self.height = 0

        if self.width == self.target_width and self.height == self.target_height:
            if not self.text_ready:
                self.opt_x = [self.rect.left + 120, self.rect.right - 120]
                self.text_ready = True
        else:
            self.text_ready = False

        self.rect = pygame.Rect((self.x, self.y, self.width, self.height))
        self.rect.center = (self.x, self.y)
        if self.width > 5 or self.height > 5:
            pygame.draw.rect(display, (70, 70, 70), (self.rect.x - 4, self.rect.y - 4, self.rect.width + 8, self.rect.height + 8))
            pygame.draw.rect(display, (50, 50, 50), self.rect)
        if self.text_ready:
            if type(self.prompt) == list:
                for index, line in enumerate(self.prompt):
                    draw_text(display, line, self.rect.centerx, self.rect.centery - 30 + (index * 30), WHITE, 14, centered=True)
            else:
                draw_text(display, self.prompt, self.rect.centerx, self.rect.centery - 15, WHITE, 14, centered=True)

            if not self.activate:
                if len(self.options) > 1:
                    for index, option in enumerate(self.options):
                        color = YELLOW if index == self.index else WHITE
                        draw_text(display, option, self.opt_x[index], self.rect.bottom - 50, color, 20, centered=True)
                else:
                    draw_text(display, "OK", self.rect.centerx, self.rect.bottom - 50, YELLOW, 20, centered=True)
            else:
                draw_text(display, "(this may take some time)", self.rect.centerx, self.rect.bottom - 50, WHITE, 10, centered=True)


"""Error Message object for game-crashes"""
class ErrorMessage(Entity):
    def __init__(self, msg):
        self.msg = msg
        self.size = 9
        Entity.__init__(self)
        self.image = pygame.Surface(((self.size) * len(self.msg), self.size)).convert_alpha()
        self.image.set_colorkey(BLACK)
        self.rect = self.image.get_rect()
        self.rect.topleft = (display_width - self.size - ((self.size) * len(self.msg)), 33)
        self.alpha = 255
        self.display_timer = 180

    def update(self, display):
        self.image.set_alpha(self.alpha)
        if self.display_timer:
            self.display_timer -= 1
        else:
            if self.alpha > 0:
                self.alpha -= 5
            else:
                self.alpha = 0
                self.kill()
        draw_text(self.image, self.msg, 0, 0, WHITE, self.size)
        display.blit(self.image, self.rect)


"""Master SHUGR Pi Operating System"""
class ShugrPiOS:
    def __init__(self, is_shugr_pi):
        self.is_shugr_pi = is_shugr_pi
        logger.info(f"Running on ShugrPi: {'yes' if self.is_shugr_pi else 'no'}")

        if self.is_shugr_pi:
            flags = pygame.NOFRAME | pygame.FULLSCREEN | pygame.SCALED
        else:
            flags = pygame.NOFRAME
        self.screen = pygame.display.set_mode((screen_width, screen_height), flags)
        self.display = pygame.Surface((display_width, display_height)).convert()
        pygame.display.set_caption("SHUGRPI OS")
        pygame.display.set_icon(load_asset(0, "images/icon.png", True))
        self.display_info = pygame.display.Info()
        if self.is_shugr_pi:
            logger.info("Video Driver: " + pygame.display.get_driver())
            logger.info("Hardware acceleration: " + str(self.display_info.hw))
            logger.info("Video memory: " + str(self.display_info.video_mem))
        logger.info("Initialized display")

        self.clock = pygame.time.Clock()

        self.master_phase = 0
        self.sub_phase = 0
        self.scroll_x = 0
        self.target_scroll_x = self.scroll_x

        self.master_index = 1
        self.top_index = 1
        self.scroll_y = 0
        self.target_scroll_y = self.scroll_y

        self.logo_timer = 120
        self.start_timer = 180

        # fallback image
        self.fail_image = load_asset(0, "images/fail_load.png")

        # top banner setup
        self.banner_top = pygame.Surface((display_width, 30)).convert()
        self.banner_top.fill(GRAY)
        self.banner_top_rect = self.banner_top.get_rect()
        self.banner_top_rect.midtop = (half_display_x, 0)

        # bottom banner setup
        self.banner_bottom = pygame.Surface((display_width, 30)).convert()
        self.banner_bottom.fill(GRAY)
        self.banner_bottom_rect = self.banner_bottom.get_rect()
        self.banner_bottom_rect.midbottom = (half_display_x, display_height)

        # master run variable
        self.running = True

        # wifi image setup
        self.wifi_images = {True:pygame.transform.scale(load_asset(0, "images/wifi_on.png"), (25, 25)), False:pygame.transform.scale(load_asset(0, "images/wifi_off.png"), (25, 25))}
        for k, image in self.wifi_images.items():
            image.set_colorkey(BLACK)

        # wifi connection setup
        self.internet_connection = check_internet_status()
        self.wifi_image = self.wifi_images[self.internet_connection]
        self.wifi_thread = threading.Thread(target=self.update_internet_connection, daemon=True)
        self.wifi_thread.start()
        logger.info(f"Connected to internet (startup): {'yes' if self.internet_connection else 'no'}")

        # battery setup
        self.battery_image = pygame.transform.scale(load_asset(0, "images/battery.png", True), (30, 30))
        self.battery_image_low = pygame.transform.scale(load_asset(0, "images/battery_low.png", True), (30, 30))

        # logo image setup
        self.original_logo_img = load_asset(0, "images/logo.png", True)
        self.logo_img = pygame.transform.scale(self.original_logo_img, (int(165 * 3), int(165 * 3)))
        self.big_logo_img = pygame.transform.scale(self.original_logo_img, (int(165 * 4), int(165 * 4)))
        self.logo_alpha = 0
        self.logo_img.set_alpha(self.logo_alpha)

        # create BG logo object
        self.bg_logo = BGLogo(self.big_logo_img)

        # super amazing sound effects (crucial for the Shugr Pi)
        self.logo_sfx = load_asset(1, "audio/shugr_pi.wav")
        if self.logo_sfx:
            self.logo_sfx.set_volume(.75)
        self.played_sound = False

        self.menu_swish_fx = load_asset(1, "audio/menu_swish.wav")
        self.menu_swish_fx.set_volume(.4)
        self.menu_up_fx = load_asset(1, "audio/menu_up.wav")
        self.menu_up_fx.set_volume(.2)
        self.menu_down_fx = load_asset(1, "audio/menu_down.wav")
        self.menu_down_fx.set_volume(.2)
        load_asset(3, "audio/shugr_pi_bg.mp3")
        pygame.mixer.music.set_volume(.2)
        self.sfx_channel = pygame.mixer.Channel(1)
        self.sfx_channel.set_volume(.7)

        # create transition 'curtain'
        self.black_screen = pygame.Surface(self.display.get_size()).convert_alpha()
        self.black_screen.fill(DARK_GRAY)
        self.black_screen.set_colorkey(WHITE)
        self.screen_alpha = 255
        self.black_screen.set_alpha(self.screen_alpha)
        self.screen_text = ""

        # scan for valid games
        self.games = self.scan_games()

        # get titles
        self.titles = []
        for game, configs in self.games.items():
            self.titles.append(configs["name"])

        # misc game variables
        self.game_index = 0
        self.title_index = 0
        self.started_game = False

        # create wheel UI element
        self.wheel = WheelUI(half_display_x, half_display_y + 60, 175, 55, self.games, self.fail_image)

        # create sub-menu
        self.sub_menu = SubMenu(self.titles[self.game_index])

        # create install-menu
        self.install_menu = InstallMenu(self.titles[self.title_index])
        self.install = False

        # error messages
        self.error_message_group = pygame.sprite.Group()

        # top banner items
        self.selection_items = [pygame.Rect((5, 1, 80, 28)), pygame.Rect((display_width - 123, 1, 32, 28)), pygame.Rect((-10, -10, 1, 1))]
        self.selection_names = ["24-hour", "Network", "Battery"]
        self.toggle_clock = False

    def setup_placeholder(self):
        logger.warning("'games' directory does not exist")

        os.makedirs(os.path.join(PATH, "placeholder"))
        with open(os.path.join(PATH, "placeholder", "main.py"), "w") as f:
            f.write('raise Exception("not a real game")')
            f.close()

        with open(os.path.join(PATH, "placeholder", "game_config.json"), "w") as f:
            pygame.image.save(load_asset(0, "images/placeholder_thumb.png"), os.path.join(PATH, "placeholder", "thumbnail.png"))
            f.write('{"name": "Placeholder", "thumbnail": "thumbnail.png", "run_type": ".py", "use_venv": 0}')
            f.close()

        logger.info("Created 'games' directory")

    def scan_games(self):
        # create master games directory
        if not os.path.exists(PATH):
            self.setup_placeholder()

        # get all game directories
        game_dirs = [d for d in os.listdir(PATH) if os.path.isdir(os.path.join(PATH, d))]

        # default configuration data for displaying games in UI
        DEFAULT_DISPLAY_CONFIG = {"name": "Name Not Available",
                                  "thumbnail": 0,
                                  "run_type": ".py",
                                  "use_venv": 0,
                                  "python_version": "3.13"}

        # get all valid games
        games = {}
        for d in game_dirs:
            # possible game paths
            main_game_py = os.path.join(PATH, d, "main.py")
            main_game_bin = os.path.join(PATH, d, "main.bin")

            # configuration data for displaying games in UI
            config_data = DEFAULT_DISPLAY_CONFIG

            # if a valid game is encountered
            if os.path.exists(main_game_py) or os.path.exists(main_game_bin):
                logger.info(f"Detected valid game: '{d}'")

                # get config file
                config_file = os.path.join(PATH, d, "game_config.json")

                # if file does not exist, make one
                if not os.path.exists(config_file):
                    logger.error(f"'{d}' configurations do not exist. Revert to default")
                    with open(config_file, "w") as f:
                        json.dump(DEFAULT_DISPLAY_CONFIG, f)
                # if file does exist, read it
                else:
                    logger.info(f"Detected configurations in '{d}'")
                    with open(config_file, "r") as f:
                        config_data = json.load(f)
                    # if thumbnail exists, load it
                    if config_data["thumbnail"] != DEFAULT_DISPLAY_CONFIG["thumbnail"]:
                        thumb_img = load_asset(0, os.path.join(PATH, d, config_data["thumbnail"]))
                        logger.info(f"Valid thumbnail detected in '{d}'")
                    else:
                        thumb_img = self.fail_image
                        logger.error(f"No thumbnail detected in '{d}'. Revert to default")
                    config_data["thumbnail"] = thumb_img

                # add game/configuration to games
                games[d] = config_data

        return games

    def update_internet_connection(self):
        try:
            while self.running:
                time.sleep(3)
                self.internet_connection = check_internet_status()
        except:
            logger.error("Failed to update internet status")

    def run(self):
        while self.running:
            # fill screen with dark gray
            self.display.fill(DARK_GRAY)

            # check for internet
            self.internet_connection = check_internet_status()

            # startup logo
            if self.master_phase == 0:
                self.display.fill((30, 30, 30))
                self.logo_img.set_alpha(self.logo_alpha)
                self.display.blit(self.logo_img, (half_display_x - self.logo_img.get_width() // 2, half_display_y - self.logo_img.get_height() // 2))
                if self.start_timer:
                    self.start_timer -= 1
                    if self.start_timer <= 120:
                        if self.logo_alpha < 255:
                            self.logo_alpha += 5
                        else:
                            self.logo_alpha = 255
                            if not self.played_sound and sound_working:
                                self.sfx_channel.play(self.logo_sfx)
                                self.played_sound = True
                else:
                    if self.logo_timer:
                        self.logo_timer -= 1
                        if self.logo_timer <= 90:
                            if self.logo_alpha > 0:
                                self.logo_alpha -= 5
                            else:
                                self.logo_alpha = 0
                    else:
                        self.logo_timer = 0
                        if self.logo_alpha == 0:
                            self.master_phase = 1
                            self.logo_alpha = 0
                            if sound_working:
                                pygame.mixer.music.play(-1, fade_ms=3000)
                            logger.info("Finished initializing ShugrPi OS")
                            logger.info("Running main loop")

            # main menu
            elif self.master_phase == 1:
                # update scroll
                if self.scroll_x != self.target_scroll_x:
                    diff = (self.target_scroll_x - self.scroll_x)
                    if abs(diff) > 1:
                        self.scroll_x += diff * 0.15
                    else:
                        self.scroll_x = self.target_scroll_x
                if self.scroll_y != self.target_scroll_y:
                    diff2 = (self.target_scroll_y - self.scroll_y)
                    if abs(diff2) > 1:
                        self.scroll_y += diff2 * 0.15
                    else:
                        self.scroll_y = self.target_scroll_y

                # draw logo
                self.bg_logo.update()
                self.bg_logo.draw(self.display)

                # draw wheel
                self.wheel.update(self.scroll_x, self.scroll_y, self.master_index)
                self.wheel.draw(self.display, self.scroll_x, self.scroll_y)

                # draw sub-menu
                self.title_index = abs(len(self.games) - 1 - self.game_index) + 1
                self.title_index %= len(self.games)
                self.sub_menu.render(self.display, self.scroll_x, self.titles[self.title_index])

                # draw install-menu
                self.install_menu.render(self.display, self.titles[self.title_index], self.sub_phase)

                # draw banners
                self.display.blit(self.banner_top, self.banner_top_rect)
                self.display.blit(self.banner_bottom, self.banner_bottom_rect)

                # draw banner items
                self.wifi_image = self.wifi_images[self.internet_connection]
                self.display.blit(self.wifi_image, (display_width - 120, 2))
                draw_text(self.display, time.strftime("%H:%M") if not self.toggle_clock else time.strftime("%I:%M"), 45, self.banner_top_rect.centery, WHITE, 13, centered=True)
                if is_ce:
                    battery_percent = pygame.system.get_power_state().battery_percent if pygame.system.get_power_state().battery_percent is not None else 100
                    self.display.blit(self.battery_image if battery_percent > 25 else self.battery_image_low, (display_width - 80, self.banner_top_rect.centery - self.battery_image.get_height() // 2))
                    draw_text(self.display, str(battery_percent) + "%", display_width - 30, self.banner_top_rect.centery, WHITE if battery_percent > 25 else (204, 0, 0), 12, centered=True)
                if len(self.error_message_group) == 0:
                    draw_text(self.display, int(self.clock.get_fps()), display_width - 40, self.banner_top_rect.bottom + 5, WHITE, 13)

                # draw game label
                if self.sub_phase == 0:
                    draw_text(self.display, self.titles[self.title_index], half_display_x, self.banner_bottom_rect.centery, WHITE, 10, centered=True)

                # draw top selection box
                if self.master_index == 0:
                    temp_rect = self.selection_items[self.top_index]
                    temp_name = self.selection_names[self.top_index]
                    self.selection_names[0] = "24-hour" if not self.toggle_clock else "12-hour"
                    pygame.draw.rect(self.display, WHITE, temp_rect, 2)
                    draw_text(self.display, temp_name.lower().capitalize(), temp_rect.centerx, temp_rect.bottom + 10, WHITE, 8, centered=True)

                # draw errors
                self.error_message_group.update(self.display)

                # run installation (if applicable)
                if self.install:
                    self.run_installation()

                # run game
                if self.started_game:
                    self.run_game()
                else:
                    if self.screen_alpha > 0:
                        self.screen_alpha -= 20
                    else:
                        self.screen_alpha = 0

                # draw black screen
                self.black_screen.set_alpha(self.screen_alpha)
                self.display.blit(self.black_screen, (0, 0))

                # draw message
                if self.screen_alpha >= 255 and self.started_game:
                    draw_text(self.display, self.screen_text, display_width // 2, display_height // 2, WHITE, 20, centered=True)

            # draw screen
            self.screen.blit(self.display, (screen_width // 2 - display_width // 2, screen_height // 2 - display_height // 2))
            pygame.display.flip()

            # events (do NOT draw anything after this chunk)
            for event in pygame.event.get():
                # shutdown
                if event.type == pygame.QUIT:
                    self.shutdown()

                # key presses
                if event.type == pygame.KEYDOWN:
                    # skip intro
                    if self.master_phase == 0:
                        self.start_timer = 0
                        self.logo_timer = 60

                    # main menu
                    if self.master_phase == 1:
                        # select game
                        if self.sub_phase == 0:
                            if event.key == pygame.K_LEFT:
                                if self.master_index == 1:
                                    self.game_index -= 1
                                    self.game_index %= len(self.games)
                                    self.wheel.target_index = self.game_index
                                    if sound_working:
                                        self.sfx_channel.play(self.menu_swish_fx)
                                elif self.master_index == 0:
                                    self.top_index = 0
                            if event.key == pygame.K_RIGHT:
                                if self.master_index == 1:
                                    self.game_index += 1
                                    self.game_index %= len(self.games)
                                    self.wheel.target_index = self.game_index
                                    if sound_working:
                                        self.sfx_channel.play(self.menu_swish_fx)
                                elif self.master_index == 0:
                                    self.top_index = 1
                            if event.key == pygame.K_UP:
                                if self.master_index == 1:
                                    self.master_index = 0
                                    self.top_index = 0
                                    self.target_scroll_y = 15
                            if event.key == pygame.K_DOWN:
                                if self.master_index == 0:
                                    self.master_index = 1
                                    self.target_scroll_y = 0
                        # select option in sub-menu
                        elif self.sub_phase == 1:
                            if self.master_index == 1:
                                if event.key == pygame.K_LEFT or event.key == pygame.K_UP:
                                    self.sub_menu.index -= 1
                                    self.sub_menu.index %= len(self.sub_menu.options)
                                if event.key == pygame.K_RIGHT or event.key == pygame.K_DOWN:
                                    self.sub_menu.index += 1
                                    self.sub_menu.index %= len(self.sub_menu.options)
                        # select option in install-menu
                        elif self.sub_phase == 2:
                            if self.install_menu.text_ready and not self.install and self.master_index == 1:
                                if event.key == pygame.K_LEFT or event.key == pygame.K_UP:
                                    self.install_menu.index -= 1
                                    self.install_menu.index %= len(self.install_menu.options)
                                if event.key == pygame.K_RIGHT or event.key == pygame.K_DOWN:
                                    self.install_menu.index += 1
                                    self.install_menu.index %= len(self.install_menu.options)

                        # bring up sub-menu / execute game / install game
                        if event.key == pygame.K_RETURN:
                            if self.master_index == 1:
                                if self.sub_phase == 0:
                                    self.sub_phase = 1
                                    self.target_scroll_x = -self.wheel.width
                                    self.sub_menu.index = 0
                                    if sound_working:
                                        self.sfx_channel.play(self.menu_up_fx)
                                elif self.sub_phase == 1:
                                    if self.sub_menu.index == 0:
                                        game_folder = list(self.games.keys())[self.title_index]
                                        self.execute_game(game_folder)
                                        if sound_working:
                                            self.sfx_channel.play(self.menu_up_fx)
                                    elif self.sub_menu.index == 1:
                                        self.sub_phase = 0
                                        self.target_scroll_x = 0
                                        if sound_working:
                                            self.sfx_channel.play(self.menu_down_fx)
                                elif self.sub_phase == 2:
                                    if self.install_menu.text_ready and not self.install:
                                        if self.install_menu.index == 0:
                                            if self.install_menu.options[0] == "Install":
                                                game_folder = list(self.games.keys())[self.title_index]
                                                self.install_game(game_folder)
                                            else:
                                                self.sub_phase = 1
                                                self.install_menu.prompt = self.install_menu.original_prompt
                                                self.install_menu.activate = False
                                                if sound_working:
                                                    self.sfx_channel.play(self.menu_down_fx)
                                        else:
                                            self.sub_phase = 1
                                            self.install_menu.prompt = self.install_menu.original_prompt
                                            self.install_menu.activate = False
                                            if sound_working:
                                                self.sfx_channel.play(self.menu_down_fx)
                            else:
                                if self.top_index == 0:
                                    self.toggle_clock = not self.toggle_clock

                        # exit out of sub-menus
                        if event.key == pygame.K_BACKSPACE:
                            if self.master_index == 1:
                                if self.sub_phase == 1:
                                    self.sub_phase = 0
                                    self.target_scroll_x = 0
                                    if sound_working:
                                        self.sfx_channel.play(self.menu_down_fx)
                                elif self.sub_phase == 2 and self.install_menu.text_ready and not self.install:
                                    if sound_working:
                                        self.sfx_channel.play(self.menu_down_fx)
                                    self.sub_phase = 1
                                    self.install_menu.prompt = self.install_menu.original_prompt
                                    self.install_menu.activate = False
                            else:
                                self.master_index = 1
                                self.target_scroll_y = 0

                    # shutdown
                    if event.key == pygame.K_ESCAPE:
                        self.shutdown()

            # keep clock running
            self.clock.tick(FPS)

    def install_game(self, game_folder):
        requirements_path = os.path.join(PATH, game_folder, "requirements.txt")
        self.game_folder = game_folder
        if os.path.exists(requirements_path) and self.internet_connection:
            self.install_folder = os.path.join(PATH, game_folder)
            logger.info(f"Attempting '{self.titles[self.title_index]}' installation...")
            self.install = True
            self.install_menu.prompt = "Preparing Installation..."
            self.install_menu.activate = True
            self.install_menu.render(self.display, self.titles[self.title_index], self.sub_phase)
            self.screen.blit(self.display, (screen_width // 2 - display_width // 2, screen_height // 2 - display_height // 2))
            pygame.display.flip()
            self.clock.tick(FPS)
        else:
            if not os.path.exists(requirements_path):
                self.install_menu.prompt = "Installation unavailable!"
                logger.error("Unable to find installation requirements")
            if not self.internet_connection:
                self.install_menu.prompt = "ShugrPi must be connected to the\n\nInternet when installing games!"
                logger.error("Unable to install without internet connection")
            self.install_menu.options = ["OK"]

    def run_installation(self):
        # create venv
        venv_dir = os.path.join(self.install_folder, ".venv")
        if self.games[self.game_folder].get("python_version"):
            logger.info("'{}' requires Python{}".format(self.titles[self.title_index], self.games[self.game_folder]["python_version"]))
        game_python = find_python_executable(self.is_shugr_pi, logger, self.games[self.game_folder].get("python_version"))
        if game_python:
            logger.info(f"Using Python: {game_python}")
            venv_proc = subprocess.Popen([game_python, "-m",  "venv", venv_dir], cwd=self.install_folder)
            venv_proc.communicate()
        else:
            venv_proc = subprocess.Popen(["python", "-m",  "venv", venv_dir], cwd=self.install_folder)
            venv_proc.communicate()
        logger.info(f"Added venv in '{self.install_folder}'...")

        # install dependencies
        venv_path = os.path.join(self.install_folder, ".venv", "bin" if self.is_shugr_pi else "Scripts")
        venv_python = os.path.join(venv_path, "python3" if self.is_shugr_pi else "python.exe")
        req_path = os.path.join(self.install_folder, "requirements.txt")
        proc = subprocess.Popen([venv_python, "-m", "pip", "install", "-r", req_path], cwd=self.install_folder, stderr=subprocess.PIPE, text=True)
        logger.info("Installing dependencies using pip (from local venv)...")

        self.install_menu.prompt = f"Installing {self.titles[self.title_index]}..."
        self.install_menu.render(self.display, self.titles[self.title_index], self.sub_phase)
        self.install_menu.activate = True
        self.screen.blit(self.display, (screen_width // 2 - display_width // 2, screen_height // 2 - display_height // 2))
        pygame.display.flip()
        self.clock.tick(FPS)

        stdout, stderr = proc.communicate()

        # catch errors
        if len(stderr.splitlines()) > 1 and proc.returncode != 0:
            proc_error = stderr.splitlines()[-1]
            self.install_menu.prompt = ["Failed to install", f"{self.titles[self.title_index]}!"]
            self.install_menu.options = ["OK"]
            self.install_menu.activate = False
            logger.error(f"Failed to install '{self.titles[self.title_index]}' | {proc_error}")

            temp_venv = os.path.join(self.install_folder, ".venv")

            if os.path.exists(temp_venv):
                try:
                    rmtree(temp_venv)
                    logger.info("Cleaned up faulty installation")
                except Exception as e:
                    logger.error(f"Failed to clean faulty installation: {e}")

        else:
            self.install_menu.prompt = f"Installed {self.titles[self.title_index]}!"
            self.install_menu.options = ["OK"]
            self.install_menu.activate = False
            logger.info(f"Installed {self.titles[self.title_index]}!")

        self.install = False

    def execute_game(self, game_folder):
        self.game_path = os.path.abspath(os.path.join(PATH, game_folder))
        self.main_app = os.path.join(self.game_path, f"main{self.games[game_folder]['run_type']}")
        self.venv = None
        # check if using a local venv
        if self.games[game_folder]['use_venv']:
            possible_venvs = [".venv", "venv"]
            for possible_venv in possible_venvs:
                venv = os.path.join(self.game_path, possible_venv)
                if os.path.exists(venv):
                    self.venv = os.path.abspath(venv)
                    logger.info(f"Detected local environment: Using '{venv}'")
            if self.venv is None:
                logger.warning(f"'{self.titles[self.title_index]}' is not fully installed")
                self.sub_phase = 2
                self.install_menu.options = ["Install", "Cancel"]
                self.install_menu.index = 0

        if self.sub_phase != 2:
            logger.info(f"Started '{self.titles[self.title_index]}' as `main{self.games[game_folder]['run_type']}`")
            self.started_game = True

    def run_game(self):
        try:
            # darken screen
            if self.screen_alpha < 255:
                self.screen_alpha += 20
                self.screen_text = "Running Game..."
            # run the actual game itself
            else:
                if sound_working:
                    pygame.mixer.music.fadeout(1000)
                self.screen_alpha = 255

                env = os.environ.copy()
                env['DISPLAY'] = ':0'

                if self.venv:
                    python_exec = os.path.join(self.game_path, ".venv", "Scripts" if not self.is_shugr_pi else "bin", "python")
                else:
                    python_exec = "python"

                processes = [python_exec, self.main_app] if self.main_app.endswith(".py") else self.main_app

                self.proc = subprocess.Popen(processes, stderr=subprocess.PIPE, cwd=self.game_path, text=True, env=env)

                if sound_working:
                    self.sfx_channel.stop()

                # Raise the game window on top
                if self.is_shugr_pi:
                    time.sleep(1)
                    subprocess.run(['wmctrl', '-a', self.titles[self.title_index]])

                stdout, stderr = self.proc.communicate()
                del self.proc

                ignored_errors = ["libpng warning: iCCP: known incorrect sRGB profile"]
                if len(stderr.splitlines()) > 1:
                    proc_error = stderr
                    if proc_error.splitlines()[-1] not in ignored_errors:
                        temp_msg = f"'{self.titles[self.title_index]}' has crashed due to the following problem:\n{proc_error}"
                        temp_msg_alt = f"{self.titles[self.title_index]} has crashed due to '{proc_error.splitlines()[-1]}'"
                        logger.error(temp_msg)
                        error_message = ErrorMessage(temp_msg_alt)
                        self.error_message_group.add(error_message)
                    else:
                        logger.info(f"'{self.titles[self.title_index]}' terminated successfully")
                else:
                    logger.info(f"'{self.titles[self.title_index]}' terminated successfully")
                self.started_game = False
                self.sub_phase = 0
                self.target_scroll_x = 0
                self.screen_text = ""
                if sound_working:
                    pygame.mixer.music.play(-1, fade_ms=3000)

        except Exception as e:
            logger.error(f"'{self.titles[self.title_index]}' failed to start: {e}")
            if sound_working:
                pygame.mixer.music.play(-1, fade_ms=3000)
            self.started_game = False
            self.sub_phase = 0
            self.target_scroll_x = 0
            self.screen_text = ""

    def shutdown(self):
        logger.info("Shutting down...")
        self.running = False
        pygame.quit()
        self.wifi_thread.join()
        logger.info("Shutdown complete!")
        sys.exit()


# run the ShugrPi OS
shugr_pi_os = ShugrPiOS(is_shugr_pi)
try:
    shugr_pi_os.run()
except KeyboardInterrupt:
    logger.info("Keyboard Interruption")
    shugr_pi_os.shutdown()
