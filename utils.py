"""Various utilities necessary to run the SHUGRPi OS"""

# import setup modules
import os
import platform
import pygame
import logging
import time
import subprocess
from socket import gethostbyname, gethostname

# misc values
base_path = os.path.dirname(os.path.abspath(__file__))
is_shugrpi = False
default_font = os.path.join(base_path, "fonts", "Kenney_Bold.ttf")
font_cache = {}

# set up logger
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
    handlers=[logging.FileHandler(os.path.join(base_path, "session.log"), "w"),
              logging.StreamHandler()]
)
logger = logging.getLogger("SHUGRPi")


# compatibility management
class CompatibilityManager:
    def __init__(self, logger):
        self.system = {"machine":platform.machine().lower(), "platform":platform.system().lower()}

        self.is_shugrpi = False
        if self.system["machine"] == "aarch64" and self.system["platform"] == "linux":
            self.is_shugrpi = True
        logger.info(f"Running on SHUGRPi: {'yes' if is_shugrpi else 'no'}")

        self.base_path = self._update_paths(self.system["platform"])
        self.audio_driver = None

        self._update_env()

    def _update_paths(self, platform):
        base_path = None
        if platform == "windows":
            base_path = os.path.dirname(os.path.abspath(__file__))
        elif platform == "linux":
            base_path = os.path.dirname(os.path.abspath(__file__))
        return base_path

    def init_audio_and_driver(self, pg, env, logger, is_shugrpi):
        drivers = ["wasapi", "alsa", "dummy"]

        for driver in drivers:
            # try:
            env["SDL_AUDIODRIVER"] = driver
            pg.mixer.quit()


            if is_shugrpi:
                pg.mixer.init(48000)
            else:
                pg.mixer.init()

            logger.info(f"Using audio driver: {pygame.mixer.get_driver()}")
            break

            # except pg.error as e:
            #     logger.error(f"Failed audio driver: {driver} ({e})")

        if self.audio_driver is None:
            env["SDL_AUDIODRIVER"] = "dummy"
            pg.mixer.quit()
            pg.mixer.init()
            self.audio_driver = "dummy"
            logger.error(f"No audio drivers available; Revert to dummy")

        return pg, env.copy()


    def _update_env(self):
        if self.is_shugrpi:
            os.environ["DISPLAY"] = ":0"
            os.environ['AUDIODEV'] = 'hdmi:CARD=vc4hdmi0,DEV=0'
            os.environ["SDL_VIDEO_ALLOW_SCREENSAVER"] = "0"
        os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "0"

    def init(self):
        return self.is_shugrpi, self.base_path, os.environ.copy()


# audio management
class AudioManager:
    def __init__(self, logger, is_shugrpi):
        # master library for sounds and music tracks
        self.master_sounds = {}
        self.master_music_tracks = {}

        self._load_sounds()
        self._load_musics()

    def _get_sound_path(self, path):
        return os.path.join(base_path, "audio", path + ".wav")

    def _get_music_path(self, path):
        return os.path.join(base_path, "audio", path + ".mp3")

    def _load_sounds(self):
        self.master_sounds["logo"] = [pygame.mixer.Sound(self._get_sound_path("shugrpi_alt")), .75, False]
        self.master_sounds["menu_swish"] = [pygame.mixer.Sound(self._get_sound_path("menu_swish")), .2, False]
        self.master_sounds["menu_up"] = [pygame.mixer.Sound(self._get_sound_path("menu_up")), .2, False]
        self.master_sounds["menu_down"] = [pygame.mixer.Sound(self._get_sound_path("menu_down")), .2, False]

    def _load_musics(self):
        self.master_music_tracks["shugrpi_bg"] = [self._get_music_path("shugrpi_bg"), .2]

    def play_music(self, music):
        pygame.mixer.music.fadeout(1000)

        pygame.mixer.music.load(self.master_music_tracks[music][0])
        pygame.mixer.music.set_volume(self.master_music_tracks[music][1])
        pygame.mixer.music.play(-1, fade_ms=500)

    def stop_music(self):
        pygame.mixer.music.fadeout(500)

    def play_sound(self, sound, in_loop=False):
        if not self.master_sounds[sound][2]:
            self.master_sounds[sound][0].set_volume(self.master_sounds[sound][1])
            self.master_sounds[sound][0].play(0)
            self.master_sounds[sound][2] = in_loop

    def stop_sound(self, sound):
        self.master_sounds[sound][0].stop()
        self.master_sounds[sound][2] = False

    def reset_sounds(self):
        for sound in self.master_sounds:
            self.master_sounds[sound][2] = False

    def stop_all(self):
        pygame.mixer.stop()


