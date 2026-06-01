import os

# --- CONFIGURAÇÕES ---
# 1. Coloque o caminho para o diretório raiz do seu projeto aqui.
#    Se o script estiver na raiz, você pode usar '.'
diretorio_raiz = '/Users/rmanfredini/IFRS/Projetos/PosDoc/masIFRS/source/mas-ifrs/agent' 

# 2. Nome do arquivo de saída que conterá todo o código.
arquivo_de_saida = 'projeto_completo_para_ia.txt'

# 3. (Opcional) Lista de diretórios e arquivos a serem ignorados.
#    É MUITO IMPORTANTE ignorar ambientes virtuais e caches.
pastas_a_ignorar = {'venv', '.venv', '__pycache__', '.git', 'node_modules', 'dist', 'build'}
arquivos_a_ignorar = {'consolidar_codigo.py'} # Ignora o próprio script

# --- SCRIPT ---
def consolidar_codigo_fonte(raiz, saida, ignorar_pastas, ignorar_arquivos):
    """
    Varre um diretório, encontra arquivos .py e os concatena em um único arquivo de texto.
    """
    print(f"Iniciando a consolidação do projeto em: {os.path.abspath(raiz)}")
    
    with open(saida, 'w', encoding='utf-8') as f_out:
        # Escreve um cabeçalho geral no arquivo
        f_out.write("="*80 + "\n")
        f_out.write("CONSOLIDAÇÃO DO CÓDIGO-FONTE DO PROJETO\n")
        f_out.write("="*80 + "\n\n")

        for dirpath, dirnames, filenames in os.walk(raiz):
            # Remove as pastas a serem ignoradas da busca para otimizar
            dirnames[:] = [d for d in dirnames if d not in ignorar_pastas]

            for filename in filenames:
                if (filename.endswith('.py') or filename.endswith('.sparql') or filename.endswith('.json')) and filename not in ignorar_arquivos:
                    caminho_completo = os.path.join(dirpath, filename)
                    caminho_relativo = os.path.relpath(caminho_completo, raiz)
                    
                    print(f"Adicionando arquivo: {caminho_relativo}")

                    # Escreve um separador e o caminho do arquivo
                    f_out.write("-" * 80 + "\n")
                    f_out.write(f"ARQUIVO: {caminho_relativo.replace(os.sep, '/')}\n")
                    f_out.write("-" * 80 + "\n\n")
                    
                    try:
                        with open(caminho_completo, 'r', encoding='utf-8', errors='ignore') as f_in:
                            f_out.write(f_in.read())
                        f_out.write("\n\n")
                    except Exception as e:
                        f_out.write(f"!!! Erro ao ler o arquivo: {e} !!!\n\n")

    print(f"\nConsolidação concluída! Todo o código foi salvo em '{saida}'.")

if __name__ == '__main__':
    consolidar_codigo_fonte(diretorio_raiz, arquivo_de_saida, pastas_a_ignorar, arquivos_a_ignorar)