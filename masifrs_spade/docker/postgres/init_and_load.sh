#!/bin/bash
set -e

# ==============================================================================
# Script de Inicialização e Carga Automática do PostgreSQL para MAS-IFRS
#
# Executado pelo container PostgreSQL se o diretório de dados estiver inicializando.
# Verifica se o banco já possui tabelas; se estiver vazio, carrega /opt/dbs/masifrs.sql.
# ==============================================================================

DB_NAME="${POSTGRES_DB:-masifrs}"
DB_USER="${POSTGRES_USER:-admin}"
SQL_DUMP="/opt/dbs/masifrs.sql"

echo "🔧 [MAS-IFRS Init] Garantindo existência do superuser 'postgres'..."
psql -v ON_ERROR_STOP=1 --username "$DB_USER" --dbname "$DB_NAME" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'postgres') THEN
            CREATE ROLE postgres WITH SUPERUSER LOGIN PASSWORD 'admin';
        END IF;
    END
    \$\$;
    GRANT ALL PRIVILEGES ON DATABASE "$DB_NAME" TO postgres;
    GRANT ALL PRIVILEGES ON DATABASE "$DB_NAME" TO "$DB_USER";
EOSQL

echo "🔍 [MAS-IFRS Init] Verificando se o banco '$DB_NAME' possui tabelas..."
TABLE_COUNT=$(psql -v ON_ERROR_STOP=1 --username "$DB_USER" --dbname "$DB_NAME" -t -A -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")

if [ "$TABLE_COUNT" -eq 0 ]; then
    if [ -f "$SQL_DUMP" ]; then
        echo "📦 [MAS-IFRS Init] Banco vazio ($TABLE_COUNT tabelas). Carregando $SQL_DUMP..."
        psql --username "$DB_USER" --dbname "$DB_NAME" -f "$SQL_DUMP" || true
        
        echo "🔑 [MAS-IFRS Init] Concedendo permissões nas tabelas para '$DB_USER'..."
        psql --username "$DB_USER" --dbname "$DB_NAME" <<-EOSQL
            GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "$DB_USER";
            GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "$DB_USER";
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "$DB_USER";
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "$DB_USER";
EOSQL
        LOADED_COUNT=$(psql -v ON_ERROR_STOP=1 --username "$DB_USER" --dbname "$DB_NAME" -t -A -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
        echo "✅ [MAS-IFRS Init] Carga de masifrs.sql finalizada! Total de tabelas carregadas: $LOADED_COUNT."
    else
        echo "⚠️  [MAS-IFRS Init] Arquivo $SQL_DUMP não encontrado! Nenhuma carga realizada."
    fi
else
    echo "ℹ️  [MAS-IFRS Init] O banco '$DB_NAME' já contém $TABLE_COUNT tabela(s). Nenhuma carga necessária."
fi
