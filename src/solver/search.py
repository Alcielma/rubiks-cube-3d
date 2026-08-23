"""
Busca sobre um pequeno conjunto de peças do cubo.

Motivação: derivar manualmente cada caso de posição/orientação para cada
fase do método de camadas (cruz, cantos, F2L, OLL, PLL) é trabalhoso e fácil
de errar silenciosamente (ver o bug de comparação lista/tupla corrigido em
`Cubie.get_global_colors`). Em vez disso, cada fase descreve apenas o
ESTADO INICIAL das peças relevantes e uma condição de objetivo; esta busca
encontra a sequência de movimentos que satisfaz o objetivo, correta por
construção.

Três otimizações tornam isso viável para até ~20 peças rastreadas
simultaneamente (duas primeiras camadas + última camada inteira):

1. Busca bidirecional (meet-in-the-middle): quando o objetivo é conhecido
   como um único estado concreto, explora a partir do início E do objetivo
   ao mesmo tempo, parando quando as duas frentes se encontram. Troca uma
   busca O(ramificação^profundidade) por O(2 × ramificação^(profundidade/2)).
   `resolve_in_place_orientation()` permite reduzir até objetivos
   "flexíveis" (OLL: qualquer slot da última camada serve) a um único
   estado concreto, então isso vale para toda fase do solver, não só
   cruz/cantos/F2L.
2. Tabela de movimentos pré-computada: toda orientação alcançável é um dos
   24 elementos do grupo de rotação do cubo, então cada peça vira um
   inteiro `código = índice_da_posição * 24 + id_da_orientação` (0-647) em
   vez de uma matriz 3x3 de floats. A tabela `_move_effect_arrays()` é uma
   lista (uma por movimento) de arrays de 648 posições, `novo_código =
   tabela[movimento][código]` — indexação de lista, não hash de dict.
3. Estado = tupla de inteiros simples (códigos de peça), não tupla de
   tuplas (posição, orientação). Hashear/comparar tuplas de int é bem mais
   rápido que tuplas aninhadas, o que importa quando a busca precisa
   armazenar centenas de milhares de estados visitados.
"""
from collections import deque

from cube.notation import LETTER_TO_FACE, parse_move
from graphics.matrix import Matrix3, rotation_matrix_for_axis

ALL_MOVES = [letter + suffix for letter in LETTER_TO_FACE for suffix in ("", "'", "2")]
ALL_POSITIONS = [(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1)]
ORIENTATION_COUNT = 24  # tamanho do grupo de rotação do cubo

POSITION_INDEX = {position: i for i, position in enumerate(ALL_POSITIONS)}
INDEX_POSITION = {i: position for position, i in POSITION_INDEX.items()}

_move_matrices_cache = None
_inverse_move_cache = None
_orientation_group_cache = None  # (lista de Matrix3, dict chave->id)
_move_effect_arrays_cache = None  # lista (por movimento) de arrays: código -> novo código


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


def _piece_code(position, oid):
    return POSITION_INDEX[tuple(position)] * ORIENTATION_COUNT + oid


def _decode_piece(code):
    position_idx, oid = divmod(code, ORIENTATION_COUNT)
    return INDEX_POSITION[position_idx], oid


def _move_effect_arrays():
    """
    Uma lista (uma por movimento, na ordem de `ALL_MOVES`) de arrays de
    27*24 = 648 posições: `arrays[move_idx][code]` é o código da peça
    depois de aplicar aquele movimento. Computado uma única vez (18 x 27 x
    24 = 11.664 combinações, cada uma com uma multiplicação de matriz) para
    que a busca em si seja só indexação de lista com inteiros.
    """
    global _move_effect_arrays_cache
    if _move_effect_arrays_cache is not None:
        return _move_effect_arrays_cache

    orientations, id_by_key = _orientation_group()
    move_matrices = _move_matrices()

    arrays = []
    for notation in ALL_MOVES:
        axis, index, matrix = move_matrices[notation]
        array = [0] * (len(ALL_POSITIONS) * ORIENTATION_COUNT)
        for position in ALL_POSITIONS:
            affected = position[axis] == index
            new_position = tuple(round(v) for v in matrix.transform_vector(position)) if affected else position
            for oid, orientation_matrix in enumerate(orientations):
                new_oid = id_by_key[_orientation_key(matrix.multiply(orientation_matrix))] if affected else oid
                array[_piece_code(position, oid)] = _piece_code(new_position, new_oid)
        arrays.append(array)

    _move_effect_arrays_cache = arrays
    return arrays


