import os
import subprocess
import appscript
import shutil
import platform
import time

import pandas as pd
import json

import pydicom

from pyfiglet import figlet_format

import tkinter as tk
from tkinter import filedialog


def is_runnning(app):
    count = int(subprocess.check_output(["osascript",
                "-e", "tell application \"System Events\"",
                "-e", "count (every process whose name is \"" + app + "\")",
                "-e", "end tell"]).strip())
    return count > 0

def convert_dicomdir_to_dcm(dicomdir_path, dcm_path):

    # Go one folder up
    dicomdir_directory = os.path.dirname(dicomdir_path)
    dicomdir = pydicom.dcmread(dicomdir_path)

    os.mkdir(dcm_path)

    for patient in dicomdir.patient_records:
        dir_name = str(patient.PatientName) + "__" + patient.PatientID
        dir_path = os.path.join(dcm_path, dir_name)

        dir_path = dir_path.replace('(', '').replace(')', '')
        dir_path = dir_path.replace(' ', '_').replace('^', '_').replace(",", "")

        os.mkdir(dir_path)

        for i in range(len(patient.children)):
            exam = patient.children[i]

            dir_name = exam.StudyDate + "__" + exam.StudyDescription + "__" + patient.PatientID + "__" + exam.AccessionNumber
            dir_path_exam = os.path.join(dir_path, dir_name)

            dir_path_exam = dir_path_exam.replace('(', '').replace(')', '')
            dir_path_exam = dir_path_exam.replace(' ', '_').replace('^', '_').replace(",", "")

            os.mkdir(dir_path_exam)

            for k in range(len(exam.children)):
                series = exam.children[k]

                dir_name = series.Modality + "__" + series.SeriesDescription + "__" + str(k)
                dir_path_series = os.path.join(dir_path_exam, dir_name)

                dir_path_series = dir_path_series.replace('(', '').replace(')', '')
                dir_path_series = dir_path_series.replace(' ', '_').replace('^', '_').replace(",", "")

                os.mkdir(dir_path_series)

                for j in range(len(series.children)):
                    image = series.children[j]

                    image_file_name = image.ReferencedFileID[1]
                    image_path = os.path.join(dicomdir_directory, "IMAGES", image_file_name)
                    #dicom = pydicom.dcmread(image_path)

                    dcm_file_name = image.ReferencedSOPClassUIDInFile + "__" + str(j) + ".dcm"
                    dcm_save_path = os.path.join(dir_path_series, dcm_file_name)
                    shutil.copy(image_path, dcm_save_path)


def get_predictions(dir_path):
    files = os.listdir(dir_path)
    files_paths = ""

    for file_name in files:
        file_path = os.path.join(dir_path, file_name)
        files_paths = files_paths + "-F 'dicom=@" + file_path + "' "

    sybil_cmd = "CURL -X POST -F 'data={}' " + files_paths + "http://127.0.0.1:5000/dicom/files"

    shell_output = subprocess.check_output(sybil_cmd, shell=True, text=True)
    js = json.loads(shell_output)

    return js


def traverse_folders(folder, p):

    items = os.listdir(folder)
    subfolders = [item for item in items if os.path.isdir(os.path.join(folder, item))]

    if len(subfolders) == 0:
        print(folder)

        json_result = get_predictions(dir_path=folder)

        if json_result["statusCode"] != 200:
            pred1 = "NA"
            pred2 = "NA"
            pred3 = "NA"
            pred4 = "NA"
            pred5 = "NA"
            pred6 = "NA"
        else:
            predictions = json_result["data"]["predictions"][0][0]
            pred1 = predictions[0]
            pred2 = predictions[1]
            pred3 = predictions[2]
            pred4 = predictions[3]
            pred5 = predictions[4]
            pred6 = predictions[5]

        new_data = {"folderName" : folder,
                    "statusCode" : json_result["statusCode"],
                    "pred1" : pred1,
                    "pred2": pred2,
                    "pred3": pred3,
                    "pred4": pred4,
                    "pred5": pred5,
                    "pred6": pred6,
                    "comment" : json_result["message"],
                    "runtime" : json_result["runtime"]
                    }

        p = p.append(new_data, ignore_index=True)

    else:
        for subfolder_name in subfolders:

            subfolder = os.path.join(folder, subfolder_name)
            p = traverse_folders(subfolder,p)

    return p


