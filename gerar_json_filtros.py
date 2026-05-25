import json
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, URL

# 1. CONFIGURAÇÃO DA CONEXÃO COM O BANCO
url_banco = URL.create(
    drivername="postgresql",
    username="Carlos",
    password="C@3*07mo",
    host="localhost",
    port=5432,
    database="eleicoes_db",
)

engine = create_engine(url_banco, client_encoding="utf8")


def gerar_json_ultra_compacto():
    print("🚀 Buscando os dados no banco...")
    query = """
        SELECT 
            municipio, nome_local, latitude, longitude, bairro, zona,
            numero_secao, ano_eleicao, cargo, candidato, total_votos
        FROM v_detalhe_votos;
    """
    df = pd.read_sql(query, engine)

    # Tratamento de valores nulos para evitar quebras no JSON
    df["latitude"] = df["latitude"].replace({np.nan: None})
    df["longitude"] = df["longitude"].replace({np.nan: None})
    df["bairro"] = df["bairro"].fillna("")
    df["zona"] = df["zona"].fillna("")

    print("📦 Compactando a estrutura em memória...")
    dados_compactados = []

    # Agrupamos por Local Físico para evitar repetições exaustivas de strings
    grouped_locais = df.groupby(["municipio", "nome_local", "bairro", "zona"])

    for (mun, nome_local, bairro, zona), df_local in grouped_locais:
        lat = df_local["latitude"].iloc[0]
        lng = df_local["longitude"].iloc[0]

        lat = float(lat) if lat is not None else None
        lng = float(lng) if lng is not None else None

        secoes_lista = []
        # Agrupamos por Seção Eleitoral dentro desse local
        for num_secao, df_secao in df_local.groupby("numero_secao"):
            votos_lista = []
            for _, row in df_secao.iterrows():
                # Formato posicional ultra-leve: [ano, cargo, candidato, total_votos]
                votos_lista.append(
                    [
                        int(row["ano_eleicao"]),
                        str(row["cargo"]).strip(),
                        str(row["candidato"]).strip(),
                        int(row["total_votos"]),
                    ]
                )

            secoes_lista.append({"sec": str(num_secao), "v": votos_lista})

        # Montamos o dicionário usando mini-chaves (m, n, b, z, s)
        dados_compactados.append(
            {
                "m": str(mun).strip(),
                "n": str(nome_local).strip(),
                "b": str(bairro).strip(),
                "z": str(zona).strip(),
                "lat": lat,
                "lng": lng,
                "s": secoes_lista,
            }
        )

    print("💾 Gravando e dividindo os arquivos finais...")

    # Vamos dividir a lista de locais em blocos menores (ex: 200 locais por arquivo)
    tamanho_bloco = 200
    blocos = [
        dados_compactados[i : i + tamanho_bloco]
        for i in range(0, len(dados_compactados), tamanho_bloco)
    ]

    # Salva cada bloco com um número (dados_votos_1.json, dados_votos_2.json, etc)
    for index, bloco in enumerate(blocos):
        nome_arquivo = f"dados_votos_{index + 1}.json"
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            json.dump(bloco, f, ensure_ascii=False, separators=(",", ":"))
        print(f"📁 Gerado: {nome_arquivo}")

    # Salva um arquivo mestre dizendo quantos pedaços existem
    with open("manifesto.json", "w", encoding="utf-8") as f:
        json.dump({"total_arquivos": len(blocos)}, f)

    print(f"🎉 Sucesso! {len(blocos)} arquivos gerados abaixo do limite do GitHub.")


if __name__ == "__main__":
    gerar_json_ultra_compacto()
