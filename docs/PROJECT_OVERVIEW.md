# Visão Geral

- **O que a aplicação faz:**
  O **ArtemiS** é uma aplicação desktop desenvolvida em Python para o ambiente Windows, voltada para a automação e gerenciamento de impressão em lote de formulários de **Aviso de Recebimento (AR)** dos Correios brasileiros. O sistema consome arquivos de dados variáveis no formato CSV (delimitados por ponto e vírgula), cruza essas informações com layouts visuais de AR preestabelecidos para cada cliente/produto e gera documentos em formato PDF dinamicamente (contendo textos, logotipos corporativos e diversos tipos de códigos de barras, QR Codes ou DataMatrix). Em seguida, os lotes gerados são enviados automaticamente para filas de impressão física no Windows ou salvos localmente.


- **Objetivo principal:**
  Otimizar, padronizar e agilizar o processo de formatação e emissão de ARs. Ele elimina o esforço manual de alinhamento ao permitir a criação de templates visuais precisos que mapeiam dinamicamente as colunas de dados variáveis do arquivo de lote, além de suportar impressão concorrente e fluxos especializados de reimpressão seletiva de itens individuais com falha (modo *Remake*).


# Funcionalidades Atuais

O ArtemiS divide-se em três pilares principais de funcionalidades: o Processador de Lotes (Tela Principal), o Editor e Designer de Templates e o Módulo de Reimpressão (Remake).

### 1. Processamento e Fila de Lotes (Tela Principal - `App`)
- **Configuração da Impressora:** Combobox para seleção de impressoras de destino mapeadas no sistema operacional Windows ou exportação direta via opção "Criar PDF".
- **Grupo de Impressão:** Filtragem de lotes por grupos específicos (ex: subpastas de setores ou campanhas), carregada dinamicamente a partir do banco de dados.
- **Inserção por Escaneamento:** Leitura de arquivos de ordens de serviço (Workorders) inseridos por digitação ou leitor de códigos de barras.
- **Validação de Fila de Impressão:** Ao carregar um lote, o sistema valida no banco de dados se o Cliente e Produto lidos na primeira linha da WO de fato existem. Além disso, o sistema impede a mistura de WOs com cores de papel ou tamanhos de papel divergentes na mesma fila, prevenindo erros operacionais na alimentação física das impressoras.
- **Visualizador Dinâmico de Insumo:** Exibição da cor de papel configurada no produto (usando cores como Verde, Azul, Rosa, Amarelo, Marfim e Branco) por meio de um indicador gráfico colorido na interface.
- **Impressão Paralela Multithread:** Disparo do processo de geração de PDFs e comando de impressão em uma thread separada (`threading.Thread`), assegurando que a interface gráfica principal permaneça responsiva durante o processamento de grandes lotes.
- **Barra de Progresso Compartilhada:** Painel lateral de progresso dinâmico capaz de rastrear até 5 impressoras diferentes imprimindo de forma paralela e simultânea.

### 2. Designer Interativo de Templates (`EditWindow` / `ListOfPropertiesWindow`)
- **Área de Desenho (Canvas):** Canvas interativo que se autoajusta conforme as resoluções de impressão de cada tipo de gabarito e orientação (3 ARs verticais por folha, 2 horizontais por folha, 1 folha inteira A4, ou 2 verticais por folha).
- **Ferramentas de Criação de Elementos:**
  - *Selecionar / Mover:* Ferramentas para manipulação, seleção de foco e reposicionamento fino de elementos desenhados.
  - *Linha e Quadrado (Retângulo):* Criação de linhas e retângulos vetoriais com controle de espessura (largura da borda) e tracejado (Normal, Pequeno, Grande).
  - *Texto Fixo / Contador:* Inserção de strings estáticas ou contadores numéricos de lote com preenchimento de zeros automáticos (ex.: `0000001`).
  - *Segmento:* Blocos de texto que agrupam múltiplos placeholders/variáveis em linhas sequenciais com controle de entrelinha, limite de caracteres para quebra automática e amarração direta com as colunas do CSV de lote.
  - *Código de Barras:* Ferramenta de mapeamento para geração automática de códigos de barras (Code 128, Code 39, QR Code, DataMatrix) com controle de escala (proporção), rotação espacial e ligação com colunas de dados.
  - *Imagem:* Upload de logotipos em formato de imagem (PNG, JPG) gravados diretamente no banco de dados como dados binários (BLOB).
