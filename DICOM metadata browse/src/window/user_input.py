from common.utils.operating_system_utils import *
from common.utils.time import *


class UserInput:
    def __init__(self):
        self.input_folder_directory = get_desktop_directory()
        self.is_content_of_a_folder_belongs_to_same_study = True

        self.output_folder_name = 'DICOM_headers_' + get_current_time_formated()
        self.output_folder_directory = get_desktop_directory()

    def get_summary_string(self):
        summary = []

        summary.append(
            "Directory to input folder: " + default_if_blank(self.input_folder_directory, "not specified"))

        summary.append("Content of a folder belongs to the same study: " + map_bool_to_yes_no(self.is_content_of_a_folder_belongs_to_same_study))

        summary.append("Output folder name: " + default_if_blank(self.output_folder_name, "not specified"))
        summary.append(
            "Directory to output folder: " + default_if_blank(self.get_output_folder_path(), "not specified"))

        return summary

    def get_output_folder_path(self):
        return join_directories(self.output_folder_directory, self.output_folder_name)