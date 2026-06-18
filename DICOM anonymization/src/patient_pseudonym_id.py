import pandas as pd
from pydicom import Dataset
from pydicom.valuerep import PersonName

from anonymize.src.window.user_input import UserInput
from common.utils.string_utils import default_if_blank, is_not_blank, is_blank

PATIENT_PSEUDONYM_ID_OFFSET = 20000000


class PatientPseudonymIdGenerator:
    def __init__(self):
        self.next_id_serial_nr = 1
        self.patient_pseudonym_id_dictionary_based_on_empi = {} # (empi: str): id
        self.patient_pseudonym_id_dictionary_based_on_mrn_and_accession_number = {} # (mrn: str, accession_number: str): id
        self.patient_pseudonym_id_dictionary_based_on_mrn_and_birth_date = {} # (mrn: str, YYYYmmdd: str): id
        self.patient_pseudonym_id_dictionary_based_on_mrn_and_institution = {} # (mrn: str, institution: str): id
        self.patient_pseudonym_id_dictionary_based_on_patient_person_name_and_birth_date = {} # (PersonNameInstance: PersonName, YYYYmmdd: str): id
        self.patient_pseudonym_id_dictionary_based_on_patient_family_and_given_name_and_birth_date = {} # (family_name: str, given_name: str, YYYYmmdd: str): id
        self.entries_of_anonymization = [] # list of dictionaries: One dictionary per study containing the pseudonym ID and relevat information of the patient and study. Ready to be saved later as DATAFRAME.

    def get_patient_pseudonym_id(self, user_input: UserInput, patient_id: str, issuer_of_patient_id: str, accession_number,
                                 patient_name: PersonName, patient_birth_date: str, pseudonym_accession_number: str, ds: Dataset):
        patient_id_without_leading_zeros = patient_id.lstrip('0')

        result = default_if_blank(
            self.patient_pseudonym_id_dictionary_based_on_mrn_and_accession_number.get((patient_id, accession_number)),
            self.patient_pseudonym_id_dictionary_based_on_mrn_and_accession_number.get((patient_id_without_leading_zeros, accession_number)))

        if result is not None:
            self.save_entry_of_anonymization(result, patient_id, issuer_of_patient_id, accession_number, patient_name, patient_birth_date, pseudonym_accession_number, ds)
            return result

        result =  self.search_for_pseudonym_id_given_with_different_study(accession_number, issuer_of_patient_id,
                                                                       patient_birth_date, patient_id,
                                                                       patient_id_without_leading_zeros, patient_name,
                                                                       result)
        if result is None:
            result = self.generate_new_pseudonym_id(patient_id, issuer_of_patient_id, accession_number, patient_name, patient_birth_date)

        self.save_entry_of_anonymization(result, patient_id, issuer_of_patient_id, accession_number, patient_name, patient_birth_date, pseudonym_accession_number, ds)

        return result

    def generate_new_pseudonym_id(self, patient_id: str, issuer_of_patient_id: str, accession_number,
                                  patient_name: PersonName, patient_birth_date: str):
        new_pseudonym_id = str(PATIENT_PSEUDONYM_ID_OFFSET + self.next_id_serial_nr)
        self.next_id_serial_nr += 1

        patient_id_without_leading_zeros = patient_id.lstrip('0')
        self.patient_pseudonym_id_dictionary_based_on_mrn_and_accession_number[(patient_id, accession_number)] = new_pseudonym_id
        self.patient_pseudonym_id_dictionary_based_on_mrn_and_accession_number[(patient_id_without_leading_zeros, accession_number)] = new_pseudonym_id

        if is_not_blank(patient_birth_date):
            self.patient_pseudonym_id_dictionary_based_on_mrn_and_birth_date[(patient_id, patient_birth_date)] = new_pseudonym_id
            self.patient_pseudonym_id_dictionary_based_on_mrn_and_birth_date[(patient_id_without_leading_zeros, patient_birth_date)] = new_pseudonym_id

        if is_not_blank(issuer_of_patient_id):
            self.patient_pseudonym_id_dictionary_based_on_mrn_and_institution[(patient_id, issuer_of_patient_id)] = new_pseudonym_id
            self.patient_pseudonym_id_dictionary_based_on_mrn_and_institution[(patient_id_without_leading_zeros, issuer_of_patient_id)] = new_pseudonym_id

        family_and_given_name_and_birth_date_tuple = get_well_defined_patient_family_and_given_name_and_birth_date_tuple(patient_name, patient_birth_date)
        if family_and_given_name_and_birth_date_tuple is not None:
            self.patient_pseudonym_id_dictionary_based_on_patient_person_name_and_birth_date[family_and_given_name_and_birth_date_tuple] = new_pseudonym_id

        return new_pseudonym_id

    def search_for_pseudonym_id_given_with_different_study(self, accession_number, issuer_of_patient_id,
                                                           patient_birth_date, patient_id,
                                                           patient_id_without_leading_zeros, patient_name, result):
        if is_not_blank(patient_birth_date):
            result = default_if_blank(
                self.patient_pseudonym_id_dictionary_based_on_mrn_and_birth_date.get((patient_id, patient_birth_date)),
                self.patient_pseudonym_id_dictionary_based_on_mrn_and_birth_date.get((patient_id_without_leading_zeros, patient_birth_date)))
        if result is not None:
            return result

        family_and_given_name_and_birth_date_tuple = get_well_defined_patient_family_and_given_name_and_birth_date_tuple(patient_name, patient_birth_date)
        if family_and_given_name_and_birth_date_tuple is not None:
            self.patient_pseudonym_id_dictionary_based_on_patient_person_name_and_birth_date.get(family_and_given_name_and_birth_date_tuple)
        if result is not None:
            return result

        if is_not_blank(issuer_of_patient_id):
            result = default_if_blank(
                self.patient_pseudonym_id_dictionary_based_on_mrn_and_institution.get((patient_id, issuer_of_patient_id)),
                self.patient_pseudonym_id_dictionary_based_on_mrn_and_institution.get((patient_id_without_leading_zeros, issuer_of_patient_id)))
        if result is not None:
            return result

        result = self.patient_pseudonym_id_dictionary_based_on_mrn_and_birth_date.get((patient_id_without_leading_zeros, accession_number))
        if result is not None:
            return result
        return None

    def fill_with_ids_from_csv(self, csv, mrn_column='mrn', accession_number_column='accession'):
        df = pd.read_csv(csv, dtype=str)
        if mrn_column not in df.columns or accession_number_column not in df.columns or "patient_ID" not in df.columns:
            raise ValueError(f"The CSV file must contain the columns '{mrn_column}', '{accession_number_column}' and 'patient_ID'.")
        for index, row in df.iterrows():
            mrn: str = row[mrn_column].strip()
            accession_number = row[accession_number_column].strip()
            self.patient_pseudonym_id_dictionary_based_on_mrn_and_accession_number[(mrn, accession_number)] = row["patient_ID"]
            self.patient_pseudonym_id_dictionary_based_on_mrn_and_accession_number[(mrn.lstrip('0'), accession_number)] = row["patient_ID"]


    def save_entry_of_anonymization(self, patient_pseudonym_id: str, patient_id: str, issuer_of_patient_id: str, accession_number,
                                 patient_name: PersonName, patient_birth_date: str, pseudonym_accession_number: str, ds: Dataset):
        study_date = ds.get('StudyDate', '')
        study_description = ds.get('StudyDescription', '')
        admitting_diagnoses_description = ds.get('AdmittingDiagnosesDescription', '')
        study_instance_uid = ds.get('StudyInstanceUID', '')
        patient_age = ds.get('PatientAge', '')
        patient_sex = ds.get('PatientSex', '')
        patient_weight = ds.get('PatientWeight', '')
        patient_size = ds.get('PatientSize', '')
        smoking_status = ds.get('SmokingStatus', '')
        ethnic_group = ds.get('EthnicGroup', '')
        occupation = ds.get('Occupation', '')
        country_of_residence = ds.get('CountryOfResidence', '')

        self.entries_of_anonymization.append({
            'PatientPseudonymID': patient_pseudonym_id,
            'PatientRealID': patient_id,
            'RealAccessionNumber': accession_number,
            'PseudonymAccessionNumber': pseudonym_accession_number,
            'IssuerOfPatientID': issuer_of_patient_id,
            'StudyDate': study_date,
            'StudyDescription': study_description,
            'AdmittingDiagnosesDescription': admitting_diagnoses_description,
            'StudyInstanceUID': study_instance_uid,
            'PatientName': str(patient_name),
            'PatientBirthDate': str(patient_birth_date),
            'PatientAge': str(patient_age),
            'PatientSex': str(patient_sex),
            'PatientWeight': str(patient_weight),
            'PatientSize': str(patient_size),
            'SmokingStatus': str(smoking_status),
            'EthnicGroup': str(ethnic_group),
            'Occupation': str(occupation),
            'CountryOfResidence': str(country_of_residence),
        })


def get_well_defined_patient_family_and_given_name_and_birth_date_tuple(patient_name: PersonName, patient_birth_date: str):
    if is_blank(patient_birth_date) or patient_name is None:
        return None
    family_name = patient_name.family_name
    given_name = patient_name.given_name
    if is_blank(family_name) or is_blank(given_name):
        return None
    return (family_name, given_name, patient_birth_date)