# Plano de Refatoração — ArtemiS

Documento permanente de acompanhamento da modularização incremental do projeto.  
Para contexto funcional do sistema, consulte também `PROJECT_OVERVIEW.md`.  
Para decisões arquiteturais registradas, consulte `DECISIONS.md`.

**Última atualização:** 2026-06-20 (Fases A1–C1, D1 e D2 concluídas)

---

## Estado Atual

O ArtemiS continua sendo uma aplicação desktop monolítica em Python (CustomTkinter/Tkinter), com ponto de entrada em `Main.py` (~2.678 linhas, 22 classes). A refatoração seguiu a estratégia de **extração incremental + pontes de compatibilidade**, sem reescrever o monolito de uma vez.

### Arquitetura em camadas (estado real)

```
Main.py                          ← UI completa + bootstrap + orquestração de produção
├── Database.py                  ← ponte → app/models/
├── utils.py                     ← ponte → app/utils/
├── pdf_utils.py                 ← ponte → app/services/pdf_service.py
└── app/
    ├── models/                  ← SQLAlchemy schema + DataBase (concluído)
    ├── utils/                   ← CSV, barcodes, impressora, geometria (concluído)
    ├── services/
    │   ├── pdf_service.py       ← geração ReportLab (desacoplado da UI via callbacks)
    │   ├── print_service.py     ← pós-impressão, validação de papel, arquivamento
    │   └── production_service.py← fila de WO, validações, payload de produção/remake
    │   └── designer_service.py  ← validação, serialização canvas, import/export JSON
    ├── controllers/             ← vazio (placeholder)
    └── ui/
        ├── constants.py         ← ícone, fontes, cores de botão
        └── components/          ← Table, ListBox, SpinBox, Tooltip, PopUpWindow, ConfirmWindow
```

### Globals e bootstrap

- `config` e `db` são instanciados no bloco `if __name__ == "__main__"` de `Main.py`.
- `Main.py` importa serviços de `app.services` para produção/impressão; demais imports ainda usam wildcards legados.
- PyInstaller (`Main.spec`) aponta para `Main.py` como entry point.

### Acoplamento remanescente

- `App.create_pdf` e `LoadingBarFrame` permanecem na UI — adaptadores finos entre serviços e widgets.
- `EditWindow`: canvas e interação gráfica permanecem na UI; persistência/serialização delegadas a `designer_service`.
- Acesso direto ao banco (`db.*`) espalhado nas classes de UI (~99 referências em `Main.py`).

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
| `Database.py` | Ponte de compatibilidade reexportando schema + `DataBase` |

### Etapa 3 — Utilitários ✅

| Arquivo | Conteúdo |
|---------|----------|
| `app/utils/file_parser.py` | `FileUtils`, `get_sequence_from_str` |
| `app/utils/barcode_generator.py` | Code 128/39, QR, DataMatrix, blob |
| `app/utils/printer_handler.py` | `print_pdf_file`, `is_papersize_a4`, etc. |
| `app/utils/window_geometry.py` | Centralização multi-monitor |
| `app/utils/text_utils.py` | `break_line` |
| `utils.py` | Ponte de compatibilidade |

### Etapa 4 — Serviços ✅

| Item | Status |
|------|--------|
| `app/services/pdf_service.py` | ✅ Geração ReportLab; desacoplado da UI via callbacks |
| `app/services/print_service.py` | ✅ Pós-impressão, validação de papel, arquivamento em `Old/` |
| `app/services/production_service.py` | ✅ Fila de WO, validações, payload de produção/remake |
| Ponte `pdf_utils.py` | ✅ Reexportador |
| Imports diretos parciais em `Main.py` | 🔄 Serviços importados; utils/Database/pdf_utils ainda via wildcard |

### Fase B — Orquestração de produção ✅

- **`production_service.py`** — busca de WO, validação de fila, montagem de linhas/orientações, remake parcial.
- `App.search_work`, `btn_start`, `open_or_print_pdf` e `RemakeWindow` delegam aos serviços.

---

## O que ainda está pendente

### Fase A — Concluir serviços (restante)

- **A3:** (Opcional) Migrar imports restantes de `Main.py` para `app.*` de forma explícita (utils, Database, pdf_utils).

