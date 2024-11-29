from io import BytesIO

from pypdf import PdfReader, PdfWriter, PageObject
from pypdf.generic import RectangleObject


class PdfFile:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.reader = PdfReader(file_path)
        self.current_page_idx = 0
        self.pagecount = len(self.reader.pages)

    def get_page(self, idx: int):
        return PdfPage(self.reader.pages[idx])

    def get_current_page(self):
        return self.get_page(self.current_page_idx)

    def get_next_page(self):
        if self.current_page_idx < self.pagecount - 1:
            self.current_page_idx += 1

        return self.get_current_page()

    def get_prev_page(self):
        if self.current_page_idx > 0:
            self.current_page_idx -= 1

        return self.get_current_page()


class PdfPage:
    def __init__(self, page: PageObject):
        writer = PdfWriter()
        self.writer = writer
        writer.add_page(page)
        self.page = writer.pages[0]
        self.rotation = 0
        self.orig_mbox: RectangleObject = page.mediabox
        self.cache = self.render()

    def render(self):
        writer = self.writer
        pdf_bytes = BytesIO()
        writer.write(pdf_bytes)
        return pdf_bytes.getvalue()

    def get_bytes(self):
        if self.is_changed():
            self.cache = self.render()
        return self.cache

    def save(self, file_path: str):
        with open(file_path, 'wb') as f:
            self.writer.write(f)

    @property
    def mbox(self) -> RectangleObject:
        return self.page.mediabox

    def crop(self, top: int, bottom: int, left: int, right: int):
        mbox = self.mbox
        mbox.top = top
        mbox.bottom = bottom
        mbox.left = left
        mbox.right = right

    def is_changed(self):
        rot = self.rotation % 360
        mbox = self.mbox
        old = self.orig_mbox
        return bool(rot or mbox.hash_bin() != old.hash_bin())

    def get_size(self):
        mbox = self.mbox
        return mbox.width, mbox.height

    def rotate_left(self):
        page = self.page
        page.rotate(270)
        page.transfer_rotation_to_content()
        self.rotation -= 90

    def rotate_right(self):
        page = self.page
        page.rotate(90)
        page.transfer_rotation_to_content()
        self.rotation += 90
