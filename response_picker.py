# response_picker.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QButtonGroup, QRadioButton,
    QPushButton, QScrollArea, QWidget, QHBoxLayout, QSizePolicy, QFrame,
    QTextBrowser  # Import QTextBrowser
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
import mdizer  # Add this import

class ChoiceWidget(QWidget):
    """
    A custom widget that combines a QRadioButton with a QLabel to display
    a radio button alongside HTML-wrapped text.
    """
    def __init__(self, text, index, parent=None):
        super().__init__(parent)
        self.markdown_text = text  # Store the original Markdown text
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.radio_button = QRadioButton()
        self.label = QTextBrowser()  # Use QTextBrowser for better HTML rendering
        
        # Convert markdown to HTML
        html_content = mdizer.markdown_to_html(self.markdown_text)
        self.label.setHtml(f"<div style='max-width: 350px; word-wrap: break-word;'>{html_content}</div>")
        
        self.label.setReadOnly(True)
        self.label.setOpenExternalLinks(True)
        self.label.setStyleSheet("QTextBrowser { background-color: transparent; border: none; }")
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout.addWidget(self.radio_button)
        layout.addWidget(self.label)

        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)


class ResponsePicker(QDialog):
    def __init__(self, parent, choices):
        super().__init__(parent)
        self.setWindowTitle("Select a Response")
        self.setWindowIcon(QIcon("path/to/icon.png"))  # Set an appropriate icon
        self.selected_content = None
        self.initUI(choices)
        self.applyStyles()

    def initUI(self, choices):
        """
        Initializes the UI with response choices.
        """
        dialog_layout = QVBoxLayout()
        dialog_layout.setContentsMargins(15, 15, 15, 15)
        dialog_layout.setSpacing(15)

        # Title Label
        title_label = QLabel("Choose Your Response")
        title_font = QFont("Segoe UI", 14, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        dialog_layout.addWidget(title_label)

        # Instruction Label
        instruction_label = QLabel("Please select one of the responses to continue the chat:")
        instruction_label.setWordWrap(True)
        instruction_font = QFont("Segoe UI", 10)
        instruction_label.setFont(instruction_font)
        dialog_layout.addWidget(instruction_label)

        # Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ccc;
                border-radius: 5px;
            }
        """)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setSpacing(10)

        self.choice_buttons = QButtonGroup(self)
        self.choice_widgets = []

        for idx, choice in enumerate(choices):
            content = choice["message"]["content"].strip()

            # Create the custom ChoiceWidget
            choice_widget = ChoiceWidget(content, idx)
            self.choice_buttons.addButton(choice_widget.radio_button, idx)

            # Add to layout
            scroll_layout.addWidget(choice_widget)
            self.choice_widgets.append(choice_widget)

        # Spacer to push items to the top
        scroll_layout.addStretch()

        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        scroll_area.setMaximumHeight(300)  # Adjust as needed for up to 6 choices
        dialog_layout.addWidget(scroll_area)

        # Button Layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.select_button = QPushButton("Select")
        self.select_button.setEnabled(False)  # Initially disabled
        self.select_button.setIcon(QIcon("path/to/select_icon.png"))  # Set appropriate icon
        self.select_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 10pt;
            }
            QPushButton:disabled {
                background-color: #a5d6a7;
            }
            QPushButton:hover:!disabled {
                background-color: #45a049;
            }
        """)
        self.select_button.clicked.connect(self.apply_selected_choice)
        button_layout.addWidget(self.select_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.setIcon(QIcon("path/to/cancel_icon.png"))  # Set appropriate icon
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        dialog_layout.addLayout(button_layout)

        self.setLayout(dialog_layout)
        self.resize(600, 500)  # Set a reasonable default size

        # Connect signal to enable Select button when a choice is clicked
        self.choice_buttons.buttonClicked.connect(self.on_choice_selected)

    def applyStyles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #333333;
            }
        """)

    def apply_selected_choice(self):
        selected_id = self.choice_buttons.checkedId()
        if selected_id == -1:
            # No selection made
            return
        selected_widget = self.choice_widgets[selected_id]
        # Retrieve the original Markdown content
        self.selected_content = selected_widget.markdown_text
        self.accept()

    def get_selected_content(self):
        return self.selected_content

    def on_choice_selected(self, button):
        self.select_button.setEnabled(True)
