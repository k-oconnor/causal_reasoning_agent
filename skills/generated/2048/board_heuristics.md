# Board Evaluation Heuristics for 2048

When selecting a slide direction on each turn, evaluate the board state using these five heuristics. Combine them into a weighted score to compare candidate moves.

## 1. Empty Cells (Monotonic Bonus)
- **Goal:** Maximize the number of empty cells after the move.
- **Rationale:** More empty cells give more room to maneuver and reduce the chance of being forced into a dead end.
- **Tactic:** Prefer moves that leave 3+ empty cells. If a move leaves 0 or 1 empty cells, heavily penalize it unless it creates a high-value merge.

## 2. Immediate Merges
- **Goal:** Maximize the total value of tiles that can merge in one move.
- **Rationale:** Merging tiles increases your score and consolidates the board, making it easier to build larger tiles.
- **Tactic:** Sum the values of all pairs that would merge. Prefer moves with the highest merge sum. A move that merges two 128s (total 256) is better than merging two 32s (total 64).

## 3. Max Tile Placement
- **Goal:** Keep the highest tile in a corner (preferably bottom-left or bottom-right).
- **Rationale:** A corner-anchored high tile creates a stable "snake" pattern that allows systematic tile building.
- **Tactic:** After each move, check if the max tile remains in its corner. If it moves away from the corner, penalize that move. If it stays or moves closer to the corner, reward it.

## 4. Smoothness (Monotonicity)
- **Goal:** Ensure tile values decrease monotonically along rows and columns from the corner anchor.
- **Rationale:** A smooth board (e.g., 256, 128, 64, 32 along a row) allows easy merges and prevents small tiles from blocking large ones.
- **Tactic:** For each row and column, sum the absolute differences between adjacent tiles. Lower total = smoother board. Prefer moves that reduce this sum.

## 5. Preserving Legal Future Moves
- **Goal:** Avoid moves that create "dead" board states where no merges are possible.
- **Rationale:** A move that looks good now might leave the board in a state where the next turn has only 1 or 2 legal moves, increasing the risk of game over.
- **Tactic:** Simulate the board after your move, then count how many legal moves remain. Prefer moves that leave 3+ legal moves. Penalize moves that leave 0-1 legal moves.

## Weighted Scoring Formula
Combine the heuristics into a single score for each candidate move:

```
Score = (w1 * EmptyCells) + (w2 * MergeSum) + (w3 * CornerBonus) + (w4 * -SmoothnessPenalty) + (w5 * FutureMoves)
```

Recommended starting weights (adjust based on playtesting):
- w1 = 10 (empty cells)
- w2 = 1 (merge sum, scaled by tile value)
- w3 = 50 (corner bonus, binary: 50 if max tile stays in corner, 0 otherwise)
- w4 = 1 (smoothness penalty, use negative of sum of differences)
- w5 = 20 (future moves, scaled by number of legal moves remaining)

## Turn-by-Turn Decision Process
1. For each of the 4 possible slide directions (up, down, left, right):
   - Simulate the move on a copy of the board.
   - Calculate the heuristic score using the formula above.
2. Select the direction with the highest score.
3. If two directions have equal scores, prefer the one that keeps the max tile in the corner.

## Sources
- https://stackoverflow.com/questions/22342854/what-is-the-optimal-algorithm-for-the-game-2048
- https://theresamigler.com/wp-content/uploads/2020/03/2048.pdf
- https://www.baeldung.com/cs/2048-algorithm
- https://www.researchgate.net/publication/335594398_Composition_of_basic_heuristics_for_the_game_2048
