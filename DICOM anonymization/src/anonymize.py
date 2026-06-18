import os
import shutil
import traceback
from datetime import datetime
from time import sleep
import re

import PySimpleGUI as sg
import pandas as pd
from PySimpleGUI import Window

import warnings
# suppress pydicom warnings - most files have too long VR LO in the dicom contents
warnings.filterwarnings(
    'ignore', 
    module='pydicom', 
    category=UserWarning
)
from pydicom import Dataset, DataElement
from pydicom.valuerep import PersonName
import time
from anonymize.src.paths_organisation import get_and_prepare_anonymized_dicoms_folder_path, \
    get_and_prepare_anonymized_dicom_file_path, join_and_clean_file_naming
from anonymize.src.patient_pseudonym_id import PatientPseudonymIdGenerator
from anonymize.src.window.anonymize_progress_window import create_anonymization_progress_window
from anonymize.src.window.gui.element_keys import PROGRESS_PERCENTAGE_KEY, PROGRESS_BAR_KEY, EXCHANGE_MESSGES_TEXT_KEY
from anonymize.src.window.user_input import UserInput
from common.entity.hospital import Hospital
from common.entity.series import Series
from common.utils.dicom_read import read_dicom_file, handle_error_reading_dicom, is_dicom_file
from common.utils.dicom_tag import is_tag_of_pixel_data, convert_tag_to_int_tuple
from common.utils.my_logging import redirect_standard_error_and_output_stream
from common.utils.operating_system_utils import get_number_of_files_in_directory, join_directories
from common.utils.string_utils import is_blank, is_not_blank, remove_special_characters, default_if_blank
from download.src.utils.series_checker import is_series_complies_with_whitelist, is_series_complies_with_blacklist

BEGINNING_OF_TIME = datetime(2000, 1, 1, 0, 0)
YYYYMMDD = 'yyyymmdd'
CSV_WITH_FIELDS_TO_KEEP = 'anonymize/fields_to_keep.csv'

UNSAVED_ENTRIES = 0
UNSAVED_ENTRIES_THRESHOLD = 5000

ALLOWED_RENAME_REPEATS=5
TIME_RENAME_REPEATS=1

LOGFILE = None
def log(message: str, *args):
    if args:
        message = message + ' ' + ' '.join([str(arg) for arg in args])
    if LOGFILE is None:
        raise FileNotFoundError("Could not find logfile, logfile is not defined")
    with open(LOGFILE, 'a') as f:
        f.write("\n[{}] {}".format(time.strftime( '%Y-%m-%d-%H-%M-%S.txt'),message))
    print(message)



