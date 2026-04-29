# 2048 Strategy for Score Maximization

## Core Principle: Corner Locking

Always keep your highest tile in one corner (typically bottom-right). This creates a stable anchor point that prevents your largest values from getting trapped in the middle of the board. Your next highest tiles should be arranged adjacent to this corner tile, creating a descending sequence along the edges.

## Building Monotonic Rows and Columns

Maintain a monotonic (consistently increasing or decreasing) sequence of tiles along your chosen corner's row and column. For example, if your highest tile is in the bottom-right corner, the bottom row should decrease leftward, and the right column should decrease upward. This "snake" pattern allows tiles to merge naturally as they cascade toward your corner.

## Merge Timing and Patience

- Only merge tiles when they are adjacent in your monotonic sequence
- Avoid merging tiles that would break your corner-locked pattern
- Let smaller tiles accumulate and merge gradually rather than forcing immediate combinations
- When you have a choice, merge tiles that are farthest from your corner first

## The Danger of Random Lateral Moves

Random lateral moves (swiping left when you've committed to bottom-right corner) are extremely dangerous because they:
- Disrupt your monotonic sequence
- Can trap your highest tile away from its corner
- Create gaps that fill with random tiles, breaking your pattern
- Often lead to deadlocked boards where no useful moves remain

## Tactical Decision-Making

Before each move, re-evaluate the entire board. Ask:
1. Is my highest tile still in its corner?
2. Are my rows and columns still monotonic?
3. Will this move create a gap that can't be easily filled?
4. Can I combine small tiles without disrupting my pattern?

## Emergency Recovery

If forced to break your corner pattern:
- Immediately work to re-establish the corner
- Use the edge opposite your corner as a temporary holding area
- Never make two consecutive moves away from your corner

## Sources

- https://puzzling.stackexchange.com/questions/39/general-strategy-for-2048
- https://www.imore.com/2048-tips-and-tricks
- https://www.quora.com/How-do-I-win-the-game-%E2%80%9C2048%E2%80%9D
- https://www.reddit.com/r/2048/comments/2j08rx/give_us_your_best_tips_for_higher_play/
