from subprocess import run
from shutil import which

from ..app import IS_WIN


def get_ghostscript_cmd():
    cmd = which('gs')
    if not cmd and IS_WIN:
        cmd = which("gswin64c")

    return cmd


def print_pdf_ghostscript(pdf_path: str, gs_cmd: str = None,
                          printer_name: str = None):
    if not gs_cmd:
        gs_cmd = get_ghostscript_cmd()

    dev = 'mswinpr2' if IS_WIN else 'lpr'

    cmd = [
        gs_cmd,
        '-dNOPAUSE',          # Disable pausing between pages
        '-dBATCH',            # Exit after processing
        '-dQUIET',            # Suppress output (optional)
        '-dPDFFitPage',
        f"-sDEVICE={dev}",
    ]

    if printer_name:
        cmd += [f"-sOutputFile='{printer_name}'"]

    cmd += [
        "-dPrinted",  # Send to the printer, not to a file
        "-f", pdf_path  # Path to the input PDF file
    ]

    run(cmd, check=True)
