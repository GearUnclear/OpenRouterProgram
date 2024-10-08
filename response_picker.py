# response_picker.py

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QButtonGroup, QRadioButton, QPushButton
from PyQt5.QtCore import Qt

class ResponsePicker(QDialog):
    def __init__(self, parent, choices):
        super().__init__(parent)
        self.setWindowTitle("Select a Response")
        self.selected_content = None
        self.initUI(choices)

    def initUI(self, choices):
        dialog_layout = QVBoxLayout()

        instruction_label = QLabel("Please select one of the responses to continue the chat:")
        dialog_layout.addWidget(instruction_label)

        self.choice_buttons = QButtonGroup(self)
        for idx, choice in enumerate(choices):
            content = choice["message"]["content"].strip()
            radio_button = QRadioButton(f"Choice {idx + 1}:\n{content}")
            self.choice_buttons.addButton(radio_button, idx)
            dialog_layout.addWidget(radio_button)

        select_button = QPushButton("Select")
        select_button.clicked.connect(self.apply_selected_choice)
        dialog_layout.addWidget(select_button)

        self.setLayout(dialog_layout)

    def apply_selected_choice(self):
        selected_id = self.choice_buttons.checkedId()
        if selected_id == -1:
            # No selection made
            return
        selected_button = self.choice_buttons.button(selected_id)
        self.selected_content = selected_button.text().split(":\n", 1)[1]
        self.accept()

    def get_selected_content(self):
        return self.selected_content
