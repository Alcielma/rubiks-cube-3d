"""
Arquivo com a classe Cubie, que representa cada peça individual do cubo mágico
Cada Cubie tem posição lógica, posição de animação, orientação e cores nas faces
"""
from OpenGL.GL import *
from colors import BLACK, WHITE, YELLOW, BLUE, GREEN, RED, ORANGE
from matrix import Matrix3


class Cubie:
    """
    Classe que representa uma única peça (cubinho) do cubo mágico
    """
    def __init__(self, logical_position, size=0.97):
        """
        Inicializa um novo Cubie
        :param logical_position: Posição lógica (x, y, z) no cubo (valores -1, 0, 1)
        :param size: Tamanho do cubinho (padrão 0.9 para deixar espaço entre eles)
        """
        self.logical_position = list(logical_position)  # Posição final do cubinho
        self.animation_position = list(logical_position)  # Posição temporária para animação
        self.size = size
        x, y, z = logical_position

        # Inicializa todas as faces como preto (internas, não visíveis)
        self.stickers = {
            "front": BLACK,
            "back": BLACK,
            "left": BLACK,
            "right": BLACK,
            "top": BLACK,
            "bottom": BLACK
        }

        # Atribui cores às faces externas do cubo mágico
        if z == 1:  # Face frontal (z positivo)
            self.stickers["front"] = YELLOW
        if z == -1:  # Face traseira (z negativo)
            self.stickers["back"] = WHITE
        if x == -1:  # Face esquerda (x negativo)
            self.stickers["left"] = ORANGE
        if x == 1:  # Face direita (x positivo)
            self.stickers["right"] = RED
        if y == 1:  # Face superior (y positivo)
            self.stickers["top"] = BLUE
        if y == -1:  # Face inferior (y negativo)
            self.stickers["bottom"] = GREEN

        self.orientation = Matrix3()  # Orientação final do cubinho
        self.animation_orientation = Matrix3()  # Orientação temporária para animação

        # Calcula os vértices do cubinho
        s = size / 2
        self.vertices = [
            [-s, -s, -s],  # 0: trás-inferior-esquerdo
            [ s, -s, -s],  # 1: trás-inferior-direito
            [ s,   s, -s],  # 2: trás-superior-direito
            [-s,   s, -s],  # 3: trás-superior-esquerdo
            [-s, -s,    s],  # 4: frente-inferior-esquerdo
            [ s, -s,    s],  # 5: frente-inferior-direito
            [ s,   s,    s],  # 6: frente-superior-direito
            [-s,   s,    s]   # 7: frente-superior-esquerdo
        ]

        # Arestas do cubinho (apenas para referência, não desenhadas)
        self.edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),  # Arestas da face traseira
            (4, 5), (5, 6), (6, 7), (7, 4),  # Arestas da face frontal
            (0, 4), (1, 5), (2, 6), (3, 7)   # Arestas conectando frente e trás
        ]

        # Faces do cubinho, com seus vértices e nome da face
        self.faces = [
            ([0, 1, 2, 3], "back"),     # Face traseira
            ([4, 5, 6, 7], "front"),    # Face frontal
            ([0, 1, 5, 4], "bottom"),   # Face inferior
            ([2, 3, 7, 6], "top"),      # Face superior
            ([0, 3, 7, 4], "left"),     # Face esquerda
            ([1, 2, 6, 5], "right")     # Face direita
        ]

    def draw(self):
        """
        Desenha o cubinho na tela usando OpenGL
        Aplica translação e rotação com base na posição e orientação
        """
        glPushMatrix()  # Salva a matriz de transformação atual
        glTranslatef(*self.animation_position)  # Move o cubinho para sua posição
        # Aplica a rotação da animação + rotação final
        glMultMatrixf(self.animation_orientation.multiply(self.orientation).to_opengl())

        glBegin(GL_QUADS)  # Inicia o desenho de quadriláteros (faces)
        for vertex_indices, local_face in self.faces:
            color = self.stickers[local_face]
            glColor3fv(color)  # Define a cor da face
            for vi in vertex_indices:
                  glVertex3fv(self.vertices[vi])  # Desenha cada vértice da face
        glEnd()

        glPopMatrix()  # Restaura a matriz de transformação anterior

    def animate_rotate(self, matrix, axis, index):
        """
        Aplica uma rotação temporária para a animação
        Rotaciona em torno do centro do cubo mágico, não do próprio cubinho
        :param matrix: Matriz de rotação a ser aplicada
        :param axis: Eixo de rotação (0: x, 1: y, 2: z)
        :param index: Índice da face a ser rotacionada (-1 ou 1)
        """
        # Rotaciona a posição de animação
        pos = self.animation_position
        new_pos = matrix.transform_vector(pos)
        self.animation_position = new_pos
        # Rotaciona a orientação de animação
        self.animation_orientation = matrix.multiply(self.animation_orientation)

    def reset_animation(self):
        """
        Reseta a posição e orientação de animação para os valores finais
        Chamado quando a animação de rotação de face termina
        """
        self.animation_position = list(self.logical_position)
        self.animation_orientation = Matrix3()

    def rotate(self, matrix, axis, index):
        """
        Aplica uma rotação permanente ao cubinho (sem animação)
        :param matrix: Matriz de rotação a ser aplicada
        :param axis: Eixo de rotação (0: x, 1: y, 2: z)
        :param index: Índice da face a ser rotacionada (-1 ou 1)
        """
        if self.logical_position[axis] == index:
            new_pos = matrix.transform_vector(self.logical_position)
            self.logical_position = [round(x) for x in new_pos]
            self.orientation = matrix.multiply(self.orientation)

    def get_global_colors(self):
        """
        Retorna as cores das faces do cubo mágico (globais), levando em conta a orientação do cubinho
        :return: Dicionário com as cores das faces globais (front, back, left, right, top, bottom)
        """
        # Mapeia cada face LOCAL do cubinho para seu vetor normal
        local_normals = {
            "front": (0, 0, 1),
            "back": (0, 0, -1),
            "left": (-1, 0, 0),
            "right": (1, 0, 0),
            "top": (0, 1, 0),
            "bottom": (0, -1, 0)
        }
        
        global_colors = {
            "front": None,
            "back": None,
            "left": None,
            "right": None,
            "top": None,
            "bottom": None
        }
        
        # Para cada face LOCAL do cubinho
        for local_face, normal in local_normals.items():
            # Rotaciona o vetor normal com a orientação do cubinho
            rotated_normal = self.orientation.transform_vector(normal)
            # Arredonda para evitar erros de ponto flutuante
            rotated_normal = [round(x) for x in rotated_normal]
            
            # Mapeia o vetor normal rotacionado para a face GLOBAL
            if rotated_normal == (0, 0, 1):
                global_face = "front"
            elif rotated_normal == (0, 0, -1):
                global_face = "back"
            elif rotated_normal == (-1, 0, 0):
                global_face = "left"
            elif rotated_normal == (1, 0, 0):
                global_face = "right"
            elif rotated_normal == (0, 1, 0):
                global_face = "top"
            elif rotated_normal == (0, -1, 0):
                global_face = "bottom"
            else:
                continue  # Não deve acontecer
            
            # Atribui a cor do sticker local à face global
            global_colors[global_face] = self.stickers[local_face]
        
        return global_colors
