import pandas as pd
import json
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# Conexão com o Banco
url_banco = URL.create(
    drivername="postgresql",
    username="Carlos",
    password="C@3*07mo",  # Substitua pela sua senha
    host="localhost",
    port=5432,
    database="eleicoes_db"
)
engine = create_engine(url_banco)

print("Buscando e detalhando dados por seção...")

# Mudança na Query: adicionamos a coluna v.secao no SELECT e no GROUP BY
query = """
    SELECT 
        l.id_local_votacao,
        l.nome_local,
        l.latitude,
        l.longitude,
        v.ano_eleicao,
        v.secao,
        v.cargo,
        v.nome_candidato,
        SUM(v.quantidade_votos) as total_votos
    FROM dim_locais_votacao l
    JOIN fato_votos v ON l.id_local_votacao = v.id_local_votacao
    GROUP BY l.id_local_votacao, l.nome_local, l.latitude, l.longitude, v.ano_eleicao, v.secao, v.cargo, v.nome_candidato
"""

df = pd.read_sql(query, engine)

locais_dict = {}

for _, row in df.iterrows():
    id_local = int(row['id_local_votacao'])
    
    if id_local not in locais_dict:
        locais_dict[id_local] = {
            "nome": row['nome_local'],
            "lat": float(row['latitude']),
            "lng": float(row['longitude']),
            "secoes": {}  # Agora organizamos por um dicionário de seções
        }
    
    num_secao = str(row['secao'])
    
    # Se a seção ainda não existe neste local, inicializa a lista de votos dela
    if num_secao not in locais_dict[id_local]["secoes"]:
        locais_dict[id_local]["secoes"][num_secao] = []
        
    # Adiciona o voto detalhado dentro daquela seção específica
    locais_dict[id_local]["secoes"][num_secao].append({
        "ano": int(row['ano_eleicao']),
        "cargo": row['cargo'],
        "candidato": row['nome_candidato'],
        "qtd": int(row['total_votos'])
    })

# Formata o dicionário para uma lista limpa para o JavaScript
dados_finais = []
for id_local, info in locais_dict.items():
    local_formatado = {
        "nome": info["nome"],
        "lat": info["lat"],
        "lng": info["lng"],
        "secoes": []
    }
    # Transforma o objeto de seções em uma lista de objetos
    for num_secao, votos in info["secoes"].items():
        local_formatado["secoes"].append({
            "numero_secao": num_secao,
            "votos": votos
        })
    dados_finais.append(local_formatado)

# Salva o arquivo JSON atualizado
with open('dados_votos.json', 'w', encoding='utf-8') as f:
    json.dump(dados_finais, f, ensure_ascii=False, indent=4)

print("Arquivo detalhado por seção 'dados_votos.json' gerado com sucesso!")