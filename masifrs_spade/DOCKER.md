# 🐳 Executando MAS-IFRS (SPADE 4.1.4) com Docker

Esta arquitetura orquestra em containers todos os componentes necessários para a execução completa do ecossistema:
- **PostgreSQL 17**: Banco de dados relacional. Na inicialização, se o banco estiver vazio, carrega automaticamente a estrutura e os dados do arquivo `DBs/masifrs.sql` (5.735 consumos, 22.122 gerações, baterias, etc.).
- **GraphDB 10.8**: Banco de grafos semântico / RDF Triplestore (Ontotext). Na inicialização, se o repositório `masIFRS` não existir ou estiver vazio, o serviço cria automaticamente o repositório e carrega a ontologia a partir de `DBs/masIFRS-config.ttl`.
- **Prosody XMPP**: Servidor de mensageria XMPP configurado para auto-registro livre dos agentes SPADE.
- **MAS-IFRS Agentes + Monitor HTTPS**: Container Python 3.12 com SPADE 4.1.4, PyTorch, Chronos, agentes e o Monitor Web com certificado TLS.

---

## 🚀 Como Iniciar

A partir da raiz do projeto ou da pasta `masifrs_spade`:

```bash
# Iniciar todos os serviços em segundo plano (build inicial)
docker compose up -d --build
```

Para acompanhar os logs em tempo real:
```bash
docker compose logs -f masifrs_spade
```

Para parar todos os containers:
```bash
docker compose down
```

---

## 🌐 Portas e Acessos Disponíveis no Host

| Serviço | URL / Porta | Credenciais / Notas |
|---|---|---|
| **Monitor Web (HTTPS)** | [https://localhost:8765](https://localhost:8765) | Interface gráfica dos agentes |
| **GraphDB Workbench** | [http://localhost:7200](http://localhost:7200) | Usuário: `admin` / Senha: `admin` |
| **PostgreSQL** | `localhost:5435` (mapeada para `5432` interna) | Banco: `masifrs` / Usuário: `admin` / Senha: `admin` |
| **XMPP Server (Prosody)** | `localhost:5333` (mapeada para `5222` interna) | Domínio interno: `xmpp` / `localhost` |

> [!NOTE]
> O repositório `masIFRS` e a ontologia `DBs/masIFRS-config.ttl` são carregados automaticamente. Você pode navegar visualmente pelas classes e instâncias semânticas pelo GraphDB Workbench em [http://localhost:7200](http://localhost:7200).

---

## 🛠️ Executar Apenas os Bancos no Docker e Agentes Localmente

Se você preferir rodar os agentes em sua máquina (usando o virtualenv `.venv-spade`) e deixar apenas o PostgreSQL, GraphDB e XMPP no Docker:

1. Suba os serviços de infraestrutura:
   ```bash
   docker compose up -d postgres graphdb xmpp
   ```

2. Execute os agentes localmente:
   ```bash
   cd masifrs_spade
   ./start.sh
   ```
