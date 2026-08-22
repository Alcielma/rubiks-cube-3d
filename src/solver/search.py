"""
Busca sobre um pequeno conjunto de peças do cubo.

Motivação: derivar manualmente cada caso de posição/orientação para cada
fase do método de camadas (cruz, cantos, F2L, OLL, PLL) é trabalhoso e fácil
de errar silenciosamente (ver o bug de comparação lista/tupla corrigido em
`Cubie.get_global_colors`). Em vez disso, cada fase descreve apenas o
ESTADO INICIAL das peças relevantes e uma condição de objetivo; esta busca
encontra a sequência de movimentos que satisfaz o objetivo, correta por
construção.

Duas otimizações tornam isso viável para até ~12 peças rastreadas
simultaneamente (cruz + cantos + arestas da segunda camada):

1. Busca bidirecional (meet-in-the-middle) quando o estado-objetivo é
   conhecido explicitamente (o caso comum: cada peça na própria posição de
   origem com orientação identidade — a definição de "resolvido" para
   aquele subconjunto). Troca uma busca O(ramificação^profundidade) por
   O(2 × ramificação^(profundidade/2)).
2. Tabela de movimentos pré-computada (`_move_effect_table`): como toda
   orientação alcançável é um dos 24 elementos do grupo de rotação do
   cubo, cada peça é representada durante a busca como (posição, id da
   orientação 0-23) em vez de uma matriz 3x3 de floats. Aplicar um
   movimento vira uma busca em dicionário (O(1), inteiros) em vez de uma
   multiplicação de matrizes — decisivo quando a busca explora centenas de
   milhares de estados, cada um com várias peças.
"""
from collections import deque

from cube.notation import LETTER_TO_FACE, parse_move
from graphics.matrix import Matrix3, rotation_matrix_for_axis

ALL_MOVES = [letter + suffix for letter in LETTER_TO_FACE for suffix in ("", "'", "2")]
ALL_POSITIONS = [(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1)]

_move_matrices_cache = None
_inverse_move_cache = None
_orientation_group_cache = None  # (lista de Matrix3, dict chave->id)
_move_effect_table_cache = None  # (notation, position, oid) -> (new_position, new_oid)


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


def _orientation_group():
    """
    Enumera as 24 orientações possíveis (grupo de rotação do cubo) a partir
    da identidade, fechando sob os 3 geradores de 90 graus. Retorna
    (lista de Matrix3 indexada por id, dict chave-arredondada -> id).
    """
    global _orientation_group_cache
    if _orientation_group_cache is not None:
        return _orientation_group_cache

    generators = [rotation_matrix_for_axis(axis, 90) for axis in (0, 1, 2)]

    orientations = [Matrix3()]
    id_by_key = {_orientation_key(orientations[0]): 0}

    frontier = [orientations[0]]
    while frontier:
        new_frontier = []
        for matrix in frontier:
            for generator in generators:
                new_matrix = generator.multiply(matrix)
                key = _orientation_key(new_matrix)
                if key not in id_by_key:
                    id_by_key[key] = len(orientations)
                    orientations.append(new_matrix)
                    new_frontier.append(new_matrix)
        frontier = new_frontier

    _orientation_group_cache = (orientations, id_by_key)
    return _orientation_group_cache


def _oid_for_matrix(matrix):
    """ID (0-23) da orientação mais próxima de `matrix` no grupo de rotação do cubo."""
    _, id_by_key = _orientation_group()
    return id_by_key[_orientation_key(matrix)]


def _move_effect_table():
    """
    (notation, position, oid) -> (new_position, new_oid) para todas as
    combinações de movimento x posição x orientação. Computado uma única
    vez (18 x 27 x 24 = 11.664 combinações, cada uma com uma multiplicação
    de matriz) para que a busca em si não precise de nenhuma aritmética de
    ponto flutuante.
    """
    global _move_effect_table_cache
    if _move_effect_table_cache is not None:
        return _move_effect_table_cache

    orientations, id_by_key = _orientation_group()
    move_matrices = _move_matrices()

    table = {}
    for notation, (axis, index, matrix) in move_matrices.items():
        for position in ALL_POSITIONS:
            affected = position[axis] == index
            new_position = tuple(round(v) for v in matrix.transform_vector(position)) if affected else position
            for oid, orientation_matrix in enumerate(orientations):
                if affected:
                    new_oid = id_by_key[_orientation_key(matrix.multiply(orientation_matrix))]
                else:
                    new_oid = oid
                table[(notation, position, oid)] = (new_position, new_oid)

    _move_effect_table_cache = table
    return table


def _to_fast_state(pieces):
    """Converte peças (posição, Matrix3) para a representação rápida (posição, id de orientação)."""
    return tuple((tuple(position), _oid_for_matrix(orientation)) for position, orientation in pieces)


