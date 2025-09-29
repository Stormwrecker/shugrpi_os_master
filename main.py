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

# the operating system
master_platform = platform.system().lower()
is_shugr_pi = True if master_platform == "linux" else False

# set necessary environment variables
if is_shugr_pi:
    os.environ["SDL_VIDEODRIVER"] = "kmsdrm"
    os.environ["SDL_VIDEO_SYNC"] = "1"
    os.environ["SDL_AUDIODRIVER"] = "alsa"
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
logger.info("Successfully loaded Pygame-CE")

# import other modules
import threading
import random
import time
import json
import math
from utils import *

# import RPi.GPIO if available
try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

# set up pygame
pygame.init()
sound_working = True
try:
    pygame.mixer.init()
    logger.info("Initialized pygame.mixer")
except:
    sound_working = False
    logger.error("Initializing pygame.mixer failed; No sound available")

# setup window and display sizes
display_info = pygame.display.Info()
display_width, display_height = (800, 450)
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

# load assets
def load_asset(kind, path, flag=False):
    """0: image, 1: sound, 2: font, 3: other"""
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
        # other
        elif kind == 3:
            return os.path.join(base_path, path)
    except:
        return None


# text handling
font_cache = {}
all_fonts = []
default_font = os.path.join(base_path, "fonts/PressStart2P.ttf")
def get_font(font, size):
    actual_font = str(font) + str(size)
    if actual_font not in font_cache:
        font_cache[actual_font] = pygame.font.Font(font, size)

    return font_cache[actual_font]


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
            self.thumbnails.append(temp_thumb)
            self.item_angle = math.radians(self.angle_increment * index + 90)
            x = int(math.cos(self.item_angle) * self.width) + self.centerx
            y = int(math.sin(self.item_angle) * self.height) + self.centery
            wheel_item = WheelItem(index, self.games[key]["name"], temp_thumb, x, y, self.item_angle)
            self.item_group.add(wheel_item)

    def update(self):
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
        self.item_group.update(self)

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

    def draw(self, display):
        pygame.draw.ellipse(display, GRAY, pygame.Rect((self.centerx - (self.width * 1.5),
                                                        self.centery - 20, self.width * 3,
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

    def update(self, wheel):
        # get wheel_ui values for positioning
        self.w_width = wheel.width
        self.w_height = wheel.height
        self.w_centerx = wheel.centerx
        self.w_centery = wheel.centery

        current_angle = self.base_angle + math.radians(wheel.master_angle)

        # center rect based on wheel_ui pos
        self.rect.midbottom = (int(math.cos(current_angle) * self.w_width) + self.w_centerx,
                            int(math.sin(current_angle) * self.w_height) + self.w_centery + 40)

        self.z_depth = math.sin(current_angle) + 2

        # Draw selection frame if this is the selected item
        bottom_item = wheel.get_bottom_item()
        if bottom_item and self.index == bottom_item.index:
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
            self.image = pygame.transform.scale(self.original_image, (size_x, size_y))
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


"""Master SHUGR Pi Operating System"""
class ShugrPiOS:
    def __init__(self, is_shugr_pi):
        self.is_shugr_pi = is_shugr_pi
        logger.info(f"Running on ShugrPi: {'yes' if self.is_shugr_pi else 'no'}")

        if self.is_shugr_pi:
            flags = pygame.NOFRAME | pygame.SCALED | pygame.FULLSCREEN
        else:
            flags = pygame.NOFRAME
        self.screen = pygame.display.set_mode((screen_width, screen_height), flags)
        self.display = pygame.Surface((display_width, display_height)).convert()
        logger.info("Initialized display")

        self.clock = pygame.time.Clock()

        self.master_phase = 0
        self.sub_phase = 0

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
        self.wifi_images = {True:pygame.transform.scale(load_asset(0, "images/wifi_on.png"), (30, 30)), False:pygame.transform.scale(load_asset(0, "images/wifi_off.png"), (30, 30))}
        for k, image in self.wifi_images.items():
            image.set_colorkey(BLACK)

        # wifi connection setup
        self.internet_connection = check_internet_status()
        self.wifi_image = self.wifi_images[self.internet_connection]
        self.wifi_thread = threading.Thread(target=self.update_internet_connection, daemon=True)
        self.wifi_thread.start()
        logger.info(f"Connected to internet (startup): {'yes' if self.internet_connection else 'no'}")

        # logo image setup
        self.original_logo_img = load_asset(0, "images/logo.png", True)
        self.logo_img = pygame.transform.scale(self.original_logo_img, (int(165 * 3), int(165 * 3)))
        self.big_logo_img = pygame.transform.scale(self.original_logo_img, (int(165 * 4), int(165 * 4)))
        self.logo_alpha = 0
        self.logo_img.set_alpha(self.logo_alpha)

        # create BG logo object
        self.bg_logo = BGLogo(self.big_logo_img)

        # super amazing sound effect (crucial for the Shugr Pi)
        self.logo_sfx = load_asset(1, "audio/shugr_pi.wav")
        self.logo_sfx.set_volume(1)
        self.played_sound = False

        # create transition 'curtain'
        self.black_screen = pygame.Surface(self.display.get_size()).convert_alpha()
        self.black_screen.fill(DARK_GRAY)
        self.black_screen.set_colorkey(WHITE)
        self.screen_alpha = 255
        self.black_screen.set_alpha(self.screen_alpha)
        self.screen_text = ""

        # scan for valid games
        self.games = self.scan_games()
        for i in range(3):
            self.games[i] = {"name":random.choice(["Something", "Whatever"]), "thumbnail":self.fail_image}
        self.titles = []
        for game, configs in self.games.items():
            self.titles.append(configs["name"])
        self.game_index = 0

        # create wheel UI element
        self.wheel = WheelUI(half_display_x, half_display_y + 60, 175, 55, self.games, self.fail_image)

    def scan_games(self):
        # create master games directory
        if not os.path.exists(os.path.join(base_path, "games")):
            os.makedirs(os.path.join(base_path, "games"))

        # get all game directories
        game_dirs = [d for d in os.listdir(PATH) if os.path.isdir(os.path.join(PATH, d))]

        # default configuration data for displaying games in UI
        DEFAULT_DISPLAY_CONFIG = {"name": "Name Not Available",
                                  "thumbnail": 0}

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
                config_file = os.path.join(PATH, d, "display_config.json")

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
                                self.logo_sfx.play()
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
                            logger.info("Finished initializing ShugrPi OS")
                            logger.info("Running main loop")

            # main menu
            elif self.master_phase == 1:

                # draw logo
                self.bg_logo.update()
                self.bg_logo.draw(self.display)

                # draw wheel
                self.wheel.update()
                self.wheel.draw(self.display)

                # draw banners
                self.display.blit(self.banner_top, self.banner_top_rect)
                self.display.blit(self.banner_bottom, self.banner_bottom_rect)

                # draw banner items
                self.wifi_image = self.wifi_images[self.internet_connection]
                self.display.blit(self.wifi_image, (screen_width - 70, 0))

                # draw game label
                draw_text(self.display, self.titles[self.game_index], half_display_x, self.banner_bottom_rect.centery, WHITE, 10, centered=True)

            # draw screen
            self.screen.blit(self.display, (0, 0))
            pygame.display.flip()

            # events (do NOT draw anything after this chunk)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.shutdown()
                if event.type == pygame.KEYDOWN:
                    if self.master_phase == 0:
                        self.start_timer = 0
                        self.logo_timer = 60
                    if event.key == pygame.K_LEFT:
                        self.game_index -= 1
                        self.game_index %= len(self.games)
                        self.wheel.target_index = self.game_index
                    if event.key == pygame.K_RIGHT:
                        self.game_index += 1
                        self.game_index %= len(self.games)
                        self.wheel.target_index = self.game_index
                    if event.key == pygame.K_ESCAPE:
                        self.shutdown()

            # keep clock running
            self.clock.tick(FPS)

    def shutdown(self):
        logger.info("Shutting down...")
        self.running = False
        pygame.quit()
        logger.info("Shutdown complete!")
        sys.exit()


# run the ShugrPi OS
shugr_pi_os = ShugrPiOS(is_shugr_pi)
try:
    shugr_pi_os.run()
except KeyboardInterrupt:
    logger.info("Keyboard Interruption")
    shugr_pi_os.shutdown()