def anonymize(user_input: UserInput):
    global LOGFILE

    # Tee everything printed to the terminal (stdout + stderr) into a log file
    # saved alongside the key sheet, so each run leaves a full terminal record.
    csv_folder = user_input.get_output_csv_folder_path()
    os.makedirs(csv_folder, exist_ok=True)
    terminal_log_path = join_directories(
        csv_folder,
        'terminal_log_{}_{}'.format(
            default_if_blank(user_input.project_name, 'anonymization'),
            time.strftime('%Y-%m-%d-%H-%M-%S.log')
        )
    )
    redirect_standard_error_and_output_stream(terminal_log_path)
    print("[INFO] Saving terminal output to: %s" % terminal_log_path)

    patients_paths_dictionary_per_patient_pseudonym_id = {}
    series_paths_dictionary_per_study_uid = {}
    series_paths_dictionary_per_series_uid = {}
    studies_per_patient_dictionary = {}
    series_per_study_dictionary = {}
    study_date_per_study_uid = {}

    patient_pseudonym_id_generator = PatientPseudonymIdGenerator()
    if user_input.input_csv_file_path is not None and os.path.isfile(user_input.input_csv_file_path):
        patient_pseudonym_id_generator.fill_with_ids_from_csv(csv=user_input.input_csv_file_path)
    
    global UNSAVED_ENTRIES
    # If you need to use already given pseudonym IDs uncomment and edit the following line
    # patient_pseudonym_id_generator.fill_with_ids_from_csv(csv=r'/Users/lab/Desktop/rpdr_concatenated_all_final.csv', mrn_column='mrn_download_report')

    dicom_tags_without_phi = get_dicom_tags_without_phi()
    get_and_prepare_anonymized_dicoms_folder_path(user_input)

    input_folder_directory = user_input.input_folder_directory
    # logfile will be located in source directory
    LOGFILE = input_folder_directory + '/../' + 'log_{}'.format(time.strftime('%Y-%m-%d-%H-%M-%S.txt'))
    with open(LOGFILE, 'w') as logfile:
        logfile.write(
            "==== BEGINNING THE LOGFILE ==="
        )
    
    window: Window = create_anonymization_progress_window(user_input)
    event, values = window.read(timeout=10)
    update_progress_status(window, 0, 300, 'Calculating total number of files to anonymize. This may take many minutes. The program will look like crashing. Please be patient.')
    update_progress_status(window, 0, 300, 'Calculating total number of files to anonymize. This may take many minutes. The program will look like crashing. Please be patient.')
    files_count = get_number_of_files_in_directory(input_folder_directory)
    update_progress_status(window, 0, files_count, 'Done calculating total number of files to anonymize.')
    update_progress_status(window, 0, files_count, 'Done calculating total number of files to anonymize.')
    number_of_anonymized_files = 0

    number_of_errors = 0
    for root, dirs, files in os.walk(input_folder_directory):
        event, values = window.read(timeout=10)
        if event == sg.WIN_CLOSED:
            update_progress_status(window, number_of_anonymized_files, files_count, 'Interrupted. Saving progress before closing...')
            save_progress(user_input, patient_pseudonym_id_generator, {})
            break
        try:
            for filename in files:
                source_path = os.path.join(root, filename)
                if filename.startswith('.'):
                    os.remove(source_path)
                if is_dicom_file(filename):  # exclude non-dicoms, good for messy folders
                    update_progress_status(window, number_of_anonymized_files, files_count, 'anonymizing %s' % source_path)
                    ds = read_dicom_file(source_path)
                    number_of_anonymized_files += 1
                    UNSAVED_ENTRIES += 1
                    if ds is None:
                        handle_error_reading_dicom(source_path)
                        continue
                    if is_dicom_satisfies_filters(ds, user_input):
                        anonymize_dicom_file_and_keep_study_date(user_input, ds, dicom_tags_without_phi,
                                                                 patients_paths_dictionary_per_patient_pseudonym_id, series_paths_dictionary_per_study_uid,
                                                                 series_paths_dictionary_per_series_uid, study_date_per_study_uid, patient_pseudonym_id_generator)
                        update_studies_per_patient_and_series_per_study_dictionaries(ds, studies_per_patient_dictionary,
                                                                                     series_per_study_dictionary)
                    if UNSAVED_ENTRIES >= UNSAVED_ENTRIES_THRESHOLD:
                        update_progress_status(window, number_of_anonymized_files, files_count, 'Saving progress with %d entries...' % UNSAVED_ENTRIES)
                        save_progress(user_input, patient_pseudonym_id_generator, {})
                        UNSAVED_ENTRIES = 0
        except Exception as e:
            number_of_errors += 1
            log("Oops!" + e.__class__.__name__ + " occurred at {} with {}".format(root, filename))
            log(e)
            traceback.print_exc()

    update_progress_status(window, number_of_anonymized_files, files_count, 'completed first part of anonymization with %d errors. Saving progress before starting to anonymize the dates...' % number_of_errors)
    number_of_days_after_oldest_study_per_study_uid = {}
    save_progress(user_input, patient_pseudonym_id_generator, number_of_days_after_oldest_study_per_study_uid)
    log(
        "\n[DEBUG] Completed patient anonymization. On to dates...\n"
    )
    number_of_errors += anonymize_study_dates(window, files_count, studies_per_patient_dictionary, series_per_study_dictionary,
                                              series_paths_dictionary_per_study_uid,
                                              series_paths_dictionary_per_series_uid, study_date_per_study_uid, number_of_days_after_oldest_study_per_study_uid,
                                              user_input)

    update_progress_status(window, number_of_anonymized_files, files_count, 'completed anonymization with %d errors. Saving progress...' % number_of_errors)
    save_progress(user_input, patient_pseudonym_id_generator, number_of_days_after_oldest_study_per_study_uid)
    update_progress_status(window, number_of_anonymized_files, files_count, 'completed anonymization with %d errors. Saving progress completed.' % number_of_errors)


