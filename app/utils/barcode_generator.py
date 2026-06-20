from barcode import Code128, Code39
from barcode.writer import ImageWriter
from PIL import ImageTk, Image
from pylibdmtx.pylibdmtx import encode
import pyqrcode
import io


def create_barcode(code, width, height, path='temp/codigo_de_barras'):
    barcode_aux = Code128(code, writer=ImageWriter())
    options = {"module_width": float(width), "module_height": float(height), "write_text": False, "quiet_zone": 0}

    barcode_aux.save(path, options)


def create_barcode39(code, width, height, path='temp/codigo_de_barras39'):
    barcode_aux = Code39(code, writer=ImageWriter(), add_checksum=False)
    options = {"module_width": float(width), "module_height": float(height), "write_text": False, "quiet_zone": 0}

    barcode_aux.save(path, options)


def create_qrcode(code, path='temp/qr_code.png'):
    qr = pyqrcode.create(code)
    qr.png(path, scale=5, module_color='#000000', background='#ffffff')


def create_datamatrix(code, path='temp/dmtx.png'):
    encoded = encode(code.encode('utf8'))
    img = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    img.save(path)


def change_proportion(image, proportion, orientation=0):
    if type(proportion) != int:
        raise Exception('Proportion must be a Interger')

    percent = proportion / 100
    original_image = image

    if orientation > 0:
        image = image.rotate(orientation, expand=True)

    w, h = image.size
    w, h = int(w * percent), int(h * percent)

    image = image.resize((w, h))

    image = image.convert("RGBA")
    img_tk = ImageTk.PhotoImage(image)

    img_gray = image.convert("L")
    img_gray = img_gray.point(lambda x: x if x not in list(range(40)) else 128)
    img_gray_tk = ImageTk.PhotoImage(img_gray)

    return [img_tk, img_gray_tk, original_image, proportion, orientation]


def get_image(filepath='', blob=''):
    """
    :param filepath: path to the image
    :param blob: if you use the blob from sqlite, it will ignore the filepath
    :return: A list with Image tkinter for canvas, gray TkImage for canvas, original Image, proportion and orientation
    """

    if blob:
        image_stream = io.BytesIO(blob)
        img = Image.open(image_stream)
    else:
        img = Image.open(filepath)

    # Transform image to RGBA
    img = img.convert("RGBA")
    img_tk = ImageTk.PhotoImage(img)

    img_gray = img.convert("L")
    img_gray = img_gray.point(lambda x: x if x not in list(range(40)) else 128)
    img_gray_tk = ImageTk.PhotoImage(img_gray)

    return [img_tk, img_gray_tk, img, 100, 0]


def convert_image_to_blob(image):
    """
    :param image: Object PIL Image
    :return: BLOB Image Data
    """
    image_stream = io.BytesIO()
    image.save(image_stream, format='PNG')
    image_data = image_stream.getvalue()
    return image_data
