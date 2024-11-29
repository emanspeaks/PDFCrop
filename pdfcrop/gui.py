from tkinter import Tk, Canvas, Button, filedialog, Event, Label
from webbrowser import open_new_tab

from pdf2image import convert_from_bytes
from PIL.ImageTk import PhotoImage

from .pdf import PdfFile, PdfPage
from .printing import print_pdf
from .app import get_app


class MainWindow:
    def reset(self):
        self.image = None
        self.tk_image = None
        self.start_x = self.start_y = None
        self.rect = None
        self.zoom_level = 1.0

    def set_title(self, subtitle: str = None):
        title = get_app().TITLE
        if subtitle:
            title += ' - ' + subtitle
        self.root.title(title)

    def __init__(self, root: Tk):
        self.root = root
        self.set_title()

        self.pdf: PdfFile = None
        self.page: PdfPage = None
        self.reset()

        # Canvas for displaying the PDF page
        cnvs = Canvas(root, width=800, height=600, bg="white")
        cnvs.pack(fill="both", expand=True)
        cnvs.bind("<ButtonPress-1>", self.start_draw)
        cnvs.bind("<B1-Motion>", self.draw_rectangle)
        cnvs.bind("<ButtonRelease-1>", self.end_draw)
        cnvs.bind("<Motion>", self.update_coordinates)
        self.canvas = cnvs

        # Navigation and action buttons
        toolbar = {
            "Open PDF": self.open_pdf,
            "Prev Pg": self.prev_page,
            "Next Pg": self.next_page,
            "Zoom -": self.zoom_out,
            "Zoom +": self.zoom_in,
            "Rot Left": self.rotate_left,
            "Rot Right": self.rotate_right,
            "Clear Crop": self.clear_rect,
            "Open in Browser": self.open_chrome,
            "Save to PDF": self.save_selection,
            "Print Page": self.print_page,
        }
        for k, v in toolbar.items():
            btn = Button(root, text=k, command=v)
            btn.pack(side="left", padx=5, pady=5)

        # Status bar to display mouse coordinates
        statbar = Label(root, text="(0, 0)",
                        anchor="w", bd=1, relief="sunken", height=1)
        statbar.pack(side="left", padx=5, pady=5)
        self.status_bar = statbar

    def update_coordinates(self, event: Event):
        self.status_bar.config(text=f"({event.x}, {event.y})")

    def open_pdf(self, file_path: str = None):
        if not file_path:
            file_path = filedialog.askopenfilename(filetypes=[("PDF Files",
                                                               "*.pdf")])
        if file_path:
            self.reset()
            self.pdf = PdfFile(file_path)
            self.load_page()
            self.display_page()

    def load_page(self):
        pdf = self.pdf
        if pdf:
            page = pdf.get_current_page()
            self.page = page
            self.set_title(f"{pdf.file_path} - "
                           f"Page {pdf.current_page_idx + 1}/{pdf.pagecount}")

    def img_from_page(self):
        # Use pdf2image to convert the PDF page to an image
        images = convert_from_bytes(self.page.get_bytes(),
                                    dpi=self.get_dpi()*self.zoom_level)

        return images[0]

    def display_page(self):
        if self.page:
            # Convert current page to an image
            img = self.img_from_page()
            self.image = img
            tkimg = PhotoImage(img)
            self.tk_image = tkimg

            # Display the image on the canvas
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=tkimg)

    def zoom_in(self):
        # Increase zoom level by 10%
        self.zoom_level += 0.1
        self.display_page()

    def zoom_out(self):
        # Decrease zoom level by 10%
        self.zoom_level -= 0.1
        self.display_page()

    def prev_page(self):
        pdf = self.pdf
        if pdf:
            pdf.get_prev_page()
            self.load_page()
            self.display_page()

    def next_page(self):
        pdf = self.pdf
        if pdf:
            pdf.get_next_page()
            self.load_page()
            self.display_page()

    def start_draw(self, event: Event):
        # Store the starting point of the rectangle
        self.start_x, self.start_y = event.x, event.y

    def draw_rectangle(self, event: Event):
        # Draw a rectangle as the user drags the mouse
        self.clear_rect()
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y, outline="red",
            width=2,
        )
        # manually call since this event handler preempts the default
        self.update_coordinates(event)

    def end_draw(self, event: Event):
        # Finalize the rectangle coordinates
        if self.rect:
            self.end_x, self.end_y = event.x, event.y

    def get_dpi(self):
        return self.root.winfo_fpixels('1i')

    def save_selection(self):
        page = self.page
        if self.rect:
            # Get page dimensions
            mbox_width, mbox_height = page.get_size()

            # Convert image coordinates to page coordinates
            image_width, image_height = self.image.size
            media_startx = self.start_x/image_width*mbox_width
            media_endx = self.end_x/image_width*mbox_width
            # Flip the Y axis
            media_starty = (1 - self.start_y/image_height)*mbox_height
            media_endy = (1 - self.end_y/image_height)*mbox_height

            # Crop the page
            top = max(media_starty, media_endy)
            bottom = min(media_starty, media_endy)
            left = min(media_startx, media_endx)
            right = max(media_startx, media_endx)
            page.crop(top, bottom, left, right)

        if page.is_changed():
            # Save to a new PDF
            output_file = filedialog.asksaveasfilename(
                defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")]
            )
            if output_file:
                page.save(output_file)
                self.open_pdf(output_file)

    def open_chrome(self):
        open_new_tab(self.pdf_path)

    def rotate_left(self):
        page = self.page
        if page:
            page.rotate_left()
            self.display_page()

    def rotate_right(self):
        page = self.page
        if page:
            page.rotate_right()
            self.display_page()

    def clear_rect(self):
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = None

    def print_page(self):
        print_pdf(self.pdf.file_path)  # , self.page.render())