def update_progress_status(window, number_of_anonymized_files: int, number_of_total_files_to_anonymize: int,
                           message):
    update_progress_bar_and_percentage(window, completed=number_of_anonymized_files,
                                       total=number_of_total_files_to_anonymize)
    # update_estimated_remaining_time(window, completed=number_of_anonymized_files,
    #                                 total=number_of_total_files_to_anonymize)
    update_progress_messages_with_message(message, window)


def update_progress_messages_with_message(message, window):
    window[EXCHANGE_MESSGES_TEXT_KEY].update(message)


def update_progress_bar_and_percentage(window, completed, total):
    window[PROGRESS_PERCENTAGE_KEY].update(("%.2f" % (100.0 * completed / total)) + ' %')
    window[PROGRESS_BAR_KEY].update(completed, total)


def remove_date_like(s: str):
    '''
    Goal: regex the s and remove anything that looks like a date.
    Patterns matched:
    - dd/mm/yyyy
    - dd/mm/yy
    - dd-mm-yyyy
    - dd-mm-yy
    - yyyymmdd
    - yyyy-mm-dd
    - yy-mm-dd
    - yymmdd
    - mm/yyyy
    - mm/yy
    - mm-yyyy
    - mm-yy
    - m/yyyy
    - m/yy
    - m-yyyy
    - m-yy
    - d/m/yy
    - d-m-yy
    - m.d.yy
    ... and similar patterns with different separators and different number of digits for day and month
    '''
    import re

    pattern = r"""\b(?:
        \d{1,2}[./-]\d{1,2}[./-]\d{2,4} |   # d/m/yy, dd/mm/yyyy, m.dd.yy, etc.
        \d{4}[./-]\d{1,2}[./-]\d{1,2} |     # yyyy-mm-dd, yyyy/m/d, yyyy.m.d
        \d{2}[./-]\d{1,2}[./-]\d{1,2} |     # yy-mm-dd, yy/m/d, yy.m.d
        \d{8} |                             # yyyymmdd
        \d{6} |                             # yymmdd
        \d{1,2}[./-]\d{2,4} |                # m/yyyy, mm.yyyy, m/yy, m.yy, etc.
        \d{1}[./-]\d{1}
    )\b"""

    cleaned = re.sub(pattern, "REMOVED_DATE", s, flags=re.VERBOSE)
    return cleaned

def remove_forbidden_strings(s: str, forbidden_strings):
    for forbidden_string in forbidden_strings:
        s = s.replace(forbidden_string, 'PHI')
    return s

def clean(date: str):
    # parse dates like 2020-20-20
    # parse dates like 2020/20/20
    if '-' in date:
        date = ''.join(date.split('-'))
    elif '/' in date:
        date = ''.join(date.split('/'))
    return date

def get_anonymized_accession_number(study_instance_uid):
    study_instance_uid = remove_special_characters(study_instance_uid)
    return 'ANON' + study_instance_uid[-10:]


