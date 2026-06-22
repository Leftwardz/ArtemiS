"""Helpers Win32 para DEVMODE por JOB, capacidades e status de spooler.

Tudo aqui é "por job": o DEVMODE é aplicado a um DC/handle temporário e
NUNCA gravado de volta na impressora (não usa SetPrinter), portanto não
altera configurações permanentes nem exige privilégio de administrador.
"""

import win32con
import win32print

from app.utils.printing.base import (
    DUPLEX_TO_DMDUP,
    ORIENTATION_TO_DMORIENT,
)


def _open_use(printer_name):
    return win32print.OpenPrinter(
        printer_name, {'DesiredAccess': win32print.PRINTER_ACCESS_USE},
    )


def printer_port(printer_name):
    """Porta da impressora (necessária para DeviceCapabilities)."""
    handle = _open_use(printer_name)
    try:
        info = win32print.GetPrinter(handle, 2)
        return info.get('pPortName', '') or ''
    finally:
        win32print.ClosePrinter(handle)


def build_job_devmode(printer_name, job):
    """Monta um DEVMODE para este JOB e o valida via DocumentProperties.

    Retorna (devmode, applied_dict). Levanta exceção se não conseguir abrir
    a impressora (o backend converte isso em PrintResult.failure).
    """
    handle = _open_use(printer_name)
    try:
        info = win32print.GetPrinter(handle, 2)
        dm = info['pDevMode']
        if dm is None:
            raise RuntimeError('Driver não forneceu DEVMODE base.')

        applied = {}
        fields = dm.Fields

        paper = (str(job.paper_size).strip() if job.paper_size is not None else '')
        if paper and paper != '0':
            dm.PaperSize = int(paper)
            fields |= win32con.DM_PAPERSIZE
            applied['PaperSize'] = int(paper)

        if job.copies and int(job.copies) >= 1:
            dm.Copies = int(job.copies)
            fields |= win32con.DM_COPIES
            applied['Copies'] = int(job.copies)

        dmdup = DUPLEX_TO_DMDUP.get(job.duplex)
        if dmdup:
            dm.Duplex = dmdup
            fields |= win32con.DM_DUPLEX
            applied['Duplex'] = dmdup

        dmorient = ORIENTATION_TO_DMORIENT.get(job.orientation)
        if dmorient:
            dm.Orientation = dmorient
            fields |= win32con.DM_ORIENTATION
            applied['Orientation'] = dmorient

        if job.tray is not None:
            dm.DefaultSource = int(job.tray)
            fields |= win32con.DM_DEFAULTSOURCE
            applied['DefaultSource'] = int(job.tray)

        dm.Fields = fields

        # Deixa o driver normalizar/validar (best-effort; mantém dm em caso de falha).
        try:
            merged = win32print.DocumentProperties(
                0, handle, printer_name, dm, dm,
                win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER,
            )
            if hasattr(merged, 'PaperSize'):
                dm = merged
        except Exception:
            pass

        return dm, applied
    finally:
        win32print.ClosePrinter(handle)


def query_device_capabilities(printer_name):
    """Capacidades relevantes (duplex/cópias/papéis/bandejas) para log/validação."""
    caps = {}
    try:
        port = printer_port(printer_name)
        caps['duplex'] = bool(win32print.DeviceCapabilities(
            printer_name, port, win32con.DC_DUPLEX))
        try:
            caps['max_copies'] = int(win32print.DeviceCapabilities(
                printer_name, port, win32con.DC_COPIES))
        except Exception:
            caps['max_copies'] = None
        try:
            caps['papers'] = list(win32print.DeviceCapabilities(
                printer_name, port, win32con.DC_PAPERS) or [])
        except Exception:
            caps['papers'] = []
        try:
            caps['bins'] = list(win32print.DeviceCapabilities(
                printer_name, port, win32con.DC_BINS) or [])
        except Exception:
            caps['bins'] = []
    except Exception as exc:
        caps['error'] = repr(exc)
    return caps


def read_recent_job_status(printer_name, max_jobs=8):
    """Lê o status dos jobs recentes no spooler (best-effort) para log."""
    statuses = []
    handle = None
    try:
        handle = _open_use(printer_name)
        jobs = win32print.EnumJobs(handle, 0, max_jobs, 1)
        for jb in jobs:
            statuses.append({
                'JobId': jb.get('JobId'),
                'Status': jb.get('Status'),
                'pStatus': jb.get('pStatus'),
                'Document': jb.get('pDocument'),
            })
    except Exception as exc:
        statuses.append({'error': repr(exc)})
    finally:
        if handle is not None:
            try:
                win32print.ClosePrinter(handle)
            except Exception:
                pass
    return statuses


def describe_devmode(dm):
    """Resumo legível do DEVMODE para o log."""
    try:
        return {
            'PaperSize': getattr(dm, 'PaperSize', None),
            'Copies': getattr(dm, 'Copies', None),
            'Duplex': getattr(dm, 'Duplex', None),
            'Orientation': getattr(dm, 'Orientation', None),
            'DefaultSource': getattr(dm, 'DefaultSource', None),
            'Fields': getattr(dm, 'Fields', None),
        }
    except Exception as exc:
        return {'error': repr(exc)}
