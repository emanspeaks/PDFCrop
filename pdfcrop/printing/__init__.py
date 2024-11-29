from subprocess import run
from os.path import isfile

from ..app import CURRENT_OS, IS_WIN, get_app

from .ghostscript import get_ghostscript_cmd, print_pdf_ghostscript

if IS_WIN:
    from os import startfile

    from .windows import (
        print_dialog_context, send_raw_data_to_printer, win_get_printer_name,
    )


def get_printer_name():
    if IS_WIN:
        app = get_app()
        with print_dialog_context(app.hwnd) as pdex:
            return win_get_printer_name(pdex)


def print_pdf_bytes(pdf_data: bytes, printer_name: str = None):
    if CURRENT_OS in ["Linux", "Darwin"]:
        from .cups import cups_print_pdf_bytes
        cups_print_pdf_bytes(pdf_data)

    elif IS_WIN:
        app = get_app()
        job_name = app.TITLE
        send_raw_data_to_printer(pdf_data, job_name, printer_name)

    else:
        raise NotImplementedError(f"Native printing with OS {CURRENT_OS} "
                                  "not supported")


def print_pdf(pdf_path: str, pdf_data: bytes = None):
    if not isfile(pdf_path):
        raise FileNotFoundError(f"The file '{pdf_path}' does not exist.")

    if pdf_data:
        try:
            # first try native printing:
            printer_name = get_printer_name()
            print_pdf_bytes(pdf_data, printer_name)
        except Exception as e:
            print(f"Error while printing natively: {e}")
        else:
            return

    gscmd = get_ghostscript_cmd()
    if gscmd:
        try:
            print_pdf_ghostscript(pdf_path, gscmd)
        except Exception as e:
            print(f"Error while printing with Ghostscript: {e}")
        else:
            return

    if CURRENT_OS not in ("Linux", "Darwin", "Windows"):
        raise NotImplementedError(f"Printing not implemented for {CURRENT_OS}")

    if IS_WIN:
        startfile(pdf_path, "print")
    else:
        run(["lp", pdf_path], check=True)
