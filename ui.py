from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame

from constants import (
    ACCENT_COLOR,
    BAD_COLOR,
    BG_BOTTOM_COLOR,
    BG_COLOR,
    BG_TOP_COLOR,
    BUTTON_COLOR,
    BUTTON_EDGE,
    BUTTON_HOVER,
    CARD_COLOR,
    GOOD_COLOR,
    GRID_COLOR,
    HISTORICAL_CRASH_YEAR,
    MUTED_TEXT,
    PANEL_COLOR,
    PANEL_EDGE,
    PANEL_GLOW,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TEXT_COLOR,
    WARN_COLOR,
    get_font,
)
from engine import GameState, PolicySelection, TurnResult
from events import WildcardEvent


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    callback: Callable[[], None]
    hotkey: int | None = None

    def draw(self, screen: pygame.Surface, mouse_pos: tuple[int, int]) -> None:
        hovered = self.rect.collidepoint(mouse_pos)
        color = BUTTON_HOVER if hovered else BUTTON_COLOR

        shadow = self.rect.move(0, 3)
        pygame.draw.rect(screen, (10, 8, 7), shadow, border_radius=12)
        pygame.draw.rect(screen, color, self.rect, border_radius=12)
        pygame.draw.rect(screen, BUTTON_EDGE, self.rect, width=2, border_radius=12)

        shine = pygame.Rect(self.rect.x + 2, self.rect.y + 2, self.rect.width - 4, 8)
        pygame.draw.rect(screen, (205, 172, 136, 36), shine, border_radius=10)

        text = get_font(19, bold=True).render(self.label, True, TEXT_COLOR)
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)

        if self.hotkey is not None:
            key = pygame.key.name(self.hotkey).upper()
            hint = get_font(12, bold=True).render(key, True, (214, 180, 137))
            hint_rect = hint.get_rect(bottomright=(self.rect.right - 9, self.rect.bottom - 7))
            screen.blit(hint, hint_rect)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()
                return True
        if event.type == pygame.KEYDOWN and self.hotkey is not None and event.key == self.hotkey:
            self.callback()
            return True
        return False


@dataclass
class Slider:
    rect: pygame.Rect
    label: str
    get_value: Callable[[], float]
    set_value: Callable[[float], None]
    hotkey_down: int | None = None
    hotkey_up: int | None = None
    dragging: bool = False

    def _value_from_mouse_x(self, x: int) -> float:
        rel = (x - self.rect.x) / max(1, self.rect.width)
        continuous = (rel * 2.0) - 1.0
        return max(-1.0, min(1.0, continuous))

    def draw(self, screen: pygame.Surface, mouse_pos: tuple[int, int]) -> None:
        hovered = self.rect.collidepoint(mouse_pos)
        track_bg = (48, 39, 34) if hovered else (42, 34, 30)
        pygame.draw.rect(screen, track_bg, self.rect, border_radius=9)
        pygame.draw.rect(screen, PANEL_EDGE, self.rect, width=2, border_radius=9)

        y_mid = self.rect.centery
        x_left = self.rect.x + 14
        x_right = self.rect.right - 14
        pygame.draw.line(screen, MUTED_TEXT, (x_left, y_mid), (x_right, y_mid), 3)

        tick_positions = [x_left, (x_left + x_right) // 2, x_right]
        for tx in tick_positions:
            pygame.draw.line(screen, TEXT_COLOR, (tx, y_mid - 8), (tx, y_mid + 8), 2)

        value = self.get_value()
        knob_x = int(x_left + ((value + 1.0) * 0.5) * (x_right - x_left))
        knob_color = ACCENT_COLOR if value > 0 else BAD_COLOR if value < 0 else WARN_COLOR
        center_x = tick_positions[1]
        pygame.draw.line(screen, knob_color, (center_x, y_mid), (knob_x, y_mid), 4)
        pygame.draw.circle(screen, knob_color, (knob_x, y_mid), 11)
        pygame.draw.circle(screen, (20, 16, 14), (knob_x, y_mid), 11, 2)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.dragging = True
            self.set_value(self._value_from_mouse_x(event.pos[0]))
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self.set_value(self._value_from_mouse_x(event.pos[0]))
            return True
        if event.type == pygame.KEYDOWN:
            if self.hotkey_down is not None and event.key == self.hotkey_down:
                self.set_value(max(-1.0, self.get_value() - 0.1))
                return True
            if self.hotkey_up is not None and event.key == self.hotkey_up:
                self.set_value(min(1.0, self.get_value() + 0.1))
                return True
        return False


_BACKGROUND_CACHE: pygame.Surface | None = None


def _lerp_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _background_surface() -> pygame.Surface:
    global _BACKGROUND_CACHE
    if _BACKGROUND_CACHE is not None:
        return _BACKGROUND_CACHE

    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    surface.fill(BG_COLOR)

    for y in range(SCREEN_HEIGHT):
        t = y / max(1, SCREEN_HEIGHT - 1)
        pygame.draw.line(surface, _lerp_color(BG_TOP_COLOR, BG_BOTTOM_COLOR, t), (0, y), (SCREEN_WIDTH, y))

    grid = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for x in range(0, SCREEN_WIDTH, 40):
        alpha = 42 if x % 160 == 0 else 20
        pygame.draw.line(grid, (*GRID_COLOR, alpha), (x, 0), (x, SCREEN_HEIGHT), 1)
    for y in range(0, SCREEN_HEIGHT, 40):
        alpha = 42 if y % 160 == 0 else 20
        pygame.draw.line(grid, (*GRID_COLOR, alpha), (0, y), (SCREEN_WIDTH, y), 1)
    surface.blit(grid, (0, 0))

    glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*PANEL_GLOW, 65), (200, 120), 280)
    pygame.draw.circle(glow, (*ACCENT_COLOR, 42), (SCREEN_WIDTH - 180, 140), 220)
    surface.blit(glow, (0, 0))

    _BACKGROUND_CACHE = surface.convert()
    return _BACKGROUND_CACHE


