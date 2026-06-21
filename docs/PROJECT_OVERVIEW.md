# ArtemiS — Visão Geral

Documentação funcional e estrutural do projeto na sua forma atual.  
Para orientações de desenvolvimento e decisões de arquitetura, consulte `docs/AI_CONTEXT.md` e `docs/DECISIONS.md`.

---

## O que é

O **ArtemiS** é uma aplicação desktop em Python para Windows voltada à automação de impressão em lote de formulários de **Aviso de Recebimento (AR)** dos Correios brasileiros.

O sistema:

- Lê arquivos CSV de Workorders (WO) em pastas configuráveis, delimitados por ponto e vírgula.
- Cruza os dados variáveis com layouts visuais cadastrados por cliente e produto.
- Gera PDFs dinâmicos com textos, logotipos, códigos de barras (Code 128, Code 39), QR Code e DataMatrix.
- Envia lotes para impressoras Windows via `PDFtoPrinter.exe` (até cinco filas paralelas) ou exporta PDF para visualização.
- Oferece editor visual de templates, painel administrativo e reimpressão seletiva de itens (modo *Remake*).

**Objetivo:** padronizar e agilizar a emissão de ARs, eliminando alinhamento manual por meio de templates que mapeiam colunas do CSV, com validação de fila e suporte a reimpressão parcial.

### Stack

| Camada | Tecnologia |
|--------|------------|
| Interface | CustomTkinter / Tkinter |
| Persistência | SQLAlchemy + SQLite |
| PDF | ReportLab |
| Impressão Windows | `PDFtoPrinter.exe`, APIs Win32 |
| Distribuição | PyInstaller (`Main.spec` → executável `.exe`) |

---

## Módulos funcionais

### 1. Produção — tela principal (`App`)

Arquivo: `app/ui/main_app.py`

- Seleção de impressora Windows ou opção **Criar PDF**.
- Filtro por **grupo de impressão** (subpastas de lote cadastradas no banco).
- Entrada de WO por digitação ou leitor de código de barras.
- Validação de fila: cliente/produto existentes no banco; mesma cor e tamanho de papel em todas as WOs da fila.
- Indicador visual da cor de papel do produto (Verde, Azul, Rosa, Amarelo, Marfim, Branco).
- Geração de PDF e impressão em thread de fundo, com UI responsiva.
- Painel de progresso (`LoadingBarFrame`) para até cinco impressoras simultâneas.

Serviços envolvidos: `work_queue_service`, `production_service`, `print_job_coordinator`, `pdf_service`, `print_service`.

### 2. Designer de templates (`EditWindow`)

Arquivo: `app/ui/designer_window.py`

- Canvas com gabaritos por orientação: 3 ARs verticais, 2 horizontais, 2 verticais ou folha A4 inteira.
- Ferramentas: seleção, linha, retângulo, texto fixo, contador, segmento, código de barras e imagem (BLOB no banco).
- Painel de propriedades (`ListOfPropertiesWindow`): coordenadas, fontes, rotação (0°/90°/180°/270°), colunas CSV e valores default.
- Atalhos: `Delete`, setas, `Control+Z` (undo, 10 níveis), `Control+C` (duplicação de elementos — segmentos excluídos; ver limitações).
- Preview PDF de teste (`temp/text.pdf`).
- Importação e exportação de produtos em JSON (geometrias + imagens em Base64).

Serviços envolvidos: `designer_service`, `pdf_service`; adaptador `designer_canvas_adapter`.

### 3. Remake — reimpressão seletiva (`RemakeWindow`)

Arquivo: `app/ui/remake_window.py`

- Ativado com **Habilitar Remake** ao escanear WO já arquivada em `Old/`.
- Filtros por intervalo de linhas, RankInJob, número do AR ou nome do destinatário.
- Montagem de fila parcial e geração de PDF apenas com os registros escolhidos.

Serviço envolvido: `remake_service`.

### 4. Configuração e administração (`ConfigWindow`)

Arquivo: `app/ui/config_window.py`

- Acesso via identidade Windows (sem senha do ArtemiS).
- Administradores locais e de domínio sempre entram; demais usuários/grupos são liberados na configuração.
- Pesquisa de usuários e grupos no AD e na máquina local.
- CRUD de clientes e produtos; duplicação; import/export de layouts.
- Caminhos globais: pasta de busca de WOs e arquivo SQLite (`config.json`).
- Cadastro de impressoras e grupos de impressão exibidos na tela de produção.

Serviços envolvidos: `admin_service`, `settings_service`, `app/utils/windows_auth.py`.

---

## Fluxos de uso

### Administrador — configuração e design

