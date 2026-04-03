from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass(frozen=True)
class WildcardEvent:
    name: str
    description: str
    year_start: int
    year_end: int
    probability: float
    d_employment: float = 0.0
    d_inflation: float = 0.0
    d_debt: float = 0.0
    d_reserves: float = 0.0
    d_bank_stability: float = 0.0
    d_risk: float = 0.0

    def valid_in_year(self, year: int) -> bool:
        return self.year_start <= year <= self.year_end


WILDCARD_EVENTS = [
    WildcardEvent(
        name="1920-21 Deflationary Recession",
        description="Post-war demand drops and prices unwind sharply.",
        year_start=1920,
        year_end=1921,
        probability=0.65,
        d_employment=-2.8,
        d_inflation=-2.1,
        d_reserves=-4.0,
        d_risk=3.5,
    ),
    WildcardEvent(
        name="Speculative Credit Boom",
        description="Loose margin lending inflates equity prices beyond fundamentals.",
        year_start=1926,
        year_end=1929,
        probability=0.40,
        d_employment=0.8,
        d_inflation=0.5,
        d_bank_stability=-4.0,
        d_risk=5.0,
    ),
    WildcardEvent(
        name="Stock Market Crash",
        description="Panic selling slashes household wealth and business confidence.",
        year_start=1929,
        year_end=1929,
        probability=0.92,
        d_employment=-6.2,
        d_inflation=-1.4,
        d_debt=2.2,
        d_reserves=-8.0,
        d_bank_stability=-9.0,
        d_risk=18.0,
    ),
    WildcardEvent(
        name="Bank Runs Spread",
        description="Deposit withdrawals force widespread bank failures.",
        year_start=1930,
        year_end=1932,
        probability=0.45,
        d_employment=-3.8,
        d_inflation=-0.8,
        d_debt=1.5,
        d_reserves=-5.0,
        d_bank_stability=-10.0,
        d_risk=12.0,
    ),
    WildcardEvent(
        name="Tariff Retaliation Shock",
        description="Trading partners retaliate after tariff policy, cutting exports.",
        year_start=1930,
        year_end=1932,
        probability=0.45,
        d_employment=-2.1,
        d_inflation=-0.6,
        d_reserves=-3.0,
        d_risk=6.0,
    ),
    WildcardEvent(
        name="Emergency Relief Demand",
        description="Mass unemployment drives pressure for relief and public works.",
        year_start=1931,
        year_end=1935,
        probability=0.40,
        d_debt=1.8,
        d_reserves=-2.5,
        d_risk=2.8,
    ),
    WildcardEvent(
        name="New Deal Confidence Bump",
        description="Institutional reforms improve confidence and credit flow.",
        year_start=1933,
        year_end=1935,
        probability=0.55,
        d_employment=3.2,
        d_inflation=0.7,
        d_debt=1.0,
        d_bank_stability=9.0,
        d_risk=-12.0,
    ),
    WildcardEvent(
        name="Dust Bowl Disruption",
        description="Agricultural collapse increases hardship and migration.",
        year_start=1934,
        year_end=1935,
        probability=0.45,
        d_employment=-1.8,
        d_inflation=0.2,
        d_reserves=-2.0,
        d_risk=4.5,
    ),
]


YEARLY_SHOCK_EVENTS = [
    WildcardEvent(
        name="Regional Drought",
        description="Crop failures cut incomes, trigger loan distress, and drain reserves.",
        year_start=1920,
        year_end=1935,
        probability=1.0,
        d_employment=-1.9,
        d_inflation=0.7,
        d_debt=0.9,
        d_reserves=-2.8,
        d_bank_stability=-2.5,
        d_risk=5.2,
    ),
    WildcardEvent(
        name="Industrial Layoff Wave",
        description="Manufacturing retrenchment drives unemployment and confidence shocks.",
        year_start=1920,
        year_end=1935,
        probability=1.0,
        d_employment=-2.2,
        d_inflation=-0.7,
        d_debt=0.9,
        d_reserves=-2.1,
        d_bank_stability=-3.2,
        d_risk=6.0,
    ),
    WildcardEvent(
        name="Rail and Freight Strike",
        description="Supply disruptions trigger losses and worsen bank liquidity pressure.",
        year_start=1920,
        year_end=1935,
        probability=1.0,
        d_employment=-1.6,
        d_inflation=0.4,
        d_debt=0.5,
        d_reserves=-2.4,
        d_bank_stability=-2.0,
        d_risk=4.0,
    ),
    WildcardEvent(
        name="Credit Panic Rumors",
        description="Rumor-driven withdrawals weaken banks and tighten lending.",
        year_start=1920,
        year_end=1935,
        probability=1.0,
        d_employment=-1.4,
        d_inflation=-0.4,
        d_debt=0.6,
        d_reserves=-2.8,
        d_bank_stability=-3.8,
        d_risk=5.8,
    ),
    WildcardEvent(
        name="Commodity Price Slump",
        description="Falling farm and raw-material prices force debt stress in rural regions.",
        year_start=1920,
        year_end=1935,
        probability=1.0,
        d_employment=-1.5,
        d_inflation=-1.2,
        d_debt=0.7,
        d_reserves=-2.0,
        d_bank_stability=-2.5,
        d_risk=4.8,
    ),
    WildcardEvent(
        name="Unexpected Export Contract",
        description="Foreign demand briefly boosts jobs and reserve inflows.",
        year_start=1920,
        year_end=1935,
        probability=1.0,
        d_employment=1.8,
        d_inflation=0.5,
        d_debt=-0.9,
        d_reserves=2.6,
        d_bank_stability=2.0,
        d_risk=-4.0,
    ),
    WildcardEvent(
        name="Productivity Breakthrough",
        description="Efficiency gains lower costs and stabilize confidence.",
        year_start=1920,
        year_end=1935,
        probability=1.0,
        d_employment=1.4,
        d_inflation=-0.2,
        d_debt=-0.6,
        d_reserves=1.8,
        d_bank_stability=2.2,
        d_risk=-3.4,
    ),
]


def sample_events(year: int, rng: Random) -> list[WildcardEvent]:
    triggered: list[WildcardEvent] = []
    for event in WILDCARD_EVENTS:
        if event.valid_in_year(year) and rng.random() <= event.probability:
            triggered.append(event)
    shock = _sample_yearly_shock(year, rng)
    if shock is not None:
        triggered.append(shock)
    return triggered


def _sample_yearly_shock(year: int, rng: Random) -> WildcardEvent | None:
    valid_events = [event for event in YEARLY_SHOCK_EVENTS if event.valid_in_year(year)]
    if not valid_events:
        return None

    # No guaranteed yearly shock. The crisis era is harsher from 1929-1932.
    shock_probability = 0.78 if year < 1929 else 0.90 if year <= 1932 else 0.82
    if rng.random() > shock_probability:
        return None

    # Mostly negative outcomes, with occasional positive relief.
    weights = [0.17, 0.17, 0.16, 0.16, 0.14, 0.11, 0.09]
    return rng.choices(valid_events, weights=weights[: len(valid_events)], k=1)[0]
