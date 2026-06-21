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
        self.rect.midtop = (half_display_x, DISPLAY_HEIGHT)

        self.button_image = self.image.copy()
        self.button_image.set_colorkey(BLACK)

        self.toggled = False
        self.target_scroll = 100
        self.scroll = 0

        self.last_key = None

    def _setup_keys(self):
        self.keys = [chr(i) for i in range(0, 1000) if chr(i).isascii() and chr(i).isprintable()]
        self.keys = self.keys[33:] + self.keys[:32]

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

        btn = UiElement("Backspace", self.x_start + 60, 30 + (self.size + self.padding) * (row + 1), row, col,
                        group=self.button_group, size=self.size, font=retro_font, centered=True, func=self._return_backspace)
        btn_rect = btn.rect.copy().inflate(-10, -10)
        self.button_rects.append(btn_rect)

        for rect in self.button_rects:
            r = rect.copy().inflate(4, 4)
            self.button_shadow_rects.append(r)

    def _return_key(self):
        btn_mgr = self.button_manager
        current_y = btn_mgr.y_index
        lookup_pos = btn_mgr.x_index + sum([len(btn_mgr.master_ui_dict[i]) for i in range(current_y)])
        self.last_key = self.keys[lookup_pos]

    def _return_backspace(self):
        self.last_key = "BACKSPACE"

    def toggle(self):
        self.toggled = not self.toggled
        if self.toggled:
            self.button_manager.reset()

    def update(self, dt):
        self.button_manager.update(dt)
        if self.toggled:
            self.target_scroll = -225
        else:
            self.target_scroll = 100

        if self.scroll != self.target_scroll:
            self.scroll = ease_out_to(self.scroll, self.target_scroll, 0.15 * dt)

    def handle_event(self, event, text_fields:dict=None):
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
            if text_fields is not None:
                selected_text_field = [v for v in list(text_fields.values()) if v.true_selected][0]
                selected_text_field.update_text(self.last_key)

    def draw(self, display):
        display.blit(self.image, (self.rect.x, self.rect.y + self.scroll))

        self.button_image.fill(BLACK)
        for rect in self.button_shadow_rects:
            pygame.draw.rect(self.button_image, (40, 40, 40), rect, border_radius=3)
        for rect in self.button_rects:
            pygame.draw.rect(self.button_image, (20, 20, 20), rect, border_radius=3)
        self.button_manager.draw(self.button_image)
        display.blit(self.button_image, (self.rect.x, self.rect.y + self.scroll))


__all__ = ["VirtualKeyboard"]
