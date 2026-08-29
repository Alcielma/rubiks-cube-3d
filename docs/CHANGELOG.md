# Changelog

Tracks all changes made as part of the general-purpose solver effort (see
`docs/SOLVER_PLAN.md` for the phased plan this follows). Newest first.

## UX: "Resolvido em MM:SS" message (2026-08-22)

Small Phase 7-style polish item, requested directly rather than planned:
show how long a `K` solve took, on screen, not just in the console.

### Added
- `CubeSolver.solve()` times the actual solving work and, on success, sets
  `Renderer.solve_message` to `"Resolvido em MM:SS"`
  (`CubeSolver._format_elapsed()`). Not set for the already-solved
  no-op case (nothing meaningful to report).
- `Renderer.draw_ui()` renders it as a green banner top-center of the
  window (doesn't overlap the existing "?" help button).
- `InputHandler` clears the message on any subsequent manual move or
  scramble (`R`/`U`/etc. or `S`); `solve()` also clears it at the start of
  each run, so a stale time never lingers once the cube's been touched
  again.

### Verified
- Headless: message set with the right prefix/format after a real solve;
  not set after the already-solved no-op path.
- Live GUI (real `Renderer`/`InputHandler`, genuine posted key events): `S`
  then `K` shows the message; a manual move or a new `S` clears it;
  solving again after a single manual move shows `00:00` correctly
  (genuinely sub-second).
- A screenshot captured from the actual render thread (`glReadPixels`
  only returns real data on the thread that owns the GL context — an
  earlier attempt from the driver/test thread silently produced an
  all-black image) confirms on-screen placement, sizing, and readability.

---

## Phase 6 — Orchestration & integration (2026-08-22)

**Goal:** wire `CubeSolver.solve()` (what the `K` key calls) to actually
run the full Phase 1-5 pipeline against the cube's current state, instead
of the original scramble-history-reversal logic. This is the point of the
whole multi-phase effort: `K` should now solve the cube from *any*
reachable state.

### Added
- `CubeSolver.is_solved()`: checks the entire cube (all 20 movable
  pieces) by combining every phase's own constraint-builders
  (`_cross_edge_constraints` + `_corner_constraints` +
  `_middle_edge_constraints` + `_top_corner_constraints` +
  `_top_edge_constraints`). No new solving logic — this was "free" given
  the constraint infrastructure already built across Phases 1-5. Used for
  `solve()`'s early-exit ("already solved") and final verification.
- `CubeSolver.MOVE_LIMIT` (500) / `SolverMoveLimitExceeded`: `move()`
  counts every move against this limit; `solve()` catches the exception
  and reports a clear warning instead of the solver thread spinning
  forever if some future case ever falls through every phase's existing
  safety nets uncovered by tests.
- Rewrote `solve()`: early-exits if already solved, otherwise runs
  `solve_layer1_cross` → `solve_layer1_corners` → `solve_layer2` →
  `solve_layer3_cross` → `solve_layer3_orient_corners` →
  `solve_layer3_position_corners` → `solve_layer3_position_edges` in
  order, then verifies and reports the final state. Dropped the old
  history-reversal loop entirely.

### Changed / removed
- `solve()` no longer reads `Cube.scramble_history` at all (previously:
  `if not self.cube.scramble_history: return` early, then replay it
  reversed). `scramble()` still populates the list — removing that too
  was out of scope and not worth the churn since nothing reads it now —
  but it's fully inert.
- `InputHandler`'s `K` handler in `controller.py` needed **zero changes**:
  it already just called `solver.solve()` unconditionally (aside from the
  `not solving` guard). The `scramble_history` precondition lived
  entirely inside the old `solve()` body, so replacing that body was
  sufficient — worth noting since the original plan draft expected a
  controller-side change too.

### Verified
- Headless, calling `solve()` (not the individual phase methods) directly:
  an already-solved cube (clean no-op, confirmed via `is_solved()`), 75
  scrambled trials (15 × scramble lengths 1/5/20/50/100), a cube touched
  only by manual moves with `scramble_history` empty throughout, a mixed
  scramble+manual state with history manually cleared mid-session, and
  calling `solve()` twice back to back (idempotent — second call returns
  in ~0.001s). All passed, zero failures.
- Live GUI (real `Renderer`, real `InputHandler`, genuine posted `S`/`R`/
  `U'`/`F`/`K` key events — not calling solver methods directly): `S` then
  `K` solved correctly, and — the capstone check — pressing only manual
  face keys (never `S`) with `scramble_history` confirmed empty, then
  `K`, solved the cube correctly through the real key-handling path. This
  is the literal original limitation reported at the very start of this
  effort ("does `K` solve consistently" → "no, only after `S`"), now
  fixed end to end.
- Discovered while testing this phase (not a code bug, an environment
  one): the actual running app the user launches (`run.sh` in the shared
  checkout at the repo root) is on a different branch/commit than this
  work — all of Phases 0-6 live only on `worktree-solver-plan`, checked
  out in this session's isolated worktree. Set up a second `.venv` and
  `run.sh` inside the worktree itself so the finished solver can actually
  be run and tried, without needing to merge branches first.

---

## Phase 5 — Last layer permutation / 2-look PLL (2026-08-22)

**Goal:** implement `solve_layer3_position_corners` and
`solve_layer3_position_edges` — the last two placeholders. With this, the
cube fully solves end to end (Phases 1-5), verified against genuine
solved-cube ground truth.

### Added
- Generalized Phase 4's OLL-only helpers into constraint-agnostic ones:
  `_make_orientation_progress` → `_make_progress`,
  `_solve_orientation` → `_solve_with_progress`. Permutation (PLL: exact
  target position) and orientation (OLL: flexible target position) turned
  out to be the same *shape* of search problem — "some subset of pieces
  still wrong among the same possibilities, solve them all together" —
  so the exact same progress-search-plus-guaranteed-fallback machinery
  serves both without any PLL-specific search code.
- `_top_corner_constraints()` / `_top_edge_constraints()`: exact
  target-position constraints for the last layer, same shape as Phase
  1-2's `_corner_constraints()`/`_cross_edge_constraints()` (just "top"
  instead of "bottom") — used once orientation is already correct (Phase
  4) and only position is left to fix.
