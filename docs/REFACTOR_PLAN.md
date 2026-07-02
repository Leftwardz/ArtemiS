# Plano de Refatoração — ArtemiS

Documento permanente de acompanhamento da modularização incremental do projeto.  
Para contexto funcional do sistema, consulte também `PROJECT_OVERVIEW.md`.  
Para decisões arquiteturais registradas, consulte `DECISIONS.md`.

**Última atualização:** 2026-06-20 (Fases A1–E, D1–D6, E1–E6 e A3 concluídas)

---

## Estado Atual

O ArtemiS é uma aplicação desktop em Python (CustomTkinter/Tkinter). Entry point: `main.py` (PyInstaller `Main.spec`); `Main.py` permanece como shim de compatibilidade.

### Arquitetura em camadas (estado real)

```
main.py / Main.py                ← entry → app/bootstrap.py
└── app/
    ├── bootstrap.py             ← config.json, DataBase, App.mainloop()
    ├── runtime.py               ← ApplicationContext (runtime.context)
    ├── application_context.py
    ├── models/                  ← SQLAlchemy schema + DataBase (concluído)
    ├── utils/                   ← CSV, barcodes, impressora, geometria, document_delivery
    ├── services/
    │   ├── pdf_service.py
    │   ├── print_service.py
    │   ├── production_service.py
    │   ├── designer_service.py
    │   ├── work_queue_service.py
    │   ├── remake_service.py
    │   ├── print_job_coordinator.py
    │   ├── admin_service.py
    │   └── settings_service.py
    ├── controllers/             ← vazio (placeholder)
    └── ui/
        ├── constants.py
        ├── components/
        ├── remake_window.py
        ├── main_app.py
        ├── designer_window.py
        └── config_window.py
```

Pontes raiz **`Database.py`**, **`utils.py`** e **`pdf_utils.py`** foram **removidas** (A3).

### Globals e bootstrap

- `ApplicationContext` (`config`, `db`) vive em `runtime.context`, inicializado por `app/bootstrap.py`.
- Serviços (`admin_service`, `settings_service`) leem/mutam via `runtime.context`.
- `main.py` / `Main.py` delegam para `app.bootstrap.main()`.
- PyInstaller (`Main.spec`) aponta para `main.py`.

### Acoplamento remanescente

- UI acessa config via `settings_service`; dados via `admin_service.get_db()` injetado nos serviços.
- `DataBase` permanece god object (repositórios — longo prazo).

---

## O que já foi concluído

### Etapa 1 — Preparação de estrutura ✅

- Diretórios `app/ui`, `app/controllers`, `app/services`, `app/models`, `app/utils`.
- Pacotes inicializados com `__init__.py`.

### Etapa 2 — Modelos de banco de dados ✅

| Arquivo | Conteúdo |
|---------|----------|
| `app/models/schema.py` | Entidades SQLAlchemy: `Client`, `Product`, `Drawing`, `User`, `Printer`, `PrintingGroup` |
| `app/models/database_manager.py` | Classe `DataBase` — CRUD, desenhos, usuários, impressoras, grupos |

~~`Database.py`~~ — ponte removida (A3).

### Etapa 3 — Utilitários ✅

| Arquivo | Conteúdo |
|---------|----------|
| `app/utils/file_parser.py` | `FileUtils`, `get_sequence_from_str` |
| `app/utils/barcode_generator.py` | Code 128/39, QR, DataMatrix, blob |
| `app/utils/printer_handler.py` | `print_pdf_file`, `is_papersize_a4`, etc. |
| `app/utils/window_geometry.py` | Centralização multi-monitor |
| `app/utils/text_utils.py` | `break_line` |

~~`utils.py`~~ — ponte removida (A3).

### Etapa 4 — Serviços ✅

| Item | Status |
|------|--------|
| `app/services/pdf_service.py` | ✅ Geração ReportLab; desacoplado da UI via callbacks |
| `app/services/print_service.py` | ✅ Pós-impressão, validação de papel, arquivamento em `Old/` |
| `app/services/production_service.py` | ✅ Fila de WO, validações, payload de produção/remake |
| Imports explícitos `app.*` | ✅ Sem pontes raiz (A3) |

### Fase B — Orquestração de produção ✅

- **`production_service.py`** — busca de WO, validação de fila, montagem de linhas/orientações, remake parcial.
- `App.search_work`, `btn_start`, `open_or_print_pdf` e `RemakeWindow` delegam aos serviços.

---

## O que ainda está pendente

