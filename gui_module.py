# chat_interface.py

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QTextEdit, QPushButton, QSpinBox, QMessageBox, QDialog, QLineEdit, QButtonGroup, QRadioButton, QMenu, QAction
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QEvent
from PyQt5.QtGui import QTextCursor

# Import the API module and mdizer
from api_module import get_api_key, make_api_request
import mdizer

# List of models
MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "liquid/lfm-40b:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemini-flash-1.5-8b-exp",
    "meta-llama/llama-3.1-8b-instruct:free"
]

class APICallThread(QThread):
    responses_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_key, message_history, model, num_choices=1):
        super().__init__()
        self.api_key = api_key
        self.message_history = message_history.copy()
        self.model = model
        self.num_choices = num_choices

    def run(self):
        try:
            choices = []
            for _ in range(self.num_choices):
                response_json = make_api_request(
                    api_key=self.api_key,
                    message_history=self.message_history,
                    model=self.model
                )
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    choice = response_json["choices"][0]
                    choices.append(choice)
                elif "error" in response_json:
                    error_message = response_json.get("error", "Unknown error occurred.")
                    self.error_occurred.emit(error_message)
                    return
                else:
                    self.error_occurred.emit("Unexpected response format.")
                    return
            self.responses_ready.emit(choices)
        except Exception as e:
            self.error_occurred.emit(str(e))

