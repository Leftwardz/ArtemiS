"""Backend XPS Print API (experimental, melhor esforço).

Estratégia:
1. Converte o PDF em XPS usando o Ghostscript empacotado (-sDEVICE=xpswrite).
2. Submete o XPS ao spooler via Win32 XPS Print API (StartXpsPrintJob, em
   XpsPrint.dll), escrevendo os bytes no IXpsPrintJobStream do documento.

Disponibilidade (is_available): exige XpsPrint.dll carregável + Ghostscript
(para gerar o XPS). Se faltar qualquer um, o backend some da lista (o app
continua funcionando normalmente com os demais backends).

Limitação desta versão: as opções de acabamento (duplex/bandeja/cópias) usam
o PrintTicket padrão do driver — não montamos PrintTicket customizado. Os
parâmetros não aplicáveis são apenas registrados em log.
"""

import ctypes
import os
import subprocess
import tempfile
from ctypes import wintypes

from app.utils.ghostscript_paths import (
    ghostscript_env,
    ghostscript_is_available,
    resolve_ghostscript_exe,
)
from app.utils.printing.base import (
    DUPLEX_SIMPLEX,
    PrintBackend,
    PrintJob,
    PrintResult,
)

# XPS_JOB_COMPLETION
_XPS_JOB_IN_PROGRESS = 0
_XPS_JOB_COMPLETED = 1
_XPS_JOB_CANCELLED = 2
_XPS_JOB_FAILED = 3

_WAIT_TIMEOUT_MS = 120000  # 2 min


class _XPS_JOB_STATUS(ctypes.Structure):
    _fields_ = [
        ('jobId', ctypes.c_int32),
        ('currentDocument', ctypes.c_int32),
        ('currentPage', ctypes.c_int32),
        ('currentPageTotal', ctypes.c_int32),
        ('completion', ctypes.c_int),
        ('jobStatus', ctypes.c_int32),  # HRESULT
    ]


def _vtable_func(interface_ptr, index, restype, argtypes):
    """Resolve um método COM pelo índice na vtable (ctypes puro, sem comtypes)."""
    vtable = ctypes.cast(interface_ptr, ctypes.POINTER(ctypes.c_void_p))[0]
    func_addr = ctypes.cast(vtable, ctypes.POINTER(ctypes.c_void_p))[index]
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return proto(func_addr)


def _release(interface_ptr):
    if not interface_ptr:
        return
    try:
        release = _vtable_func(interface_ptr, 2, ctypes.c_ulong, [])
        release(interface_ptr)
    except Exception:
        pass