def _draw_panel(
    screen: pygame.Surface,
    rect: pygame.Rect,
    *,
    fill: tuple[int, int, int] = PANEL_COLOR,
    border: tuple[int, int, int] = PANEL_EDGE,
    radius: int = 16,
    show_highlight: bool = True,
) -> None:
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 0))
    pygame.draw.rect(panel, (*fill, 230), (0, 0, rect.width, rect.height), border_radius=radius)
    pygame.draw.rect(panel, (*border, 255), (0, 0, rect.width, rect.height), width=2, border_radius=radius)
    if show_highlight and rect.width > 10 and rect.height > 8:
        highlight_h = min(10, rect.height - 6)
        highlight = pygame.Rect(3, 3, rect.width - 6, highlight_h)
        pygame.draw.rect(panel, (194, 166, 131, 24), highlight, border_radius=10)
    screen.blit(panel, rect.topleft)


def metric_color(value: float, good_min: float | None, bad_max: float | None) -> tuple[int, int, int]:
    if good_min is not None and value >= good_min:
        return GOOD_COLOR
    if bad_max is not None and value <= bad_max:
        return BAD_COLOR
    return WARN_COLOR


def get_ui_layout() -> dict[str, pygame.Rect]:
    margin = 20
    header = pygame.Rect(margin, margin, SCREEN_WIDTH - 2 * margin, 152)
    cards = pygame.Rect(margin, header.bottom + 16, SCREEN_WIDTH - 2 * margin, 136)
    strip = pygame.Rect(margin, cards.bottom + 12, SCREEN_WIDTH - 2 * margin, 64)
    lower_y = strip.bottom + 18
    lower_h = SCREEN_HEIGHT - lower_y - margin
    gap = 16
    policy_w = int((SCREEN_WIDTH - (2 * margin) - gap) * 0.64)
    policy = pygame.Rect(margin, lower_y, policy_w, lower_h)
    log = pygame.Rect(policy.right + gap, lower_y, SCREEN_WIDTH - policy.right - gap - margin, lower_h)
    return {"header": header, "cards": cards, "strip": strip, "policy": policy, "log": log}


