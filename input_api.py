"""Input management for the SHUGRPi OS (supports multiple input devices)"""

import pygame
import json
import io

# get pygame for necessary values
from pygame.locals import *

# available inputs for the SHUGRPi
INPUT_BINDINGS = {}
AVAILABLE_ACTIONS = ["UP", "DOWN", "LEFT", "RIGHT", "A", "B", "X", "Y", "SELECT", "START", "POWER"]
KEY_BINDINGS = [K_UP, K_DOWN, K_LEFT, K_RIGHT, K_a, K_b, K_x, K_y, K_RSHIFT, K_RETURN, K_ESCAPE]
JOYSTICK_BINDINGS = [11, 12, 13, 14, 0, 1, 2, 3, 4, 6, 5]
AXIS_BINDINGS = [(1, -1), (1, 1), (0, -1), (0, 1)]

# for i, action in enumerate(AVAILABLE_ACTIONS):
#     INPUT_BINDINGS[action] = []
#     INPUT_BINDINGS[action].append({"type": "key", "value": KEY_BINDINGS[i]})
#     INPUT_BINDINGS[action].append({"type": "button", "value": JOYSTICK_BINDINGS[i]})
#     if i < len(AXIS_BINDINGS):
#         INPUT_BINDINGS[action].append({"type": "axis", "axis": AXIS_BINDINGS[i][0], "direction": AXIS_BINDINGS[i][1]})
# print(INPUT_BINDINGS)
# with open("data/bindings.json", "w") as f:
#     f.write(json.dumps(INPUT_BINDINGS, indent=4))

INPUT_BINDINGS = json.load(io.FileIO("data/bindings.json"))

class ControllerManager:
    def __init__(self):
        pygame.joystick.init()
        self.joysticks = {}

        for i in range(pygame.joystick.get_count()):
            self._add(i)

    def _add(self, device_index):
        j = pygame.joystick.Joystick(device_index)
        self.joysticks[j.get_instance_id()] = j
        print("Connected:", j.get_name())

    def _remove(self, instance_id):
        if instance_id in self.joysticks:
            print("Disconnected:", self.joysticks[instance_id].get_name())
            del self.joysticks[instance_id]

    def handle_event(self, event):
        if event.type == pygame.JOYDEVICEADDED:
            self._add(event.device_index)

        elif event.type == pygame.JOYDEVICEREMOVED:
            self._remove(event.instance_id)

    def get_all(self):
        return list(self.joysticks.values())


class InputDevice:
    def __init__(self, keyboard=True, joystick=None):
        self.keyboard = keyboard
        self.joystick = joystick

    def get_key(self, key):
        if not self.keyboard:
            return False
        keys = pygame.key.get_pressed()
        return keys[key]

    def get_button(self, button):
        if self.joystick:
            return self.joystick.get_button(button)
        return False

    def get_axis(self, axis):
        if self.joystick:
            return self.joystick.get_axis(axis)
        return 0.0


class InputManager:
    def __init__(self, bindings, device, buffer_time=0.1, deadzone=0.2):

        self.bindings = bindings
        self.device = device
        self.buffer_time = buffer_time
        self.deadzone = deadzone

        self.held = {a: False for a in bindings}
        self.pressed = {a: False for a in bindings}
        self.released = {a: False for a in bindings}
        self.buffer = {a: 0.0 for a in bindings}

    def update(self, dt):
        for a in self.pressed:
            self.pressed[a] = False
            self.released[a] = False

        for action, inputs in self.bindings.items():

            active = False

            for inp in inputs:

                if inp["type"] == "key":
                    if self.device.get_key(inp["value"]):
                        active = True

                elif inp["type"] == "button":
                    if self.device.get_button(inp["value"]):
                        active = True

                elif inp["type"] == "axis":
                    val = self.device.get_axis(inp["axis"])

                    if inp["direction"] < 0 and val < -self.deadzone:
                        active = True
                    if inp["direction"] > 0 and val > self.deadzone:
                        active = True

            # state transitions
            if active:
                if not self.held[action]:
                    self.pressed[action] = True
                    self.buffer[action] = self.buffer_time
                self.held[action] = True
            else:
                if self.held[action]:
                    self.released[action] = True
                self.held[action] = False

        # update buffers
        for a in self.buffer:
            if self.buffer[a] > 0:
                self.buffer[a] -= dt

    # queries
    def is_down(self, action):
        return self.held[action]

    def is_pressed(self, action):
        return self.pressed[action]

    def is_buffered(self, action):
        return self.buffer[action] > 0

    def consume_buffer(self, action):
        self.buffer[action] = 0


joystick_manager = ControllerManager()

# Player 1 = keyboard
p1_device = InputDevice(keyboard=True)
p1_input = InputManager(INPUT_BINDINGS, p1_device)

# Player 2 = joystick (if exists)
joysticks = joystick_manager.get_all()

p2_input = None
if not p2_input and joysticks:
    p2_input = InputManager(INPUT_BINDINGS, InputDevice(keyboard=False, joystick=joysticks[0]))


