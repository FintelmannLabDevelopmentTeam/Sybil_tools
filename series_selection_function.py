"""Provides the function selectSingleSeriesFromStudy() and its helper functions.

Authors: Jonathan Mueller, Noe Bertramo
Last updated: 2026-01-02
License: """



from typing import Literal, Optional, Union
import numpy as np
import pandas as pd
import ast

#required columns
# identifying columns (required)
studyID_column = "Study Instance UID"
manufacturer_column = "Manufacturer"

# filtering columns
contrast_column = "IV CONTRAST (IVC)"
slicethickness_column = "Slice Thickness"
kernel_column = "Reconstruction Kernel"
tubevoltage_column = "Peak Tube Voltage"
tubecurrent_column = "Tube Current"

#created columns
kernel_class_column_name = "kernel_class"

manufacturer_names = {
    "ge": ["GE MEDICAL SYSTEMS"],
    "siemens": ["SIEMENS", "Siemens Healthineers"],
    "philips": ["Philips"],
    "toshiba": ["TOSHIBA", "CANON"]}


def extract_kernel(x):
    """Extracts the first element of a list, if possible, returns original value otherwise.
    
    Kernels are sometimes saved as list elements. The kernel is nearly always the first element, with other elements having little importance.
    Use .apply to run this eg: df["colum"].apply(SeriesSelection_V2.extract_kernel)"""
    x = str(x).strip()
    if x.startswith("[") and x.endswith("]"):
        try:
            lst = ast.literal_eval(x)
            return lst[0]
        except:
            return x
    return x


def printStatusMessage(df, n_series_pre, n_studies_pre, filter_by):
    """Prints a status message, containing the number of removed series, number of studies lost and studies with more than one sereis reamining after the step.""" 
    print(f"Filtering by {filter_by}. Removing {n_series_pre - len(df)} series. Losing {n_studies_pre - df[studyID_column].nunique()} studies.") 
    print(f"{df[df.duplicated(studyID_column,keep=False)][studyID_column].nunique()} studies left with more than one series.\n")


def filterByNumericalColumn(df, column, filter_method):
    """Generic filter function for all numerical columns."""

    if filter_method == "ignore":
        print(f"ignoring {column}\n")
        return df

    # check validity of keyword
    if filter_method not in {"min", "max"}:
        raise KeyError(f"{filter_method} is not a valid argument. Please use min, max or ignore")
    
    #calculate number of series and studies before filtering
    n_studies_pre = df[studyID_column].nunique()
    n_series_pre = len(df)

    #enforce float for incoming column
    df[column] = df[column].astype(float)

    #create rank column
    df["numerical_rank"] = df.groupby(studyID_column)[column].rank(method="dense")
    #filter by rank column
    df = df[df["numerical_rank"] == df.groupby(studyID_column)["numerical_rank"].transform(filter_method)]
    
    df = df.drop(columns="numerical_rank")
    printStatusMessage(df, n_series_pre, n_studies_pre, f"{column} {filter_method}")

    return df


def filterByContrast(df, contrast_filtermethod):
    """Specialty function for filtering by contrast.
    
    The options are: only_contrast, only_noncontrast, prefer_contrast, prefer_noncontrast. 
    "Only" options remove anything, but the desired option. "Prefer" options remove the undesired options, if a desired option is available. If not they take no action.
    Rows containing "ERROR" as contrast code are treated as NA and always counted as the undesired option."""
    # check if selection by contrast is wanted
    if contrast_filtermethod == "ignore":
        print("ignoring contrast\n")
        return df

    allowed_values = ["Yes", "No", "ERROR"] #changing this will only change the printout not the actually allowed codes

    # check for values in contrast column which can not be read
    invalid_values_mask = ~df[contrast_column].isin(allowed_values)
    if invalid_values_mask.sum() > 0:
        print(f"{invalid_values_mask.sum()} rows with unrecognized contrast codes found. Please make sure that all relevant entries are coded as {allowed_values}.\n"
            "The code will run as-is, but all unknown codes will not be accounted for.\n")

    #calculate number of series and studies before filtering
    n_series_pre = len(df)
    n_studies_pre = df[studyID_column].nunique()

    # only keep series with contrast
    if contrast_filtermethod == "only_contrast":
        df = df[df[contrast_column] == "Yes"]
        printStatusMessage(df, n_series_pre, n_studies_pre, contrast_filtermethod)

    # only keep series without contrast
    elif contrast_filtermethod == "only_noncontrast":
        df = df[df[contrast_column] == "No"]
        printStatusMessage(df, n_series_pre, n_studies_pre, contrast_filtermethod)

    # prefer contrast
    elif contrast_filtermethod == "prefer_contrast":

        #create rank column
        df["contrast_rank"] = np.where(df[contrast_column] == "Yes", 1, 2)
        #filter by rank column
        df = df[df["contrast_rank"]== df.groupby(studyID_column)["contrast_rank"].transform("min")]
        printStatusMessage(df, n_series_pre, n_studies_pre, contrast_filtermethod)
        df = df.drop(columns="contrast_rank")

    # prefer non-contrast
    elif contrast_filtermethod == "prefer_noncontrast":

        #create rank column
        df["contrast_rank"] = np.where(df[contrast_column] == "No", 1, 2)
        #filter by rank column
        df = df[df["contrast_rank"]== df.groupby(studyID_column)["contrast_rank"].transform("min")]
        printStatusMessage(df, n_series_pre, n_studies_pre, contrast_filtermethod)
        df = df.drop(columns="contrast_rank")

    else:
        raise KeyError(f"{contrast_filtermethod} is not a valid argument")

    return df


