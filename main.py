"""
The official SHUGR PI Operating System
designed specifically for the SHUGR PI

Code and Assets by Stormwrecker
All Rights Reserved
"""

# import setup modules
import os
import platform

# the operating system
master_platform = platform.system().lower()
is_shugr_pi = True if master_platform == "linux" else False

# set necessary environment variables
if is_shugr_pi:
    os.environ["SDL_VIDEODRIVER"] = "kmsdrm"
    os.environ["SDL_VIDEO_SYNC"] = "1"
    os.environ["SDL_AUDIODRIVER"] = "alsa"
    os.environ["SDL_VIDEO_ALLOW_SCREENSAVER"] = "0"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# master directory
base_path = os.path.abspath(".")
PATH = "C:/Users/rebel/PycharmProjects/"

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
from utils import *
import random
import time

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


"""Logo for floating in the BG"""
class BGLogo(pygame.sprite.Sprite):
    def __init__(self, img):
        pygame.sprite.Sprite.__init__(self)
        self.original_image = img
        self.reset()
        self.start_timer = 120

    def reset(self):
        self.image = self.original_image.copy()
        self.image = pygame.transform.rotate(self.image, random.randint(-20, 20))
        self.rect = self.image.get_rect()
        self.rect.center = (random.randint(75, screen_width - 75), random.randint(50, screen_height - 50))
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
        self.wait_timer = 180
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
        self.original_thumbnail = pygame.transform.scale(pygame.image.load("images/fail_load.png").convert_alpha(), (180, 180))

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
        self.games = {}

        # master run variable
        self.running = True

    def scan_games(self):
        if not os.path.exists(os.path.join(base_path, "games")):
            os.makedirs(os.path.join(base_path, "games"))
        game_dirs = [d for d in os.listdir(PATH) if os.path.isdir(os.path.join(PATH, d))]
        valid_games = []
        for d in game_dirs:
            main_game_py = os.path.join(PATH, d, "main.py")
            main_game_app = os.path.join(PATH, d, "main.bin")
            if os.path.exists(main_game_py) or os.path.exists(main_game_app):
                valid_games.append(d)
        return valid_games

    def update_internet_connection(self):
        try:
            while True:
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

                # draw banners
                self.display.blit(self.banner_top, self.banner_top_rect)
                self.display.blit(self.banner_bottom, self.banner_bottom_rect)

                # draw banner items
                self.wifi_image = self.wifi_images[self.internet_connection]
                self.display.blit(self.wifi_image, (screen_width - 70, 0))

            # draw screen
            self.screen.blit(self.display, (0, 0))
            pygame.display.flip()

            # events (do NOT draw anything after this chunk)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.shutdown()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.shutdown()

            self.clock.tick(FPS)

    def shutdown(self):
        logger.info("Shutting down...")
        self.running = False
        pygame.quit()


# run the ShugrPi OS
shugr_pi_os = ShugrPiOS(is_shugr_pi)
try:
    shugr_pi_os.run()
except KeyboardInterrupt:
    logger.info("Keyboard Interruption")
    shugr_pi_os.shutdown()

logger.info("Shutdown complete!")