- **Painel Flutuante de Propriedades:** Inspetor dinâmico que exibe e edita os atributos do objeto focado (coordenadas X/Y, fontes instaladas, tamanhos de fonte, estilos bold/normal, rotações angulares em 0/90/180/270 graus, colunas associadas e valores default).
- **Recursos de Produtividade no Editor:**
  - Atalhos de teclado para deleção (`Delete`) e deslocamento fino de elementos pixel a pixel via setas direcionais.
  - Histórico de desfazer (`Control+Z`) limitado a 10 etapas.
  - Duplicação rápida de elementos comuns (`Control+C`).
  - Geração de PDF de teste instantânea (`Visualizar`), renderizando um arquivo de demonstração em `temp/text.pdf` preenchido com dados ilustrativos.
- **Importação/Exportação de Layouts:** Exportação de produtos e suas geometrias e logotipos para arquivos JSON (com imagens codificadas em Base64), permitindo a fácil transferência de templates entre diferentes instalações do sistema.

### 3. Tela de Reimpressão Seletiva (`RemakeWindow`)
- **Tela de Busca e Consulta:** Interface secundária acionada automaticamente ao escanear uma WO previamente concluída (armazenada em uma pasta `Old`) sob o modo remake habilitado.
- **Filtros de Registros da WO:** Permite filtrar linhas do arquivo de lote original a partir de múltiplos critérios (Range de linhas, ID física da etiqueta "RankInJob", Número específico do código do AR ou Nome do destinatário).
- **Fila de Remake Parcial:** O operador pode selecionar e incluir registros individuais específicos na tabela para reimprimir apenas itens defeituosos ou perdidos, evitando o desperdício de insumos que ocorre ao reprocessar todo o lote original.

### 4. Gerenciamento e Administração (`ConfigWindow`)
- **Segurança de Acesso:** Formulários de autenticação de usuários (Login/Cadastro) com hash SHA-256 de senhas.
- **Cadastro de Entidades:** Cadastro, duplicação e exclusão simplificada de Clientes e Produtos.
- **Variáveis Globais do Sistema:** Definição da pasta padrão de escaneamento de WOs e alteração do arquivo de banco de dados SQLite utilizado pelo sistema.
- **Grupos de Impressão e Impressoras:** Cadastro direto de novos grupos de impressão e nomes de filas físicas para exibição dinâmica nas telas de produção.

---

# Fluxo de Uso

### 1. Fluxo de Configuração e Design (Administrador)
1. O administrador abre o ArtemiS. Caso seja o primeiro acesso, o sistema solicita o cadastro de uma credencial administradora inicial.
2. Clicando no ícone de engrenagem (`⚙`), o administrador realiza o login para acessar o painel de configurações.
3. No painel, ele define a pasta raiz para busca de arquivos (ex.: `C:\AR`) e o local do banco de dados SQLite.
4. Cadastra um novo Cliente e cria um Produto associado.
5. Abre o editor de layout (`EditWindow`) do produto. Define se o papel é A4 comum ou outros tamanhos, se a folha conterá 3 ARs por folha na vertical, 2 na horizontal, etc., e seleciona a cor do papel físico associado.
6. Usando a barra de ferramentas, o administrador desenha as bordas do AR (retângulos/linhas), define as legendas fixas (textos fixos) e insere as áreas onde serão preenchidos os dados do lote (Segmentos e Códigos de Barras), associando cada uma delas à respectiva coluna correspondente do arquivo CSV (ex: Coluna_2 para o endereço, Coluna_1 para o código de barras). Insere logotipos se necessário.
7. O administrador gera uma visualização temporária em PDF para conferir as proporções e o alinhamento. Estando tudo correto, ele salva o produto e fecha a janela de design.

