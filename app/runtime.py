"""Shared application state initialized at bootstrap."""

from app.application_context import ApplicationContext

context: ApplicationContext = None
config = None
db = None


def init(config_dict, database):
    global context, config, db
    context = ApplicationContext(config=config_dict, db=database)
    config = config_dict
    db = database


def set_db(database):
    global context, db
    db = database
    if context is not None:
        context.db = database


def set_config(config_dict):
    global context, config
    config = config_dict
    if context is not None:
        context.config = config_dict
