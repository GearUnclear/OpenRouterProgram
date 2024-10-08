# chat_interface.py

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QTextEdit, QPushButton, QSpinBox, QMessageBox,
    QLineEdit, QMenu, QAction, QDialog, QMenuBar, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QEvent
from PyQt5.QtGui import QTextCursor

# Import the API module, mdizer, and response_picker
from api_module import get_api_key, make_api_request
import mdizer
from response_picker import ResponsePicker

# List of models
MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "liquid/lfm-40b:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemini-flash-1.5-8b",
    "meta-llama/llama-3.1-8b-instruct:free"
]

class APICallThread(QThread):
    responses_ready = pyqtSignal(list)  # Signal to emit received responses
    no_responses = pyqtSignal()         # Signal to emit when no responses are received
    progress_update = pyqtSignal(int)    # Signal to emit progress updates

    def __init__(self, api_key, message_history, model, num_choices=1):
        super().__init__()
        self.api_key = api_key
        self.message_history = message_history.copy()
        self.model = model
        self.num_choices = num_choices

    def run(self):
        choices = []
        try:
            for i in range(self.num_choices):
                # Determine temperature for each choice
                temperature = 0.5 if i % 2 == 0 else 1.5

                response_json = make_api_request(
                    api_key=self.api_key,
                    message_history=self.message_history,
                    model=self.model,
                    temperature=temperature  # Pass varying temperature
                )

                if "choices" in response_json and len(response_json["choices"]) > 0:
                    choice = response_json["choices"][0]
                    choices.append(choice)
                    self.progress_update.emit(len(choices))  # Emit progress
                elif "error" in response_json:
                    error_message = response_json.get("error", "Unknown error occurred.")
                    # Log the error if needed
                    print(f"API Error: {error_message}")
                    break  # Stop further processing on error
                else:
                    # Unexpected response format
                    print("Unexpected response format from API.")
                    break  # Stop further processing on unexpected format

        except Exception as e:
            # Log the exception if needed
            print(f"Exception during API call: {str(e)}")

        # After attempting all API calls, determine what to emit
        if choices:
            self.responses_ready.emit(choices)
        else:
            self.no_responses.emit()

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

        # Progress Bar Layout
        progress_layout = QHBoxLayout()
        self.progress_label = QLabel("Progress: 0/0")
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # Indeterminate initially
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # Hidden initially
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        main_layout.addLayout(progress_layout)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Menu bar
        menu_bar = self.menuBar()
        chat_menu = menu_bar.addMenu('Chat')

        clear_chat_action = QAction('Clear Chat', self)
        clear_chat_action.triggered.connect(self.clear_chat)
        chat_menu.addAction(clear_chat_action)

        # Retrieve API key
        try:
            self.api_key = get_api_key("API_KEY_OPENROUTER")
        except Exception as e:
            QMessageBox.critical(self, "API Key Error", str(e))
            self.close()

    def update_progress(self, received):
        total = self.choices_spin.value()
        self.progress_label.setText(f"Progress: {received}/{total}")
        self.progress_bar.setValue(received)
        if received >= total:
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
        else:
            self.progress_bar.setVisible(True)
            self.progress_label.setVisible(True)

    def clear_chat(self):
        confirmation = QMessageBox.question(
            self,
            "Clear Chat",
            "Are you sure you want to clear the chat? This will erase the conversation history.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirmation == QMessageBox.Yes:
            self.message_history.clear()
            self.message_positions.clear()
            self.chat_display.clear()
            QMessageBox.information(self, "Chat Cleared", "The chat has been cleared.")

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

        # Initialize progress bar
        self.progress_bar.setMaximum(num_choices)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"Progress: 0/{num_choices}")
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)

        self.thread = APICallThread(
            api_key=self.api_key,
            message_history=self.message_history,
            model=self.model_name,
            num_choices=num_choices
        )
        self.thread.responses_ready.connect(self.handle_responses)
        self.thread.no_responses.connect(self.handle_no_responses)
        self.thread.progress_update.connect(self.update_progress)
        self.thread.start()

    def handle_responses(self, choices):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        if len(choices) == 1:
            # Only one choice, continue the chat
            content = choices[0]["message"]["content"].strip()
            self.message_history.append({"role": "assistant", "content": content})
            self.display_message("Assistant", content, is_html=True)
        else:
            # Multiple choices, use the ResponsePicker
            response_picker = ResponsePicker(self, choices)
            if response_picker.exec_() == QDialog.Accepted:
                selected_content = response_picker.get_selected_content()
                if selected_content:
                    self.message_history.append({"role": "assistant", "content": selected_content})
                    self.display_message("Assistant", selected_content, is_html=True)
            else:
                QMessageBox.warning(self, "Selection Cancelled", "No response was selected.")

    def handle_no_responses(self):
        # Delete the last user message
        if self.message_history and self.message_history[-1]["role"] == "user":
            last_message = self.message_history.pop()
            self.message_positions.pop()
            self.chat_display.undo()  # Undo the last display
            self.alert_user_no_responses(last_message["content"])
        else:
            # In case there's no user message to delete
            self.alert_user_no_responses(None)

    def alert_user_no_responses(self, last_message_content):
        error_dialog = QMessageBox(self)
        error_dialog.setWindowTitle("Error")
        if last_message_content:
            error_dialog.setText("No responses received due to an error. Your last message has been removed.")
            copy_button = error_dialog.addButton("Copy Message", QMessageBox.ActionRole)
            error_dialog.addButton(QMessageBox.Ok)
        else:
            error_dialog.setText("An unknown error occurred, and no responses were received.")
            error_dialog.addButton(QMessageBox.Ok)

        error_dialog.exec_()

        if last_message_content:
            # If the user chose to copy the message
            clicked_button = error_dialog.clickedButton()
            if clicked_button == copy_button:
                self.copy_message_to_clipboard(last_message_content)

    def copy_message_to_clipboard(self, message):
        clipboard = QApplication.clipboard()
        clipboard.setText(message)
        QMessageBox.information(self, "Copied", "Your last message has been copied to the clipboard.")

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
                if new_content:
                    self.edit_message(index, new_content)
                    edit_dialog.accept()
                else:
                    QMessageBox.warning(self, "Input Error", "Message content cannot be empty.")

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
            # Reset message_positions
            self.message_positions = []
            # Clear and re-display messages up to the edited message
            self.chat_display.clear()
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

    def copy_message_to_clipboard(self, message):
        clipboard = QApplication.clipboard()
        clipboard.setText(message)
        QMessageBox.information(self, "Copied", "Your last message has been copied to the clipboard.")

def main():
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