def filterBySliceThicknessCutoffs(df, slicethickness_cutoffs):
    """Specialty function to filter for slice thickness cutoffs."""
    # check if thickness cutoffs are wanted
    if slicethickness_cutoffs == "ignore":
        print("ignoring slice thickness cutoffs\n")
        return df

    # check if input is valid
    if not (isinstance(slicethickness_cutoffs, list) and len(slicethickness_cutoffs) == 2):
        raise ValueError("slicethickness_cutoffs must be a list with min and max. If you want only one bound set the other to 0 or float(inf)")

    #calculate number of series and studies before filtering
    n_studies_pre = df[studyID_column].nunique()
    n_series_pre = len(df)

    #filter by slice thickness cutoffs
    df = df[df[slicethickness_column]
        .astype(float)
        .between(slicethickness_cutoffs[0], slicethickness_cutoffs[1])]

    printStatusMessage(df,n_series_pre,n_studies_pre,f"slice thickness cutoffs {slicethickness_cutoffs}",)

    return df


def classifyKernels(df):
    """Helper function to classify kernels into soft and sharp.
    
    The manufactuere names can be changed in the top level "manufacturer_names" dict.
    The mappings can be changed in the individual kernel mappings.
    The Siemens kernel name contains a two digit sharpness indicator, which is the only value used in this function. The cutoff for the distincion is set as "siemens_cutoff".
    Toshiba and Canon have individual mappings.
    Please be advised: Kernel classification is complex and the distinction between sharp and soft is not always clear. This is a best effort with the information available.
    Sources include: https://academy.siemens-healthineers.com/en-us/ct-kernel-concept-usa (accessed 2026-04-10),
    https://repository.tudelft.nl/record/uuid:f4db76bd-8c3f-49b3-b3d3-b8e299738a7b (accessed 2026-04-10)
    """
    #clean kernel column
    df[kernel_column] = df[kernel_column].str.strip()

    #mapping of soft/sharp kernels
    siemens_cutoff = float(50)

    ge_map = {
        "SOFT":     "soft",
        "STANDARD": "soft",
        "DETAIL":   "sharp",
        "DETAIL2":  "sharp",
        "BONE":     "sharp",
        "BONEPLUS": "sharp",
        "LUNG":     "sharp",
        "EDGE":     "sharp"}

    philips_map = {
        "A": "soft",
        "B": "soft",
        "C": "sharp",
        "D": "sharp",
        "E": "sharp",
        "L": "sharp",
        "YA": "sharp",
        "YB": "sharp",
        "YC": "sharp",
        "YE": "sharp",
        "YD": "sharp",
        "YF": "sharp"}

    toshiba_map = { #this map is not used, it is here for demonstrative purposes
        "FC*":  "soft",
        "FC0*": "soft",
        "FC1*": "soft",
        "FC5*": "sharp",
        "FC8*": "sharp",
        "FC3*": "sharp"}

    toshiba_map_doubledigits = {
        float(0): "soft",
        float(1): "soft",
        float(5): "sharp",
        float(8): "sharp",
        float(3): "sharp"}

    #determining which lines belong to which manufacturere
    siemens_mask = df[manufacturer_column].isin(manufacturer_names["siemens"])
    ge_mask = df[manufacturer_column].isin(manufacturer_names["ge"])
    philips_mask = df[manufacturer_column].isin(manufacturer_names["philips"])
    toshiba_mask = df[manufacturer_column].isin(manufacturer_names["toshiba"])

    #apply kernel mapping by manufacturer

    #siemens
    df.loc[siemens_mask, kernel_class_column_name] = np.where(
        df.loc[siemens_mask, kernel_column]
        .str.extract(r"(\d\d)")[0]
        .astype(float)<= siemens_cutoff,"soft","sharp")

    #ge
    df.loc[ge_mask, kernel_class_column_name] = df.loc[ge_mask, kernel_column].map(ge_map)

    #philips
    df.loc[philips_mask, kernel_class_column_name] = df.loc[philips_mask, kernel_column].map(philips_map)

    #toshiba
    df.loc[toshiba_mask, kernel_class_column_name] = np.where(df.loc[toshiba_mask, kernel_column].str.contains(r"FC\d(?:$|\D)"),"soft", #set all single digit kernels to soft
                                                              df.loc[toshiba_mask, kernel_column].str.extract(r"(\d)\d")[0].astype(float).map(toshiba_map_doubledigits)) #map double digit kernels, where no single digit was found

    #check if all kernels could be mapped
    if df[kernel_class_column_name].isna().any():
        print(f"ATTENTION: {df[kernel_class_column_name].isna().sum()} kernels couldn't be assigned to a class. Please check mapping against kernel and manufacturer names in your dataset.")

    return df