def _draw_header(screen: pygame.Surface, state: GameState, rect: pygame.Rect) -> None:
    _draw_panel(screen, rect, radius=18)

    left_x = rect.x + 22
    risk_rect = pygame.Rect(rect.right - 370, rect.y + 12, 350, rect.height - 24)
    content_max_w = max(240, risk_rect.left - left_x - 20)

    title_font = get_font(44, bold=True)
    subtitle_font = get_font(21)
    era_font = get_font(20, bold=True)

    title = title_font.render("Federal Reserve Crisis Desk", True, TEXT_COLOR)
    subtitle_lines = _wrap_text(
        "America is brittle. Every move can deepen unrest, defaults, and bank failures.",
        subtitle_font,
        content_max_w,
    )
    era = era_font.render("Campaign Window: 1920-1935", True, ACCENT_COLOR)

    title_y = rect.y + 16
    screen.blit(title, (left_x, title_y))

    subtitle_y = title_y + title.get_height() + 2
    for line in subtitle_lines[:2]:
        screen.blit(subtitle_font.render(line, True, MUTED_TEXT), (left_x, subtitle_y))
        subtitle_y += subtitle_font.get_linesize() - 2

    era_y = rect.bottom - era.get_height() - 14
    screen.blit(era, (left_x, era_y))

    _draw_risk_widget(screen, state, risk_rect)


def _draw_risk_widget(screen: pygame.Surface, state: GameState, rect: pygame.Rect) -> None:
    _draw_panel(screen, rect, fill=(58, 44, 36), border=(150, 112, 84), radius=12)
    current_risk = max(0.0, 100.0 - state.avoid_chance)
    baseline_risk = max(1.0, 100.0 - state.initial_avoid_chance)
    risk_change_pct = ((current_risk - baseline_risk) / baseline_risk) * 100.0

    years_left = HISTORICAL_CRASH_YEAR - state.year
    if years_left > 0:
        deadline_text = f"{years_left} years to 1929 crash window"
    elif years_left == 0:
        deadline_text = "1929 crash window is now"
    else:
        deadline_text = f"{abs(years_left)} years past 1929"

    bar = pygame.Rect(rect.x + 12, rect.y + 92, rect.width - 24, 14)
    fill_w = int(bar.width * max(0.0, min(1.0, current_risk / 100.0)))
    year_color = (255, 123, 88)
    delta_color = BAD_COLOR if risk_change_pct > 0 else GOOD_COLOR if risk_change_pct < 0 else WARN_COLOR
    compact = rect.height < 140
    title_size = 17 if compact else 18
    year_size = 28 if compact else 32
    stat_size = 15 if compact else 16
    title_y = rect.y + 8
    year_y = rect.y + 26
    risk_y = rect.y + 34
    delta_y = rect.y + (53 if compact else 61)
    bar.y = rect.y + (74 if compact else 92)
    deadline_y = rect.y + (94 if compact else 112)

    screen.blit(get_font(title_size, bold=True).render("Great Depression Risk", True, TEXT_COLOR), (rect.x + 12, title_y))
    screen.blit(get_font(year_size, bold=True).render(f"YEAR {state.year}", True, year_color), (rect.x + 12, year_y))
    screen.blit(get_font(stat_size, bold=True).render(f"Risk {current_risk:.1f}%", True, WARN_COLOR), (rect.x + 206, risk_y))
    screen.blit(
        get_font(stat_size, bold=True).render(f"Delta vs 1920 {risk_change_pct:+.0f}%", True, delta_color),
        (rect.x + 12, delta_y),
    )
    pygame.draw.rect(screen, (33, 29, 26), bar, border_radius=7)
    if fill_w > 0:
        pygame.draw.rect(screen, delta_color, (bar.x, bar.y, fill_w, bar.height), border_radius=7)
    screen.blit(get_font(14, bold=True).render(deadline_text, True, MUTED_TEXT), (rect.x + 12, deadline_y))


def draw_game(
    screen: pygame.Surface,
    state: GameState,
    pending_policy: PolicySelection,
    last_result: TurnResult | None,
    buttons: list[Button],
    sliders: list[Slider],
) -> None:
    screen.blit(_background_surface(), (0, 0))
    layout = get_ui_layout()
    _draw_header(screen, state, layout["header"])

    draw_state_cards(screen, state, layout)
    draw_policy_panel(screen, state, pending_policy, layout["policy"])
    draw_log_panel(screen, state, pending_policy, last_result, layout["log"])

    mouse_pos = pygame.mouse.get_pos()
    for slider in sliders:
        slider.draw(screen, mouse_pos)
    for button in buttons:
        button.draw(screen, mouse_pos)