### ~~Fase B — Orquestração de produção~~ ✅ Concluída

~~**B1:** Criar `app/services/production_service.py`~~ — implementado.

### Fase C — Lógica do designer ✅

- **`designer_service.py`** — validação de produto, serialização canvas↔dict, import/export JSON, duplicação.
- `EditWindow`, `ConfigWindow.import_product`, `ExportProductWindow` e `DuplicateProductWindow` delegam ao serviço.

### Fase D — Organização da UI (Etapa 6 original, reordenada)

1. **`app/ui/components/`** ✅ — widgets reutilizáveis (`Table`, `ListBox`, `SpinBox`, `Tooltip`, popups).
2. **`app/ui/remake_window.py`** ✅ — `RemakeWindow`
3. **`app/ui/main_app.py`** — `App` + `LoadingBarFrame` ← **PRÓXIMO (D3)**.
4. `app/ui/designer_window.py` — `EditWindow` + janelas auxiliares do designer.
5. `app/ui/config_window.py` — `ConfigWindow` + janelas admin (login/registro inclusos na UI, sem módulo auth separado).
6. Bootstrap — `main.py` na raiz; atualizar `Main.spec`.

### Fase E — Infraestrutura transversal (não bloqueante)

- Injeção de `db` e `config` (eliminar globals implícitos).
- Corrigir vazamentos de sessão DB em métodos de impressoras/grupos (documentado em `PROJECT_OVERVIEW.md`).
- Controle de privilégios de usuário — somente se houver requisito funcional futuro.

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
| UI (widgets, estados) | `App` |
| I/O filesystem, validação de fila | `production_service` + `App.search_work` (UI de popups) |
| Orquestração de impressão (thread) | `App.create_pdf` (adaptador) |
| Pós-processamento (mover CSV para `Old/`) | `print_service.finish_print_job` |
| Acesso direto ao banco | Espalhado em `App`, `RemakeWindow`, `ConfigWindow`, `EditWindow` |

### ~~`print_service.py` incompleto~~ ✅ Resolvido (A2)

`finish_print_job`, `validate_printer_paper` e `get_printer_paper_error_message` centralizam pós-impressão. `LoadingBarFrame` permanece na UI e passa `exe_index` ao serviço.

### Globals `db` / `config`

Serviços extraídos herdarão dependência implícita até a fase de bootstrap. Aceitável nas Fases A–C; resolver na Fase D/E.

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

### D3 — Migrar `App` + `LoadingBarFrame` para `app/ui/main_app.py` ← **PRÓXIMO PASSO**

| Campo | Detalhe |
|-------|---------|
| **Objetivo** | Extrair de `EditWindow` / import-export: validação de nome de produto, serialização canvas↔dict↔banco, import/export JSON com Base64. |
| **Benefício** | Segundo maior bloco de lógica (~1.500 linhas de designer) preparado para migração de UI. |
| **Risco** | Médio — serialização de canvas é frágil; testar save/load e import/export. |
| **Dependências** | Recomendado após B1 ✅. |

---

### D — Migrar UI para `app/ui/`

| Campo | Detalhe |
|-------|---------|
| **Objetivo** | Mover classes de `Main.py` para módulos em `app/ui/` na ordem: components → remake → main → designer → config; criar bootstrap `main.py`. |
| **Benefício** | `Main.py` deixa de ser monolito; entry point claro. |
| **Risco** | Alto se feito antes das Fases A–C (move acoplamento junto); baixo/médio se feito depois. |
| **Dependências** | A1 ✅, A2 ✅, B1 ✅, C1 (recomendado). Atualizar `Main.spec`. |

---

## Ordem de Execução Recomendada

```
A1  Desacoplar pdf_service (callbacks)           ✅
A2  Completar print_service                      ✅
B1  production_service                            ✅
C1  designer_service                              ✅
D1  app/ui/components                             ✅
D2  app/ui/remake_window                          ✅
D3  app/ui/main_app                               ← PRÓXIMO
D4  app/ui/designer_window
D5  app/ui/config_window
D6  bootstrap main.py + Main.spec
E   Infraestrutura (injeção db/config, bugs DB)
A3  Limpar imports (opcional, a qualquer momento)
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
