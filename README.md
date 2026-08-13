# Cubo Mágico 3D em Python

Este é um projeto de Cubo Mágico 3D interativo desenvolvido com **Python, Pygame e PyOpenGL**
(ideal para estudos de Computação Gráfica).

## Funcionalidades

- Visualização 3D do cubo com cores padrão WCA simplificadas.
- Rotação de câmera livre com o mouse (vertical e horizontal).
- Zoom com a roda do mouse.
- Rotação de todas as faces do cubo via teclado.
- Rotação inversa (anti-horária) com a tecla `Shift`.
- Botão interativo `?` com instruções de uso em tela.
- Função de embaralhar (com histórico acumulado).
- Solução automática animada que desfaz todo o histórico de embaralhamentos.

---

## Controles

### Teclado

| Tecla               | Ação                                           |
|---------------------|------------------------------------------------|
| `L` / `R`           | Girar face Esquerda / Direita (horário)        |
| `U` / `D`           | Girar face Superior / Inferior (horário)       |
| `F` / `B`           | Girar face Frontal / Traseira (horário)        |
| `Shift` + (face)    | Girar face no sentido anti-horário             |
| `S`                 | Embaralhar o cubo (várias vezes cumulativo)    |
| `K`                 | Solucionar o cubo automaticamente (animado)    |

### Mouse

- **Botão esquerdo + arrastar**: Rotacionar a câmera.
- **Roda do mouse**: Zoom in / zoom out.
- **Botão `?` (canto superior esquerdo)**: Abrir/fechar instruções.

---

## Cores das faces (configuração atual)

- **Amarelo** → Frontal (F)
- **Branco**  → Traseira (B)
- **Vermelho** → Direita (R)
- **Laranja** → Esquerda (L)
- **Azul**    → Superior (U)
- **Verde**   → Inferior (D)

---

## Estrutura de pastas

```text
rubiks-cube-3d/
├── src/
│   ├── main.py
│   ├── cube/
│   │   ├── cube.py
│   │   ├── cubie.py
│   │   └── colors.py
│   ├── graphics/
│   │   ├── renderer.py
│   │   ├── camera.py
│   │   ├── matrix.py
│   │   └── transforms.py
│   ├── input/
│   │   └── controller.py
│   └── solver/
│       └── solver.py
├── tests/
├── assets/
├── README.md
└── requirements.txt
```

### Descrição dos módulos

- **src/main.py** → ponto de entrada da aplicação; configura o ambiente de execução e inicia o sistema de renderização.
- **src/cube/** → contém a lógica e o estado do Cubo Mágico, incluindo os cubinhos, cores, posições e operações do cubo.
- **src/graphics/** → responsável pela renderização 3D com OpenGL, gerenciamento da câmera e operações matemáticas utilizadas nas transformações e matrizes.
- **src/input/controller.py** → processa as entradas do usuário, como eventos de teclado e mouse, e as converte em ações dentro do jogo.
- **src/solver/solver.py** → responsável pela lógica de resolução automática do cubo, incluindo a execução animada dos movimentos e estruturas preparadas para futuras implementações de métodos de resolução.
- **tests/** → diretório reservado para os testes automatizados dos módulos do projeto.
- **assets/** → armazena recursos externos utilizados pela aplicação, como fontes, texturas, imagens e outros arquivos.
- **requirements.txt** → lista as dependências Python necessárias para executar o projeto.

---

## Como executar

1. Instale o Python 3.8+ (recomendado 3.11/3.12).
2. Crie um ambiente virtual (opcional, mas recomendado):
   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Linux/macOS
   # .venv\Scripts\activate      # Windows
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Execute a aplicação:
   ```bash
   python src/main.py
   ```
   > Alternativa (se preferir rodar como módulo):
   > ```bash
   > PYTHONPATH=src python -m main
   > ```

---

## Observações

- O solucionador atual desfaz **exatamente** os movimentos de `scramble()` em ordem inversa.
  Isso é o suficiente para garantir que o cubo volte ao estado resolvido com animação completa.
- A estrutura já está preparada para implementar futuramente o **método de camadas
  (Layer-by-Layer)** real. Os placeholders estão em `src/solver/solver.py`.
