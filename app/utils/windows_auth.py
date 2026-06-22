"""Autenticação de configuração via identidade Windows (local e domínio)."""

import os

import win32api
import win32con
import win32net
import win32netcon
import win32security

try:
    import win32com.client
    _HAS_ADSI = True
except ImportError:
    _HAS_ADSI = False

# Com UAC, administradores aparecem no token filtrado como "deny-only".
_LOCAL_ADMIN_GROUP_NAMES = frozenset({'administrators', 'administradores'})


def _normalize_principal(name):
    if not name or '\\' not in name:
        return name.upper() if name else ''
    domain, account = name.split('\\', 1)
    return f'{domain.upper()}\\{account}'


def get_current_principal():
    """Retorna o usuário Windows atual no formato DOMÍNIO\\usuário."""
    domain = os.environ.get('USERDOMAIN', '')
    user = os.environ.get('USERNAME', '')
    if domain and user:
        return _normalize_principal(f'{domain}\\{user}')
    return user.upper()


def _open_process_token():
    return win32security.OpenProcessToken(
        win32api.GetCurrentProcess(),
        win32con.TOKEN_QUERY,
    )


def _sid_string(sid):
    return win32security.ConvertSidToStringSid(sid)


def _token_includes_sid(target_sid, token=None):
    """True se o SID aparece nos grupos do token (inclui membership UAC deny-only)."""
    target = _sid_string(target_sid)
    close_token = False
    if token is None:
        token = _open_process_token()
        close_token = True
    try:
        groups = win32security.GetTokenInformation(token, win32security.TokenGroups)
        for sid, _attrs in groups:
            if _sid_string(sid) == target:
                return True
    finally:
        if close_token:
            win32api.CloseHandle(token)
    return False


def _check_membership(group_account, group_domain=None):
    try:
        sid, _, _ = win32security.LookupAccountName(group_domain, group_account)
    except win32security.error:
        return False

    if win32security.CheckTokenMembership(None, sid):
        return True
    return _token_includes_sid(sid)


def _user_in_local_admin_group():
    """Consulta direta ao SAM — funciona mesmo com token UAC filtrado."""
    user = os.environ.get('USERNAME', '')
    if not user:
        return False
    try:
        groups, _total = win32net.NetUserGetLocalGroups(None, user, 0)
    except win32net.error:
        return False
    return any(g['name'].lower() in _LOCAL_ADMIN_GROUP_NAMES for g in groups)


def is_local_admin():
    """True se o usuário atual pertence ao grupo Administradores locais."""
    admins_sid = win32security.CreateWellKnownSid(win32security.WinBuiltinAdministratorsSid)

    if _token_includes_sid(admins_sid):
        return True

    try:
        token = _open_process_token()
        linked = win32security.GetTokenInformation(token, win32security.TokenLinkedToken)
        if win32security.CheckTokenMembership(linked.LinkedToken, admins_sid):
            return True
    except win32security.error:
        pass

    return _user_in_local_admin_group()


def is_domain_admin():
    """True se o usuário atual pertence ao grupo Domain Admins do domínio."""
    dns_domain = os.environ.get('USERDNSDOMAIN')
    if not dns_domain:
        return False
    computer = os.environ.get('COMPUTERNAME', '').upper()
    if dns_domain.upper() == computer:
        return False
    return _check_membership('Domain Admins', dns_domain)


def is_windows_admin():
    """Administrador local ou de domínio — acesso total à configuração."""
    return is_local_admin() or is_domain_admin()


def is_member_of_group(group_principal):
    """
    Verifica se o usuário atual pertence ao grupo informado.
    group_principal: 'DOMÍNIO\\NomeDoGrupo'
    """
    normalized = _normalize_principal(group_principal)
    if '\\' not in normalized:
        return False
    domain, account = normalized.split('\\', 1)
    computer = os.environ.get('COMPUTERNAME', '').upper()
    lookup_domain = None if domain == computer else domain

    if _check_membership(account, lookup_domain):
        return True

    user = os.environ.get('USERNAME', '')
    if not user:
        return False

    account_lower = account.lower()
    if lookup_domain is None:
        try:
            groups, _total = win32net.NetUserGetLocalGroups(None, user, 0)
            return any(g['name'].lower() == account_lower for g in groups)
        except win32net.error:
            return False

    try:
        groups, _total = win32net.NetUserGetGroups(lookup_domain, user, 0)
        return any(g['name'].lower() == account_lower for g in groups)
    except win32net.error:
        return False


def user_matches(current, configured):
    """Compara usuário atual com entrada cadastrada (ignora diferença de maiúsculas no domínio)."""
    return _normalize_principal(current) == _normalize_principal(configured)


def can_access_config(allowed_principals):
    """
    allowed_principals: lista de dicts {'name': 'DOM\\x', 'type': 'user'|'group'}
    Administradores Windows sempre têm acesso.
    """
    if is_windows_admin():
        return True

    current = get_current_principal()
    for entry in allowed_principals:
        name = entry.get('name', '')
        ptype = entry.get('type', 'user')
        if ptype == 'user' and user_matches(current, name):
            return True
        if ptype == 'group' and is_member_of_group(name):
            return True
    return False


