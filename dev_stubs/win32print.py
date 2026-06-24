"""Linux-only stub for the Windows ``win32print`` module (part of pywin32).

ArtemiS is a Windows desktop application; ``pywin32`` cannot be installed on
Linux. These stubs only exist so the app can be imported, linted and run for
development on Linux. Any function that requires real Windows printing raises
``NotImplementedError`` if actually invoked (printing is Windows-only).
"""

PRINTER_ACCESS_USE = 0x00000008
PRINTER_ACCESS_ADMINISTER = 0x00000004
PRINTER_ENUM_LOCAL = 0x00000002
PRINTER_ENUM_CONNECTIONS = 0x00000004


def _unsupported(name):
    raise NotImplementedError(
        f"win32print.{name} is not available on Linux (Windows-only printing). "
        "Run ArtemiS on Windows to use real printing functionality."
    )


def SetDefaultPrinter(printer):  # noqa: N802
    _unsupported("SetDefaultPrinter")


def GetDefaultPrinter():  # noqa: N802
    _unsupported("GetDefaultPrinter")


def EnumPrinters(*args, **kwargs):  # noqa: N802
    return []


def OpenPrinter(*args, **kwargs):  # noqa: N802
    _unsupported("OpenPrinter")


def GetPrinter(*args, **kwargs):  # noqa: N802
    _unsupported("GetPrinter")


def ClosePrinter(*args, **kwargs):  # noqa: N802
    _unsupported("ClosePrinter")
