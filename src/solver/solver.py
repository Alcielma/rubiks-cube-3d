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
from cube.notation import FACE_AXIS_INDEX, FACE_NORMALS, LETTER_TO_FACE, face_for_normal, parse_move
from solver.search import solve_pieces, resolve_in_place_orientation


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
    # Método de camadas (Layer-by-Layer). Fases 1-4 implementadas;
    # as demais fases (5-7) seguem como placeholders.
    # ---------------------------------------------------------------
    # Ordem das faces laterais ao redor da face inferior. A ordem em si não
    # importa para a corretude (cada peça é buscada de forma independente e
    # as anteriores entram como restrição no objetivo), mas seguir a volta
    # do cubo evita cruzamentos de busca desnecessários.
    CROSS_SIDE_FACES = ("front", "right", "back", "left")

    # Pares de faces laterais adjacentes ao redor do cubo, na mesma ordem/
    # sentido de CROSS_SIDE_FACES. Define tanto os 4 cantos da primeira
    # camada (junto com "bottom") quanto as 4 arestas da segunda camada
    # (F2L, sem cor de topo/base).
    ADJACENT_SIDE_FACES = (("front", "right"), ("right", "back"), ("back", "left"), ("left", "front"))

    @staticmethod
    def _constraint(cubie, target_positions, checks):
        """
        Descreve o que significa "essa peça está correta": em qual(is)
        posição(ões) lógica(s) ela pode estar, e quais adesivos (por normal
        local) devem apontar para qual face global.

        `target_positions` normalmente é uma única posição (ex.: a cruz e
        os cantos da primeira camada têm exatamente um slot correto). Para
        o OLL (Fase 4), onde a permutação ainda não importa — só a
        orientação —, pode ser um conjunto de posições aceitáveis (ex.:
        "qualquer um dos 4 slots da última camada").

        Uma aresta precisa de 1 checagem (a outra orientação decorre da
        ortogonalidade); um canto precisa de 2 quando a posição é exata
        (a terceira face fica implícita), ou de apenas 1 quando a posição
        é flexível (OLL: só "a cor do topo vira para cima" importa).
        """
        if isinstance(target_positions[0], int):
            target_positions = (target_positions,)
        return {
            "cubie": cubie,
            "target_positions": frozenset(tuple(pos) for pos in target_positions),
            "checks": checks,
        }

    @staticmethod
    def _constraint_satisfied(state, info):
        """Verifica UMA constraint contra o estado (posição, orientação) de UMA peça."""
        position, orientation = state
        if position not in info["target_positions"]:
            return False
        for local_normal, target_face in info["checks"]:
            rotated_normal = orientation.transform_vector(local_normal)
            if face_for_normal(rotated_normal) != target_face:
                return False
        return True

    @classmethod
    def _constraints_satisfied(cls, states, constraints):
        """Verifica se um estado simulado (lista de (posição, orientação)) satisfaz todas as constraints, em ordem."""
        return all(cls._constraint_satisfied(state, info) for state, info in zip(states, constraints))

    @classmethod
    def _count_satisfied(cls, states, constraints):
        """Quantas constraints, das fornecidas, o estado simulado satisfaz."""
        return sum(1 for state, info in zip(states, constraints) if cls._constraint_satisfied(state, info))

    def _current_state(self, constraints):
        """Lê a posição/orientação REAL atual de cada peça das constraints."""
        return [
            (tuple(info["cubie"].logical_position), info["cubie"].orientation)
            for info in constraints
        ]

    def _resolve_goal_state(self, active):
        """
        Reduz cada constraint em `active` a um (posição, Matrix3) concreto:
        se a posição-alvo é única (cruz/cantos/F2L), usa-a; se é flexível
        (OLL: qualquer slot da última camada serve), usa a posição ATUAL da
        peça — qualquer uma das opções funciona, pois um giro de U preserva
        "a cor do topo vira pra cima" para todas as peças da última camada
        simultaneamente. A orientação correta nessa posição vem de
        `resolve_in_place_orientation` (busca de órbita de uma peça só, sem
        geometria derivada à mão), o que permite usar busca bidirecional
        (bem mais rápida) mesmo para objetivos flexíveis.
        """
        goal = []
        for info in active:
            cubie = info["cubie"]
            target_positions = info["target_positions"]
            target_pos = next(iter(target_positions)) if len(target_positions) == 1 else tuple(cubie.logical_position)

            def satisfies(matrix, checks=info["checks"]):
                for local_normal, target_face in checks:
                    if face_for_normal(matrix.transform_vector(local_normal)) != target_face:
                        return False
                return True

            target_orientation = resolve_in_place_orientation(
                tuple(cubie.logical_position), cubie.orientation, target_pos, satisfies
            )
            goal.append((target_pos, target_orientation))
        return goal

    # Conjuntos de faces tentados em ordem crescente ao resolver um grupo
    # (ver `_solve_group`). "top" está sempre disponível (nunca desfaz uma
    # peça já colocada, já que arestas/cantos resolvidos ficam nas camadas
    # de baixo) e nunca incluímos "bottom" (nenhuma fase depois da Fase 2
    # precisa mexer nela, e mexer significaria desfazer a cruz/os cantos).
    # Um algoritmo real de OLL/PLL tipicamente usa só 1-2 faces laterais
    # (dado o alinhamento certo via U, que a própria busca já explora) —
    # começar pequeno é o que torna essas fases tratáveis: menos peças de
    # F2L ficam "no caminho" de um giro (só arriscam ser mexidas peças que
    # tocam uma face ativa), e a busca ramifica bem menos.
    FACE_EXPANSION_STAGES = (
        {"top", "right"},
        {"top", "right", "front"},
        {"top", "right", "front", "left"},
        {"top", "right", "front", "left", "back"},
    )

    @staticmethod
    def _moves_for_faces(faces):
        """Todas as notações de movimento (com sufixos) cuja face pertence a `faces`."""
        return [
            letter + suffix
            for letter, face in LETTER_TO_FACE.items()
            if face in faces
            for suffix in ("", "'", "2")
        ]

    @staticmethod
    def _constraint_touches_faces(info, axes_indices):
        """
        True se a peça da constraint PODE ser afetada por alguma face ativa.
        Só é seguro dizer "não" quando a posição-alvo é única (F2L: a peça
        já está lá, resolvida) e NENHUM dos eixos/índices que ela ocupa
        corresponde a uma face ativa — nesse caso, nenhum movimento no
        conjunto restrito jamais a toca, então ela nem precisa ser
        rastreada. Para posição flexível (OLL) sempre mantemos.

        Só chamado para peças de `already_placed` em `_solve_group` — as
        peças que a busca está tentando corrigir AGORA nunca passam por
        aqui, sempre entram incondicionalmente (ver `_solve_group`):
        excluí-las faria a busca "resolver" um problema vazio sem realmente
        posicioná-las.
        """
        target_positions = info["target_positions"]
        if len(target_positions) != 1:
            return True
        position = next(iter(target_positions))
        return any(position[axis] == index for axis, index in axes_indices)

    def _solve_group(self, new_constraints, already_placed, label, max_depth=10):
        """
        Busca (BFS bidirecional) a sequência de movimentos mais curta que
        posiciona `new_constraints` corretamente sem desfazer nenhuma peça
        de `already_placed`, e a executa.

        Tenta conjuntos de faces cada vez maiores (`FACE_EXPANSION_STAGES`)
        até uma busca encontrar solução, descartando da busca (com
        segurança, ver `_constraint_touches_faces`) as peças de
        `already_placed` que o conjunto de faces daquela tentativa nunca
        poderia tocar — `new_constraints` SEMPRE entra por completo,
        incondicionalmente, já que são justamente as peças sendo
        posicionadas agora (podem estar em qualquer lugar ainda). Isso é o
        que torna o OLL (Fase 4, até 20 peças no total) tratável: a
        tentativa inicial (2 faces) rastreia bem menos peças de
        `already_placed` e ramifica bem menos que usar as 18 notações e
        todas as peças de uma vez, e cobre a enorme maioria dos casos reais
        (a busca já pode girar U livremente para "alinhar" o caso com as
        faces disponíveis). O último estágio (todas as faces laterais) é
        sempre correto — é o mesmo espaço de busca completo usado pelas
        fases anteriores — só mais lento.
        """
        for stage_faces in self.FACE_EXPANSION_STAGES:
            axes_indices = {FACE_AXIS_INDEX[face] for face in stage_faces if face != "top"}
            kept_placed = [info for info in already_placed if self._constraint_touches_faces(info, axes_indices)]
            restricted = kept_placed + list(new_constraints)

            def goal_fn(states, restricted=restricted):
                return self._constraints_satisfied(states, restricted)

            goal_state = self._resolve_goal_state(restricted)
            allowed_moves = self._moves_for_faces(stage_faces)
            solution = solve_pieces(
                self._current_state(restricted), goal_fn, goal_state=goal_state,
                allowed_moves=allowed_moves, max_depth=max_depth,
            )
            if solution is not None:
                self.moves(solution)
                return True

        print(f"AVISO: não encontrei uma sequência para resolver {label}.")
        return False

    def _solve_constraints_incrementally(self, constraints, already_placed=(), label="peça"):
        """
        Resolve uma lista de constraints uma de cada vez: para cada nova
        peça, busca a sequência de movimentos mais curta que a posiciona
        corretamente SEM desfazer nenhuma peça já resolvida (as anteriores
        desta chamada + `already_placed`, ex.: a cruz já pronta ao resolver
        os cantos). Adequado quando cada peça pode ser corrigida
        isoladamente — não serve para orientação (OLL), onde corrigir uma
        peça sozinha pode ser impossível por paridade; ver
        `_solve_constraints_together`.
        """
        placed = list(already_placed)
        for i, constraint in enumerate(constraints, start=1):
            self._solve_group([constraint], already_placed=placed, label=f"{label} #{i}")
            placed.append(constraint)

    def _solve_constraints_together(self, constraints, already_placed=(), label="grupo", max_depth=10):
        """
        Resolve um grupo de constraints de uma só vez (uma única busca
        conjunta), em vez de uma peça por vez. Necessário para o OLL:
        arestas/cantos da última camada têm paridade de orientação
        conjunta (soma de flips par, soma de giros múltipla de 3) — corrigir
        uma peça isoladamente, mantendo as outras EXATAMENTE como estão,
        pode violar essa paridade e não ter solução, mesmo quando corrigir
        todas juntas é perfeitamente possível.
        """
        return self._solve_group(list(constraints), already_placed=already_placed, label=label, max_depth=max_depth)

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
        for face_a, face_b in self.ADJACENT_SIDE_FACES:
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

    def _middle_edge_constraints(self):
        """
        Constrói as constraints das 4 arestas da segunda camada (F2L) a
        partir do estado ATUAL do cubo. Diferente da cruz e dos cantos,
        essas arestas não têm cor de topo nem de base — ficam na camada do
        meio (índice 0 no eixo da face inferior, que é o padrão em `target_pos`).
        """
        constraints = []
        for face_a, face_b in self.ADJACENT_SIDE_FACES:
            color_a = self.get_center_color(face_a)
            color_b = self.get_center_color(face_b)
            cubie = self.get_edge_cubie(color_a, color_b)

            axis_a, index_a = FACE_AXIS_INDEX[face_a]
            axis_b, index_b = FACE_AXIS_INDEX[face_b]
            target_pos = [0, 0, 0]
            target_pos[axis_a] = index_a
            target_pos[axis_b] = index_b
            # bottom_axis permanece 0: é exatamente a camada do meio.

            home_face_a = next(face for face, color in cubie.stickers.items() if color == color_a)

            constraints.append(self._constraint(
                cubie, target_pos, [(FACE_NORMALS[home_face_a], face_a)]
            ))
        return constraints

    def _top_edge_positions(self):
        """As 4 posições lógicas dos slots de aresta da última camada (topo)."""
        top_axis, top_index = FACE_AXIS_INDEX["top"]
        positions = []
        for side_face in self.CROSS_SIDE_FACES:
            side_axis, side_index = FACE_AXIS_INDEX[side_face]
            pos = [0, 0, 0]
            pos[top_axis] = top_index
            pos[side_axis] = side_index
            positions.append(tuple(pos))
        return positions

    def _top_corner_positions(self):
        """As 4 posições lógicas dos slots de canto da última camada (topo)."""
        top_axis, top_index = FACE_AXIS_INDEX["top"]
        positions = []
        for face_a, face_b in self.ADJACENT_SIDE_FACES:
            axis_a, index_a = FACE_AXIS_INDEX[face_a]
            axis_b, index_b = FACE_AXIS_INDEX[face_b]
            pos = [0, 0, 0]
            pos[top_axis] = top_index
            pos[axis_a] = index_a
            pos[axis_b] = index_b
            positions.append(tuple(pos))
        return positions

    def _last_layer_edges(self):
        """As 4 peças de aresta que têm a cor do topo (identificadas pela cor, não pela posição atual)."""
        top_color = self.get_center_color("top")
        return [
            self.get_edge_cubie(top_color, self.get_center_color(side_face))
            for side_face in self.CROSS_SIDE_FACES
        ]

    def _last_layer_corners(self):
        """Os 4 cantos que têm a cor do topo (identificados pela cor, não pela posição atual)."""
        top_color = self.get_center_color("top")
        return [
            self.get_corner_cubie(top_color, self.get_center_color(face_a), self.get_center_color(face_b))
            for face_a, face_b in self.ADJACENT_SIDE_FACES
        ]

    def _oll_orientation_constraint(self, cubie, valid_positions):
        """
        Constraint de orientação para o OLL: a peça pode estar em QUALQUER
        um dos slots da última camada (a permutação é resolvida na Fase 5),
        mas seu adesivo da cor do topo precisa apontar para "top".
        """
        top_color = self.get_center_color("top")
        home_face_top = next(face for face, color in cubie.stickers.items() if color == top_color)
        return self._constraint(cubie, valid_positions, [(FACE_NORMALS[home_face_top], "top")])

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
        """
        Resolve as 4 arestas da segunda camada (F2L), mantendo a primeira
        camada (cruz + cantos, já resolvida) intacta. Mesma técnica de
        busca incremental: a primeira camada inteira entra como restrição
        fixa desde o início, e cada aresta da segunda camada é buscada sem
        desfazer nada que já esteja correto.
        """
        first_layer_constraints = self._cross_edge_constraints() + self._corner_constraints()
        self._solve_constraints_incrementally(
            self._middle_edge_constraints(), already_placed=first_layer_constraints, label="aresta da segunda camada"
        )

    def solve_layer3_cross(self):
        """
        Orienta as 4 arestas da última camada (2-look OLL, parte 1): faz a
        cor do topo aparecer virada para cima em todas elas. Não se
        importa com a permutação (qual aresta fica em qual slot) — isso é
        resolvido na Fase 5. Ver `_solve_orientation` para a estratégia
        (busca rasa por progresso + fallback garantido).
        """
        first_two_layers = self._cross_edge_constraints() + self._corner_constraints() + self._middle_edge_constraints()
        self._solve_orientation(
            self._last_layer_edges(), self._top_edge_positions(), first_two_layers,
            label="orientação das arestas da última camada (OLL)",
        )

    # Profundidade máxima por estágio em `_make_orientation_progress`,
    # pareada por posição com `FACE_EXPANSION_STAGES`. Cada estágio usa uma
    # profundidade ajustada ao seu custo (mais peças/movimentos permitidos
    # = busca mais cara por nível, então profundidade menor) — o objetivo
    # aqui é ficar barato (é só o "caminho rápido"; ver o fallback
    # garantido em `_solve_orientation`), não exaustivo: quando até "todas
    # as faces" falha nessa profundidade rasa, simplesmente não há
    # progresso raso disponível para este estado, e o fallback assume.
    PROGRESS_STAGE_DEPTHS = (9, 6, 5, 4)

    def _make_orientation_progress(self, already_placed, target_constraints, current_count):
        """
        Busca (BFS rasa) uma sequência curta que orienta PELO MENOS MAIS UM
        elemento de `target_constraints` do que `current_count` (podendo
        pular direto para "todos", já que às vezes orientar exatamente
        mais um é matematicamente impossível — ver o comentário longo em
        `_solve_orientation`). Executa e retorna True se encontrou; False
        caso nenhum estágio tenha funcionado dentro do seu orçamento raso
        de profundidade.
        """
        for stage_faces, max_depth in zip(self.FACE_EXPANSION_STAGES, self.PROGRESS_STAGE_DEPTHS):
            axes_indices = {FACE_AXIS_INDEX[face] for face in stage_faces if face != "top"}
            kept_placed = [info for info in already_placed if self._constraint_touches_faces(info, axes_indices)]
            restricted = kept_placed + list(target_constraints)
            kept_count = len(kept_placed)

            def goal_fn(states, kept_placed=kept_placed, kept_count=kept_count):
                if not self._constraints_satisfied(states[:kept_count], kept_placed):
                    return False
                return self._count_satisfied(states[kept_count:], target_constraints) > current_count

            allowed_moves = self._moves_for_faces(stage_faces)
            solution = solve_pieces(
                self._current_state(restricted), goal_fn, max_depth=max_depth, allowed_moves=allowed_moves
            )
            if solution is not None:
                self.moves(solution)
                return True

        return False

    def _solve_orientation(self, oll_pieces, valid_positions, already_placed, label, max_rounds=8):
        """
        Orienta cada peça em `oll_pieces` (arestas OU cantos da última
        camada — a cor do topo precisa virar pra cima), em qualquer um dos
        slots em `valid_positions` (a permutação exata fica para a Fase
        5), mantendo `already_placed` intacto.

        Repete uma busca RASA por PROGRESSO (`_make_orientation_progress`,
        barata) até todas estarem orientadas — a mesma estratégia usada
        por qualquer "2-look OLL" real (aplicar um gatilho curto
        repetidas vezes, com ajustes de U entre uma aplicação e outra). O
        gatilho que a própria busca encontra para o caso mais comum de
        cantos (2 faces, 1 já orientado) por sinal É o Sune clássico
        (`R U R' U R U2 R'`) — a busca o redescobriu sozinha, sem receita.

        Quando uma rodada não acha NENHUM progresso raso, cai para uma
        busca completa e garantida (`_solve_constraints_together`, mais
        profunda e cara) só para aquela rodada. Isso é necessário, não só
        uma otimização: a paridade de orientação — soma de flips de
        aresta sempre par; soma de giros de canto sempre múltipla de 3 —
        às vezes torna "orientar exatamente mais uma peça" matematicamente
        impossível. Ex. cantos: com exatamente 2 já corretos, os outros 2
        têm giros que só somam à paridade certa se forem opostos (+1 e
        -1, nunca +1 e +1) — então NUNCA dá pra corrigir só um deles, e a
        única "próxima parada" válida é corrigir os 2 juntos. O mesmo
        raciocínio vale para arestas (soma de flips par: "exatamente 1 ou
        3 corrigidas" é impossível). Uma busca rasa por "só mais uma"
        nunca encontra isso — é genuinamente impossível naquela
        profundidade ou em qualquer profundidade —, daí o fallback
        garantido (descoberto assim: `solve_layer3_cross` chegou a falhar
        silenciosamente em scrambles maiores antes deste fallback existir,
        ver `docs/CHANGELOG.md`).
        """
        for _ in range(max_rounds):
            constraints = [self._oll_orientation_constraint(cubie, valid_positions) for cubie in oll_pieces]
            current_count = self._count_satisfied(self._current_state(constraints), constraints)
            if current_count == len(constraints):
                return

            if self._make_orientation_progress(already_placed, constraints, current_count):
                continue

            # Nenhum progresso raso disponível: cai para a busca completa e
            # garantida (mais cara), só para esta rodada. `_solve_group` já
            # imprime seu próprio aviso se nem essa encontrar solução.
            self._solve_constraints_together(
                constraints, already_placed=already_placed, label=f"{label} (busca completa)", max_depth=14,
            )
            return

        print(f"AVISO: {label} não convergiu.")

    def solve_layer3_orient_corners(self, max_rounds=8):
        """
        Orienta os 4 cantos da última camada (2-look OLL, parte 2). Mantém
        as duas primeiras camadas E as arestas da última camada (já
        orientadas na etapa anterior) intactas. Ver `_solve_orientation`
        para a estratégia (busca rasa por progresso + fallback garantido).
        """
        already_placed = self._cross_edge_constraints() + self._corner_constraints() + self._middle_edge_constraints()
        top_edge_positions = self._top_edge_positions()
        already_placed += [
            self._oll_orientation_constraint(cubie, top_edge_positions)
            for cubie in self._last_layer_edges()
        ]
        self._solve_orientation(
            self._last_layer_corners(), self._top_corner_positions(), already_placed,
            label="orientação dos cantos da última camada (OLL)", max_rounds=max_rounds,
        )

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