### 2. Fluxo de Produção (Operador)
1. O operador seleciona a impressora física que receberá os documentos e o grupo de impressão (que define a subpasta de lote onde o arquivo se encontra).
2. Ele escaneia com um leitor de código de barras ou digita o código identificador da Workorder. O ArtemiS pesquisa o arquivo correspondente na pasta do grupo selecionado.
3. Ao encontrar o arquivo de dados, o ArtemiS lê a primeira linha para identificar o Cliente e Produto e busca as propriedades do layout no banco de dados.
4. O sistema exibe na tela qual a cor do papel necessária para aquele lote (ex.: Verde). O operador confere a cor e insere o papel adequado na bandeja da impressora.
5. Se o operador adicionar mais WOs à fila, o ArtemiS valida se todas pertencem à mesma cor e tamanho de papel. Havendo divergência, o sistema impede a inserção e exibe uma janela de erro para evitar desperdício de insumos.
6. O operador clica no botão **Start**. O ArtemiS inicia em segundo plano a leitura do CSV, desenha os dados e elementos geométricos em PDFs individuais para cada lote de WO na pasta de destino `PDFs` e junta todos eles em um único arquivo PDF unificado.
7. O sistema envia silenciosamente o PDF unificado para a impressora física por meio de um processo paralelo em lote executado pelo utilitário `PDFtoPrinter.exe`. Se a impressora selecionada for "Criar PDF", o arquivo unificado é apenas aberto na tela do leitor de PDF padrão do Windows.
8. Uma vez impressa com sucesso, a Workorder original (CSV) é movida de forma automática pelo ArtemiS para a subpasta `Old` (dentro da pasta do lote), liberando espaço no diretório de entrada.

### 3. Fluxo de Reimpressão (Modo Remake)
1. Em caso de perda física de ARs durante a impressão (ex.: papel atolado ou etiqueta borrada), o operador seleciona o checkbox **Habilitar Remake** no painel principal.
2. O operador escaneia a identificação da WO correspondente. O ArtemiS busca o arquivo na pasta de arquivos processados (`Old`).
3. Uma tela secundária (`RemakeWindow`) é exibida mostrando os dados lidos do arquivo CSV.
4. O operador localiza os registros específicos com defeito por meio dos campos de busca (por exemplo, digitando o número do AR do formulário danificado ou o nome do destinatário).
5. O operador adiciona os registros encontrados à fila de remake e clica em **Start**.
6. O sistema gera um PDF final unificado contendo estritamente as páginas selecionadas para reimpressão e envia-o para a impressora configurada, mantendo o arquivo de dados original intacto na pasta `Old`.

---

# Estrutura do Projeto

As principais pastas e arquivos identificados no projeto ArtemiS desempenham os seguintes papéis estruturais:

### Arquivos na Raiz
- **[Main.py](file:///c:/Python/Projetos/ArtemiS/Main.py):** Arquivo principal e ponto de entrada da aplicação. Contém a interface gráfica principal, todas as classes de janelas secundárias (CustomTkinter/Toplevel) e a orquestração do loop de eventos do Tkinter.
- **[Database.py](file:///c:/Python/Projetos/ArtemiS/Database.py):** Módulo de controle do banco de dados SQLite. Contém os esquemas de tabelas do SQLAlchemy e todas as consultas Sql, inserções, exclusões e rotinas de hashing criptográfico.
- **[pdf_utils.py](file:///c:/Python/Projetos/ArtemiS/pdf_utils.py):** Módulo encarregado da geração física dos PDFs. Contém a lógica de desenho das primitivas geométricas, rotação de textos e barcodes, renderização dinâmica dos dados do CSV e concatenação dos arquivos PDF intermediários.
- **[utils.py](file:///c:/Python/Projetos/ArtemiS/utils.py):** Agrupa funções utilitárias diversas, incluindo leitura de arquivos CSV com fallback de codificação (UTF-8/ANSI), geração de imagens temporárias de códigos de barras (Code 128, 39, QR e DataMatrix), validação física do tamanho de página da impressora de destino e centralização de janelas Tkinter em layouts multi-monitor.
- **[config.json](file:///c:/Python/Projetos/ArtemiS/config.json):** Arquivo de configuração persistente que armazena os caminhos absolutos do banco de dados SQLite (`database_location`) e do diretório raiz de escaneamento de WOs (`search_folder`).
- **[database.db](file:///c:/Python/Projetos/ArtemiS/database.db):** Banco de dados SQLite contendo as tabelas do sistema (clientes, produtos, desenhos/geometrias, grupos, impressoras e credenciais).
- **[Main.spec](file:///c:/Python/Projetos/ArtemiS/Main.spec):** Arquivo de instrução do PyInstaller utilizado para compilar o código Python em um arquivo executável autônomo `.exe`.
- **[azure.tcl](file:///c:/Python/Projetos/ArtemiS/azure.tcl):** Script que define as cores e elementos visuais do tema "Azure Dark" aplicado aos Treeviews padrão do Tkinter que compõem as tabelas.
- **[requirements.txt](file:///c:/Python/Projetos/ArtemiS/requirements.txt):** Especificação de todas as dependências externas e bibliotecas Python necessárias para executar e construir o projeto.
- **[PDFtoPrinter.exe](file:///c:/Python/Projetos/ArtemiS/PDFtoPrinter.exe) (e duplicatas `_2.exe` a `_5.exe`):** Binários compilados utilitários externos que recebem comandos via linha de comando para mandar um arquivo PDF silenciosamente para uma impressora física do Windows. Existem cinco arquivos idênticos para evitar bloqueios de arquivo durante concorrência de impressão de até 5 filas paralelas.

### Subdiretórios
- **`fontes/`:** Contém as fontes tipográficas em formato TTF/OTF que garantem fidelidade visual no canvas do designer e na geração dos relatórios PDF (Arial, Times New Roman, Trebuchet MS, Saira Extra Condensed e Morganite).
- **`theme/`:** Guarda recursos gráficos associados ao arquivo `azure.tcl` (como imagens de checkboxes, setas e bordas do tema escuro/claro).
- **`img/`:** Guarda ícones utilizados no projeto (ex.: `favicon3.ico`).
- **`temp/`:** Pasta de trabalho temporária. Utilizada para salvar as imagens de código de barras recém-geradas que serão inseridas no PDF e os arquivos PDF avulsos de cada WO antes da junção do lote. O sistema limpa esses arquivos periodicamente.
- **`__pycache__/`:** Diretório gerado automaticamente pelo interpretador Python contendo os bytecodes compilados dos módulos para aceleração de carregamento.

---

# Funcionalidades Incompletas ou Pendentes

Com base na leitura estrita e detalhada do código-fonte do sistema, foram identificados os seguintes comportamentos incorretos, inconsistências ou trechos incompletos:

- **Instanciação Inválida para Rotação de Imagens no PDF (`pdf_utils.py`):**
  No arquivo [pdf_utils.py](file:///c:/Python/Projetos/ArtemiS/pdf_utils.py#L520-L532), no fluxo de renderização de imagens do produto com orientação maior que zero, o código tenta rotacionar e salvar o logotipo usando:
  ```python
  with Image.open(io.BytesIO(item['image'])) as img:
      img = img.rotate(orientation, expand=True)
      ...
  ```
  Contudo, a classe `Image` importada na linha 11 pertence à biblioteca `reportlab.platypus` (um objeto flowable do PDF), que não dispõe do método `.open()`. O correto seria utilizar `PIL.Image.open()` (já que a biblioteca Pillow foi importada como `import PIL` no topo do arquivo). Isso significa que **a rotação de logotipos inseridos no editor de layout falhará com um erro de atributo (`AttributeError`) se executada**, caracterizando uma funcionalidade inacabada ou com bug pendente de correção.
  
- **Vazamento de Conexões de Sessão do Banco de Dados (`Database.py`):**
  Diferente das rotinas de clientes e produtos no arquivo [Database.py](file:///c:/Python/Projetos/ArtemiS/Database.py), os métodos `search_printers` (linha 325), `save_printers` (linha 332), `search_print_group` (linha 415), `insert_print_group` (linha 422) e `delete_print_group` (linha 432) iniciam conexões de sessão com o banco através de `connect_to_database()` mas **não realizam a chamada de fechamento `self.session.close()`**. Isso gera um acúmulo de sessões órfãs no SQLite à medida que o operador navega ou altera configurações, o que pode causar lentidões ou problemas de concorrência com o arquivo do banco de dados.

- **Inconsistência de Tratamento de Erro de Buffer em `is_papersize_a4` (`utils.py`):**
  No arquivo [utils.py](file:///c:/Python/Projetos/ArtemiS/utils.py#L290), a rotina de validação de tamanho de papel da impressora do Windows tenta interceptar uma exceção de buffer insuficiente:
  ```python
  except pywintypes.error as e:
  ```
  No entanto, o módulo `pywintypes` **não foi importado no arquivo `utils.py`**. Em um cenário em que a chamada retorne erro de buffer, o interpretador Python falhará ao tentar resolver o nome com um erro `NameError: name 'pywintypes' is not defined`, mascarando o erro real de impressão.

- **Desativação de Validação de Consistência de Coluna (`pdf_utils.py`):**
  A validação que confirma se uma coluna configurada no layout visual existe fisicamente no arquivo CSV da WO (linha 332 de [pdf_utils.py](file:///c:/Python/Projetos/ArtemiS/pdf_utils.py)) foi desativada e deixada comentada:
  ```python
  # if not get_element(file_columns, column[0]):
  #     raise f'Coluna {int(column[0]) + 1}, não existe no arquivo\nWork: {file_columns[3]}'
  ```
  Isso deixa o gerador suscetível a falhas silenciosas de preenchimento ou quebras de script caso o operador configure incorretamente o layout em relação ao arquivo CSV de entrada.

- **Impossibilidade de Duplicação de Segmentos no Editor (`Main.py`):**
  No mapeamento de cópia de componentes com Ctrl+C no canvas em [Main.py](file:///c:/Python/Projetos/ArtemiS/Main.py#L2055-L2056), a ação para duplicar blocos do tipo "Segmento" foi desabilitada explicitamente:
  ```python
  if segment:
      pass  # Nao utilizar Control-C com Segmento
  ```
  Isso obriga o operador a abrir uma nova janela de configuração de segmento e redigitar todos os placeholders e propriedades se desejar criar múltiplos segmentos estruturalmente idênticos.

---

# Dúvidas e Suposições

Abaixo estão listados os pontos que não puderam ser categoricamente determinados a partir da leitura direta do código, bem como as hipóteses formuladas:

- **Significado da Sigla "AR":**
  *Suposição:* Embora o termo "AR" apareça em strings de logs e títulos de janelas, não há uma definição explícita do termo no código. Assume-se hipoteticamente tratar-se de **Aviso de Recebimento**, devido ao formato dos códigos de rastreamento de placeholder (padrão dos Correios do Brasil com duas letras, nove dígitos e o sufixo "BR"), os tamanhos de papel A4 compatíveis com três dobras horizontais e o contexto de impressão logística de correspondências registradas.
  
- **Existência de Níveis de Privilégios de Usuários:**
  *Suposição:* O banco de dados prevê uma coluna `privileges` na tabela `User` e o formulário de cadastro define o valor `'admin'` por padrão. No entanto, não há nenhuma linha de código no ArtemiS que faça verificações condicionais dessa propriedade para bloquear ou liberar acesso a telas ou ferramentas. Infere-se que o sistema de controle de acesso por privilégios está incompleto ou planejado para uma implementação futura, agindo atualmente de maneira puramente representativa.

- **Presença de Código KMeans Alheio ao Projeto:**
  *Suposição:* No rodapé do arquivo [utils.py](file:///c:/Python/Projetos/ArtemiS/utils.py#L358-L394), sob a cláusula `if __name__ == '__main__':`, há uma implementação de algoritmo KMeans com dados sintéticos aleatórios gerados pelo Numpy. Conclui-se hipoteticamente que se trata de um código experimental antigo ou trecho de playground de programação que foi esquecido na versão final do arquivo e que não exerce qualquer impacto ou papel na aplicação principal.

- **Legado de Arquitetura Web local (Eel / SciPy):**
  *Suposição:* O arquivo [requirements.txt](file:///c:/Python/Projetos/ArtemiS/requirements.txt) inclui bibliotecas como `Eel`, `gevent`, `gevent-websocket`, `scipy` e `greenlet`. Nenhuma dessas dependências é chamada pelos módulos do projeto (`Main.py`, `Database.py`, `utils.py` ou `pdf_utils.py`). Supõe-se que o projeto possa ter sido idealizado anteriormente para utilizar uma interface web renderizada localmente com a biblioteca Eel, ou que as dependências sejam resquícios de um ambiente de desenvolvimento compartilhado com outras aplicações da equipe.