def _to_fast_state(pieces):
    """Converte peças (posição, Matrix3) para a representação rápida: tupla de códigos de peça (int)."""
    return tuple(_piece_code(position, _oid_for_matrix(orientation)) for position, orientation in pieces)


def _from_fast_state(state):
    """Converte de volta para (posição, Matrix3), para a fronteira pública da API."""
    orientations, _ = _orientation_group()
    result = []
    for code in state:
        position, oid = _decode_piece(code)
        result.append((position, orientations[oid]))
    return result


MOVE_INDEX = {notation: i for i, notation in enumerate(ALL_MOVES)}


def _apply_move_to_state(state, array):
    return tuple(array[code] for code in state)


def home_state(target_positions):
    """
    Estado-objetivo trivial para um conjunto de peças: cada uma na própria
    posição de origem (`target_positions`) com orientação identidade. Válido
    sempre que `target_positions[i]` for a posição de criação da peça i (o
    caso de todo constraint usado pelas fases do solver: a peça só tem as
    cores certas nas faces certas porque foi criada naquela posição).
    """
    return [(tuple(pos), Matrix3()) for pos in target_positions]


def _piece_orbit(position, oid):
    """
    Todos os códigos de peça fisicamente alcançáveis para UMA peça sozinha
    (o resto do cubo é ignorado), partindo de (position, oid). O grupo de
    movimentos age transitivamente sobre peças do mesmo tipo, então isso dá
    o conjunto completo de estados válidos para esse tipo (24 para aresta:
    12 posições x 2 orientações; 24 para canto: 8 x 3).
    """
    arrays = _move_effect_arrays()
    start = _piece_code(position, oid)
    visited = {start}
    frontier = [start]
    while frontier:
        new_frontier = []
        for code in frontier:
            for array in arrays:
                new_code = array[code]
                if new_code not in visited:
                    visited.add(new_code)
                    new_frontier.append(new_code)
        frontier = new_frontier
    return visited


def resolve_in_place_orientation(current_position, current_orientation, target_position, satisfies):
    """
    Dado que uma peça está em `current_position` com `current_orientation`
    (Matrix3), retorna a Matrix3 que essa MESMA peça teria se estivesse em
    `target_position` (que pode ser igual a `current_position`, ou não —
    qualquer posição do mesmo tipo funciona) satisfazendo o predicado
    `satisfies(matrix) -> bool`.

    A órbita de uma peça sozinha (`_piece_orbit`) precisa começar de um
    estado GENUINAMENTE alcançável para ESSA peça — por isso o começo é
    sempre `(current_position, current_orientation)`, o estado real atual,
    nunca `(target_position, current_orientation)` (essa combinação pode
    nem pertencer ao mesmo componente conectado). A partir daí, a órbita
    inteira (24 estados) já inclui `target_position` com todas as
    orientações fisicamente válidas ali.

    Não precisa de nenhuma geometria derivada à mão (eixos de flip de
    aresta, giro de canto, etc.). Permite reduzir um objetivo "flexível"
    (ex.: OLL: qualquer orientação onde a cor do topo vire pra cima, na
    posição atual) a um único estado concreto, para poder usar a busca
    bidirecional (bem mais rápida) em vez da unidirecional.

    Espera exatamente uma orientação válida em `target_position` que
    satisfaça `satisfies` — verdade para qualquer peça legítima do cubo, já
    que suas cores determinam uma única orientação correta em cada posição
    onde ela pode fisicamente estar.
    """
    orientations, _ = _orientation_group()
    current_oid = _oid_for_matrix(current_orientation)
    orbit = _piece_orbit(current_position, current_oid)

    target_position = tuple(target_position)
    target_position_idx = POSITION_INDEX[target_position]
    matches = [
        code for code in orbit
        if code // ORIENTATION_COUNT == target_position_idx and satisfies(orientations[code % ORIENTATION_COUNT])
    ]
    assert len(matches) == 1, f"esperava exatamente 1 orientação válida em {target_position}, achei {len(matches)}"
    return orientations[matches[0] % ORIENTATION_COUNT]


