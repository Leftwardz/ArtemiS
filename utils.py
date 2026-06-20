from app.utils.file_parser import FileUtils, get_sequence_from_str
from app.utils.window_geometry import get_monitor, calculate_center_screen_with_monitor, calculate_center_screen
from app.utils.barcode_generator import (
    create_barcode, create_barcode39, create_qrcode, create_datamatrix,
    change_proportion, get_image, convert_image_to_blob
)
from app.utils.printer_handler import set_default_printer, is_process_running, is_papersize_a4, print_pdf_file
from app.utils.text_utils import break_line

# Backward compatibility module bridge