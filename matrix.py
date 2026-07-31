"""
Arquivo com a classe Matrix3 para operações de matrizes 3x3
Usada para rotacionar as peças do cubo mágico e calcular novas posições e orientações
"""
import math


class Matrix3:
    """
    Classe que representa uma matriz 3x3 para transformações geométricas em espaço 3D
    O padrão é a matriz identidade (não altera vetores
    """
    def __init__(self, m00=1, m01=0, m02=0,
                       m10=0, m11=1, m12=0,
                       m20=0, m21=0, m22=1):
        # Armazena os dados da matriz em uma lista 2D
        self.data = [
         [m00, m01, m02],
         [m10, m11, m12],
         [m20, m21, m22]
        ]

    @staticmethod
    def rotation_x(angle_deg):
        """
        Cria uma matriz de rotação ao redor do eixo X
        :param angle_deg: Ângulo de rotação em graus
        :return: Objeto Matrix3 com a matriz de rotação
        """
        angle = math.radians(angle_deg)  # Converte graus para radianos
        c = math.cos(angle)
        s = math.sin(angle)
        return Matrix3(
            1, 0, 0,
            0, c, s,
            0, -s, c
        )

    @staticmethod
    def rotation_y(angle_deg):
        """
        Cria uma matriz de rotação ao redor do eixo Y
        :param angle_deg: Ângulo de rotação em graus
        :return: Objeto Matrix3 com a matriz de rotação
        """
        angle = math.radians(angle_deg)  # Converte graus para radianos
        c = math.cos(angle)
        s = math.sin(angle)
        return Matrix3(
            c, 0, -s,
            0, 1, 0,
            s, 0, c
        )

    @staticmethod
    def rotation_z(angle_deg):
        """
        Cria uma matriz de rotação ao redor do eixo Z
        :param angle_deg: Ângulo de rotação em graus
        :return: Objeto Matrix3 com a matriz de rotação
        """
        angle = math.radians(angle_deg)  # Converte graus para radianos
        c = math.cos(angle)
        s = math.sin(angle)
        return Matrix3(
            c, s, 0,
            -s, c, 0,
            0, 0, 1
        )

    def multiply(self, other):
        """
        Multiplica esta matriz por outra matriz 3x3
        :param other: Matriz a ser multiplicada
        :return: Nova Matrix3 com o resultado da multiplicação
        """
        result = Matrix3()
        for i in range(3):
               for j in range(3):
                  result.data[i][j] = sum(
                      self.data[i][k] * other.data[k][j]
                      for k in range(3)
                  )
        return result

    def transform_vector(self, vec):
        """
        Aplica a transformação da matriz a um vetor 3D
        :param vec: Vetor a ser transformado
        :return: Novo vetor com a transformação aplicada
        """
        return [
               self.data[0][0] * vec[0] + self.data[0][1] * vec[1] + self.data[0][2] * vec[2],
               self.data[1][0] * vec[0] + self.data[1][1] * vec[1] + self.data[1][2] * vec[2],
               self.data[2][0] * vec[0] + self.data[2][1] * vec[1] + self.data[2][2] * vec[2]
        ]

    def to_opengl(self):
        """
        Converte a matriz 3x3 para o formato de matriz 4x4 do OpenGL
        Necessário para usar com a função glMultMatrixf
        A ordem é transposta para o OpenGL
        :return: Lista no formato de matriz OpenGL (4x4)
        """
        return [
               self.data[0][0], self.data[1][0], self.data[2][0], 0,
               self.data[0][1], self.data[1][1], self.data[2][1], 0,
               self.data[0][2], self.data[1][2], self.data[2][2], 0,
               0, 0, 0, 1
        ]
