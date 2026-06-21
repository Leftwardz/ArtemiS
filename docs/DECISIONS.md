# Decisões Arquiteturais — ArtemiS

Registro permanente de decisões tomadas durante a refatoração incremental.  
Consulte `REFACTOR_PLAN.md` para o plano de execução atual e `AI_CONTEXT.md` para o processo de trabalho.

**Última atualização:** 2026-06-20 (Fases A1–C1 e D1 implementadas)

---

## Como usar este documento

Cada entrada registra uma decisão consciente — não um detalhe de implementação.  
Ao tomar uma nova decisão arquitetural durante a refatoração, adicionar entrada no final com data, motivo e impacto.

---

## D-001 — Refatoração incremental com pontes de compatibilidade

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 (registrado retroativamente; decisão tomada no início da refatoração) |
| **Decisão** | Extrair módulos para `app/` mantendo arquivos raiz (`Database.py`, `utils.py`, `pdf_utils.py`) como reexportadores. Não reescrever `Main.py` de uma vez. |
| **Motivo** | Reduz risco de regressão; permite evolução gradual sem quebrar PyInstaller nem fluxos de produção existentes. |
| **Impacto esperado** | Imports legados continuam funcionando; novos módulos convivem com o monolito até a fase de migração de UI. |

---

## D-002 — Separar modelos antes de UI e serviços

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 (registrado retroativamente) |
| **Decisão** | Ordem de extração: modelos (`app/models`) → utilitários (`app/utils`) → serviços (`app/services`) → orquestração → UI (`app/ui`). |
| **Motivo** | Camadas inferiores têm menos dependências de Tkinter; extraí-las primeiro estabiliza a base. |
| **Impacto esperado** | Etapas 1–3 concluídas com sucesso; `DataBase` e utilitários já utilizáveis independentemente da UI. |

---

## D-003 — Não criar `auth_controller` neste momento

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Eliminar `auth_controller.py` do plano. Login e registro permanecem nas classes de UI (`LoginWindow`, `RegisterWindow`) chamando `DataBase` diretamente. |
| **Motivo** | Auth atual é fina (~100 linhas): validação mínima de tamanho de senha + chamadas a `db.verify_user()` / `db.register_user()`. Coluna `privileges` existe no banco mas não é verificada em nenhum fluxo. Um controlador seria pass-through sem regra de domínio. |
| **Impacto esperado** | Menos arquivos artificiais; auth só ganha camada própria se surgir requisito de sessão, expiração ou controle de privilégios. |

---

## D-004 — Evitar camadas artificiais / controladores por padrão MVC

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Não criar controladores apenas para seguir padrão arquitetural. Criar módulos somente onde há responsabilidade de domínio observável no código. Preferir `app/services/` para orquestração. |
| **Motivo** | Análise do código mostrou que `auth_controller` e um `print_controller` separado seriam wrappers vazios. O diretório `app/controllers/` permanece placeholder até haver necessidade real. |
| **Impacto esperado** | Plano revisado substitui "Etapa 5 — 4 controladores" por serviços de orquestração concretos (`production_service`, `designer_service`). |

---

## D-005 — Substituir `queue_controller` + `remake_controller` por `production_service`

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Unificar lógica de fila de produção e remake em `app/services/production_service.py`. Remake é modo (flag + subconjunto de linhas), não domínio separado. |
| **Motivo** | `RemakeWindow.btn_start` delega para `master.create_pdf()`. Não há fluxo independente de remake — apenas seleção parcial de linhas sobre o mesmo pipeline de PDF/impressão. |
| **Impacto esperado** | Um serviço cobre `search_work`, validações de fila, montagem de payload e modo remake; evita duplicação entre dois controladores. |

---

## D-006 — Substituir `designer_controller` por `designer_service`

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Extrair lógica do designer para `app/services/designer_service.py` (validação, serialização canvas, import/export JSON), mantendo interação gráfica em `EditWindow`. |
| **Motivo** | `EditWindow` concentra ~700 linhas de canvas **e** persistência/serialização — fronteira natural entre serviço e UI. O termo "service" reflete melhor a natureza da extração do que "controller". |
| **Impacto esperado** | Designer testável sem Tkinter para save/load e import/export; UI migrável depois para `app/ui/designer_window.py`. |

---

