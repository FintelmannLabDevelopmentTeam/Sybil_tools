# Sybil_tools

This repository contains a collection of tools uesful for working with Sybil.


## Command line tool
Name: command_line_tool

Description:

Instructions:


## Series Selection Script
Name: series_selection_function

Description: Provides the function selectSingleSeriesFromStudy() and its helper functions.
The standard configuration is set up to select the best suited scan for analysis with Sybil.

Working principles:
The selectSingleSeriesFromStudy() filters based on the following characteristics in the presented order (defaults in parantethis).
1. IV contrast (only_noncontrast)
2. Slice thickness cutoffs ([0,2.5])
3. Slice thickness (min)
4. Kernel class (prefer_sharp)
5. Tube voltage (max)
6. Tube amperage (max)
7. Random selection (True)

The function creates a new column called "kernel_class" on which the kernel filtering is based. 
It contains the classification into soft and sharp. The exact mappings can be found in the classifyKernels() subfunction.

Instructions:
This function is designed to be imported and called.
This function expects a pandas datframe containing the columns specified in "filtering columns".
Please make sure the column names match.
If the information required for filtering is not available to you, set the "ignore" flag in the function call.
To modify the behaviour of the function please reference available options and documentation in the function itself.
