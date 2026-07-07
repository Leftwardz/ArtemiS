import json
import os

from app import audit, runtime
from app.models.database_manager import DataBase
from app.services.print_group_service import ensure_workorder_directories
from app.services.print_group_service import DEFAULT_SEARCH_FOLDER
from app.ui.theme import init_theme_from_config


def main():
    try:
        with open("config.json") as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        with open("config.json", "w") as config_file:
            config = {
                "database_location": "database.db",
                "search_folder": DEFAULT_SEARCH_FOLDER,
                "print_backend": "pdftoprinter",
                "win32_raster_dpi": 300,
                "audit_enabled": True,
                "audit_central_location": "",
                "audit_flush_interval_seconds": 180,
                "audit_retention_days": 180,
                "language": "pt",
                "locales_folder": "",
                "ui_theme": "slate",
            }
            json.dump(config, config_file, indent=4)

    init_theme_from_config(config)

    runtime.init(config, DataBase(config["database_location"]))
    runtime.context.db.create_tables()
    ensure_workorder_directories(
        config["search_folder"],
        runtime.context.db.search_print_group(),
    )

    from app.i18n import init_i18n
    init_i18n(config)

    audit.init_audit(config)

    from app.utils.ghostscript_paths import log_ghostscript_startup
    log_ghostscript_startup()

    from app.ui.main_app import App

    app = App()
    try:
        app.mainloop()
    finally:
        audit.shutdown_audit()