1. Abre o ArtemiS; clica no ícone ⚙ (requer ser administrador Windows ou estar liberado na lista de acesso).
2. Acessa configurações — sem login/senha; o Windows identifica o usuário.
3. Define pasta de busca (ex.: `C:\AR`) e caminho do banco SQLite.
4. Libera outros usuários ou grupos da rede em **Gerenciar Acesso** (opcional).
5. Cadastra cliente e produto.
6. Abre o editor: tipo de papel, orientação do gabarito e cor física.
7. Desenha layout e associa elementos às colunas CSV (ex.: `Coluna_2` → endereço).
8. Gera PDF de teste, valida alinhamento e salva.

### Operador — produção

1. Seleciona impressora e grupo de impressão.
2. Escaneia ou digita código da WO; o sistema localiza o CSV na subpasta do grupo.
3. Identifica cliente/produto na primeira linha e carrega o layout.
4. Confere a cor de papel indicada e prepara a impressora.
5. Adiciona WOs à fila; o sistema bloqueia mistura de cor ou tamanho de papel.
6. Clica **Start**: gera PDFs em `temp/`, unifica em `{search_folder}/PDFs/`.
7. Imprime via `PDFtoPrinter.exe` ou abre o PDF se **Criar PDF** estiver selecionado.
8. Move o CSV processado para `Old/` na pasta do lote.

### Operador — remake

1. Habilita **Habilitar Remake**.
2. Escaneia WO; busca o arquivo em `Old/`.
3. Filtra registros com defeito na janela de remake.
4. Adiciona itens à fila e clica **Start**.
5. Reimprime apenas as páginas selecionadas; o CSV original permanece em `Old/`.

---

## Estrutura do repositório

```
ArtemiS/
├── Main.py / main.py       # Entry point → app.bootstrap.main()
├── config.json             # database_location, search_folder
├── database.db             # SQLite (clientes, produtos, desenhos, usuários, etc.)
├── Main.spec               # PyInstaller
├── azure.tcl               # Tema Azure (Treeviews)
├── requirements.txt
├── PDFtoPrinter.exe        # + _2 … _5 para impressão paralela
├── fontes/                 # TTF/OTF (canvas e PDF)
├── theme/                  # Recursos do tema
├── img/                    # Ícones
├── temp/                   # Barcodes e PDFs intermediários
└── app/
    ├── bootstrap.py        # Inicialização: config, banco, App
    ├── runtime.py          # ApplicationContext (config + db)
    ├── application_context.py
    ├── models/
    │   ├── schema.py
    │   └── database_manager.py   # DataBase
    ├── utils/
    │   ├── file_parser.py
    │   ├── barcode_generator.py
    │   ├── printer_handler.py
    │   ├── window_geometry.py
    │   ├── text_utils.py
    │   └── document_delivery.py
    ├── services/
    │   ├── pdf_service.py
    │   ├── print_service.py
    │   ├── production_service.py
    │   ├── work_queue_service.py
    │   ├── remake_service.py
    │   ├── print_job_coordinator.py
    │   ├── designer_service.py
    │   ├── admin_service.py
    │   └── settings_service.py
    └── ui/
        ├── constants.py
        ├── components/           # Table, ListBox, SpinBox, Tooltip, popups
        ├── main_app.py
        ├── designer_window.py
        ├── designer_canvas_adapter.py
        ├── config_window.py
        └── remake_window.py
```

### Camadas

| Camada | Responsabilidade |
|--------|------------------|
| `app/ui` | Janelas, componentes visuais e interação com o operador |
| `app/services` | Regras de negócio, orquestração de produção, PDF e impressão |
| `app/models` | Schema SQLAlchemy e acesso a dados (`DataBase`) |
| `app/utils` | CSV, códigos de barras, impressora, geometria de janelas |
| `app/runtime` | Estado compartilhado da aplicação (`ApplicationContext`) |

O bootstrap (`app/bootstrap.py`) carrega `config.json`, instancia `DataBase`, registra o contexto em `runtime.context` e inicia o loop da interface.

---

## Deploy em rede (SQLite compartilhado)

### Modelo operacional atual

Na prática, o ArtemiS funciona assim:

| Componente | Onde roda | Observação |
|------------|-----------|------------|
| **Executável / app Python** | Local, em cada PC de produção | Um processo por estação; UI, PDF e impressão são locais |
| **`config.json`** | Local em cada PC (ou imagem padrão) | Aponta caminhos; em rede, `database_location` costuma ser UNC (ex.: `\\servidor\ArtemiS\database.db`) |
| **`database.db` (SQLite)** | Pasta compartilhada na rede | Vários PCs leem/escrevem o **mesmo arquivo** para layouts, clientes, produtos, grupos de impressão e `config_access` |
| **Pastas de WO (`search_folder`)** | Rede ou local | CSVs de lote; cada estação pode ter caminho próprio ou compartilhado |
| **`temp/`** | Local em cada PC | PDFs e barcodes intermediários — não compartilhados |

Ou seja: **identidade e impressão são locais**; **cadastro de layouts e regras de configuração centralizados no SQLite da rede**.

### Auth Windows × banco compartilhado — há conflito?

