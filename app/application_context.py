from dataclasses import dataclass


@dataclass
class ApplicationContext:
    config: dict
    db: object
