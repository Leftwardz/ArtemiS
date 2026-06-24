"""Linux-only stub for the Windows ``win32ui`` module (part of pywin32)."""


def __getattr__(name):
  def _stub(*args, **kwargs):
    raise NotImplementedError(
      f"win32gui.{name} is not available on Linux (Windows-only API)."
    )

  return _stub
