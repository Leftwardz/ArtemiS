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
[x] Etapa 4: Isolamento de Regras de Negócio e PDFs (app/services)
  (x)Criar app/services/pdf_service.py com desenho de ReportLab e união de PDFs
  (x)Desacoplar pdf_service da UI via callbacks (A1)
  (x)Completar app/services/print_service.py — pós-impressão e validação (A2)
  (x)Criar app/services/production_service.py — fila de WO e remake (B1)
  [ ] Ajustar imports restantes em Main.py (A3, opcional)
[x] Etapa 5: Serviços de orquestração (substitui controladores artificiais)
  (x)production_service.py — fila e produção (substitui queue_controller + remake_controller)
  (x)designer_service.py — editor de layouts (substitui designer_controller)
  [-] auth_controller.py — NÃO CRIAR (decisão D-003)
[ ] Etapa 6: Divisão e Organização da Interface Gráfica (app/ui)
 Mover a tela principal App e fila para app/ui/main_app.py
 Mover EditWindow para app/ui/designer_window.py
 Mover RemakeWindow para app/ui/remake_window.py
 Mover ConfigWindow e secundárias para app/ui/config_window.py
 Mover login/registro para app/ui/config_window.py (sem módulo auth separado)
 Separar widgets reutilizados (Table, SpinBox, ListBox, Tooltip) em app/ui/components
 Criar script bootstrap main.py

---
Plano detalhado: docs/REFACTOR_PLAN.md
Decisões: docs/DECISIONS.md
Guia para IAs: docs/AI_CONTEXT.md
