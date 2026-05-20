import pandas as pd
import unicodedata
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# 1. CARREGAR OS ARQUIVOS CSV
print("Carregando arquivos...")
df_urnas_raw = pd.read_csv('URNAS_JF.csv')
df_votacao_raw = pd.read_csv('VOTACAO_JF_2024_COORDENADAS.csv')

# 2. FUNÇÃO DE PADRONIZAÇÃO DE TEXTO
def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    # Converte para maiúsculas e remove espaços nas pontas
    texto = str(texto).upper().strip()
    # Remove acentos (Ex: "MÃE" vira "MAE", "JOSÉ" vira "JOSE")
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    # Remove múltiplos espaços internos se houver
    texto = " ".join(texto.split())
    return texto

print("Normalizando nomes de locais para o cruzamento...")
df_urnas_raw['local_busca'] = df_urnas_raw['Name'].apply(normalizar_texto)
df_votacao_raw['local_busca'] = df_votacao_raw['NM_LOCAL_VOTACAO'].apply(normalizar_texto)


# 3. CONSTRUÇÃO DA TABELA DIMENSÃO (dim_locais_votacao)
# Vamos isolar os locais únicos usando o arquivo de urnas que possui as coordenadas corretas
print("Criando a tabela Dimensão de Locais...")

# Selecionamos apenas as colunas relevantes de localização
dim_locais = df_urnas_raw[[
    'local_busca', 'Name', 'ZONA', 'LOCALIDADE', 'ENDERECO', 'BAIRRO', 'LATITUDE', 'LONGITUDE'
]].copy()

# Remove duplicados para garantir que cada local físico seja uma única linha
dim_locais = dim_locais.drop_duplicates(subset=['local_busca']).reset_index(drop=True)

# Criamos uma chave primária sequencial (ID) para o banco de dados
dim_locais['id_local_votacao'] = dim_locais.index + 1

# Renomeando colunas para um padrão mais limpo para o banco de dados
dim_locais.columns = [
    'local_busca', 'nome_local', 'zona', 'municipio', 'endereco', 'bairro', 'latitude', 'longitude', 'id_local_votacao'
]


# 4. CONSTRUÇÃO DA TABELA FATO (fato_votos)
print("Criando a tabela Fato de Votos...")

# Fazemos um merge (join) para trazer o 'id_local_votacao' para dentro da tabela de votação
df_votos_processado = pd.merge(
    df_votacao_raw,
    dim_locais[['id_local_votacao', 'local_busca']],
    on='local_busca',
    how='left'
)

# Alerta caso algum local da votação não tenha sido encontrado no arquivo de coordenadas
locais_nao_encontrados = df_votos_processado[df_votos_processado['id_local_votacao'].isna()]['NM_LOCAL_VOTACAO'].unique()
if len(locais_nao_encontrados) > 0:
    print(f"Aviso: {len(locais_nao_encontrados)} locais não cruzaram perfeitamente devido a divergências de nome.")
    print("Exemplos não encontrados:", locais_nao_encontrados[:5])

# Selecionamos e limpamos as colunas da Fato (ignorando a coluna geométrica com erro do arquivo original)
fato_votos = df_votos_processado[[
    'id_local_votacao', 'ANO_ELEICAO', 'NR_TURNO', 'NR_SECAO', 
    'DS_CARGO', 'NR_VOTAVEL', 'NM_VOTAVEL', 'QT_VOTOS'
]].copy()

# Ajustando nomes das colunas da fato
fato_votos.columns = [
    'id_local_votacao', 'ano_eleicao', 'turno', 'secao', 
    'cargo', 'numero_candidato', 'nome_candidato', 'quantidade_votos'
]

# Garantindo integridade: remover registros onde o local não pôde ser mapeado (se houver)
fato_votos = fato_votos.dropna(subset=['id_local_votacao'])
fato_votos['id_local_votacao'] = fato_votos['id_local_votacao'].astype(int)


# 5. CARREGAMENTO NO POSTGRESQL VIA SQLALCHEMY
# Substitua com suas credenciais: 'postgresql://usuario:senha@localhost:5432/nome_do_banco'

# Em vez de escrever a string direto, separe os dados em um objeto URL:
url_banco = URL.create(
    drivername="postgresql",
    username="Carlos",             # Seu usuário do PostgreSQL
    password="C@3*07mo",       # Coloque sua senha exata aqui (mesmo com caracteres especiais)
    host="localhost",
    port=5432,
    database="eleicoes_db"           # O nome do seu banco de dados
)

print("Conectando ao banco de dados PostgreSQL...")
engine = create_engine(url_banco)

# Salva a dimensão (remover coluna temporária de busca antes de salvar)
dim_locais.drop(columns=['local_busca']).to_sql('dim_locais_votacao', engine, if_exists='replace', index=False)
print("Tabela 'dim_locais_votacao' enviada com sucesso.")

# Salva a fato (pode demorar alguns segundos a mais dependendo do volume total do estado)
fato_votos.to_sql('fato_votos', engine, if_exists='replace', index=False, chunksize=10000)
print("Tabela 'fato_votos' enviada com sucesso.")

print("Pipeline finalizado!")