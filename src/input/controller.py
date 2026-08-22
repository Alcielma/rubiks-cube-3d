"""
Módulo de entrada de usuário (renomeado de input.py para controller.py).
Processa:
- Botão esquerdo do mouse (rotacionar câmera / botão de ajuda)
- Roda do mouse (zoom)
- Teclado (rotacionar faces do cubo, embaralhar, solucionar)
"""
import threading

import pygame
from pygame.locals import *

# Mapeia cada tecla de face para sua letra de notação padrão (ver cube/notation.py).
FACE_KEYS = {
    K_l: "L",
    K_r: "R",
    K_u: "U",
    K_d: "D",
    K_f: "F",
    K_b: "B",
}


class InputHandler:
    """Handler único de eventos de entrada. É alimentado pelo loop principal."""

    def __init__(self, renderer):
        self.dragging = False
        self.last_mouse_pos = (0, 0)
        self.renderer = renderer

    def _point_in_help_button(self, x, y):
        """Retorna True se (x,y) estiver dentro do botão ? (coordenadas de tela)."""
        bx = self.renderer.help_button_x
        by = self.renderer.help_button_y
        bs = self.renderer.help_button_size
        return bx <= x <= bx + bs and by <= y <= by + bs

    def handle_event(self, event, camera, cube):
        """
        Processa um evento do pygame.
        :param event: evento recebido
        :param camera: objeto Camera (rotação e zoom)
        :param cube: objeto Cube (rotação de faces e embaralhamento)
        """
        if event.type == MOUSEBUTTONDOWN:
            if event.button == 1:
                x, y = pygame.mouse.get_pos()
                if self._point_in_help_button(x, y):
                    self.renderer.show_instructions = not self.renderer.show_instructions
                else:
                    self.dragging = True
                    self.last_mouse_pos = pygame.mouse.get_pos()

        elif event.type == MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False

        elif event.type == MOUSEMOTION:
            if self.dragging:
                x, y = pygame.mouse.get_pos()
                dx = x - self.last_mouse_pos[0]
                dy = y - self.last_mouse_pos[1]
                camera.rotate(dx * 0.5, dy * 0.5)
                self.last_mouse_pos = (x, y)

        elif event.type == MOUSEWHEEL:
            camera.set_zoom(camera.zoom - event.y * 0.5)

        elif event.type == KEYDOWN:
            mod = pygame.key.get_mods()
            shift_pressed = mod & KMOD_SHIFT

            if event.key in FACE_KEYS:
                notation = FACE_KEYS[event.key] + ("'" if shift_pressed else "")
                cube.apply_move(notation)
            if event.key == K_s:
                cube.scramble()
            if event.key == K_k:
                if self.renderer.solver and not self.renderer.solver.solving:
                    solve_thread = threading.Thread(target=self.renderer.solver.solve)
                    solve_thread.daemon = True
                    solve_thread.start()
