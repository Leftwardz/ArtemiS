from barcode import Code128, Code39
from barcode.writer import ImageWriter
from PIL import ImageTk, Image, ImageFilter
from pylibdmtx.pylibdmtx import encode
from pylibdmtx.pylibdmtx import decode
from screeninfo import get_monitors
import os
import io
import datamatrix
import win32print
import pyqrcode
import win32api
import win32com.client
import subprocess
import win32ui
import psutil
from time import sleep
import csv
from datetime import datetime
import re

class FileUtils:
    def __init__(self, path):
        try:
            self.lines = []
            with open(path, 'r', encoding='UTF-8') as arquivo_csv:
                csv_reader = csv.reader(arquivo_csv, delimiter=';')
                for line in csv_reader:
                    if line:
                        self.lines.append(line)
        except UnicodeDecodeError:
            self.lines = []
            with open(path, 'r', encoding='ANSI') as arquivo_csv:
                csv_reader = csv.reader(arquivo_csv, delimiter=';')
                for line in csv_reader:
                    if line:
                        self.lines.append(line)
        finally:
            self.lines = list(enumerate(self.lines))

    def get_element(self, lst, index, default=None):
        try:
            return lst[index]
        except IndexError:
            return default

    def get_first_line_column(self, column):
        first_line = self.lines[0][1]
        return self.get_element(first_line, column, '')

    def return_filelines(self):
        return self.lines.copy()

    def search_by_rangelist(self, range_list):
        result = []
        for i in range_list:
            try:
                result.append(self.lines[i - 1])
            except IndexError:
                continue

        return result

    def search_int_with_list(self, int_list: list, column: int):
        """
        This function search for a exact INT match in a specific column

        :param int_list: [2,1,5,6]
        :param column: Column to search the string in file
        :return: List with the ranges
        """
        result = []

        for line in self.lines:
            try:
                if int(line[1][column]) in int_list:
                    result.append(line)

            except (ValueError, IndexError):
                continue

        return result

    def search_string_in_column(self, column: int, text: str):
        result = []

        text = text.upper()
        pattern = f'^{text.replace("%", "(.+?)")}'

        for line in self.lines:
            if re.search(pattern, line[1][column].upper()):
                result.append(line)

        return result

    @classmethod
    def write_log_file(cls, filepath, content):
        data = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        with open(filepath, 'a', encoding='UTF-8') as file:
            file.write('\n\n' + data + '\n')
            file.write(str(content))



def get_sequence_from_str(range_str):
    """
    :param range_str: string in this format: 1-4,6,9
    :return: list [1,2,3,4,6,9]
    """
    result = []

    range_str = range_str.split(',')

    for i in range_str:
        if '-' in i:
            initial = int(i.split('-')[0]) if int(i.split('-')[0]) else 0
            end = int(i.split('-')[1]) + 1
            for j in range(initial, end):
                result.append(j)
        else:
            result.append(int(i))

    return result

def get_monitor(master):
    """
    Get the index of the monitor where the widget is located.
    :param master: The widget for which to determine the monitor.
    :return: Index of the monitor (0 for the first monitor, 1 for the second, and so on).
    """
    widget_x = master.winfo_rootx() + master.winfo_width() / 2

    monitors = get_monitors()

    for index, monitor in enumerate(monitors):
        if monitor.x <= widget_x < monitor.x + monitor.width:
            return index

    return -1


def calculate_center_screen_with_monitor(master, width: int, height: int, monitor_index: int, move_x=0, move_y=0):
    """
    Calculate the geometry to center the app on a specific monitor based on the position of the master widget.
    :param master: The widget to use as a reference for positioning.
    :param width: The width of the app.
    :param height: The height of the app.
    :param monitor_index: Index of the target monitor (0 for the first monitor, 1 for the second, and so on).
    :param move_x: Optional x-axis offset.
    :param move_y: Optional y-axis offset.
    :return: The geometry string to center the app on the specified monitor.
    """
    master_x = master.winfo_rootx()
    master_y = master.winfo_rooty()

    monitors = get_monitors()

    if 0 <= monitor_index < len(monitors):
        target_monitor = monitors[monitor_index]
        x = target_monitor.x + (target_monitor.width / 2) - (width / 2) + move_x
        y = target_monitor.y + (target_monitor.height / 2) - (height / 2) + move_y
    else:
        # Default to centering on the primary monitor if the specified monitor index is invalid
        primary_monitor = monitors[0]
        x = primary_monitor.x + (primary_monitor.width / 2) - (width / 2) + move_x
        y = primary_monitor.y + (primary_monitor.height / 2) - (height / 2) + move_y

    return "%dx%d+%d+%d" % (width, height, x, y)


