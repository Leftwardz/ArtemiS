# Auditoria / Logs (módulo `app/audit/`)

Sistema de logs/auditoria local-first com agregação central e visão global,
projetado para ambiente multi-PC (até ~30 estações) com SQLite em pasta de
rede, sem interferir na impressão e sem migrar/alterar o banco de produção.

## Princípios

- Local-first: cada PC grava em um SQLite local dedicado (fonte da verdade).
- Best-effort: a chamada de log apenas enfileira (O(1)) e nunca bloqueia nem
  levanta exceção; o caminho de impressão jamais é afetado.
- Isolado: usa `sqlite3` puro, arquivos e conexões próprios. Não toca no banco
  de produção (sem migração, sem risco de quebrar o sistema atual).
- Agregação: uma thread copia em lote os eventos locais para um SQLite central
  na rede (visão global), tolerante a falhas de rede.

## Fluxo

```mermaid
flowchart LR
    App[ArtemiS] -->|log_*  O(1)| Q[Fila em memoria]
    Q --> W[Worker thread]
    W -->|escrita local| L[(audit_local.db)]
    W -.fallback.-> J[audit_fallback.jsonl]
    Agg[Aggregator thread] -->|le nao sincronizados| L
    Agg -->|INSERT OR IGNORE em lote| C[(central na rede)]
    UI[Tela Auditoria] -->|somente leitura| C
```

## Arquivos

| Arquivo | Papel |
|---|---|
| `app/audit/schema.py` | DDL da tabela `audit_events`, colunas, defaults. |
| `app/audit/paths.py` | Caminhos local (`%LOCALAPPDATA%\\ArtemiS\\audit`) e central. |
| `app/audit/store.py` | sqlite3 puro: connect (pragmas), insert, fetch, prune, query. |
| `app/audit/logger.py` | `AuditLogger`: fila + worker thread + fallback JSONL. |
| `app/audit/aggregator.py` | `Aggregator`: flush local→central + prune (retenção). |
| `app/audit/__init__.py` | API: `init_audit`, `shutdown_audit`, `log_*`, `query_events`. |

## Integração (pontos de captura)

- Impressão: `app/services/print_service.py` → `finish_print_job` (sucesso e
  falha; `Criar PDF` registra `create_pdf`).
- Acesso à config: `app/ui/main_app.py` → `open_toplevel` (concedido/negado).
- Cadastros: `app/services/admin_service.py` (impressoras, acessos, grupos,
  clientes).
- Erros: `app/ui/main_app.py` → `LoadingBarFrame.show_error`.
- Ciclo de vida: `app/bootstrap.py` chama `init_audit(config)` e
  `shutdown_audit()` (também via `atexit`).

## Tabela `audit_events`

`id` (uuid), `ts_utc`, `ts_local`, `pc_name`, `windows_user`, `category`
(`print|config_access|cadastro|error`), `action`, `printer`, `product`,
`backend`, `paper_size`, `copies`, `success`, `detail` (trunc. 2000), `app_version`,
`synced` (controle local). Índices em ts/usuário/impressora/categoria/synced.

## Concorrência e segurança

- Local: escritor único (worker), WAL + `busy_timeout=5000` (disco local).
- Central: `journal_mode=DELETE` (WAL é inseguro em SMB), `busy_timeout=30000`,
  transações curtas, `INSERT OR IGNORE` idempotente por uuid, retry no próximo
  ciclo se a rede falhar.
- Central é store derivado: se corromper, reconstrói a partir dos locais.

## Configuração (`config.json`)

| Chave | Default | Descrição |
|---|---|---|
| `audit_enabled` | `true` | Liga/desliga a auditoria. |
| `audit_central_location` | `""` | Caminho do SQLite central; vazio = mesma pasta do banco de produção (`artemis_audit_central.db`). |
| `audit_flush_interval_seconds` | `180` | Intervalo de agregação local→central. |
| `audit_retention_days` | `180` | Retenção (~6 meses) no central. |

## Consulta

Configurações → "Auditoria / Logs": filtros por data, usuário, impressora e
categoria; lê o banco central (visão global de todos os PCs). A visibilidade
global é assíncrona (aparece após o flush, não em tempo real).

## O que NÃO é registrado

Conteúdo do PDF, payload de layout, leituras de layout, eventos de UI de alta
frequência, segredos. `detail`/stack são truncados.

## Evolução futura

Trocar o sink central por um serviço coletor (HTTP/named pipe) ou Postgres/SQL
Server: os PCs seguem local-first; muda apenas o destino do flush no
`Aggregator`.
