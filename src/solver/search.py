"""
Busca em largura (BFS) genérica sobre um pequeno conjunto de peças do cubo.

Motivação: derivar manualmente cada caso de posição/orientação para cada
fase do método de camadas (cruz, cantos, F2L, OLL, PLL) é trabalhoso e fácil
de errar silenciosamente (ver o bug de comparação lista/tupla corrigido em
`Cubie.get_global_colors`). Em vez disso, cada fase descreve apenas o
ESTADO INICIAL das peças relevantes e uma condição de objetivo; esta busca
encontra a sequência de movimentos mais curta que satisfaz o objetivo,
correta por construção.

O espaço de busca é pequeno o suficiente (poucas peças, no máximo algumas
centenas de milhares de estados combinados) para uma BFS simples resolver
em uma fração de segundo.
"""
from collections import deque

from cube.notation import LETTER_TO_FACE, parse_move
from graphics.matrix import rotation_matrix_for_axis

ALL_MOVES = [letter + suffix for letter in LETTER_TO_FACE for suffix in ("", "'", "2")]

_move_matrices_cache = None


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


def solve_pieces(pieces, goal_fn, max_depth=10):
    """
    Busca a sequência de movimentos mais curta que leva `pieces` a um estado
    que satisfaça `goal_fn`, simulando apenas essas peças (o restante do
    cubo é ignorado, o que é seguro desde que `goal_fn` inclua todas as
    peças que não podem ser desfeitas).

    :param pieces: lista de (position, orientation) - estado inicial de cada
                   peça relevante, na mesma ordem que `goal_fn` espera.
    :param goal_fn: função (lista de (position, orientation)) -> bool
    :param max_depth: profundidade máxima de busca (limite de segurança)
    :return: lista de notações de movimento (pode ser vazia se já resolvido),
             ou None se nenhuma solução foi encontrada até `max_depth`.
    """
    move_matrices = _move_matrices()

    start = tuple(pieces)
    if goal_fn(list(start)):
        return []

    visited = {_state_key(start)}
    queue = deque([(start, [])])

    while queue:
        state, path = queue.popleft()
        if len(path) >= max_depth:
            continue

        for notation, (axis, index, matrix) in move_matrices.items():
            new_state = tuple(
                _apply_move_to_piece(position, orientation, axis, index, matrix)
                for position, orientation in state
            )
            key = _state_key(new_state)
            if key in visited:
                continue

            new_path = path + [notation]
            if goal_fn(list(new_state)):
                return new_path

            visited.add(key)
            queue.append((new_state, new_path))

    return None
