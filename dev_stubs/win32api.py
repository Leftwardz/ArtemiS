"""Linux-only stub for the Windows ``win32api`` module (part of pywin32)."""


def GetCurrentProcess():
  return 0


def CloseHandle(handle):
  pass


def __getattr__(name):
  def _stub(*args, **kwargs):
    raise NotImplementedError(
      f"win32api.{name} is not available on Linux (Windows-only API)."
    )

  return _stub
