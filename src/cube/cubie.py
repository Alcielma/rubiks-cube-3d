"""
Módulo com a classe Cubie.
Representa cada peça individual (cubinho) do cubo mágico 3D, com sua
posição lógica, orientação, cores nas faces e renderização via OpenGL.
"""
from OpenGL.GL import *

from cube.colors import BLACK, WHITE, YELLOW, BLUE, GREEN, RED, ORANGE
from graphics.matrix import Matrix3


class Cubie:
    """
    Representa um único cubinho (peça) do cubo mágico.

    Responsabilidades:
    - Guardar cores das 6 faces (stickers)
    - Guardar posição lógica e posição de animação
    - Guardar orientação (rotação permanente) e orientação temporária da animação
    - Desenhar a si mesmo no espaço 3D
    """

    def __init__(self, logical_position, size=0.97):
        """
        Cria um novo cubinho na posição lógica informada.

        :param logical_position: tupla (x, y, z) com valores em {-1, 0, 1}
        :param size: tamanho do cubinho; ligeiramente menor que 1 para deixar folga
        """
        self.logical_position = list(logical_position)
        self.animation_position = list(logical_position)
        self.size = size
        x, y, z = logical_position

        # Todas as 6 faces começam como preta (interna / não visível)
        self.stickers = {
            "front": BLACK,
            "back": BLACK,
            "left": BLACK,
            "right": BLACK,
            "top": BLACK,
            "bottom": BLACK,
        }

        # Apenas as faces externas do cubo recebem cor
        if z == 1:
            self.stickers["front"] = YELLOW
        if z == -1:
            self.stickers["back"] = WHITE
        if x == -1:
            self.stickers["left"] = ORANGE
        if x == 1:
            self.stickers["right"] = RED
        if y == 1:
            self.stickers["top"] = BLUE
        if y == -1:
            self.stickers["bottom"] = GREEN

        self.orientation = Matrix3()
        self.animation_orientation = Matrix3()

        s = size / 2
        self.vertices = [
            [-s, -s, -s],
            [s, -s, -s],
            [s, s, -s],
            [-s, s, -s],
            [-s, -s, s],
            [s, -s, s],
            [s, s, s],
            [-s, s, s],
        ]

        self.edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        ]

        self.faces = [
            ([0, 1, 2, 3], "back"),
            ([4, 5, 6, 7], "front"),
            ([0, 1, 5, 4], "bottom"),
            ([2, 3, 7, 6], "top"),
            ([0, 3, 7, 4], "left"),
            ([1, 2, 6, 5], "right"),
        ]

    def draw(self):
        """Desenha o cubinho no espaço 3D aplicando posição e orientação."""
        glPushMatrix()
        glTranslatef(*self.animation_position)
        glMultMatrixf(self.animation_orientation.multiply(self.orientation).to_opengl())

        glBegin(GL_QUADS)
        for vertex_indices, local_face in self.faces:
            color = self.stickers[local_face]
            glColor3fv(color)
            for vi in vertex_indices:
                glVertex3fv(self.vertices[vi])
        glEnd()

        glPopMatrix()

    def animate_rotate(self, matrix, axis, index):
        """
        Aplica um passo incremental de rotação (para animação).
        Rotaciona em torno da ORIGEM (centro do cubo mágico), não do próprio cubinho.
        """
        pos = self.animation_position
        new_pos = matrix.transform_vector(pos)
        self.animation_position = new_pos
        self.animation_orientation = matrix.multiply(self.animation_orientation)

    def reset_animation(self):
        """Reseta os valores temporários de animação para os valores permanentes."""
        self.animation_position = list(self.logical_position)
        self.animation_orientation = Matrix3()

    def rotate(self, matrix, axis, index):
        """Aplica uma rotação permanente ao cubinho (sem animação)."""
        if self.logical_position[axis] == index:
            new_pos = matrix.transform_vector(self.logical_position)
            self.logical_position = [round(x) for x in new_pos]
            self.orientation = matrix.multiply(self.orientation)

    def get_global_colors(self):
        """
        Retorna as cores que aparecem em cada face GLOBAL do cubo mágico,
        levando em conta a orientação atual do cubinho.
        """
        local_normals = {
            "front": (0, 0, 1),
            "back": (0, 0, -1),
            "left": (-1, 0, 0),
            "right": (1, 0, 0),
            "top": (0, 1, 0),
            "bottom": (0, -1, 0),
        }

        global_colors = {
            "front": None,
            "back": None,
            "left": None,
            "right": None,
            "top": None,
            "bottom": None,
        }

        for local_face, normal in local_normals.items():
            rotated_normal = self.orientation.transform_vector(normal)
            rotated_normal = [round(x) for x in rotated_normal]

            if rotated_normal == (0, 0, 1):
                global_face = "front"
            elif rotated_normal == (0, 0, -1):
                global_face = "back"
            elif rotated_normal == (-1, 0, 0):
                global_face = "left"
            elif rotated_normal == (1, 0, 0):
                global_face = "right"
            elif rotated_normal == (0, 1, 0):
                global_face = "top"
            elif rotated_normal == (0, -1, 0):
                global_face = "bottom"
            else:
                continue

            global_colors[global_face] = self.stickers[local_face]

        return global_colors
