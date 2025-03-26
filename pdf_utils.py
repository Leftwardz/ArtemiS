import PyPDF2
import os
import PIL
import io
import math
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader
from datetime import datetime
from utils import *
from Main import PopUpWindow, App
import traceback

pdfmetrics.registerFont(TTFont('Arial', 'fontes/Arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold', 'fontes/arialbd.ttf'))
pdfmetrics.registerFont(TTFont('Trebuchet ms', 'fontes/trebuc.ttf'))
pdfmetrics.registerFont(TTFont('Trebuchet MS', 'fontes/trebuc.ttf'))
pdfmetrics.registerFont(TTFont('Trebuchet ms-Bold', 'fontes/trebucbd.ttf'))
pdfmetrics.registerFont(TTFont('Trebuchet MS-Bold', 'fontes/trebucbd.ttf'))
pdfmetrics.registerFont(TTFont('Arial Narrow', 'fontes/arialn.ttf'))
pdfmetrics.registerFont(TTFont('Arial narrow', 'fontes/arialn.ttf'))
pdfmetrics.registerFont(TTFont('Arial narrow-Bold', 'fontes/arialnb.ttf'))
pdfmetrics.registerFont(TTFont('Arial Narrow-Bold', 'fontes/arialnb.ttf'))
pdfmetrics.registerFont(TTFont('Times New Roman', 'fontes/times.ttf'))
pdfmetrics.registerFont(TTFont('Times new roman', 'fontes/times.ttf'))
pdfmetrics.registerFont(TTFont('Times New Roman-Bold', 'fontes/timesbd.ttf'))
pdfmetrics.registerFont(TTFont('Times new roman-Bold', 'fontes/timesbd.ttf'))
pdfmetrics.registerFont(TTFont('Saira Extracondensed', 'fontes/SairaExtraCondensed-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Saira extracondensed', 'fontes/SairaExtraCondensed-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Saira Extracondensed-Bold', 'fontes/SairaExtraCondensed-Bold.ttf'))
pdfmetrics.registerFont(TTFont('Saira extracondensed-Bold', 'fontes/SairaExtraCondensed-Bold.ttf'))

pdfmetrics.registerFont(TTFont('Saira Extracondensed', 'fontes/SairaExtraCondensed-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Morganite Semibold', 'fontes/Morganite-Semibold.ttf'))
pdfmetrics.registerFont(TTFont('Morganite semibold', 'fontes/Morganite-Semibold.ttf'))


def join_pdfs(pdf_list, joined_pdf_name):
    merger = PyPDF2.PdfMerger()

    for pdf in pdf_list:
        merger.append(pdf)

    with open(joined_pdf_name, 'wb') as result:
        merger.write(result)


def get_element(lst, index, default=None):
    try:
        return lst[index]
    except IndexError:
        return default


def normalize_rotated_x_y(x1, y1, angle):
    # No reportlab a posicao x e y é afetada pela rotação, calculo realizado para normalizar
    if angle == 90:
        aux_x, aux_y = x1, y1
        x1 = - aux_y + A4[1]
        y1 = - aux_x
    elif angle == 180:
        x1 = -x1
        y1 = -A4[1] + y1
    elif angle == 270:
        aux_x, aux_y = x1, y1
        x1 = aux_y - A4[1]
        y1 = aux_x
    else:
        y1 = A4[1] - y1

    return x1, y1


def filter_segments(segment_id, item_list, test):
    if test:
        return list(filter(lambda item: item['segment_id'] == segment_id, item_list))
    else:
        return list(filter(lambda item: item['segment_id'] == segment_id and 'IGNORE' not in item['tag'], item_list))


