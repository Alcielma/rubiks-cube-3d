"""
Arquivo com a classe Camera, que gerencia a visualização do cubo mágico
Controla a rotação e o zoom da câmera
"""
from OpenGL.GL import *
from OpenGL.GLU import *


class Camera:
    """
    Classe que representa a câmera do jogo
    Controla a rotação ao redor do cubo e o zoom
    """
    def __init__(self):
        """
        Inicializa a câmera com valores padrão
        """
        self.rotation_x = 0  # Rotação ao redor do eixo X (vertical)
        self.rotation_y = 0  # Rotação ao redor do eixo Y (horizontal)
        self.zoom = 8  # Nível de zoom (distância da câmera ao cubo)

    def apply(self):
        """
        Aplica as transformações da câmera à matriz de modelagem do OpenGL
        Deve ser chamado antes de desenhar o cubo
        """
        glLoadIdentity()  # Reseta a matriz de transformação
        glTranslatef(0, 0, -self.zoom)  # Aplica o zoom (afasta a câmera)
        glRotatef(self.rotation_y, 0, 1, 0)  # Rotaciona ao redor do eixo Y (primeiro)
        glRotatef(self.rotation_x, 1, 0, 0)  # Rotaciona ao redor do eixo X (depois)

    def rotate(self, dx, dy):
        """
        Atualiza a rotação da câmera
        :param dx: Variação da rotação horizontal (eixo Y)
        :param dy: Variação da rotação vertical (eixo X)
        """
        self.rotation_y += dx
        self.rotation_x += dy

    def set_zoom(self, value):
        """
        Define o nível de zoom, limitando-o a valores razoáveis
        :param value: Novo valor de zoom
        """
        self.zoom = max(2, min(20, value))  # Limita o zoom entre 2 e 20
