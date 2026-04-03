from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Any

from constants import END_YEAR, START_YEAR
from events import WildcardEvent, sample_events


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass
class PolicySelection:
    # Continuous stance per lever in [-1.0, 1.0]:
    # -1.0 = lower/decrease, 0.0 = hold, +1.0 = raise/increase
    interest_rate: float = 0.0
    tax_rate: float = 0.0
    government_spending: float = 0.0
    emergency_liquidity: float = 0.0


@dataclass
class TurnResult:
    year: int
    policy_summary: str
    policy_effects: dict[str, float]
    net_changes: dict[str, float]
    events_triggered: list[WildcardEvent]
    avoid_chance: float
    depression_triggered: bool


@dataclass
class GameState:
    year: int = START_YEAR
    turn_index: int = 0

    # "Real-ish" starting values for the U.S. around 1920.
    employment: float = 95.0  # (%)
    inflation: float = 1.0  # (%)
    debt: float = 33.0  # Debt/GDP (%)
    reserves: float = 85.0  # Treasury capacity index (0-100+)
    bank_stability: float = 74.0  # Banking system confidence index (0-100)

    # Policy controls.
    policy_rate: float = 4.0  # Approx short-term nominal policy rate (%)
    tax_level: float = 11.0  # Effective federal tax burden (% of GDP)
    spending_level: float = 3.5  # Federal spending (% of GDP)
    liquidity_level: float = 3.0  # Emergency lending intensity index

    avoid_chance: float = 90.0
    initial_avoid_chance: float = 90.0
    policy_missteps: int = 0
    depression_triggered: bool = False
    victory: bool = False
    history: list[TurnResult] = field(default_factory=list)

    def is_finished(self) -> bool:
        return self.depression_triggered or self.victory or self.year > END_YEAR

    def apply_turn(self, policy: PolicySelection, rng: Random) -> TurnResult:
        if self.is_finished():
            raise RuntimeError("Game already finished.")

        before = {
            "employment": self.employment,
            "inflation": self.inflation,
            "debt": self.debt,
            "reserves": self.reserves,
            "bank_stability": self.bank_stability,
        }
        policy_effects = self._apply_policy(policy)
        self._apply_policy_discipline(policy)
        events_triggered = sample_events(self.year, rng)
        for event in events_triggered:
            self._apply_event(event)

        self._recompute_outcome()
        net_changes = {
            "employment": self.employment - before["employment"],
            "inflation": self.inflation - before["inflation"],
            "debt": self.debt - before["debt"],
            "reserves": self.reserves - before["reserves"],
            "bank_stability": self.bank_stability - before["bank_stability"],
        }
        result = TurnResult(
            year=self.year,
            policy_summary=self._summarize_policy(policy),
            policy_effects=policy_effects,
            net_changes=net_changes,
            events_triggered=events_triggered,
            avoid_chance=self.avoid_chance,
            depression_triggered=self.depression_triggered,
        )
        self.history.append(result)
        self.turn_index += 1
        self.year += 1

        if self.year > END_YEAR and not self.depression_triggered:
            self.victory = self.avoid_chance >= 60.0

        return result

    def _apply_policy(self, policy: PolicySelection) -> dict[str, float]:
        # Apply lever positions first so policy can accumulate across rounds.
        self.policy_rate = clamp(self.policy_rate + 0.75 * policy.interest_rate, 0.0, 12.0)
        self.tax_level = clamp(self.tax_level + 0.8 * policy.tax_rate, 5.0, 30.0)
        self.spending_level = clamp(
            self.spending_level + 0.6 * policy.government_spending, 1.5, 20.0
        )
        self.liquidity_level = clamp(
            self.liquidity_level + 0.7 * policy.emergency_liquidity, 0.0, 12.0
        )

        (
            d_employment,
            d_inflation,
            d_debt,
            d_reserves,
            d_bank_stability,
        ) = self._compute_policy_deltas(
            policy,
            self.policy_rate,
            self.tax_level,
            self.spending_level,
            self.liquidity_level,
        )

        self.employment += d_employment
        self.inflation += d_inflation
        self.debt += d_debt
        self.reserves += d_reserves
        self.bank_stability += d_bank_stability

        self._clamp_metrics()
        return {
            "employment": d_employment,
            "inflation": d_inflation,
            "debt": d_debt,
            "reserves": d_reserves,
            "bank_stability": d_bank_stability,
        }

    def preview_policy(self, policy: PolicySelection) -> dict[str, float]:
        next_policy_rate = clamp(self.policy_rate + 0.75 * policy.interest_rate, 0.0, 12.0)
        next_tax_level = clamp(self.tax_level + 0.8 * policy.tax_rate, 5.0, 30.0)
        next_spending_level = clamp(self.spending_level + 0.6 * policy.government_spending, 1.5, 20.0)
        next_liquidity_level = clamp(
            self.liquidity_level + 0.7 * policy.emergency_liquidity,
            0.0,
            12.0,
        )
        (
            d_employment,
            d_inflation,
            d_debt,
            d_reserves,
            d_bank_stability,
        ) = self._compute_policy_deltas(
            policy,
            next_policy_rate,
            next_tax_level,
            next_spending_level,
            next_liquidity_level,
        )
        return {
            "policy_rate": next_policy_rate,
            "tax_level": next_tax_level,
            "spending_level": next_spending_level,
            "liquidity_level": next_liquidity_level,
            "employment": d_employment,
            "inflation": d_inflation,
            "debt": d_debt,
            "reserves": d_reserves,
            "bank_stability": d_bank_stability,
        }

    @staticmethod
    def _compute_policy_deltas(
        policy: PolicySelection,
        policy_rate: float,
        tax_level: float,
        spending_level: float,
        liquidity_level: float,
    ) -> tuple[float, float, float, float, float]:
        # Reduced-form dynamics tuned to create historically plausible trajectories.
        demand_impulse = (
            -0.9 * policy.interest_rate
            - 0.7 * policy.tax_rate
            + 1.0 * policy.government_spending
            + 0.7 * policy.emergency_liquidity
        )
        anti_inflation_bias = 0.20 * (policy_rate - 4.0) + 0.08 * (tax_level - 11.0)

        d_employment = 0.95 * demand_impulse
        d_inflation = 0.42 * demand_impulse - anti_inflation_bias
        d_debt = (
            0.95 * max(0.0, spending_level - 3.5)
            - 0.55 * max(0.0, tax_level - 11.0)
            + 0.40 * max(0.0, liquidity_level - 3.0)
        )
        d_reserves = (
            1.0 * max(0.0, tax_level - 11.0)
            - 1.4 * max(0.0, spending_level - 3.5)
            - 0.9 * max(0.0, liquidity_level - 3.0)
        )
        d_bank_stability = (
            -0.7 * max(0.0, policy_rate - 5.0)
            + 0.9 * max(0.0, liquidity_level - 3.0)
            + 0.2 * policy.interest_rate
        )
        return d_employment, d_inflation, d_debt, d_reserves, d_bank_stability

    def _apply_event(self, event: WildcardEvent) -> None:
        self.employment += event.d_employment
        self.inflation += event.d_inflation
        self.debt += event.d_debt
        self.reserves += event.d_reserves
        self.bank_stability += event.d_bank_stability
        self.avoid_chance += -event.d_risk
        self._clamp_metrics()

    def _apply_policy_discipline(self, policy: PolicySelection) -> None:
        # Penalize pro-cyclical tightening when the system is already weak.
        tightening = (
            max(0, policy.interest_rate)
            + max(0, policy.tax_rate)
            + max(0, -policy.government_spending)
            + max(0, -policy.emergency_liquidity)
        )
        support = (
            max(0, -policy.interest_rate)
            + max(0, -policy.tax_rate)
            + max(0, policy.government_spending)
            + max(0, policy.emergency_liquidity)
        )
        fragile = self.employment < 90.0 or self.bank_stability < 68.0 or self.reserves < 45.0

        if tightening >= 2:
            self.policy_missteps += 1
        elif tightening == 0 and support >= 2:
            self.policy_missteps = max(0, self.policy_missteps - 1)

        if fragile and tightening > 0:
            self.employment -= 0.85 * tightening
            self.bank_stability -= 1.10 * tightening
            self.reserves -= 0.75 * tightening
        elif fragile and support >= 2:
            self.employment += 0.90 * support
            self.bank_stability += 1.20 * support
            self.reserves += 0.80 * support

        # Failing to respond in fragile crisis years compounds systemic risk.
        if self.year >= 1929 and fragile and support == 0:
            self.policy_missteps += 1
            self.employment -= 0.5
            self.bank_stability -= 0.7

        if self.policy_missteps >= 3:
            extra = self.policy_missteps - 2
            self.employment -= 0.9 * extra
            self.bank_stability -= 1.2 * extra
            self.reserves -= 0.8 * extra

        self._clamp_metrics()

    def _recompute_outcome(self) -> None:
        # Risk model combines unemployment, banking stress, deflation, debt, and reserve depletion.
        unemployment = 100.0 - self.employment
        deflation_stress = max(0.0, -self.inflation) * 2.8
        debt_stress = max(0.0, self.debt - 60.0) * 0.55
        reserve_stress = max(0.0, 38.0 - self.reserves) * 0.75
        bank_stress = max(0.0, 63.0 - self.bank_stability) * 0.85
        misstep_stress = self.policy_missteps * 3.5

        total_stress = (
            0.82 * unemployment
            + deflation_stress
            + debt_stress
            + reserve_stress
            + bank_stress
            + misstep_stress
        )
        self.avoid_chance = clamp(100.0 - total_stress, 0.0, 100.0)

        self.depression_triggered = (
            self.avoid_chance <= 8.0
            or self.employment < 74.0
            or self.bank_stability < 28.0
            or self.reserves < 14.0
            or (
                self.year >= 1929
                and self.policy_missteps >= 4
                and (self.employment < 85.0 or self.bank_stability < 50.0)
            )
        )

    def _clamp_metrics(self) -> None:
        self.employment = clamp(self.employment, 45.0, 100.0)
        self.inflation = clamp(self.inflation, -20.0, 20.0)
        self.debt = clamp(self.debt, 10.0, 220.0)
        self.reserves = clamp(self.reserves, 0.0, 130.0)
        self.bank_stability = clamp(self.bank_stability, 0.0, 100.0)
        self.avoid_chance = clamp(self.avoid_chance, 0.0, 100.0)

    @staticmethod
    def _summarize_policy(policy: PolicySelection) -> str:
        def stance(value: float, low_word: str, hold_word: str, high_word: str) -> str:
            if value <= -0.08:
                return f"{low_word} ({value:+.2f})"
            if value >= 0.08:
                return f"{high_word} ({value:+.2f})"
            return f"{hold_word} ({value:+.2f})"

        rate_txt = stance(policy.interest_rate, "lowered", "held", "raised")
        tax_txt = stance(policy.tax_rate, "lowered", "held", "raised")
        spend_txt = stance(policy.government_spending, "cut", "held", "increased")
        loan_txt = stance(policy.emergency_liquidity, "reduced", "held", "expanded")
        return (
            f"Rates {rate_txt}; taxes {tax_txt}; spending {spend_txt}; "
            f"emergency liquidity {loan_txt}."
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "employment": self.employment,
            "inflation": self.inflation,
            "debt": self.debt,
            "reserves": self.reserves,
            "bank_stability": self.bank_stability,
            "policy_rate": self.policy_rate,
            "tax_level": self.tax_level,
            "spending_level": self.spending_level,
            "liquidity_level": self.liquidity_level,
            "avoid_chance": self.avoid_chance,
            "policy_missteps": self.policy_missteps,
            "depression_triggered": self.depression_triggered,
            "victory": self.victory,
        }