### ~~Fase A — Concluir serviços (restante)~~ ✅ Concluída

- ~~**A3:** Migrar imports e remover pontes legadas~~ — concluído.

### ~~Fase B — Orquestração de produção~~ ✅ Concluída

~~**B1:** Criar `app/services/production_service.py`~~ — implementado.

### Fase C — Lógica do designer ✅

- **`designer_service.py`** — validação de produto, serialização canvas↔dict, import/export JSON, duplicação.
- `EditWindow`, `ConfigWindow.import_product`, `ExportProductWindow` e `DuplicateProductWindow` delegam ao serviço.

### Fase D — Organização da UI (Etapa 6 original, reordenada)

1. **`app/ui/components/`** ✅ — widgets reutilizáveis (`Table`, `ListBox`, `SpinBox`, `Tooltip`, popups).
2. **`app/ui/remake_window.py`** ✅ — `RemakeWindow`
3. **`app/ui/main_app.py`** ✅ — `App` + `LoadingBarFrame`
4. **`app/ui/designer_window.py`** ✅ — `EditWindow`, `ListOfPropertiesWindow`, `GetImageWindow`, `GetTextWindow`, `GetBarcodeWindow`, `GetSegmentWindow`
5. **`app/ui/config_window.py`** ✅ — `ConfigWindow`, login/registro, import/export, grupos
6. Bootstrap — `main.py` + `Main.spec` ✅

### ~~Fase E — Infraestrutura transversal~~ ✅ Concluída

- **`app/runtime.py`** — `config` e `db` centralizados; bootstrap inicializa; UI deixa de usar `sys.modules['__main__']`.
- **Sessões DB** — métodos de impressoras/grupos em `database_manager.py` já fecham sessão (corrigido na migração para `app/models`).

### Explicitamente fora do escopo atual

- ~~`auth_controller.py`~~ — não criar (decisão registrada em `DECISIONS.md`).
- Controladores criados apenas para seguir padrão MVC.
- Reescrita completa de `Main.py`.

---

## Problemas Identificados

### ~~Acoplamento serviço → UI~~ ✅ Resolvido (A1)

`pdf_service.py` usa callbacks (`on_progress`, `on_error`, `on_complete`). `App.create_pdf` adapta callbacks para `LoadingBarFrame` via `App.after()`.

### Responsabilidades misturadas em `App` (parcialmente resolvido)

| Responsabilidade | Onde está hoje |
|------------------|----------------|
| UI (widgets, estados) | `app/ui/main_app.py` (`App`, `LoadingBarFrame`) |
| I/O filesystem, validação de fila | `production_service` + `App.search_work` (UI de popups) |
| Orquestração de impressão (thread) | `App.create_pdf` em `main_app.py` (adaptador) |
| Pós-processamento (mover CSV para `Old/`) | `print_service.finish_print_job` |
| Acesso direto ao banco | `app.runtime.db` nos módulos UI |

### ~~`print_service.py` incompleto~~ ✅ Resolvido (A2)

`finish_print_job`, `validate_printer_paper` e `get_printer_paper_error_message` centralizam pós-impressão. `LoadingBarFrame` permanece na UI e passa `exe_index` ao serviço.

### ~~Globals `db` / `config`~~ ✅ Resolvido (E)

Estado compartilhado em `app/runtime.py`; bootstrap atribui após carregar `config.json`.

### Bugs conhecidos (referência)

Documentados em `PROJECT_OVERVIEW.md` — rotação de imagens no PDF, vazamento de sessões DB, `pywintypes` não importado em `utils.py`, validação de coluna CSV desativada, duplicação de segmentos desabilitada no editor.

---

## Próximas Etapas Recomendadas

### ~~A1 — Desacoplar `pdf_service` da UI via callbacks~~ ✅ Concluído

### ~~A2 — Completar `print_service`~~ ✅ Concluído

### ~~B1 — Criar `production_service`~~ ✅ Concluído

### A3 — Limpar imports (opcional)

| Campo | Detalhe |
|-------|---------|
| **Objetivo** | Substituir wildcards por imports explícitos de `app.*` em `Main.py`. |
| **Benefício** | Dependências visíveis; facilita navegação. |
| **Risco** | Baixo. |
| **Dependências** | Nenhuma bloqueante. |

---

### ~~C1 — Criar `designer_service`~~ ✅ Concluído

### ~~D1 — Migrar componentes para `app/ui/components/`~~ ✅ Concluído

