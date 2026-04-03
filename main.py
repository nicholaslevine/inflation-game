from __future__ import annotations

import argparse
import sys
from random import Random

import pygame

from constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from engine import GameState, PolicySelection
from ui import (
    Button,
    Slider,
    draw_end_state,
    draw_game,
    draw_shock_event_popup,
    draw_year_summary_popup,
    get_button_layout,
    get_slider_layout,
)


def _prompt_choice(label: str) -> int:
    prompt = f"{label} [-1=lower/cut, 0=hold, 1=raise/increase]: "
    while True:
        raw = input(prompt).strip()
        if raw in {"-1", "0", "1"}:
            return int(raw)
        print("Enter -1, 0, or 1.")


def run_terminal_game() -> None:
    rng = Random()
    state = GameState()
    print("No graphics framebuffer detected. Running terminal mode.\n")
    print("Controls each year: -1 lower/cut, 0 hold, 1 raise/increase.\n")

    while not state.is_finished():
        print(f"\n=== Year {state.year} ===")
        print(
            f"Employment {state.employment:.1f}% | Inflation {state.inflation:.1f}% | "
            f"Debt {state.debt:.1f}% | Reserves {state.reserves:.1f} | "
            f"Bank {state.bank_stability:.1f} | Avoid {state.avoid_chance:.1f}%"
        )

        policy = PolicySelection(
            interest_rate=_prompt_choice("Interest Rate"),
            tax_rate=_prompt_choice("Taxes"),
            government_spending=_prompt_choice("Government Spending"),
            emergency_liquidity=_prompt_choice("Emergency Loans"),
        )
        result = state.apply_turn(policy, rng)
        print(f"Policy: {result.policy_summary}")
        if result.events_triggered:
            print("Events:")
            for e in result.events_triggered:
                print(f"- {e.name}: {e.description}")
        else:
            print("Events: none")
        print(f"Avoid chance now: {result.avoid_chance:.1f}%")

    print("\n=== End State ===")
    if state.depression_triggered:
        print("The Great Depression begins in your timeline.")
    elif state.victory:
        print("You stabilized the economy through 1935.")
    else:
        print("Timeline ended without total collapse, but risk remains elevated.")


def run_game() -> None:
    pygame.init()
    pygame.display.set_caption("Inflation Game - Federal Reserve Simulator")
    try:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    except pygame.error as exc:
        pygame.quit()
        print(f"pygame window unavailable ({exc}).")
        run_terminal_game()
        return
    clock = pygame.time.Clock()

    rng = Random()
    state = GameState()
    pending_policy = PolicySelection()
    last_result = None
    show_year_summary = False
    pending_event_alerts = []
    current_event_alert = 0

    def set_interest(value: float) -> None:
        pending_policy.interest_rate = max(-1.0, min(1.0, value))

    def set_tax(value: float) -> None:
        pending_policy.tax_rate = max(-1.0, min(1.0, value))

    def set_spending(value: float) -> None:
        pending_policy.government_spending = max(-1.0, min(1.0, value))

    def set_liquidity(value: float) -> None:
        pending_policy.emergency_liquidity = max(-1.0, min(1.0, value))

    def end_year() -> None:
        nonlocal last_result, pending_policy, show_year_summary, pending_event_alerts, current_event_alert
        if state.is_finished():
            return
        last_result = state.apply_turn(pending_policy, rng)
        pending_policy = PolicySelection()
        for slider in sliders:
            slider.dragging = False
        pending_event_alerts = list(last_result.events_triggered)
        current_event_alert = 0
        show_year_summary = not pending_event_alerts

    def new_game() -> None:
        nonlocal state, pending_policy, last_result, show_year_summary, pending_event_alerts, current_event_alert
        state = GameState()
        pending_policy = PolicySelection()
        last_result = None
        show_year_summary = False
        pending_event_alerts = []
        current_event_alert = 0

    button_rects = get_button_layout()
    buttons = [
        Button(button_rects["new_game"], "New Game", new_game, pygame.K_n),
        Button(button_rects["end_year"], "End Year", end_year, pygame.K_SPACE),
    ]
    slider_rects = get_slider_layout()
    sliders = [
        Slider(slider_rects["interest"], "Interest Rate", lambda: pending_policy.interest_rate, set_interest, pygame.K_a, pygame.K_d),
        Slider(slider_rects["tax"], "Tax Level", lambda: pending_policy.tax_rate, set_tax, pygame.K_s, pygame.K_w),
        Slider(slider_rects["spending"], "Government Spending", lambda: pending_policy.government_spending, set_spending, pygame.K_q, pygame.K_e),
        Slider(slider_rects["liquidity"], "Emergency Liquidity", lambda: pending_policy.emergency_liquidity, set_liquidity, pygame.K_f, pygame.K_r),
    ]

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif pending_event_alerts:
                if event.type == pygame.KEYDOWN and event.key in {pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER}:
                    current_event_alert += 1
                    if current_event_alert >= len(pending_event_alerts):
                        pending_event_alerts = []
                        current_event_alert = 0
                        show_year_summary = True
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    current_event_alert += 1
                    if current_event_alert >= len(pending_event_alerts):
                        pending_event_alerts = []
                        current_event_alert = 0
                        show_year_summary = True
            elif show_year_summary:
                if event.type == pygame.KEYDOWN and event.key in {pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER}:
                    for slider in sliders:
                        slider.dragging = False
                    show_year_summary = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for slider in sliders:
                        slider.dragging = False
                    show_year_summary = False
            else:
                for slider in sliders:
                    if slider.handle_event(event):
                        break
                for button in buttons:
                    button.handle_event(event)

        draw_game(screen, state, pending_policy, last_result, buttons, sliders)
        if pending_event_alerts and last_result is not None:
            active_event = pending_event_alerts[current_event_alert]
            draw_shock_event_popup(
                screen,
                active_event,
                last_result.year,
                current_event_alert + 1,
                len(pending_event_alerts),
            )
        elif show_year_summary and last_result is not None:
            draw_year_summary_popup(screen, last_result, state)
        if state.is_finished() and not show_year_summary and not pending_event_alerts:
            draw_end_state(screen, state)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Great Depression policy simulation.")
    parser.add_argument(
        "--terminal",
        action="store_true",
        help="Force terminal mode without opening a pygame window.",
    )
    args = parser.parse_args()

    if args.terminal:
        run_terminal_game()
    else:
        run_game()
