"""
Arquivo com a classe InputHandler, que gerencia a entrada do usuário
Processa cliques do mouse, movimento do mouse, roda do mouse e teclado
"""
import pygame
from pygame.locals import *
import threading


class InputHandler:
    """
    Classe que gerencia a entrada do usuário
    """
    def __init__(self, renderer):
        """
        Inicializa o handler de entrada
        :param renderer: Referência ao objeto Renderer para acessar o botão de ajuda
        """
        self.dragging = False  # Indica se o usuário está arrastando o mouse para rotacionar a câmera
        self.last_mouse_pos = (0, 0)  # Última posição do mouse durante o arraste
        self.renderer = renderer  # Referência ao Renderer para controlar o botão de ajuda

    def handle_event(self, event, camera, cube):
        """
        Processa um evento de entrada do usuário
        :param event: Evento do Pygame a ser processado
        :param camera: Objeto Camera para controlar a visualização
        :param cube: Objeto Cube para controlar o cubo mágico
        """
        if event.type == MOUSEBUTTONDOWN:
            if event.button == 1:  # Botão esquerdo do mouse
                # Verifica se o clique foi no botão de ajuda
                x, y = pygame.mouse.get_pos()
                btn_x = self.renderer.help_button_x
                btn_y = self.renderer.help_button_y
                btn_size = self.renderer.help_button_size
                if btn_x <= x <= btn_x + btn_size and btn_y <= y <= btn_y + btn_size:
                    # Alterna a visibilidade das instruções
                    self.renderer.show_instructions = not self.renderer.show_instructions
                else:
                    # Inicia o arraste para rotacionar a câmera
                    self.dragging = True
                    self.last_mouse_pos = pygame.mouse.get_pos()
        elif event.type == MOUSEBUTTONUP:
             if event.button == 1:  # Botão esquerdo do mouse solto
                 self.dragging = False
        elif event.type == MOUSEMOTION:
            if self.dragging:  # Se estiver arrastando
                x, y = pygame.mouse.get_pos()
                dx = x - self.last_mouse_pos[0]  # Variação horizontal
                dy = y - self.last_mouse_pos[1]  # Variação vertical
                camera.rotate(dx * 0.5, dy * 0.5)  # Aplica a rotação à câmera (fator de 0.5 para suavizar)
                self.last_mouse_pos = (x, y)
        elif event.type == MOUSEWHEEL:
            # Roda do mouse para zoom
            camera.set_zoom(camera.zoom - event.y * 0.5)  # event.y é positivo para cima, negativo para baixo
        elif event.type == KEYDOWN:
            mod = pygame.key.get_mods()  # Verifica se Shift está pressionado
            shift_pressed = mod & KMOD_SHIFT
            # Rotaciona as faces do cubo
            if event.key == K_l:  # Face esquerda
                cube.rotate_face(0, -1, 90 if not shift_pressed else -90)
            if event.key == K_r:  # Face direita
                cube.rotate_face(0, 1, 90 if not shift_pressed else -90)
            if event.key == K_u:  # Face superior
                cube.rotate_face(1, 1, 90 if not shift_pressed else -90)
            if event.key == K_d:  # Face inferior
                cube.rotate_face(1, -1, 90 if not shift_pressed else -90)
            if event.key == K_f:  # Face frontal
                cube.rotate_face(2, 1, 90 if not shift_pressed else -90)
            if event.key == K_b:  # Face traseira
                cube.rotate_face(2, -1, 90 if not shift_pressed else -90)
            if event.key == K_s:  # Tecla S para embaralhar
                cube.scramble()
            if event.key == K_k:  # Tecla K para solucionar automaticamente
                if not self.renderer.solver.solving:
                    solve_thread = threading.Thread(target=self.renderer.solver.solve)
                    solve_thread.daemon = True  # Thread daemon para fechar com o programa
                    solve_thread.start()