### ~~D2 — Migrar `RemakeWindow`~~ ✅ Concluído

### ~~D3 — Migrar `App` + `LoadingBarFrame` para `app/ui/main_app.py`~~ ✅ Concluído

| Campo | Detalhe |
|-------|---------|
| **Objetivo** | Extrair tela principal de produção e barra de progresso paralela. |
| **Benefício** | ~450 linhas removidas de `Main.py`; serviços de produção/impressão co-localizados com a UI que os usa. |
| **Risco** | Médio — `open_toplevel` referencia janelas ainda em `Main.py`; resolvido com import tardio via `sys.modules['__main__']`. |
| **Dependências** | D2 ✅. |

---

### ~~D4 — Migrar `EditWindow` para `app/ui/designer_window.py`~~ ✅ Concluído

| Campo | Detalhe |
|-------|---------|
| **Objetivo** | Extrair designer de templates e janelas auxiliares (propriedades, texto, imagem, barcode, segmento). |
| **Benefício** | ~1.446 linhas removidas de `Main.py`; imports de barcode/text utils explícitos no módulo do designer. |
| **Risco** | Médio — canvas e serialização frágeis; testar save/load, visualizar PDF e inserção de elementos. |
| **Dependências** | C1 ✅, D3 ✅. |

---

### ~~D5 — Migrar `ConfigWindow` e admin para `app/ui/config_window.py`~~ ✅ Concluído

| Campo | Detalhe |
|-------|---------|
| **Objetivo** | Extrair configurações, login/registro, import/export e gestão de grupos. |
| **Benefício** | `Main.py` reduzido a bootstrap (~35 linhas). |
| **Risco** | Médio — troca de caminho do DB recria `runtime.db` no módulo `__main__`. |
| **Dependências** | D4 ✅. |

---

### ~~D6 — Criar `main.py` e atualizar `Main.spec`~~ ✅ Concluído

| Campo | Detalhe |
|-------|---------|
| **Objetivo** | Entry point dedicado; `Main.py` como shim. |
| **Benefício** | Separação clara bootstrap vs compatibilidade; build PyInstaller usa `main.py`. |
| **Risco** | Baixo — `main()` publica `config`/`db` em `sys.modules['__main__']`. |
| **Dependências** | D5 ✅. |

---

### ~~Fase E — Infraestrutura transversal~~ ✅ Concluída

| Campo | Detalhe |
|-------|---------|
| **Objetivo** | Centralizar `config`/`db`; eliminar `_runtime()` / `__main__`. |
| **Benefício** | Imports explícitos; compatível com Windows (`main.py` = `Main.py`). |
| **Risco** | Baixo. |
| **Dependências** | D6 ✅. |

---

### A3 — Limpar imports (opcional)

| Campo | Detalhe |
|-------|---------|
| **Objetivo** | Substituir wildcards restantes (`pdf_utils`, pontes legadas) por imports explícitos de `app.*`. |
| **Benefício** | Dependências visíveis; facilita navegação. |
| **Risco** | Baixo. |
| **Dependências** | Nenhuma bloqueante. |

---

## Ordem de Execução Recomendada

```
A1  Desacoplar pdf_service (callbacks)           ✅
A2  Completar print_service                      ✅
B1  production_service                            ✅
C1  designer_service                              ✅
D1  app/ui/components                             ✅
D2  app/ui/remake_window                          ✅
D3  app/ui/main_app                               ✅
D4  app/ui/designer_window                    ✅
D5  app/ui/config_window                      ✅
D6  bootstrap main.py + Main.spec             ✅
E   Infraestrutura (app/runtime.py)              ✅
A3  Limpar imports (opcional)
```

### Casos de teste manuais obrigatórios após A1/A2/B1

- Lote normal com impressora física.
- Opção "Criar PDF".
- Remake parcial via `RemakeWindow`.
- Remake com checkbox "Não Utilizar Tela Secundária".
- Múltiplas WOs na fila (mesma cor e tamanho de papel).
- Rejeição de WO com cor ou tamanho divergente.

---

## Referência cruzada

| Documento | Conteúdo |
|-----------|----------|
| `docs/Tasks.md` | Checklist original (parcialmente superseded por este plano) |
| `docs/DECISIONS.md` | Decisões arquiteturais e revisões do plano original |
| `docs/AI_CONTEXT.md` | Guia para IAs que continuarem o trabalho |
| `docs/PROJECT_OVERVIEW.md` | Funcionalidades, fluxos e bugs conhecidos do produto |
