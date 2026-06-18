# dicom_anonymize_app.py
import PySimpleGUI as sg

from PySimpleGUI import Window

from anonymize.src.window.constants import THEME
from anonymize.src.window.creator import create_window
from anonymize.src.window.event_handler import handle_events
from anonymize.src.window.gui.element_keys import EXIT_BUTTON_TEXT
from anonymize.src.window.user_input import UserInput


def run_dicom_anonymize_app():
    sg.theme(THEME)
    user_input = UserInput()
    window: Window = create_window(user_input)
    while True:
        event, values = window.read()

        handle_events(window, event, values, user_input)

        if event == EXIT_BUTTON_TEXT or event == sg.WIN_CLOSED:
            break
    window.close()


# run_dicom_anonymize_app()
