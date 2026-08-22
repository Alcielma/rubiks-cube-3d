# Development Plan: General-Purpose Cube Solver

> **Status:** Phases 0-3 (foundations, bottom cross, first-layer corners,
> second-layer edges) are done. See `docs/CHANGELOG.md` for what actually
> changed in each phase, verified results, and any bugs found along the
> way. This file stays a plan of record; the changelog is the detailed
> history.

## Problem statement

`CubeSolver.solve()` currently only reverses `Cube.scramble_history` — it can
undo exactly the moves `scramble()` made, in reverse, with each angle negated.
It cannot solve:

- A cube scrambled partly by hand (`L/R/U/D/F/B` keys), since manual turns
  are never recorded in `scramble_history`.
- A cube whose history was cleared/lost (e.g. after a previous solve, then a
  few more manual turns).
- Any state set up independently of this app's own move log.

Goal: make `K` solve the cube from **any legally-reachable state**, by reading
the cube's current piece positions/orientations directly instead of relying
on a move log. Every state produced by real quarter-turns is solvable by
construction, so we don't need illegal-state detection — just a real
solving algorithm.

The natural fit is the **beginner's Layer-By-Layer (LBL) method**, since
`src/solver/solver.py` already has placeholder methods named for exactly
this method (`solve_layer1_cross`, `solve_layer1_corners`, `solve_layer2`,
`solve_layer3_cross`, `solve_layer3_orient_corners`,
`solve_layer3_position_corners`, `solve_layer3_position_edges`).

---

## Phase 0 — Foundations (refactor before adding solving logic) — ✅ done

Goal: give the solver a clean, non-graphics API to read/mutate cube state,
and a single source of truth for move execution.

- Add `get_corner_cubie(color1, color2, color3)` next to the existing
  `get_edge_cubie(color1, color2)` in `solver.py`.
- Add `get_center_color(face)` — centers never move, so this is the fixed
  reference for "what color belongs on this face."
- Unify move application. Today the same concept is expressed three
  different ways:
  - `InputHandler` calls `cube.rotate_face(axis, index, angle)` directly.
  - `Cube.scramble()` re-implements the rotation math inline instead of
    calling `rotate_face`.
  - `CubeSolver` has unused `move_L`/`move_L_prime`/etc. helpers that push
    `(name, axis, index, angle)` onto `renderer.move_queue`, but `solve()`
    itself bypasses them and pushes tuples directly.

  Consolidate to one path: a `Cube.apply_move(notation)` (or equivalent)
  that all three call sites use, so future algorithm code can't drift out
  of sync with manual/scramble behavior.
- Add 180° turn support. LBL algorithms use double moves (`U2`, `R2`, ...)
  constantly; today only ±90° is exercised. Verify `Cube.update()`'s step
  clamping and `Matrix3.rotation_*` behave correctly for a 180° target, and
  extend `move_queue` tuples / notation parsing to include doubles.
- Define a standard move-notation parser: `U, U', U2, D, D', D2, L, R, F, B,
  ...` → `(axis, index, angle)`, matching this project's fixed color/axis
  scheme (documented in `README.md`'s "Cores das faces" section).

**Exit criteria:** manual keys, `scramble()`, and the solver all route
through the same move-application function; a 180° move animates and
updates logical state correctly; existing headless consistency tests
(from this session) still pass.

---

## Phase 1 — Bottom cross (first layer edges) — ✅ done

- Implemented `solve_layer1_cross` — but not via a hand-derived case table
  as originally sketched here. A generic BFS (`solver/search.py`) proved
  both simpler and more robust: manually enumerating every
  position/orientation/already-placed-edges case is exactly the kind of
  thing that fails silently on a case nobody thought of (see the
  `get_global_colors` bug in the changelog). Each edge's placement is
  found by searching for the shortest move sequence that keeps all
  previously-placed edges fixed while placing the next one.
- **Test:** 1500 randomized headless trials (scramble lengths 1-100) — all
  solved, ~26ms/trial. Live GUI run confirmed the animated path too. See
  `docs/CHANGELOG.md` for full results.

## Phase 2 — First layer corners — ✅ done

- Implemented `solve_layer1_corners` using the same BFS-over-constraints
  technique as Phase 1, generalized: a shared `_constraint()` /
  `_constraints_satisfied()` / `_solve_constraints_incrementally()` now
  back both the cross and the corners, rather than duplicating the
  per-piece search loop. The cross's 4 edges are included as fixed
  constraints from the start of corner-solving.
- Tracking 4 cross edges + up to 4 corners jointly (8 pieces) made the
  original plain BFS from Phase 1 too slow (~30s for one cube). Fixed by
  adding bidirectional BFS to `solver/search.py`: since the goal for every
  constraint here is always "piece at its home position, identity
  orientation" (that's what "correct" means), the goal state is known
  explicitly, so the search can meet in the middle instead of only
  searching forward. This took corner-solving from ~30s to ~0.2s per cube.
- **Test:** 1500 randomized headless trials (scramble lengths 1-100) —
  full first layer (cross + corners) solved 1500/1500, ~84ms/trial. Live
  GUI run confirmed the animated path too. See `docs/CHANGELOG.md`.

## Phase 3 — Second layer edges (F2L) — ✅ done

- Implemented `solve_layer2` with the same constraint-BFS technique as
  Phases 1-2 (no hand-derived left-insert/right-insert case tables
  needed): the 4 middle-layer edges (no top/bottom color) are placed one
  at a time, with the entire first layer (cross + corners) included as
  fixed constraints from the start.
- Tracking up to 12 pieces jointly (8 from the first layer + 4 F2L edges)
  exposed a second performance cliff even with Phase 2's bidirectional
  BFS: ~7-10s per cube, because simulating Matrix3 floating-point
  rotations for that many pieces per search node adds up over the states
  a bidirectional search still has to expand. Fixed by precomputing a
  move-effect lookup table: every orientation reachable by a cube piece is
  one of exactly 24 elements of the cube's rotation group, so each piece
  is represented during search as (position, orientation-id 0-23) and
  applying a move becomes a single dict lookup instead of a matrix
  multiply. Cut it to ~0.5s per cube (plus a smaller general win from
  unrolling `Matrix3.multiply`, used everywhere else in the app too).
- **Test:** 1500 randomized headless trials (scramble lengths 1-100) —
  first two layers fully solved 1500/1500, ~158ms/trial. Live GUI run
  confirmed the animated path too. See `docs/CHANGELOG.md`.

## Phase 4 — Last layer orientation (2-look OLL)

- `solve_layer3_cross`: orient the last layer's edges (dot / L-shape /
  line cases → matching algorithm), repeating with `U` rotations between
  attempts until the top-facing edges all match.
