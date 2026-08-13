"""
Arquivo principal do jogo.
Cria o renderer e inicia o loop principal da aplicação.

Ajusta o sys.path para permitir rodar diretamente via `python src/main.py`
sem precisar de PYTHONPATH ou `python -m src.main`.
"""
import sys
import pathlib

# Adiciona a pasta "src" ao sys.path para resolver os imports dos subpacotes
_SRC_DIR = pathlib.Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from graphics.renderer import Renderer


def main():
    """Função principal: cria o Renderer e inicia o jogo."""
    renderer = Renderer()
    renderer.run()


if __name__ == "__main__":
    main()