def draw_state_cards(screen: pygame.Surface, state: GameState, layout: dict[str, pygame.Rect]) -> None:
    cards_rect = layout["cards"]
    x0 = cards_rect.x
    y = cards_rect.y
    h = cards_rect.height
    gap = 12

    cards = [
        ("Employment", f"{state.employment:.1f}%", metric_color(state.employment, 92.0, 84.0)),
        ("Inflation", f"{state.inflation:.1f}%", metric_color(-abs(state.inflation), -2.0, -6.0)),
        ("Debt / GDP", f"{state.debt:.1f}%", metric_color(-state.debt, -55.0, -90.0)),
        ("Reserves", f"{state.reserves:.1f}", metric_color(state.reserves, 55.0, 35.0)),
        ("Bank Stability", f"{state.bank_stability:.1f}", metric_color(state.bank_stability, 60.0, 35.0)),
    ]

    count = len(cards)
    total_gap = gap * (count - 1)
    w = (cards_rect.width - total_gap) // count

    for i, (label, value, color) in enumerate(cards):
        x = x0 + i * (w + gap)
        card = pygame.Rect(x, y, w, h)
        _draw_panel(screen, card, fill=CARD_COLOR, border=PANEL_EDGE, radius=14)

        lsurf = get_font(19, bold=True).render(label, True, MUTED_TEXT)
        vsurf = get_font(35, bold=True).render(value, True, color)
        screen.blit(lsurf, (x + 14, y + 20))
        screen.blit(vsurf, (x + 14, y + 58))

        gauge = pygame.Rect(x + 14, y + h - 22, w - 28, 8)
        pygame.draw.rect(screen, (14, 22, 36), gauge, border_radius=5)
        level = max(0.1, min(1.0, (color[1] + color[0]) / 470.0))
        fill_w = max(10, int(gauge.width * level))
        pygame.draw.rect(screen, color, (gauge.x, gauge.y, fill_w, gauge.height), border_radius=5)

    strip = layout["strip"]
    _draw_panel(screen, strip, fill=CARD_COLOR, border=PANEL_EDGE, radius=12)
    msg = f"Depression Avoidance Odds: {state.avoid_chance:.1f}%"
    detail = (
        f"Rate {state.policy_rate:.2f}%   Tax {state.tax_level:.2f}% GDP   "
        f"Spending {state.spending_level:.2f}% GDP   Liquidity {state.liquidity_level:.2f}"
    )
    color = GOOD_COLOR if state.avoid_chance >= 65 else WARN_COLOR if state.avoid_chance >= 35 else BAD_COLOR
    screen.blit(get_font(24, bold=True).render(msg, True, color), (strip.x + 12, strip.y + 8))
    screen.blit(get_font(18).render(detail, True, MUTED_TEXT), (strip.x + 12, strip.y + 36))


def _pending_label(value: float) -> tuple[str, tuple[int, int, int]]:
    if value >= 0.08:
        return f"RAISE {value:+.2f}", ACCENT_COLOR
    if value <= -0.08:
        return f"LOWER {value:+.2f}", BAD_COLOR
    return "HOLD +0.00", WARN_COLOR


