from __future__ import annotations

from functools import lru_cache

import pygame

SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900
FPS = 60

START_YEAR = 1920
END_YEAR = 1935
HISTORICAL_CRASH_YEAR = 1929

BG_COLOR = (19, 17, 15)
BG_TOP_COLOR = (46, 40, 35)
BG_BOTTOM_COLOR = (12, 11, 10)
GRID_COLOR = (92, 78, 62)

PANEL_COLOR = (40, 34, 30)
CARD_COLOR = (51, 43, 37)
PANEL_EDGE = (114, 94, 72)
PANEL_GLOW = (96, 70, 48)

TEXT_COLOR = (222, 211, 193)
MUTED_TEXT = (165, 149, 129)
GOOD_COLOR = (145, 171, 120)
WARN_COLOR = (198, 152, 83)
BAD_COLOR = (177, 90, 81)
ACCENT_COLOR = (175, 128, 86)

BUTTON_COLOR = (76, 60, 44)
BUTTON_HOVER = (96, 75, 53)
BUTTON_EDGE = (155, 118, 84)


@lru_cache(maxsize=64)
def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    candidates = ("bahnschrift", "trebuchetms", "verdana", "arial")
    for name in candidates:
        if pygame.font.match_font(name):
            return pygame.font.SysFont(name, size, bold=bold)
    return pygame.font.SysFont(None, size, bold=bold)