## D-007 — Completar serviços antes de migrar UI

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Extrair lógica de negócio (Fases A–C) **antes** de mover classes de `Main.py` para `app/ui/` (Fase D). |
| **Motivo** | Mover ~2.600 linhas de UI sem extrair lógica apenas reorganiza pastas mantendo acoplamento. Diffs enormes dificultam review e rollback. |
| **Impacto esperado** | Etapa 6 original (`app/ui/`) reposicionada para depois de `production_service` e `designer_service`. |

---

## D-008 — Priorizar desacoplamento de `pdf_service` (A1) como primeiro passo

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Próxima implementação: substituir parâmetro `master` em `write_text_to_pdf` por callbacks. Não iniciar migração de UI nem `production_service` antes disso. |
| **Motivo** | Menor refatoração com maior impacto (~15 pontos de acoplamento). Elimina dependência invertida serviço→UI que bloqueia `print_service`, `production_service` e testes isolados. |
| **Impacto esperado** | `pdf_service.py` deixa de importar/referenciar Tkinter; `App.create_pdf` vira adaptador fino. |

---

## D-009 — `LoadingBarFrame` permanece na UI; serviço recebe `exe_index`

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Alocação de slots `PDFtoPrinter.exe` (_1 a _5) e widgets de progresso ficam em `LoadingBarFrame` (UI). `print_service` recebe índice do executável como parâmetro, sem conhecer widgets. |
| **Motivo** | Gerenciamento de slots é estado visual/concorrente ligado à interface; mover para serviço misturaria UI com I/O de impressão de forma diferente. |
| **Impacto esperado** | Fronteira clara: UI aloca slot e exibe progresso; serviço executa impressão e arquivamento. |

---

## D-010 — Manter `Main.py` como entry point até fase bootstrap

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Não alterar entry point do PyInstaller (`Main.spec` → `Main.py`) até a fase D6 (bootstrap `main.py`). |
| **Motivo** | Evitar quebra de build `.exe` durante refatorações intermediárias. |
| **Impacto esperado** | `Main.py` continua executável durante Fases A–C; ponte temporária ou remoção só na fase final. |

---

## D-011 — Callbacks de progresso PDF devem respeitar thread-safety do Tkinter

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Ao implementar A1, adaptador em `App` deve usar `App.after()` para atualizar widgets a partir da thread de `write_text_to_pdf`. |
| **Motivo** | `create_pdf` dispara `Thread(target=write_text_to_pdf)`. Tkinter não é thread-safe; código atual já chama widgets da thread secundária (funciona na prática, mas é frágil). A refatoração é oportunidade de corrigir. |
| **Impacto esperado** | Progresso e erros exibidos de forma segura; reduz riscos de crash intermitente em lotes grandes. |

---

## D-012 — Documentação deve ser atualizada ao final de cada etapa

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Ao concluir qualquer fase do plano, atualizar `REFACTOR_PLAN.md` (progresso) e `DECISIONS.md` (se houver nova decisão). IAs e desenvolvedores devem consultar `AI_CONTEXT.md` antes de alterar código. |
| **Motivo** | Continuidade do trabalho sem depender de histórico de conversa (Cursor, Codex, Antigravity, etc.). |
| **Impacto esperado** | Onboarding instantâneo para qualquer agente ou pessoa no projeto. |

---

## Decisões do plano original revogadas ou adiadas

| Item original (`Tasks.md`) | Status |
|----------------------------|--------|
| `auth_controller.py` | **Revogado** — ver D-003 |
| `remake_controller.py` | **Revogado** — absorvido por `production_service` (D-005) |
| `queue_controller.py` | **Renomeado/reformulado** → `production_service` (D-005) |
| `designer_controller.py` | **Renomeado/reformulado** → `designer_service` (D-006) |
| Migrar UI antes de serviços | **Adiado** — ver D-007 |
| Controle de privilégios de usuário | **Adiado** — aguarda requisito funcional |

---

## D-013 — Implementação das Fases A1, A2 e B1 (2026-06-20)

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Implementar em sequência: callbacks em `pdf_service`, completar `print_service`, criar `production_service` e integrar em `Main.py`. |
| **Motivo** | Executar o plano revisado; maior impacto com risco controlado antes da migração de UI. |
| **Impacto esperado** | Serviços de PDF, impressão e produção desacoplados da UI; `Main.py` reduzido nas áreas de fila e pós-impressão; base pronta para `designer_service` e Fase D. |

