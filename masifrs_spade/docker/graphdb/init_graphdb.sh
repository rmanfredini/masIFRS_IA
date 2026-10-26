#!/bin/sh
set -e

# ==============================================================================
# Script de Inicialização e Carga Automática do GraphDB para MAS-IFRS
#
# Verifica se o repositório masIFRS existe e se possui dados; se estiver vazio,
# cria o repositório e carrega a ontologia do arquivo masIFRS-config.ttl.
# ==============================================================================

GRAPHDB_BASE_URL="${GRAPHDB_BASE_URL:-http://localhost:7200}"
# Se a URL contiver /repositories/..., extrair apenas o host:porta
GRAPHDB_BASE_URL=$(echo "$GRAPHDB_BASE_URL" | sed -E 's|/repositories/.*||')
REPO_ID="${REPO_ID:-masIFRS}"
CONFIG_FILE="${REPO_CONFIG_PATH:-/opt/dbs/masIFRS-config.ttl}"

# Fallback para caminho local se executado fora do container Docker
if [ ! -f "$CONFIG_FILE" ]; then
    if [ -f "DBs/masIFRS-config.ttl" ]; then
        CONFIG_FILE="DBs/masIFRS-config.ttl"
    elif [ -f "masifrs_spade/DBs/masIFRS-config.ttl" ]; then
        CONFIG_FILE="masifrs_spade/DBs/masIFRS-config.ttl"
    elif [ -f "../DBs/masIFRS-config.ttl" ]; then
        CONFIG_FILE="../DBs/masIFRS-config.ttl"
    fi
fi

echo "⏳ [GraphDB Init] Verificando GraphDB em $GRAPHDB_BASE_URL..."
MAX_ATTEMPTS=30
ATTEMPT=0
until curl -s -f "$GRAPHDB_BASE_URL/rest/repositories" >/dev/null 2>&1; do
    ATTEMPT=$((ATTEMPT + 1))
    if [ "$ATTEMPT" -ge "$MAX_ATTEMPTS" ]; then
        echo "⚠️  [GraphDB Init] GraphDB não respondeu em $GRAPHDB_BASE_URL após ${MAX_ATTEMPTS} tentativas. Continuando..."
        exit 0
    fi
    sleep 2
done
echo "✅ [GraphDB Init] GraphDB está online."

# 1. Verificar se o repositório já existe
REPOS=$(curl -s "$GRAPHDB_BASE_URL/rest/repositories" || echo "[]")
REPO_EXISTS=false
if echo "$REPOS" | grep -q "\"id\":\"$REPO_ID\""; then
    REPO_EXISTS=true
fi

if [ "$REPO_EXISTS" = "false" ]; then
    echo "📦 [GraphDB Init] Repositório '$REPO_ID' não existe. Criando a partir de $CONFIG_FILE..."
    if [ -f "$CONFIG_FILE" ]; then
        curl -s -X POST "$GRAPHDB_BASE_URL/rest/repositories" -F "config=@$CONFIG_FILE"
        echo "✅ [GraphDB Init] Repositório '$REPO_ID' criado com sucesso!"
    else
        echo "❌ [GraphDB Init] Arquivo de configuração '$CONFIG_FILE' não encontrado!"
        exit 0
    fi
else
    echo "ℹ️  [GraphDB Init] Repositório '$REPO_ID' já existe."
fi

# 2. Verificar se o repositório possui declarações (se está vazio)
SIZE=$(curl -s "$GRAPHDB_BASE_URL/repositories/$REPO_ID/size" || echo "0")
echo "🔍 [GraphDB Init] Declarações atuais em '$REPO_ID': $SIZE"

if [ "$SIZE" = "0" ] || [ -z "$SIZE" ]; then
    echo "📥 [GraphDB Init] Repositório '$REPO_ID' está vazio. Carregando ontologia de $CONFIG_FILE..."
    if [ -f "$CONFIG_FILE" ]; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$GRAPHDB_BASE_URL/repositories/$REPO_ID/statements" \
            -H "Content-Type: text/turtle" \
            --data-binary "@$CONFIG_FILE")
        
        NEW_SIZE=$(curl -s "$GRAPHDB_BASE_URL/repositories/$REPO_ID/size" || echo "0")
        echo "✅ [GraphDB Init] Ontologia carregada com sucesso! (HTTP $HTTP_CODE | Total: $NEW_SIZE declarações)"
    else
        echo "❌ [GraphDB Init] Arquivo de ontologia '$CONFIG_FILE' não encontrado!"
    fi
else
    echo "ℹ️  [GraphDB Init] O repositório '$REPO_ID' já possui $SIZE declarações. Nenhuma carga adicional necessária."
fi
