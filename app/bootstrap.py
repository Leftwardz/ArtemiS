import json
import os

from app import audit, runtime
from app.models.database_manager import DataBase
from app.ui.main_app import App


def main():
    try:
        with open("config.json") as config_file:
            config = json.load(config_file)
            if not os.path.exists(config["search_folder"]):
                os.mkdir(config["search_folder"])
    except FileNotFoundError:
        with open("config.json", "w") as config_file:
            config = {
                "database_location": "database.db",
                "search_folder": "C:\\AR",
                "print_backend": "pdftoprinter",
                "audit_enabled": True,
                "audit_central_location": "",
                "audit_flush_interval_seconds": 180,
                "audit_retention_days": 180,
            }
            json.dump(config, config_file, indent=4)
        if not os.path.exists("C:\\AR"):
            os.mkdir("C:\\AR")

    runtime.init(config, DataBase(config["database_location"]))
    runtime.context.db.create_tables()

    audit.init_audit(config)

    app = App()
    try:
        app.mainloop()
    finally:
        audit.shutdown_audit()