**Não há conflito lógico** entre o auth Windows (2026-06) e o SQLite compartilhado. As duas camadas são separadas:

1. **Quem pode abrir ⚙ Configurações** — decidido **no PC**, pela sessão Windows (`app/utils/windows_auth.py`): usuário logado, grupos do token, admin local/domínio.
2. **Quem está liberado na lista** — lido do **SQLite compartilhado** (tabela `config_access`), igual clientes/produtos.

Fluxo ao clicar em ⚙:

```
PC local                          Pasta compartilhada
────────                          ───────────────────
Windows: quem é o usuário?  ──┐
Windows: é admin?           ──┼──► can_access_config()
SQLite: config_access       ──┘         │
                                        ├─ admin Windows → entra
                                        ├─ usuário/grupo na lista → entra
                                        └─ senão → acesso negado
```

**Tela de produção (Start, fila, impressão)** não usa auth Windows — operadores continuam trabalhando normalmente.

### O que funciona bem nesse modelo

- **Lista de acesso centralizada:** liberar `EMPRESA\Grupo Operadores` em um PC vale para todos que apontam para o mesmo `database.db`.
- **Layouts únicos:** alteração de produto/desenho reflete em todas as estações na próxima leitura do banco.
- **Sem senha duplicada:** cada PC valida o login Windows que o usuário já fez na estação.

### Cuidados e limitações

| Tópico | Detalhe |
|--------|---------|
| **Preferir contas de domínio** | Cadastre `EMPRESA\usuario` ou `EMPRESA\grupo`. Entradas `NOME-DO-PC\usuario` só valem naquele computador. |
| **Admin local por estação** | Quem é admin **daquele PC** sempre abre config ali, mesmo sem estar em `config_access`. Em rede, isso costuma ser TI — comportamento intencional. |
| **SQLite multi-acesso** | Vários PCs escrevendo no mesmo `.db` na rede é **arriscado** (lock, corrupção) — risco **pré-existente**, não introduzido pelo auth. Evite editar config/layout simultaneamente em muitas máquinas; preferir um administrador central. |
| **Tabela `config_access` nova** | Mesmas regras de concorrência das demais tabelas. Escritas são raras (só ao gerenciar acesso). |
| **Tabela `users` legada** | Login/senha antigo não é mais usado; registros antigos não bloqueiam nem liberam ninguém. |
| **`config.json` por PC** | Impressoras em `printers` no SQLite são compartilhadas; cada estação ainda imprime na impressora **local** escolhida na combo. |
| **PC fora do domínio** | Pesquisa AD não funciona; use contas locais ou entrada manual `COMPUTADOR\conta`. |

### Recomendações para TI

1. Apontar `database_location` para UNC estável com backup.
2. Gerenciar acesso preferencialmente com **grupos de domínio** (ex.: `EMPRESA\ArtemiS-Config`).
3. Manter PCs de produção no **mesmo domínio** quando possível.
4. Restringir quem pode abrir config em produção; operadores do dia a dia não precisam estar em `config_access`.

---

## Limitações conhecidas

### Duplicação de segmentos no editor

Em `app/ui/designer_window.py`, o atalho Ctrl+C não duplica blocos do tipo **Segmento** — a ação é ignorada de propósito. Segmentos idênticos precisam ser recriados pelo painel de propriedades.

### Coluna CSV inexistente

Em `app/services/pdf_service.py`, se uma coluna referenciada no layout não existir no CSV, o campo correspondente é omitido no PDF sem mensagem de erro na interface. Layouts inconsistentes podem gerar documentos incompletos de forma silenciosa.

### Controle de acesso à configuração

O acesso às configurações usa a identidade Windows do usuário logado **na estação**. Administradores locais (`Administrators`) e de domínio (`Domain Admins`) sempre têm acesso. Outros usuários ou grupos podem ser liberados em **Gerenciar Acesso**; a lista fica na tabela `config_access` do SQLite (compartilhado se `database_location` for UNC). Ver seção **Deploy em rede** acima. A tabela legada `users` (login/senha SHA-256) permanece no banco mas não é mais utilizada.

### Dependências declaradas não utilizadas

Alguns pacotes listados em `requirements.txt` (ex.: `Eel`, `gevent`, `scipy`, `greenlet`) não são importados pelo código em `app/`. Convém revisar a lista antes de builds ou ambientes de produção.

---

## Glossário

| Termo | Significado |
|-------|-------------|
| **AR** | Aviso de Recebimento (Correios) |
| **WO** | Workorder — arquivo CSV de lote |
| **Cliente / Produto** | Par que identifica o layout e regras de impressão no banco |
| **Grupo de impressão** | Subpasta de busca de WOs dentro de `search_folder` |
| **Old/** | Subpasta onde WOs processadas são arquivadas |
| **Remake** | Reimpressão parcial de linhas selecionadas de uma WO já processada |
