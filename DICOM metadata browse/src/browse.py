import os
import shutil
import traceback
from datetime import datetime

import pandas as pd
import pydicom
import PySimpleGUI as sg
from PySimpleGUI import Window
from pydicom import datadict

from browse.src.window.browsing_progress_window import create_scanning_progress_window
from browse.src.window.gui.element_keys import EXCHANGE_MESSGES_TEXT_KEY, PROGRESS_PERCENTAGE_KEY, PROGRESS_BAR_KEY, \
    ESTIMATED_REMAINING_TIME_KEY
from browse.src.window.user_input import UserInput
from common.utils.dicom_read import read_dicom_file, handle_error_reading_dicom, is_dicom_file
from common.utils.operating_system_utils import join_directories, get_number_of_files_in_directory, \
    get_number_of_folders_and_subfolders_in_directory
from common.utils.remaining_time_estimater import AverageTaskTimeConsumption
from common.utils.time import format_seconds, calculate_elapsed_time_in_seconds
from download.src.entity.pacs_response import ResponseStatus

PIXEL_DATA_ELEMENT_TAG_KEYWORD = 'PixelData'
ESTIMATED_RUNNING_TIME_MESSAGE = 'Estimated remaining time: %s'
CSV_WITH_ALL_META_DATA = 'csv_with_all_meta_data.csv'


def browse (user_input: UserInput):
    df = pd.DataFrame()
    df = browse_dicom_files(user_input, df)
    print("done")


def browse_dicom_files(user_input: UserInput, df: pd.DataFrame):
    output_folder_path = get_and_prepare_output_folder_directory(user_input)
    csv_with_all_meta_data = join_directories(output_folder_path, CSV_WITH_ALL_META_DATA)

    last_series_instance_uid = None

    window: Window = create_scanning_progress_window(user_input)
    event, values = window.read(timeout=10)
    average_task_time_consumption: AverageTaskTimeConsumption = AverageTaskTimeConsumption(number_of_recent_tasks_to_remember = 10,default_average_task_time_consumption = 1)
    update_progress_status(window, 0, 300, average_task_time_consumption, 'Calculating number of files. This may take many minutes.')
    update_progress_status(window, 0, 300, average_task_time_consumption, 'Calculating number of files. This may take many minutes.')

    input_folder_directory = user_input.input_folder_directory
    files_count = get_number_of_files_in_directory(input_folder_directory)
    number_of_browsed_files = 0
    last_task_start_time = datetime.now()

    for root, dirs, files in os.walk(input_folder_directory):
        event, values = window.read(timeout=10)
        if event == sg.WIN_CLOSED:
            break
        update_progress_status(window, number_of_browsed_files, files_count, average_task_time_consumption, 'browsing at %s' % root)
        for filename in files:
            if is_dicom_file(filename):  # exclude non-dicoms, good for messy folders
                source_path = os.path.join(root, filename)
                ds = read_dicom_file(source_path, stop_before_pixels=True)
                if ds is None:
                    handle_error_reading_dicom(source_path)
                    continue
                new_series_instance_uid = ds.SeriesInstanceUID
                if new_series_instance_uid == last_series_instance_uid:
                    continue
                last_series_instance_uid = new_series_instance_uid
                df, response_status = convert_and_add_dataset_to_dataframe(df, ds)
                if response_status == ResponseStatus.ERROR:
                    print('Error reading %s' % source_path)
                    #destination = root.replace('Structured_dicoms', 'problematic_files')
                    #os.makedirs(destination, exist_ok=True)
                    #shutil.move(source_path, destination)
                    last_series_instance_uid = ''
                elif user_input.is_content_of_a_folder_belongs_to_same_study:
                    break
        number_of_covered_files = len(files)
        number_of_browsed_files += number_of_covered_files
        # df.to_csv(csv_with_all_meta_data, sep=',', index=False)
        average_task_time_consumption.update_with_last_task_time_consumption(time_consumption_in_seconds=calculate_elapsed_time_in_seconds(last_task_start_time), number_of_covered_itterations =number_of_covered_files)

        last_task_start_time = datetime.now()
    
    update_progress_status(window, number_of_browsed_files, files_count, average_task_time_consumption, 'DONE')
    

    df.to_csv(csv_with_all_meta_data, sep=',', index=False, escapechar='\\')
    return df


def update_progress_status(window, number_of_browsed_folders: int, folders_count: int, average_task_time_consumption: AverageTaskTimeConsumption,
                           message):
    update_progress_bar_and_percentage(window, completed=number_of_browsed_folders, total=folders_count)
    update_estimated_remaining_time(window, completed=number_of_browsed_folders, total=folders_count, average_task_time_consumption=average_task_time_consumption)
    update_progress_messages_with_message(message, window)

