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
        """
        Retorna nova matriz = this * other (multiplicação matricial padrão).

        Desenrolada manualmente (sem laços/geradores): esta é a operação
        mais chamada durante a animação E durante a busca do solver
        (solver/search.py explora até algumas centenas de milhares de
        estados, cada um recalculando a orientação de várias peças), então
        o overhead de laços em Python puro é bem mensurável aqui.
        """
        a = self.data
        b = other.data
        return Matrix3(
            a[0][0] * b[0][0] + a[0][1] * b[1][0] + a[0][2] * b[2][0],
            a[0][0] * b[0][1] + a[0][1] * b[1][1] + a[0][2] * b[2][1],
            a[0][0] * b[0][2] + a[0][1] * b[1][2] + a[0][2] * b[2][2],
            a[1][0] * b[0][0] + a[1][1] * b[1][0] + a[1][2] * b[2][0],
            a[1][0] * b[0][1] + a[1][1] * b[1][1] + a[1][2] * b[2][1],
            a[1][0] * b[0][2] + a[1][1] * b[1][2] + a[1][2] * b[2][2],
            a[2][0] * b[0][0] + a[2][1] * b[1][0] + a[2][2] * b[2][0],
            a[2][0] * b[0][1] + a[2][1] * b[1][1] + a[2][2] * b[2][1],
            a[2][0] * b[0][2] + a[2][1] * b[1][2] + a[2][2] * b[2][2],
        )

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


def rotation_matrix_for_axis(axis, angle_deg):
    """
    Constrói a matriz de rotação para o eixo (0=x, 1=y, 2=z) e ângulo dados.

    Única fonte de verdade para "qual função de rotação usar para qual eixo",
    usada tanto por `Cube` (animação/estado permanente) quanto pela busca do
    solver (cube/solver/search.py), que simula movimentos sem depender de Cube.
    """
    if axis == 0:
        return Matrix3.rotation_x(angle_deg)
    elif axis == 1:
        return Matrix3.rotation_y(angle_deg)
    else:
        return Matrix3.rotation_z(angle_deg)