### Detalhes da implementação

- **`pdf_service`:** `write_text_to_pdf` recebe `on_progress`, `on_error`, `on_complete`; sem referências a Tkinter.
- **`App.create_pdf`:** adaptador com `App.after()` para thread-safety (D-011 aplicado).
- **`print_service`:** `finish_print_job`, `validate_printer_paper`, `get_printer_paper_error_message`.
- **`production_service`:** busca de WO, validação de fila, carregamento de linhas, orientações, remake parcial.
- **Correção colateral:** se geração falhar sem PDFs completos, não tenta juntar lista vazia.

---

## D-014 — Implementação da Fase C1 (`designer_service`)

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Criar `app/services/designer_service.py` e delegar validação, serialização canvas, import/export e duplicação de produtos. |
| **Motivo** | Segundo maior bloco de lógica de negócio fora da produção; prepara migração do designer para `app/ui/`. |
| **Impacto esperado** | `pass_canvas_to_dict` (~100 linhas) removido de `Main.py`; regras de produto testáveis sem abrir o editor visual. |

### Funções principais

- `validate_product_name`, `serialize_canvas_to_dict`, `save_product_with_drawings`
- `build_export_payload`, `parse_import_file`, funções de import/replace
- `duplicate_product`, `has_unsaved_changes`, `ORIENTATION_LABELS`

---

## D-015 — Extração de componentes UI para `app/ui/components` (D1)

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Mover `Table`, `ListBox`, `SpinBox`, `Tooltip`, `PopUpWindow` e `ConfirmWindow` para `app/ui/components/`. Constantes visuais em `app/ui/constants.py`. |
| **Motivo** | Primeiro passo da Fase D; widgets reutilizáveis sem lógica de negócio, baixo risco, reduz `Main.py`. |
| **Impacto esperado** | ~250 linhas removidas de `Main.py`; janelas futuras importam componentes de um único pacote. |

---

## D-016 — Extração de `RemakeWindow` para `app/ui/remake_window.py` (D2)

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Mover `RemakeWindow` para módulo dedicado; ampliar `app/ui/constants.py` com `PAPER_COLOR_LIST` e dimensões padrão. |
| **Motivo** | Janela relativamente isolada; valida padrão de extração de telas antes de `main_app`. |
| **Impacto esperado** | ~210 linhas removidas de `Main.py`; remake importável independentemente. |

---

## D-017 — Extração de `App` + `LoadingBarFrame` para `app/ui/main_app.py` (D3)

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Mover `App` e `LoadingBarFrame` para `app/ui/main_app.py`; constantes `APP_NAME`, dimensões e cores via `app/ui/constants.py`; acesso a `db`, `config` e janelas admin (`ConfigWindow`, `LoginWindow`, `RegisterWindow`) via helper `_runtime()` → `sys.modules['__main__']`. |
| **Motivo** | Tela principal concentra orquestração de produção já delegada a serviços; extração reduz monolito sem exigir mover login/config antes. |
| **Impacto esperado** | ~450 linhas removidas de `Main.py`; imports de `print_service` e `production_service` saem de `Main.py`. |

---

## D-018 — Extração do designer para `app/ui/designer_window.py` (D4)

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Mover `EditWindow` e janelas auxiliares (`ListOfPropertiesWindow`, `GetImageWindow`, `GetTextWindow`, `GetBarcodeWindow`, `GetSegmentWindow`) para `app/ui/designer_window.py`; ampliar `constants.py` com `FONT_LIST` e `PAPER_SIZE_TIP`; imports explícitos de `barcode_generator`, `text_utils` e `generate_test_pdf`. |
| **Motivo** | Maior bloco de UI restante no monolito; lógica de persistência já delegada a `designer_service` na Fase C1. |
| **Impacto esperado** | ~1.446 linhas removidas de `Main.py`; `pdf_utils` deixa de ser importado em `Main.py`. |

---