def calculate_center_screen(width: int, height: int, window, move_x=0, move_y=0):
    """
    Receive the width and height from the app, and center in the screen
    :param width: width from the app
    :param height: height from the app
    :param window: customtkinter CTk, Frame or TopLevel object
    :return: return the geometry to center the app to the screen
    """
    screen_width, screen_height = window.winfo_screenwidth(), window.winfo_screenheight()
    x, y = (screen_width / 2) - (width / 2), (screen_height / 2) - (height / 2)
    return "%dx%d+%d+%d" % (width, height, x + move_x, y + move_y)


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


def set_default_printer(printer):
    win32print.SetDefaultPrinter(printer)


def is_process_running(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            return True
    return False


def is_papersize_a4(printer_name, paper_size=9):
    try:
        # Obter um identificador de impressora
        PRINTER_DEFAULTS = {"DesiredAccess": win32print.PRINTER_ACCESS_USE}
        printer_handle = win32print.OpenPrinter(printer_name, PRINTER_DEFAULTS)

        try:
            try:
                # Isso irá falhar com um erro, mas retornará o tamanho necessário
                printer_info = win32print.GetPrinter(printer_handle, 2)
            except pywintypes.error as e:
                if e.winerror == 122:  # ERROR_INSUFFICIENT_BUFFER
                    needed_size = e.args[2]
                    printer_info = win32print.GetPrinter(printer_handle, 2, needed_size)
                else:
                    raise

            if int(paper_size) == 0:
                return True
            else:
                if printer_info['pDevMode'].PaperSize == int(paper_size):
                    return True
                else:
                    return False

        finally:
            # Garantir que o identificador da impressora seja fechado
            win32print.ClosePrinter(printer_handle)

    except Exception as e:
        path = 'Errors_Logs.txt'
        FileUtils.write_log_file(path, e)
        return False


def print_pdf_file(pdf_path, printer_name, exe_index):
    # set_default_printer(printer_name)
    executables = [
        'PDFtoPrinter.exe',
        'PDFtoPrinter_2.exe',
        'PDFtoPrinter_3.exe',
        'PDFtoPrinter_4.exe',
        'PDFtoPrinter_5.exe',
    ]

    command = [executables[exe_index], 'focus="Impressão de AR"', printer_name, pdf_path]

    try:
        subprocess.call(command, shell=True)
    except subprocess.CalledProcessError:
        raise 'Erro ao enviar arquivo para a impressora'


def break_line(text, limit):
    text_array = text.split()
    if int(limit) == 0 or text.strip() == '':
        line1 = text
        line2 = None
    else:
        line1 = text_array[0]  # Mantém sempre a primeira palavra na primeira linha
        remaining_characters = int(limit) - len(line1)
        line2 = None

        for i, word in enumerate(text_array[1:], start=1):
            if len(line1) + len(word) + 1 <= int(limit):
                line1 += ' ' + word
                remaining_characters -= len(word) + 1
            else:
                line2 = ' '.join(text_array[i:])
                break

    return [line1, line2]


if __name__ == '__main__':
    import numpy as np


    # Implementação simples de k-means
    def k_means(X, k, max_iters=100, tol=1e-4):
        # Inicialização dos centróides de forma aleatória
        centroids = X[np.random.choice(range(X.shape[0]), k, replace=False)]

        for _ in range(max_iters):
            # Atribuição de pontos aos clusters mais próximos
            labels = np.argmin(np.linalg.norm(X - centroids[:, np.newaxis], axis=2), axis=0)

            # Atualização dos centróides
            new_centroids = np.array([X[labels == i].mean(axis=0) for i in range(k)])

            # Verifica a convergência
            if np.linalg.norm(new_centroids - centroids) < tol:
                break

            centroids = new_centroids

        return labels, centroids


    # Dados de exemplo
    # Substitua esta parte pelo seu carregamento real de dados
    np.random.seed(42)
    X = np.random.rand(100, 2)

    # Número de clusters
    k = 3

    # Executa o k-means
    labels, centroids = k_means(X, k)

    # Exibe os resultados
    for i in range(k):
        cluster_points = X[labels == i]
        print(f'Cluster {i + 1}: {cluster_points}')
        print(f'Centróide {i + 1}: {centroids[i]}')