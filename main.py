"""
Arquivo principal do jogo
Cria um objeto Renderer e inicia o loop do jogo
"""
from renderer import Renderer


def main():
    """
    Função principal do jogo
    Cria o Renderer e inicia o jogo
    """
    renderer = Renderer()  # Cria o objeto Renderer com configurações padrão
    renderer.run()  # Inicia o loop principal do jogo


if __name__ == "__main__":
    main()  # Executa a função main se este arquivo for o arquivo principal