- `solve_layer3_orient_corners`: orient the last layer's corners (repeated
  Sune/Anti-Sune-family algorithm + `U` between corners) until all 4 show
  the top color.
- Scope: beginner 2-look OLL (a handful of cases), not the full 57-case OLL.
- **Test:** whole top face shows one color, first two layers still intact,
  from ~500 random states.

## Phase 5 — Last layer permutation (2-look PLL)

- `solve_layer3_position_corners`: cycle last-layer corners into correct
  position (one corner-cycling algorithm + `U`-search over the 4
  rotations to find/verify the right setup).
- `solve_layer3_position_edges`: cycle last-layer edges into position
  (one edge-cycling algorithm), then final `U` alignment (AUF).
- **Test:** cube fully solved from ~500 random states (this is the full
  pipeline end to end).

## Phase 6 — Orchestration & integration

- Rewrite `CubeSolver.solve()` to run Phases 1–5 against the cube's
  *current* state, independent of `scramble_history`. Drop (or keep only
  as an optional debug fast-path) the history-reversal logic.
- `InputHandler`'s `K` handler no longer needs `scramble_history` to be
  non-empty — remove that implicit precondition; `solve()` should just
  early-return if already solved.
- Add a move-count safety cap (e.g. abort with a clear log message past
  ~500 moves) so a gap in case-detection logic fails loudly instead of
  hanging the solver thread forever.

## Phase 7 — UX polish (optional)

- Beginner LBL solutions are long (~100–150 turns from a 20–25 move
  scramble). Consider a faster `animation_speed` during solve, or a
  toggle to skip animation entirely, plus an on-screen move counter.

## Phase 8 — Testing strategy (throughout, not just at the end)

- Extend the headless test harness already used to validate the
  history-reversal solver: generate states via (a) `scramble()`, (b)
  random *manual* moves not recorded in any history, and (c) mixes of
  both — then assert `is_solved()` after running the new solver. (b) is
  the key new capability this plan adds over the current implementation.
- Run each phase's isolated test (Phases 1–5 above) before wiring
  everything together in Phase 6 — this makes it far easier to localize a
  bad case-detection branch.
- Target ≥1000 random trials per phase before calling it done, matching
  the rigor used to validate the current reversal-based solver.

## Phase 9 — Stretch goal (optional, not required for "solve any state")

- Once beginner LBL is solid, consider an optimal/near-optimal solver
  (Kociemba's two-phase algorithm) as an advanced mode behind a flag.
  This needs coordinate representations and precomputed pruning tables —
  substantially more work than LBL, and out of scope unless specifically
  wanted later.

---

## Key risks

- **Duplicated move logic** (Phase 0) is the most valuable early fix —
  every later phase adds moves programmatically, so any divergence
  between `scramble()`'s inline math and `rotate_face()` becomes a subtle,
  hard-to-localize bug once case-detection algorithms are layered on top.
- **No 180° move support today** — must be added before any LBL algorithm
  can be encoded, since `U2`/`R2`/etc. appear in nearly every trigger.
- **Case-detection correctness is the actual hard part**, not the move
  execution (already proven reliable in the reversal solver). Build and
  test each phase in isolation first.
- Cube-local axes (not camera-relative) are already used correctly by
  `rotate_face` — this must be preserved so algorithms stay valid
  regardless of camera orientation.
