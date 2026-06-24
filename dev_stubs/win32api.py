"""Linux-only stub for the Windows ``win32api`` module (part of pywin32).

See dev_stubs/win32print.py for rationale. Windows-only; importable on Linux
so ArtemiS can be developed/run, but real calls raise NotImplementedError.
"""


def __getattr__(name):
    def _stub(*args, **kwargs):
        raise NotImplementedError(
            f"win32api.{name} is not available on Linux (Windows-only API)."
        )

    return _stub
