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
