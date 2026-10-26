-- MAS-IFRS PostgreSQL Initialization Schema
-- Executado automaticamente na primeira inicialização do container PostgreSQL

CREATE TABLE IF NOT EXISTS consumos (
    id SERIAL PRIMARY KEY,
    campus_id INT NOT NULL,
    valor_kw NUMERIC(10, 2) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS geracoes (
    id SERIAL PRIMARY KEY,
    campus_id INT NOT NULL,
    dispositivo_id VARCHAR(50) NOT NULL,
    potenciagerada_kw NUMERIC(10, 2) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS baterias (
    id SERIAL PRIMARY KEY,
    campus_id INT NOT NULL,
    capacidade_kwh NUMERIC(10, 2) DEFAULT 100.0,
    carga_percentual NUMERIC(5, 2) DEFAULT 75.0,
    eficiencia_percentual NUMERIC(5, 2) DEFAULT 90.0,
    ativo BOOLEAN DEFAULT TRUE,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para buscas temporais
CREATE INDEX IF NOT EXISTS idx_consumos_campus_time ON consumos (campus_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_geracoes_campus_time ON geracoes (campus_id, timestamp DESC);

-- Dados iniciais simulados para o campus 1 se vazio
INSERT INTO consumos (campus_id, valor_kw, timestamp)
SELECT 1, 45.5, NOW() - INTERVAL '1 hour'
WHERE NOT EXISTS (SELECT 1 FROM consumos WHERE campus_id = 1);

INSERT INTO geracoes (campus_id, dispositivo_id, potenciagerada_kw, timestamp)
SELECT 1, 'inversor_solar_1', 32.0, NOW() - INTERVAL '1 hour'
WHERE NOT EXISTS (SELECT 1 FROM geracoes WHERE campus_id = 1);

INSERT INTO baterias (campus_id, capacidade_kwh, carga_percentual, eficiencia_percentual, ativo)
SELECT 1, 100.0, 80.0, 92.0, TRUE
WHERE NOT EXISTS (SELECT 1 FROM baterias WHERE campus_id = 1);
