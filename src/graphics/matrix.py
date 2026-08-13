"""
Módulo com a classe Matrix3.
Representa uma matriz 3x3 usada para transformações geométricas:
rotações ao redor dos eixos X, Y e Z, multiplicação de matrizes e
aplicação de transformação em vetores 3D.
"""
import math


class Matrix3:
    """
    Matriz 3x3 com operações típicas usadas no cubo mágico.
    O valor padrão é a matriz identidade.
    """

    def __init__(self, m00=1, m01=0, m02=0,
                 m10=0, m11=1, m12=0,
                 m20=0, m21=0, m22=1):
        self.data = [
            [m00, m01, m02],
            [m10, m11, m12],
            [m20, m21, m22],
        ]

    @staticmethod
    def rotation_x(angle_deg):
        """Retorna uma matriz de rotação ao redor do eixo X (ângulo em graus)."""
        angle = math.radians(angle_deg)
        c = math.cos(angle)
        s = math.sin(angle)
        return Matrix3(
            1, 0, 0,
            0, c, s,
            0, -s, c,
        )

    @staticmethod
    def rotation_y(angle_deg):
        """Retorna uma matriz de rotação ao redor do eixo Y (ângulo em graus)."""
        angle = math.radians(angle_deg)
        c = math.cos(angle)
        s = math.sin(angle)
        return Matrix3(
            c, 0, -s,
            0, 1, 0,
            s, 0, c,
        )

    @staticmethod
    def rotation_z(angle_deg):
        """Retorna uma matriz de rotação ao redor do eixo Z (ângulo em graus)."""
        angle = math.radians(angle_deg)
        c = math.cos(angle)
        s = math.sin(angle)
        return Matrix3(
            c, s, 0,
            -s, c, 0,
            0, 0, 1,
        )

    def multiply(self, other):
        """Retorna nova matriz = this * other (multiplicação matricial padrão)."""
        result = Matrix3()
        for i in range(3):
            for j in range(3):
                result.data[i][j] = sum(
                    self.data[i][k] * other.data[k][j]
                    for k in range(3)
                )
        return result

    def transform_vector(self, vec):
        """Aplica a matriz a um vetor 3D e retorna o vetor transformado."""
        return [
            self.data[0][0] * vec[0] + self.data[0][1] * vec[1] + self.data[0][2] * vec[2],
            self.data[1][0] * vec[0] + self.data[1][1] * vec[1] + self.data[1][2] * vec[2],
            self.data[2][0] * vec[0] + self.data[2][1] * vec[1] + self.data[2][2] * vec[2],
        ]

    def to_opengl(self):
        """
        Converte a matriz 3x3 para uma matriz 4x4 no formato de colunas do OpenGL.
        Usado para enviar a rotação via glMultMatrixf.
        """
        return [
            self.data[0][0], self.data[1][0], self.data[2][0], 0,
            self.data[0][1], self.data[1][1], self.data[2][1], 0,
            self.data[0][2], self.data[1][2], self.data[2][2], 0,
            0, 0, 0, 1,
        ]
