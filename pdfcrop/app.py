from platform import system as platsys
from tkinter import Tk

CURRENT_OS = platsys()
IS_WIN = CURRENT_OS == "Windows"


class Application:
    TITLE = "PDFCrop"

    def __init__(self):
        self.root = Tk()
        from .gui import MainWindow
        self.main_window: MainWindow = None

    def main(self):
        from .gui import MainWindow
        self.main_window = MainWindow(self.root)
        self.root.mainloop()

    @property
    def hwnd(self):
        return self.root.winfo_id()


_APP: Application = None


def get_app():
    return _APP


def run():
    global _APP
    _APP = Application()
    _APP.main()
