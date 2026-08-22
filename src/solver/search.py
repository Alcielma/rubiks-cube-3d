"""
Busca sobre um pequeno conjunto de peças do cubo.

Motivação: derivar manualmente cada caso de posição/orientação para cada
fase do método de camadas (cruz, cantos, F2L, OLL, PLL) é trabalhoso e fácil
de errar silenciosamente (ver o bug de comparação lista/tupla corrigido em
`Cubie.get_global_colors`). Em vez disso, cada fase descreve apenas o
ESTADO INICIAL das peças relevantes e uma condição de objetivo; esta busca
encontra a sequência de movimentos que satisfaz o objetivo, correta por
construção.

Quando o estado-objetivo é conhecido explicitamente (o caso comum: cada
peça na própria posição de origem com orientação identidade — a definição
de "resolvido" para aquele subconjunto de peças), usa busca bidirecional
(meet-in-the-middle): explora a partir do início E a partir do objetivo
simultaneamente, expandindo sempre a fronteira menor. Isso troca uma busca
O(ramificação^profundidade) por O(2 × ramificação^(profundidade/2)) — para
8 peças rastreadas (cruz + 4 cantos) e profundidade ~10, a diferença é a
diferença entre segundos e minutos.
"""
from collections import deque

from cube.notation import LETTER_TO_FACE, parse_move
from graphics.matrix import Matrix3, rotation_matrix_for_axis

ALL_MOVES = [letter + suffix for letter in LETTER_TO_FACE for suffix in ("", "'", "2")]

_move_matrices_cache = None
_inverse_move_cache = None


def _move_matrices():
    """(notation -> (axis, index, matrix)) para todos os 18 movimentos possíveis, computado uma vez."""
    global _move_matrices_cache
    if _move_matrices_cache is None:
        cache = {}
        for notation in ALL_MOVES:
            axis, index, angle = parse_move(notation)
            cache[notation] = (axis, index, rotation_matrix_for_axis(axis, angle))
        _move_matrices_cache = cache
    return _move_matrices_cache


def _inverse_notation(notation):
    """Notação do movimento inverso: "R" <-> "R'", "R2" é seu próprio inverso."""
    letter, suffix = notation[0], notation[1:]
    if suffix == "":
        return letter + "'"
    elif suffix == "'":
        return letter
    return notation


def _inverse_moves():
    global _inverse_move_cache
    if _inverse_move_cache is None:
        _inverse_move_cache = {n: _inverse_notation(n) for n in _move_matrices()}
    return _inverse_move_cache


def _orientation_key(matrix):
    """Chave hasheável para uma matriz de orientação (arredondada para inteiros)."""
    return tuple(round(v) for row in matrix.data for v in row)


def _state_key(pieces):
    return tuple((position, _orientation_key(orientation)) for position, orientation in pieces)


def _apply_move_to_piece(position, orientation, axis, index, matrix):
    """Simula o efeito de um movimento sobre UMA peça (posição, orientação)."""
    if position[axis] != index:
        return position, orientation
    new_position = tuple(round(x) for x in matrix.transform_vector(position))
    new_orientation = matrix.multiply(orientation)
    return new_position, new_orientation


def _apply_move_to_state(state, axis, index, matrix):
    return tuple(_apply_move_to_piece(p, o, axis, index, matrix) for p, o in state)


def home_state(target_positions):
    """
    Estado-objetivo trivial para um conjunto de peças: cada uma na própria
    posição de origem (`target_positions`) com orientação identidade. Válido
    sempre que `target_positions[i]` for a posição de criação da peça i (o
    caso de todo constraint usado pelas fases do solver: a peça só tem as
    cores certas nas faces certas porque foi criada naquela posição).
    """
    return [(tuple(pos), Matrix3()) for pos in target_positions]


