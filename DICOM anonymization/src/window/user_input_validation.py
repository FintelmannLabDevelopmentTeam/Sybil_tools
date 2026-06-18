import PySimpleGUI as sg

from anonymize.src.window.user_input import UserInput
from common.utils.operating_system_utils import is_directory
from common.utils.string_utils import is_blank, is_not_blank


def validate_user_input(user_input: UserInput):
    summary = []
    print("[DEBUG] Validating user input... {}".format(user_input.get_summary_string()))
    if is_blank(user_input.project_name):
        summary.append("No project name was specified")

    if not is_integer(user_input.threshold):
        summary.append("Threshold was not specified")

    if not is_directory(user_input.input_folder_directory):
        summary.append("Input folder directory does not exist")

    if is_blank(user_input.get_output_csv_folder_path()):
        summary.append("Key sheet (PHI) output directory was not specified")
    else:
        print("[DEBUG] Key sheet CSV will be saved in: %s" % user_input.get_output_csv_folder_path())

    if is_blank(user_input.output_folder_name):
        summary.append("Output folder name was not specified")

    if is_blank(user_input.output_folder_directory):
        summary.append("Output folder directory was not specified")

    elif not is_directory(user_input.output_folder_directory):
        summary.append("Output folder saving directory does not exist")

    if is_blank(user_input.input_csv_file_path):
        print("[DEBUG] Input MRN/ACC to ID CSV file path was not specified")
    elif not user_input.input_csv_file_path.lower().endswith('.csv'):
        # bounce if there is a file but it is not a csv file
        summary.append("Input MRN/ACC to ID file is not a CSV file")

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
