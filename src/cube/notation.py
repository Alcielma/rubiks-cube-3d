"""
Notação padrão de movimentos do cubo (U, U', U2, D, ...) mapeada para o
esquema (axis, index) usado por `Cube.rotate_face`.

Esta é a única fonte de verdade para "qual face fica em qual eixo/índice";
tanto o teclado (controller.py) quanto o solver (solver.py) e testes devem
usar `parse_move` em vez de repetir esses números.

axis: 0 = x, 1 = y, 2 = z
index: qual lado do eixo (-1 ou 1)
"""

LETTER_TO_FACE = {
    "L": "left",
    "R": "right",
    "U": "top",
    "D": "bottom",
    "F": "front",
    "B": "back",
}

FACE_AXIS_INDEX = {
    "left": (0, -1),
    "right": (0, 1),
    "top": (1, 1),
    "bottom": (1, -1),
    "front": (2, 1),
    "back": (2, -1),
}

BASE_ANGLE = 90


def parse_move(notation):
    """
    Converte uma notação de movimento ("R", "R'", "R2", ...) em (axis, index, angle).

    - sem sufixo: giro horário de 90 graus
    - sufixo "'": giro anti-horário de 90 graus
    - sufixo "2": giro de 180 graus

    Lança ValueError para notação desconhecida.
    """
    if not notation:
        raise ValueError("Notação de movimento vazia")

    letter, suffix = notation[0], notation[1:]
    if letter not in LETTER_TO_FACE:
        raise ValueError(f"Face desconhecida '{letter}' no movimento '{notation}'")

    axis, index = FACE_AXIS_INDEX[LETTER_TO_FACE[letter]]

    if suffix == "":
        angle = BASE_ANGLE
    elif suffix == "'":
        angle = -BASE_ANGLE
    elif suffix == "2":
        angle = BASE_ANGLE * 2
    else:
        raise ValueError(f"Sufixo desconhecido '{suffix}' no movimento '{notation}'")

    return axis, index, angle
