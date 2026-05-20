import pandas as pd
import unicodedata
import os
import glob
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# ==========================================
# 1. CONFIGURAÇÃO CONEXÃO BANCO
# ==========================================
url_banco = URL.create(
    drivername="postgresql",
    username="Carlos",
    password="C@3*07mo", 
    host="localhost",
    port=5432,
    database="eleicoes_db"
)
engine = create_engine(url_banco)

def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    # Converte para string, remove espaços extras e joga para maiúsculo
    texto = str(texto).strip().upper()
    # Substitui caracteres quebrados comuns do Windows/TSE antes de limpar
    texto = texto.replace('Ã', 'A').replace('É', 'E').replace('Ó', 'O').replace('Ç', 'C').replace('Ú', 'U').replace('Í', 'I')
    # Remove qualquer acentuação restante usando a biblioteca unicodedata
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return " ".join(texto.split())

# ==========================================
# 2. PROCESSAMENTO AUTOMÁTICO DE URNAS (DIMENSÃO)
# ==========================================
print("Buscando arquivos de urnas nas pastas...")
arquivos_urnas = glob.glob('pasta_urnas/*.csv') # Pega todos os CSVs da pasta

lista_df_urnas = []
colunas_urnas = ['NAME', 'ZONA', 'LOCALIDADE', 'ENDERECO', 'BAIRRO', 'LATITUDE', 'LONGITUDE']

for arquivo in arquivos_urnas:
    print(f"Lendo e padronizando localizações do arquivo: {arquivo}")
    # Força a leitura em latin-1 com tratamento de erros de string
    df = pd.read_csv(arquivo, encoding='utf-8', on_bad_lines='skip')
        
    df.columns = df.columns.str.upper()
    df_clean = df[colunas_urnas].copy()
    lista_df_urnas.append(df_clean)

# Junta todos os anos de urnas encontrados em um só dataframe
dim_locais_raw = pd.concat(lista_df_urnas, ignore_index=True)

print("Removendo duplicidades históricas de locais...")
dim_locais_raw['local_busca'] = dim_locais_raw['NAME'].apply(normalizar_texto)
dim_locais_raw['municipio_busca'] = dim_locais_raw['LOCALIDADE'].apply(normalizar_texto)

# Remove duplicados (garante que o colégio eleitoral seja único no banco)
dim_locais = dim_locais_raw.drop_duplicates(subset=['local_busca', 'municipio_busca']).reset_index(drop=True)
dim_locais['id_local_votacao'] = dim_locais.index + 1

dim_locais_final = dim_locais[[
    'id_local_votacao', 'NAME', 'ZONA', 'LOCALIDADE', 'ENDERECO', 'BAIRRO', 'LATITUDE', 'LONGITUDE', 'local_busca', 'municipio_busca'
]].copy()
dim_locais_final.columns = [
    'id_local_votacao', 'nome_local', 'zona', 'municipio', 'endereco', 'bairro', 'latitude', 'longitude', 'local_busca', 'municipio_busca'
]

# ==========================================
# 3. PROCESSAMENTO AUTOMÁTICO DE VOTOS (FATO)
# ==========================================
print("\nBuscando arquivos de votação nas pastas...")
arquivos_votacao = glob.glob('pasta_votacao/*.csv')

lista_df_votos = []
colunas_votos = ['ANO_ELEICAO', 'NR_TURNO', 'NR_SECAO', 'DS_CARGO', 'NR_VOTAVEL', 'NM_VOTAVEL', 'QT_VOTOS', 'NM_LOCAL_VOTACAO', 'NM_MUNICIPIO']

for arquivo in arquivos_votacao:
    print(f"Empilhando dados de votação do arquivo: {arquivo}")
    # Força a leitura em latin-1 para garantir os acentos das seções/candidatos
    df = pd.read_csv(arquivo, encoding='utf-8', on_bad_lines='skip')
        
    df.columns = df.columns.str.upper()
    df_clean = df[colunas_votos].copy()
    lista_df_votos.append(df_clean)

# Junta todas as votações de todos os anos do histórico
fato_votos_raw = pd.concat(lista_df_votos, ignore_index=True)

fato_votos_raw['local_busca'] = fato_votos_raw['NM_LOCAL_VOTACAO'].apply(normalizar_texto)
fato_votos_raw['municipio_busca'] = fato_votos_raw['NM_MUNICIPIO'].apply(normalizar_texto)

print("Cruzando a grande massa de votos com os IDs geográficos...")
fato_processada = pd.merge(
    fato_votos_raw,
    dim_locais_final[['id_local_votacao', 'local_busca', 'municipio_busca']],
    on=['local_busca', 'municipio_busca'],
    how='left'
)

fato_votos_final = fato_processada[[
    'id_local_votacao', 'ANO_ELEICAO', 'NR_TURNO', 'NR_SECAO', 'DS_CARGO', 'NR_VOTAVEL', 'NM_VOTAVEL', 'QT_VOTOS'
]].copy()
fato_votos_final.columns = [
    'id_local_votacao', 'ano_eleicao', 'turno', 'secao', 'cargo', 'numero_candidato', 'nome_candidato', 'quantidade_votos'
]

fato_votos_final = fato_votos_final.dropna(subset=['id_local_votacao'])
fato_votos_final['id_local_votacao'] = fato_votos_final['id_local_votacao'].astype(int)

# ==========================================
# 4. CARGA DO HISTÓRICO NO POSTGRESQL
# ==========================================
print("\nSubstituindo dados antigos no banco pelas novas tabelas consolidadas...")
dim_locais_banco = dim_locais_final.drop(columns=['local_busca', 'municipio_busca'])

dim_locais_banco.to_sql('dim_locais_votacao', engine, if_exists='replace', index=False)
fato_votos_final.to_sql('fato_votos', engine, if_exists='replace', index=False, chunksize=20000)

print("\n--- BANCO DE DADOS ATUALIZADO COM SUCESSO COBRINDO TODO O HISTÓRICO! ---")