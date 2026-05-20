import os
import sys

try:
    import charset_normalizer
except ImportError:
    import subprocess

    print("Instalando biblioteca para detecção automática de texto...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "charset-normalizer"]
    )
    import charset_normalizer


def analisar_e_converter_csv_pesado(caminho_origem, caminho_destino=None):
    if not caminho_destino:
        nome, ext = os.path.splitext(caminho_origem)
        caminho_destino = f"{nome}_utf8{ext}"

    print(
        f"\n[1/3] Analisando os primeiros bytes de: {os.path.basename(caminho_origem)}..."
    )

    # Detecta a codificação lendo apenas o cabeçalho e as primeiras linhas (super rápido)
    with open(caminho_origem, "rb") as f:
        amostra = f.read(512 * 1024)  # 512 KB de amostra
        resultado = charset_normalizer.from_bytes(amostra).best()

    if not resultado:
        print("❌ Não foi possível detectar a codificação automaticamente.")
        return False

    codificacao_detectada = resultado.encoding
    confianca = resultado.coherence
    print(
        f"🔍 Codificação Detectada: '{codificacao_detectada}' (Confiança: {confianca*100:.1f}%)"
    )

    print(f"[2/3] Convertendo arquivo pesado para UTF-8 de forma segura...")

    try:
        # Lendo e escrevendo em blocos de 16MB para não travar a memória RAM
        tamanho_bloco = 16 * 1024 * 1024
        total_bytes = os.path.getsize(caminho_origem)
        bytes_processados = 0

        with open(
            caminho_origem, "r", encoding=codificacao_detectada, errors="replace"
        ) as origem:
            with open(caminho_destino, "w", encoding="utf-8", newline="") as destino:
                while True:
                    linhas = origem.readlines(tamanho_bloco)
                    if not linhas:
                        break
                    destino.writelines(linhas)
                    bytes_processados += sum(
                        len(line.encode(codificacao_detectada, errors="replace"))
                        for line in linhas
                    )
                    progresso = (bytes_processados / total_bytes) * 100
                    print(
                        f"   ⚡ Progresso: {min(progresso, 100.0):.1f}% processado...",
                        end="\r",
                    )

        print(f"\n[3/3] 🎉 Sucesso absoluto!")
        print(
            f"✅ Arquivo original salvo e corrigido em: '{os.path.basename(caminho_destino)}'"
        )
        return True

    except Exception as e:
        print(f"\n❌ Erro durante a conversão: {str(e)}")
        return False


if __name__ == "__main__":
    print("=== CONVERSOR DE ENCODING AUTOMÁTICO E ULTRA-RÁPIDO ===")
    print(
        "Digite ou cole o caminho completo do arquivo de votação (ex: pasta_votacao/votacao_2022.csv):"
    )
    caminho = input("Caminho do arquivo: ").strip().strip('"').strip("'")

    if os.path.exists(caminho):
        analisar_e_converter_csv_pesado(caminho)
    else:
        print("❌ Arquivo não encontrado! Verifique se digitou o caminho correto.")