class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenRouter Chat Interface")
        self.setGeometry(100, 100, 800, 600)
        self.api_key = ""
        self.model_name = ""
        self.message_history = []
        self.message_positions = []
        self.initUI()

    def initUI(self):
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        # Model selection
        model_layout = QHBoxLayout()
        model_label = QLabel("Select Model:")
        self.model_combo = QComboBox()
        self.model_combo.addItems(MODELS)
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        main_layout.addLayout(model_layout)

        # Number of choices
        choices_layout = QHBoxLayout()
        choices_label = QLabel("Number of Choices:")
        self.choices_spin = QSpinBox()
        self.choices_spin.setMinimum(1)
        self.choices_spin.setMaximum(5)
        self.choices_spin.setValue(1)
        choices_layout.addWidget(choices_label)
        choices_layout.addWidget(self.choices_spin)
        main_layout.addLayout(choices_layout)

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chat_display.customContextMenuRequested.connect(self.show_chat_context_menu)
        main_layout.addWidget(self.chat_display)

        # Prompt input
        prompt_layout = QHBoxLayout()
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Type your message here...")
        self.prompt_input.returnPressed.connect(self.handle_user_input)
        send_button = QPushButton("Send")
        send_button.clicked.connect(self.handle_user_input)
        prompt_layout.addWidget(self.prompt_input)
        prompt_layout.addWidget(send_button)
        main_layout.addLayout(prompt_layout)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Retrieve API key
        try:
            self.api_key = get_api_key("API_KEY_OPENROUTER")
        except Exception as e:
            QMessageBox.critical(self, "API Key Error", str(e))
            self.close()

    def handle_user_input(self):
        user_input = self.prompt_input.text().strip()
        if not user_input:
            QMessageBox.warning(self, "Input Error", "Please enter a message.")
            return

        self.message_history.append({"role": "user", "content": user_input})
        self.prompt_input.clear()
        self.display_message("You", user_input)
        self.start_api_call()

    def start_api_call(self):
        # Start the API call
        self.model_name = self.model_combo.currentText()
        num_choices = self.choices_spin.value()

        self.thread = APICallThread(
            api_key=self.api_key,
            message_history=self.message_history,
            model=self.model_name,
            num_choices=num_choices
        )
        self.thread.responses_ready.connect(self.handle_responses)
        self.thread.error_occurred.connect(self.display_error)
        self.thread.start()

    def handle_responses(self, choices):
        if len(choices) == 1:
            # Only one choice, continue the chat
            content = choices[0]["message"]["content"].strip()
            self.message_history.append({"role": "assistant", "content": content})
            self.display_message("Assistant", content, is_html=True)
        else:
            # Multiple choices, let the user select one
            self.present_choices(choices)

    def present_choices(self, choices):
        self.choice_dialog = QDialog(self)
        self.choice_dialog.setWindowTitle("Select a Response")
        dialog_layout = QVBoxLayout()

        instruction_label = QLabel("Please select one of the responses to continue the chat:")
        dialog_layout.addWidget(instruction_label)

        self.choice_buttons = QButtonGroup(self.choice_dialog)
        for idx, choice in enumerate(choices):
            content = choice["message"]["content"].strip()
            radio_button = QRadioButton(f"Choice {idx + 1}:\n{content}")
            self.choice_buttons.addButton(radio_button, idx)
            dialog_layout.addWidget(radio_button)

        select_button = QPushButton("Select")
        select_button.clicked.connect(self.apply_selected_choice)
        dialog_layout.addWidget(select_button)

        self.choice_dialog.setLayout(dialog_layout)
        self.choice_dialog.exec_()

    def apply_selected_choice(self):
        selected_id = self.choice_buttons.checkedId()
        if selected_id == -1:
            QMessageBox.warning(self.choice_dialog, "Selection Error", "Please select a response.")
            return

        selected_button = self.choice_buttons.button(selected_id)
        content = selected_button.text().split(":\n", 1)[1]
        self.message_history.append({"role": "assistant", "content": content})
        self.display_message("Assistant", content, is_html=True)
        self.choice_dialog.accept()

    def display_message(self, sender, message, is_html=False):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)

        # Record the start position
        start_pos = cursor.position()

        formatted_message = mdizer.markdown_to_html(message) if is_html else message
        cursor.insertHtml(f"<b>{sender}:</b> {formatted_message}<br>")

        # Record the end position
        end_pos = cursor.position()

        self.message_positions.append((start_pos, end_pos))

        self.chat_display.moveCursor(QTextCursor.End)

    def show_chat_context_menu(self, position):
        cursor = self.chat_display.cursorForPosition(position)
        pos = cursor.position()

        # Find the message index corresponding to this position
        message_index = None
        for i, (start, end) in enumerate(self.message_positions):
            if start <= pos <= end:
                message_index = i
                break

        if message_index is not None:
            menu = QMenu()
            edit_action = QAction('Edit Message', self)
            edit_action.triggered.connect(lambda: self.edit_message_in_place(message_index))
            menu.addAction(edit_action)
            menu.exec_(self.chat_display.viewport().mapToGlobal(position))
        else:
            QMessageBox.warning(self, "Error", "Could not determine the message to edit.")

    def edit_message_in_place(self, index):
        if 0 <= index < len(self.message_history):
            message = self.message_history[index]
            role = message['role']
            content = message['content']

            # Open a dialog to edit the message
            edit_dialog = QDialog(self)
            layout = QVBoxLayout(edit_dialog)

            content_input = QTextEdit(edit_dialog)
            content_input.setPlainText(content)
            layout.addWidget(content_input)

            # OK and Cancel buttons
            button_layout = QHBoxLayout()
            ok_button = QPushButton("OK")
            cancel_button = QPushButton("Cancel")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            def accept():
                new_content = content_input.toPlainText().strip()
                self.edit_message(index, new_content)
                edit_dialog.accept()

            def reject():
                edit_dialog.reject()

            ok_button.clicked.connect(accept)
            cancel_button.clicked.connect(reject)

            edit_dialog.setLayout(layout)
            edit_dialog.setWindowTitle('Edit Message')
            edit_dialog.exec_()
        else:
            self.chat_display.append("<b>Error:</b> Invalid message index.")

    def edit_message(self, index, new_content):
        if 0 <= index < len(self.message_history):
            self.message_history[index]['content'] = new_content
            # Remove messages after the edited one
            self.message_history = self.message_history[:index + 1]
            self.message_positions = self.message_positions[:index]
            self.chat_display.clear()
            # Re-display messages up to the edited message
            for i in range(len(self.message_history)):
                message = self.message_history[i]
                sender = "You" if message['role'] == 'user' else "Assistant"
                content = message['content']
                is_html = message['role'] == 'assistant'
                self.display_message(sender, content, is_html=is_html)
            # If the edited message is from the user, re-send API call
            if self.message_history[index]['role'] == 'user':
                self.start_api_call()
        else:
            self.chat_display.append("<b>Error:</b> Invalid message index.")

    def display_error(self, error_text):
        QMessageBox.critical(self, "Error", error_text)

def main():
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
