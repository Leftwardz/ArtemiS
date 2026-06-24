"""Linux-only stub for the Windows ``win32net`` module (part of pywin32)."""


class error(Exception):
  pass


def NetUserGetLocalGroups(server, user, level):  # noqa: N802
  return ([{"name": "Administrators"}], 1)


def NetUserEnum(server, level, filter_, resume):  # noqa: N802
  return ([], 0, 0)


def NetLocalGroupEnum(server, level, resume):  # noqa: N802
  return ([], 0, 0)


def NetUserGetGroups(domain, user, level):  # noqa: N802
  raise error()
