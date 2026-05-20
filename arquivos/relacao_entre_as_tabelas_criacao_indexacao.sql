-- 1. Ativa a extensão geográfica PostGIS (caso ainda não esteja ativa)
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Define as Chaves Primárias e cria o relacionamento real entre as tabelas
ALTER TABLE dim_locais_votacao ADD PRIMARY KEY (id_local_votacao);
ALTER TABLE fato_votos ADD CONSTRAINT fk_votos_local FOREIGN KEY (id_local_votacao) REFERENCES dim_locais_votacao(id_local_votacao);

-- 3. Cria a coluna espacial de geometria (Pontos com coordenadas GPS)
ALTER TABLE dim_locais_votacao ADD COLUMN geom geometry(Point, 4326);

-- 4. Converte as latitudes e longitudes textuais em pontos geográficos reais
UPDATE dim_locais_votacao 
SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- 5. Cria o índice espacial (para o mapa carregar os pontos em milissegundos)
CREATE INDEX idx_dim_locais_geom ON dim_locais_votacao USING gist(geom);

-- 6. Cria os índices de texto (para os 6 filtros do site funcionarem instantaneamente)
CREATE INDEX idx_dim_locais_municipio ON dim_locais_votacao(municipio);
CREATE INDEX idx_dim_locais_bairro ON dim_locais_votacao(bairro);
CREATE INDEX idx_dim_locais_zona ON dim_locais_votacao(zona);

CREATE INDEX idx_fato_votos_ano ON fato_votos(ano_eleicao);
CREATE INDEX idx_fato_votos_cargo ON fato_votos(cargo);
CREATE INDEX idx_fato_votos_candidato ON fato_votos(nome_candidato);