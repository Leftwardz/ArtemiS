"""Logger dedicado de impressão (logs/print.log).

Registra: backend escolhido, parâmetros enviados, comando/DEVMODE,
sucesso/falha e mensagens de erro do driver ou spooler.
"""

import logging
import os

_LOGGER_NAME = 'artemis.print'
_LOG_DIR = 'logs'
_LOG_FILE = os.path.join(_LOG_DIR, 'print.log')

_logger = None


def get_print_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if not logger.handlers:
        try:
            os.makedirs(_LOG_DIR, exist_ok=True)
            handler = logging.FileHandler(_LOG_FILE, encoding='utf-8')
        except Exception:
            # Se não conseguir criar o arquivo (pasta somente leitura, etc.),
            # cai para console para nunca quebrar a impressão por causa de log.
            handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%d-%m-%Y %H:%M:%S',
        ))
        logger.addHandler(handler)

    _logger = logger
    return logger