""" Image Utilities """

def load_image(path, alpha=False):
    try:
        if not alpha:
            return pygame.image.load(path).convert()
        else:
            return pygame.image.load(path).convert_alpha()
    except Exception as e:
        logger.warning(f"unable to load '{path}': {e}")
        return pygame.image.load(os.path.join(base_path, "images", "fail_load.png")).convert()


def preload_images():
    master_images = {}
    image_path = os.path.join(base_path, "images")
    alpha_images = ["icon"]
    for temp_file in os.listdir(image_path):
        temp_path = os.path.join(image_path, temp_file)
        if os.path.isfile(temp_path):
            do_alpha = True if temp_file.split(".")[0] in alpha_images else False
            master_images[temp_file.split(".")[0]] = load_image(os.path.join(image_path, temp_file), do_alpha)
    return master_images


def load_thumbnail(thumb_path, fail_image):
    try:
        return pygame.image.load(thumb_path).convert()
    except:
        if thumb_path is not None:
            logger.warning(f"unable to load thumbnail from '{thumb_path}'")
        return fail_image


""" Internet Utilities"""

def check_internet_status():
    my_ip = gethostbyname(gethostname())
    internet_connection = False
    if my_ip != "127.0.0.1":
        internet_connection = True
    return internet_connection


""" Text Utilities """

# font handling
def get_font(font, size):
    actual_font = str(font) + str(size)
    if actual_font not in font_cache:
        font_cache[actual_font] = pygame.font.Font(font, size)

    return font_cache[actual_font]


# text renderer (simpler)
def draw_text(display, text, x, y, color, size, font=default_font, centered=False):
    font = get_font(font, size)
    text_surface = font.render(str(text), False, color)
    text_rect = text_surface.get_rect()
    if centered:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    display.blit(text_surface, text_rect)


# text object (optimized)
class Text(pygame.sprite.Sprite):
    def __init__(self, text, x, y, color, size, font=default_font, centered=False):
        pygame.sprite.Sprite.__init__(self)
        self.text = str(text)
        self.color = color

        self.font = self._get_font(font, size)
        self.image = self.font.render(self.text, False, self.color)
        self.rect = self.image.get_rect()
        self.centered = centered
        self.x = x
        self.y = y

        if self.centered:
            self.rect.center = (self.x, self.y)
        else:
            self.rect.topleft = (self.x, self.y)

    def set_text(self, new_text):
        self.text = str(new_text)
        self.image = self.font.render(self.text, False, self.color)
        self.rect = self.image.get_rect()
        if self.centered:
            self.rect.center = (self.x, self.y)
        else:
            self.rect.topleft = (self.x, self.y)

    def _get_font(self, font, size):
        return get_font(font, size)

    def draw(self, display):
        display.blit(self.image, self.rect)


""" Various Utilities """

# get general information about a game
def get_game_info(game_path, game_app):
    # calculate game size
    total_size = 0
    for root, _, files in os.walk(game_path):
        for file in files:
            temp_size = os.stat(os.path.join(root, file)).st_size
            total_size += temp_size

    # calculate last played
    last_played_raw = os.stat(game_app).st_atime
    last_played = time.ctime(last_played_raw)

    return {"size":round(total_size / 1000000, 1),
            "last_played_raw":last_played_raw,
            "last_played":last_played}


# timer object
class Timer:
    def __init__(self, duration, repeat=False, action=None):
        self.duration = float(duration)
        self.repeat = repeat
        self.action = action

        self.time = 0.0
        self.active = True
        self.finished = False
        self.value = self.duration - self.time

    def update(self, dt):
        if not self.active or self.finished:
            return self.finished

        self.time += dt

        if self.time >= self.duration:
            if self.action and not self.finished:
                self.action()

            if self.repeat:
                self.reset()
            else:
                self.time = self.duration
                self.finished = True

        return self.finished

    def start(self):
        self.active = True

    def stop(self):
        self.active = False

    def reset(self):
        self.time = 0.0
        self.finished = False


__all__ = ["CompatibilityManager",
           "AudioManager",
           "load_image",
           "check_internet_status",
           "get_font",
           "draw_text",
           "Text",
           "get_game_info",
           "logger",
           "load_thumbnail",
           "preload_images",
           "Timer"]
