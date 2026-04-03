# Inflation Game (Great Depression Policy Simulator)

`pygame` simulation where the player acts as U.S. policymakers from 1920 to 1935.

## Concept
- You control:
  - Interest rates
  - Taxes
  - Government spending
  - Emergency bank liquidity/loans
- Each year, some historically grounded events may trigger (crash, bank runs, tariff shocks, Dust Bowl, etc.), which will most likely be detrimental by may be positive.
- Goal: maximize your probability of avoiding a full depression by keeping:
  - Employment and reserves high
  - Inflation and debt in a controlled range
  - Banking system stable
- Difficulty: This game is intentionally made to be very hard to win: only a few mistakes had to be made to cause the Great Depression, and we sought to replicate that here. 

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
