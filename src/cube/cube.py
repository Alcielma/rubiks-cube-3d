"""
Módulo com a classe Cube, que representa o cubo mágico completo.
Responsável por gerenciar a coleção de cubinhos, as animações de rotação de faces
e a funcionalidade de embaralhamento (com histórico para desfazer depois).
"""
import random

from cube.cubie import Cubie
from graphics.matrix import Matrix3


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

    def rotate_face(self, axis, index, angle):
        """
        Inicia a animação de rotação de uma face do cubo.

        :param axis: Eixo da rotação (0 = x, 1 = y, 2 = z)
        :param index: Qual face do eixo (-1 ou 1)
        :param angle: Ângulo de rotação (normalmente 90 ou -90 graus)
        """
        if self.animating:
            return
        self.animating = True
        self.animation_axis = axis
        self.animation_index = index
        self.animation_target_angle = angle
        self.animation_current_angle = 0

        if axis == 0:
            self.animation_matrix = Matrix3.rotation_x(angle)
        elif axis == 1:
            self.animation_matrix = Matrix3.rotation_y(angle)
        else:
            self.animation_matrix = Matrix3.rotation_z(angle)

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

        if self.animation_axis == 0:
            current_matrix = Matrix3.rotation_x(step)
        elif self.animation_axis == 1:
            current_matrix = Matrix3.rotation_y(step)
        else:
            current_matrix = Matrix3.rotation_z(step)

        for cubie in self.cubies:
            if cubie.logical_position[self.animation_axis] == self.animation_index:
                cubie.animate_rotate(current_matrix, self.animation_axis, self.animation_index)

        if abs(self.animation_current_angle - self.animation_target_angle) < 0.01:
            for cubie in self.cubies:
                if cubie.logical_position[self.animation_axis] == self.animation_index:
                    new_pos = self.animation_matrix.transform_vector(cubie.logical_position)
                    cubie.logical_position = [round(x) for x in new_pos]
                    cubie.orientation = self.animation_matrix.multiply(cubie.orientation)
                    cubie.reset_animation()
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

            if axis == 0:
                matrix = Matrix3.rotation_x(angle)
            elif axis == 1:
                matrix = Matrix3.rotation_y(angle)
            else:
                matrix = Matrix3.rotation_z(angle)

            for cubie in self.cubies:
                if cubie.logical_position[axis] == index:
                    new_pos = matrix.transform_vector(cubie.logical_position)
                    cubie.logical_position = [round(x) for x in new_pos]
                    cubie.orientation = matrix.multiply(cubie.orientation)
                    cubie.reset_animation()
