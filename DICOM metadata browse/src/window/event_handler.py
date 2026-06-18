import PySimpleGUI as sg
from PySimpleGUI import Window

from browse.src.browse import browse
from browse.src.window.gui.element_keys import EXIT_BUTTON_TEXT, BROWSE_INPUT_FOLDER_BUTTON_KEY, \
    BROWSE_OUTPUT_FOLDER_BUTTON_KEY, SUBMIT_BUTTON_TEXT, INPUT_FOLDER_DIRECTORY_INPUT_KEY, \
    OUTPUT_FOLDER_DIRECTORY_INPUT_KEY, OUTPUT_FOLDER_NAME_INPUT_KEY, \
    CONTENT_OF_A_FOLDER_BELONGS_TO_SAME_STUDY_CHECKBOX_KEY
from browse.src.window.user_input import UserInput
from browse.src.window.user_input_validation import validate_user_input
from common.gui.directory import browse_and_select_directory


def handle_events(window: Window, event, values, user_input: UserInput):
    if event == EXIT_BUTTON_TEXT or event == sg.WIN_CLOSED:
        handle_exit_event(window, values, user_input)

    elif event == BROWSE_INPUT_FOLDER_BUTTON_KEY:
        handle_browse_input_directory_button_clicked_event(window, user_input)

    elif event == BROWSE_OUTPUT_FOLDER_BUTTON_KEY:
        handle_browse_output_directory_button_clicked_event(window, user_input)

    elif event == SUBMIT_BUTTON_TEXT:
        handle_submit_event(window, values, user_input)


def handle_exit_event(window, values, user_input):
    pass  # do nothing


def handle_browse_input_directory_button_clicked_event(window, user_input):
    previous_directory = user_input.input_folder_directory
    new_directory = browse_and_select_directory(previous_directory)
    window[INPUT_FOLDER_DIRECTORY_INPUT_KEY].update(new_directory)
    user_input.input_folder_directory = new_directory


def handle_browse_output_directory_button_clicked_event(window, user_input):
    previous_directory = user_input.output_folder_directory
    new_directory = browse_and_select_directory(previous_directory)
    window[OUTPUT_FOLDER_DIRECTORY_INPUT_KEY].update(new_directory)
    user_input.output_folder_directory = new_directory


def handle_submit_event(window, values, user_input):
    save_values_to_user_input(values, user_input)
    is_valid = validate_user_input(user_input)
    if not is_valid:
        return
    from common.gui.constants import FUTURA_Normal_FONT
    confirm_button_name = 'Confirm and read Dicom headers'
    button_clicked = sg.popup(*user_input.get_summary_string(), "",
                              title="Input Check",
                              font=FUTURA_Normal_FONT,
                              custom_text=('Back', confirm_button_name))
    if button_clicked == confirm_button_name:
        # WA TODO redirect_standard_error_and_output_stream(get_std_out_err_log_file_path(user_input))
        log_user_input_values(user_input)
        browse (user_input)


def save_values_to_user_input(values, user_input: UserInput):
    user_input.input_folder_directory = values[INPUT_FOLDER_DIRECTORY_INPUT_KEY]
    user_input.is_content_of_a_folder_belongs_to_same_study = values[CONTENT_OF_A_FOLDER_BELONGS_TO_SAME_STUDY_CHECKBOX_KEY]
    user_input.output_folder_name = values[OUTPUT_FOLDER_NAME_INPUT_KEY]
    user_input.output_folder_directory = values[OUTPUT_FOLDER_DIRECTORY_INPUT_KEY]


def read_value_when_specified(is_specified, value):
    if is_specified:
        return value
    return ''


def log_user_input_values(user_input: UserInput):
    # WA TODO
    pass
    # logger = get_logger('Submitting', log_file=get_log_file_path(user_input))
    #
    # # Test messages
    # logger.info("User input:")
    # input_summary_string = user_input.get_summary_string()
    # for info in input_summary_string:
    #     logger.info(info)
    #
    # return logger