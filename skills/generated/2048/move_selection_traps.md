# Common 2048 Move-Selection Traps and Recovery Patterns

## The Anchor Corner Trap

**The trap:** Breaking your anchor corner by moving tiles away from it, or allowing a small tile to get stuck there.

**The fix:** Always keep your highest tile in one corner (typically bottom-left or top-left). Never move that tile away from the corner. If a 2 or 4 spawns in your anchor corner, do NOT move it—merge it with an adjacent tile first, or use a sequence that pushes it toward the corner without breaking your chain.

## The Isolated Large Tile Trap

**The trap:** Your largest tile gets surrounded by smaller tiles that cannot merge with it, blocking its growth path.

**The fix:** Keep your largest tile in the anchor corner with a descending chain of tiles along the edge. For example, if your anchor is bottom-left, maintain a row like 1024, 512, 256, 128 along the bottom row. Never let a small tile get between your largest tile and its next merge partner.

## The Overusing Down/Right Trap

**The trap:** Moving only down and right (or only two directions) until you box yourself into a corner with no good moves left.

**The fix:** Use three directions, not two. The standard strategy is to move only down, left, and up (never right), or down, right, and up (never left). Reserve the third direction for emergencies. If you must use the forbidden direction, do it only when it creates a merge that clears space.

## The Single-Merge Chase Trap

**The trap:** Obsessing over one big merge (e.g., combining two 512s) while ignoring the rest of the board, causing the board to fill up with small tiles.

**The fix:** Always maintain board order. Before chasing a big merge, ensure your smaller tiles are organized in descending chains. If the board is getting cluttered, take a detour to clean up small tiles first. A single merge is worthless if you run out of space.

## Recovery Patterns

### Pattern 1: The Snake Recovery
When your anchor corner is compromised, create a "snake" pattern by building a descending chain along one edge, then zigzag back. This re-establishes order without losing progress.

### Pattern 2: The Emergency Clear
If the board is nearly full, use a sequence of moves that creates multiple merges simultaneously. Move in the direction that collapses the most tiles, even if it temporarily breaks your anchor.

### Pattern 3: The Sacrifice
Sometimes you must sacrifice a medium tile (e.g., 64) to free up space. Merge it with a smaller tile to create a new chain, accepting the temporary loss of progress.

## Tactical Rules for Turn-by-Turn Planning

1. **Before each move, check:** Will this move break my anchor corner? If yes, find another move.
2. **Maintain a descending chain** along your anchor edge. If the chain is broken, prioritize fixing it.
3. **Never use the forbidden direction** unless it creates at least one merge and clears at least two empty cells.
4. **When in doubt, move toward your anchor corner.** This preserves board structure.
5. **If the board is 75% full,** stop chasing big merges and focus on clearing small tiles.

## Sources
- https://ironyca.wordpress.com/2014/03/20/strategy-guide-to-winning-the-2048-game/
- https://puzzling.stackexchange.com/questions/39/general-strategy-for-2048
- https://www.arkadium.com/blog/how-to-beat-2048/
- https://www.2048.org/strategy-tips/
