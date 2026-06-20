# Contexto para IAs — ArtemiS

Documento de onboarding para qualquer agente de IA (Cursor, Codex, Antigravity ou outro) que trabalhe neste repositório.  
**Leia este arquivo antes de propor ou implementar alterações.**

**Última atualização:** 2026-06-20 (Fases A1–C1, D1 e D2 concluídas)

---

## Sobre o Projeto

**ArtemiS** é uma aplicação desktop Python para Windows que automatiza a impressão em lote de formulários de **Aviso de Recebimento (AR)** dos Correios brasileiros.

### O que o sistema faz

- Lê arquivos CSV (WO — Workorders) de pastas configuráveis.
- Cruza dados variáveis com layouts visuais (templates) por cliente/produto.
- Gera PDFs dinamicamente (texto, logotipos, códigos de barras, QR, DataMatrix).
- Envia lotes para impressoras Windows via `PDFtoPrinter.exe` (até 5 filas paralelas) ou exporta PDF.
- Oferece editor visual de templates, reimpressão seletiva (Remake) e painel de configuração/admin.

### Stack principal

- Python, CustomTkinter/Tkinter (UI)
- SQLAlchemy + SQLite (persistência)
- ReportLab (PDF)
- PyInstaller (`Main.spec` → executável Windows)

### Documentação complementar

| Arquivo | Quando ler |
|---------|------------|
| `docs/PROJECT_OVERVIEW.md` | Funcionalidades, fluxos de uso, bugs conhecidos |
| `docs/REFACTOR_PLAN.md` | Estado da refatoração, próximas etapas, ordem de execução |
| `docs/DECISIONS.md` | Decisões arquiteturais — o que fazer e o que **não** fazer |
| `docs/Tasks.md` | Checklist original (parcialmente superseded por `REFACTOR_PLAN.md`) |

---

## Arquitetura

### Estrutura de pastas (estado atual)

```
ArtemiS/
├── Main.py                 # Monolito: UI (22 classes) + bootstrap + orquestração (~2.678 linhas)
├── Database.py             # Ponte → app/models/
├── utils.py                # Ponte → app/utils/
├── pdf_utils.py            # Ponte → app/services/pdf_service.py
├── config.json             # Caminhos: database_location, search_folder
├── database.db             # SQLite
├── Main.spec               # PyInstaller (entry: Main.py)
├── fontes/                 # TTF/OTF para PDF e canvas
├── theme/                  # Recursos azure.tcl
├── img/                    # Ícones
├── temp/                   # Barcodes e PDFs intermediários
└── app/
    ├── models/
    │   ├── schema.py           # SQLAlchemy: Client, Product, Drawing, User, Printer, PrintingGroup
    │   └── database_manager.py # Classe DataBase (CRUD, queries)
    ├── utils/
    │   ├── file_parser.py      # FileUtils, get_sequence_from_str
    │   ├── barcode_generator.py
    │   ├── printer_handler.py  # print_pdf_file, is_papersize_a4
    │   ├── window_geometry.py
    │   └── text_utils.py
    ├── services/
    │   ├── pdf_service.py      # Geração ReportLab (callbacks, sem Tkinter)
    │   ├── print_service.py    # Pós-impressão, validação de papel, arquivamento
    │   ├── production_service.py # Fila de WO, validações, payload produção/remake
    │   └── designer_service.py   # Validação, serialização canvas, import/export
    ├── controllers/            # VAZIO — não criar controladores artificiais
    └── ui/
        ├── constants.py        # APP_NAME, ICON, FONT, cores, dimensões, PAPER_COLOR_LIST
        ├── components/         # Table, ListBox, SpinBox, Tooltip, popups
        ├── remake_window.py    # RemakeWindow
        ├── main_app.py         # App + LoadingBarFrame (tela principal)
        ├── designer_window.py  # EditWindow + auxiliares do designer
        └── config_window.py    # ConfigWindow + login/admin
```

### Responsabilidades por camada