def generate_test_pdf(items=None, path="temp/text.pdf", orientation='Default'):
    pdf = canvas.Canvas(path, pagesize=A4)
    qtd_pages = 1
    for page in range(qtd_pages):
        pdf.setDash([10, 4])
        pdf.setLineWidth(0.5)

        if orientation == 0:
            # Default AR - Vertical - 3 for paper
            pdf.line(0, 2 * (A4[1] // 3), A4[0], 2 * (A4[1] // 3))
            pdf.line(0, A4[1] // 3, A4[0], A4[1] // 3)
            pdf.setDash([])

            # AR Vertical positions, 3 ARs for A4
            ar_height = A4[1] // 3
            position_dict = {
                0: 0,
                1: ar_height,
                2: ar_height * 2
            }
            for i in range(3):
                draw_ar(items, pdf, offset_y=position_dict[i], is_test=True)

        elif orientation == 1:
            # Horizontal AR - 2 for paper
            pdf.line((A4[0] // 2), 0, (A4[0] // 2), A4[1])
            pdf.setDash([])

            ar_width = A4[0] // 2
            position_dict = {
                0: 0,
                1: ar_width
            }

            for i in range(2):
                draw_ar(items, pdf, offset_x=position_dict[i], is_test=True)

        elif orientation == 2:
            # Full size A4 AR
            pdf.setDash([])
            draw_ar(items, pdf, is_test=True)

        elif orientation == 3:
            # Vertical AR - 2 for paper
            pdf.line(0, (A4[1] // 2), A4[0], (A4[1] // 2))
            pdf.setDash([])

            ar_height = A4[1] // 2
            position_dict = {
                0: 0,
                1: ar_height
            }

            for i in range(2):
                draw_ar(items, pdf, offset_y=position_dict[i], is_test=True)

        pdf.showPage()
    pdf.save()


def write_text_to_pdf(items, files_lines, master: App, orientation_list, path, is_remake=False, printer=None):
    """
    :param items: List of Dictionarys with all the drawings from canvas
    :param files_lines: List of files with a list of the lines, [[file1_lines], [file2_lines]]
    :param master: App Interface GUI
    :param orientation_list: Define what is the type of AR [default, 2 horizontal AR or Full A4 AR]
    :param is_remake: Define its remake or not
    """

    # Todos os PDFs serão salvos em um lista para posteriormente serem agrupados e impressos de uma vez
    completed_pdfs = []

    # Arquivos usados para o processamento serão movidos para Old
    files_to_move = []
    total = len(files_lines)

    for i, lines in enumerate(files_lines):
        try:
            # master.create_progress_bar()
            original_filepath = lines[-1]
            filename, extension = os.path.splitext(os.path.basename(original_filepath)) # Get the filename only
            if is_remake:
                date = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = filename + '_Remake_' + date
            complete_path = os.path.join(path, filename + '.pdf')

            pdf = canvas.Canvas(complete_path, pagesize=A4)
            lines = lines[:-1]  # Remove the last item, because is the filename

            if orientation_list[i] == '0':
                configure_3vertical_ar(pdf, lines, items, master, i, total, printer, filename)
            elif orientation_list[i] == '1':
                configure_horizontal_ar(pdf, lines, items, master, i, total, printer, filename)
            elif orientation_list[i] == '2':
                configure_full_A4_ar(pdf, lines, items, master, i, total, printer, filename)
            elif orientation_list[i] == '3':
                configure_2vertical_ar(pdf, lines, items, master, i, total, printer, filename)

            pdf.save()
            files_to_move.append(original_filepath)
            completed_pdfs.append(complete_path)
            # master.destroy_progress_bar()
            master.loading_frame.update_progressbar(printer, 1, 'Finalizando PDF')

        except Exception as e:
            master.loading_frame.show_error(printer, traceback.format_exc())
            break

    master.loading_frame.update_progressbar(printer, 1, 'Juntando PDFs')
    # No final do For, na qual todos os PDFs estão gerados, será feito o agrupamento e será impresso
    first_pdf = completed_pdfs[0].replace('.pdf', '')[-6:]
    last_pdf = completed_pdfs[-1].replace('.pdf', '')[-6:]
    date = datetime.now().strftime('%Y%m%d_%H%M%S')
    joined_pdf_filename = f'{first_pdf}_{last_pdf}_{date}.pdf'
    joined_pdf_filepath = os.path.join(path, joined_pdf_filename)

    join_pdfs(completed_pdfs, joined_pdf_filepath)

    master.open_or_print_pdf(joined_pdf_filepath, files_to_move, is_remake, printer)


def configure_3vertical_ar(pdf, filelines, items, master, current_index, total, printer, filename):
    qtd_pages = math.ceil(len(filelines) / 3)

    first_ar = filelines[0:qtd_pages]
    second_ar = filelines[qtd_pages:qtd_pages * 2]
    third_ar = filelines[qtd_pages * 2:]

    ar_height = A4[1] // 3
    y_offset_dict = {
        0: 0,
        1: ar_height,
        2: ar_height * 2
    }
    for page in range(qtd_pages):
        if get_element(first_ar, page):
            draw_ar(items[current_index], pdf, first_ar[page][1], offset_y=y_offset_dict[0], counter=first_ar[page][0], filename=filename)
        if get_element(second_ar, page):
            draw_ar(items[current_index], pdf, second_ar[page][1], offset_y=y_offset_dict[1], counter=second_ar[page][0], filename=filename)
        if get_element(third_ar, page):
            draw_ar(items[current_index], pdf, third_ar[page][1], offset_y=y_offset_dict[2], counter=third_ar[page][0], filename=filename)

        # Draw AuxLines
        pdf.setDash([10, 4])
        pdf.setLineWidth(0.5)
        pdf.line(0, 2 * (A4[1] // 3), A4[0], 2 * (A4[1] // 3))
        pdf.line(0, A4[1] // 3, A4[0], A4[1] // 3)
        pdf.setDash([])

        pdf.showPage()
        progress = (page + 1) / qtd_pages
        text = f'{current_index + 1}/{total}'
        master.loading_frame.update_progressbar(printer, progress, text)
        master.update_idletasks()


def configure_2vertical_ar(pdf, filelines, items, master, current_index, total, printer, filename):
    qtd_pages = math.ceil(len(filelines) / 2)

    first_ar = filelines[0:qtd_pages]
    second_ar = filelines[qtd_pages:qtd_pages * 2]

    ar_height = A4[1] // 2
    y_offset_dict = {
        0: 0,
        1: ar_height,
    }
    for page in range(qtd_pages):
        if get_element(first_ar, page):
            draw_ar(items[current_index], pdf, first_ar[page][1], offset_y=y_offset_dict[0], counter=first_ar[page][0], filename=filename)
        if get_element(second_ar, page):
            draw_ar(items[current_index], pdf, second_ar[page][1], offset_y=y_offset_dict[1], counter=second_ar[page][0], filename=filename)

        # Draw AuxLines
        pdf.setDash([10, 4])
        pdf.setLineWidth(0.5)
        pdf.line(0, (A4[1] // 2), A4[0], (A4[1] // 2))
        pdf.setDash([])

        pdf.showPage()
        progress = (page + 1) / qtd_pages
        text = f'{current_index + 1}/{total}'
        master.loading_frame.update_progressbar(printer, progress, text)
        master.update_idletasks()


def configure_horizontal_ar(pdf, filelines, items, master, current_index, total, printer, filename):
    qtd_pages = math.ceil(len(filelines) / 2)

    first_ar = filelines[0:qtd_pages]
    second_ar = filelines[qtd_pages:qtd_pages * 2]

    ar_width = A4[0] // 2
    x_offset_dict = {
        0: 0,
        1: ar_width,
    }
    for page in range(qtd_pages):
        if get_element(first_ar, page):
            draw_ar(items[current_index], pdf, first_ar[page][1], offset_x=x_offset_dict[0], counter=first_ar[page][0], filename=filename)
        if get_element(second_ar, page):
            draw_ar(items[current_index], pdf, second_ar[page][1], offset_x=x_offset_dict[1], counter=second_ar[page][0], filename=filename)

        # Draw AuxLines
        pdf.setDash([10, 4])
        pdf.setLineWidth(0.5)
        pdf.line((A4[0] // 2), 0, (A4[0] // 2), A4[1])
        pdf.setDash([])

        pdf.showPage()
        progress = (page + 1) / qtd_pages
        text = f'{current_index + 1}/{total}'
        master.loading_frame.update_progressbar(printer, progress, text)
        master.update_idletasks()


def configure_full_A4_ar(pdf, filelines, items, master, current_index, total, printer, filename):
    qtd_pages = len(filelines)

    first_ar = filelines[0:qtd_pages]

    for page in range(qtd_pages):
        if get_element(first_ar, page):
            draw_ar(items[current_index], pdf, first_ar[page][1], counter=first_ar[page][0], filename=filename)

        pdf.showPage()
        progress = (page + 1) / qtd_pages
        text = f'{current_index + 1}/{total}'
        master.loading_frame.update_progressbar(printer, progress, text)
        master.update_idletasks()


def draw_ar(items, pdf_canvas, file_columns=None, counter=None, offset_x=0, offset_y=0, is_test=False, filename='Test'):
    painted_segments_id = []

    for item in items:
        x1 = float(item['x1']) / 2 + offset_x
        y1 = float(item['y1']) / 2 + offset_y
        x2 = float(item['x2']) / 2 + offset_x if item['x2'] else None
        y2 = float(item['y2']) / 2 + offset_y if item['y2'] else None
        proportion = int(item['proportion']) / 2 if item['proportion'] else None
        orientation = int(item['orientation']) if item['orientation'] else 0
        column = None

        if item['file_columns'] and not is_test:
            column = item['file_columns'].split('.')
            column = [int(i.replace('Coluna_', '')) - 1 for i in column]
            # if not get_element(file_columns, column[0]):
            #     raise f'Coluna {int(column[0]) + 1}, não existe no arquivo\nWork: {file_columns[3]}'

        if item['item_type'] in ['text', 'counter', 'barcode_text']:
            font_style = '-' + item['font_style'].capitalize() if item['font_style'] == 'bold' else ''
            font = [item['font_name'].capitalize() + font_style, (float(item['font_size']) / 2) * 1.35]

            angle = int(item['orientation'])

            x1, y1 = normalize_rotated_x_y(x1, y1, angle)

            pdf_canvas.rotate(angle)
            pdf_canvas.setFont(*font)
            if is_test or item['item_type'] == 'text':
                pdf_canvas.drawString(x1, y1 + 2, item['text'])
            else:
                if item['item_type'] == 'counter':
                    pdf_canvas.drawString(x1, y1 + 2, str(counter + 1).zfill(7))
                else:
                    if get_element(file_columns, column[0]):
                        pdf_canvas.drawString(x1, y1 + 2, file_columns[column[0]].strip())

            pdf_canvas.rotate(-angle)  # Voltar ao angulo padrao

        elif item['item_type'] == 'rectangle':
            if item['dashed'] == '4':
                # Por erro de proporção, é feito um conversão do dash "Grande"
                pdf_canvas.setDash([4, 2])
            elif item['dashed'] == '40':
                pdf_canvas.setDash([10, 4])
            x_rect = min(x1, x2)
            y_rect = max(y1, y2)
            width_rect = max(x1, x2) - x_rect
            height_rect = y_rect - min(y1, y2)

            pdf_canvas.setLineWidth(float(item['thickness']) / 2)
            pdf_canvas.rect(x_rect, A4[1] - y_rect, width_rect, height_rect)
            pdf_canvas.setDash([])

        elif item['item_type'] == 'line':
            if item['dashed'] == '4':
                # Por erro de proporção, é feito um conversão do dash "Grande"
                pdf_canvas.setDash([4, 2])
            elif item['dashed'] == '40':
                pdf_canvas.setDash([10, 4])

            pdf_canvas.setLineWidth(float(item['thickness']) / 2)
            pdf_canvas.line(x1, A4[1] - y1, x2, A4[1] - y2)
            pdf_canvas.setDash([])

        elif item['item_type'] == 'segment':
            font_style = '-' + item['font_style'].capitalize() if item['font_style'] == 'bold' else ''
            font = [item['font_name'] + font_style, (float(item['font_size']) / 2) * 1.35]

            angle = int(item['orientation'])
            x1, y1 = normalize_rotated_x_y(x1, y1, angle)

            # Desenhar todos os segmentos
            if item['segment_id'] not in painted_segments_id:
                painted_segments_id.append(item['segment_id'])
                pdf_canvas.rotate(angle)
                for i, segment in enumerate(filter_segments(item['segment_id'], items, is_test)):
                    pdf_canvas.setFont(*font)
                    if is_test:
                        pdf_canvas.drawString(x1, y1 + 2, segment['text'])
                    else:
                        if get_element(file_columns, column[i]):
                            text = file_columns[column[i]].strip()
                            text = break_line(text, item['char_limit'])
                            pdf_canvas.drawString(x1, y1 + 2, text[0])

                            # Verify if needs to break the line
                            if text[1]:
                                y1 -= float(item['line_distance']) / 2
                                pdf_canvas.drawString(x1, y1 + 2, text[1])

                    y1 -= float(item['line_distance']) / 2
                pdf_canvas.rotate(-angle)

        elif item['item_type'] == 'barcode':
            path = f'temp/barcode{int(x1)}{int(y1)}{counter}{filename}'
            w, h = item['barcode_width'], item['barcode_height']

            if is_test:
                create_barcode(item['text'], w, h, path=path)
            else:
                if get_element(file_columns, column[0]):
                    create_barcode(file_columns[column[0]].strip(), w, h, path=path)
                else:
                    continue

            with PIL.Image.open(path + '.png') as img:
                if orientation > 0:
                    img = img.rotate(orientation, expand=True)
                    img.save(path + '.png')
                largura, altura = img.size

            largura *= (proportion / 100)
            altura *= (proportion / 100)

            pdf_canvas.drawImage(path + '.png', x1, A4[1] - y1, width=largura, height=altura, mask="auto")
            os.remove(os.path.abspath(path + '.png'))

        elif item['item_type'] == 'barcode39':
            path = f'temp/barcode39{int(x1)}{int(y1)}{counter}{filename}'
            w, h = item['barcode_width'], item['barcode_height']

            if is_test:
                create_barcode39(item['text'], w, h, path=path)
            else:
                if get_element(file_columns, column[0]):
                    create_barcode39(file_columns[column[0]].strip(), w, h, path=path)
                else:
                    continue

            with PIL.Image.open(path + '.png') as img:
                if orientation > 0:
                    img = img.rotate(orientation, expand=True)
                    img.save(path + '.png')
                largura, altura = img.size

            largura *= (proportion / 100)
            altura *= (proportion / 100)

            pdf_canvas.drawImage(path + '.png', x1, A4[1] - y1, width=largura, height=altura)
            os.remove(os.path.abspath(path + '.png'))

        elif item['item_type'] == 'barcodeQR':
            if item['text'].strip() == '':
                continue

            path = f'temp/QRbarcode{int(x1)}{int(y1)}{counter}{filename}.png'

            if is_test:
                create_qrcode(item['text'], path=path)
            else:
                if get_element(file_columns, column[0]):
                    create_qrcode(file_columns[column[0]].strip(), path=path)
                else:
                    continue

            with PIL.Image.open(path) as img:
                if orientation > 0:
                    img = img.rotate(orientation, expand=True)
                    img.save(path)
                largura, altura = img.size

            largura *= (proportion / 100)
            altura *= (proportion / 100)

            pdf_canvas.drawImage(path, x1, A4[1] - y1, width=largura, height=altura)
            os.remove(os.path.abspath(path))

        elif item['item_type'] == 'barcodeMatrix':
            path = f'temp/Matrixbarcode{int(x1)}{int(y1)}{counter}{filename}.png'

            if is_test:
                create_datamatrix(item['text'], path=path)
            else:
                if get_element(file_columns, column[0]):
                    create_datamatrix(file_columns[column[0]].strip(), path=path)
                else:
                    continue

            with PIL.Image.open(path) as img:
                if orientation > 0:
                    img = img.rotate(orientation, expand=True)
                    img.save(path)
                largura, altura = img.size

            largura *= (proportion / 100)
            altura *= (proportion / 100)

            pdf_canvas.drawImage(path, x1, A4[1] - y1, width=largura, height=altura)
            os.remove(os.path.abspath(path))

        elif item['item_type'] == 'image':
            if orientation == 0:
                image_reader = ImageReader(io.BytesIO(item['image']))

                with PIL.Image.open(io.BytesIO(item['image'])) as img:
                    largura, altura = img.size

                largura *= (proportion / 100)
                altura *= (proportion / 100)

                pdf_canvas.drawImage(image_reader, x1, A4[1] - y1, width=largura, height=altura)

            else:
                path = f'temp/image{int(x1)}{int(y1)}{counter}{filename}.png'

                with Image.open(io.BytesIO(item['image'])) as img:
                    img = img.rotate(orientation, expand=True)
                    largura, altura = img.size
                    img.save(path)

                largura *= (proportion / 100)
                altura *= (proportion / 100)

                pdf_canvas.drawImage(path, x1, A4[1] - y1, width=largura, height=altura)
                os.remove(os.path.abspath(path))


if __name__ == '__main__':
    pass