#!/usr/bin/env python3
"""Print joystick button index when you press any button. Run and press each key to see its index."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame

def main():
    pygame.init()
    pygame.joystick.init()
    n = pygame.joystick.get_count()
    if n == 0:
        print("No joystick found. Connect controller and run again.")
        return
    js = pygame.joystick.Joystick(0)
    js.init()
    name = js.get_name()
    num_buttons = js.get_numbuttons()
    print(f"Controller: {name}")
    print(f"Buttons: {num_buttons}. Press any button (or Ctrl+C to exit):")
    print("  Index 0=A, 1=B, 2=X, 3=Y, 4=LB, 5=RB, 6=Back/View, 7=Start/Menu, ...")
    print("-" * 50)
    prev = [False] * num_buttons
    while True:
        pygame.event.pump()
        for i in range(num_buttons):
            cur = js.get_button(i) == 1
            if cur and not prev[i]:
                print(f"  Button index {i} PRESSED")
            prev[i] = cur

if __name__ == "__main__":
    main()
