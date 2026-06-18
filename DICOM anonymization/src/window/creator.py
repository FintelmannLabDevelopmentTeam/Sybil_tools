import PySimpleGUI as sg

from PySimpleGUI import Window

from anonymize.src.window.constants import APP_NAME
from anonymize.src.window.gui.element_keys import SUBMIT_BUTTON_TEXT, OUTPUT_FOLDER_NAME_INPUT_KEY, \
    OUTPUT_FOLDER_DIRECTORY_INPUT_KEY, BROWSE_OUTPUT_FOLDER_BUTTON_KEY, BROWSE_INPUT_FOLDER_BUTTON_KEY, \
    INPUT_FOLDER_DIRECTORY_INPUT_KEY, THRESHOLD_INPUT_FIELD_KEY, USE_WHITELIST_KEY, ENTER_WHITELIST_TEXT_KEY, \
    WHITELIST_INPUT_FIELD_KEY, USE_BLACKLIST_KEY, ENTER_BLACKLIST_TEXT_KEY, BLACKLIST_INPUT_FIELD_KEY, \
    PROJECT_NAME_INPUT_FIELD_KEY, INPUT_CSV_FILE_PATH_INPUT_KEY, BROWSE_INPUT_CSV_FILE_BUTTON_KEY , FILE_PATH_KEY, \
    BROWSE_FILE_BUTTON_TEXT, FIRST_ROW_IS_HEADER_KEY, DELIMITER_IS_COMMA_KEY, DELIMITER_IS_SEMICOLON_KEY, CSV_TABLE_KEY, \
    MRN_COLUMN_NAME_INPUT_FIELD_KEY, ACCESSION_NUMBER_COLUMN_NAME_INPUT_FIELD_KEY, OUTPUT_CSV_FILE_PATH_OUTPUT_KEY, BROWSE_OUTPUT_CSV_FILE_BUTTON_KEY, \
    OUTPUT_CSV_FOLDER_DIRECTORY_INPUT_KEY, BROWSE_OUTPUT_CSV_FOLDER_BUTTON_KEY

from anonymize.src.window.user_input import UserInput
from common.gui.buttons import get_submit_button, get_exit_button, get_browse_folder_button, get_browse_file_button
from common.gui.constants import FUTURA_Normal_FONT
from common.gui.directory import get_output_folder_name_text, get_folder_name_input_box, \
    get_select_folder_directory_text, get_select_folder_directory_input_box
from download.src.window.gui.csv import *
from common.gui.file import get_path_to_selected_file_input_text
from common.gui.filters import get_general_filter_section
from common.gui.separator import get_line_separator
from common.gui.user_information import get_enter_project_name_text, get_enter_project_name_input_field, get_enter_accession_number_column_name_input_field, get_enter_accession_number_column_name_text, get_enter_mrn_column_name_input_field, get_enter_mrn_column_name_text


def create_window(user_input: UserInput):
    # The window layout in 2 sections

    configuration_section = [
        get_project_name(),
        get_input_folder_section(user_input),
        get_csv_file_configuration(user_input),
        get_filter_section(user_input),
        get_output_folder_section(user_input),
        
    ]

    submit_section = [
        [get_line_separator()],
        [sg.VerticalSeparator()],
        [
            get_submit_button(SUBMIT_BUTTON_TEXT), get_exit_button(),
        ]
    ]

    # ----- Full layout -----
    layout = configuration_section + submit_section

    window: Window = sg.Window(APP_NAME, layout, resizable=True, grab_anywhere=True, font=FUTURA_Normal_FONT,
                               size=(1280, 720))
    return window


def get_project_name():
    return [
        [get_enter_project_name_text(), get_enter_project_name_input_field(PROJECT_NAME_INPUT_FIELD_KEY)],
    ]


def get_filter_section(user_input: UserInput):
    return get_general_filter_section(user_input.use_whitelist, user_input.use_blacklist, user_input.whitelist, user_input.blacklist,
                                      THRESHOLD_INPUT_FIELD_KEY,
                                      USE_WHITELIST_KEY, ENTER_WHITELIST_TEXT_KEY, WHITELIST_INPUT_FIELD_KEY,
                                      USE_BLACKLIST_KEY, ENTER_BLACKLIST_TEXT_KEY, BLACKLIST_INPUT_FIELD_KEY)


def get_csv_file_configuration(user_input: UserInput):
    delimiter_is_comma = user_input.csv_delimiter == ","
    delimiter_is_semicolon = user_input.csv_delimiter == ";"
    return [
        [get_line_separator()],
        [sg.VerticalSeparator()],
        [get_select_csv_file_text_header(text='Select a CSV file with pseudonym mapping: (with columns mrn, accession, patient_ID)')],
        [get_path_to_selected_file_input_text(INPUT_CSV_FILE_PATH_INPUT_KEY),
         get_browse_folder_button(BROWSE_INPUT_CSV_FILE_BUTTON_KEY)],
        [get_select_folder_directory_text(text="Key sheet (PHI) output directory: ",
                                          tooltip="This is where the key_sheet_with_PHI CSV (linking pseudonyms back "
                                                  "to the original MRN/accession) will be saved."),
         get_select_folder_directory_input_box(OUTPUT_CSV_FOLDER_DIRECTORY_INPUT_KEY,
                                               default_directory=user_input.get_output_csv_folder_path()),
         get_browse_folder_button(BROWSE_OUTPUT_CSV_FOLDER_BUTTON_KEY)],
    ]

def get_input_folder_section(user_input):
    return [
        [get_select_folder_directory_text(text='DICOM files location: ', tooltip='The program will search for DICOM '
                                                                                 'files in the specified location and'
                                                                                 ' all its subfolders.'),
         get_select_folder_directory_input_box(key=INPUT_FOLDER_DIRECTORY_INPUT_KEY,
                                               default_directory=user_input.input_folder_directory, size=(28, 1)),
         get_browse_folder_button(BROWSE_INPUT_FOLDER_BUTTON_KEY)]
    ]


def get_output_folder_section(user_input):
    return [
        [get_line_separator()],
        [sg.VerticalSeparator()],
        [get_output_folder_name_text(),
         get_folder_name_input_box(OUTPUT_FOLDER_NAME_INPUT_KEY, default_text=user_input.output_folder_name)],
        [get_select_folder_directory_text(text="To directory: ", tooltip="This is where the output folder with the "
                                                                         "anonymized DICOM files will be saved."),
         get_select_folder_directory_input_box(OUTPUT_FOLDER_DIRECTORY_INPUT_KEY,
                                               default_directory=user_input.output_folder_directory),
         get_browse_folder_button(BROWSE_OUTPUT_FOLDER_BUTTON_KEY)]
    ]
