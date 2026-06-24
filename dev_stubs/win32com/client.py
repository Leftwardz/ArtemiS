"""Linux-only stub for ``win32com.client`` (part of pywin32).

See dev_stubs/win32print.py for rationale. Windows-only; importable on Linux
so ArtemiS can be developed/run, but real calls raise NotImplementedError.
"""


def Dispatch(*args, **kwargs):  # noqa: N802
    raise NotImplementedError(
        "win32com.client.Dispatch is not available on Linux (Windows-only COM)."
    )


def __getattr__(name):
    def _stub(*args, **kwargs):
        raise NotImplementedError(
            f"win32com.client.{name} is not available on Linux (Windows-only COM)."
        )

    return _stub