def _bidirectional_bfs(start, goal, max_depth):
    move_matrices = _move_matrices()
    inverse_of = _inverse_moves()

    start_key = _state_key(start)
    goal_key = _state_key(goal)
    if start_key == goal_key:
        return []

    forward_path = {start_key: []}
    forward_state = {start_key: start}
    backward_path = {goal_key: []}  # caminho de `state` até goal
    backward_state = {goal_key: goal}

    frontier_f = [start_key]
    frontier_b = [goal_key]

    for _ in range(max_depth):
        if not frontier_f or not frontier_b:
            break

        if len(frontier_f) <= len(frontier_b):
            new_frontier = []
            for key in frontier_f:
                state = forward_state[key]
                path = forward_path[key]
                for notation, (axis, index, matrix) in move_matrices.items():
                    new_state = _apply_move_to_state(state, axis, index, matrix)
                    new_key = _state_key(new_state)
                    if new_key in forward_path:
                        continue
                    new_path = path + [notation]
                    forward_path[new_key] = new_path
                    forward_state[new_key] = new_state
                    new_frontier.append(new_key)
                    if new_key in backward_path:
                        return new_path + backward_path[new_key]
            frontier_f = new_frontier
        else:
            new_frontier = []
            for key in frontier_b:
                state = backward_state[key]
                path = backward_path[key]
                for notation, (axis, index, matrix) in move_matrices.items():
                    inv_axis, inv_index, inv_matrix = move_matrices[inverse_of[notation]]
                    pred_state = _apply_move_to_state(state, inv_axis, inv_index, inv_matrix)
                    pred_key = _state_key(pred_state)
                    if pred_key in backward_path:
                        continue
                    # aplicar `notation` a pred_state leva de volta a `state`,
                    # de onde `path` já alcança o objetivo.
                    pred_path = [notation] + path
                    backward_path[pred_key] = pred_path
                    backward_state[pred_key] = pred_state
                    new_frontier.append(pred_key)
                    if pred_key in forward_path:
                        return forward_path[pred_key] + pred_path
            frontier_b = new_frontier

    return None


def _unidirectional_bfs(start, goal_fn, max_depth):
    move_matrices = _move_matrices()

    visited = {_state_key(start)}
    queue = deque([(start, [])])

    while queue:
        state, path = queue.popleft()
        if len(path) >= max_depth:
            continue

        for notation, (axis, index, matrix) in move_matrices.items():
            new_state = _apply_move_to_state(state, axis, index, matrix)
            key = _state_key(new_state)
            if key in visited:
                continue

            new_path = path + [notation]
            if goal_fn(list(new_state)):
                return new_path

            visited.add(key)
            queue.append((new_state, new_path))

    return None


def solve_pieces(pieces, goal_fn, goal_state=None, max_depth=10):
    """
    Busca a sequência de movimentos mais curta que leva `pieces` a um estado
    que satisfaça `goal_fn`, simulando apenas essas peças (o restante do
    cubo é ignorado, o que é seguro desde que `goal_fn` inclua todas as
    peças que não podem ser desfeitas).

    :param pieces: lista de (position, orientation) - estado inicial de cada
                   peça relevante, na mesma ordem que `goal_fn` espera.
    :param goal_fn: função (lista de (position, orientation)) -> bool.
                    Usada para o atalho "já resolvido" e, se `goal_state`
                    for informado, para validar o resultado da busca
                    bidirecional (defesa extra dada a complexidade dela).
    :param goal_state: se informado (lista de (position, orientation)), a
                    busca é bidirecional (muito mais rápida) — ver
                    `home_state()` para o caso comum. Se omitido, cai para
                    uma BFS unidirecional guiada só por `goal_fn`.
    :param max_depth: profundidade máxima de busca (limite de segurança)
    :return: lista de notações de movimento (pode ser vazia se já resolvido),
             ou None se nenhuma solução foi encontrada até `max_depth`.
    """
    start = tuple(pieces)
    if goal_fn(list(start)):
        return []

    if goal_state is None:
        return _unidirectional_bfs(start, goal_fn, max_depth)

    solution = _bidirectional_bfs(start, tuple(goal_state), max_depth)
    if solution is not None:
        assert goal_fn(list(_replay(start, solution))), "busca bidirecional produziu uma solução que não satisfaz goal_fn"
    return solution


def _replay(start, notations):
    move_matrices = _move_matrices()
    state = start
    for notation in notations:
        axis, index, matrix = move_matrices[notation]
        state = _apply_move_to_state(state, axis, index, matrix)
    return state