def filterByKernel(df, kernel_filtermethod):
    """Filters by soft/sharp kernel.
    
    Only "prefer" options are currently available.
    The soft/sharp mapping is done using the classifyKernels() function."""
    if kernel_filtermethod == "ignore":
        print("ignoring reconstruction kernel\n")
        return df

    df = classifyKernels(df)

    if kernel_filtermethod not in {"prefer_sharp", "prefer_soft"}:
        raise KeyError(f"{kernel_filtermethod} is not a valid argument. Please use prefer_sharp, prefer_soft or ignore")

    #calculate number of series and studies before filtering
    n_series_pre = len(df)
    n_studies_pre = df[studyID_column].nunique()

    kernel_ranks = {"sharp": 1, "soft": 2} if kernel_filtermethod == "prefer_sharp" else {"soft": 1, "sharp": 2}
    
    #create rank column
    df["kernel_rank"] = df[kernel_class_column_name].map(kernel_ranks).fillna(2) #fill nas to make sure they don't get dropped
    #filer by rank column
    df = df[df["kernel_rank"] == df.groupby(studyID_column)["kernel_rank"].transform("min")]
    printStatusMessage(df, n_series_pre, n_studies_pre, f"kernel {kernel_filtermethod}")
    df = df.drop(columns="kernel_rank")

    return df


def selectSingleSeriesFromStudy(df,
                                contrast_filtermethod: Literal["only_contrast","only_noncontrast","prefer_contrast","prefer_noncontrast","ignore",] = "only_noncontrast",
                                slicethickness_cutoffs: Union[Optional[list[float]], Literal["ignore"]] = [0,2.5],
                                slicethickness_filtermethod: Literal["min", "max", "ignore"] = "min",
                                kernel_filtermethod: Literal["prefer_sharp", "prefer_soft", "ignore"] = "prefer_sharp",
                                tubevoltage_filtermethod: Literal["min", "max", "ignore"] = "max",
                                tubecurrent_filtermethod: Literal["min", "max", "ignore"] = "max",
                                remaining_randomselection: Literal[True, False] = True):
    """Main function of the module SeriesSelection. Filters a datframe down so only one series per study remains.
    
    The behavior for each criterion can be modified in the function call.
    The standard behavior is set up to maximize performance on Sybil predictions."""
    
    df = filterByContrast(df, contrast_filtermethod=contrast_filtermethod)

    df = filterBySliceThicknessCutoffs(df,slicethickness_cutoffs=slicethickness_cutoffs)

    df = filterByNumericalColumn(df,column=slicethickness_column,filter_method=slicethickness_filtermethod)

    df = filterByKernel(df, kernel_filtermethod=kernel_filtermethod)

    df = filterByNumericalColumn(df, column=tubevoltage_column, filter_method=tubevoltage_filtermethod)

    df = filterByNumericalColumn(df, column=tubecurrent_column, filter_method=tubecurrent_filtermethod)

    #randomselect if desired
    if remaining_randomselection == True:

        #calculate number of series and studies before filtering
        n_series_pre = len(df)
        n_studies_pre = df[studyID_column].nunique()
        #select one series at random
        df = df.groupby(studyID_column).sample(random_state=42)
        printStatusMessage(df, n_series_pre, n_studies_pre, "random selection")

    #check that only one series per study is left
    if df.duplicated(subset=studyID_column).any():
        print(f"ATTENTION: {df.duplicated(studyID_column).sum()} studies left with more than one series selected, please check")

    return df