def draw_policy_panel(
    screen: pygame.Surface,
    state: GameState,
    pending_policy: PolicySelection,
    rect: pygame.Rect,
) -> None:
    x = rect.x
    y = rect.y
    w = rect.width
    h = rect.height
    _draw_panel(screen, rect)
    screen.blit(get_font(30, bold=True).render("Policy Directives", True, TEXT_COLOR), (x + 16, y + 14))
    screen.blit(
        get_font(18).render("Set each policy with continuous sliders (-1.00 to +1.00 stance).", True, MUTED_TEXT),
        (x + 16, y + 50),
    )

    lines = [
        ("Interest Rate", pending_policy.interest_rate, state.policy_rate, "0.75%", "A / D"),
        ("Tax Level", pending_policy.tax_rate, state.tax_level, "0.80%", "W / S"),
        (
            "Government Spending",
            pending_policy.government_spending,
            state.spending_level,
            "0.60%",
            "Q / E",
        ),
        (
            "Emergency Liquidity",
            pending_policy.emergency_liquidity,
            state.liquidity_level,
            "0.70 idx",
            "F / R",
        ),
    ]

    for i, (label, value, current_level, step, keys) in enumerate(lines):
        row_y = y + 90 + i * 68
        row_rect = pygame.Rect(x + 14, row_y - 10, w - 28, 58)
        _draw_panel(screen, row_rect, fill=(56, 47, 40), border=(124, 101, 79), radius=10)

        pending, color = _pending_label(value)
        stat = f"Current level {current_level:.2f}    step {step}"
        screen.blit(get_font(20, bold=True).render(label, True, TEXT_COLOR), (x + 28, row_y - 1))
        screen.blit(get_font(16).render(stat, True, MUTED_TEXT), (x + 28, row_y + 23))
        screen.blit(get_font(15, bold=True).render(f"{pending}", True, color), (x + w - 340, row_y + 2))
        screen.blit(get_font(15).render(f"Keys {keys}", True, ACCENT_COLOR), (x + w - 340, row_y + 24))

    controls = _policy_controls_layout(rect)
    hint_y = controls["row_1_y"] - 16
    hint = get_font(16, bold=True).render("Controls: Drag sliders (or keys +/-0.10) | Space End Year | N New Game | Esc Quit", True, MUTED_TEXT)
    screen.blit(hint, (x + 16, hint_y))


def draw_year_summary_popup(screen: pygame.Surface, result: TurnResult, state: GameState) -> None:
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((4, 3, 2, 210))
    screen.blit(overlay, (0, 0))

    panel = pygame.Rect(170, 88, SCREEN_WIDTH - 340, SCREEN_HEIGHT - 176)
    _draw_panel(screen, panel, fill=(58, 44, 38), border=(160, 122, 90), radius=18)

    screen.blit(get_font(42, bold=True).render(f"Year {result.year} Report", True, TEXT_COLOR), (panel.x + 24, panel.y + 20))
    screen.blit(
        get_font(20).render("Summary of what changed after policy execution and shocks.", True, MUTED_TEXT),
        (panel.x + 24, panel.y + 72),
    )

    risk_change = result.avoid_chance - state.initial_avoid_chance
    risk_line = f"Avoidance Odds: {result.avoid_chance:.1f}%  ({risk_change:+.1f} vs 1920 baseline)"
    risk_color = GOOD_COLOR if risk_change >= 0 else BAD_COLOR
    screen.blit(get_font(21, bold=True).render(risk_line, True, risk_color), (panel.x + 24, panel.y + 108))

    net = result.net_changes
    rows = [
        ("Employment", net["employment"]),
        ("Inflation", net["inflation"]),
        ("Debt / GDP", net["debt"]),
        ("Reserves", net["reserves"]),
        ("Bank Stability", net["bank_stability"]),
    ]
    y0 = panel.y + 152
    for i, (label, value) in enumerate(rows):
        yy = y0 + i * 50
        row = pygame.Rect(panel.x + 24, yy - 8, panel.width - 48, 40)
        _draw_panel(screen, row, fill=(66, 51, 44), border=(138, 109, 88), radius=9)
        value_color = GOOD_COLOR if value > 0 else BAD_COLOR if value < 0 else WARN_COLOR
        screen.blit(get_font(21, bold=True).render(label, True, TEXT_COLOR), (row.x + 10, yy))
        screen.blit(get_font(21, bold=True).render(f"{value:+.2f}", True, value_color), (row.right - 130, yy))

    screen.blit(get_font(24, bold=True).render("Shock Events", True, TEXT_COLOR), (panel.x + 24, panel.y + 432))
    if result.events_triggered:
        max_text_w = panel.width - 90
        y_cursor = panel.y + 466
        for event in result.events_triggered[:3]:
            title = get_font(17, bold=True).render(f"> {event.name}", True, WARN_COLOR)
            screen.blit(title, (panel.x + 28, y_cursor))
            y_cursor += 22
            desc_lines = _wrap_text(event.description, get_font(15), max_text_w)
            for line in desc_lines[:2]:
                screen.blit(get_font(15).render(line, True, MUTED_TEXT), (panel.x + 44, y_cursor))
                y_cursor += 18
            y_cursor += 8
            if y_cursor > panel.bottom - 66:
                break
    else:
        screen.blit(get_font(18).render("No major shock events.", True, GOOD_COLOR), (panel.x + 28, panel.y + 468))

    screen.blit(
        get_font(20, bold=True).render("Press Space/Enter or click to continue", True, ACCENT_COLOR),
        (panel.x + 24, panel.bottom - 44),
    )


