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
from solver.search import solve_pieces, home_state


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
    # Método de camadas (Layer-by-Layer). Fases 1-2 implementadas;
    # as demais fases (3-7) seguem como placeholders.
    # ---------------------------------------------------------------
    # Ordem das faces laterais ao redor da face inferior. A ordem em si não
    # importa para a corretude (cada peça é buscada de forma independente e
    # as anteriores entram como restrição no objetivo), mas seguir a volta
    # do cubo evita cruzamentos de busca desnecessários.
    CROSS_SIDE_FACES = ("front", "right", "back", "left")

    # Pares de faces laterais adjacentes que definem cada um dos 4 cantos da
    # primeira camada, na mesma ordem/sentido de CROSS_SIDE_FACES.
    CORNER_SIDE_FACES = (("front", "right"), ("right", "back"), ("back", "left"), ("left", "front"))

    @staticmethod
    def _constraint(cubie, target_pos, checks):
        """
        Descreve o que significa "essa peça está correta": em qual posição
        lógica ela deve estar, e quais adesivos (por normal local) devem
        apontar para qual face global. Uma aresta precisa de 1 checagem
        (a outra orientação decorre da ortogonalidade); um canto precisa de
        2 (a terceira face fica implícita).
        """
        return {"cubie": cubie, "target_pos": tuple(target_pos), "checks": checks}

    @staticmethod
    def _constraints_satisfied(states, constraints):
        """Verifica se um estado simulado (lista de (posição, orientação)) satisfaz todas as constraints, em ordem."""
        for (position, orientation), info in zip(states, constraints):
            if position != info["target_pos"]:
                return False
            for local_normal, target_face in info["checks"]:
                rotated_normal = orientation.transform_vector(local_normal)
                if face_for_normal(rotated_normal) != target_face:
                    return False
        return True

    def _current_state(self, constraints):
        """Lê a posição/orientação REAL atual de cada peça das constraints."""
        return [
            (tuple(info["cubie"].logical_position), info["cubie"].orientation)
            for info in constraints
        ]

    def _solve_constraints_incrementally(self, constraints, already_placed=(), label="peça"):
        """
        Resolve uma lista de constraints uma de cada vez: para cada nova
        peça, busca (BFS) a sequência de movimentos mais curta que a
        posiciona corretamente SEM desfazer nenhuma peça já resolvida
        (as anteriores desta chamada + `already_placed`, ex.: a cruz já
        pronta ao resolver os cantos).
        """
        active = list(already_placed)
        for i, constraint in enumerate(constraints, start=1):
            active.append(constraint)

            def goal_fn(states, active=active):
                return self._constraints_satisfied(states, active)

            goal_state = home_state([info["target_pos"] for info in active])
            solution = solve_pieces(self._current_state(active), goal_fn, goal_state=goal_state)
            if solution is None:
                print(f"AVISO: não encontrei uma sequência para posicionar {label} #{i}.")
                continue

            self.moves(solution)

    def _cross_edge_constraints(self):
        """Constrói as constraints das 4 arestas da cruz a partir do estado ATUAL do cubo."""
        bottom_axis, bottom_index = FACE_AXIS_INDEX["bottom"]
        bottom_color = self.get_center_color("bottom")

        constraints = []
        for side_face in self.CROSS_SIDE_FACES:
            side_color = self.get_center_color(side_face)
            cubie = self.get_edge_cubie(bottom_color, side_color)

            side_axis, side_index = FACE_AXIS_INDEX[side_face]
            target_pos = [0, 0, 0]
            target_pos[bottom_axis] = bottom_index
            target_pos[side_axis] = side_index

            home_face = next(face for face, color in cubie.stickers.items() if color == bottom_color)

            constraints.append(self._constraint(
                cubie, target_pos, [(FACE_NORMALS[home_face], "bottom")]
            ))
        return constraints

    def _corner_constraints(self):
        """Constrói as constraints dos 4 cantos da primeira camada a partir do estado ATUAL do cubo."""
        bottom_axis, bottom_index = FACE_AXIS_INDEX["bottom"]
        bottom_color = self.get_center_color("bottom")

        constraints = []
        for face_a, face_b in self.CORNER_SIDE_FACES:
            color_a = self.get_center_color(face_a)
            color_b = self.get_center_color(face_b)
            cubie = self.get_corner_cubie(bottom_color, color_a, color_b)

            axis_a, index_a = FACE_AXIS_INDEX[face_a]
            axis_b, index_b = FACE_AXIS_INDEX[face_b]
            target_pos = [0, 0, 0]
            target_pos[bottom_axis] = bottom_index
            target_pos[axis_a] = index_a
            target_pos[axis_b] = index_b

            home_face_bottom = next(face for face, color in cubie.stickers.items() if color == bottom_color)
            home_face_a = next(face for face, color in cubie.stickers.items() if color == color_a)

            constraints.append(self._constraint(
                cubie,
                target_pos,
                [
                    (FACE_NORMALS[home_face_bottom], "bottom"),
                    (FACE_NORMALS[home_face_a], face_a),
                ],
            ))
        return constraints

    def solve_layer1_cross(self):
        """
        Resolve a cruz da primeira camada (a face inferior, cor lida via
        `get_center_color`, já que os centros nunca mudam de posição).

        Para cada uma das 4 arestas, usa uma busca (BFS, ver
        `solver/search.py`) que trata as arestas JÁ posicionadas como
        restrições do objetivo e busca a sequência de movimentos mais curta
        que também posiciona a próxima corretamente. Isso evita ter que
        derivar manualmente cada caso de posição/orientação.
        """
        self._solve_constraints_incrementally(self._cross_edge_constraints(), label="aresta da cruz")

    def solve_layer1_corners(self):
        """
        Resolve os 4 cantos da primeira camada, mantendo a cruz (já
        resolvida) intacta. Mesma técnica de busca incremental da cruz: a
        cruz inteira entra como restrição fixa desde o início, e cada canto
        é buscado sem desfazer nem a cruz nem os cantos já posicionados.
        """
        cross_constraints = self._cross_edge_constraints()
        self._solve_constraints_incrementally(
            self._corner_constraints(), already_placed=cross_constraints, label="canto da primeira camada"
        )

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
