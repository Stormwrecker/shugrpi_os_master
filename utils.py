"""Various utilities necessary to run the SHUGRPi OS"""

# import setup modules
import pygame
import os
import platform
import logging
import time
import threading
import shutil
import json
from socket import gethostbyname, gethostname
from constants import *

# misc values
base_path = os.path.dirname(os.path.abspath(__file__))
default_font = os.path.join(base_path, "fonts", "Kenney_Bold.ttf")
retro_font = os.path.join(base_path, "fonts", "PressStart2P.ttf")
font_cache = {}

temp_dir = os.path.join(base_path, "logs")


""" Logging Helpers"""

def init_logger():
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir)

    # set up logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s - %(message)s",
        handlers=[logging.FileHandler(os.path.join(temp_dir, "temp_session.log"), "w"),
                  logging.StreamHandler()]
    )
    logger = logging.getLogger("SHUGRPi System Log")

    return logger


def quit_logger():
    logging.shutdown()


logger = init_logger()


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
            # os.environ['AUDIODEV'] = 'hdmi:CARD=vc4hdmi0,DEV=0'
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
        except Exception as e:
            self.working = False
            logger.error(f"AudioManager: fail ({e})")

    def _get_sound_path(self, path):
        return os.path.join(base_path, "audio", path + ".wav")

    def _get_music_path(self, path):
        return os.path.join(base_path, "audio", path + ".mp3")

    def _load_sounds(self):
        self.master_sounds["logo"] = [pygame.mixer.Sound(self._get_sound_path("shugrpi_logo")), .5, False]
        self.master_sounds["menu_swish"] = [pygame.mixer.Sound(self._get_sound_path("menu_swish")), .2, False]
        self.master_sounds["menu_up"] = [pygame.mixer.Sound(self._get_sound_path("menu_up")), .2, False]
        self.master_sounds["menu_down"] = [pygame.mixer.Sound(self._get_sound_path("menu_down")), .2, False]
        self.master_sounds["switch"] = [pygame.mixer.Sound(self._get_sound_path("switch")), .3, False]
        self.master_sounds["action"] = [pygame.mixer.Sound(self._get_sound_path("action")), .4, False]
        self.master_sounds["error"] = [pygame.mixer.Sound(self._get_sound_path("error")), .6, False]

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
    def __init__(self, linux, dm, logger, images):
        """Manager for network statuses, available networks, wifi connectivity, etc."""
        self.linux = linux
        self.dm = dm
        self.logger = logger

        self.ssid = self.dm.data["network"]["ssid"]
        self.psk_key = self.dm.data["network"]["psk-key"]

        # self.linux.reload_wifi(self.ssid, self.psk_key)

        self.ip = self._get_ip()

        self.statuses = {"Poor":[0, 25], "Moderate":[26, 50], "Good":[51, 75], "Excellent":[76, 100]}
        self.signal_strength = 0
        self.status = "inactive"

        self.logged = False

        self.wifi_connected = self._check_wifi_connection()
        self.internet_access = self._check_internet_access()

        # status updater for internet connection
        self.stop_event = threading.Event()
        self.wifi_lock = threading.Lock()
        self.wifi_thread = threading.Thread(name="SHUGRPi Network Manager", target=self._update_status, daemon=True)
        self.wifi_thread.start()

        self.wifi_list_lock = threading.Lock()
        self.wifi_list_thread = threading.Thread(name="SHUGRPi Wifi Scan", target=self.scan_networks, daemon=True)
        self.is_scanning = False

        self.text_fields = {}

        self.ui_group = pygame.sprite.Group()

        self.available_networks = []
        self.wifi_ui_group = pygame.sprite.Group()

        self._setup_empty_list()

        self.images = [images[image] for image in images if image.startswith("signal")]

    def _get_ip(self):
        """return device's IP address"""
        return gethostbyname(gethostname())

    def _check_wifi_connection(self):
        """check if wifi is connected based on if IP is not 'localhost'"""
        new_ip = self._get_ip()
        if new_ip not in ["127.0.0.1", "localhost"]:
            self.ip = new_ip
            return True
        return False

    def _update_status(self):
        """threaded check for internet access every 3 seconds"""
        try:
            while not self.stop_event.wait(3):
                self.wifi_connected = self._check_wifi_connection()
                if self.wifi_connected:
                    with self.wifi_lock:
                        self.internet_access = self._check_internet_access()
                        if self.internet_access == 0:
                            self.status = "connected"
                        else:
                            self.status = "no internet"
                else:
                    with self.wifi_lock:
                        self.status = "not connected"
        except Exception as e:
            self.logger.error(f"NetworkManager: failed to update internet status: {e}")
            with self.wifi_lock:
                self.status = "error"

    def _check_internet_access(self):
        """check internet access based on linux.ping()"""
        if self.linux.check_internet_status() == 0:
            return True
        else:
            if not self.logged:
                self.logger.warning("SHUGRPi does not have access to the internet")
                self.logged = True
            return False

    def start_scan(self):
        if not self.is_scanning:
            self.list_status_text.set_text("Scanning...")
            self.wifi_list_thread = threading.Thread(name="SHUGRPi Wifi Scan", target=self.scan_networks, daemon=True)
            self.wifi_list_thread.start()
            self.is_scanning = True

    def scan_networks(self):
        """scan for available networks"""
        self.available_networks = self.linux.scan_networks()

    def setup_ui(self):
        """set up and arrange UI for main network room"""
        first_col_x = 75
        first_col_y = 225

        second_col_x = HALF_DISPLAY_WIDTH + 125
        second_col_y = 225

        self.main_header_text = Text("Network Settings", HALF_DISPLAY_WIDTH, 85, WHITE, 25, default_font, centered=True)

        self.wifi_header_text = Text("Network Status", 190, first_col_y - 50, WHITE, 15, default_font, True)
        self.wifi_name_text = Text(f"{self.ssid}", first_col_x, first_col_y, WHITE, 11, default_font, False)
        self.status_text = Text(f"Status: {self.status}", first_col_x, first_col_y + 50, WHITE, 11, default_font, False)
        self.signal_text = Text("Signal Strength: None", first_col_x, first_col_y + 100, WHITE, 11, default_font, False)

        self.connect_header_text = Text("Wifi Setup", second_col_x + 50, first_col_y - 50, WHITE, 15, default_font, True)

        self.board_rects = [pygame.Rect(first_col_x - 10, first_col_y - 15, 250, 150)]

    def _setup_empty_list(self):
        """create shaded network-list board"""
        self.list_image = pygame.Surface((408, (DISPLAY_HEIGHT - 30) - (HALF_DISPLAY_HEIGHT - 90))).convert_alpha()
        self.list_image.set_colorkey(BLACK)
        self.list_image.fill(BLACK)
        self.list_rect = self.list_image.get_rect()
        self.list_rect.midtop = (HALF_DISPLAY_WIDTH, HALF_DISPLAY_HEIGHT - 90)

        self.shadow_surf = pygame.Surface((self.list_rect.width, self.list_rect.height)).convert()
        self.shadow_surf.set_colorkey(BLACK)
        self.shadow_surf.fill(BLACK)
        for i in range(self.list_rect.height):
            pygame.draw.line(self.shadow_surf, ([min(i // 4 + 50, 70) for _ in range(3)]), (0, i * 4),
                             (self.list_rect.width, i * 4), 4)

        self.list_status_text = Text("No networks available", self.list_rect.centerx, 200, WHITE, 15, font=retro_font, centered=True)

    def _get_networks(self):
        """generate wifi UI blocks based on available networks"""
        # self.available_networks = [{"ssid":f"HELLO{i}", "strength":20 * i} for i in range(5)]
        self.available_networks = sorted(self.available_networks, key=lambda x: x["strength"], reverse=True)

        self.wifi_ui_group.empty()

        # get 'bars' based on signal strength
        strength_ranges = [[0, 33], [34, 66], [66, 100]]
        for i, network in enumerate(self.available_networks):
            for j, r in enumerate(strength_ranges):
                if r[0] <= network["strength"] <= r[1]:
                    temp_signal = j

            # wifi UI
            wifi_ui = WifiBlockUI(network["ssid"], temp_signal, self.list_rect.width // 2, 20 + (i * 100), i, 0, self.images)
            self.wifi_ui_group.add(wifi_ui)

        # wifi UI manager for the list
        self.wifi_um = UiManager(self.wifi_ui_group)
        self.wifi_um.active = False

        if len(self.available_networks) == 0:
            self.list_status_text.set_text("No networks available")
        else:
            self.list_status_text.set_text(" ")

    def setup_wifi_list_ui(self, images):
        """set up and arrange UI for wifi-list room"""
        self.list_header_text = Text("Network List", HALF_DISPLAY_WIDTH, 85, WHITE, 20, default_font, centered=True)

        self._get_networks()

        self.scroll = 0
        self.target_scroll = 0
        self.scroll_increment = 100

        self.misc_group = pygame.sprite.Group()

    def connect_wifi(self, ssid, psk_key):
        """connect to wifi network with ssid and psk-key"""
        if self.linux.connect_wifi(ssid, psk_key) == 0:
            self.dm.update("network", {"ssid":ssid, "psk-key":psk_key})

    def disconnect_wifi(self):
        """disconnect from current network"""
        if self.linux.disconnect_wifi() == 0:
            self.wifi_connected = False
            self.internet_access = False
            self.logger.info(f"NetworkManager: disconnected wifi")

    def ask_connect(self, ssid, dialog):
        """bring up dialog prompt for password"""
        dialog.reset(f"Enter password for\n'{self.wifi_um.get_ui(self.wifi_um.x_index, self.wifi_um.y_index).ssid}'", has_ui=True, options=["Connect", "Cancel"], dialog_type=3, text_field=True)

    def handle_event(self, event, dialog):
        """handle events for wifi-list room"""
        if self.wifi_um.active:
            if len(self.wifi_ui_group):
                if event.key == pygame.K_UP:
                    if self.wifi_um.y_index - 1 >= 0:
                        self.wifi_um.change_row(-1)
                    else:
                        self.misc_um.active = True
                        self.wifi_um.active = False
                        self.misc_um.x_index = 1
                if event.key == pygame.K_DOWN:
                    self.wifi_um.change_row(1)
                if event.key == pygame.K_LEFT:
                    self.misc_um.active = True
                    self.wifi_um.active = False
                    self.misc_um.x_index = 1
                if event.key == pygame.K_RIGHT:
                    self.misc_um.active = True
                    self.wifi_um.active = False
                    self.misc_um.x_index = 0
                if event.key == pygame.K_RETURN:
                    self.ask_connect(self.wifi_um.action(), dialog)

        elif self.misc_um.active:
            if event.key in [pygame.K_RIGHT, pygame.K_DOWN]:
                self.misc_um.change_col(1)
            if event.key in [pygame.K_LEFT, pygame.K_UP]:
                self.misc_um.change_col(-1)
            if event.key == pygame.K_RETURN:
                self.misc_um.action()
            if self.misc_um.x_index == 2 and len(self.wifi_ui_group):
                self.misc_um.active = False
                self.wifi_um.active = True
                self.misc_um.x_index = 1

    def update(self, dt):
        """update statuses for network connection and update UI"""
        self.wifi_name_text.set_text(str(self.ssid))
        self.status_text.set_text(f"Status: {self.status}")

        if self.is_scanning and not self.wifi_list_thread.is_alive():
            self._get_networks()
            self.is_scanning = False

        current_status = None
        if current_status is not None:
            self.signal_text.set_text(f"Signal Strength: {current_status if self.wifi_connected else None}")
        else:
            for name, r in self.statuses.items():
                if self.signal_strength >= r[0] and self.signal_strength <= r[1]:
                    current_status = name

        self.disconnect_ui.available = self.wifi_connected

        self.target_scroll = min(self.scroll_increment * len(self.wifi_ui_group), max(0, self.scroll_increment * (self.wifi_um.y_index - 1)))

        self.scroll = ease_out_to(self.scroll, self.target_scroll, 0.15)

        self.wifi_um.update(dt)
        self.misc_um.update(dt)
        for ui in self.wifi_ui_group:
            ui.rect.y = ui.original_center[1] - self.scroll

    def draw(self, display):
        """draw network room"""
        for rect in self.board_rects:
            pygame.draw.rect(display, GRAY, rect, border_radius=3)

        self.main_header_text.draw(display)

        self.wifi_header_text.draw(display)

        self.wifi_name_text.draw(display)
        self.status_text.draw(display)
        self.signal_text.draw(display)

        self.connect_header_text.draw(display)

    def draw_alt(self, display):
        """draw wifi-list room"""
        self.list_header_text.draw(display)
        self.list_image.blit(self.shadow_surf, (0, 0))
        self.wifi_um.draw(self.list_image)
        self.misc_um.draw(display)
        display.blit(self.list_image, self.list_rect)
        self.list_status_text.draw(display)

    def quit(self):
        """stop threads"""
        self.stop_event.set()
        self.logger.info(f"NetworkManager: quit")


# data management
class DataManager:
    def __init__(self, logger):
        self.data_folder = "data"
        self.save_file = os.path.join("data", "shugrpi_config.json")
        self.logger = logger
        self.data = self.load()

    def load(self):
        if not os.path.exists(self.data_folder):
            os.mkdir("data")

        if not os.path.exists(self.save_file):
            with open(self.save_file, "w") as f:
                f.write(json.dumps(DEFAULT_SAVE))
            self.logger.warning("DataManager: save file not detected")
            return DEFAULT_SAVE

        else:
            with open(self.save_file, "r") as f:
                data = json.load(f)
            self.logger.info("DataManager: load")
            return data

    def save(self):
        with open(self.save_file, "w") as f:
            f.write(json.dumps(self.data, indent=4))
        self.logger.info("DataManager: save")

    def update(self, k, v):
        if k in self.data:
            self.data[k] = v


# clock management
class ClockManager:
    def __init__(self, linux, dm, logger):
        self.linux = linux
        self.dm = dm
        self.logger = logger

        self.current_time = time.localtime(self.dm.data["last_timestamp"])
        self.hour = self.current_time.tm_hour
        self.minute = self.current_time.tm_min
        self.round_clock = self.dm.data["round_clock"]

        self.round_clock_labels = ["Round Clock: OFF", "Round Clock: ON"]

        self.logger.info(f"Startup time: {time.strftime("%m-%d-%Y %I:%M %p", self.current_time)}")

        self.ui_group = pygame.sprite.Group()
        self.um = None

    def set_um(self, um):
        self.um = um

    def setup_ui(self):
        self.main_header_text = Text("Clock Settings", HALF_DISPLAY_WIDTH, 85, WHITE, 25, default_font, centered=True)
        first_col_x = HALF_DISPLAY_WIDTH - 260
        first_col_y = 244

        second_col_x = HALF_DISPLAY_WIDTH + 200
        second_col_y = 244

        self.set_time_text = Text("Set Time", 190, first_col_y - 50, WHITE, 16, default_font, centered=True)
        self.extras_text = Text("Options", DISPLAY_WIDTH - 190, second_col_y - 50, WHITE, 16, default_font, centered=True)

        timer_pos_x = first_col_x
        timer_pos_y = first_col_y
        timer_size = 14
        self.hour_ui = UiElement(self.hour, timer_pos_x - (timer_size*1.5), timer_pos_y, 0, 2, size=timer_size, font=default_font, group=self.ui_group, func=lambda: self.um.change_col(1))
        self.minute_ui = UiElement(self.minute, timer_pos_x + (timer_size*2), timer_pos_y, 0, 3, size=timer_size, font=default_font, group=self.ui_group, func=lambda: self.um.change_col(1))
        self.colon = Text(":", first_col_x, timer_pos_y, WHITE, timer_size, retro_font)
        self.set_time_ui = UiElement("Update", first_col_x + timer_size * 6, first_col_y, 0, 0, size=10, font=default_font, group=self.ui_group, func=self.set_time)


        self.round_clock_ui = UiElement(self.round_clock_labels[int(self.round_clock)], second_col_x, second_col_y, 0, 1, size=10, font=default_font, group=self.ui_group, func=self.toggle_round_clock)

    def set_time(self):
        self.linux.set_time(time.strftime("%Y-%m-%d") + " " + str(self.hour_ui.label + ":" + self.minute_ui.label) + ":00")

    def toggle_round_clock(self):
        self.round_clock = not self.round_clock
        if not self.round_clock:
            if int(self.hour_ui.label) > 12:
                label = str(int(self.hour_ui.label) % 12)
                self.hour_ui.change_label(("0" if int(label) < 10 else "") + label, default_font)
            elif int(self.hour_ui.label) < 1:
                label = "12"
                self.hour_ui.change_label(("0" if int(label) < 10 else "") + label, default_font)

        self.round_clock_ui.change_label(self.round_clock_labels[self.round_clock], default_font)

        self.dm.update("round_clock", self.round_clock)

    def update_time(self):
        self.current_time = time.strftime("%H:%M") if self.round_clock else time.strftime("%I:%M")

    def events(self, event):
        if self.hour_ui.selected:
            if event.key == pygame.K_UP:
                if self.round_clock:
                    label = (int(self.hour_ui.label) + 1) % 24
                else:
                    label = int(self.hour_ui.label) + 1
                    if label > 12:
                        label = 1
                self.hour_ui.change_label(("0" if label < 10 else "") + str(label), default_font)
            if event.key == pygame.K_DOWN:
                if self.round_clock:
                    label = (int(self.hour_ui.label) - 1) % 24
                else:
                    label = int(self.hour_ui.label) - 1
                    if label < 1:
                        label = 12
                self.hour_ui.change_label(("0" if label < 10 else "") + str(label), default_font)
            return True
        elif self.minute_ui.selected:
            if event.key == pygame.K_UP:
                label = str((int(self.minute_ui.label) + 1) % 60)
                self.minute_ui.change_label(("0" if int(label) < 10 else "") + label, default_font)
            if event.key == pygame.K_DOWN:
                label = str((int(self.minute_ui.label) - 1) % 60)
                self.minute_ui.change_label(("0" if int(label) < 10 else "") + label, default_font)
            return True

        return False

    def update(self):
        self.hour_ui.change_label(self.current_time.split(":")[0], default_font)
        self.minute_ui.change_label(self.current_time.split(":")[1], default_font)

    def draw(self, display):
        self.main_header_text.draw(display)
        self.set_time_text.draw(display)
        self.extras_text.draw(display)
        self.colon.draw(display)


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
        self.original_text = str(text)

        self.color = color
        self.size = size

        self.font_name = font
        self.font = self._get_font(self.font_name, self.size)
        self.alt_font = self._get_font(retro_font, self.size + 2)

        self.text, self.alt_text = self._parse_text_by_font(self.original_text, self.font_name)

        self.image = self._setup_image(self.text, self.alt_text)

        self.rect = self.image.get_rect()
        self.centered = centered
        self.x = x
        self.y = y

        if self.centered:
            self.rect.center = (self.x, self.y)
        else:
            self.rect.topleft = (self.x, self.y)

    def set_text(self, new_text):
        if self.original_text != str(new_text):
            self.original_text = str(new_text)

            self.text, self.alt_text = self._parse_text_by_font(self.original_text, self.font_name)

            self.image = self._setup_image(self.text, self.alt_text)
            self.rect = self.image.get_rect()
            if self.centered:
                self.rect.center = (self.x, self.y)
            else:
                self.rect.topleft = (self.x, self.y)

    def _get_font(self, font, size):
        return get_font(font, size)

    def _parse_text_by_font(self, text, font):
        new_text = ""
        if font == default_font:
            for t in text:
                if not t.isalnum() and not t.isspace():
                    i = text.find(t)
                    text = text.split(t)
                    text[0] += " "
                    text[1] = "  " + text[1]
                    new_text = t
        return text, new_text

    def _setup_image(self, text, alt_text=""):
        if len(alt_text) == 0:
            image = self.font.render(text, False, self.color)

            return image
        else:
            self.font: pygame.font.Font
            big_image = pygame.Surface(self.font.size(self.original_text)).convert()
            big_image.set_colorkey(BLACK)

            image = self.font.render(text[0], False, self.color)
            new_image = self.alt_font.render(alt_text, False, self.color)

            big_image.blit(new_image, (image.get_width() - self.size * .4, self.size * .4), special_flags=pygame.BLEND_RGBA_ADD)

            image = self.font.render("".join(text), False, self.color)
            big_image.blit(image, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

            return big_image

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
    def __init__(self, ui_group, col_reset=True, am=None):
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
        self.am = am

        self.active = True

    def _play_sound(self):
        if self.am:
            self.am.play_sound("switch")

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
            self._play_sound()

    def change_row(self, val):
        if self.active:
            self.y_index += val
            self.y_index %= len(self.master_ui_dict)
            if self.col_reset:
                self.x_index = 0
            else:
                if len(self.master_ui_dict[self.y_index]) <= self.x_index:
                    self.x_index = len(self.master_ui_dict[self.y_index]) - 1
            self._play_sound()

    def reset(self):
        self.x_index = 0
        self.y_index = 0

    def get_ui(self, x, y):
        return self.master_ui_dict[y][x]

    def action(self, play_sound=True):
        self.master_ui_dict[self.y_index][self.x_index].action()
        if self.am and play_sound and self.master_ui_dict[self.y_index][self.x_index].available:
            self.am.play_sound("action")
        return self.get_ui(self.x_index, self.y_index)

    def draw(self, display):
        for ui in self.master_ui_list:
            ui.draw(display)


# notification object
class Notification:
    def __init__(self, msg, am):
        self.am = am
        self.reset(msg)

    def update(self, dt):
        self.surf.set_alpha(self.alpha)
        if self.display_timer.update(dt):
            self.alpha = max(0, self.alpha - 5 * dt)

        self.text.update()

    def reset(self, msg=None, error=False):
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

        if error:
            self.am.play_sound("error")

        self.surf.set_alpha(self.alpha)

    def draw(self, display):
        if self.alpha:
            self.text.draw(self.surf)
            display.blit(self.surf, self.rect)


# dialog menu
class DialogMenu:
    def __init__(self, screen, msg, instant=False, has_ui=False, options=["OK"], am=None, virtual_keyboard=None):
        self.virtual_keyboard = virtual_keyboard

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

        self.text_surf = pygame.Surface((self.width, self.height)).convert_alpha()
        self.text_surf.fill(GRAY)
        self.text_surf.set_colorkey(BLACK)

        self.curtain = pygame.Surface((1, 1)).convert_alpha()
        self.curtain = pygame.transform.scale(self.curtain, (screen.get_width(), screen.get_height() - 60))
        self.curtain_rect = self.curtain.get_rect()
        self.curtain_rect.topleft = (0, 30)

        self.curtain.fill(DARKER_GRAY)

        self.curtain_alpha = 0
        self.curtain.set_alpha(self.curtain_alpha)
        self.curtain_fade_speed = 10

        self.am = am

        self.text_field = None

        self.reset(msg, instant, has_ui, options)

    def reset(self, msg, instant=False, has_ui=False, options=["OK"], text_field=False, dialog_type=None, error=False):
        self.msg = msg
        self.dialog_type = dialog_type

        if instant:
            self.alpha = max(200, self.alpha)
            self.curtain_alpha = max(50, self.curtain_alpha)
            self.curtain_fade_speed = 20
            self.y = HALF_DISPLAY_HEIGHT
        else:
            self.alpha = 0
            self.curtain_fade_speed = 10
            self.y = HALF_DISPLAY_HEIGHT + 100

        self.showing = False
        self.text = None
        self.max_chars = 30

        self.show_timer = Timer(120)

        self.surf.fill(GRAY)
        self.surf.blit(self.shadow_surf, (0, 0))
        self.rect.center = (HALF_DISPLAY_WIDTH, self.y)

        self.has_ui = has_ui
        self.text_field = None

        self.um = None
        if self.has_ui:
            self.ui_group = pygame.sprite.Group()
            temp_row = 1 if text_field else 0
            for opt in options:
                if opt in ["No", "Cancel"]:
                    ok_btn = UiElement(opt, self.rect.width // 2 + 100, self.rect.height - 50, temp_row, 0, 20, font=retro_font, group=self.ui_group,
                                       func=self.fade_out)
                elif opt == "OK":
                    ok_btn = UiElement(opt, self.rect.width // 2, self.rect.height - 50, 0, 0, 20, font=retro_font, group=self.ui_group,
                                       func=self.fade_out)
                elif opt in ["Yes", "Install", "Uninstall", "Remove", "Connect"]:
                    ok_btn = UiElement(opt, self.rect.width // 2 - 100, self.rect.height - 50, temp_row, 1, 20, font=retro_font, group=self.ui_group,
                                       func=self.fade_out)
            if text_field:
                self.text_field = TextField(self.width // 2, self.height // 2 + 15, 0, 0, 200, 30, "Type your password here", group=self.ui_group, keyboard=self.virtual_keyboard, new_center=(self.width // 2, self.height // 2 - 20))
            self.um = UiManager(self.ui_group, am=self.am)

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
                text = Text(msg, self.rect.width // 2, (self.rect.height // 3) - 15 * (len(msg_lines)) // 2 + (normal_size * 2 * i), WHITE, normal_size, font=retro_font, centered=True)
                text.draw(self.surf)

            small_msg_lines = self.small_msg.splitlines()
            small_size = 10
            for i, msg in enumerate(small_msg_lines):
                text = Text(msg, self.rect.width // 2, (self.rect.height // 3) - 15 * (len(msg_lines)) // 2 + (normal_size * 2 * i), WHITE, small_size, font=retro_font, centered=True)
                text.draw(self.surf)

        self.choice = None

        self.surf.set_alpha(self.alpha)
        self.curtain.set_alpha(self.curtain_alpha)

        if error:
            self.am.play_sound("error")

    def update(self, dt):
        self.surf.set_alpha(int(self.alpha))
        self.ui_surf.set_alpha(int(self.alpha))
        self.text_surf.set_alpha(int(self.alpha))
        self.curtain.set_alpha(int(self.curtain_alpha))

        if self.has_ui:
            self.um.update(dt)
        else:
            if self.show_timer.update(dt):
                self.fade_out()

        if self.showing:
            self.alpha = min(self.alpha + 10 * dt, 255)
            self.y += (HALF_DISPLAY_HEIGHT - self.y) * .15 * dt
            self.curtain_alpha = min(self.curtain_alpha + self.curtain_fade_speed * dt, 200)
        else:
            self.alpha = max(0, self.alpha - 10 * dt)
            self.y += (HALF_DISPLAY_HEIGHT + 50 - self.y) * .15 * dt
            self.curtain_alpha = max(0, self.curtain_alpha - 10 * dt)

        self.rect.center = (HALF_DISPLAY_WIDTH, self.y)

    def fade_out(self):
        self.showing = False
        if self.um is not None:
            self.choice = self.um.x_index

    def draw(self, display):
        if self.alpha:
            self.text_surf.fill(BLACK)
            display.blit(self.curtain, self.curtain_rect)
            if self.has_ui:
                self.ui_surf.fill(BLACK)
                self.um.draw(self.ui_surf)
            display.blit(self.surf, self.rect)
            if self.has_ui:
                display.blit(self.ui_surf, self.rect)

    def draw_text(self, display):
        if self.text_field is not None:
            self.text_field.draw(self.text_surf)
            display.blit(self.text_surf, self.rect)


# text field
class TextField(pygame.sprite.Sprite):
    def __init__(self, x, y, row, col, w, h, default_text, group, keyboard, needs_hash=False, new_center=None):
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

        self.original_pos = list(self.actual_rect.center)
        self.pos = list(self.actual_rect.center)

        self.center = (HALF_DISPLAY_WIDTH, 175) if new_center is None else new_center

        self.keyboard = keyboard

        self.selected = False
        self.true_selected = False
        self.available = True

        self.max_chars = (w - self.size//2)//self.size
        self.scroll = 0

        self.value = ""

        self.in_view = False
        self.speed = 0.15

        self.needs_hash = needs_hash
        self.hashed = False

    def update(self, dt, col, row):
        self.selected = False
        if row == self.row and col == self.col:
            self.selected = True

        if self.selected:
            self.true_selected = True

        if row is not None and col is not None:
            if not self.selected:
                self.true_selected = False

        if self.in_view:
            self.pos[0] = ease_out_to(self.pos[0], self.center[0], self.speed * dt)
            self.pos[1] = ease_out_to(self.pos[1], self.center[1], self.speed * dt)
        else:
            self.pos[0] = ease_out_to(self.pos[0], self.original_pos[0], self.speed * dt)
            self.pos[1] = ease_out_to(self.pos[1], self.original_pos[1], self.speed * dt)
        self.actual_rect.center = (int(self.pos[0]), int(self.pos[1]))

    def action(self):
        self.keyboard.toggle(self)
        self.hashed = False
        self.text.set_text(self.value)

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

        if self.hashed:
            self.text.set_text("*" * len(self.value))
        else:
            self.text.set_text(self.value)

    def clear(self):
        self.text.set_text("")
        self.text_input = ""
        self.value = ""

    def draw(self, display):
        self.image.fill(GRAY)
        if len(self.text_input):
            self.text.draw(self.image)
        else:
            self.default_text.draw(self.image)
        display.blit(self.image, self.actual_rect)
        pygame.draw.rect(display, (90, 90, 90), self.actual_rect, 4)
        if self.true_selected and not self.selected:
            pygame.draw.rect(display, GRAY, self.actual_rect, 4, border_radius=3)
        elif self.true_selected and self.selected:
            pygame.draw.rect(display, WHITE, self.actual_rect, 4, border_radius=3)


# wifi block
class WifiBlockUI(pygame.sprite.Sprite):
    def __init__(self, ssid, signal, x, y, row, col, images):
        pygame.sprite.Sprite.__init__(self)
        self.ssid = ssid
        self.signal = signal
        self.row = row
        self.col = col
        self.image = pygame.Surface((360, 80)).convert()
        self.image.set_colorkey(BLACK)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.original_center = (x, y)

        self.background_rect = pygame.Rect((0, 0, self.rect.width, self.rect.height))
        self.images = images

        self.text = Text(ssid, 10, self.rect.height - 25, WHITE, 10)
        self.connect_text = Text("Connect", self.rect.width * 2 // 3, self.rect.height // 2, WHITE, 15, centered=True)

        self.selected = False

    def update(self, dt, col, row):
        self.check_selected(col, row)

    def check_selected(self, col, row):
        self.selected = False
        if row == self.row and col == self.col:
            self.selected = True

    def action(self):
        return self.ssid

    def draw(self, display):
        self.image.fill(BLACK)
        pygame.draw.rect(self.image, (90, 90, 90), self.background_rect, border_radius=3)
        self.text.draw(self.image)
        self.connect_text.draw(self.image)
        self.image.blit(self.images[self.signal], (10, 5))
        display.blit(self.image, self.rect)
        if self.selected:
            pygame.draw.rect(display, WHITE, self.rect, 3, border_radius=3)


""" Room Utilities """

# room object
class Room:
    def __init__(self, name, x, y):
        self.name = name

        self.orig_x = x
        self.orig_y = y

        self.x = self.orig_x
        self.y = self.orig_y

        self.surf = pygame.Surface((1, 1)).convert_alpha()
        self.surf = pygame.transform.scale(self.surf, (DISPLAY_WIDTH, DISPLAY_HEIGHT)).convert_alpha()
        self.rect = self.surf.get_rect()
        self.rect.topleft = (self.x * DISPLAY_WIDTH, self.y * DISPLAY_HEIGHT)
        self.rect = pygame.FRect(self.rect)

        self.active = self.x == 0 and self.y == 0
        self.moving = False
        self.true_active = False

    def move(self, dx=0, dy=0):
        self.x = dx
        self.y = dy
        self.moving = True
        self.active = True

    def clear(self):
        self.surf.fill((0, 0, 0, 0))

    def update_pos(self, name, dt):
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

            if self.name == name:
                self.true_active = True
        else:
            if self.name != name:
                self.active = False
                self.true_active = False
            else:
                self.true_active = True

    def draw(self, display):
        if self.true_active:
            display.blit(self.surf, self.rect)


# room manager
class RoomManager:
    def __init__(self, rooms):
        self.rooms = rooms
        self.x = 0
        self.y = 0
        self.current_room = list(self.rooms.values())[0]
        self.active_rooms = [self.current_room[0]]

    def switch_to(self, name):
        target_room = self.rooms[name]

        target_room[2].reset()
        target_room[0].move(0, 0)
        if target_room[2] is not None:
            target_room[2].active = True

        if self.current_room[2] is not None:
            self.current_room[2].active = False
        diff_x = self.current_room[0].x - target_room[0].orig_x
        diff_y = self.current_room[0].y - target_room[0].orig_y

        for room in self.rooms.values():
            room[2].reset()
            if room[0].name != target_room[0].name:
                room[0].move(room[0].orig_x + diff_x, room[0].orig_y + diff_y)

        self.current_room = target_room

        return self.current_room

    def update(self, dt):
        self.active_rooms = [room[0] for room in self.rooms.values() if room[0].active]

        for _, room in self.rooms.items():
            room[0].update_pos(self.current_room[0].name, dt)

    def clear(self):
        for _, room in self.rooms.items():
            room[0].clear()

    def draw(self, display):
        for _, room in self.rooms.items():
            if room[0].active:
                room[0].draw(display)


__all__ = ["init_logger",
           "quit_logger",
           "CompatibilityManager",
           "AudioManager",
           "NetworkManager",
           "DataManager",
           "load_image",
           "get_font",
           "draw_text",
           "Text",
           "get_game_info",
           "ease_out_to",
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
           "ClockManager"]
