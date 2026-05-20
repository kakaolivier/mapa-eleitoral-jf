import json
import os
import pandas as pd
from sqlalchemy import create_engine, URL

# 1. CONFIGURAÇÃO DA CONEXÃO COM CREDENCIAIS REAIS
url_banco = URL.create(
    drivername="postgresql",
    username="Carlos",
    password="C@3*07mo",
    host="localhost",
    port=5432,
    database="eleicoes_db",
)

# O SEGREDO ESTÁ AQUI: conectamos forçando o cliente a usar UTF-8 nativo
engine = create_engine(url_banco, client_encoding="utf8")


def gerar_json_filtros():
    print("Buscando dados do banco de dados...")

    # Query que traz os dados estruturados do banco
    query = """
        SELECT 
            nome_local, municipio, bairro, zona, latitude, longitude,
            numero_secao, ano_eleicao, cargo, candidato, total_votos
        FROM v_detalhe_votos; 
    """

    # Executa a busca garantindo o charset correto
    df = pd.read_sql(query, engine)

    # ... (o resto do código do script continua exatamente igual)

    locais_dict = {}

    print("Processando e estruturando a árvore do JSON...")
    for _, row in df.iterrows():
        # Garante que o texto vindo do banco seja interpretado como string limpa
        nome_local = str(row["nome_local"]).strip()
        municipio = str(row["municipio"]).strip()
        bairro = str(row["bairro"]).strip() if pd.notna(row["bairro"]) else ""
        zona = str(row["zona"])

        id_local = f"{municipio}_{zona}_{nome_local}"

        if id_local not in locais_dict:
            lat_val = row["latitude"] if pd.notna(row["latitude"]) else None
            lng_val = row["longitude"] if pd.notna(row["longitude"]) else None

            locais_dict[id_local] = {
                "nome": nome_local,
                "municipio": municipio,
                "bairro": bairro,
                "zona": zona,
                "lat": lat_val,
                "lng": lng_val,
                "secoes": {},
            }

        num_secao = str(row["numero_secao"])
        if num_secao not in locais_dict[id_local]["secoes"]:
            locais_dict[id_local]["secoes"][num_secao] = {
                "secao": num_secao,
                "votos": [],
            }

        locais_dict[id_local]["secoes"][num_secao]["votos"].append(
            {
                "ano": int(row["ano_eleicao"]),
                "cargo": str(row["cargo"]).strip(),
                "candidato": str(row["candidato"]).strip(),
                "qtd": int(row["total_votos"]),
            }
        )

    # Formata o dicionário em formato de lista pura para o Leaflet
    dados_finais = []
    for id_local, info in locais_dict.items():
        secoes_lista = []
        for num_sec, sec_info in info["secoes"].items():
            secoes_lista.append(sec_info)

        dados_finais.append(
            {
                "nome": info["nome"],
                "municipio": info["municipio"],
                "bairro": info["bairro"],
                "zona": info["zona"],
                "lat": float(info["lat"]) if info["lat"] is not None else None,
                "lng": float(info["lng"]) if info["lng"] is not None else None,
                "secoes": secoes_lista,
            }
        )

    # ======================================================================
    # O PULO DO GATO: Gravação cirúrgica em UTF-8 sem re-decodificar os acentos
    # ======================================================================
    print("Gravando arquivo 'dados_votos.json' protegido em UTF-8...")

    # Abrir com encoding='utf-8' impede que o Windows use o charset local dele (cp1252)
    with open("dados_votos.json", "w", encoding="utf-8") as f:
        # ensure_ascii=False impede o Python de transformar "José" em "\u00e5"
        json.dump(dados_finais, f, ensure_ascii=False, indent=2)

    print("🎉 JSON gerado com acentuação 100% preservada!")


if __name__ == "__main__":
    gerar_json_filtros()
