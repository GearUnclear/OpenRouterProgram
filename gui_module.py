# chat_interface.py

import sys
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QTextBrowser, QPushButton, QSpinBox, QMessageBox,
    QLineEdit, QMenu, QAction, QDialog, QMenuBar, QProgressBar, QTextEdit,
    QSlider, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QTextCursor

# Import the updated API module
from api_module import get_api_key, make_api_request
import mdizer
from response_picker import ResponsePicker
from model_list import ModelListWindow
import markdown
# Import BeautifulSoup for HTML parsing
from bs4 import BeautifulSoup

class APICallThread(QThread):
    """
    Worker thread to handle API calls without blocking the GUI.
    """
    response_ready = pyqtSignal(list)      # Emits the list of choices once all responses are received
    no_responses = pyqtSignal()            # Emits if no responses are received
    progress_update = pyqtSignal(int)      # Emits the number of chunks received for progress bar

    def __init__(self, api_key, message_history, model, temperature_values, num_choices=1, context_length=None, max_completion_tokens=None, reasoning_effort=None, reasoning_max_tokens=None, exclude_reasoning=False, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.message_history = message_history.copy()
        self.model = model
        self.temperature_values = temperature_values
        self.num_choices = num_choices
        self.context_length = context_length
        self.max_completion_tokens = max_completion_tokens
        self.reasoning_effort = reasoning_effort
        self.reasoning_max_tokens = reasoning_max_tokens
        self.exclude_reasoning = exclude_reasoning
        self.parent_window = parent  # Reference to the main window for HTML extraction

    def run(self):
        choices = []
        try:
            for i in range(self.num_choices):
                temperature = self.temperature_values[i % len(self.temperature_values)]
                print(f"Choice {i+1}, Temperature: {temperature}")  # Debug statement

                response_text = ''
                # Make the streaming API request
                for chunk in make_api_request(
                    api_key=self.api_key,
                    message_history=self.message_history,
                    model=self.model,
                    temperature=temperature,
                    stream=True,
                    context_length=self.context_length,
                    max_completion_tokens=self.max_completion_tokens,
                    reasoning_effort=self.reasoning_effort,
                    reasoning_max_tokens=self.reasoning_max_tokens,
                    exclude_reasoning=self.exclude_reasoning
                ):
                    response_text += chunk
                    self.progress_update.emit(1)  # Emit one chunk received

                # After the full response is received
                choice = {'message': {'content': response_text}}
                choices.append(choice)
        except Exception as e:
            # Log the exception if needed
            print(f"Exception during API call: {str(e)}")

        # After attempting all API calls, determine what to emit
        if choices:
            self.response_ready.emit(choices)
        else:
            self.no_responses.emit()

class ChatWindow(QMainWindow):
    """
    Main window of the chat application.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenRouter Chat Interface")
        self.setGeometry(100, 100, 800, 600)
        self.api_key = ""
        self.model_name = ""
        self.model_id = ""
        self.context_length = 0
        self.max_completion_tokens = 0
        self.message_history = []
        self.message_positions = []
        self.initUI()

    def initUI(self):
        """
        Initializes the user interface.
        """
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        # Load models from the JSON file
        try:
            with open(r'C:\Code - Copy\FlyAway-pyrq\__PYDATA\models_jason\models_data.json', 'r') as f:
                model_data = json.load(f)
            self.model_data = model_data['data']
            self.model_id_map = {model['name']: model['id'] for model in self.model_data}
            models_list = [model['name'] for model in self.model_data]  # Create list of model names
        except Exception as e:
            QMessageBox.critical(self, "Model Load Error", f"Failed to load models: {str(e)}")
            self.close()
            return

        # Model selection
        model_layout = QHBoxLayout()
        model_label = QLabel("Select Model:")
        self.model_combo = QComboBox()
        self.model_combo.addItems(models_list)  # Use the loaded models_list instead of MODELS
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        main_layout.addLayout(model_layout)

        # Number of choices
        choices_layout = QHBoxLayout()
        choices_label = QLabel("Number of Choices:")
        self.choices_spin = QSpinBox()
        self.choices_spin.setMinimum(1)
        self.choices_spin.setMaximum(6)  # Updated maximum to 6
        self.choices_spin.setValue(1)
        choices_layout.addWidget(choices_label)
        choices_layout.addWidget(self.choices_spin)
        main_layout.addLayout(choices_layout)

        # Chat display using QTextBrowser for better HTML rendering
        self.chat_display = QTextBrowser()
        self.chat_display.setReadOnly(True)
        self.chat_display.setOpenExternalLinks(True)  # Enable clickable links
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
        self.progress_label = QLabel("Progress: 0")
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # Indeterminate initially
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # Hidden initially
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        main_layout.addLayout(progress_layout)

        # Add a button to open the model list window
        model_list_button = QPushButton("Show Model List")
        model_list_button.clicked.connect(self.show_model_list)
        main_layout.addWidget(model_list_button)

        # Context Length Slider
        context_length_layout = QHBoxLayout()
        context_length_label = QLabel("Context Length:")
        self.context_length_slider = QSlider(Qt.Horizontal)
        self.context_length_slider.setMinimum(0)
        self.context_length_slider.setMaximum(1000000)  # Default max
        self.context_length_slider.setValue(self.context_length)
        self.context_length_slider.valueChanged.connect(self.update_context_length_label)
        self.context_length_value_label = QLabel(str(self.context_length))
        context_length_layout.addWidget(context_length_label)
        context_length_layout.addWidget(self.context_length_slider)
        context_length_layout.addWidget(self.context_length_value_label)
        main_layout.addLayout(context_length_layout)

        # Max Completion Tokens Slider
        max_tokens_layout = QHBoxLayout()
        max_tokens_label = QLabel("Max Completion Tokens:")
        self.max_tokens_slider = QSlider(Qt.Horizontal)
        self.max_tokens_slider.setMinimum(0)
        self.max_tokens_slider.setMaximum(256000)  # Default max
        self.max_tokens_slider.setValue(self.max_completion_tokens)
        self.max_tokens_slider.valueChanged.connect(self.update_max_tokens_label)
        self.max_tokens_value_label = QLabel(str(self.max_completion_tokens))
        max_tokens_layout.addWidget(max_tokens_label)
        max_tokens_layout.addWidget(self.max_tokens_slider)
        max_tokens_layout.addWidget(self.max_tokens_value_label)
        main_layout.addLayout(max_tokens_layout)

        # Temperature Slider
        self.temp_layout = QHBoxLayout()
        temp_label = QLabel("Temperature:")
        self.temp_slider = QSlider(Qt.Horizontal)
        self.temp_slider.setMinimum(50)  # 0.5
        self.temp_slider.setMaximum(125) # 1.25
        self.temp_slider.setValue(70)     # 0.7 default
        self.temp_slider.valueChanged.connect(self.update_temp_label)
        self.temp_value_label = QLabel("0.7")
        self.temp_layout.addWidget(temp_label)
        self.temp_layout.addWidget(self.temp_slider)
        self.temp_layout.addWidget(self.temp_value_label)
        main_layout.addLayout(self.temp_layout)

        # Reasoning Controls
        # First, group box to organize and frame the reasoning controls
        reasoning_group = QWidget()
        reasoning_layout = QVBoxLayout(reasoning_group)
        reasoning_title = QLabel("<b>Reasoning Token Controls</b>")
        reasoning_layout.addWidget(reasoning_title)
        
        # Reasoning Effort ComboBox
        reasoning_effort_layout = QHBoxLayout()
        reasoning_effort_label = QLabel("Reasoning Effort:")
        self.reasoning_effort_combo = QComboBox()
        self.reasoning_effort_combo.addItems(["None", "Low", "Medium", "High"])
        self.reasoning_effort_combo.setCurrentIndex(0)  # "None" selected by default
        self.reasoning_effort_combo.currentIndexChanged.connect(self.update_reasoning_controls)
        reasoning_effort_layout.addWidget(reasoning_effort_label)
        reasoning_effort_layout.addWidget(self.reasoning_effort_combo)
        reasoning_layout.addLayout(reasoning_effort_layout)
        
        # Reasoning Max Tokens Slider
        reasoning_max_tokens_layout = QHBoxLayout()
        reasoning_max_tokens_label = QLabel("Max Tokens for Reasoning:")
        self.reasoning_max_tokens_slider = QSlider(Qt.Horizontal)
        self.reasoning_max_tokens_slider.setMinimum(0)
        self.reasoning_max_tokens_slider.setMaximum(64000)  # Default max
        self.reasoning_max_tokens_slider.setValue(0)
        self.reasoning_max_tokens_slider.valueChanged.connect(self.update_reasoning_max_tokens_label)
        self.reasoning_max_tokens_value_label = QLabel("0")
        reasoning_max_tokens_layout.addWidget(reasoning_max_tokens_label)
        reasoning_max_tokens_layout.addWidget(self.reasoning_max_tokens_slider)
        reasoning_max_tokens_layout.addWidget(self.reasoning_max_tokens_value_label)
        reasoning_layout.addLayout(reasoning_max_tokens_layout)
        
        # Exclude Reasoning Option
        reasoning_exclude_layout = QHBoxLayout()
        self.exclude_reasoning_checkbox = QCheckBox("Exclude Reasoning from Response")
        self.exclude_reasoning_checkbox.setChecked(False)
        reasoning_exclude_layout.addWidget(self.exclude_reasoning_checkbox)
        reasoning_layout.addLayout(reasoning_exclude_layout)
        
        # Add the reasoning group to main layout
        main_layout.addWidget(reasoning_group)

        # Connect choices spin box to control temperature slider visibility
        self.choices_spin.valueChanged.connect(self.update_temp_slider_visibility)
        self.update_temp_slider_visibility(1)  # Initial state

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

        # After loading the model data:
        self.model_data = model_data['data']
        self.model_id_map = {model['name']: model['id'] for model in self.model_data}

    def extract_text_from_html(self, html_content):
        """
        Extracts plain text from HTML content.

        Args:
            html_content (str): The HTML content to extract text from.

        Returns:
            str: The extracted plain text.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text()
        except Exception as e:
            print(f"Error extracting text from HTML: {e}")
            return html_content  # Return the original content if extraction fails

    def update_progress(self, chunks_received):
        """
        Updates the progress bar based on the number of chunks received.
        """
        current_value = self.progress_bar.value() + chunks_received
        self.progress_bar.setValue(current_value)
        self.progress_label.setText(f"Chunks received: {current_value}")

    def clear_chat(self):
        """
        Clears the chat history and the display.
        """
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
        """
        Handles the user's input when they send a message.
        """
        user_input = self.prompt_input.text().strip()
        if not user_input:
            QMessageBox.warning(self, "Input Error", "Please enter a message.")
            return

        self.message_history.append({"role": "user", "content": user_input})
        self.prompt_input.clear()
        self.display_message("You", user_input)
        self.start_api_call()

    def start_api_call(self):
        """
        Initiates the API call in a separate thread.
        """
        self.model_name = self.model_combo.currentText()
        model_id = self.model_id_map.get(self.model_name, self.model_id)
        if not model_id:
            QMessageBox.warning(self, "Model Error", f"Could not find ID for model: {self.model_name}")
            return

        num_choices = self.choices_spin.value()

        # Define temperature values based on number of choices
        if num_choices == 1:
            temperature_values = [self.temp_slider.value() / 100]
        else:
            all_temperatures = [0.5, 0.6, 0.7, 1.0, 1.1, 1.25]
            temperature_values = all_temperatures[:num_choices]

        print(f"Number of choices: {num_choices}, Temperatures: {temperature_values}")  # Debug statement

        # Initialize progress bar
        self.progress_bar.setMaximum(0)  # Indeterminate
        self.progress_bar.setValue(0)
        self.progress_label.setText("Chunks received: 0")
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)

        # Disable input during API call
        self.prompt_input.setEnabled(False)

        # Use the stored context_length and max_completion_tokens if available
        context_length = self.context_length if self.context_length > 0 else None
        max_completion_tokens = self.max_completion_tokens if self.max_completion_tokens > 0 else None
        
        # Get reasoning parameters
        reasoning_effort = None
        reasoning_max_tokens = None
        exclude_reasoning = False
        
        # Get reasoning effort if selected
        effort_index = self.reasoning_effort_combo.currentIndex()
        if effort_index > 0:  # If not "None"
            if effort_index == 1:
                reasoning_effort = "low"
            elif effort_index == 2:
                reasoning_effort = "medium"
            elif effort_index == 3:
                reasoning_effort = "high"
        
        # Get reasoning max tokens if set
        reasoning_max_tokens_value = self.reasoning_max_tokens_slider.value()
        if reasoning_max_tokens_value > 0:
            reasoning_max_tokens = reasoning_max_tokens_value
            
        # Get exclude reasoning setting
        exclude_reasoning = self.exclude_reasoning_checkbox.isChecked()
        
        print(f"Reasoning parameters - Effort: {reasoning_effort}, Max Tokens: {reasoning_max_tokens}, Exclude: {exclude_reasoning}")

        self.thread = APICallThread(
            api_key=self.api_key,
            message_history=self.message_history,
            model=model_id,
            temperature_values=temperature_values,
            num_choices=num_choices,
            context_length=self.context_length,
            max_completion_tokens=self.max_completion_tokens,
            reasoning_effort=reasoning_effort,
            reasoning_max_tokens=reasoning_max_tokens,
            exclude_reasoning=exclude_reasoning,
            parent=self
        )
        self.thread.response_ready.connect(self.handle_responses)
        self.thread.no_responses.connect(self.handle_no_responses)
        self.thread.progress_update.connect(self.update_progress)
        self.thread.finished.connect(self.api_call_finished)
        self.thread.start()

    def api_call_finished(self):
        """
        Re-enables the input after the API call is finished.
        """
        self.prompt_input.setEnabled(True)

    def handle_responses(self, choices):
        """
        Handles the responses received from the API.
        """
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

        if len(choices) == 1:
            response = choices[0]["message"]
            content = response.get("content", "").strip()
            reasoning = response.get("reasoning", "")
            
            # Add the response to message history
            message_data = {"role": "assistant", "content": content}
            if reasoning:
                message_data["reasoning"] = reasoning
            self.message_history.append(message_data)
            
            # Display in the chat
            self.display_message("Assistant", content, reasoning)
        else:
            response_picker = ResponsePicker(self, choices)
            if response_picker.exec_() == QDialog.Accepted:
                selected_content = response_picker.get_selected_content()
                selected_reasoning = response_picker.get_selected_reasoning()
                if selected_content:
                    # Create message data for history
                    message_data = {"role": "assistant", "content": selected_content}
                    if selected_reasoning:
                        message_data["reasoning"] = selected_reasoning
                    self.message_history.append(message_data)
                    
                    # Display in chat
                    self.display_message("Assistant", selected_content, selected_reasoning)
            else:
                QMessageBox.warning(self, "Selection Cancelled", "No response was selected.")

    def handle_no_responses(self):
        """
        Handles the scenario where no responses are received.
        """
        # Delete the last user message
        if self.message_history and self.message_history[-1]["role"] == "user":
            last_message = self.message_history.pop()
            if self.message_positions:
                self.message_positions.pop()
            self.chat_display.undo()  # Undo the last display
            self.alert_user_no_responses(last_message["content"])
        else:
            # In case there's no user message to delete
            self.alert_user_no_responses(None)

    def alert_user_no_responses(self, last_message_content):
        """
        Alerts the user that no responses were received.
        """
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
        """
        Copies a message to the clipboard.
        """
        clipboard = QApplication.clipboard()
        clipboard.setText(message)
        QMessageBox.information(self, "Copied", "Your message has been copied to the clipboard.")

    def display_message(self, sender, message, reasoning=None):
        """
        Displays a message in the chat window with proper markdown formatting.
        """
        if sender.lower() == "assistant":
            try:
                formatted_message = mdizer.markdown_to_html(message)
                if reasoning:
                    formatted_reasoning = mdizer.markdown_to_html(reasoning)
                else:
                    formatted_reasoning = None
            except Exception as e:
                formatted_message = self.escape_html(message)
                formatted_reasoning = self.escape_html(reasoning) if reasoning else None
                print(f"Markdown conversion failed: {e}")
        else:
            formatted_message = self.escape_html(message)
            formatted_reasoning = None
        
        # Start with sender and the main message
        full_message = f"<b>{sender}:</b><br>{formatted_message}"
        
        # Add reasoning if it exists
        if formatted_reasoning:
            full_message += f"<br><br><details><summary><b>Reasoning</b></summary><div class='reasoning'>{formatted_reasoning}</div></details>"
            
        # Add final break
        full_message += "<br><br>"
        
        # Use insertHtml instead of append
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(full_message)
        
        # Record the start and end positions for editing
        end_pos = cursor.position()
        start_pos = end_pos - len(full_message)
        self.message_positions.append((start_pos, end_pos))
        
        # Ensure the latest message is visible
        self.chat_display.ensureCursorVisible()

    def escape_html(self, text):
        """
        Escapes HTML special characters in text.

        Args:
            text (str): The text to escape.

        Returns:
            str: The escaped text.
        """
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def show_chat_context_menu(self, position):
        """
        Shows a context menu for editing messages.
        """
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
        """
        Allows the user to edit a message in place.
        """
        if 0 <= index < len(self.message_history):
            message = self.message_history[index]
            role = message['role']
            content = message['content']

            # Open a dialog to edit the message
            edit_dialog = QDialog(self)
            edit_dialog.setWindowTitle('Edit Message')
            layout = QVBoxLayout(edit_dialog)

            content_input = QTextEdit(edit_dialog)  # Changed from QLineEdit to QTextEdit
            content_input.setText(content)
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
            edit_dialog.exec_()
        else:
            self.chat_display.append("<b>Error:</b> Invalid message index.")

    def edit_message(self, index, new_content):
        """
        Edits a message in the message history and updates the display.
        """
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
                self.display_message(sender, content)  # Markdown handled internally
            # If the edited message is from the user, re-send API call
            if self.message_history[index]['role'] == 'user':
                self.start_api_call()
        else:
            self.chat_display.append("<b>Error:</b> Invalid message index.")

    def show_model_list(self):
        """
        Opens the model list window and connects the model selection and update signals.
        """
        self.model_list_window = ModelListWindow()
        self.model_list_window.model_selected.connect(self.select_model)
        self.model_list_window.models_updated.connect(self.reload_models)  # **New: Connect the models_updated signal**
        self.model_list_window.show()

    def select_model(self, model_name, model_id, context_length, max_completion_tokens):
        """
        Selects the model based on the emitted data from ModelListWindow.
        """
        self.model_name = model_name
        self.model_id = model_id
        self.context_length = context_length
        self.max_completion_tokens = max_completion_tokens

        # Update the combo box
        index = self.model_combo.findText(model_name)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        else:
            QMessageBox.warning(self, "Model Selection Error", f"Model '{model_name}' not found in the list.")

        # Update slider maximums and current values
        self.context_length_slider.setMaximum(context_length)
        self.context_length_slider.setValue(context_length)
        self.max_tokens_slider.setMaximum(max_completion_tokens)
        self.max_tokens_slider.setValue(max_completion_tokens)

        # Update labels
        self.update_context_length_label(context_length)
        self.update_max_tokens_label(max_completion_tokens)

        # Display model information
        info_message = (f"Model '{model_name}' selected.\n"
                        f"Context Length: {context_length}\n"
                        f"Max Completion Tokens: {max_completion_tokens}")
        QMessageBox.information(self, "Model Selected", info_message)

    def update_context_length_label(self, value):
        self.context_length = min(value, self.context_length_slider.maximum())
        self.context_length_value_label.setText(str(self.context_length))

    def update_max_tokens_label(self, value):
        self.max_completion_tokens = min(value, self.max_tokens_slider.maximum())
        self.max_tokens_value_label.setText(str(self.max_completion_tokens))

    def load_models(self):
        """
        Loads the model list from the JSON file and initializes model-related attributes.
        """
        try:
            with open(r'C:\Code - Copy\FlyAway-pyrq\__PYDATA\models_jason\models_data.json', 'r') as f:
                model_data = json.load(f)
            MODELS = [model['name'] for model in model_data['data']]
        except Exception as e:
            QMessageBox.critical(self, "Model Load Error", f"Failed to load models: {str(e)}")
            self.close()
            return

        # Initialize model_data and model_id_map
        self.model_data = model_data['data']
        self.model_id_map = {model['name']: model['id'] for model in self.model_data}

        # Populate the model_combo if it exists
        try:
            self.model_combo.clear()
            self.model_combo.addItems(MODELS)
        except AttributeError:
            pass  # model_combo not yet initialized

    def reload_models(self):
        """
        Reloads the model list from the JSON file and updates the model combo box.
        """
        try:
            with open(r'C:\Code - Copy\FlyAway-pyrq\__PYDATA\models_jason\models_data.json', 'r') as f:
                model_data = json.load(f)
                
            # Update model_data and model_id_map
            self.model_data = model_data['data']
            self.model_id_map = {model['name']: model['id'] for model in self.model_data}
            models_list = [model['name'] for model in self.model_data]

            # Update the model_combo
            current_model = self.model_combo.currentText()
            self.model_combo.blockSignals(True)  # Prevent triggering selection changes
            self.model_combo.clear()
            self.model_combo.addItems(models_list)  # Add the new models
            
            # Try to restore the previously selected model
            if current_model in models_list:
                index = self.model_combo.findText(current_model)
                self.model_combo.setCurrentIndex(index)
            else:
                self.model_combo.setCurrentIndex(0)  # Select the first model by default
            
            self.model_combo.blockSignals(False)

            QMessageBox.information(self, "Models Updated", "The model list has been updated with the latest models.")
            
        except Exception as e:
            QMessageBox.critical(self, "Model Reload Error", f"Failed to reload models: {str(e)}")
            return

    def update_temp_label(self, value):
        """Updates the temperature label with the actual value (divided by 100)."""
        temp = value / 100
        self.temp_value_label.setText(f"{temp:.2f}")

    def update_temp_slider_visibility(self, num_choices):
        """Shows/hides temperature controls based on number of choices."""
        show = (num_choices == 1)
        for widget in (self.temp_layout.itemAt(i).widget() for i in range(self.temp_layout.count())):
            widget.setVisible(show)

    def update_reasoning_controls(self, index):
        """
        Updates the state of reasoning controls based on the selected effort level.
        """
        # Enable/disable max tokens slider based on selected effort
        if index == 0:  # None
            self.reasoning_max_tokens_slider.setEnabled(False)
            self.reasoning_max_tokens_slider.setValue(0)
            self.update_reasoning_max_tokens_label(0)
        else:
            self.reasoning_max_tokens_slider.setEnabled(True)
            # Always update values based on effort level when changing
            if index == 1:  # Low
                self.reasoning_max_tokens_slider.setValue(1600)  # ~20% of 8000
            elif index == 2:  # Medium
                self.reasoning_max_tokens_slider.setValue(16000)  # ~50% of 32000
            elif index == 3:  # High
                self.reasoning_max_tokens_slider.setValue(32000)  # ~80% of max (64000 max)
            self.update_reasoning_max_tokens_label(self.reasoning_max_tokens_slider.value())

    def update_reasoning_max_tokens_label(self, value=None):
        """
        Updates the label showing the max tokens for reasoning.
        """
        if value is None:
            value = self.reasoning_max_tokens_slider.value()
        self.reasoning_max_tokens_value_label.setText(str(value))

def main():
    """
    Entry point of the application.
    """
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