def _bidirectional_bfs(start_fast, goal_fast, max_depth, notations):
    """BFS bidirecional (meet-in-the-middle) sobre tuplas de códigos de peça (int)."""
    all_arrays = _move_effect_arrays()
    inverse_of = _inverse_moves()
    arrays = [all_arrays[MOVE_INDEX[n]] for n in notations]
    inverse_arrays = [all_arrays[MOVE_INDEX[inverse_of[n]]] for n in notations]

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
                for i, array in enumerate(arrays):
                    new_state = _apply_move_to_state(state, array)
                    if new_state in forward_path:
                        continue
                    new_path = path + [notations[i]]
                    forward_path[new_state] = new_path
                    new_frontier.append(new_state)
                    if new_state in backward_path:
                        return new_path + backward_path[new_state]
            frontier_f = new_frontier
        else:
            new_frontier = []
            for state in frontier_b:
                path = backward_path[state]
                for i, inverse_array in enumerate(inverse_arrays):
                    # pred_state + notation == state, então pred_state = apply(inverse(notation), state)
                    pred_state = _apply_move_to_state(state, inverse_array)
                    if pred_state in backward_path:
                        continue
                    pred_path = [notations[i]] + path
                    backward_path[pred_state] = pred_path
                    new_frontier.append(pred_state)
                    if pred_state in forward_path:
                        return forward_path[pred_state] + pred_path
            frontier_b = new_frontier

    return None


def _unidirectional_bfs(start, goal_fn, max_depth, notations):
    """
    BFS unidirecional — fallback para objetivos que não se reduzem a um
    único estado concreto (ex.: "progresso": pelo menos mais uma peça
    orientada do que agora, usada por `CubeSolver._make_orientation_progress`
    para o OLL dos cantos — várias sequências diferentes satisfazem isso,
    não um único estado-alvo).
    """
    all_arrays = _move_effect_arrays()
    arrays = [all_arrays[MOVE_INDEX[n]] for n in notations]

    start_fast = _to_fast_state(start)

    visited = {start_fast}
    queue = deque([(start_fast, [])])

    while queue:
        state, path = queue.popleft()
        if len(path) >= max_depth:
            continue

        for notation, array in zip(notations, arrays):
            new_state = _apply_move_to_state(state, array)
            if new_state in visited:
                continue

            new_path = path + [notation]
            if goal_fn(_from_fast_state(new_state)):
                return new_path

            visited.add(new_state)
            queue.append((new_state, new_path))

    return None


def _replay(start, notations):
    all_arrays = _move_effect_arrays()
    state = _to_fast_state(start)
    for notation in notations:
        state = _apply_move_to_state(state, all_arrays[MOVE_INDEX[notation]])
    return _from_fast_state(state)


def solve_pieces(pieces, goal_fn, goal_state=None, max_depth=10, allowed_moves=None):
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
                    (códigos de peça inteiros) — muito mais rápida. Ver
                    `home_state()` e `resolve_in_place_orientation()`. Se
                    omitido, cai para uma BFS unidirecional guiada só por
                    `goal_fn`.
    :param max_depth: profundidade máxima de busca (limite de segurança)
    :param allowed_moves: subconjunto de notações a considerar (padrão:
                    todas as 18). Restringir ajuda quando há muitas peças
                    rastreadas — menos ramificação, busca mais rápida — às
                    custas de não encontrar soluções que precisem de uma
                    face fora do subconjunto.
    :return: lista de notações de movimento (pode ser vazia se já resolvido),
             ou None se nenhuma solução foi encontrada até `max_depth`.
    """
    notations = allowed_moves if allowed_moves is not None else ALL_MOVES

    start = tuple(pieces)
    if goal_fn(list(start)):
        return []

    if goal_state is None:
        return _unidirectional_bfs(start, goal_fn, max_depth, notations)

    solution = _bidirectional_bfs(_to_fast_state(start), _to_fast_state(goal_state), max_depth, notations)
    if solution is not None:
        assert goal_fn(_replay(start, solution)), "busca bidirecional produziu uma solução que não satisfaz goal_fn"
    return solution