def anonymize_dicom_file_and_keep_study_date(user_input: UserInput, ds: Dataset, dicom_tags_without_phi,
                                             patients_paths_dictionary_per_patient_pseudonym_id: dict, series_paths_dictionary_per_study_uid: dict,
                                             series_paths_dictionary_per_series_uid: dict, study_date_per_study_uid: dict, patient_pseudonym_id_generator: PatientPseudonymIdGenerator):
    patient_id, issuer_of_patient_id = get_patient_id_with_issuer(ds)
    accession_number = ds.get('AccessionNumber', '')
    patient_name = ds.get('PatientName', '')
    patient_birth_date = ds.get('PatientBirthDate', '')
    patient_age = ds.get('PatientAge', '')
    study_date = ds.get('StudyDate', '')
    study_date = clean(study_date)
    
    study_instance_uid = ds.get('StudyInstanceUID', '')
    study_date_per_study_uid[study_instance_uid] = study_date

    pseudonym_accession_number = get_anonymized_accession_number(study_instance_uid)

    patient_pseudonym_id = patient_pseudonym_id_generator.get_patient_pseudonym_id(user_input, patient_id, issuer_of_patient_id,
                                                                                             accession_number, patient_name,
                                                                                             patient_birth_date, pseudonym_accession_number, ds)
    forbidden_strings = get_forbidden_strings(ds)
    ds.remove_private_tags()
    # Wipe StudyDescription of date-like patterns
    ds.StudyDescription = remove_date_like(ds.get('StudyDescription', ''))
    # Remove Hosp: DFCI/BWH
    ds.StudyDescription = re.sub(
        r'(DFCI|BWH)', '__',
        ds.StudyDescription
    )
    clean_data_set(ds, dicom_tags_without_phi, forbidden_strings)
    ds_file_meta = ds.file_meta
    clean_data_set(ds_file_meta, dicom_tags_without_phi, forbidden_strings)

    ds.PatientID = patient_pseudonym_id
    ds.AccessionNumber = pseudonym_accession_number
    ds.PatientName = PersonName('Anonymized^%s^' % patient_pseudonym_id)
    add_patient_age_if_not_protected(patient_age, ds)
    ds.StudyDate = study_date
    
    anonymized_dicom_file = get_and_prepare_anonymized_dicom_file_path(
        user_input, ds, patients_paths_dictionary_per_patient_pseudonym_id,
        series_paths_dictionary_per_study_uid,
        series_paths_dictionary_per_series_uid
    )
    # writing task: add safeguards
    for i in range(5):
        try:
            ds.save_as(anonymized_dicom_file)
            break
        except Exception as e:
            log("Could not save dicom. Trying again...")
            time.sleep(1)


def clean_data_set(ds: Dataset, dicom_tags_without_phi, forbidden_strings):
    for data_element in ds:
        clean_data_element(data_element, dicom_tags_without_phi, ds, forbidden_strings)


def clean_data_element(data_element: DataElement, dicom_tags_without_phi, ds: Dataset, forbidden_strings: list):
    element_tag = data_element.tag
    value = data_element.value
    if is_element_phi(element_tag, dicom_tags_without_phi):
        del ds[element_tag]
    elif type(value) == str:
        data_element.value = remove_forbidden_strings(value, forbidden_strings)
    elif data_element.VR == 'SQ':
        for data_set in data_element:
            clean_data_set(data_set, dicom_tags_without_phi, forbidden_strings)


def get_forbidden_strings(ds: Dataset):
    patient_name = ds.get('PatientName', '')
    forbidden_strings = get_person_name_components_without_abbreviations(patient_name)
    accession_number = ds.get('AccessionNumber', '')
    if is_not_blank(accession_number):
        forbidden_strings.append(accession_number)
    patient_id = ds.get('PatientID', '')
    if is_not_blank(patient_id):
        forbidden_strings.append(patient_id)
    study_date = ds.get('StudyDate', '')
    if is_not_blank(study_date):
        forbidden_strings.append(study_date)
        study_date = clean(study_date)
        forbidden_strings.append(study_date) # add both cleaned and raw dates
    return forbidden_strings


def get_person_name_components_without_abbreviations(person_name: PersonName):
    name = str(person_name)
    patient_name_components = [x.strip() for x in name.split('^')]
    patient_name_components_without_abbreviations = [x for x in patient_name_components if
                                                     len(x) > 2]  # filter small components (Initials)
    return patient_name_components_without_abbreviations


def add_patient_age_if_not_protected(patient_age: str, ds):
    if is_blank(patient_age):
        return
    if is_blank(ds.get('PatientAge', '')): # Age was removed before because it was unwanted.
        return
    if 'Y' not in patient_age:  # Patient age is weeks or months
        ds.PatientAge = patient_age
        return
    patient_age_formatted = patient_age.replace('Y', '')
    patient_age_formatted = patient_age_formatted.replace('y', '')
    age = int(patient_age_formatted)
    if age < 90:
        ds.PatientAge = patient_age


