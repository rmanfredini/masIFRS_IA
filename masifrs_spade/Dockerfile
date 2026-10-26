# ==============================================================================
# MAS-IFRS (SPADE 4.1.4) — Container dos Agentes e Monitor HTTPS
# ==============================================================================
FROM --platform=linux/amd64 python:3.12-slim

# Evitar prompts interativos no apt e buffers no Python
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Instalação de dependências do sistema necessárias para compilação e execução
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    openssl \
    curl \
    procps \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependências Python em camada separada para cache do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copiar todo o código da versão SPADE
COPY . /app

# Garantir permissão de execução no script de inicialização
RUN chmod +x /app/start.sh

# Porta do Monitor Web (HTTPS)
EXPOSE 8765

# Executa o script que inicia os agentes SPADE e o monitor HTTPS
ENTRYPOINT ["/app/start.sh"]
