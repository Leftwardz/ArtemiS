"""Compatibilidade com entry point legado — preferir main.py."""
from app.ui.config_window import (
    AddClientWindow,
    ConfigWindow,
    DuplicateProductWindow,
    ExportProductWindow,
    LoginWindow,
    ManageGroupWindow,
    RegisterWindow,
)
from main import main

if __name__ == "__main__":
    main()