class XpsBackend(PrintBackend):
    name = 'xps'
    label = 'XPS Print API (experimental)'
    experimental = True

    def is_available(self) -> bool:
        try:
            ctypes.WinDLL('XpsPrint.dll')
        except Exception:
            return False
        try:
            return ghostscript_is_available()
        except Exception:
            return False

    def _pdf_to_xps(self, job, log):
        gs_exe = resolve_ghostscript_exe(job.config)
        env = ghostscript_env(job.config)
        tmpdir = tempfile.mkdtemp(prefix='ar_xps_')
        xps_path = os.path.join(tmpdir, 'document.xps')
        command = [
            gs_exe,
            '-dNOPAUSE', '-dBATCH', '-dQUIET', '-dSAFER',
            '-sDEVICE=xpswrite',
            f'-sOutputFile={xps_path}',
            job.pdf_path,
        ]
        log.info('comando GS->XPS: %s', command)
        result = subprocess.run(
            command, env=env, capture_output=True, text=True,
            cwd=os.path.dirname(gs_exe) if os.path.isfile(gs_exe) else None,
        )
        if result.returncode != 0 or not os.path.isfile(xps_path):
            detail = (result.stderr or result.stdout or '').strip()
            raise RuntimeError(f'Falha ao gerar XPS via Ghostscript.\n{detail}')
        return xps_path, tmpdir

    def _submit_xps(self, printer_name, xps_path, log):
        xpsprint = ctypes.WinDLL('XpsPrint.dll')
        ole32 = ctypes.windll.ole32
        kernel32 = ctypes.windll.kernel32

        com_inited = False
        completion_event = None
        job_ptr = ctypes.c_void_p()
        doc_stream = ctypes.c_void_p()
        ticket_stream = ctypes.c_void_p()

        try:
            hr = ole32.CoInitializeEx(None, 0x2)  # APARTMENTTHREADED
            com_inited = hr in (0, 1)  # S_OK / S_FALSE

            completion_event = kernel32.CreateEventW(None, True, False, None)
            if not completion_event:
                raise OSError('CreateEventW falhou.')

            start = xpsprint.StartXpsPrintJob
            start.restype = ctypes.c_int32  # HRESULT
            start.argtypes = [
                wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
                wintypes.HANDLE, wintypes.HANDLE,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint32,
                ctypes.POINTER(ctypes.c_void_p),
                ctypes.POINTER(ctypes.c_void_p),
                ctypes.POINTER(ctypes.c_void_p),
            ]

            hr = start(
                printer_name, 'Impressão de AR', None,
                None, completion_event,
                None, 0,
                ctypes.byref(job_ptr),
                ctypes.byref(doc_stream),
                ctypes.byref(ticket_stream),
            )
            if hr < 0:
                raise OSError(f'StartXpsPrintJob HRESULT=0x{hr & 0xffffffff:08X}')

            with open(xps_path, 'rb') as fh:
                data = fh.read()

            # IXpsPrintJobStream: ...ISequentialStream::Write (idx 4), Close (idx 5)
            write = _vtable_func(
                doc_stream, 4, ctypes.c_int32,
                [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)],
            )
            close = _vtable_func(doc_stream, 5, ctypes.c_int32, [])

            buf = ctypes.create_string_buffer(data, len(data))
            written = ctypes.c_ulong(0)
            hr = write(doc_stream, ctypes.cast(buf, ctypes.c_void_p),
                       len(data), ctypes.byref(written))
            if hr < 0:
                raise OSError(f'IXpsPrintJobStream.Write HRESULT=0x{hr & 0xffffffff:08X}')

            hr = close(doc_stream)
            if hr < 0:
                raise OSError(f'IXpsPrintJobStream.Close HRESULT=0x{hr & 0xffffffff:08X}')

            kernel32.WaitForSingleObject(completion_event, _WAIT_TIMEOUT_MS)

            # IXpsPrintJob::GetJobStatus (idx 4 após IUnknown 0-2 + Cancel 3)
            status = _XPS_JOB_STATUS()
            get_status = _vtable_func(
                job_ptr, 4, ctypes.c_int32, [ctypes.POINTER(_XPS_JOB_STATUS)],
            )
            get_status(job_ptr, ctypes.byref(status))
            log.info('XPS job: completion=%s jobStatus=0x%08X',
                     status.completion, status.jobStatus & 0xffffffff)

            if status.completion == _XPS_JOB_FAILED:
                raise OSError(f'XPS job FAILED (HRESULT=0x{status.jobStatus & 0xffffffff:08X})')
            if status.completion == _XPS_JOB_CANCELLED:
                raise OSError('XPS job CANCELLED')
        finally:
            _release(ticket_stream)
            _release(doc_stream)
            _release(job_ptr)
            if completion_event:
                try:
                    kernel32.CloseHandle(completion_event)
                except Exception:
                    pass
            if com_inited:
                try:
                    ole32.CoUninitialize()
                except Exception:
                    pass

    def print_job(self, job: PrintJob) -> PrintResult:
        from app.utils.printing.logger import get_print_logger
        log = get_print_logger()

        unsupported = []
        if job.duplex != DUPLEX_SIMPLEX:
            unsupported.append(f'duplex={job.duplex}')
        if job.copies and int(job.copies) > 1:
            unsupported.append(f'copies={job.copies}')
        if job.tray is not None:
            unsupported.append(f'tray={job.tray}')
        if unsupported:
            log.warning('XPS (sem PrintTicket custom) usa default do driver para: %s',
                        ', '.join(unsupported))

        tmpdir = None
        try:
            xps_path, tmpdir = self._pdf_to_xps(job, log)
            self._submit_xps(job.printer, xps_path, log)
        except Exception as exc:
            return PrintResult.failure(self.name, f'Erro no backend XPS: {exc}', detail=repr(exc))
        finally:
            if tmpdir and os.path.isdir(tmpdir):
                import shutil
                shutil.rmtree(tmpdir, ignore_errors=True)

        return PrintResult.success(self.name, message='Enviado via XPS Print API')
