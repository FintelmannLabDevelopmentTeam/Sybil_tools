from PySimpleGUI import Window

from anonymize.src.window.constants import APP_NAME
from anonymize.src.window.gui.element_keys import ESTIMATED_REMAINING_TIME_KEY, EXCHANGE_MESSGES_TEXT_KEY, \
    PROGRESS_BAR_KEY, PROGRESS_PERCENTAGE_KEY
from anonymize.src.window.user_input import UserInput
from common.gui.buttons import get_run_pause_button, get_exit_button
from common.gui.constants import FUTURA_Normal_FONT
from common.gui.filters import *


def create_anonymization_progress_window(user_input: UserInput):
    layout = [
        get_progress_status(),
    ]

    window: Window = sg.Window(APP_NAME, layout, resizable=True, grab_anywhere=True, font=FUTURA_Normal_FONT, size=(1400, 200))
    return window

def get_progress_status():
    return [
        [
            get_progress_bar_and_percentage(),
        ],
        [sg.Text("", key=ESTIMATED_REMAINING_TIME_KEY), ],
        get_progress_messages(),
    ]


def get_progress_messages():
    return sg.Text("",
                   tooltip="current DICOM file being anonymized",
                   key=EXCHANGE_MESSGES_TEXT_KEY)


def get_progress_bar():
    return sg.ProgressBar(1, orientation='h', border_width=10, expand_x=True, key=PROGRESS_BAR_KEY)


def get_progress_percentage():
    return sg.Text("0%", key=PROGRESS_PERCENTAGE_KEY)


def get_progress_bar_and_percentage():
    return [
        get_progress_bar(),
        get_progress_percentage(),
    ]
