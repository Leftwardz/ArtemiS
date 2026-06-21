# Architecture Decoupling Plan — ArtemiS

Documento de análise de acoplamentos **pós-refatoração** (Fases A–E concluídas).  
Objetivo: mapear dependências que ainda impedem testes headless, manutenção isolada e evolução da arquitetura.

**Status:** concluído (E1–E6 + A3 legado removido).  
**Relacionado:** `REFACTOR_PLAN.md`, `DECISIONS.md`, `PROJECT_OVERVIEW.md`

---

## Escopo da análise

Foram inspecionados:

- `app/ui/` — janelas, componentes, bootstrap
- `app/services/` — pdf, print, production, designer
- `app/models/` — `DataBase`
- `app/runtime.py`, `ApplicationContext` (pontes `pdf_utils.py`, `utils.py`, `Database.py` **removidas**)
- Fluxos cruzados: produção, remake, designer, config/admin

### O que já está bem desacoplado (baseline positivo)

| Área | Estado |
|------|--------|
| `pdf_service.write_text_to_pdf` | Sem Tkinter; progresso via callbacks opcionais |
| `production_service` (maioria) | Funções puras ou I/O de filesystem; `db` injetado por parâmetro |
| `print_service` (validação/arquivamento) | Sem UI; usa `printer_handler` |
| Organização em `app/ui/*` | Monolito eliminado; responsabilidades por módulo de tela |
| `app/runtime.py` | Substituiu `sys.modules['__main__']` (menos frágil que antes) |

---

## 1. UI ↔ regras de negócio

**Padrão observado:** serviços extraídos existem, mas janelas ainda **orquestram** fluxos completos e decidem erros via `PopUpWindow` / `ConfirmWindow` inline.

| Sintoma | Onde |
|---------|------|
| Validação de fila + busca de WO + decisão de abrir `RemakeWindow` num único método | `app/ui/main_app.py` → `App.search_work` (~80 linhas) |
| Import/export de produto com parsing JSON, confirmação e persistência misturados | `app/ui/config_window.py` → `ConfigWindow.import_product` |
| Remake: montagem de linhas + validação de impressora + disparo de PDF | `app/ui/remake_window.py` → `btn_start` |
| Designer: validação, save, delete, preview PDF na mesma classe | `app/ui/designer_window.py` → `EditWindow` |

**Impacto:** impossível reutilizar o fluxo de produção/remake/import **sem** instanciar widgets ou simular callbacks Tk.

**Direção recomendada:** camada de **casos de uso** fina (`app/services/` ou `app/use_cases/`) que retornam `Result` / dataclasses (`WorkSearchResult`, `ImportResult`, `RemakeJobPayload`) — UI só renderiza e reage.

---

## 2. UI ↔ banco de dados

**Padrão observado:** UI chama `runtime.db.*` diretamente; serviços recebem `db` como parâmetro, mas a UI **não passa por serviço** em dezenas de pontos.

| Módulo | Chamadas diretas a `runtime.db` (aprox.) |
|--------|------------------------------------------|
| `config_window.py` | ~30 |
| `main_app.py` | ~4 (+ indiretas via `production_service`) |
| `designer_window.py` | ~6 |
| `remake_window.py` | ~3 (`self.db = runtime.db`) |

**Classes admin sem intermediário:** `LoginWindow`, `RegisterWindow`, `ManageGroupWindow`, `ExportProductWindow`, `DuplicateProductWindow` — CRUD e auth inline.

**Impacto:** trocar SQLite por outro backend ou mockar testes exige patch global em `runtime.db`; regras de persistência espalhadas entre UI e `designer_service`.

**Direção recomendada:** repositórios estreitos (`ClientRepository`, `ProductRepository`, `UserRepository`, …) ou consolidar acesso via serviços existentes; UI nunca importa `DataBase` diretamente (exceto bootstrap).

---

## 3. Geração de PDF ↔ widgets / janelas

