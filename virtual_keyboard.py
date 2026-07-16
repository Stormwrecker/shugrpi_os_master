"""
Virtual-keyboard object for the SHUGRPi OS that has its own UI with a corresponding
UI manager (imported from the ``utils`` module)
"""

# necessary modules
import pygame
from utils import *
from constants import *


# virtual keyboard object
class VirtualKeyboard:
    def __init__(self):
        self.um = None

        self.text_field = None

        self._setup_keys()

        self.width = DISPLAY_WIDTH - 50
        self.height = 225
        self.size = 20
        self.padding = self.size // 2 + 6
        self.x_start = (self.width - (self.size + self.padding) * 20) // 2 + self.padding // 2

        self.button_group = pygame.sprite.Group()
        self.button_rects = []
        self.button_shadow_rects = []
        self._setup_buttons()
        self.button_manager = UiManager(self.button_group, False)

        self.image = pygame.Surface((self.width, self.height)).convert_alpha()
        self.image.set_colorkey(BLACK)
        self.image.fill(BLACK)
        for i in range(125):
            pygame.draw.line(self.image, ([max(80 - i//2, 40) for _ in range(3)]), (0, i*2), (self.width, i*2), 2)
        self.rect = self.image.get_rect()
        self.rect.midtop = (HALF_DISPLAY_WIDTH, DISPLAY_HEIGHT)

        self.button_image = self.image.copy()
        self.button_image.set_colorkey(BLACK)
        self.button_image.fill(BLACK)
        for rect in self.button_shadow_rects:
            pygame.draw.rect(self.button_image, (40, 40, 40), rect, border_radius=3)
        for rect in self.button_rects:
            pygame.draw.rect(self.button_image, (20, 20, 20), rect, border_radius=3)

        self.ui_image = self.image.copy()
        self.ui_image.set_colorkey(BLACK)

        self.toggled = False
        self.target_scroll = 100
        self.scroll = 0

        self.clicking = False

        self.last_key = None

        self._setup_curtain()

    def _setup_keys(self):
        self.keys = [chr(i) for i in range(0, 1000) if chr(i).isascii() and chr(i).isprintable()]
        self.keys = self.keys[33:] + self.keys[:32]
        self.keys.remove(" ")

    def _setup_buttons(self):
        row = 0
        col = 0

        for i, key in enumerate(self.keys):
            btn = UiElement(key, self.x_start + (self.size + self.padding) * col, 20 + (self.size + self.padding) * row,
                            row, col, group=self.button_group, size=self.size, font=retro_font, centered=True, func=self._return_key)
            btn_rect = btn.rect.copy().inflate(-10, -10)
            self.button_rects.append(btn_rect)

            col += 1
            if col >= 20:
                row += 1
                col = 0

        col += 1
        btn = UiElement("Space", self.x_start + (self.size + self.padding) * col, 20 + (self.size + self.padding) * row, row, col-1,
                        group=self.button_group, size=self.size, font=retro_font, centered=True, func=self._return_space)
        btn_rect = btn.rect.copy().inflate(-10, -10)
        self.button_rects.append(btn_rect)

        col += 1
        btn = UiElement("←", self.x_start + (self.size + self.padding) * (col+1), 20 + (self.size + self.padding) * row, row, col-1,
                        group=self.button_group, size=self.size, font=retro_font, centered=True, func=self._return_backspace)
        btn_rect = btn.rect.copy().inflate(-10, -10)
        self.button_rects.append(btn_rect)

        col += 1
        btn = UiElement("Enter", self.x_start + (self.size + self.padding) * (col+2), 20 + (self.size + self.padding) * row, row, col-1,
                        group=self.button_group, size=self.size, font=retro_font, centered=True, func=lambda: self.toggle(self.text_field))
        btn_rect = btn.rect.copy().inflate(-10, -10)
        self.button_rects.append(btn_rect)

        for rect in self.button_rects:
            r = rect.copy().inflate(4, 4)
            self.button_shadow_rects.append(r)

    def _setup_curtain(self):
        self.curtain = pygame.Surface((1, 1)).convert_alpha()
        self.curtain = pygame.transform.scale(self.curtain, (DISPLAY_WIDTH, DISPLAY_HEIGHT - 60))
        self.curtain_rect = self.curtain.get_rect()
        self.curtain_rect.topleft = (0, 30)

        self.curtain.fill(DARKER_GRAY)

        self.curtain_alpha = 0
        self.curtain.set_alpha(self.curtain_alpha)
        self.curtain_fade_speed = 10

    def _return_key(self):
        btn_mgr = self.button_manager
        current_y = btn_mgr.y_index
        lookup_pos = btn_mgr.x_index + sum([len(btn_mgr.master_ui_dict[i]) for i in range(current_y)])
        self.last_key = self.keys[lookup_pos]

    def _return_space(self):
        self.last_key = " "

    def _return_backspace(self):
        self.last_key = "BACKSPACE"

    def toggle(self, text_field=None):
        self.last_key = ""
        self.toggled = not self.toggled
        if self.toggled:
            self.button_manager.reset()
            self.text_field = text_field
            self.text_field.in_view = True
        else:
            if self.text_field is not None:
                self.text_field.in_view = False

    def update(self, dt):
        self.button_manager.update(dt)
        self.curtain.set_alpha(self.curtain_alpha)

        if self.toggled:
            self.target_scroll = -225
            self.curtain_alpha = min(self.curtain_alpha + self.curtain_fade_speed * dt, 200)
        else:
            self.target_scroll = 100
            self.curtain_alpha = max(0, self.curtain_alpha - 10 * dt)
            if self.curtain_alpha == 0:
                self.text_field = None

        if self.scroll != self.target_scroll:
            self.scroll = ease_out_to(self.scroll, self.target_scroll, 0.15 * dt)

    def handle_event(self, event, text_fields=None):
        if event.key == pygame.K_UP:
            self.button_manager.change_row(-1)
        if event.key == pygame.K_DOWN:
            self.button_manager.change_row(1)
        if event.key == pygame.K_LEFT:
            self.button_manager.change_col(-1)
        if event.key == pygame.K_RIGHT:
            self.button_manager.change_col(1)
        if event.key == pygame.K_RETURN:
            self.button_manager.action()
            self.clicking = True
            if text_fields is not None:
                selected_fields = [v for v in list(text_fields.values()) if v.true_selected]
                if len(selected_fields) > 0:
                    selected_text_field = selected_fields[0]
                    selected_text_field.update_text(self.last_key)

    def draw(self, display):
        if self.curtain_alpha:
            display.blit(self.curtain, self.curtain_rect)
            self.text_field.draw(display)

        display.blit(self.image, (self.rect.x, self.rect.y + self.scroll))
        display.blit(self.button_image, (self.rect.x, self.rect.y + self.scroll))

        self.ui_image.fill(BLACK)
        self.button_manager.draw(self.ui_image)
        display.blit(self.ui_image, (self.rect.x, self.rect.y + self.scroll))


__all__ = ["VirtualKeyboard"]