def draw_log_panel(
    screen: pygame.Surface,
    state: GameState,
    pending_policy: PolicySelection,
    last_result: TurnResult | None,
    rect: pygame.Rect,
) -> None:
    preview = state.preview_policy(pending_policy)
    x = rect.x
    y = rect.y
    w = rect.width
    button_safe_top = rect.bottom - 58

    def _fits_text(text_y: int, size: int, pad: int = 4) -> bool:
        return text_y + get_font(size).get_height() + pad <= button_safe_top

    _draw_panel(screen, rect)

    screen.blit(get_font(31, bold=True).render("Projected Direct Policy Impact", True, TEXT_COLOR), (x + 16, y + 14))
    screen.blit(
        get_font(14).render("Immediate model effects only. Wildcard shocks are not included.", True, MUTED_TEXT),
        (x + 16, y + 49),
    )

    lever_rows = [
        f"Policy Rate: {state.policy_rate:.2f}% -> {preview['policy_rate']:.2f}%",
        f"Tax Level: {state.tax_level:.2f}% GDP -> {preview['tax_level']:.2f}% GDP",
        f"Gov Spending: {state.spending_level:.2f}% GDP -> {preview['spending_level']:.2f}% GDP",
        f"Emergency Liquidity: {state.liquidity_level:.2f} -> {preview['liquidity_level']:.2f}",
    ]

    lever_y0 = y + 79
    lever_gap = 32
    for i, row in enumerate(lever_rows):
        yy = lever_y0 + i * lever_gap
        row_rect = pygame.Rect(x + 16, yy - 6, w - 32, 26)
        _draw_panel(screen, row_rect, fill=(60, 49, 41), border=(131, 104, 81), radius=8)
        row_surf = get_font(18).render(row, True, ACCENT_COLOR)
        row_text_rect = row_surf.get_rect(midleft=(row_rect.x + 9, row_rect.centery))
        screen.blit(row_surf, row_text_rect)

    metric_rows = [
        ("Employment", preview["employment"]),
        ("Inflation", preview["inflation"]),
        ("Debt / GDP", preview["debt"]),
        ("Reserves", preview["reserves"]),
        ("Bank Stability", preview["bank_stability"]),
    ]
    metric_y0 = lever_y0 + len(lever_rows) * lever_gap + 18
    metric_gap = 35
    metric_cutoff = button_safe_top - 86
    for i, (label, value) in enumerate(metric_rows):
        yy = metric_y0 + i * metric_gap
        if yy > metric_cutoff:
            break
        row_rect = pygame.Rect(x + 16, yy - 7, w - 32, 30)
        _draw_panel(screen, row_rect, fill=(66, 50, 43), border=(136, 106, 86), radius=8)
        value_color = GOOD_COLOR if value > 0 else BAD_COLOR if value < 0 else WARN_COLOR
        label_surf = get_font(20, bold=True).render(label, True, TEXT_COLOR)
        label_rect = label_surf.get_rect(midleft=(row_rect.x + 9, row_rect.centery))
        screen.blit(label_surf, label_rect)
        value_surf = get_font(20, bold=True).render(f"{value:+.2f}", True, value_color)
        value_rect = value_surf.get_rect(midright=(row_rect.right - 10, row_rect.centery))
        screen.blit(value_surf, value_rect)

    divider_y = min(metric_y0 + len(metric_rows) * metric_gap + 4, button_safe_top - 54)
    pygame.draw.line(screen, PANEL_EDGE, (x + 16, divider_y), (x + w - 16, divider_y), 2)
    title_y = divider_y + 12
    screen.blit(get_font(22, bold=True).render("Crisis Ledger", True, TEXT_COLOR), (x + 16, title_y))
    ledger_line_1_y = divider_y + 42
    ledger_line_2_y = divider_y + 66

    if last_result is None:
        text = "No year resolved yet. Stage directives and execute End Year."
        if _fits_text(ledger_line_1_y, 15):
            screen.blit(get_font(15).render(text, True, MUTED_TEXT), (x + 16, ledger_line_1_y))
        if _fits_text(ledger_line_2_y, 14):
            screen.blit(
                get_font(14).render("Shocks and damage reports will print here.", True, ACCENT_COLOR),
                (x + 16, ledger_line_2_y),
            )
        return

    if _fits_text(ledger_line_1_y, 14):
        screen.blit(
            get_font(14).render(f"Year {last_result.year}: {last_result.policy_summary}", True, MUTED_TEXT),
            (x + 16, ledger_line_1_y),
        )

    p = last_result.policy_effects
    policy_line = (
        f"Policy Delta  EMP {p['employment']:+.1f}   INF {p['inflation']:+.1f}   "
        f"DEBT {p['debt']:+.1f}   RES {p['reserves']:+.1f}"
    )
    if _fits_text(ledger_line_2_y, 14):
        screen.blit(get_font(14, bold=True).render(policy_line, True, WARN_COLOR), (x + 16, ledger_line_2_y))

    if last_result.events_triggered:
        events_y = divider_y + 90
        if _fits_text(events_y, 14):
            screen.blit(get_font(14, bold=True).render("Triggered events this year. See summary popup.", True, TEXT_COLOR), (x + 16, events_y))
    elif _fits_text(divider_y + 90, 14):
        screen.blit(get_font(14, bold=True).render("No major shocks this year.", True, GOOD_COLOR), (x + 16, divider_y + 90))


