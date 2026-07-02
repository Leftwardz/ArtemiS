"""Linux-only stub for ``pywintypes`` (part of pywin32)."""


class error(Exception):
  def __init__(self, winerror=0, *args):
    super().__init__(*args)
    self.winerror = winerror