def iteration():

    input_path = filedialog.askdirectory()
    if input_path == "":
        return False
    print("Selected input path: " + input_path)

    output_folder = os.path.dirname(input_path)
    print("Folder for the output CSV: " + output_folder)

    for item in os.listdir(input_path):
        item_path = os.path.join(input_path, item)
        if not os.path.isdir(item_path) and item == "DICOMDIR":
            print("")
            print("### Visage export (DICOMDIR) detected ###")
            print("Converting...")

            dicomdir_path = os.path.join(input_path, "DICOMDIR")

            dcm_path = os.path.join(input_path, "dcm")
            dcm_path_base = dcm_path
            counter = 1
            while os.path.exists(dcm_path):
                dcm_path = dcm_path_base + str(counter)
                counter += 1

            convert_dicomdir_to_dcm(dicomdir_path, dcm_path)

            series_list = list()

            for patient in os.listdir(dcm_path):
                print("Patient: " + patient)
                patient_path = os.path.join(dcm_path, patient)

                for exam in os.listdir(patient_path):
                    exam_path = os.path.join(patient_path, exam)

                    for series in os.listdir(exam_path):
                        no = len(series_list) + 1
                        print("Series #" + str(no) + ":   " + series)
                        series_path = os.path.join(exam_path, series)
                        series_list.append(series_path)

            if len(series_list) == 1:
                input_path = series_list[0]
            else:
                series_no = "b"
                while series_no != "a" and not series_no.isnumeric():
                    series_no = input("Select series (type 'a' to select all):  ")

                if series_no == "a":
                    input_path = dcm_path
                else:
                    series_no = int(series_no) - 1
                    input_path = series_list[series_no]

    p = pd.DataFrame(
        columns=["folderName", "statusCode", "pred1", "pred2", "pred3", "pred4", "pred5", "pred6", "comment",
                 "runtime"])
    p = traverse_folders(input_path, p)

    p["version"] = [sybil_version] * len(p)

    # So that we can print the full df
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    print("")
    print(p)
    print("")

    name_part = pd.Timestamp.now().strftime("%Y-%m-%d__%H-%M-%S")
    output_file = os.path.join(output_folder, "Sybil_predictions__" + name_part + ".csv")
    p.to_csv(output_file, index=False)

    return True


os_system = platform.system()

root = tk.Tk()
root.withdraw()

print(figlet_format("Sybil"))
print("A validated deep learning model")

if subprocess.check_output("docker ps -q --filter ancestor=mitjclinic/sybil:mgh", shell=True, text=True) == "":
    if os_system == "Windows":
        subprocess.Popen("Docker run -p 127.0.0.1:5000:5000 mitjclinic/sybil:mgh")
    elif os_system == "Darwin":
        appscript.app("Terminal").do_script("Docker run -p 127.0.0.1:5000:5000 mitjclinic/sybil:mgh")

    print("Please wait while the docker container is starting.")

    for i in range(60):
        print("\rTime remaining: {} seconds.".format(100 - i), end='')
        time.sleep(1.1)  # :))
    print("")

# Version check
if os_system == "Windows":
    command = "docker exec $(docker ps -q --filter ancestor=mitjclinic/sybil:mgh) bash -c \"python -c \\\"import sybil; print(sybil.__version__)\\\"\""
elif os_system == "Darwin":
    command = "docker exec `docker ps -q --filter ancestor=mitjclinic/sybil:mgh` bash -c 'python -c\"import sybil; print(sybil.__version__)\"'"
sybil_version = subprocess.check_output(command, shell=True, text=True)
print("Version: " + sybil_version)

print("")

while iteration():
    pass

print("")
input("Press enter to exit")

exit()