def update_estimated_remaining_time(window, completed, total, average_task_time_consumption: AverageTaskTimeConsumption):
    estimated_remaining_time = average_task_time_consumption.calculate_estimated_remaining_time_in_seconds(completed, total)
    estimated_remaining_time_formatted = format_estimated_running_time_message(estimated_remaining_time)
    window[ESTIMATED_REMAINING_TIME_KEY].update(estimated_remaining_time_formatted)


def format_estimated_running_time_message(estimated_remaining_time):
    return ESTIMATED_RUNNING_TIME_MESSAGE % format_seconds(estimated_remaining_time)


def update_progress_messages_with_message(message, window):
    window[EXCHANGE_MESSGES_TEXT_KEY].update(message)


def update_progress_bar_and_percentage(window, completed, total):
    window[PROGRESS_PERCENTAGE_KEY].update(("%.2f" % (100.0 * completed / total)) + ' %')
    window[PROGRESS_BAR_KEY].update(completed, total)


def is_new_row_different_from_last_one(new_row: dict, df: pd.DataFrame):
    if df.empty:
        return True
    last_row = df.iloc[-1].to_dict()
    return not last_row == new_row


def get_important_columns_ordered():
    return ["(0010, 0010); PatientName",
            "(0020, 0010); StudyID",
            "(0008, 0022); AcquisitionDate",
            "(0008, 0081); InstitutionAddress",
            "(0010, 0021); IssuerOfPatientID",
            "(0010, 1000); OtherPatientIDs",
            "(0010, 1040); PatientAddress",
            "(0010, 0030); PatientBirthDate",
            "(0010, 1005); PatientBirthName",
            "(0010, 2154); PatientTelephoneNumbers",
            "(0008, 1048); PhysiciansOfRecord",
            "(0032, 1032); RequestingPhysician",
            "(0008, 0050); AccessionNumber",
            "(0008, 0023); ContentDate",
            "(0008, 0080); InstitutionName",
            "(0008, 1070); OperatorsName",
            "(0010, 0020); PatientID",
            "(0008, 1050); PerformingPhysicianName",
            "(0008, 0090); ReferringPhysicianName",
            "(0008, 1010); StationName",
            "(0040, 0009); ScheduledProcedureStepID",
            "(0040, 1001); RequestedProcedureID",
            "(0002, 0016); SourceApplicationEntityTitle"]


def reorder_columns(df):
    columns_ordered = get_columns_ordered(df)
    return df[columns_ordered]


def get_columns_ordered(df):
    columns = df.columns
    important_columns_ordered = get_important_columns_ordered()
    intersection = [value for value in important_columns_ordered if value in columns]
    difference = [value for value in columns if value not in important_columns_ordered]
    result = intersection + difference
    return result


def append_dictionary_to_dataframe(df: pd.DataFrame, dictionary: dict):
    index_new_row = int(df.shape[0])
    for e in dictionary.items():
        df.loc[index_new_row, e[0]] = str(e[1])


def convert_and_add_dataset_to_dataframe(df, ds, log=True):
    response_status = ResponseStatus.SUCCESS
    try:
        d = convert_dicom_dataset_to_dictionary(ds)
        if log:
            print(len(df), "currently with non zero items in row:", sum(len(d[key]) != 0  for key in d.keys()))

        d.update(convert_dicom_dataset_to_dictionary(ds.file_meta))
        if is_new_row_different_from_last_one(d, df):
            append_dictionary_to_dataframe(df, d)
    except Exception as e:
        print("Oops!", e.__class__, "occurred.")
        print(e)
        traceback.print_exc()
        response_status = ResponseStatus.ERROR
    return df, response_status


def get_and_prepare_output_folder_directory(user_input):
    output_folder_path = user_input.get_output_folder_path()
    os.makedirs(output_folder_path, exist_ok=True)
    return output_folder_path


def convert_dicom_dataset_to_dictionary(ds: pydicom.dataset.Dataset):
    d = dict()

    for element in ds:
        try:
            tag = get_element_tag_description(element)
            if element.VR == 'SQ':
                d[tag] = [convert_dicom_dataset_to_dictionary(item) for item in element]
            else:
                value = element.value
                # Convert bytes to string representation to avoid CSV escaping issues
                if isinstance(value, bytes):
                    d[tag] = value.hex()
                elif isinstance(value, (list, tuple)):
                    d[tag] = str(value)
                else:
                    d[tag] = str(value) if value is not None else ''
        except Exception as err:
            print('element is corrupt')
            print(element)
            print(err)
            traceback.print_exc()

    return d


def get_element_tag_description(elem):
    tag = elem.tag
    description = elem.description()
    result = ' '.join([description, str(tag)])
    return result