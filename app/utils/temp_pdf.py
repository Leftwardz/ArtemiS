import os
import tempfile


def write_temp_pdf(pdf_bytes: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix='.pdf', prefix='artemis_')
    os.close(fd)
    with open(path, 'wb') as file:
        file.write(pdf_bytes)
    return path


def remove_temp_pdf(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
