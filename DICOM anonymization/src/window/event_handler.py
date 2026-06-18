import PySimpleGUI as sg
from PySimpleGUI import Window

from anonymize.src.anonymize import anonymize
from anonymize.src.window.gui.element_keys import EXIT_BUTTON_TEXT, BROWSE_OUTPUT_FOLDER_BUTTON_KEY, SUBMIT_BUTTON_TEXT, \
    OUTPUT_FOLDER_DIRECTORY_INPUT_KEY, OUTPUT_FOLDER_NAME_INPUT_KEY, BROWSE_INPUT_FOLDER_BUTTON_KEY, \
    INPUT_FOLDER_DIRECTORY_INPUT_KEY, USE_WHITELIST_KEY, USE_BLACKLIST_KEY, ENTER_WHITELIST_TEXT_KEY, \
    WHITELIST_INPUT_FIELD_KEY, ENTER_BLACKLIST_TEXT_KEY, BLACKLIST_INPUT_FIELD_KEY, PROJECT_NAME_INPUT_FIELD_KEY, \
    THRESHOLD_INPUT_FIELD_KEY, BROWSE_INPUT_CSV_FILE_BUTTON_KEY, INPUT_CSV_FILE_PATH_INPUT_KEY, MRN_COLUMN_NAME_INPUT_FIELD_KEY, \
    ACCESSION_NUMBER_COLUMN_NAME_INPUT_FIELD_KEY, INPUT_CSV_FILE_PATH_OUTPUT_KEY, OUTPUT_CSV_FILE_PATH_OUTPUT_KEY, BROWSE_OUTPUT_CSV_FILE_BUTTON_KEY, \
    OUTPUT_CSV_FOLDER_DIRECTORY_INPUT_KEY, BROWSE_OUTPUT_CSV_FOLDER_BUTTON_KEY

from anonymize.src.window.user_input import UserInput
from anonymize.src.window.user_input_validation import validate_user_input
from common.gui.directory import browse_and_select_directory
from common.gui.csv import browse_and_select_csv_file
from common.gui.text import update_text_and_input_list_readonly_status


def handle_events(window: Window, event, values, user_input: UserInput):
    if event == EXIT_BUTTON_TEXT or event == sg.WIN_CLOSED:
        handle_exit_event(window, values, user_input)

    elif event == BROWSE_INPUT_FOLDER_BUTTON_KEY:
        handle_browse_input_directory_button_clicked_event(window, user_input)

    elif event == BROWSE_OUTPUT_CSV_FILE_BUTTON_KEY:
        handle_browse_output_csv_file_button_clicked_event(window, user_input)

    elif event == BROWSE_INPUT_CSV_FILE_BUTTON_KEY:
        handle_browse_file_button_clicked_event(window, user_input)

    elif event == USE_WHITELIST_KEY:
        handle_use_whitelist_clicked_event(window, user_input, values)

    elif event == USE_BLACKLIST_KEY:
        handle_use_blacklist_clicked_event(window, user_input, values)

    elif event == BROWSE_OUTPUT_FOLDER_BUTTON_KEY:
        handle_browse_output_directory_button_clicked_event(window, user_input)

    elif event == BROWSE_OUTPUT_CSV_FOLDER_BUTTON_KEY:
        handle_browse_output_csv_directory_button_clicked_event(window, user_input)

    elif event == SUBMIT_BUTTON_TEXT:
        handle_submit_event(window, values, user_input)


def handle_exit_event(window, values, user_input):
    pass  # do nothing


def handle_browse_input_directory_button_clicked_event(window, user_input):
    previous_directory = user_input.input_folder_directory
    new_directory = browse_and_select_directory(previous_directory)
    window[INPUT_FOLDER_DIRECTORY_INPUT_KEY].update(new_directory)
    user_input.input_folder_directory = new_directory

def handle_browse_file_button_clicked_event(window, user_input):
    new_file_path = browse_and_select_csv_file()
    window[INPUT_CSV_FILE_PATH_INPUT_KEY].update(new_file_path)
    user_input.input_csv_file_path = new_file_path

