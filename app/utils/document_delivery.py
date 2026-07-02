import os


def open_path(path: str):
    """Abre arquivo ou pasta com o aplicativo padrão do sistema (Windows)."""
    os.startfile(os.path.abspath(path))
