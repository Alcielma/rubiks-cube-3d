"""
Módulo com a classe Cube, que representa o cubo mágico completo.
Responsável por gerenciar a coleção de cubinhos, as animações de rotação de faces
e a funcionalidade de embaralhamento (com histórico para desfazer depois).
"""
import random

from cube.cubie import Cubie
from cube.notation import parse_move
from graphics.matrix import Matrix3, rotation_matrix_for_axis


class Cube:
    """
    Representa o cubo mágico completo com 27 cubinhos (Cubies).

    Oferece:
    - Rotação de faces com animação suave
    - Embaralhamento aleatório com histórico
    - Desenho de todos os cubinhos na tela
    """

    def __init__(self):
        """Inicializa um novo cubo mágico resolvido com todos os 27 cubinhos."""
        self.cubies = []
        self._create_cubies()

        self.animating = False
        self.animation_axis = None
        self.animation_index = None
        self.animation_target_angle = 0
        self.animation_current_angle = 0
        self.animation_speed = 500
        self.animation_matrix = None

        # Histórico acumulado de todos os embaralhamentos (ainda não desfeitos)
        self.scramble_history = []

    def _create_cubies(self):
        """Cria os 27 cubinhos nas 27 posições lógicas (x,y,z) de -1 a 1."""
        for x in [-1, 0, 1]:
            for y in [-1, 0, 1]:
                for z in [-1, 0, 1]:
                    self.cubies.append(Cubie(logical_position=(x, y, z)))

    def draw(self):
        """Desenha todos os cubinhos do cubo mágico."""
        for cubie in self.cubies:
            cubie.draw()

    @staticmethod
    def _rotation_matrix(axis, angle):
        """Constrói a matriz de rotação para o eixo (0=x, 1=y, 2=z) e ângulo dados."""
        return rotation_matrix_for_axis(axis, angle)

    def _apply_slice_rotation(self, axis, index, matrix):
        """Aplica permanentemente uma matriz de rotação a todos os cubinhos da fatia (axis, index)."""
        for cubie in self.cubies:
            if cubie.logical_position[axis] == index:
                new_pos = matrix.transform_vector(cubie.logical_position)
                cubie.logical_position = [round(x) for x in new_pos]
                cubie.orientation = matrix.multiply(cubie.orientation)
                cubie.reset_animation()

    def rotate_face(self, axis, index, angle):
        """
        Inicia a animação de rotação de uma face do cubo.

        :param axis: Eixo da rotação (0 = x, 1 = y, 2 = z)
        :param index: Qual face do eixo (-1 ou 1)
        :param angle: Ângulo de rotação (90, -90 ou 180 graus)
        """
        if self.animating:
            return
        self.animating = True
        self.animation_axis = axis
        self.animation_index = index
        self.animation_target_angle = angle
        self.animation_current_angle = 0
        self.animation_matrix = self._rotation_matrix(axis, angle)

    def apply_move(self, notation):
        """Inicia a animação de um movimento em notação padrão (ex.: "R", "U'", "F2")."""
        axis, index, angle = parse_move(notation)
        self.rotate_face(axis, index, angle)

    def apply_move_instant(self, notation):
        """Aplica um movimento em notação padrão imediatamente, sem animação."""
        axis, index, angle = parse_move(notation)
        matrix = self._rotation_matrix(axis, angle)
        self._apply_slice_rotation(axis, index, matrix)

    def update(self, dt):
        """
        Avança a animação de rotação de face pelo tempo `dt` (segundos).

        Ao final da animação, aplica a rotação permanente aos cubinhos afetados.
        """
        if not self.animating:
            return

        step = self.animation_speed * dt
        if self.animation_target_angle < 0:
            step = -step

        if abs(self.animation_current_angle + step) >= abs(self.animation_target_angle):
            step = self.animation_target_angle - self.animation_current_angle

        self.animation_current_angle += step

        current_matrix = self._rotation_matrix(self.animation_axis, step)

        for cubie in self.cubies:
            if cubie.logical_position[self.animation_axis] == self.animation_index:
                cubie.animate_rotate(current_matrix, self.animation_axis, self.animation_index)

        if abs(self.animation_current_angle - self.animation_target_angle) < 0.01:
            self._apply_slice_rotation(self.animation_axis, self.animation_index, self.animation_matrix)
            self.animating = False

    def scramble(self, moves=20):
        """
        Embaralha o cubo com `moves` movimentos aleatórios.

        Os movimentos são aplicados SEM animação (para ser rápido) e são
        registrados no `scramble_history` para permitir desfazer depois.
        Se chamar este método várias vezes, os novos movimentos são acrescentados
        ao histórico existente (não sobrescreve).
        """
        if self.animating:
            return

        for _ in range(moves):
            axis = random.randint(0, 2)
            index = random.choice([-1, 1])
            angle = random.choice([90, -90])

            # Registra o movimento para poder desfazer depois
            self.scramble_history.append((axis, index, angle))

            matrix = self._rotation_matrix(axis, angle)
            self._apply_slice_rotation(axis, index, matrix)