| Local | Acoplamento |
|-------|-------------|
| `app/ui/main_app.py` | `create_pdf` → `Thread` + `LoadingBarFrame` + callbacks `App.after()` + `finish_print_job` |
| `app/ui/remake_window.py` | `self.master.create_pdf(...)` — pipeline de PDF acoplado à janela pai |
| `app/ui/designer_window.py` | `generate_test_pdf` + `os.startfile('temp/text.pdf')` em `show_pdf` |
| `app/services/designer_service.py` | `serialize_canvas_to_dict(canvas, …)` — API do **Tkinter Canvas** dentro de “serviço” |
| `app/services/pdf_service.py` | Limpo de Tkinter ✅; callbacks são funções genéricas |

**Impacto:** preview do designer e serialização **exigem** Tkinter Canvas; produção exige `App` ou mock de `create_pdf`.

**Direção recomendada:**

- Mover `serialize_canvas_to_dict` para `app/ui/` (adaptador) ou trabalhar só com `list[dict]` no serviço.
- Extrair `PrintJobRunner` (thread + callbacks) fora de `App`.
- `RemakeWindow` recebe callable `start_print_job(payload)` injetado, não `master.create_pdf`.

---

## 4. Variáveis globais

| Local | Variável | Uso |
|-------|----------|-----|
| `app/runtime.py` | `config`, `db` | Escrita em `bootstrap.main()`; leitura em toda UI |
| `app/bootstrap.py` | mutação de `runtime.*` | Side effect na inicialização |

**Impacto:** estado implícito; testes paralelos difíceis; troca de DB em runtime (`save_database_location`) muta global compartilhado.

**Direção recomendada:** objeto `ApplicationContext` (dataclass) criado no bootstrap e passado aos construtores das janelas — `runtime.py` vira wrapper temporário até migração completa.

---

## 5. Métodos multi-subsistema

| Método | Subsistemas tocados |
|--------|---------------------|
| `App.search_work` | UI widgets, filesystem, `production_service`, `runtime.db`, `PopUpWindow`, `RemakeWindow` |
| `App.create_pdf` | UI progress, threading, `pdf_service`, `runtime.config`, print pós-processo |
| `App.open_or_print_pdf` | UI progress, `print_service`, filesystem |
| `RemakeWindow.btn_start` | `runtime.db`, `print_service`, `production_service`, `App.create_pdf` |
| `ConfigWindow.save_database_location` | UI, `config.json`, `runtime.config`, `DataBase` recreate, navegação |
| `EditWindow.save_changes` | Canvas, `designer_service`, `runtime.db`, popups, refresh de `ConfigWindow` |
| `finish_print_job` | PDF path, impressora física / `os.startfile`, arquivamento CSV |

---

## 6. Classes com múltiplas responsabilidades

| Classe | Linhas (aprox.) | Responsabilidades misturadas |
|--------|-----------------|------------------------------|
| `EditWindow` | ~1.490 | Editor gráfico, histórico undo, persistência, delete, preview PDF, navegação |
| `ListOfPropertiesWindow` | ~500 | Painel de propriedades + manipulação direta do canvas pai |
| `ConfigWindow` | ~350 | CRUD clientes/produtos, paths, impressoras, grupos, atalho para editor |
| `App` | ~490 | Fila WO, validação, impressão, login entry, progresso paralelo |
| `DataBase` | ~350 | Clientes, produtos, desenhos, usuários, auth, impressoras, grupos |

Arquivo `config_window.py` concentra **7 classes** (config, login, registro, export, duplicate, grupos, add client).

---

## 7. Lógica não reutilizável sem GUI

| Capacidade | Bloqueio atual |
|------------|----------------|
| Buscar e validar WO na fila | `App.search_work` + popups |
| Remake parcial | `RemakeWindow` + `App.create_pdf` |
| Salvar produto / desenhos | `EditWindow` + Canvas Tk |
| Import/export JSON | `ConfigWindow` + diálogos de arquivo |
| Gerar PDF de produção | Callbacks amarrados a `LoadingBarFrame` / `App.after` |
| Preview PDF do designer | `show_pdf` + `os.startfile` |
| Login / registro | Janelas modais sem serviço testável isolado |

