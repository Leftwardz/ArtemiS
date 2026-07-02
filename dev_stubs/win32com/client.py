"""Linux-only stub for ``win32com.client`` (part of pywin32)."""


def Dispatch(*args, **kwargs):  # noqa: N802
  raise NotImplementedError(
    "win32com.client.Dispatch is not available on Linux (Windows-only COM)."
  )


def GetObject(*args, **kwargs):  # noqa: N802
  raise NotImplementedError(
    "win32com.client.GetObject is not available on Linux (Windows-only COM)."
  )


def __getattr__(name):
  def _stub(*args, **kwargs):
    raise NotImplementedError(
      f"win32com.client.{name} is not available on Linux (Windows-only COM)."
    )

  return _stub
