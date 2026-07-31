"""
Arquivo com o solucionador automático do cubo mágico
Implementa o método de camadas (Layer-by-Layer)
"""
import time


class CubeSolver:
    """
    Classe que implementa o solucionador automático do cubo mágico
    """
    def __init__(self, cube, renderer):
        """
        Inicializa o solucionador
        :param cube: Objeto da classe Cube (cubo mágico)
        :param renderer: Objeto da classe Renderer (para controlar o loop durante a solução)
        """
        self.cube = cube
        self.renderer = renderer
        self.solving = False  # Indica se o solucionador está executando

    def get_cubie(self, x, y, z):
        """
        Obtém um cubinho por sua posição lógica
        :param x: Posição no eixo X (-1, 0, 1)
        :param y: Posição no eixo Y (-1, 0, 1)
        :param z: Posição no eixo Z (-1, 0, 1)
        :return: Objeto Cubie na posição especificada
        """
        for cubie in self.cube.cubies:
            if cubie.logical_position == [x, y, z]:
                return cubie
        return None
    
    def get_edge_cubie(self, color1, color2):
        """
        Obtém um cubinho de aresta (que tem duas cores visíveis) por suas duas cores
        :param color1: Primeira cor (tupla RGB)
        :param color2: Segunda cor (tupla RGB)
        :return: Cubie object or None
        """
        for cubie in self.cube.cubies:
            # Verifica se é um cubo de aresta (posição com exatamente um zero)
            pos = cubie.logical_position
            zero_count = sum(1 for p in pos if p == 0)
            if zero_count != 1:
                continue
            
            global_colors = cubie.get_global_colors()
            visible_colors = [c for c in global_colors.values() if c is not None and c != (0,0,0)]
            if (color1 in visible_colors and color2 in visible_colors):
                return cubie
        return None

    def wait_for_queue(self):
        """
        Espera até que a fila de movimentos esteja vazia
        """
        while (len(self.renderer.move_queue) > 0 or self.renderer.current_move is not None) and self.renderer.running:
            time.sleep(0.01)

    # Métodos para movimentos básicos (notação WCA: L, R, U, D, F, B, e suas versões invertidas com ')
    def move_L(self):
        """Movimento L (esquerda horário) - adiciona à fila"""
        self.renderer.move_queue.append( ("L", 0, -1, 90) )
        self.wait_for_queue()

    def move_L_prime(self):
        """Movimento L' (esquerda anti-horário) - adiciona à fila"""
        self.renderer.move_queue.append( ("L'", 0, -1, -90) )
        self.wait_for_queue()

    def move_R(self):
        """Movimento R (direita horário) - adiciona à fila"""
        self.renderer.move_queue.append( ("R", 0, 1, 90) )
        self.wait_for_queue()

    def move_R_prime(self):
        """Movimento R' (direita anti-horário) - adiciona à fila"""
        self.renderer.move_queue.append( ("R'", 0, 1, -90) )
        self.wait_for_queue()

    def move_U(self):
        """Movimento U (superior horário) - adiciona à fila"""
        self.renderer.move_queue.append( ("U", 1, 1, 90) )
        self.wait_for_queue()

    def move_U_prime(self):
        """Movimento U' (superior anti-horário) - adiciona à fila"""
        self.renderer.move_queue.append( ("U'", 1, 1, -90) )
        self.wait_for_queue()

    def move_D(self):
        """Movimento D (inferior horário) - adiciona à fila"""
        self.renderer.move_queue.append( ("D", 1, -1, 90) )
        self.wait_for_queue()

    def move_D_prime(self):
        """Movimento D' (inferior anti-horário) - adiciona à fila"""
        self.renderer.move_queue.append( ("D'", 1, -1, -90) )
        self.wait_for_queue()

    def move_F(self):
        """Movimento F (frontal horário) - adiciona à fila"""
        self.renderer.move_queue.append( ("F", 2, 1, 90) )
        self.wait_for_queue()

    def move_F_prime(self):
        """Movimento F' (frontal anti-horário) - adiciona à fila"""
        self.renderer.move_queue.append( ("F'", 2, 1, -90) )
        self.wait_for_queue()

    def move_B(self):
        """Movimento B (traseira horário) - adiciona à fila"""
        self.renderer.move_queue.append( ("B", 2, -1, 90) )
        self.wait_for_queue()

    def move_B_prime(self):
        """Movimento B' (traseira anti-horário) - adiciona à fila"""
        self.renderer.move_queue.append( ("B'", 2, -1, -90) )
        self.wait_for_queue()

    # Métodos para as etapas do método de camadas
    def solve_layer1_cross(self):
        """Etapa 1: Cruz branca (face inferior)"""
        print("Etapa 1: Cruz branca - Não implementado completamente ainda (placeholder)")

    def solve_layer1_corners(self):
        """Etapa 2: Cantos da primeira camada"""
        print("Etapa 2: Cantos da primeira camada - Não implementado completamente ainda (placeholder)")

    def solve_layer2(self):
        """Etapa 3: Segunda camada"""
        print("Etapa 3: Segunda camada - Não implementado completamente ainda (placeholder)")

    def solve_layer3_cross(self):
        """Etapa 4: Cruz amarela (face superior)"""
        print("Etapa 4: Cruz amarela - Não implementado completamente ainda (placeholder)")

    def solve_layer3_orient_corners(self):
        """Etapa 5: Orientar cantos da última camada"""
        print("Etapa 5: Orientar cantos - Não implementado completamente ainda (placeholder)")

    def solve_layer3_position_corners(self):
        """Etapa 6: Posicionar cantos da última camada"""
        print("Etapa 6: Posicionar cantos - Não implementado completamente ainda (placeholder)")

    def solve_layer3_position_edges(self):
        """Etapa 7: Posicionar arestas da última camada"""
        print("Etapa 7: Posicionar arestas - Não implementado completamente ainda (placeholder)")

    def solve(self):
        """
        Desfaz o embaralhamento para solucionar o cubo mágico
        """
        if self.solving:
            return
        self.solving = True
        print("Iniciando solução automática do cubo mágico...")

        if not self.cube.scramble_history:
            print("Nenhum embaralhamento registrado para desfazer.")
            self.solving = False
            return

        # Faz uma cópia do histórico atual para evitar inconsistências durante a solução.
        history_to_undo = list(reversed(self.cube.scramble_history))

        # Desfaz os movimentos de embaralhamento na ordem inversa.
        for axis, index, angle in history_to_undo:
            # Para desfazer um movimento, invertemos o ângulo
            undo_angle = -angle
            # Adiciona o movimento à fila usando os parâmetros diretamente
            self.renderer.move_queue.append( ("undo", axis, index, undo_angle) )
            self.wait_for_queue()

        self.cube.scramble_history = []
        print("Cubo mágico solucionado!")
        self.solving = False
