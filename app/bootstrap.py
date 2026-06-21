import json
import os

from app import runtime
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
            }
            json.dump(config, config_file, indent=4)
        if not os.path.exists("C:\\AR"):
            os.mkdir("C:\\AR")

    runtime.init(config, DataBase(config["database_location"]))
    runtime.context.db.create_tables()

    app = App()
    app.mainloop()
