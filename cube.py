"""
Arquivo com a classe Cube, que representa o cubo mágico completo
Contém a lista de cubinhos e métodos para rotacionar faces e embaralhar
"""
from cubie import Cubie
from matrix import Matrix3
import random


class Cube:
    """
    Classe que representa o cubo mágico completo
    Contém os 27 cubinhos e gerencia as animações de rotação de faces
    """
    def __init__(self):
        """
        Inicializa um novo cubo mágico, criando todos os 27 cubinhos
        """
        self.cubies = []  # Lista de todos os cubinhos
        self._create_cubies()  # Cria os cubinhos nas posições iniciais
        self.animating = False  # Indica se uma animação está em andamento
        self.animation_axis = None  # Eixo da animação (0: x, 1: y, 2: z)
        self.animation_index = None  # Índice da face a ser animada (-1 ou 1)
        self.animation_target_angle = 0  # Ângulo final da animação (graus)
        self.animation_current_angle = 0  # Ângulo atual da animação (graus)
        self.animation_speed = 500 # Velocidade da animação (graus por segundo)
        self.animation_matrix = None  # Matriz de rotação para a animação
        self.scramble_history = []  # Histórico acumulado de embaralhamentos para desfazer

    def _create_cubies(self):
        """
        Cria todos os 27 cubinhos e os adiciona à lista
        Posições lógicas (x, y, z) variam de -1 a 1
        """
        for x in [-1, 0, 1]:
            for y in [-1, 0, 1]:
                for z in [-1, 0, 1]:
                    self.cubies.append(Cubie(logical_position=(x, y, z)))

    def draw(self):
        """
        Desenha todos os cubinhos do cubo mágico na tela
        """
        for cubie in self.cubies:
            cubie.draw()

    def rotate_face(self, axis, index, angle):
        """
        Inicia a animação de rotação de uma face do cubo
        :param axis: Eixo de rotação (0: x, 1: y, 2: z)
        :param index: Índice da face a ser rotacionada (-1 ou 1)
        :param angle: Ângulo de rotação (graus, 90 ou -90)
        """
        if self.animating:  # Se já tem uma animação em andamento, ignora
            return
        self.animating = True
        self.animation_axis = axis
        self.animation_index = index
        self.animation_target_angle = angle
        self.animation_current_angle = 0
        # Cria a matriz de rotação para a face
        if axis == 0:
            self.animation_matrix = Matrix3.rotation_x(angle)
        elif axis == 1:
            self.animation_matrix = Matrix3.rotation_y(angle)
        else:
            self.animation_matrix = Matrix3.rotation_z(angle)

    def update(self, dt):
        """
        Atualiza a animação de rotação de face
        :param dt: Tempo decorrido desde a última atualização (segundos)
        """
        if not self.animating:  # Se não tem animação, não faz nada
            return
        # Calcula o passo da animação (com o mesmo sinal do ângulo alvo)
        step = self.animation_speed * dt
        if self.animation_target_angle < 0:
            step = -step
        # Verifica se o passo ultrapassa o ângulo alvo
        if abs(self.animation_current_angle + step) >= abs(self.animation_target_angle):
            step = self.animation_target_angle - self.animation_current_angle
        self.animation_current_angle += step
        # Cria a matriz de rotação para este passo
        if self.animation_axis == 0:
            current_matrix = Matrix3.rotation_x(step)
        elif self.animation_axis == 1:
            current_matrix = Matrix3.rotation_y(step)
        else:
            current_matrix = Matrix3.rotation_z(step)
        # Aplica o passo da animação a todos os cubinhos da face
        for cubie in self.cubies:
            if cubie.logical_position[self.animation_axis] == self.animation_index:
                cubie.animate_rotate(current_matrix, self.animation_axis, self.animation_index)
        # Verifica se a animação terminou
        if abs(self.animation_current_angle - self.animation_target_angle) < 0.01:
            # Atualiza a posição e orientação final dos cubinhos da face
            for cubie in self.cubies:
                if cubie.logical_position[self.animation_axis] == self.animation_index:
                    new_pos = self.animation_matrix.transform_vector(cubie.logical_position)
                    cubie.logical_position = [round(x) for x in new_pos]
                    cubie.orientation = self.animation_matrix.multiply(cubie.orientation)
                    cubie.reset_animation()  # Reseta os valores de animação
            self.animating = False  # Marca a animação como terminada

    def scramble(self, moves=20):
        """
        Embaralha o cubo mágico com uma série de rotações aleatórias
        :param moves: Número de movimentos de embaralhamento (padrão: 20)
        """
        if self.animating:  # Se tem animação em andamento, ignora
            return
        for _ in range(moves):
            axis = random.randint(0, 2)  # Eixo aleatório (0, 1, 2)
            index = random.choice([-1, 1])  # Índice aleatório (-1, 1)
            angle = random.choice([90, -90])  # Ângulo aleatório (90 ou -90)
            # Registra o movimento no histórico
            self.scramble_history.append( (axis, index, angle) )
            # Cria a matriz de rotação
            if axis == 0:
                matrix = Matrix3.rotation_x(angle)
            elif axis == 1:
                matrix = Matrix3.rotation_y(angle)
            else:
                matrix = Matrix3.rotation_z(angle)
            # Aplica a rotação aos cubinhos da face
            for cubie in self.cubies:
                if cubie.logical_position[axis] == index:
                    new_pos = matrix.transform_vector(cubie.logical_position)
                    cubie.logical_position = [round(x) for x in new_pos]
                    cubie.orientation = matrix.multiply(cubie.orientation)
                    cubie.reset_animation()
