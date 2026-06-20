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
