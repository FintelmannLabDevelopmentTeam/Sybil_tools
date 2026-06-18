import PySimpleGUI as sg

from PySimpleGUI import Window

from browse.src.window.constants import APP_NAME
from browse.src.window.gui.element_keys import SUBMIT_BUTTON_TEXT, INPUT_FOLDER_DIRECTORY_INPUT_KEY, \
    BROWSE_INPUT_FOLDER_BUTTON_KEY, OUTPUT_FOLDER_NAME_INPUT_KEY, OUTPUT_FOLDER_DIRECTORY_INPUT_KEY, \
    BROWSE_OUTPUT_FOLDER_BUTTON_KEY, CONTENT_OF_A_FOLDER_BELONGS_TO_SAME_STUDY_CHECKBOX_KEY
from browse.src.window.user_input import UserInput
from common.gui.buttons import get_submit_button, get_exit_button, get_browse_folder_button
from common.gui.constants import FUTURA_Normal_FONT
from common.gui.directory import get_output_folder_name_text, get_folder_name_input_box, \
    get_select_folder_directory_text, get_select_folder_directory_input_box
from common.gui.separator import get_line_separator


def create_window(user_input: UserInput):
    # The window layout in 2 sections

    configuration_section = [
        get_input_folder_section(user_input),
        get_checkbox_content_of_a_folder_belongs_to_same_study(user_input),
        get_output_folder_section(user_input)
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
                                                                         "CSV file containing read header information will be saved."),
         get_select_folder_directory_input_box(OUTPUT_FOLDER_DIRECTORY_INPUT_KEY,
                                               default_directory=user_input.output_folder_directory),
         get_browse_folder_button(BROWSE_OUTPUT_FOLDER_BUTTON_KEY)]
    ]


def get_checkbox_content_of_a_folder_belongs_to_same_study(user_input):
    return [sg.Checkbox('The content of a folder belongs always to the same series', enable_events=True, default=user_input.is_content_of_a_folder_belongs_to_same_study, key=CONTENT_OF_A_FOLDER_BELONGS_TO_SAME_STUDY_CHECKBOX_KEY)]
