import os

from pydicom import Dataset

from anonymize.src.window.user_input import UserInput
from common.utils.operating_system_utils import join_directories
from common.utils.string_utils import is_blank, remove_special_characters

ANONYMIZED_DICOMS_FOLDER_NAME = "anonymized_dicoms"


def get_dicom_file_name(ds):
    #  modality = ds.get("Modality", "")
    series_instance_uid = remove_special_characters(ds.get("SeriesInstanceUID"))
    instance_number = str(ds.get("InstanceNumber", "0")).zfill(4)
    suffix = '.dcm'
    file_name = join_and_clean_file_naming(series_instance_uid[-10:], instance_number) + suffix
    return file_name


def get_series_folder_name(ds):
    modality = ds.get("Modality", "")
    series_description = ds.get("SeriesDescription", '')[:50]
    series_instance_uid_suffix = remove_special_characters(ds.get("SeriesInstanceUID"))[-10:]
    return join_and_clean_file_naming(modality, series_description, series_instance_uid_suffix)


def get_study_folder_name(ds):
    study_description = ds.get("StudyDescription", "")[:50]
    study_instance_uid_suffix = remove_special_characters(ds.get("StudyInstanceUID"))[-10:]
    return join_and_clean_file_naming(study_description, study_instance_uid_suffix)


def get_and_prepare_anonymized_dicom_file_path(user_input: UserInput, ds: Dataset, patients_paths_dictionary_per_patient_pseudonym_id: dict, series_paths_dictionary_per_study_uid: dict,
                                               series_paths_dictionary_per_series_uid: dict):
    series_folder_path = get_and_prepare_series_folder_path(user_input, ds, patients_paths_dictionary_per_patient_pseudonym_id, series_paths_dictionary_per_study_uid,
                                                            series_paths_dictionary_per_series_uid)
    dicom_file_name = get_dicom_file_name(ds)
    return join_directories(series_folder_path, dicom_file_name)


def get_and_prepare_series_folder_path(user_input, ds, patients_paths_dictionary_per_patient_pseudonym_id: dict, series_paths_dictionary_per_study_uid: dict, series_paths_dictionary_per_series_uid: dict):
    series_instance_uid = ds.get("SeriesInstanceUID")
    path_cache = series_paths_dictionary_per_series_uid.get(series_instance_uid)
    if path_cache is not None:
        return path_cache
    study_folder_path = get_and_prepare_study_folder_path(user_input, ds, patients_paths_dictionary_per_patient_pseudonym_id, series_paths_dictionary_per_study_uid)
    series_folder_name = get_series_folder_name(ds)
    series_folder_path = join_directories(study_folder_path, series_folder_name)
    series_paths_dictionary_per_series_uid[series_instance_uid] = series_folder_path
    return prepare_output_folder_directory(series_folder_path)


def get_and_prepare_study_folder_path(user_input, ds: Dataset, patients_paths_dictionary_per_patient_pseudonym_id: dict, series_paths_dictionary_per_study_uid: dict):
    study_instance_uid = ds.get("StudyInstanceUID")
    path_cache = series_paths_dictionary_per_study_uid.get(study_instance_uid)
    if path_cache is not None:
        return path_cache
    patient_folder_path = get_and_prepare_patient_folder_path(user_input, ds, patients_paths_dictionary_per_patient_pseudonym_id)
    study_folder_name = get_study_folder_name(ds)
    study_folder_path = join_directories(patient_folder_path, study_folder_name)
    series_paths_dictionary_per_study_uid[study_instance_uid] = study_folder_path
    return prepare_output_folder_directory(study_folder_path)


def clean_character_in_file_naming(character):
    if character.isalnum():
        return character
    return '_'


def clean_file_naming(file_name):
    result = ''
    for character in file_name:
        result += clean_character_in_file_naming(character)
    return result


def join_and_clean_file_naming(*name_components):
    cleaned_name_components = []
    for name_component in name_components:
        cleaned_name_components.append(clean_file_naming(name_component))
    return '__'.join(cleaned_name_components)


def get_and_prepare_patient_folder_path(user_input, ds: Dataset, patients_paths_dictionary_per_patient_pseudonym_id: dict):
    patient_id = ds.PatientID
    path_cache = patients_paths_dictionary_per_patient_pseudonym_id.get(patient_id)
    if path_cache is not None:
        return path_cache
    dicoms_folder_path = get_anonymized_dicoms_folder_path(user_input)
    patient_folder_path = join_directories(dicoms_folder_path, patient_id)
    patients_paths_dictionary_per_patient_pseudonym_id[patient_id] = patient_folder_path
    return prepare_output_folder_directory(patient_folder_path)


def get_anonymized_dicoms_folder_path(user_input):
    output_folder_path = user_input.get_output_folder_path()
    return join_directories(output_folder_path, ANONYMIZED_DICOMS_FOLDER_NAME)


def get_and_prepare_anonymized_dicoms_folder_path(user_input):
    output_folder_path = get_and_prepare_output_folder_directory(user_input)
    return prepare_output_folder_directory(output_folder_path)


def get_and_prepare_output_folder_directory(user_input: UserInput):
    output_folder_path = user_input.get_output_folder_path()
    return prepare_output_folder_directory(output_folder_path)


def prepare_output_folder_directory(output_folder_path):
    os.makedirs(output_folder_path, exist_ok=True)
    return output_folder_path