def draw_shock_event_popup(
    screen: pygame.Surface,
    event: WildcardEvent,
    year: int,
    index: int,
    total: int,
) -> None:
    def _effect_rows() -> list[tuple[str, float]]:
        rows = [
            ("Employment", event.d_employment),
            ("Inflation", event.d_inflation),
            ("Debt / GDP", event.d_debt),
            ("Reserves", event.d_reserves),
            ("Bank Stability", event.d_bank_stability),
            ("Avoidance Odds", -event.d_risk),
        ]
        return [(name, delta) for name, delta in rows if abs(delta) >= 0.01]

    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((6, 2, 2, 224))
    screen.blit(overlay, (0, 0))

    panel = pygame.Rect(110, 110, SCREEN_WIDTH - 220, SCREEN_HEIGHT - 220)
    _draw_panel(screen, panel, fill=(60, 34, 30), border=(188, 96, 78), radius=20, show_highlight=False)

    screen.blit(get_font(22, bold=True).render(f"SHOCK ALERT {index}/{total}", True, BAD_COLOR), (panel.x + 28, panel.y + 22))
    screen.blit(get_font(52, bold=True).render(f"Year {year}", True, TEXT_COLOR), (panel.x + 28, panel.y + 56))
    screen.blit(get_font(40, bold=True).render(event.name, True, WARN_COLOR), (panel.x + 28, panel.y + 120))
    pygame.draw.line(screen, (182, 95, 76), (panel.x + 28, panel.y + 176), (panel.right - 28, panel.y + 176), 3)

    max_w = panel.width - 56
    lines = _wrap_text(event.description, get_font(30), max_w)
    y_cursor = panel.y + 198
    for line in lines:
        screen.blit(get_font(30).render(line, True, TEXT_COLOR), (panel.x + 28, y_cursor))
        y_cursor += 38
        if y_cursor > panel.bottom - 230:
            break

    effects_title_y = max(y_cursor + 8, panel.y + 334)
    screen.blit(get_font(24, bold=True).render("Applied Economic Effects", True, TEXT_COLOR), (panel.x + 28, effects_title_y))
    effects = _effect_rows()
    for i, (label, delta) in enumerate(effects[:6]):
        yy = effects_title_y + 34 + i * 30
        color = GOOD_COLOR if delta > 0 else BAD_COLOR
        if label == "Inflation" and delta > 0:
            color = WARN_COLOR
        if label == "Debt / GDP" and delta > 0:
            color = BAD_COLOR
        row_rect = pygame.Rect(panel.x + 28, yy - 4, panel.width - 56, 24)
        _draw_panel(screen, row_rect, fill=(70, 42, 36), border=(152, 87, 71), radius=7)
        label_surf = get_font(18, bold=True).render(label, True, TEXT_COLOR)
        label_rect = label_surf.get_rect(midleft=(row_rect.x + 8, row_rect.centery))
        screen.blit(label_surf, label_rect)
        suffix = "%" if label in {"Employment", "Inflation", "Debt / GDP", "Avoidance Odds"} else ""
        value = f"{delta:+.1f}{suffix}"
        value_surf = get_font(18, bold=True).render(value, True, color)
        value_rect = value_surf.get_rect(midright=(row_rect.right - 8, row_rect.centery))
        screen.blit(value_surf, value_rect)

    footer = "Press Space/Enter or click to acknowledge this event"
    screen.blit(get_font(22, bold=True).render(footer, True, ACCENT_COLOR), (panel.x + 28, panel.bottom - 74))


