# Inflation Game (Great Depression Policy Simulator)

`pygame` simulation where the player acts as U.S. policymakers from 1920 to 1935.

## Concept
- You control:
  - Interest rates
  - Taxes
  - Government spending
  - Emergency bank liquidity/loans
- Each year, probabilistic and historically grounded events may trigger (crash, bank runs, tariff shocks, Dust Bowl, etc.).
- Goal: maximize your probability of avoiding a full depression by keeping:
  - Employment and reserves high
  - Inflation and debt in a controlled range
  - Banking system stable

## Run
```bash
python3 -m pip install pygame
python3 main.py
```

## Controls
- `A / D`: lower/raise interest-rate stance
- `W / S`: lower/raise tax stance
- `Q / E`: cut/increase government spending
- `F / R`: reduce/expand emergency loans
- `Space`: end year and resolve outcomes
- `N`: new game
- `Esc`: quit