def _local_users_match(query):
    results = []
    q = query.lower()
    resume = 0
    while True:
        try:
            data, _, resume = win32net.NetUserEnum(
                None, 0, win32netcon.FILTER_NORMAL_ACCOUNT, resume,
            )
        except win32net.error:
            break
        for item in data:
            name = item['name']
            if q in name.lower():
                computer = os.environ.get('COMPUTERNAME', 'LOCAL')
                results.append({
                    'name': _normalize_principal(f'{computer}\\{name}'),
                    'display': f'{computer}\\{name}',
                    'type': 'user',
                })
        if not resume:
            break
    return results


def _local_groups_match(query):
    results = []
    q = query.lower()
    resume = 0
    while True:
        try:
            data, _, resume = win32net.NetLocalGroupEnum(None, 0, resume)
        except win32net.error:
            break
        for item in data:
            name = item['name']
            if q in name.lower():
                computer = os.environ.get('COMPUTERNAME', 'LOCAL')
                results.append({
                    'name': _normalize_principal(f'{computer}\\{name}'),
                    'display': f'{computer}\\{name}',
                    'type': 'group',
                })
        if not resume:
            break
    return results


def _domain_search(query, principal_type, limit):
    if not _HAS_ADSI:
        return []
    results = []
    q = query.replace('(', '').replace(')', '').replace('*', '').replace('\\', '')
    if len(q) < 2:
        return results
    try:
        root = win32com.client.GetObject('LDAP://rootDSE')
        domain_dn = root.Get('defaultNamingContext')
        domain_dns = root.Get('dnsHostName', '')
        domain_short = domain_dns.split('.', 1)[0].upper() if domain_dns else os.environ.get('USERDNSDOMAIN', '').upper()

        conn = win32com.client.Dispatch('ADsDSOObject')
        cmd = win32com.client.Dispatch('ADODB.Command')
        cmd.ActiveConnection = conn

        def _run_search(ldap_filter, columns):
            nonlocal results
            col_list = ','.join(columns)
            cmd.CommandText = f'<LDAP://{domain_dn}>;{ldap_filter};{col_list};subtree'
            rs = cmd.Execute()
            if rs.EOF:
                return
            rs.MoveFirst()
            while not rs.EOF and len(results) < limit:
                values = {}
                for col in columns:
                    try:
                        values[col] = rs.Fields(col).Value or ''
                    except Exception:
                        values[col] = ''
                yield values
                rs.MoveNext()

        if principal_type in ('user', 'both'):
            ldap_filter = (
                f'(&(objectCategory=person)(objectClass=user)'
                f'(|(sAMAccountName=*{q}*)(displayName=*{q}*)(cn=*{q}*)))'
            )
            for row in _run_search(ldap_filter, ['sAMAccountName', 'displayName']):
                sam = row['sAMAccountName']
                display = row['displayName'] or sam
                if sam:
                    principal = _normalize_principal(f'{domain_short}\\{sam}')
                    results.append({
                        'name': principal,
                        'display': f'{display} ({domain_short}\\{sam})',
                        'type': 'user',
                    })

        if principal_type in ('group', 'both') and len(results) < limit:
            ldap_filter = f'(&(objectCategory=group)(|(sAMAccountName=*{q}*)(cn=*{q}*)))'
            for row in _run_search(ldap_filter, ['sAMAccountName', 'cn']):
                sam = row['sAMAccountName'] or row['cn']
                if sam:
                    principal = _normalize_principal(f'{domain_short}\\{sam}')
                    results.append({
                        'name': principal,
                        'display': f'{domain_short}\\{sam}',
                        'type': 'group',
                    })
    except Exception:
        pass
    return results


def search_principals(query, principal_type='both', limit=25):
    """
    Pesquisa usuários e/ou grupos no domínio (se disponível) e na máquina local.
    principal_type: 'user', 'group' ou 'both'
    """
    query = (query or '').strip()
    if len(query) < 2:
        return []

    seen = set()
    results = []

    for item in _domain_search(query, principal_type, limit):
        if item['name'] not in seen:
            seen.add(item['name'])
            results.append(item)

    if principal_type in ('user', 'both'):
        for item in _local_users_match(query):
            if item['name'] not in seen and len(results) < limit:
                seen.add(item['name'])
                results.append(item)

    if principal_type in ('group', 'both'):
        for item in _local_groups_match(query):
            if item['name'] not in seen and len(results) < limit:
                seen.add(item['name'])
                results.append(item)

    return results[:limit]


def resolve_manual_principal(text):
    """
    Valida e normaliza entrada manual (DOMÍNIO\\conta).
    Retorna dict {'name', 'display', 'type'} ou None se inválido.
    """
    text = (text or '').strip()
    if '\\' not in text:
        return None
    domain, account = text.split('\\', 1)
    if not domain or not account:
        return None
    try:
        sid, resolved_domain, account_type = win32security.LookupAccountName(domain, account)
        normalized = _normalize_principal(f'{resolved_domain}\\{account}')
        ptype = 'group' if account_type in (
            win32security.SidTypeGroup,
            win32security.SidTypeWellKnownGroup,
            win32security.SidTypeAlias,
        ) else 'user'
        return {
            'name': normalized,
            'display': normalized,
            'type': ptype,
        }
    except win32security.error:
        return None
