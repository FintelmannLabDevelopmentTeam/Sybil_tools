from common.entity.dicom_constants import DEFAULT_WHITELIST, DEFAULT_BLACKLIST
from common.utils.operating_system_utils import *
from common.utils.time import *


class UserInput:
    def __init__(self):
        self.project_name = None

        self.threshold = 1
        self.use_whitelist = False
        self.whitelist = DEFAULT_WHITELIST
        self.use_blacklist = False
        self.blacklist = DEFAULT_BLACKLIST

        self.input_folder_directory = get_desktop_directory()
        self.input_csv_file_path = None
        self.first_row_is_header = True
        self.csv_delimiter = ","
        self.csv_mrn_column_name = "mrn"
        self.csv_accession_number_column_name = "accession"
        self.output_folder_name = 'DICOM_anonymized_' + get_current_time_formated()
        self.output_folder_directory = get_desktop_directory()
        self.output_csv_folder_path = join_directories(get_desktop_directory(), 'ANONYMIZED_KEY_FILES')

    def get_whitelist(self):
        return self.whitelist

    def set_whitelist(self, whitelist):
        self.whitelist = whitelist

    def get_blacklist(self):
        return self.blacklist

    def set_blacklist(self, blacklist):
        self.blacklist = blacklist

    def get_summary_string(self):
        summary = []
        summary.append("Project name: " + default_if_blank(self.project_name, "not specified"))
        summary.append(
            "Directory to input folder: " + default_if_blank(self.input_folder_directory, "not specified"))
        if self.input_csv_file_path is not None:
            summary.append("Input MRN/ACC to ID CSV file: " + self.input_csv_file_path)
            summary.append("MRN Column Name in CSV: " + self.csv_mrn_column_name)
            summary.append("Accession Number Column Name in CSV: " + self.csv_accession_number_column_name)
        else:
            summary.append("No Input MRN/ACC to ID CSV file specified")
        summary.append("Threshold for number of images per series: " + str(self.threshold))
        summary.append(self.get_info_list(self.use_whitelist, self.whitelist, "Whitelist"))
        summary.append(self.get_info_list(self.use_blacklist, self.blacklist, "Blacklist"))

        summary.append("Output folder name: " + default_if_blank(self.output_folder_name, "not specified"))
        summary.append(
            "Directory to output folder: " + default_if_blank(self.get_output_folder_path(), "not specified"))
        summary.append("Output CSV folder path: " + default_if_blank(self.get_output_csv_folder_path(), "not specified"))

        return summary

    def get_output_folder_path(self):
        return join_directories(self.output_folder_directory, self.output_folder_name)

    def get_output_csv_folder_path(self):
        return self.output_csv_folder_path

    def get_info_list(self, use: bool, my_list: str, list_name: str):
        if not use or is_blank(my_list):
            return "No " + list_name
        return list_name + ": " + my_list