"""
Arquivo com a classe Renderer, que gerencia a janela do jogo e a renderização
Contém o loop principal do jogo e desenha a interface do usuário
"""
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from cube import Cube
from camera import Camera
from input import InputHandler
from solver import CubeSolver


class Renderer:
    """
    Classe que gerencia a janela do jogo e a renderização
    """
    def __init__(self, width=1200, height=800, title="Cubo Mágico 3D"):
        """
        Inicializa o Renderer
        :param width: Largura da janela (padrão: 1200)
        :param height: Altura da janela (padrão: 800)
        :param title: Título da janela (padrão: "Cubo Mágico 3D")
        """
        self.width = width
        self.height = height
        self.title = title
        self.running = False
        self.cube = Cube()  # Objeto do cubo mágico
        self.camera = Camera()  # Objeto da câmera
        self.solver = None  # Objeto do solucionador automático (inicializado depois)
        self.input_handler = InputHandler(self)  # Handler de entrada (recebe referência a este Renderer)
        self.font = None  # Fonte para desenhar texto
        self.show_instructions = False  # Indica se as instruções devem ser exibidas
        self.move_queue = []  # Fila de movimentos a serem executados
        self.current_move = None  # Movimento atual sendo executado (para animação)
        # Configurações do botão de ajuda
        self.help_button_x = 10  # Posição X do botão
        self.help_button_y = 10  # Posição Y do botão
        self.help_button_size = 40  # Tamanho do botão

    def init(self):
        """
        Inicializa o Pygame e o OpenGL
        """
        pygame.init()
        pygame.display.set_mode((self.width, self.height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption(self.title)
        self.font = pygame.font.SysFont('Arial', 24)  # Fonte Arial, tamanho 24
        self.solver = CubeSolver(self.cube, self)  # Inicializa o solucionador

        glEnable(GL_DEPTH_TEST)  # Habilita o teste de profundidade para renderização 3D
        glClearColor(0.5, 0.5, 0.5, 1.0)  # Define a cor de fundo da janela (cinza médio)
        glMatrixMode(GL_PROJECTION)  # Muda para a matriz de projeção
        gluPerspective(45, (self.width / self.height), 0.1, 50.0)  # Define a perspectiva (campo de visão 45 graus)
        glMatrixMode(GL_MODELVIEW)  # Volta para a matriz de modelagem

    def draw_ui(self):
        """
        Desenha a interface do usuário (botão de ajuda e instruções)
        """
        glDisable(GL_DEPTH_TEST)  # Desabilita o teste de profundidade para desenhar UI em 2D
        glEnable(GL_BLEND)  # Habilita blending para transparência
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)  # Define a função de blending
        glMatrixMode(GL_PROJECTION)  # Muda para a matriz de projeção
        glPushMatrix()  # Salva a matriz atual
        glLoadIdentity()  # Reseta a matriz
        gluOrtho2D(0, self.width, self.height, 0)  # Define uma projeção ortográfica 2D (inverte Y para que 0 seja o topo)
        glMatrixMode(GL_MODELVIEW)  # Muda para a matriz de modelagem
        glPushMatrix()  # Salva a matriz atual
        glLoadIdentity()  # Reseta a matriz

        # Desenha o botão de ajuda
        # Primeiro desenha o fundo do botão
        glColor3f(0.2, 0.2, 0.2)  # Cor cinza escuro
        glBegin(GL_QUADS)
        glVertex2f(self.help_button_x, self.help_button_y)
        glVertex2f(self.help_button_x + self.help_button_size, self.help_button_y)
        glVertex2f(self.help_button_x + self.help_button_size, self.help_button_y + self.help_button_size)
        glVertex2f(self.help_button_x, self.help_button_y + self.help_button_size)
        glEnd()

        # Desenha o texto "?" no botão
        help_surface = self.font.render("?", True, (255, 255, 255))
        help_data = pygame.image.tostring(help_surface, "RGBA", True)
        # Centraliza o texto no botão
        text_width = help_surface.get_width()
        text_height = help_surface.get_height()
        glRasterPos2d(
            self.help_button_x + (self.help_button_size - text_width) / 2,
            self.help_button_y + (self.help_button_size - text_height) / 2 + text_height
        )
        glDrawPixels(text_width, text_height, GL_RGBA, GL_UNSIGNED_BYTE, help_data)

        # Desenha as instruções se show_instructions for True
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
                "Scroll: Zoom"
            ]

            # Desenha o fundo da caixa de instruções (mesma cor do botão)
            box_x = self.help_button_x + self.help_button_size + 10
            box_y = self.help_button_y
            box_width = 350
            box_height = len(instructions) * 35 + 30

            glColor3f(0.2, 0.2, 0.2)
            glBegin(GL_QUADS)
            glVertex2f(box_x, box_y)
            glVertex2f(box_x + box_width, box_y)
            glVertex2f(box_x + box_width, box_y + box_height)
            glVertex2f(box_x, box_y + box_height)
            glEnd()

            # Desenha cada linha de instrução centralizada na caixa
            for i, text in enumerate(instructions):
                surface = self.font.render(text, True, (255, 255, 255), (51, 51, 51))  # 51 é 0.2 * 255
                text_data = pygame.image.tostring(surface, "RGBA", True)
                text_width = surface.get_width()
                text_x = box_x + (box_width - text_width) / 2
                glRasterPos2d(text_x, box_y + 30 + i * 35)
                glDrawPixels(surface.get_width(), surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, text_data)

        glPopMatrix()  # Restaura a matriz de modelagem
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()  # Restaura a matriz de projeção
        glMatrixMode(GL_MODELVIEW)
        glDisable(GL_BLEND)  # Desabilita blending
        glEnable(GL_DEPTH_TEST)  # Reabilita o teste de profundidade

    def clear(self):
        """
        Limpa o buffer de cor e o buffer de profundidade
        """
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def swap_buffers(self):
        """
        Troca os buffers de exibição (double buffering)
        """
        pygame.display.flip()

    def run(self):
        """
        Loop principal do jogo
        """
        self.init()
        self.running = True
        clock = pygame.time.Clock()  # Objeto para controlar a taxa de quadros
        last_time = pygame.time.get_ticks()  # Tempo da última atualização

        while self.running:
            current_time = pygame.time.get_ticks()
            dt = (current_time - last_time) / 1000.0  # Tempo decorrido em segundos
            last_time = current_time

            # Processa todos os eventos
            for event in pygame.event.get():
                if event.type == QUIT:  # Clique no botão de fechar a janela
                    self.running = False
                self.input_handler.handle_event(event, self.camera, self.cube)  # Processa o evento

            # Processa a fila de movimentos
            if self.current_move is None:
                if len(self.move_queue) > 0:
                    # Pega o próximo movimento da fila
                    move_name, axis, index, angle = self.move_queue.pop(0)
                    self.current_move = (move_name, axis, index, angle)
                    # Inicia o movimento
                    self.cube.rotate_face(axis, index, angle)
            else:
                # Verifica se a animação do movimento atual terminou
                if not self.cube.animating:
                    self.current_move = None
            
            self.cube.update(dt)  # Atualiza a animação do cubo
            self.clear()  # Limpa a tela
            self.camera.apply()  # Aplica as transformações da câmera
            self.cube.draw()  # Desenha o cubo
            self.draw_ui()  # Desenha a interface do usuário
            self.swap_buffers()  # Atualiza a tela
            clock.tick(60)  # Limita a taxa de quadros a 60 FPS

        pygame.quit()  # Fecha o Pygame quando o loop termina