def get_patient_id_with_issuer(ds):
    patient_id = ds.get('PatientID', '')
    issuer_of_patient_id = ds.get('IssuerOfPatientID', '')
    if (is_blank(issuer_of_patient_id)):
        # print('Issuer of patient ID (%s) is unknown.' % patient_id)
        issuer_of_patient_id = 'MGH'
    return patient_id, issuer_of_patient_id


def is_element_phi(element_tag, dicom_tags_without_phi):
    if (element_tag.group, element_tag.element) in dicom_tags_without_phi:
        return False
    if is_tag_of_pixel_data(element_tag):
        return False
    return True


def get_dicom_tags_without_phi():
    csv_with_fields_to_keep = CSV_WITH_FIELDS_TO_KEEP
    df_fields_to_keep = pd.read_csv(csv_with_fields_to_keep, dtype=str)
    tags_to_keep = set(df_fields_to_keep['Tag'])
    tags_to_keep = [convert_tag_to_int_tuple(tag) for tag in tags_to_keep]
    return set(tags_to_keep)


def extract_date_of_a_study(study_instance_uid, study_date_per_study_uid: dict, series_per_study_dictionary, series_paths_dictionary_per_series_uid: dict):
    study_date = study_date_per_study_uid.get(study_instance_uid)
    if is_not_blank(study_date):
        return study_date

    for series_instance_uid in series_per_study_dictionary.get(study_instance_uid, []):
        series_path = series_paths_dictionary_per_series_uid.get(series_instance_uid)
        if series_path is None:
            continue
        for root, dirs, files in os.walk(series_path):
            if len(files) == 0:
                continue
            first_file = files[0]
            source_path = os.path.join(root, first_file)
            ds = read_dicom_file(source_path, stop_before_pixels=True)
            study_date = ds.get('StudyDate')
            study_date = clean(study_date)
            if is_not_blank(study_date):
                return study_date
    return YYYYMMDD


def get_date_anonymized_with_difference_in_days(oldest_date: datetime, date_to_anonymize: str, study_instance_uid: str, number_of_days_after_oldest_study_per_study_uid: dict):
    date_anonymized = parse_dicom_date(date_to_anonymize)
    if date_anonymized is None or oldest_date is None:
        return (YYYYMMDD, 'xxxxx')
    difference_in_days = date_anonymized - oldest_date
    date_anonymized = BEGINNING_OF_TIME + difference_in_days
    difference_in_days = str(difference_in_days.days).zfill(5)
    number_of_days_after_oldest_study_per_study_uid[study_instance_uid] = difference_in_days
    date_anonymized = date_anonymized.strftime('%Y%m%d')
    return (date_anonymized, difference_in_days)


def anonymize_study_dates_for_series(window, files_count, number_of_anonymized_files,
                                     series_instance_uid, date_anonymized, series_paths_dictionary_per_series_uid, user_input):
    series_path = series_paths_dictionary_per_series_uid.get(series_instance_uid)
    if series_path is None:
        return
    for root, dirs, files in os.walk(series_path):
        if len(files) < int(user_input.threshold):
            log('Series %s violates threshold' % series_instance_uid)
            shutil.rmtree(root)
            return
        for filename in files:
            if '.dcm' in filename or '.DCM' in filename:
                source_path = os.path.join(root, filename)
                update_progress_status(window, number_of_anonymized_files[0], files_count,
                                       'anonymizing study date of %s' % source_path)
                try:
                    ds = read_dicom_file(source_path)
                except Exception as e:
                    log("Failed reading dicoms within anonymize_study_dates_for_series {}: {}".format(source_path, e))
                    raise e
                if ds is None:
                    log('failure to read %s' %source_path)
                    continue
                ds.StudyDate = date_anonymized
                ds.SeriesDate = date_anonymized
                try:
                    ds.save_as(source_path)
                except Exception as e:
                    log("Failed to save file to {}".format(source_path))
            number_of_anonymized_files[0] += 1


