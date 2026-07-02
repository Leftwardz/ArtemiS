"""Rasterização de PDF -> imagens via Ghostscript empacotado.

O win32print/GDI e (em parte) o XPS não renderizam PDF nativamente. Como o
projeto já empacota o Ghostscript, reaproveitamos o GS apenas como
rasterizador (sem enviar nada para impressora aqui).
"""

import glob
import os
import shutil
import subprocess
import tempfile

from app.utils.ghostscript_paths import ghostscript_env, resolve_ghostscript_exe

DEFAULT_DPI = 300


class RasterizedPdf:
    """Contexto com as imagens das páginas; limpa os temporários ao sair."""

    def __init__(self, image_paths, tmpdir):
        self.image_paths = image_paths
        self.tmpdir = tmpdir

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.cleanup()
        return False

    def cleanup(self):
        if self.tmpdir and os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)
            self.tmpdir = None


def rasterize_pdf(pdf_path, dpi=DEFAULT_DPI, config=None):
    """Renderiza cada página do PDF como PNG e devolve um RasterizedPdf.

    Levanta exceção em caso de falha (o backend converte em PrintResult).
    """
    gs_exe = resolve_ghostscript_exe(config)
    env = ghostscript_env(config)
    tmpdir = tempfile.mkdtemp(prefix='ar_raster_')
    pattern = os.path.join(tmpdir, 'page_%04d.png')

    command = [
        gs_exe,
        '-dNOPAUSE', '-dBATCH', '-dQUIET', '-dSAFER',
        '-sDEVICE=png16m',
        f'-r{int(dpi)}',
        f'-sOutputFile={pattern}',
        pdf_path,
    ]

    result = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(gs_exe) if os.path.isfile(gs_exe) else None,
    )
    if result.returncode != 0:
        shutil.rmtree(tmpdir, ignore_errors=True)
        detail = (result.stderr or result.stdout or '').strip()
        raise RuntimeError(f'Falha ao rasterizar PDF via Ghostscript.\n{detail}')

    image_paths = sorted(glob.glob(os.path.join(tmpdir, 'page_*.png')))
    if not image_paths:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise RuntimeError('Ghostscript não gerou páginas para o PDF informado.')

    return RasterizedPdf(image_paths, tmpdir)