def handle_browse_output_csv_file_button_clicked_event(window, user_input):
    new_file_path = browse_and_select_csv_file()
    window[OUTPUT_CSV_FILE_PATH_OUTPUT_KEY].update(new_file_path)
    user_input.output_csv_file_path = new_file_path

def handle_use_whitelist_clicked_event(window, user_input: UserInput, values):
    user_input.use_whitelist = values[USE_WHITELIST_KEY]
    use_whitelist_text = window[ENTER_WHITELIST_TEXT_KEY]
    whitelist_input = window[WHITELIST_INPUT_FIELD_KEY]
    update_text_and_input_list_readonly_status(use_whitelist_text, whitelist_input, user_input.use_whitelist,
                                               user_input.get_whitelist, user_input.set_whitelist)


def handle_use_blacklist_clicked_event(window, user_input: UserInput, values):
    user_input.use_blacklist = values[USE_BLACKLIST_KEY]
    use_blacklist_text = window[ENTER_BLACKLIST_TEXT_KEY]
    blacklist_input = window[BLACKLIST_INPUT_FIELD_KEY]
    update_text_and_input_list_readonly_status(use_blacklist_text, blacklist_input, user_input.use_blacklist,
                                               user_input.get_blacklist, user_input.set_blacklist)


def handle_browse_output_directory_button_clicked_event(window, user_input):
    previous_directory = user_input.output_folder_directory
    new_directory = browse_and_select_directory(previous_directory)
    window[OUTPUT_FOLDER_DIRECTORY_INPUT_KEY].update(new_directory)
    user_input.output_folder_directory = new_directory


def handle_browse_output_csv_directory_button_clicked_event(window, user_input):
    previous_directory = user_input.output_csv_folder_path
    new_directory = browse_and_select_directory(previous_directory)
    window[OUTPUT_CSV_FOLDER_DIRECTORY_INPUT_KEY].update(new_directory)
    user_input.output_csv_folder_path = new_directory


def handle_submit_event(window, values, user_input):
    save_values_to_user_input(values, user_input)
    is_valid = validate_user_input(user_input)
    if not is_valid:
        return
    from common.gui.constants import FUTURA_Normal_FONT
    confirm_button_name = 'Confirm and start anonymization'
    button_clicked = sg.popup(*user_input.get_summary_string(), "",
                              title="Input Check",
                              font=FUTURA_Normal_FONT,
                              custom_text=('Back', confirm_button_name))
    if button_clicked == confirm_button_name:
        # WA TODO redirect_standard_error_and_output_stream(get_std_out_err_log_file_path(user_input))
        log_user_input_values(user_input)
        anonymize (user_input)


def save_values_to_user_input(values, user_input: UserInput):
    user_input.project_name = values[PROJECT_NAME_INPUT_FIELD_KEY]
    user_input.threshold = values[THRESHOLD_INPUT_FIELD_KEY]
    user_input.input_folder_directory = values[INPUT_FOLDER_DIRECTORY_INPUT_KEY]
    user_input.threshold = values[THRESHOLD_INPUT_FIELD_KEY]
    user_input.use_whitelist = values[USE_WHITELIST_KEY]
    if user_input.use_whitelist:
        user_input.whitelist = values[WHITELIST_INPUT_FIELD_KEY]
    user_input.use_blacklist = values[USE_BLACKLIST_KEY]
    if user_input.use_blacklist:
        user_input.blacklist = values[BLACKLIST_INPUT_FIELD_KEY]
    user_input.output_folder_name = values[OUTPUT_FOLDER_NAME_INPUT_KEY]
    user_input.output_folder_directory = values[OUTPUT_FOLDER_DIRECTORY_INPUT_KEY]
    user_input.output_csv_folder_path = values[OUTPUT_CSV_FOLDER_DIRECTORY_INPUT_KEY]

    user_input.csv_mrn_column_name = 'mrn'
    user_input.csv_accession_number_column_name = 'accession'


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
