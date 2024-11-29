from cups import Connection


def cups_print_pdf_bytes(pdf_data: bytes):
    # Open a direct connection to the printer and send the data
    conn = Connection()
    printer_name = conn.getDefault()
    printer_attrs = conn.getPrinterAttributes(printer_name)
    printer_uri = printer_attrs["printer-uri-supported"]
    job_id = conn.createJob(printer_uri, "Python Print Job", {},
                            {"copies": 1})
    conn.sendDocument(printer_uri, job_id, pdf_data, "application/pdf",
                      last_document=True)
