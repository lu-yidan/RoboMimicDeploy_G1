from common.path_config import PROJECT_ROOT

import os
import pygame
from pygame.locals import *
from enum import IntEnum, unique

@unique
class JoystickButton(IntEnum):
    # Xbox One/Series controller on Linux (xpad driver)
    # Override any button with env var JOYSTICK_<NAME>, e.g. JOYSTICK_START=7
    A = 0
    B = 1
    X = 3
    Y = 4
    L1 = 6      # LB
    R1 = 7      # RB
    SELECT = 10  # View/Back button
    START = 11   # Menu/Start button
    L3 = 13     # Left Stick Press
    R3 = 14     # Right Stick Press
    HOME = 15   # Xbox Guide button
    UP = 16     # D-pad Up
    DOWN = 17   # D-pad Down
    LEFT = 18   # D-pad Left
    RIGHT = 19  # D-pad Right


def _default_remap():
    """Logical button -> physical index. Override with env vars, e.g. JOYSTICK_START=7."""
    remap = {}
    for btn in JoystickButton:
        val = os.environ.get(f"JOYSTICK_{btn.name}")
        if val is not None:
            remap[btn] = int(val)
    return remap

class JoyStick:
    def __init__(self):
        pygame.init()
        pygame.joystick.init()
        
        joystick_count = pygame.joystick.get_count()
        if joystick_count == 0:
            raise RuntimeError("No joystick connected!")
        
        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        
        self.button_count = self.joystick.get_numbuttons()
        self.button_states = [False] * self.button_count  
        self.button_pressed = [False] * self.button_count  
        self.button_released = [False] * self.button_count 

        self.axis_count = self.joystick.get_numaxes()
        self.axis_states = [0.0] * self.axis_count
        
        self.hat_count = self.joystick.get_numhats()
        self.hat_states = [(0, 0)] * self.hat_count

        self.remap = _default_remap()

    def _physical_id(self, button_id):
        """Map logical button to physical index (for alternate controller layouts)."""
        return self.remap.get(button_id, button_id)

    def update(self):
        """update joystick state"""
        pygame.event.pump()  
        
        self.button_released = [False] * self.button_count
        
        for i in range(self.button_count):
            current_state = self.joystick.get_button(i) == 1
            if self.button_states[i] and not current_state:
                self.button_released[i] = True
            self.button_states[i] = current_state

        for i in range(self.axis_count):
            self.axis_states[i] = self.joystick.get_axis(i)
        
        for i in range(self.hat_count):
            self.hat_states[i] = self.joystick.get_hat(i)

    def is_button_pressed(self, button_id):
        """detect button pressed"""
        phys = self._physical_id(button_id)
        if 0 <= phys < self.button_count:
            return self.button_states[phys]
        return False

    def is_button_released(self, button_id):
        """detect button released"""
        phys = self._physical_id(button_id)
        if 0 <= phys < self.button_count:
            return self.button_released[phys]
        return False

    def get_axis_value(self, axis_id):
        """get joystick axis value"""
        if 0 <= axis_id < self.axis_count:
            return self.axis_states[axis_id]
        return 0.0

    def get_hat_direction(self, hat_id=0):
        """get joystick hat direction"""
        if 0 <= hat_id < self.hat_count:
            return self.hat_states[hat_id]
        return (0, 0)