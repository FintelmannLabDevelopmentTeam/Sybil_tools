import PySimpleGUI as sg

from browse.src.window.user_input import UserInput
from common.utils.operating_system_utils import is_directory
from common.utils.string_utils import is_blank, is_not_blank


def validate_user_input(user_input: UserInput):
    summary = []

    if not is_directory(user_input.input_folder_directory):
        summary.append("Input folder directory does not exist")

    if is_blank(user_input.output_folder_name):
        summary.append("Output folder name was not specified")

    if is_blank(user_input.output_folder_directory):
        summary.append("Output folder directory was not specified")

    elif not is_directory(user_input.output_folder_directory):
        summary.append("Output folder saving directory does not exist")

    if len(summary) == 0:
        return True

    from common.gui.constants import FUTURA_Normal_FONT
    sg.popup("The following issues where encountered:", *summary, "",
             title="Verify your input",
             custom_text='Back',
             font=FUTURA_Normal_FONT)

    return False


def is_integer(x):
    return is_not_blank(x) and x.isnumeric()
