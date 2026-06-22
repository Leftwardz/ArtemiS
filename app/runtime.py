"""Shared application state initialized at bootstrap."""

from typing import Optional

from app.application_context import ApplicationContext

context: Optional[ApplicationContext] = None


def init(config_dict, database):
    global context
    context = ApplicationContext(config=config_dict, db=database)


def set_db(database):
    global context
    if context is not None:
        context.db = database


def set_config(config_dict):
    global context
    if context is not None:
        context.config = config_dict