| Camada | Responsabilidade | Status |
|--------|------------------|--------|
| `app/models` | Schema e acesso a dados | ✅ Concluído |
| `app/utils` | Funções puras/auxiliares (CSV, barcode, impressora, geometria) | ✅ Concluído |
| `app/services/pdf_service` | Desenho e montagem de PDFs | ✅ Desacoplado (callbacks) |
| `app/services/print_service` | Pós-impressão e arquivamento | ✅ Concluído |
| `app/services/production_service` | Fila de WO, validações, remake | ✅ Concluído |
| `app/services/designer_service` | Serialização canvas, import/export | ✅ Concluído |
| `app/ui/main_app` | Tela principal de produção + progresso paralelo | ✅ Concluído (D3) |
| `app/ui/designer_window` | Editor de templates + janelas auxiliares | ✅ Concluído (D4) |
| `app/ui/config_window` | Configurações, login, import/export | ✅ Concluído (D5) |
| `Main.py` | Bootstrap + reexport para `__main__` | 🔄 ~35 linhas (D6 moverá para `main.py`) |

### Classes principais

| Classe | Módulo | Papel |
|--------|--------|-------|
| `App` | `app/ui/main_app.py` | Tela principal — fila de WO, Start, impressão |
| `LoadingBarFrame` | `app/ui/main_app.py` | Progresso paralelo (até 5 impressoras) |
| `RemakeWindow` | `app/ui/remake_window.py` | Reimpressão seletiva |
| `EditWindow` | `app/ui/designer_window.py` | Designer de templates |
| `ListOfPropertiesWindow` / `Get*Window` | `app/ui/designer_window.py` | Auxiliares do designer |
| `ConfigWindow` | `app/ui/config_window.py` | Administração |
| `LoginWindow` / `RegisterWindow` | `app/ui/config_window.py` | Auth simples (sem camada separada) |
| `Table`, `ListBox`, `SpinBox`, `Tooltip` | `app/ui/components/` | Componentes reutilizáveis |

### Globals importantes

- `config` — dict carregado de `config.json` (instanciado em `Main.py`).
- `db` — instância de `DataBase` (instanciada em `Main.py`).
- Ambos são **globais de módulo** — serviços extraídos ainda dependem implicitamente deles.

---

## Estado Atual da Refatoração

### Concluído ✅

1. Estrutura `app/` com pacotes.
2. Modelos + ponte `Database.py`.
3. Utilitários + ponte `utils.py`.
4. `pdf_service.py` + ponte `pdf_utils.py` — **desacoplado da UI (A1)**.
5. `print_service.py` — pós-impressão e validação de papel **(A2)**.
6. `production_service.py` — fila de WO e remake **(B1)**.
7. `designer_service.py` — editor de layouts **(C1)**.
8. Componentes UI em `app/ui/components/` **(D1)**.
9. `RemakeWindow` em `app/ui/remake_window.py` **(D2)**.
10. `App` + `LoadingBarFrame` em `app/ui/main_app.py` **(D3)**.
11. Designer em `app/ui/designer_window.py` **(D4)**.
12. Config/admin em `app/ui/config_window.py` **(D5)**.

### Próximo passo recomendado 🎯

**D6 — Criar `main.py` e atualizar `Main.spec`** (ver `REFACTOR_PLAN.md`).

### Explicitamente fora do escopo imediato 🚫

- `auth_controller` — não criar.
- Controladores vazios ou por padrão MVC.
- Migrar UI (`app/ui/`) antes de concluir Fases A–C.
- Reescrita completa de `Main.py`.
- Implementar controle de privilégios (coluna `privileges` existe mas não é usada).

---

## Regras para Alterações

### Obrigatório

1. **Mudanças incrementais** — extrair blocos pequenos e testáveis; nunca reescrever módulos inteiros de uma vez.
2. **Manter compatibilidade** — preservar pontes (`Database.py`, `utils.py`, `pdf_utils.py`) enquanto `Main.py` não migrar imports.
3. **Não criar camadas artificiais** — só extrair módulo quando há responsabilidade real observável no código.
4. **Preservar comportamento** — refatoração estrutural, não alteração funcional (salvo bugs explicitamente solicitados).
5. **Atualizar documentação** ao concluir cada etapa (ver Processo Obrigatório abaixo).
6. **Não commitar** a menos que o usuário peça explicitamente.

