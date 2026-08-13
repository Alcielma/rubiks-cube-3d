"""
Módulo com a classe Renderer.
Responsável por toda a renderização OpenGL, loop principal do jogo,
interface 2D do usuário (botão de ajuda, instruções) e fila de movimentos
animados usada pelo solver.
"""
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

from cube.cube import Cube
from graphics.camera import Camera
from input.controller import InputHandler
from solver.solver import CubeSolver


class Renderer:
    """
    Coordena janela, eventos, renderização 3D, interface 2D e loop do jogo.
    """

    def __init__(self, width=1200, height=800, title="Cubo Mágico 3D"):
        self.width = width
        self.height = height
        self.title = title
        self.running = False

        self.cube = Cube()
        self.camera = Camera()
        self.solver = None
        self.input_handler = InputHandler(self)

        self.font = None
        self.show_instructions = False

        # Fila de movimentos a animar; consumida pelo loop principal
        self.move_queue = []
        self.current_move = None

        # Botão ? no canto superior esquerdo
        self.help_button_x = 10
        self.help_button_y = 10
        self.help_button_size = 40

    def init(self):
        """Inicializa pygame, janela OpenGL, fonte e o solver."""
        pygame.init()
        pygame.display.set_mode((self.width, self.height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption(self.title)
        self.font = pygame.font.SysFont("Arial", 24)
        self.solver = CubeSolver(self.cube, self)

        glEnable(GL_DEPTH_TEST)
        glClearColor(0.5, 0.5, 0.5, 1.0)

        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (self.width / self.height), 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)

    def _draw_rect(self, x, y, w, h, color):
        """Helper: desenha um retângulo em coordenadas de tela (tela invertida Y=0 em cima)."""
        glColor3f(*color)
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + w, y)
        glVertex2f(x + w, y + h)
        glVertex2f(x, y + h)
        glEnd()

    def _draw_pygame_text(self, text, x, y, color=(255, 255, 255), bg=(51, 51, 51)):
        """
        Helper: desenha um texto pygame como textura GL via glDrawPixels.
        A posição y indica o topo do texto.
        """
        surface = self.font.render(text, True, color, bg)
        data = pygame.image.tostring(surface, "RGBA", True)
        text_w = surface.get_width()
        text_h = surface.get_height()
        # glRasterPos recebe o canto inferior esquerdo, por isso somamos text_h em Y
        glRasterPos2d(x, y + text_h)
        glDrawPixels(text_w, text_h, GL_RGBA, GL_UNSIGNED_BYTE, data)

    def draw_ui(self):
        """
        Desenha a interface 2D do usuário sobre a cena 3D.
        Usa projeção ortográfica para trabalhar em pixels.
        """
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, self.width, self.height, 0)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # Fundo do botão "?"
        self._draw_rect(
            self.help_button_x,
            self.help_button_y,
            self.help_button_size,
            self.help_button_size,
            color=(0.2, 0.2, 0.2),
        )

        # Texto "?" centralizado no botão
        help_surface = self.font.render("?", True, (255, 255, 255))
        help_w = help_surface.get_width()
        help_h = help_surface.get_height()
        self._draw_pygame_text(
            "?",
            x=self.help_button_x + (self.help_button_size - help_w) / 2,
            y=self.help_button_y + (self.help_button_size - help_h) / 2,
            color=(255, 255, 255),
            bg=(51, 51, 51),
        )

        if self.show_instructions:
            instructions = [
                "L/R: Girar Laterais",
                "U/D: Girar Topo/Base",
                "F/B: Girar Frente/Trás",
                "Shift + Tecla: Girar anti-horário",
                "amarelo => F",
                "verde => D",
                "laranja => L",
                "verelho => R",
                "azul => U",
                "S: Embaralhar",
                "K: Solucionar automaticamente",
                "Mouse: Rotacionar Camera",
                "Scroll: Zoom",
            ]

            box_x = self.help_button_x + self.help_button_size + 10
            box_y = self.help_button_y
            box_width = 350
            box_height = len(instructions) * 35 + 30

            self._draw_rect(box_x, box_y, box_width, box_height, color=(0.2, 0.2, 0.2))

            for i, text in enumerate(instructions):
                surface = self.font.render(text, True, (255, 255, 255), (51, 51, 51))
                text_x = box_x + (box_width - surface.get_width()) / 2
                self._draw_pygame_text(text, x=text_x, y=box_y + 30 + i * 35)

        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)

    def clear(self):
        """Limpa os buffers de cor e profundidade."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def swap_buffers(self):
        """Troca os buffers (double buffering) para exibir o quadro desenhado."""
        pygame.display.flip()

    def run(self):
        """Loop principal do jogo: eventos, atualização, desenho."""
        self.init()
        self.running = True
        clock = pygame.time.Clock()
        last_time = pygame.time.get_ticks()

        while self.running:
            current_time = pygame.time.get_ticks()
            dt = (current_time - last_time) / 1000.0
            last_time = current_time

            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
                self.input_handler.handle_event(event, self.camera, self.cube)

            # Consome a fila de movimentos animados
            if self.current_move is None:
                if self.move_queue:
                    move_name, axis, index, angle = self.move_queue.pop(0)
                    self.current_move = (move_name, axis, index, angle)
                    self.cube.rotate_face(axis, index, angle)
            else:
                if not self.cube.animating:
                    self.current_move = None

            self.cube.update(dt)
            self.clear()
            self.camera.apply()
            self.cube.draw()
            self.draw_ui()
            self.swap_buffers()
            clock.tick(60)

        pygame.quit()
