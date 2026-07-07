"""Various utilities necessary to run the SHUGRPi OS"""

# import setup modules
import os
import platform
import pygame
import logging
import time
import subprocess
from socket import gethostbyname, gethostname
from constants import *

# misc values
base_path = os.path.dirname(os.path.abspath(__file__))
default_font = os.path.join(base_path, "fonts", "Kenney_Bold.ttf")
retro_font = os.path.join(base_path, "fonts", "PressStart2P.ttf")
font_cache = {}

# set up logger
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
    handlers=[logging.FileHandler(os.path.join(base_path, "session.log"), "w"),
              logging.StreamHandler()]
)
logger = logging.getLogger("SHUGRPi")

""" Device Managers """

# compatibility management
class CompatibilityManager:
    def __init__(self, logger):
        """Manage system and environment variables"""
        self.system = {"machine":platform.machine().lower(), "platform":platform.system().lower()}

        self.is_shugrpi = False
        if self.system["machine"] == "aarch64" and self.system["platform"] == "linux":
            self.is_shugrpi = True
        logger.info(f"Running on SHUGRPi device: {'yes' if self.is_shugrpi else 'no'}")

        self.base_path = self._update_paths(self.system["platform"])

    def _update_paths(self, platform):
        base_path = None
        if platform == "windows":
            base_path = os.path.dirname(os.path.abspath(__file__))
        elif platform == "linux":
            base_path = os.path.dirname(os.path.abspath(__file__))
        return base_path

    def _update_env(self):
        if self.is_shugrpi:
            os.environ["DISPLAY"] = ":0"
            os.environ['AUDIODEV'] = 'hdmi:CARD=vc4hdmi0,DEV=0'
            os.environ["SDL_VIDEO_ALLOW_SCREENSAVER"] = "0"
        os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "0"

    def init(self):
        self._update_env()
        return self.is_shugrpi, self.base_path, os.environ.copy()


# audio management
class AudioManager:
    def __init__(self, logger, is_shugrpi):
        # master library for sounds and music tracks
        self.master_sounds = {}
        self.master_music_tracks = {}
        self.working = True

        try:
            self._load_sounds()
            self._load_musics()
        except:
            self.working = False

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
        if self.working:
            pygame.mixer.music.fadeout(1000)

            pygame.mixer.music.load(self.master_music_tracks[music][0])
            pygame.mixer.music.set_volume(self.master_music_tracks[music][1])
            pygame.mixer.music.play(-1, fade_ms=500)

    def stop_music(self):
        if self.working:
            pygame.mixer.music.fadeout(500)

    def play_sound(self, sound, in_loop=False):
        if self.working:
            if not self.master_sounds[sound][2]:
                self.master_sounds[sound][0].set_volume(self.master_sounds[sound][1])
                self.master_sounds[sound][0].play(0)
                self.master_sounds[sound][2] = in_loop

    def stop_sound(self, sound):
        if self.working:
            self.master_sounds[sound][0].stop()
            self.master_sounds[sound][2] = False

    def reset_sounds(self):
        for sound in self.master_sounds:
            self.master_sounds[sound][2] = False

    def stop_all(self):
        if self.working:
            pygame.mixer.stop()


# network management
class NetworkManager:
    def __init__(self, linux):
        self.ssid = None
        self.psk_key = None
        self.status = 0
        self.signal_strength = 0
        self.linux = linux

    def connect_to_wifi(self, ssid, psk_key):
        self.linux.connect_to_wifi(ssid.value, psk_key.value)


""" Image Utilities """

def load_image(path):
    try:
        image = pygame.image.load(path)

        if image.get_alpha():
            image = image.convert_alpha()
        else:
            image = image.convert()

        return image

    except Exception as e:
        logger.warning(f"unable to load '{path}': {e}")
        return pygame.image.load(os.path.join(base_path, "images", "fail_load.png")).convert()


def preload_images():
    master_images = {}
    image_path = os.path.join(base_path, "images")

    for temp_file in os.listdir(image_path):
        temp_path = os.path.join(image_path, temp_file)
        if os.path.isfile(temp_path):
            master_images[temp_file.split(".")[0]] = load_image(os.path.join(image_path, temp_file))

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


# ease out to target number
def ease_out_to(current_value, target_value, speed):
    diff = (target_value - current_value)
    if abs(int(diff)) > speed:
        current_value += diff * speed
    else:
        current_value = target_value
    return current_value


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


""" UI utilities """

default_group = pygame.sprite.Group()