### Preferências de estilo (do projeto)

- Reutilizar funções e convenções existentes.
- Diff mínimo focado no problema.
- Comentários só para lógica não óbvia.
- Não adicionar testes triviais nem abstrações prematuras.

### Armadilhas conhecidas

- `write_text_to_pdf` roda em **thread separada** — callbacks de UI usam `App.after()` (implementado em A1).
- Remake tem dois fluxos: com tela secundária (`RemakeWindow`) e direto (checkbox "Não Utilizar Tela Secundária").
- Grupo de impressão `'AR'` é tratado como string vazia no caminho (legado).
- Vazamentos de sessão DB em métodos de impressoras/grupos (ver `PROJECT_OVERVIEW.md`).
- `Main.spec` aponta para `Main.py` — não mudar entry point até fase bootstrap.

---

## Processo Obrigatório

### Antes de alterar código

1. Ler `docs/PROJECT_OVERVIEW.md` — entender o produto e bugs conhecidos.
2. Ler `docs/REFACTOR_PLAN.md` — identificar etapa atual e dependências.
3. Ler `docs/DECISIONS.md` — respeitar decisões registradas (especialmente o que **não** fazer).
4. Confirmar qual fase está em execução (A1, A2, B1, etc.) e não pular etapas sem motivo.

### Durante a implementação

- Alterar o mínimo necessário para a etapa corrente.
- Manter pontes de compatibilidade funcionando.
- Não mover arquivos de UI (`app/ui/`) antes da Fase D unless explicitly requested.

### Após análise ou implementação

1. **Atualizar `docs/REFACTOR_PLAN.md`** — marcar etapa concluída, ajustar "Estado Atual" se necessário.
2. **Atualizar `docs/DECISIONS.md`** — se houver nova decisão arquitetural (formato: data, decisão, motivo, impacto).
3. **Registrar progresso** — descrever o que foi feito, riscos remanescentes e próximo passo.
4. Opcionalmente sincronizar `docs/Tasks.md` se o usuário mantiver esse checklist.

### Casos de teste manuais (fluxo de produção)

Após alterações em PDF, impressão ou fila de WO, validar:

- [ ] Lote normal → impressora física
- [ ] Opção "Criar PDF"
- [ ] Remake parcial via `RemakeWindow`
- [ ] Remake sem tela secundária (checkbox)
- [ ] Múltiplas WOs (mesma cor e tamanho de papel)
- [ ] Rejeição de WO com cor ou tamanho divergente
- [ ] Arquivo movido para `Old/` após impressão normal (não movido em remake)

---

## Ordem de execução (referência rápida)

```
A1  pdf_service callbacks          ✅
A2  print_service completo         ✅
B1  production_service             ✅
C1  designer_service              ✅
D1  app/ui/components             ✅
D2  app/ui/remake_window          ✅
D3  app/ui/main_app               ✅
D4  app/ui/designer_window         ✅
D5  app/ui/config_window          ✅
D6  bootstrap main.py + Main.spec ← PRÓXIMO
E   infraestrutura (injeção db/config, bugs)
A3  limpar imports (opcional)
```

Detalhes completos, riscos e dependências: **`docs/REFACTOR_PLAN.md`**.

---

## Contato com decisões-chave (resumo)

| Pergunta | Resposta |
|----------|----------|
| Criar `auth_controller`? | **Não** (D-003) |
| Criar controlador só por padrão MVC? | **Não** (D-004) |
| Mover UI agora? | **Incremental** — serviços primeiro (D-007); UI em D1–D6 |
| O que fazer primeiro? | **D6** — `main.py` + `Main.spec` |
| Onde colocar orquestração? | `app/services/`, não `app/controllers/` (D-004, D-005, D-006) |
