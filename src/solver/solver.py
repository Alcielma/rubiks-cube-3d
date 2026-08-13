"""
Solucionador automático do cubo mágico.

A versão atual desfaz o histórico de todos os embaralhamentos executados
pelo método `Cube.scramble()`. Isso garante que o cubo volte ao estado
resolvido de forma totalmente visual (um movimento por vez, com animação).

O esqueleto para o método de camadas (Layer-by-Layer) também está presente
como métodos placeholder para eventuais implementações futuras.
"""
import time

from cube.colors import WHITE, YELLOW, BLUE, GREEN, RED, ORANGE


class CubeSolver:
    """Coordena a solução automática do Cube via fila de movimentos do Renderer."""

    def __init__(self, cube, renderer):
        self.cube = cube
        self.renderer = renderer
        self.solving = False

    def get_cubie(self, x, y, z):
        """Retorna o cubinho na posição lógica (x,y,z) ou None."""
        for cubie in self.cube.cubies:
            if cubie.logical_position == [x, y, z]:
                return cubie
        return None

    def get_edge_cubie(self, color1, color2):
        """
        Retorna o cubinho de aresta (com exatamente duas cores visíveis) que
        possui ambas as cores fornecidas. Útil para o método de camadas.
        """
        for cubie in self.cube.cubies:
            pos = cubie.logical_position
            zero_count = sum(1 for p in pos if p == 0)
            if zero_count != 1:
                continue

            global_colors = cubie.get_global_colors()
            visible_colors = [c for c in global_colors.values() if c is not None and c != (0, 0, 0)]
            if color1 in visible_colors and color2 in visible_colors:
                return cubie
        return None

    def wait_for_queue(self):
        """Bloqueia até que a fila de movimentos do Renderer seja totalmente consumida."""
        while (len(self.renderer.move_queue) > 0 or self.renderer.current_move is not None) and self.renderer.running:
            time.sleep(0.01)

    # ---------------------------------------------------------------
    # Movimentos básicos (notação WCA). Cada um enfileira o movimento
    # e espera o término da animação antes de seguir.
    # ---------------------------------------------------------------
    def move_L(self):
        self.renderer.move_queue.append(("L", 0, -1, 90))
        self.wait_for_queue()

    def move_L_prime(self):
        self.renderer.move_queue.append(("L'", 0, -1, -90))
        self.wait_for_queue()

    def move_R(self):
        self.renderer.move_queue.append(("R", 0, 1, 90))
        self.wait_for_queue()

    def move_R_prime(self):
        self.renderer.move_queue.append(("R'", 0, 1, -90))
        self.wait_for_queue()

    def move_U(self):
        self.renderer.move_queue.append(("U", 1, 1, 90))
        self.wait_for_queue()

    def move_U_prime(self):
        self.renderer.move_queue.append(("U'", 1, 1, -90))
        self.wait_for_queue()

    def move_D(self):
        self.renderer.move_queue.append(("D", 1, -1, 90))
        self.wait_for_queue()

    def move_D_prime(self):
        self.renderer.move_queue.append(("D'", 1, -1, -90))
        self.wait_for_queue()

    def move_F(self):
        self.renderer.move_queue.append(("F", 2, 1, 90))
        self.wait_for_queue()

    def move_F_prime(self):
        self.renderer.move_queue.append(("F'", 2, 1, -90))
        self.wait_for_queue()

    def move_B(self):
        self.renderer.move_queue.append(("B", 2, -1, 90))
        self.wait_for_queue()

    def move_B_prime(self):
        self.renderer.move_queue.append(("B'", 2, -1, -90))
        self.wait_for_queue()

    # ---------------------------------------------------------------
    # Placeholders do método de camadas (a implementar no futuro)
    # ---------------------------------------------------------------
    def solve_layer1_cross(self):
        print("Etapa 1: Cruz branca - placeholder (não implementado).")

    def solve_layer1_corners(self):
        print("Etapa 2: Cantos da primeira camada - placeholder (não implementado).")

    def solve_layer2(self):
        print("Etapa 3: Segunda camada - placeholder (não implementado).")

    def solve_layer3_cross(self):
        print("Etapa 4: Cruz amarela - placeholder (não implementado).")

    def solve_layer3_orient_corners(self):
        print("Etapa 5: Orientar cantos - placeholder (não implementado).")

    def solve_layer3_position_corners(self):
        print("Etapa 6: Posicionar cantos - placeholder (não implementado).")

    def solve_layer3_position_edges(self):
        print("Etapa 7: Posicionar arestas - placeholder (não implementado).")

    def solve(self):
        """
        Desfaz o histórico de embaralhamento, animando cada movimento na tela.

        Ao final, limpa o histórico para que o próximo `K` só seja executado
        caso novos `S` sejam pressionados.
        """
        if self.solving:
            return
        self.solving = True
        print("Iniciando solução automática do cubo mágico...")

        if not self.cube.scramble_history:
            print("Nenhum embaralhamento registrado para desfazer.")
            self.solving = False
            return

        # Copia para evitar inconsistências caso novos embaralhamentos
        # sejam invocados enquanto a solução roda em outra thread.
        history_to_undo = list(reversed(self.cube.scramble_history))

        for axis, index, angle in history_to_undo:
            undo_angle = -angle
            self.renderer.move_queue.append(("undo", axis, index, undo_angle))
            self.wait_for_queue()

        # Limpa o histórico após a solução
        self.cube.scramble_history = []
        print("Cubo mágico solucionado!")
        self.solving = False