def anonymize_study_dates_for_study(window, files_count, number_of_anonymized_files,
                                    study_instance_uid: str, date_anonymized: str,
                                    difference_in_days_to_oldest_scan: str,
                                    series_per_study_dictionary: dict, series_paths_dictionary_per_study_uid: dict,
                                    series_paths_dictionary_per_series_uid: dict, user_input):
    study_old_path: str = series_paths_dictionary_per_study_uid.get(study_instance_uid)
    if study_old_path is None:
        return
    study_folder_name = os.path.basename(study_old_path)
    new_folder_name = join_and_clean_file_naming(difference_in_days_to_oldest_scan, study_folder_name)

    # WA TODO update series paths if necessary
    series_of_study = series_per_study_dictionary.get(study_instance_uid, [])
    for series_instance_uid in series_of_study:
        anonymize_study_dates_for_series(window, files_count, number_of_anonymized_files,
                                         series_instance_uid, date_anonymized, series_paths_dictionary_per_series_uid, user_input)

    study_new_path = study_old_path.replace(study_folder_name, new_folder_name)
    for RenameRepeat in range(ALLOWED_RENAME_REPEATS):
        try:
            os.rename(study_old_path, study_new_path)
            break
        except Exception as e:
            log("[ {} | Warning {}/5 ] Could not rename {} into {}. Possibly duplicated folder.".format(time.ctime(), RenameRepeat, study_old_path, study_new_path))
            log(e)
            time.sleep(TIME_RENAME_REPEATS)
            # log("[ Warning ] Source exists {}. Dest exists {}".format(os.path.exists(study_old_path),os.path.exists(study_new_path)))
    if RenameRepeat == ALLOWED_RENAME_REPEATS - 1: # hit max repeats
        log(
            " [ {} | Warning ] Could not rename file despite waiting {} repeats. {} into {}".format(time.ctime(), RenameRepeat, study_old_path, study_new_path)
        )
        log(
            "[ {} | Warning ] Source exists ? {} Dest exists ? {}".format(time.ctime(), os.path.exists(study_old_path),os.path.exists(study_new_path))
        )
        
    series_paths_dictionary_per_study_uid[study_instance_uid] = study_new_path


def anonymize_study_dates_for_patient_folder(window, files_count, number_of_anonymized_files,
                                             patient_id: str, studies_of_patient: set,
                                             series_per_study_dictionary: dict, series_paths_dictionary_per_study_uid: dict,
                                             series_paths_dictionary_per_series_uid: dict, study_date_per_study_uid: dict, number_of_days_after_oldest_study_per_study_uid: dict,
                                             user_input):
    try:
        date_of_studies: dict = {
            study_instance_uid: extract_date_of_a_study(study_instance_uid, study_date_per_study_uid, series_per_study_dictionary,
                                                    series_paths_dictionary_per_series_uid) for study_instance_uid in
            studies_of_patient}
    except Exception as e:
        log("Failed at extracting dates of a study")
        raise e

    oldest_study_date = min([date for date in date_of_studies.values()])
    oldest_study_date = parse_dicom_date(oldest_study_date)

    anonymized_date_of_sutdies_with_difference_in_days: dict = {
        study_instance_uid: get_date_anonymized_with_difference_in_days(oldest_study_date,
                                                                        date_of_studies.get(study_instance_uid), study_instance_uid, number_of_days_after_oldest_study_per_study_uid) for
        study_instance_uid in studies_of_patient if date_of_studies.get(study_instance_uid) != YYYYMMDD}

    for (study_instance_uid, (
            date_anonymized,
            difference_in_days_to_oldest_scan)) in anonymized_date_of_sutdies_with_difference_in_days.items():
        anonymize_study_dates_for_study(window, files_count, number_of_anonymized_files,
                                        study_instance_uid, date_anonymized, difference_in_days_to_oldest_scan,
                                        series_per_study_dictionary, series_paths_dictionary_per_study_uid, series_paths_dictionary_per_series_uid,
                                        user_input)


def parse_dicom_date(oldest_study_date):
    try:
        return datetime.strptime(oldest_study_date, '%Y%m%d')
    except:
        return None


