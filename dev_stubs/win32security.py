"""Linux-only stub for the Windows ``win32security`` module (part of pywin32)."""

TokenGroups = 2
TokenLinkedToken = 19
WinBuiltinAdministratorsSid = 26
SidTypeGroup = 2
SidTypeWellKnownGroup = 4
SidTypeAlias = 4


class error(Exception):
  pass


class _LinkedToken:
  LinkedToken = 0


def OpenProcessToken(process, access):  # noqa: N802
  return 0


def ConvertSidToStringSid(sid):  # noqa: N802
  return "S-1-5-32-544"


def GetTokenInformation(token, info_class):  # noqa: N802
  if info_class == TokenLinkedToken:
    raise error()
  return []


def CreateWellKnownSid(sid_type):  # noqa: N802
  return b"admin-sid"


def CheckTokenMembership(token, sid):  # noqa: N802
  return True


def LookupAccountName(domain, account):  # noqa: N802
  raise error()
