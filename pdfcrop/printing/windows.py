from typing import TYPE_CHECKING
from ctypes import (
    Structure, POINTER, WinDLL, sizeof, byref, windll, HRESULT, cast,
    wstring_at, c_wchar
)
from ctypes.wintypes import (
    DWORD, HWND, HGLOBAL, WORD, HINSTANCE, LPVOID, LPCWSTR, HDC, LPHANDLE,
)
from contextlib import contextmanager

from win32print import (
    OpenPrinter, StartDocPrinter, StartPagePrinter, WritePrinter,
    EndPagePrinter, EndDocPrinter, ClosePrinter,
)

if TYPE_CHECKING:
    from _win32typing import PyPrinterHANDLE  # type: ignore


MAXPAGERANGES = 10  # this was from the MS example, just needs to be at least 1

# Constants for PrintDlgEx
PD_ALLPAGES = 0x00000000
PD_COLLATE = 0x00000010
PD_RETURNDC = 0x00000100
PD_PRINTSETUP = 0x00000040
PD_USEDEVMODECOPIESANDCOLLATE = 0x00000400
PD_RESULT_PRINT = 1
PD_RESULT_APPLY = 2
START_PAGE_GENERAL = 0xffffffff

WCHARSZ = sizeof(c_wchar)
WIN_WCHAR_ENCODING = 'utf-16-le'
"""
Win API only has UTF-16-LE support because they were early adopters before
the rest of the internet converged on utf-8.  Calls to Win API funcs need to
encode as utf-16-le.  Use this constant when doing low-level codec operations.
"""


class PRINTPAGERANGE(Structure):
    _fields_ = [
        ('nFromPage', DWORD),
        ('nToPage', DWORD),
    ]


class PRINTDLGEX(Structure):
    _fields_ = [
        ('lStructSize', DWORD),
        ('hwndOwner', HWND),
        ('hDevMode', HGLOBAL),
        ('hDevNames', HGLOBAL),
        ('hDC', HDC),
        ('Flags', DWORD),
        ('Flags2', DWORD),
        ('ExclusionFlags', DWORD),
        ('nPageRanges', DWORD),
        ('nMaxPageRanges', DWORD),
        ('lpPageRanges', POINTER(PRINTPAGERANGE)),
        ('nMinPage', DWORD),
        ('nMaxPage', DWORD),
        ('nCopies', DWORD),
        ('hInstance', HINSTANCE),
        ('lpPrintTemplateName', LPCWSTR),
        ('lpCallback', LPVOID),  # LPUNKNOWN
        ('nPropertyPages', DWORD),
        ('lphPropertyPages', LPHANDLE),  # *HPROPSHEETPAGE
        ('nStartPage', DWORD),
        ('dwResultAction', DWORD),
    ]


class DEVNAMES(Structure):
    _fields_ = [
        ('wDriverOffset', WORD),
        ('wDeviceOffset', WORD),
        ('wOutputOffset', WORD),
        ('wDefault', WORD),
    ]


kernel32: WinDLL = windll.kernel32
gdi32: WinDLL = windll.gdi32
comdlg32: WinDLL = windll.comdlg32

kernel32.GlobalFree.argtypes = [HGLOBAL]
kernel32.GlobalLock.argtypes = [HGLOBAL]
kernel32.GlobalLock.restype = LPVOID
kernel32.GlobalUnlock.argtypes = [HGLOBAL]
gdi32.DeleteDC.argtypes = [HDC]
comdlg32.PrintDlgExW.argtypes = [POINTER(PRINTDLGEX)]
comdlg32.PrintDlgExW.restype = HRESULT  # Return type for COM-style result


def delete_device_context(hdc):
    """Deletes the device context (DC)."""
    if hdc:
        gdi32.DeleteDC(hdc)


def free_handle(handle):
    """Free a global memory handle."""
    if handle:
        kernel32.GlobalFree(handle)


@contextmanager
def get_handle_data(h: HGLOBAL, struct: type[Structure]):
    if not h:
        return None

    # Lock the global memory handle to access its contents
    ptr: LPVOID = kernel32.GlobalLock(h)
    if not ptr:
        raise OSError("Failed to lock handle.")

    try:
        yield ptr, cast(ptr, POINTER(struct)).contents
    finally:
        # Unlock the global memory handle
        kernel32.GlobalUnlock(h)


def show_print_dialog(hwnd: HWND, pdex: PRINTDLGEX):
    # Initialize PRINTDLGEX structure
    pdex.lStructSize = sizeof(PRINTDLGEX)
    pdex.hwndOwner = hwnd  # get_app().hwnd
    # pdex.Flags = PD_USEDEVMODECOPIESANDCOLLATE | PD_ALLPAGES
    pdex.Flags = PD_ALLPAGES
    pdex.nMinPage = 1
    pdex.nMaxPage = 100
    pdex.nCopies = 1
    pdex.nStartPage = START_PAGE_GENERAL
    pdex.nMaxPageRanges = MAXPAGERANGES
    page_ranges = (PRINTPAGERANGE * MAXPAGERANGES)()
    pdex.lpPageRanges = cast(page_ranges, POINTER(PRINTPAGERANGE))

    # Call PrintDlgEx
    result = comdlg32.PrintDlgExW(byref(pdex))

    # Check if dialog was canceled or not
    if not result and pdex.dwResultAction == PD_RESULT_PRINT:
        return pdex


def win_get_printer_name(pdex: PRINTDLGEX):
    """Retrieve the selected printer name from hDevNames."""
    hDevNames: HGLOBAL = pdex.hDevNames
    if not hDevNames:
        return None

    with get_handle_data(hDevNames, DEVNAMES) as (devnames_ptr, devnames):
        # Compute the address of the device name
        base_address = devnames_ptr
        device_name_address = base_address + devnames.wDeviceOffset*WCHARSZ

        # Read the printer name as a null-terminated Unicode string
        data = wstring_at(device_name_address)
        # name = data.decode(WIN_WCHAR_ENCODING)
        return data


@contextmanager
def print_dialog_context(hwnd: HWND):
    pdex = PRINTDLGEX()
    try:
        pdex = show_print_dialog(hwnd, pdex)
        yield pdex
    finally:
        free_handle(pdex.hDevMode)
        free_handle(pdex.hDevNames)
        # free_handle(pdex.lpPageRanges)
        delete_device_context(pdex.hDC)
        del pdex


@contextmanager
def print_doc(printer_name: str, job_name: str, doctype: str = "RAW"):
    # Open printer and send raw data
    printer_handle = OpenPrinter(printer_name)
    try:
        # Start a document and page
        StartDocPrinter(printer_handle, 1, (job_name, None, doctype))
        yield printer_handle
        EndDocPrinter(printer_handle)
    finally:
        ClosePrinter(printer_handle)


@contextmanager
def print_page(printer_handle: 'PyPrinterHANDLE'):
    StartPagePrinter(printer_handle)
    try:
        yield
    finally:
        EndPagePrinter(printer_handle)


def send_raw_data_to_printer(data: bytes, job_name: str, printer_name: str):
    with print_doc(printer_name, job_name) as hprint:
        with print_page(hprint):
            # Write PDF data directly to the printer
            WritePrinter(hprint, data)