**Exceção reutilizável hoje (CLI/script):** funções isoladas em `production_service` (`validate_queue_consistency`, `normalize_group_flag`, …) e `write_text_to_pdf` **se** callbacks forem no-op.

---

## Tabela consolidada de acoplamentos

| Local | Tipo de Problema | Gravidade | Recomendação |
|-------|------------------|-----------|--------------|
| `app/services/designer_service.py` → `serialize_canvas_to_dict` | Serviço depende de widget Tk (`Canvas`) | **Crítica** | Mover para adaptador em `app/ui/`; serviço aceitar apenas `list[dict]` / DTO `Drawing` |
| `app/ui/main_app.py` → `App.search_work` | UI orquestra regra de negócio + mensagens | **Alta** | Extrair `search_and_enqueue_work(...)` retornando `Result`; UI só exibe erros |
| `app/ui/config_window.py` (geral) | UI → DB direto (~30 chamadas `runtime.db`) | **Alta** | Rotear CRUD/auth via serviços ou repositórios; proibir `runtime.db` na UI |
| `app/ui/remake_window.py` → `btn_start` | UI + DB + impressão + `master.create_pdf` | **Alta** | `RemakeService.build_job(...)` + injetar `start_print_job` callable |
| `app/ui/main_app.py` → `create_pdf` / `open_or_print_pdf` | UI + thread + PDF + pós-impressão | **Alta** | `PrintJobCoordinator` em serviço; `App` só registra callbacks visuais |
| `app/ui/designer_window.py` → `EditWindow` | Classe god (editor + persistência + preview) | **Alta** | Dividir: `CanvasEditor`, `ProductDesignerController`, janela fina |
| `app/models/database_manager.py` → `DataBase` | God object (6+ agregados) | **Alta** | Repositórios por agregado (incremental); manter fachada `DataBase` temporária |
| `app/ui/config_window.py` → `save_database_location` | UI + JSON + troca global de DB | **Alta** | `SettingsService.persist_database_path()`; UI só confirma e fecha |
| `app/runtime.py` | Estado global `config` / `db` | **Média** | `ApplicationContext` injetado; deprecar módulo global |
| `app/ui/designer_window.py` → `ListOfPropertiesWindow` | Filha manipula canvas do `master` | **Média** | `CanvasDocument` compartilhado com API estável, não referência à janela |
| `app/ui/config_window.py` → `import_product` | Negócio + confirmação + DB inline | **Média** | `ImportProductUseCase` com `ImportResult` enum |
| `app/services/production_service.py` → `get_drawings_and_orientations` | Índice CSV frágil `file[0][1][0]` | **Média** | Parser tipado; validação de schema CSV centralizada |
| `app/services/designer_service.py` (funções com `db`) | Serviço acoplado ao ORM concreto | **Média** | Protocol/Interface mínima ou repositório de produto |
| `app/services/print_service.py` → `finish_print_job` | `os.startfile` (Windows) + arquivamento | **Média** | Port `DocumentDelivery` (abrir/imprimir/mover) |
| `app/ui/designer_window.py` → `show_pdf` | Preview acoplado a path fixo + shell OS | **Média** | Serviço retorna path; UI decide abrir; path configurável |
| `app/ui/main_app.py` | Import via ponte `pdf_utils` | **Baixa** | Import direto de `app.services.pdf_service` |
| `app/ui/main_app.py` → `LoadingBarFrame` | UI aloca slot `exe_index` do PDFtoPrinter | **Baixa** | `PrintSlotPool` no `print_service` |
| `app/ui/components/list_box.py` | `command=self.focus` → `master.refresh` | **Baixa** | Callback opcional `on_selection_change` explícito |
| `app/ui/config_window.py` | 7 classes no mesmo módulo | **Baixa** | Submodules: `login.py`, `export.py`, … (organização, não comportamento) |
| `app/utils/printer_handler.py` | Dependência Windows (`win32print`) | **Baixa** | Documentar plataforma; interface stub para dev/teste off-line |
| `pdf_utils.py` / `utils.py` / `Database.py` | Pontes legadas ainda importáveis | **Baixa** | ~~A3: remover pontes após grep zero usages~~ ✅ removido |
| `app/services/pdf_service.py` → `generate_test_pdf` | Escreve em `temp/text.pdf` fixo | **Baixa** | Path via parâmetro / diretório configurável |

