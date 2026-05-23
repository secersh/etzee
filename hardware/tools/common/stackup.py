"""KiCad PCB stackup text helpers."""

import re


def replace_stackup(text, new_block):
    marker = '\t\t(stackup'
    start = text.find(marker)
    if start == -1:
        return None, "no (stackup ...) block found"

    depth = 0
    end = start
    for i, ch in enumerate(text[start:], start):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if text[end:end + 1] == "\n":
        end += 1

    return text[:start] + new_block + "\n" + text[end:], None


def replace_general_thickness(text, total_thickness):
    pattern = re.compile(r'(\n\t\(general\n\t\t\(thickness )([0-9.]+)(\)\n)')
    new_text, count = pattern.subn(rf'\g<1>{total_thickness}\g<3>', text, count=1)
    if count == 0:
        return text, "no general thickness found"
    return new_text, None


def apply_stackup_text(text, manufacturer, total_thickness):
    new_text, err = replace_stackup(text, manufacturer.stackup(total_thickness))
    if err:
        return text, err
    return replace_general_thickness(new_text, total_thickness)