def anonymize_study_dates(window: Window, files_count, studies_per_patient_dictionary: dict,
                          series_per_study_dictionary: dict,
                          series_paths_dictionary_per_study_uid: dict, series_paths_dictionary_per_series_uid: dict, study_date_per_study_uid, number_of_days_after_oldest_study_per_study_uid, user_input):
    number_of_anonymized_files = [0]
    number_of_errors = 0
    for (patient_id, studies_of_patient) in studies_per_patient_dictionary.items():
        try:
            anonymize_study_dates_for_patient_folder(
                window, files_count, number_of_anonymized_files, patient_id,
                studies_of_patient, series_per_study_dictionary,
                series_paths_dictionary_per_study_uid, series_paths_dictionary_per_series_uid, study_date_per_study_uid, number_of_days_after_oldest_study_per_study_uid,
                user_input
            )
        except Exception as e:
            number_of_errors += 1
            log("Oops!", e.__class__.__name__, "occurred anonymizing study dates for patient %s" % patient_id)
            log(e)
            traceback.print_exc()
    return number_of_errors


def update_studies_per_patient_and_series_per_study_dictionaries(ds: Dataset, studies_per_patient_dictionary: dict,
                                                                 series_per_study_dictionary: dict):
    patient_id = ds.PatientID
    study_instance_uid = ds.get("StudyInstanceUID")
    series_instance_uid = ds.get("SeriesInstanceUID")

    studies_of_patient = studies_per_patient_dictionary.get(patient_id)
    if studies_of_patient is None:
        studies_of_patient = set()
        studies_per_patient_dictionary[patient_id] = studies_of_patient
    studies_of_patient.add(study_instance_uid)

    series_of_study = series_per_study_dictionary.get(study_instance_uid)
    if series_of_study is None:
        series_of_study = set()
        series_per_study_dictionary[study_instance_uid] = series_of_study
    series_of_study.add(series_instance_uid)


def is_dicom_satisfies_filters(ds, user_input):
    if user_input.use_whitelist or user_input.use_blacklist:
        series = Series(mrn=None, accession_number=None, hospital=Hospital.MGH, # mrn && accession_number has no role with white and black lists
                        series_description=ds.get("SeriesDescription", ""),
                        number_of_series_related_instances=None)
        return is_series_complies_with_whitelist(series, user_input) and is_series_complies_with_blacklist(series, user_input)
    return True

def save_progress(user_input: UserInput, patient_pseudonym_id_generator: PatientPseudonymIdGenerator, number_of_days_after_oldest_study_per_study_uid_per_study_uid: dict, keep_duplicates=False):
    update_number_of_days_after_oldest_study(number_of_days_after_oldest_study_per_study_uid_per_study_uid, patient_pseudonym_id_generator)
    data_frame = pd.DataFrame(patient_pseudonym_id_generator.entries_of_anonymization)
    log("Saving progress with %d entries." % len(patient_pseudonym_id_generator.entries_of_anonymization))
    csv_file_name = 'key_sheet_with_PHI'+ user_input.project_name + '.csv'

    csv_folder = user_input.get_output_csv_folder_path()
    os.makedirs(csv_folder, exist_ok=True)
    csv_path = join_directories(csv_folder, csv_file_name)
    log("to %s" % csv_path)
    if keep_duplicates == False:
        # set col to str to handle multivalues
        for col in data_frame.columns:
            data_frame[col] = data_frame[col].astype(str)
        try:
            dropped_data_frame = data_frame.drop_duplicates()
        except Exception as e:
            log(f"Failed on row {len(data_frame)}, Exeption: {e}")
    else:
        dropped_data_frame = data_frame
    
    dropped_data_frame.to_csv(csv_path)


def update_number_of_days_after_oldest_study(number_of_days_after_oldest_study_per_study_uid_per_study_uid, patient_pseudonym_id_generator):
    if len(number_of_days_after_oldest_study_per_study_uid_per_study_uid) == 0:
        return
    for dictionary in patient_pseudonym_id_generator.entries_of_anonymization:
        study_instance_uid = dictionary.get('StudyInstanceUID', '')
        if is_blank(study_instance_uid):
            continue
        number_of_days_after_oldest_study = number_of_days_after_oldest_study_per_study_uid_per_study_uid.get(study_instance_uid)
        if is_not_blank(number_of_days_after_oldest_study):
            dictionary['NumberOfDaysAfterOldestStudy'] = number_of_days_after_oldest_study