def _apply_move_to_state_fast(state, notation, table):
    return tuple(table[(notation, position, oid)] for position, oid in state)


def home_state(target_positions):
    """
    Estado-objetivo trivial para um conjunto de peças: cada uma na própria
    posição de origem (`target_positions`) com orientação identidade. Válido
    sempre que `target_positions[i]` for a posição de criação da peça i (o
    caso de todo constraint usado pelas fases do solver: a peça só tem as
    cores certas nas faces certas porque foi criada naquela posição).
    """
    return [(tuple(pos), Matrix3()) for pos in target_positions]


def _bidirectional_bfs(start_fast, goal_fast, max_depth):
    """BFS bidirecional (meet-in-the-middle) sobre a representação rápida (posição, id de orientação)."""
    table = _move_effect_table()
    inverse_of = _inverse_moves()
    notations = ALL_MOVES

    if start_fast == goal_fast:
        return []

    forward_path = {start_fast: []}
    backward_path = {goal_fast: []}  # caminho de `state` até goal

    frontier_f = [start_fast]
    frontier_b = [goal_fast]

    for _ in range(max_depth):
        if not frontier_f or not frontier_b:
            break

        if len(frontier_f) <= len(frontier_b):
            new_frontier = []
            for state in frontier_f:
                path = forward_path[state]
                for notation in notations:
                    new_state = _apply_move_to_state_fast(state, notation, table)
                    if new_state in forward_path:
                        continue
                    new_path = path + [notation]
                    forward_path[new_state] = new_path
                    new_frontier.append(new_state)
                    if new_state in backward_path:
                        return new_path + backward_path[new_state]
            frontier_f = new_frontier
        else:
            new_frontier = []
            for state in frontier_b:
                path = backward_path[state]
                for notation in notations:
                    # pred_state + notation == state, então pred_state = apply(inverse(notation), state)
                    pred_state = _apply_move_to_state_fast(state, inverse_of[notation], table)
                    if pred_state in backward_path:
                        continue
                    pred_path = [notation] + path
                    backward_path[pred_state] = pred_path
                    new_frontier.append(pred_state)
                    if pred_state in forward_path:
                        return forward_path[pred_state] + pred_path
            frontier_b = new_frontier

    return None


def _unidirectional_bfs(start, goal_fn, max_depth):
    """BFS unidirecional usando Matrix3 diretamente (caminho de fallback para objetivos que não são um único estado)."""
    move_matrices = _move_matrices()

    def apply_move_to_piece(position, orientation, axis, index, matrix):
        if position[axis] != index:
            return position, orientation
        new_position = tuple(round(x) for x in matrix.transform_vector(position))
        new_orientation = matrix.multiply(orientation)
        return new_position, new_orientation

    def state_key(state):
        return tuple((position, _orientation_key(orientation)) for position, orientation in state)

    visited = {state_key(start)}
    queue = deque([(start, [])])

    while queue:
        state, path = queue.popleft()
        if len(path) >= max_depth:
            continue

        for notation, (axis, index, matrix) in move_matrices.items():
            new_state = tuple(
                apply_move_to_piece(position, orientation, axis, index, matrix)
                for position, orientation in state
            )
            key = state_key(new_state)
            if key in visited:
                continue

            new_path = path + [notation]
            if goal_fn(list(new_state)):
                return new_path

            visited.add(key)
            queue.append((new_state, new_path))

    return None


def _replay(start, notations):
    move_matrices = _move_matrices()
    state = start
    for notation in notations:
        axis, index, matrix = move_matrices[notation]
        state = tuple(
            (
                tuple(round(x) for x in matrix.transform_vector(position)) if position[axis] == index else position,
                matrix.multiply(orientation) if position[axis] == index else orientation,
            )
            for position, orientation in state
        )
    return state


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
                    busca é bidirecional sobre uma representação compacta
                    (posição, id de orientação 0-23) — muito mais rápida.
                    Ver `home_state()` para o caso comum. Se omitido, cai
                    para uma BFS unidirecional guiada só por `goal_fn`.
    :param max_depth: profundidade máxima de busca (limite de segurança)
    :return: lista de notações de movimento (pode ser vazia se já resolvido),
             ou None se nenhuma solução foi encontrada até `max_depth`.
    """
    start = tuple(pieces)
    if goal_fn(list(start)):
        return []

    if goal_state is None:
        return _unidirectional_bfs(start, goal_fn, max_depth)

    solution = _bidirectional_bfs(_to_fast_state(start), _to_fast_state(goal_state), max_depth)
    if solution is not None:
        assert goal_fn(list(_replay(start, solution))), "busca bidirecional produziu uma solução que não satisfaz goal_fn"
    return solution
