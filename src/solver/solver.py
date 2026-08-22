"""
Solucionador automático do cubo mágico.

A versão atual desfaz o histórico de todos os embaralhamentos executados
pelo método `Cube.scramble()`. Isso garante que o cubo volte ao estado
resolvido de forma totalmente visual (um movimento por vez, com animação).

O esqueleto para o método de camadas (Layer-by-Layer) também está presente
como métodos placeholder para eventuais implementações futuras.
"""
import time

from cube.colors import BLACK
from cube.notation import FACE_AXIS_INDEX, FACE_NORMALS, face_for_normal, parse_move
from solver.search import solve_pieces


class CubeSolver:
    """Coordena a solução automática do Cube via fila de movimentos do Renderer."""

    def __init__(self, cube, renderer):
        self.cube = cube
        self.renderer = renderer
        self.solving = False
        # Quando True (padrão), os movimentos são animados via a fila do
        # Renderer. Testes automatizados podem definir como False para
        # aplicar os movimentos instantaneamente, sem precisar de um loop
        # de renderização rodando.
        self.animated = True

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
            visible_colors = [c for c in global_colors.values() if c is not None and c != BLACK]
            if color1 in visible_colors and color2 in visible_colors:
                return cubie
        return None

    def get_corner_cubie(self, color1, color2, color3):
        """
        Retorna o cubinho de canto (as três coordenadas lógicas não-zero) que
        possui as três cores fornecidas visíveis. Útil para o método de camadas.
        """
        target = {color1, color2, color3}
        for cubie in self.cube.cubies:
            pos = cubie.logical_position
            if any(p == 0 for p in pos):
                continue

            global_colors = cubie.get_global_colors()
            visible_colors = {c for c in global_colors.values() if c is not None and c != BLACK}
            if target <= visible_colors:
                return cubie
        return None

    def get_center_color(self, face):
        """
        Retorna a cor fixa de uma face ('front', 'back', 'left', 'right',
        'top' ou 'bottom'), lida a partir do cubinho central correspondente.
        Como os centros nunca mudam de posição, essa é a referência confiável
        de "qual cor pertence a essa face" durante a solução.
        """
        axis, index = FACE_AXIS_INDEX[face]
        for cubie in self.cube.cubies:
            pos = cubie.logical_position
            if pos[axis] == index and all(pos[a] == 0 for a in range(3) if a != axis):
                return cubie.get_global_colors()[face]
        return None

    def wait_for_queue(self):
        """Bloqueia até que a fila de movimentos do Renderer seja totalmente consumida."""
        while (len(self.renderer.move_queue) > 0 or self.renderer.current_move is not None) and self.renderer.running:
            time.sleep(0.01)

    # ---------------------------------------------------------------
    # Movimento básico (notação padrão, ex.: "R", "U'", "F2"). Enfileira o
    # movimento e espera o término da animação antes de seguir. Bloco de
    # construção usado pelos métodos de solução por camadas (Layer-by-Layer).
    # ---------------------------------------------------------------
    def move(self, notation):
        if self.animated:
            axis, index, angle = parse_move(notation)
            self.renderer.move_queue.append((notation, axis, index, angle))
            self.wait_for_queue()
        else:
            self.cube.apply_move_instant(notation)

    def moves(self, notations):
        """Executa uma sequência de movimentos em notação padrão, em ordem."""
        for notation in notations:
            self.move(notation)

    # ---------------------------------------------------------------
    # Método de camadas (Layer-by-Layer). Fase 1 (cruz) implementada;
    # as demais fases (2-7) seguem como placeholders.
    # ---------------------------------------------------------------
    # Ordem das faces laterais ao redor da face inferior. A ordem em si não
    # importa para a corretude (cada aresta é buscada de forma independente
    # e as anteriores entram como restrição no objetivo), mas seguir a volta
    # do cubo evita cruzamentos de busca desnecessários.
    CROSS_SIDE_FACES = ("front", "right", "back", "left")

    def solve_layer1_cross(self):
        """
        Resolve a cruz da primeira camada (a face inferior, cor lida via
        `get_center_color`, já que os centros nunca mudam de posição).

        Para cada uma das 4 arestas da cruz, usa uma busca (BFS, ver
        `solver/search.py`) que trata as arestas JÁ posicionadas como
        restrições do objetivo (devem permanecer no lugar) e busca a
        sequência de movimentos mais curta que também posiciona a próxima
        aresta corretamente. Isso evita ter que derivar manualmente cada
        caso de posição/orientação (fatiamento em camadas do cubo).
        """
        bottom_axis, bottom_index = FACE_AXIS_INDEX["bottom"]
        bottom_color = self.get_center_color("bottom")

        placed = []  # cada item: {"cubie", "target_pos", "local_normal"}

        for side_face in self.CROSS_SIDE_FACES:
            side_color = self.get_center_color(side_face)
            cubie = self.get_edge_cubie(bottom_color, side_color)

            side_axis, side_index = FACE_AXIS_INDEX[side_face]
            target_pos = [0, 0, 0]
            target_pos[bottom_axis] = bottom_index
            target_pos[side_axis] = side_index

            home_face = next(face for face, color in cubie.stickers.items() if color == bottom_color)

            placed.append({
                "cubie": cubie,
                "target_pos": tuple(target_pos),
                "local_normal": FACE_NORMALS[home_face],
            })

            def goal_fn(states, placed=placed):
                for (position, orientation), info in zip(states, placed):
                    if position != info["target_pos"]:
                        return False
                    rotated_normal = orientation.transform_vector(info["local_normal"])
                    if face_for_normal(rotated_normal) != "bottom":
                        return False
                return True

            current_state = [
                (tuple(info["cubie"].logical_position), info["cubie"].orientation)
                for info in placed
            ]

            solution = solve_pieces(current_state, goal_fn)
            if solution is None:
                print(f"AVISO: não encontrei uma sequência para posicionar a aresta da cruz em '{side_face}'.")
                continue

            self.moves(solution)

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