---

## Plano de desacoplamento proposto (não executar ainda)

Ordem sugerida por **impacto / risco**, alinhada ao estilo incremental do projeto.

### Fase E1 — Corrigir inversão serviço ↔ UI (designer)

| ID | Ação | Risco |
|----|------|-------|
| E1.1 | Mover `serialize_canvas_to_dict` para `app/ui/designer_canvas_adapter.py` | Baixo |
| E1.2 | `designer_service` persistir só `list[dict]`; testes unitários do dict↔DB | Médio |

### Fase E2 — Casos de uso de produção e remake

| ID | Ação | Risco |
|----|------|-------|
| E2.1 | `WorkQueueService.search_work(...)` → `WorkSearchResult` | Médio |
| E2.2 | `RemakeService.prepare_partial_job(...)` → payload para PDF | Médio |
| E2.3 | `PrintJobCoordinator.run(...)` extrair thread/callbacks de `App` | Médio |

### Fase E3 — Remover DB da UI

| ID | Ação | Risco |
|----|------|-------|
| E3.1 | `config_window`: auth e CRUD via serviços | Alto (muitos pontos) |
| E3.2 | `remake_window` / `designer_window`: eliminar `runtime.db` | Médio |
| E3.3 | `SettingsService` para `config.json` + troca de DB | Médio |

### Fase E4 — Estado da aplicação

| ID | Ação | Risco |
|----|------|-------|
| E4.1 | Introduzir `ApplicationContext`; bootstrap popula e injeta | Médio |
| E4.2 | Deprecar `app/runtime.py` após migração | Baixo | ✅ aliases `config`/`db` removidos; usar `runtime.context` |

### Fase E5 — Modelo de dados (opcional, longo prazo)

| ID | Ação | Risco |
|----|------|-------|
| E5.1 | Fatias de `DataBase` em repositórios por agregado | Alto |
| E5.2 | Parser CSV robusto em `production_service` | Médio |

### Fase E6 — Higiene

| ID | Ação | Risco |
|----|------|-------|
| E6.1 | A3: eliminar pontes `pdf_utils`, wildcards | Baixo | ✅ |
| E6.2 | Abstrair `os.startfile` / impressão para testes | Baixo |

---

## Critérios de aceite (quando executar)

- [x] Nenhum módulo em `app/services/` importa `tkinter` / `customtkinter`
- [x] Nenhum arquivo em `app/ui/` chama `runtime.db` diretamente
- [x] `write_text_to_pdf` invocável via script com callbacks no-op
- [x] `serialize_canvas_to_dict` removido de `designer_service`
- [ ] `validate_queue_consistency` e fluxo de enqueue cobertos por teste sem GUI (testes não solicitados)
- [x] Pontes raiz `Database.py`, `utils.py`, `pdf_utils.py` eliminadas
- [x] Estado via `runtime.context` (sem aliases `runtime.config` / `runtime.db`)

---

## Fase A3 — Remoção de legado (2026-06-20)

| ID | Ação | Status |
|----|------|--------|
| A3.1 | Remover `Database.py`, `utils.py`, `pdf_utils.py` | ✅ |
| A3.2 | Imports diretos `app.models.database_manager` no bootstrap/settings | ✅ |
| A3.3 | `runtime.context` exclusivo; UI usa `settings_service` / `admin_service` | ✅ |
| A3.4 | Aliases legados removidos de `admin_service` | ✅ |

---

## Referências cruzadas

| Documento | Uso |
|-----------|-----|
| `REFACTOR_PLAN.md` | Histórico do que já foi feito (A–E) |
| `DECISIONS.md` | Registrar decisões E1–E6 ao executar |
| `PROJECT_OVERVIEW.md` | Bugs funcionais (CSV, PDF rotação) — separados deste plano estrutural |
