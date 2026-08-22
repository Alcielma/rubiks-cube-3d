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

# Vetor normal (local OU global, é a mesma convenção) de cada face. Usado por
# Cubie.get_global_colors e pela busca do solver (solver/search.py) para
# descobrir "para onde aponta" um adesivo depois de aplicar uma orientação.
FACE_NORMALS = {
    "front": (0, 0, 1),
    "back": (0, 0, -1),
    "left": (-1, 0, 0),
    "right": (1, 0, 0),
    "top": (0, 1, 0),
    "bottom": (0, -1, 0),
}

NORMAL_TO_FACE = {normal: face for face, normal in FACE_NORMALS.items()}


def face_for_normal(vector):
    """Retorna o nome da face global ('front', 'top', ...) para um vetor normal (arredondado para inteiros)."""
    return NORMAL_TO_FACE.get(tuple(round(v) for v in vector))


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