- `_position_last_layer()`: positions all 8 last-layer pieces (corners
  and edges) in one combined `_solve_with_progress()` call.
  `solve_layer3_position_corners()` and `solve_layer3_position_edges()`
  both just call it — kept as two separate public methods to match the
  plan's phase/step naming, but calling either (or both, in either order)
  does the same thing; the second call is a no-op if the first already
  finished.
- `_solve_with_progress()` gained a `fallback_max_depth` parameter
  (default 14, matching Phase 4's OLL usage unchanged); last-layer
  positioning passes 16 (see "Fixed" below for why).

### Fixed
1. **Corners-only positioning was unreliable** (correctness/design, caught
   before merging): the first version positioned corners and edges as two
   separate `_solve_with_progress()` calls — corners first (edges tracked
   as "must stay oriented, position free"), edges second (corners tracked
   as "must stay exactly placed"). This is the literal "2-look PLL" the
   plan described, but permutation has a *joint* parity invariant between
   corners and edges (the whole cube's permutation is always even — you
   can never swap just 2 corners without an accompanying odd change in
   edges, or vice versa), so requiring "corners exactly placed, edges
   anywhere" has no solution more than half the time in this testing —
   confirmed even the guaranteed fallback (depth 14) failing on a
   majority of trials at scramble length 5. It happened to still work
   most of the time end-to-end, because the edges step's own
   `already_placed` freshly rebuilds corner constraints from current
   color state (the true target, not a snapshot) — so an unfinished
   corners step effectively got "retried" folded into the edges step.
   That's an accidental safety net, not a designed guarantee, and it
   still failed outright on 2/15 (scramble 20) and 1/15 (scramble 50)
   trials. Fixed by positioning corners and edges together from the
   start (`_position_last_layer`), which respects the joint parity
   constraint naturally and is arguably more faithful to real PLL anyway
   (most named PLL algorithms move corners and edges in the same
   sequence).
2. **`fallback_max_depth=14` still weren't enough for the combined
   search** in some cases even after fix #1 — real named PLL algorithms
   for some cases (e.g. "H perm", certain double-swaps) run into the
   mid-teens even for humans, and this search additionally has to keep
   both full lower layers correct at the same time. Raised to 16 for
   `_position_last_layer` specifically (left at 14 for OLL, which never
   needed more).
3. **Not a solver bug — a test-script bug that briefly looked like one**:
   an early full-solve verification script set each cubie's
   `original_position` reference *after* calling `scramble()` instead of
   before, so it was comparing the solved cube against a snapshot of the
   *scrambled* state — reporting ~20 of 26 pieces "unsolved" after a
   correct, complete solve. Worth recording because it's an easy mistake
   to repeat: always capture the ground-truth reference immediately after
   `Cube()` construction, before any `scramble()` call.

### Verified
- Headless: full Phase 1-5 pipeline against genuine ground truth (each
  cubie's real creation position/orientation, captured before scrambling)
  — 75 trials (15 × scramble lengths 1/5/20/50/100), zero failures,
  ~10.6s/trial average.
- Re-ran Phase 1 (1500 trials), Phase 2 (1500), Phase 3 (150), and Phase 4
  (100) regressions after the `_make_progress`/`_solve_with_progress`
  rename and the OLL/PLL refactor — all still pass, zero failures,
  confirming the generalization didn't disturb Phase 4's behavior.
- Live GUI (real `Renderer`, real animation queue): 2/2 scrambled cubes
  fully solved end to end (Phases 1-5), ~34-42s each with animation.

---

## Phase 4 — Last layer orientation / 2-look OLL (2026-08-22)

**Goal:** implement `solve_layer3_cross` (orient the 4 top edges) and
`solve_layer3_orient_corners` (orient the 4 top corners) — the whole top
face becomes one color, permutation left for Phase 5.

This phase took much longer than Phases 1-3 and surfaced two real bugs and
one fundamental algorithmic dead-end, documented in full below because the
detours are as informative as the final design.

### Added
- Generalized `CubeSolver._constraint()` to accept a *set* of acceptable
  target positions, not just one — needed because OLL doesn't care which
  of the 4 top slots a piece ends up in, only its orientation.
- `CubeSolver._solve_constraints_together()`: solves a group of
  constraints in one joint search, as opposed to
  `_solve_constraints_incrementally()`'s one-at-a-time approach. Required
  because orientation has a parity invariant (edge-flip sum is always
  even, corner-twist sum is always ≡0 mod 3) — fixing one piece while
  holding everything else *exactly* fixed can be provably impossible even
  when fixing several together is possible.
- `resolve_in_place_orientation()` and `_piece_orbit()` in
  `solver/search.py`: given a piece's current state, find the one
  orientation it would need at some (possibly different) position to
  satisfy an arbitrary predicate, by flood-filling that single piece's
  full 24-state orbit (12 positions × 2 orientations for an edge, 8 × 3
  for a corner) — no hand-derived flip/twist geometry needed. This is
  what lets a *flexible* goal (OLL: any top slot) still reduce to one
  concrete state, so the fast bidirectional search from Phase 2 still
  applies instead of falling back to a slow unidirectional one.
- **Adaptive face-set expansion** (`CubeSolver.FACE_EXPANSION_STAGES`,
  `_moves_for_faces()`, `_constraint_touches_faces()`, rewritten
  `_solve_group()`): tries `{U,R}` first, then `{U,R,F}`, then adding `L`,
  then `B` — restricting both the allowed moves *and* which already-placed
  F2L pieces even need tracking (a piece whose home slot's axis is never
  touched by the active faces provably can't move, so it's dropped from
  the search state entirely). Necessary because by Phase 4 the joint
  piece count reaches ~20 (both full layers + all 4 top edges), and a
  handful of OLL cases only became findable at all once branching and
  piece count were both cut down for the common case.
- `CubeSolver._make_orientation_progress()` +
  `PROGRESS_STAGE_DEPTHS`: for corner orientation specifically, instead of
  one joint search for "all 4 correct", repeatedly searches (shallow,
  cheap) for "at least one more correct than now", applies it, and
  repeats — mirroring how real "2-look OLL" is executed (a short trigger,
  applied repeatedly with `U` adjustments). The trigger the search finds
  on its own for the common case (`{U,R}`, one corner already correct) is
  the classical **Sune** (`R U R' U R U2 R'`) — the search rediscovered a
  famous named algorithm from first principles, which is a nice sanity
  check on the whole approach.
- Guaranteed fallback in `solve_layer3_orient_corners()`: when even the
  shallow "+1" search finds nothing (see "Fixed" below for why that's
  sometimes mathematically expected, not a bug), falls back to
  `_solve_constraints_together()` with a deeper budget (`max_depth=14`)
  for that round only. Bounds the worst case instead of leaving it
  unbounded.

### Fixed
1. **Face-exclusion bug** (correctness): the first version of adaptive
   face-set filtering excluded a piece from tracking whenever its target
   position didn't touch the trial's active faces — but this check was
   also applied to the piece(s) *currently being solved*, not just
   already-placed ones. A piece not yet in place has no fixed "current
   position" to check against its target, so it could be wrongly excluded
   from the whole problem, making the search trivially "succeed" with an
   empty move list while never actually placing that piece. Silent
   corruption: `solve_layer1_cross` (Phase 1!) started leaving edges
   unplaced once face-expansion was added, only caught because the Phase
   1 regression suite was re-run after the change (a reminder to always
   re-run existing regressions after touching shared code, not just the
   new phase's tests). Fixed by splitting `_solve_group()`'s single
   `active` list into `new_constraints` (always included, unconditionally)
   and `already_placed` (the only list eligible for exclusion).
2. **`allowed_moves` silently ignored in the unidirectional search
   path** (performance, not correctness — but severe): `_unidirectional_bfs()`
   always used all 18 moves internally regardless of what `solve_pieces()`
   was asked to restrict to. Corner-orientation "progress" searches that
   were supposed to explore only 6 moves (`{U,R}`) were actually exploring
   all 18, turning a sub-second search into one taking 13-38+ seconds
   (confirmed by explicit timing: identical run times whether `max_depth`
   was 4, 6, or 8 — a dead giveaway the depth parameter wasn't the actual
   bottleneck). Fixed by threading the restricted move list all the way
   into `_unidirectional_bfs()`.
3. **Depth-6 was one move too shallow for the "+1 progress" search's
   cheapest stage** — Sune itself is 7 moves; capping at 6 made even the
   *findable* common case fail and fall through to more expensive stages
   for no reason. Raised the cheapest stage's depth to 9 once the
   `allowed_moves` bug above made that affordable again.
4. **Understood, not "fixed" — a dead end worth recording**: profiling why
   corner orientation sometimes took 30-60+ seconds even after fix #2
   led to discovering that going from "2 corners correctly oriented" to
   "3 correctly oriented" is *impossible*, not just hard: with 2 corners
   already at twist 0, the invariant (total corner twist ≡ 0 mod 3 across
   all 8 corners) forces the other 2's twists to sum to 0 mod 3, which for
   two nonzero values in {1, 2} only happens as 1+2 — meaning fixing
   either one alone would leave the other at a nonzero twist that can't
   satisfy the invariant by itself. The only reachable next milestone from
   "2 correct" is "4 correct" (both remaining corners at once), never "3
   correct". A shallow "find +1" search was, correctly, finding nothing —
   it was asking for something that doesn't exist, at any depth. This is
   *why* the guaranteed fallback (item above) exists — not a performance
   knob, a correctness necessity for this specific transition.
5. **Real solve failures at scramble length ≥20** (correctness): the
   guaranteed-fallback fix above was applied only to
   `solve_layer3_orient_corners` at first. `solve_layer3_cross` (edges)
   still called `_solve_constraints_together()` alone with the default
   `max_depth=10` — but edge-flip parity has the exact same "can't fix
   exactly one" dead end as corner twist (flip sum is always even, so
   "exactly 1 or 3 corrected" can be unreachable), and a first full Phase
   1-4 test run caught it printing "AVISO: não encontrei uma sequência
   para resolver orientação das arestas..." and genuinely leaving the
   cube unsolved for some harder scrambles. Fixed by extracting the whole
   progress-search-with-guaranteed-fallback strategy into one shared
   `_solve_orientation()` used by both `solve_layer3_cross` and
   `solve_layer3_orient_corners`, instead of only the corners method
   having it.

### Verified
- Headless: after fix #5, a full regression pass across all four phases —
  Phase 1 (1500 trials), Phase 2 (1500 trials), Phase 3 (150 trials, all
  reduced-count reruns to confirm no regression from Phase 4's changes to
  shared code) and Phase 4 itself (100 trials: 20 × scramble lengths
  1/5/20/50/100) — all passed with **zero failures**. Phase 4's 100-trial
  run (the one that includes the harder lengths that previously failed
  under fix #5) took 840.8s total, ~8.4s/trial average, dominated by the
  guaranteed-fallback path on the harder cases.
- Live GUI (real `Renderer`, real animation queue): 2/2 scrambled cubes
  had cross + corners + F2L + full OLL correctly solved, ~30-40s each
  (animation time included, plus at least one guaranteed-fallback round).
- Correctness spot-check: after a full Phase 1-4 solve, cross/corners/F2L
  positions and OLL edges/corners orientations all verified directly
  against the cube's real sticker colors (not just re-deriving from the
  same constraint objects used to solve).
- Performance: the common case (most scrambles, most rounds within a
  scramble) resolves in well under a second; the guaranteed-fallback path
  (necessary, not a bug — see item 4) is bounded at ~30s per triggering
  round rather than unbounded, and triggers on a meaningful minority of
  cases (not just extreme ones) — a real cost of prioritizing a fully
  general search-based approach over hand-tuned OLL algorithms, traded
  deliberately for not needing to hand-derive/verify per-case algorithms.

---

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