# generic UI element
class UiElement(pygame.sprite.Sprite):
    def __init__(self, label, x, y, row, col, size=8, font=default_font, centered=False, group=None, func=None):
        """
        UI element that can be selected and activated via keyboard/controller navigation.
        ``row`` and ``col`` can technically be used interchangeably depending on UI layout,
        but for clarity, prefer ``row`` for vertical navigation and ``col`` for horizontal
        navigation.

        :param label: object used as the UI element's label (can be a string or a pygame.Surface)
        :param x: x coordinate
        :param y: y coordinate
        :param row: the row from which the UI can be accessed via up/down navigation.
        :param col: the column from which the UI can be accessed via left/right navigation
        :param font: the font used for ``label`` (if string)
        :param group: the group to contain the UI element
        :param func: the function that this UI element can call on activation
        """

        if group is None:
            pygame.sprite.Sprite.__init__(self, default_group)
        else:
            pygame.sprite.Sprite.__init__(self, group)

        self.x = x
        self.y = y
        self.row = row
        self.col = col
        self.size = size

        self.label = label
        self.label_type = self._get_label_type(self.label)

        if self.label_type == 0:
            self.pre_rect = pygame.Rect((self.x, self.y, 10, 10))
            self.text = Text(label, self.pre_rect.centerx, self.pre_rect.centery, WHITE, size, font=font, centered=True)
            r = self.text.rect
            self.rect = pygame.Rect((r.x - size//2, r.y - size//2, r.width + size, r.height + size))
            self.original_pos = self.rect.topleft if not centered else self.rect.center

        elif self.label_type == 1:
            self.image = label
            self.rect = self.image.get_rect()
            if not centered:
                self.rect.topleft = (x, y)
            else:
                self.rect.center = (x, y)
            self.original_pos = self.rect.center

        self.selected = False
        self.available = True

        if self.rect is not None:
            self.gray_rect = self.rect.copy()
            self.gray_rect.inflate_ip(-8, -8)
            self.gray_surf = pygame.Surface(self.gray_rect.size).convert()
            self.gray_surf.set_colorkey(BLACK)
            self.gray_surf.fill((175, 175, 175))

        self.func = func

    def _get_label_type(self, label):
        if type(label) == str:
            return 0

        elif type(label) == pygame.surface.Surface:
            return 1

        elif label is None:
            return None

    def change_label(self, new_label, font=retro_font):
        if new_label != self.label:
            self.label_type = self._get_label_type(new_label)
            if self.label_type == 0:
                self.pre_rect = pygame.Rect((self.x, self.y, 10, 10))
                self.text = Text(new_label, self.pre_rect.centerx, self.pre_rect.centery, WHITE, self.size, font=font, centered=True)
                r = self.text.rect
                self.rect = pygame.Rect((r.x - self.size//2, r.y - self.size//2, r.width + self.size, r.height + self.size))

                self.gray_rect = self.rect.copy()
                self.gray_rect.inflate_ip(-8, -8)
                self.gray_surf = pygame.Surface(self.gray_rect.size).convert()
                self.gray_surf.set_colorkey(BLACK)
                self.gray_surf.fill((175, 175, 175))

            elif self.label_type == 1:
                self.image = new_label
                self.rect = self.image.get_rect()
                self.rect.center = self.original_pos

            self.label = new_label

    def update(self, dt, col, row):
        self.check_selected(col, row)
        if self.label_type == 0:
            self.text.rect.center = self.rect.center
            self.gray_rect.center = self.rect.center

    def check_selected(self, col, row):
        self.selected = False
        if row == self.row and col == self.col:
            self.selected = True

    def action(self):
        if self.func is not None:
            if self.available:
                self.func()

    def draw(self, display):
        if self.selected:
            pygame.draw.rect(display, WHITE, self.rect, 3, border_radius=3)

        if self.label_type == 0:
            self.text.draw(display)
        elif self.label_type == 1:
            display.blit(self.image, self.rect)

        if not self.available:
            display.blit(self.gray_surf, self.gray_rect, special_flags=pygame.BLEND_RGB_MIN)


# UI Manager
class UiManager:
    def __init__(self, ui_group, col_reset=True):
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

        self.col_reset = col_reset

        self.active = True

    def update(self, dt):
        if self.active:
            x_index = self.x_index
            y_index = self.y_index
        else:
            x_index = None
            y_index = None

        for ui in self.master_ui_list:
            ui.update(dt, x_index, y_index)

    def change_col(self, val):
        if self.active:
            self.x_index += val
            self.x_index %= len(self.master_ui_dict[self.y_index])

    def change_row(self, val):
        if self.active:
            self.y_index += val
            self.y_index %= len(self.master_ui_dict)
            if self.col_reset:
                self.x_index = 0
            else:
                if len(self.master_ui_dict[self.y_index]) <= self.x_index:
                    self.x_index = len(self.master_ui_dict[self.y_index]) - 1

    def reset(self):
        self.x_index = 0
        self.y_index = 0

    def get_ui(self, x, y):
        return self.master_ui_dict[y][x]

    def action(self):
        self.master_ui_dict[self.y_index][self.x_index].action()
        return self.get_ui(self.x_index, self.y_index)

    def draw(self, display):
        for ui in self.master_ui_list:
            ui.draw(display)


# notification object
class Notification:
    def __init__(self, msg):
        self.reset(msg)

    def update(self, dt):
        self.surf.set_alpha(self.alpha)
        if self.display_timer.update(dt):
            self.alpha = max(0, self.alpha - 5 * dt)

        self.text.update()

    def reset(self, msg=None):
        self.msg = str(msg)
        self.size = 9
        self.x = DISPLAY_WIDTH - 20
        self.y = 37

        self.text = Text(self.msg, 0, 0, WHITE, self.size, font=retro_font)

        self.surf = pygame.Surface(self.text.rect.size).convert_alpha()
        self.surf.set_colorkey(BLACK)
        self.rect = self.surf.get_rect()
        self.rect.topright = (self.x, self.y)

        self.alpha = 255 if msg is not None else 0
        self.display_timer = Timer(240)

        self.surf.set_alpha(self.alpha)

    def draw(self, display):
        if self.alpha:
            self.text.draw(self.surf)
            display.blit(self.surf, self.rect)


# dialog menu
class DialogMenu:
    def __init__(self, screen, msg, instant=False, has_ui=False, options=["OK"]):
        self.width = 500
        self.height = 250

        self.surf = pygame.Surface((self.width, self.height)).convert_alpha()
        self.surf.fill(GRAY)
        self.surf.set_colorkey(BLACK)
        self.rect = self.surf.get_rect()

        self.shadow_surf = pygame.Surface((self.width, self.height)).convert()
        self.shadow_surf.set_colorkey(BLACK)
        self.shadow_surf.fill(BLACK)
        for i in range(125):
            pygame.draw.line(self.shadow_surf, ([max(90 - i//2, 40) for _ in range(3)]), (0, i*2), (self.width, i*2), 2)

        self.ui_surf = pygame.Surface((self.width, self.height)).convert_alpha()
        self.ui_surf.fill(GRAY)
        self.ui_surf.set_colorkey(BLACK)

        self.curtain = pygame.Surface((1, 1)).convert_alpha()
        self.curtain = pygame.transform.scale(self.curtain, (screen.get_width(), screen.get_height() - 60))
        self.curtain_rect = self.curtain.get_rect()
        self.curtain_rect.topleft = (0, 30)

        self.curtain.fill(DARKER_GRAY)

        self.curtain_alpha = 0
        self.curtain.set_alpha(self.curtain_alpha)
        self.curtain_fade_speed = 10

        self.reset(msg, instant, has_ui, options)

    def reset(self, msg, instant=False, has_ui=False, options=["OK"], dialog_type=None):
        self.msg = msg
        self.dialog_type = dialog_type

        if instant:
            self.alpha = max(200, self.alpha)
            self.curtain_alpha = max(50, self.curtain_alpha)
            self.curtain_fade_speed = 20
            self.y = half_display_y
        else:
            self.alpha = 0
            self.curtain_fade_speed = 10
            self.y = half_display_y + 100

        self.showing = False
        self.text = None
        self.max_chars = 30

        self.show_timer = Timer(120)

        self.surf.fill(GRAY)
        self.surf.blit(self.shadow_surf, (0, 0))
        self.rect.center = (half_display_x, self.y)

        self.has_ui = has_ui

        self.um = None
        if self.has_ui:
            self.ui_group = pygame.sprite.Group()
            for opt in options:
                if opt in ["No", "Cancel"]:
                    ok_btn = UiElement(opt, self.rect.width // 2 + 50, self.rect.height - 50, 0, 0, 20, font=retro_font, group=self.ui_group,
                                       func=self.fade_out)
                elif opt == "OK":
                    ok_btn = UiElement(opt, self.rect.width // 2, self.rect.height - 50, 0, 0, 20, font=retro_font, group=self.ui_group,
                                       func=self.fade_out)
                elif opt in ["Yes", "Install"]:
                    ok_btn = UiElement(opt, self.rect.width // 2 - 50, self.rect.height - 50, 0, 1, 20, font=retro_font, group=self.ui_group,
                                       func=self.fade_out)
            self.um = UiManager(self.ui_group)

        self.small_msg = []
        if self.msg is not None:
            self.showing = True

            letter_count = 0
            line_count = 0
            is_small = False
            msg_list = [i for i in self.msg]

            for i, v in enumerate(self.msg[:]):
                letter_count += 1

                # check for line break
                if v == "\n":
                    letter_count = 0
                    line_count += 1

                # check for small characters
                if v == "^":
                    is_small = not is_small

                # insert line breaks if line exceeds max_chars
                if letter_count >= self.max_chars:
                    if msg_list[i] == " ":
                        msg_list[i] = "\n"
                        letter_count = 0
                        line_count += 1

                    self.msg = "".join(msg_list)

                # add small characters to a separate list
                if is_small:
                    if v != "^":
                        self.small_msg.append(v)

            temp_msg = [i for i in self.msg]
            temp_msg.reverse()
            for i, v in enumerate(self.small_msg):
                if v in temp_msg:
                    temp_msg.remove(v)
            temp_msg.reverse()

            for i in range(line_count):
                self.small_msg.insert(0, "\n")

            self.msg = "".join([i if i != "^" else " " for i in temp_msg])

            # convert all small characters from a list to a string
            self.small_msg = "".join(self.small_msg[:])

            msg_lines = self.msg.splitlines()
            normal_size = 15
            for i, msg in enumerate(msg_lines):
                text = Text(msg, self.rect.width // 2, (self.rect.height // 3 + 10) - 15 * (len(msg_lines)) // 2 + (normal_size * 2 * i), WHITE, normal_size, font=retro_font, centered=True)
                text.draw(self.surf)

            small_msg_lines = self.small_msg.splitlines()
            small_size = 10
            for i, msg in enumerate(small_msg_lines):
                text = Text(msg, self.rect.width // 2, (self.rect.height // 3 + 10) - 15 * (len(msg_lines)) // 2 + (normal_size * 2 * i), WHITE, small_size, font=retro_font, centered=True)
                text.draw(self.surf)

        self.choice = None

        self.surf.set_alpha(self.alpha)
        self.curtain.set_alpha(self.curtain_alpha)

    def update(self, dt):
        self.surf.set_alpha(self.alpha)
        self.ui_surf.set_alpha(self.alpha)
        self.curtain.set_alpha(self.curtain_alpha)

        if self.has_ui:
            self.um.update(dt)
        else:
            if self.show_timer.update(dt):
                self.fade_out()

        if self.showing:
            self.alpha = min(self.alpha + 10 * dt, 255)
            self.y += (half_display_y - self.y) * .15 * dt
            self.curtain_alpha = min(self.curtain_alpha + self.curtain_fade_speed * dt, 200)
        else:
            self.alpha = max(0, self.alpha - 10 * dt)
            self.y += (half_display_y + 50 - self.y) * .15 * dt
            self.curtain_alpha = max(0, self.curtain_alpha - 10 * dt)

        self.rect.center = (half_display_x, self.y)

    def fade_out(self):
        self.showing = False
        if self.um is not None:
            self.choice = self.um.x_index

    def draw(self, display):
        if self.alpha:
            display.blit(self.curtain, self.curtain_rect)
            if self.has_ui:
                self.ui_surf.fill(BLACK)
                self.um.draw(self.ui_surf)
            display.blit(self.surf, self.rect)
            if self.has_ui:
                display.blit(self.ui_surf, self.rect)


# text field
class TextField(pygame.sprite.Sprite):
    def __init__(self, x, y, row, col, w, h, default_text, group, keyboard):
        pygame.sprite.Sprite.__init__(self, group)

        self.size = h//2
        self.text = Text("", self.size//2, self.size//2, WHITE, self.size, retro_font, False)
        self.default_text = Text(default_text, w//2, h//2, (180, 180, 180), self.size*2//3 - 2, retro_font, True)

        self.text_input = ""

        self.row = row
        self.col = col

        self.image = pygame.Surface((w, h)).convert()
        self.image.fill(GRAY)
        self.actual_rect = self.image.get_rect()
        self.actual_rect.center = (x, y)

        self.keyboard = keyboard

        self.selected = False
        self.true_selected = False

        self.max_chars = (w - self.size//2)//self.size
        self.scroll = 0

        self.value = ""

    def update(self, dt, col, row):
        self.selected = False
        if row == self.row and col == self.col:
            self.selected = True

        if self.selected:
            self.true_selected = True

        if row is not None and col is not None:
            if not self.selected:
                self.true_selected = False

    def action(self):
        self.keyboard.toggle()

    def update_text(self, k):
        if k != "BACKSPACE":
            self.text_input += k
        else:
            self.text_input = self.text_input[:len(self.text_input) - 1]

        self.text.set_text(self.text_input)
        if len(self.text_input) > self.max_chars:
            self.scroll = -(len(self.text_input) - 1 - self.max_chars) * self.size
            self.text.rect.x = self.scroll

        self.value = self.text_input

    def clear(self):
        self.text.set_text("")
        self.text_input = ""

    def draw(self, display):
        self.image.fill(GRAY)
        if len(self.text_input):
            self.text.draw(self.image)
        else:
            self.default_text.draw(self.image)
        display.blit(self.image, self.actual_rect)
        pygame.draw.rect(display, GRAY, self.actual_rect, 4)
        if self.true_selected:
            pygame.draw.rect(display, WHITE, self.actual_rect, 4, border_radius=3)


""" Room Utilities """

# room object
class Room:
    def __init__(self, x, y):
        self.orig_x = x
        self.orig_y = y

        self.x = self.orig_x
        self.y = self.orig_y

        self.surf = pygame.Surface((1, 1)).convert_alpha()
        self.surf = pygame.transform.scale(self.surf, (DISPLAY_WIDTH, DISPLAY_HEIGHT)).convert_alpha()
        self.rect = self.surf.get_rect()
        self.rect.topleft = (self.x * DISPLAY_WIDTH, self.y * DISPLAY_HEIGHT)
        self.rect = pygame.FRect(self.rect)

        self.moving = False

    def move(self, dx=0, dy=0):
        self.x = dx
        self.y = dy
        self.moving = True

    def clear(self):
        self.surf.fill((0, 0, 0, 0))

    def update_pos(self, dt):
        if self.moving:
            actual_target_x = self.x * DISPLAY_WIDTH
            diff = abs(self.rect.x - actual_target_x)
            if diff >= 1:
                self.rect.x += (actual_target_x - self.rect.x) * .15 * dt
            else:
                self.rect.x = actual_target_x

            actual_target_y = self.y * DISPLAY_HEIGHT
            diff = abs(self.rect.y - actual_target_y)
            if diff >= 1:
                self.rect.y += (actual_target_y - self.rect.y) * .15 * dt
            else:
                self.rect.y = actual_target_y

            if self.rect.x == actual_target_x and self.rect.y == actual_target_y:
                self.moving = False

    def draw(self, display):
        display.blit(self.surf, self.rect)


# room manager
class RoomManager:
    def __init__(self, rooms):
        self.rooms = rooms
        self.x = 0
        self.y = 0
        self.current_room = list(self.rooms.values())[0]

    def switch_to(self, name):
        target_room = self.rooms[name]
        target_room[2].reset()
        target_room[0].move(0, 0)
        if target_room[2] is not None:
            target_room[2].active = True

        if self.current_room[2] is not None:
            self.current_room[2].active = False
        self.current_room[0].move(self.current_room[0].orig_x - target_room[0].orig_x, self.current_room[0].orig_y - target_room[0].orig_y)

        self.current_room = target_room
        return self.current_room

    def update(self, dt):
        for _, room in self.rooms.items():
            room[0].update_pos(dt)

    def clear(self):
        for _, room in self.rooms.items():
            room[0].clear()

    def draw(self, display):
        for _, room in self.rooms.items():
            room[0].draw(display)


""" Clock Utilities """

class SystemClock:
    def __init__(self, linux, current_time):
        self.linux = linux
        self.current_time = current_time
        self.hour = self.current_time.split(":")[0]
        self.minute = self.current_time.split(":")[1]

        self.round_clock = False
        self.round_clock_labels = ["12-hour format", "24-hour format"]

    def set_time(self, t):
        self.linux.set_time(time.strftime("%Y-%m-%d") + " " + str(t) + ":00")

    def switch_format(self):
        self.round_clock = not self.round_clock


__all__ = ["CompatibilityManager",
           "AudioManager",
           "NetworkManager",
           "load_image",
           "check_internet_status",
           "get_font",
           "draw_text",
           "Text",
           "get_game_info",
           "ease_out_to",
           "logger",
           "load_thumbnail",
           "preload_images",
           "Timer",
           "default_font",
           "retro_font",
           "UiElement",
           "UiManager",
           "TextField",
           "Notification",
           "DialogMenu",
           "Room",
           "RoomManager",
           "SystemClock"]
