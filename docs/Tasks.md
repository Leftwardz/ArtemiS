Progresso da Refatoração Incremental - ArtemiS
Acompanhamento das etapas de modularização do projeto:

[x] Etapa 1: Preparação de Estrutura e Mapeamento Inicial
 (x)Criar diretórios app/ui, app/controllers, app/services, app/models, app/utils
 (x) Inicializar os pacotes Python com arquivos __init__.py
[x] Etapa 2: Isolamento dos Modelos de Banco de Dados (app/models)
  (x)Criar app/models/schema.py com as classes do SQLAlchemy
  (x)Criar app/models/database_manager.py com a classe DataBase
  (x)Atualizar Database.py como ponte para compatibilidade
[x] Etapa 3: Modularização de Utilitários (app/utils)
  (x)Criar app/utils/file_parser.py para a lógica de CSV (FileUtils e ranges)
  (x)Criar app/utils/barcode_generator.py para geração de códigos de barras/QR/DataMatrix
  (x)Criar app/utils/printer_handler.py para wrapper do PDFtoPrinter e papel
  (x)Criar app/utils/window_geometry.py para centralização e geometria de tela
  (x)Atualizar utils.py como re-exportador
[/] Etapa 4: Isolamento de Regras de Negócio e PDFs (app/services)
  (x)Criar app/services/pdf_service.py com desenho de ReportLab e união de PDFs
 Criar app/services/print_service.py para gerenciamento concorrente da fila de impressão
 Ajustar importações em Main.py e pdf_utils.py
[ ] Etapa 5: Criação dos Controladores (app/controllers)
 Criar controlador de fila e produção queue_controller.py
 Criar controlador do remake remake_controller.py
 Criar controlador do editor de layouts designer_controller.py
 Criar controlador de login e credenciais auth_controller.py
[ ] Etapa 6: Divisão e Organização da Interface Gráfica (app/ui)
 Mover a tela principal App e fila para app/ui/main_app.py
 Mover EditWindow para app/ui/designer_window.py
 Mover RemakeWindow para app/ui/remake_window.py
 Mover ConfigWindow e secundárias para app/ui/config_window.py
 Mover login/registro para app/ui/auth_windows.py
 Separar widgets reutilizados (Table, SpinBox, ListBox, Tooltip) em app/ui/components
 Criar script bootstrap main.py