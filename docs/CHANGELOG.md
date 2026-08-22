# Changelog

Tracks all changes made as part of the general-purpose solver effort (see
`docs/SOLVER_PLAN.md` for the phased plan this follows). Newest first.

## Phase 3 — Second layer edges / F2L (2026-08-22)

**Goal:** implement `solve_layer2`, completing the first two layers
without disturbing the first layer from Phases 1-2.

### Added
- `CubeSolver.ADJACENT_SIDE_FACES`: renamed from `CORNER_SIDE_FACES` — the
  same 4 adjacent-side-face pairs now define both the first-layer corners
  and the second-layer edges, so the old corner-only name stopped fitting.
- `CubeSolver._middle_edge_constraints()`: builds constraints for the 4
  F2L edges (no top/bottom color — they live at index 0 on the bottom
  face's axis, i.e. the middle layer).
- `CubeSolver.solve_layer2()`: real implementation, replacing its
  placeholder. Seeds the incremental solve with the entire first layer
  (cross + corners) already "placed", then places each F2L edge in turn —
  no new machinery needed beyond what Phases 1-2 already built.
- `solver/search.py`: a precomputed move-effect table
  (`_move_effect_table`, `_orientation_group`) representing every piece
  during search as `(position, orientation-id 0-23)` instead of
  `(position, Matrix3)`. The 24 IDs are the cube's full rotation group,
  enumerated once at first use by closing the 3 quarter-turn generators;
  the table maps every `(move, position, orientation-id)` combination
  (18 × 27 × 24 = 11,664 entries) to its result, computed once. Applying a
  move during search is now a dict lookup, not a matrix multiply. The
  public `solve_pieces()`/`home_state()` API is unchanged — pieces still
  go in and come out as `(position, Matrix3)`; the fast representation is
  purely an internal detail of the bidirectional search.

### Fixed (performance, not correctness)
- Tracking up to 12 pieces jointly (8 from the first layer + 4 F2L edges)
  made Phase 2's bidirectional-but-Matrix3-based search take **~7-10
  seconds per cube** for the hardest edge — better than Phase 1's naive
  30s, but still too slow for comfortable use, let alone a large test
  suite. Root cause: even with bidirectional search halving the exponent,
  each expanded state still did up to 12 floating-point 3x3 matrix
  multiplies (`Matrix3.multiply` itself was also using slow nested loops
  with generator expressions — fixed too, unrolled it by hand, a general
  win since it's used everywhere in the app, not just the solver).
  Switching the hot loop to integer `(position, orientation-id)` tuples
  and dict lookups (see "Added" above) cut it to **~0.5s per cube** —
  roughly 15-20x faster than the Matrix3-based bidirectional search, and
  incidentally made Phases 1-2 faster too (cross: 5ms → ~2ms/trial;
  first layer: 84ms → ~8ms/trial).
- The debug assertion added in Phase 2 (replay the bidirectional result
  through the original `goal_fn`) still runs on every solve, using the
  original Matrix3-based replay — it doesn't touch the fast path, so it
  keeps validating the new lookup-table code without being a genuine
  bottleneck itself (runs once per solved piece, not once per search node).

### Verified
- Headless: 1500 random trials (scramble lengths 1/5/20/50/100, 300 each)
  — first two layers (cross + corners + F2L edges) solved 1500/1500,
  ~158ms/trial.
- Re-ran the Phase 1 and Phase 2 regression suites against the new
  move-effect-table search — still 1500/1500 each, and faster than before
  (cross: ~2ms/trial vs. 5ms; first layer: ~8ms/trial vs. 84ms).
- Live GUI (real `Renderer`, real animation queue): 2/2 scrambled cubes
  had their first two layers fully solved, ~14s each with animation.

---

## Phase 2 — First layer corners (2026-08-22)

**Goal:** implement `solve_layer1_corners`, completing the first layer
(cross + corners) without disturbing the cross from Phase 1.

### Added
- `CubeSolver._constraint()` / `_constraints_satisfied()` /
  `_current_state()` / `_solve_constraints_incrementally()`: generalized
  the per-piece "search for a move sequence that places this piece without
  disturbing previously-placed ones" pattern from Phase 1's cross-only
  code into something both `solve_layer1_cross` and the new
  `solve_layer1_corners` call. A constraint now carries a list of
  `(local_normal, target_face)` checks instead of a single one — an edge
  needs 1 (the other orientation follows from orthogonality), a corner
  needs 2 (the third face is then implied).
- `CubeSolver._cross_edge_constraints()` / `_corner_constraints()`: build
  the constraint list for each piece type from the cube's *current* state
  (colors read via `get_center_color`, pieces via `get_edge_cubie` /
  `get_corner_cubie`).
- `CubeSolver.CORNER_SIDE_FACES`: the 4 adjacent side-face pairs that
  define each first-layer corner slot.
- `CubeSolver.solve_layer1_corners()`: real implementation, replacing its
  placeholder. Seeds the incremental solve with all 4 cross constraints
  already "placed" (fixed), then places each corner in turn.
- `solver/search.py`: bidirectional BFS (`_bidirectional_bfs`, `home_state()`,
  `_inverse_notation()`). Necessary, not optional — see "Fixed" below.

### Fixed (performance, not correctness)
- Tracking 8 pieces jointly (4 cross edges + 4 corners) with Phase 1's
  plain forward BFS took **~30 seconds for a single cube** — the state
  space explodes because 8-piece combined states rarely collide, so
  visited-set pruning (which made the 4-edge cross fast) barely helps.
  Fixed by recognizing that every constraint's goal is always "piece at
  its own creation position, identity orientation" — literally the
  definition of solved for that piece — so the exact goal state is known
  upfront (`home_state()`) and the search can run bidirectionally (meet in
  the middle: explore forward from the start AND backward from the goal
  using inverse moves, stopping when the two frontiers intersect). This
  turns a `moves^depth` search into roughly `2 × moves^(depth/2)` and cut
  corner-solving from ~30s to ~0.2s per cube. `solve_pieces()` keeps its
  original unidirectional path as a fallback for any future goal that
  doesn't reduce to a single known state, and a debug assertion replays
  every bidirectional result through the original `goal_fn` to catch a
  wrong result from this trickier code path.

### Verified
- Headless: 1500 random trials (scramble lengths 1/5/20/50/100, 300 each)
  — full first layer (cross + corners) solved 1500/1500, ~84ms/trial.
- Live GUI (real `Renderer`, real animation queue): 2/2 scrambled cubes
  had their first layer fully solved, ~6-7s each with animation.
- Re-ran the Phase 1 cross-only regression suite (1500 trials) against the
  new bidirectional search — still 1500/1500, and incidentally faster too
  (5ms/trial vs. the original 26ms/trial).

---

## Phase 1 — Bottom cross (2026-08-22)

**Goal:** implement the first real solving stage — the bottom-layer cross —
replacing its placeholder in `solver.py`.

### Added
- `src/solver/search.py`: a small generic breadth-first search (BFS) over a
  handful of cube pieces. Each layer-by-layer phase describes only the
  *initial state* of the pieces it cares about and a goal condition;
  `solve_pieces()` finds the shortest move sequence that satisfies it. This
  replaces hand-derived case tables (error-prone — see the Phase 0 bug
  below) with a search that's correct by construction.
- `Cube.notation.FACE_NORMALS` / `NORMAL_TO_FACE` / `face_for_normal()`:
  shared "which global face does this normal vector point at" lookup, used
  by both `Cubie.get_global_colors()` and the new search goal-checking.
- `graphics/matrix.rotation_matrix_for_axis()`: module-level version of the
  axis→rotation-matrix dispatch, so `solver/search.py` can build rotation
  matrices without depending on the `Cube` class.
- `CubeSolver.solve_layer1_cross()`: real implementation. For each of the 4
  cross edges, runs a BFS whose goal keeps all *previously placed* cross
  edges fixed while also placing the next one — this is what correctly
  handles the case where the last edge is hiding in a middle-layer slot
  that touches two side faces already used by earlier edges (a case a
  naive "never touch a used face again" heuristic gets wrong; see
  `docs/SOLVER_PLAN.md`'s "Key risks" section).
- `CubeSolver.animated` flag (default `True`): when set to `False`
  (intended for tests), moves apply instantly via `Cube.apply_move_instant`
  instead of going through the animated `Renderer` queue, so solving logic
  can be tested headlessly without a running render loop.

### Fixed
- `Cubie.get_global_colors()` compared a list against tuples
  (`rotated_normal == (0, 0, 1)` where `rotated_normal` was a `list`), which
  is always `False` in Python — so this method silently returned all-`None`
  colors for every cubie, always. This meant the pre-existing
  `get_edge_cubie()` never actually found anything. Found while wiring up
  the new `get_corner_cubie`/`get_center_color` helpers in Phase 0, fixed
  there; documented here since Phase 1's cross-solver is the first thing
  that actually depends on it working.

### Verified
- Headless: 1500 random trials (scramble lengths 1/5/20/50/100, 300 each)
  — cross solved 1500/1500, ~26ms/trial.
- Live GUI (real `Renderer`, real animation queue): 2/2 scrambled cubes
  solved the cross correctly, ~2s each with animation.
- The "hidden behind two used faces" adversarial case is covered
  statistically by the 1500 randomized trials above (common in scrambles
  of length ≥ 20) rather than a single hand-built example.

---

## Phase 0 — Foundations (2026-08-22)

**Goal:** give the solver a clean, non-graphics API to read/mutate cube
state, and a single source of truth for move execution, before adding any
solving logic on top.

### Added
- `src/cube/notation.py`: single source of truth for face-letter →
  `(axis, index)`, with `parse_move()` supporting `R`, `R'`, and `R2`
  (180° moves — no code path for these existed before this).
- `CubeSolver.get_corner_cubie(color1, color2, color3)` and
  `get_center_color(face)`, alongside the pre-existing `get_edge_cubie()`.
- `CubeSolver.move(notation)` / `moves(notations)`: one generic,
  notation-driven way to enqueue an animated move and wait for it.

### Changed
- Deduplicated the rotation-matrix construction and slice-application math
  that was copy-pasted across `Cube.rotate_face`, `Cube.update`, and
  `Cube.scramble` into `Cube._rotation_matrix()` / `_apply_slice_rotation()`.
- `input/controller.py`: replaced six hand-typed `(axis, index)` key
  handlers (one per face key) with a single `FACE_KEYS` dict + the new
  notation-driven `Cube.apply_move()`.
- `solver.py`: replaced twelve near-identical, unused `move_L` /
  `move_L_prime` / ... helpers with the single generic `move()` above.

### Fixed
- `Cubie.get_global_colors()` list-vs-tuple comparison bug (see Phase 1
  section above for the full explanation — found and fixed in this phase).

### Verified
- Headless: 2000 random trials of the existing scramble-history-reversal
  solve path still land on a solved cube after the refactor (regression).
- Notation math: `R2 == R,R`; a 12-move sequence mixing bases, primes, and
  doubles round-trips back to solved via its literal inverse.
- `get_edge_cubie` / `get_corner_cubie` / `get_center_color` return correct
  results (previously silently broken by the bug above).
- Live GUI: manual moves through the refactored key path, a real animated
  180° move, and 3 repeated scramble→solve (`S`/`K`) cycles all end solved.