def _policy_controls_layout(policy: pygame.Rect) -> dict[str, int]:
    col_gap = 10
    row_gap = 8
    button_h = 36
    button_w = (policy.width - 36 - 3 * col_gap) // 4
    row_1_y = policy.bottom - 86
    row_2_y = row_1_y + button_h + row_gap
    x0 = policy.x + 18
    return {
        "button_w": button_w,
        "button_h": button_h,
        "row_1_y": row_1_y,
        "row_2_y": row_2_y,
        "x0": x0,
        "col_gap": col_gap,
    }


def get_slider_layout() -> dict[str, pygame.Rect]:
    layout = get_ui_layout()
    policy = layout["policy"]
    base_x = policy.right - 250
    width = 190
    row_start = policy.y + 90
    row_gap = 68
    return {
        "interest": pygame.Rect(base_x, row_start + 10, width, 28),
        "tax": pygame.Rect(base_x, row_start + row_gap + 10, width, 28),
        "spending": pygame.Rect(base_x, row_start + 2 * row_gap + 10, width, 28),
        "liquidity": pygame.Rect(base_x, row_start + 3 * row_gap + 10, width, 28),
    }


def get_button_layout() -> dict[str, pygame.Rect]:
    layout = get_ui_layout()
    log = layout["log"]
    button_h = 40
    gap = 10
    button_w = (log.width - 32 - gap) // 2
    row_y = log.bottom - 48
    positions = {
        "new_game": pygame.Rect(log.x + 16, row_y, button_w, button_h),
        "end_year": pygame.Rect(log.x + 16 + button_w + gap, row_y, button_w, button_h),
    }
    return positions


def draw_end_state(screen: pygame.Surface, state: GameState) -> None:
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 188))
    screen.blit(overlay, (0, 0))

    card = pygame.Rect((SCREEN_WIDTH - 900) // 2, (SCREEN_HEIGHT - 340) // 2, 900, 340)
    _draw_panel(screen, card, fill=(52, 39, 33), border=(145, 107, 80), radius=18)

    if state.depression_triggered:
        title = "System Collapse"
        body = (
            f"By {state.year}, confidence broke. Employment {state.employment:.1f}%, "
            f"bank stability {state.bank_stability:.1f}, survival odds {state.avoid_chance:.1f}%."
        )
        color = BAD_COLOR
    elif state.victory:
        title = "Fragile Stabilization"
        body = (
            f"You reached {state.year - 1} with {state.avoid_chance:.1f}% odds "
            "of avoiding a full-scale Depression."
        )
        color = GOOD_COLOR
    else:
        title = "Simulation Concluded"
        body = "Timeline ended without immediate collapse, but systemic risk remains elevated."
        color = WARN_COLOR

    body_max_width = card.width - 64
    footer_max_width = card.width - 64
    screen.blit(get_font(52, bold=True).render(title, True, color), (card.x + 32, card.y + 46))
    body_lines = _wrap_text(body, get_font(23), body_max_width)
    body_y = card.y + 138
    for line in body_lines[:3]:
        screen.blit(get_font(23).render(line, True, TEXT_COLOR), (card.x + 32, body_y))
        body_y += 30

    footer = "Press N to start a new run. Press Esc to quit."
    footer_lines = _wrap_text(footer, get_font(21, bold=True), footer_max_width)
    footer_y = card.bottom - 92
    for line in footer_lines[:2]:
        screen.blit(get_font(21, bold=True).render(line, True, MUTED_TEXT), (card.x + 32, footer_y))
        footer_y += 28
