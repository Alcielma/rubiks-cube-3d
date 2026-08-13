"""
Módulo com a classe Camera.
Controla a transformação de visualização 3D:
- Translação ao longo de Z (zoom)
- Rotação em torno do eixo Y (horizontal)
- Rotação em torno do eixo X (vertical)
"""
from OpenGL.GL import *
from OpenGL.GLU import *


class Camera:
    """
    Câmera orbital, sempre olhando para a origem (onde está o cubo).
    """

    def __init__(self):
        self.rotation_x = 0
        self.rotation_y = 0
        self.zoom = 8

    def apply(self):
        """
        Aplica a transformação da câmera à matriz de modelagem do OpenGL.
        Deve ser chamado antes de desenhar o cubo.
        """
        glLoadIdentity()
        glTranslatef(0, 0, -self.zoom)
        glRotatef(self.rotation_y, 0, 1, 0)
        glRotatef(self.rotation_x, 1, 0, 0)

    def rotate(self, dx, dy):
        """Atualiza a rotação da câmera. dx = horizontal, dy = vertical."""
        self.rotation_y += dx
        self.rotation_x += dy

    def set_zoom(self, value):
        """Atualiza o zoom, limitado entre 2 e 20 para evitar câmera muito perto/longe."""
        self.zoom = max(2, min(20, value))
