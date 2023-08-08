""" Varous helping function for openpyxl """

from typing import NoReturn

from openpyxl.worksheet.worksheet import Worksheet


def columns_best_fit(worksheet: Worksheet, row_blacklist: list) -> NoReturn:
    """Make all columns best fit regarding their content.

    :param worksheet: The worksheet to work on
    :param row_blacklist: List of row indexes that should not take part into the fit."""
    for column in worksheet.columns:
        max_length = max(
            len(str(cell.value)) for cell in column if cell.row not in row_blacklist
        )
        worksheet.column_dimensions[column[0].column_letter].width = (
            max_length + 2
        ) * 1.2