## D-019 — Extração de config/admin para `app/ui/config_window.py` (D5)

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Mover `ConfigWindow`, `ManageGroupWindow`, `DuplicateProductWindow`, `ExportProductWindow`, `AddClientWindow`, `RegisterWindow` e `LoginWindow` para `app/ui/config_window.py`; `Main.py` mantém apenas bootstrap e reexport das classes para `sys.modules['__main__']`. |
| **Motivo** | Concluir migração da UI; monolito eliminado exceto entry point. |
| **Impacto esperado** | ~740 linhas removidas de `Main.py`; persistência de `config.json` e recriação de `db` via `_runtime()`. |

---

## D-020 — Bootstrap em `main.py` e shim `Main.py` (D6)

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Criar `main.py` com `main()` que atribui `config` e `db` a `sys.modules['__main__']`; `Main.py` delega para `main()` e reexporta janelas admin; `Main.spec` usa `main.py`. |
| **Motivo** | Entry point explícito sem quebrar quem ainda executa `python Main.py`. |
| **Impacto esperado** | Fase D concluída; monolito eliminado. |

---

## D-021 — Centralizar estado em `app/runtime.py` (Fase E)

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Criar `app/runtime.py` com `config` e `db`; bootstrap inicializa; módulos UI importam `app.runtime` em vez de `sys.modules['__main__']`; `main_app.open_toplevel` importa janelas admin diretamente. |
| **Motivo** | Eliminar acoplamento frágil ao entry point; `main.py`/`Main.py` idênticos no Windows. |
| **Impacto esperado** | Zero referências a `_runtime()`; troca de DB atualiza `runtime.db` explicitamente. |

---

## D-022 — Plano de desacoplamento E1–E6 (2026-06-20)

| Fase | Entrega |
|------|---------|
| E1 | `designer_canvas_adapter.py`; serviço sem Tk Canvas |
| E2 | `work_queue_service`, `remake_service`, `print_job_coordinator` |
| E3 | `admin_service`, `settings_service`; UI sem `runtime.db` |
| E4 | `ApplicationContext` + `runtime.init` / `set_db` |
| E5 | `parse_client_product_from_work_lines` em `production_service` |
| E6 | `document_delivery.open_path`; imports diretos de `pdf_service`; `ListBox.on_select` |

---

## D-024 — Autenticação de configuração via identidade Windows

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-21 |
| **Decisão** | Substituir login/senha interno (`LoginWindow`, `RegisterWindow`, tabela `users`) por verificação da identidade Windows. Administradores locais e de domínio sempre acessam; demais usuários/grupos são cadastrados em `config_access`. Pesquisa AD/local via `app/utils/windows_auth.py`. |
| **Motivo** | Requisito operacional: corporações já gerenciam identidade no Windows/AD; evitar cadastro e senhas duplicadas no ArtemiS. |
| **Impacto esperado** | `admin_service.can_access_config()` substitui `verify_user`/`has_login`; UI ganha `ManageAccessWindow`; tabela `users` legada permanece no SQLite mas não é usada. |

---

## D-025 — Auth Windows com SQLite compartilhado em rede

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-21 |
| **Decisão** | Manter auth de configuração híbrido: **identidade validada localmente** em cada PC (`windows_auth`); **lista `config_access` centralizada** no mesmo SQLite compartilhado usado para layouts. Não replicar auth por senha no banco nem exigir login ArtemiS. |
| **Motivo** | Deploy real: app roda localmente; `database.db` fica em UNC para várias estações. Liberar um grupo de domínio uma vez deve valer em todos os PCs. Produção não deve depender de auth. |
| **Impacto esperado** | Sem conflito funcional com multi-PC. Riscos remanescentes: concorrência SQLite na rede (pré-existente); entradas `PC\usuario` só valem na máquina; admin local de cada estação sempre entra em config. Documentado em `PROJECT_OVERVIEW.md` → *Deploy em rede*. |

---

## D-023 — Remoção de pontes legadas e aliases runtime (A3)

| Campo | Valor |
|-------|-------|
| **Data** | 2026-06-20 |
| **Decisão** | Remover `Database.py`, `utils.py`, `pdf_utils.py`; imports diretos de `app.models` / `app.utils` / `app.services`; eliminar aliases `runtime.config` e `runtime.db` — consumidores usam `runtime.context` ou serviços (`admin_service`, `settings_service`). |
| **Motivo** | E6/A3: zero usages das pontes; estado global simplificado após E4. |
| **Impacto esperado** | Código raiz limpo; `Main.py` permanece apenas como shim de entry point. |
