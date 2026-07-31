# Cubo Mágico 3D em Python

Este é um projeto de Cubo Mágico 3D interativo desenvolvido com Python, PyGame e PyOpenGL para a disciplina de Computação Gráfica.

## Funcionalidades
- Visualização 3D do cubo.
- Rotação da câmera com o mouse.
- Zoom com a roda do mouse.
- Rotação das faces do cubo via teclado.
- Rotação inversa das faces com a tecla Shift.
- Botão de ajuda com instruções de uso.
- Função de embaralhar.

## Controles
### Teclado
- **L / R**: Girar faces Laterais (Left / Right).
- **U / D**: Girar faces Superior / Inferior (Up / Down).
- **F / B**: Girar faces Frontal / Traseira (Front / Back).
- **Shift + Tecla**: Girar face no sentido anti-horário.
- **S**: Embaralhar o cubo (Scramble).
- **K**: Solucionar o cubo automaticamente.

### Mouse
- **Botão Esquerdo**: Rotacionar a visualização.
- **Scroll**: Zoom In / Out.
- **Botão "?" (canto superior esquerdo)**: Abrir/fechar instruções de uso.

## Cores das Faces
- **Amarelo**: Frontal (F)
- **Branco**: Traseira (B)
- **Vermelho**: Direita (R)
- **Laranja**: Esquerda (L)
- **Azul**: Superior (U)
- **Verde**: Inferior (D)

## Como Executar
1. Certifique-se de ter o Python instalado.
2. Instale as dependências:
   ```bash
   pip install pygame PyOpenGL PyOpenGL-accelerate
   ```
3. Execute o programa:
   ```bash
   python main.py
   ```

## Estrutura do Código
- `main.py`: Ponto de entrada do programa.
- `renderer.py`: Gerencia a janela, o loop principal, a renderização OpenGL e a interface do usuário.
- `cube.py`: Lógica do cubo (conjunto de cubies e rotações de faces).
- `cubie.py`: Representação de cada pequeno cubo individual.
- `matrix.py`: Operações matemáticas de matrizes para rotações 3D.
- `camera.py`: Controle da visualização 3D.
- `input.py`: Processamento de entradas do usuário.
- `colors.py`: Definição das cores das faces.
- `solver.py`: Solucionador automático do cubo (método de camadas).
- `transforms.py`: Arquivo reservado para transformações adicionais (vazio por enquanto).
