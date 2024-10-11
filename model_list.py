from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QApplication, QHeaderView,
    QHBoxLayout, QCheckBox, QWidget
)
from PyQt5.QtCore import Qt, QSettings, pyqtSignal
import requests
import json
from datetime import datetime
import sys
import os

class PreferencesWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setGeometry(200, 200, 300, 200)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.checkboxes = {}
        
        for column in self.parent.columns:
            cb = QCheckBox(column)
            cb.setChecked(not self.parent.table.isColumnHidden(self.parent.columns.index(column)))
            cb.stateChanged.connect(self.updateColumnVisibility)
            self.checkboxes[column] = cb
            layout.addWidget(cb)

        self.setLayout(layout)

    def updateColumnVisibility(self):
        for column, checkbox in self.checkboxes.items():
            column_index = self.parent.columns.index(column)
            self.parent.table.setColumnHidden(column_index, not checkbox.isChecked())
        
        self.parent.savePreferences()

class ModelListWindow(QDialog):
    model_selected = pyqtSignal(str, str, int, int)  # Signal to emit model name, ID, context_length, and max_completion_tokens

    def format_pricing(self, pricing_dict):
        """
        Formats the pricing dict into a user-friendly string.
        """
        pricing_parts = []
        for key, value in pricing_dict.items():
            try:
                price_per_token = float(value)
                # Convert to $ per million tokens
                # According to your mapping where 0.000001 = $1
                price_per_million = price_per_token / 0.000001 * 1
                pricing_parts.append(f"{key}: ${price_per_million:.2f}/M tokens")
            except ValueError:
                pricing_parts.append(f"{key}: {value}")
        return ', '.join(pricing_parts)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Model List")
        self.setGeometry(150, 150, 1200, 600)
        self.settings = QSettings("YourCompany", "ModelListApp")
        self.models = self.load_models_from_file()
        if self.models:
            self.columns = self.get_columns_from_models(self.models)
        else:
            self.columns = ["id", "name", "created", "description", "context_length", "max_completion_tokens"]  # default columns
        self.initUI()
        if self.models:
            self.populate_table(self.models)
        else:
            QMessageBox.warning(self, "Warning", "No models loaded.")

        # Connect the double-click event
        self.table.cellDoubleClicked.connect(self.on_model_double_clicked)

    def get_columns_from_models(self, models):
        columns_set = set()
        for model in models:
            columns_set.update(model.keys())
            # Add top_provider fields
            if 'top_provider' in model:
                columns_set.add('context_length')
                columns_set.add('max_completion_tokens')
        columns = list(columns_set)
        columns.sort()  # optional: sort the columns
        return columns

    def initUI(self):
        """
        Initializes the user interface for the model list window.
        """
        layout = QVBoxLayout()

        # Table to display models
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setWordWrap(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        # Buttons layout
        button_layout = QHBoxLayout()

        refresh_button = QPushButton("Refresh Model List")
        refresh_button.clicked.connect(self.load_models)
        button_layout.addWidget(refresh_button)

        preferences_button = QPushButton("Preferences")
        preferences_button.clicked.connect(self.showPreferences)
        button_layout.addWidget(preferences_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.loadPreferences()

    def showPreferences(self):
        pref_window = PreferencesWindow(self)
        pref_window.exec_()

    def loadPreferences(self):
        for i, column in enumerate(self.columns):
            hidden = self.settings.value(f"column_{column}_hidden", False, type=bool)
            self.table.setColumnHidden(i, hidden)

    def savePreferences(self):
        for i, column in enumerate(self.columns):
            hidden = self.table.isColumnHidden(i)
            self.settings.setValue(f"column_{column}_hidden", hidden)

    def load_models_from_file(self):
        """
        Loads model data from the JSON file.
        """
        file_path = r'C:\Code - Copy\FlyAway-pyrq\__PYDATA\models_jason\models_data.json'

        # Check if the file exists
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Warning", f"JSON file not found at {file_path}. Attempting to load from API.")
            self.load_models()
            return None

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Debug: Print the loaded data structure
            print("Data loaded from file:", data)

            # Determine if 'data' key exists
            if isinstance(data, dict):
                models = data.get('data', [])
                if not models:
                    QMessageBox.warning(self, "Warning", f"No models found under 'data' key in the JSON file at {file_path}.")
            elif isinstance(data, list):
                models = data
            else:
                models = []

            if not models:
                QMessageBox.warning(self, "Warning", f"No models found in the JSON file at {file_path}.")
                return None
            else:
                QMessageBox.information(self, "Success", f"Data loaded from {file_path}")
                return models
        except json.JSONDecodeError as jde:
            QMessageBox.warning(self, "JSON Decode Error", f"Failed to parse JSON file: {str(jde)}")
            self.load_models()  # Fallback to loading from API
            return None
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to load data from file: {str(e)}")
            self.load_models()  # Fallback to loading from API
            return None

    def populate_table(self, models):
        """
        Populates the table with model data, including context_length and max_completion_tokens.
        """
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(models))

        for row, model in enumerate(models):
            for col_index, column in enumerate(self.columns):
                if column in ['context_length', 'max_completion_tokens']:
                    top_provider = model.get('top_provider', {})
                    value = top_provider.get(column, 'N/A')
                else:
                    value = model.get(column, 'N/A')

                # Special handling for 'created' field
                if column == 'created':
                    created_timestamp = value
                    if isinstance(created_timestamp, int) or isinstance(created_timestamp, float):
                        try:
                            created_dt = datetime.fromtimestamp(created_timestamp)
                            value = created_dt.strftime('%Y-%m-%d %H:%M:%S')
                        except Exception:
                            value = 'Invalid Timestamp'
                    else:
                        value = 'N/A'

                # Special handling for 'pricing' field
                elif column == 'pricing':
                    pricing_dict = value  # Should be a dict
                    if isinstance(pricing_dict, dict):
                        value = self.format_pricing(pricing_dict)
                    else:
                        value = 'N/A'

                # Format context_length
                elif column == 'context_length':
                    try:
                        int_value = int(value)
                        value = f"{int_value // 1000}K"
                    except (ValueError, TypeError):
                        value = 'N/A'

                elif isinstance(value, dict) or isinstance(value, list):
                    value = json.dumps(value, indent=2)  # Pretty-print for readability

                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row, col_index, item)

        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

    def load_models(self):
        """
        Fetches the model list from the API and populates the table.
        """
        url = 'https://openrouter.ai/api/v1/models'
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                request_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                data['request_time'] = request_time

                # Save to JSON file
                file_path = r'C:\Code - Copy\FlyAway-pyrq\__PYDATA\models_jason\models_data.json'
                os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Ensure the directory exists
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=4)

                # Determine if 'data' key exists
                if isinstance(data, dict):
                    models = data.get('data', [])
                    if not models:
                        QMessageBox.warning(self, "Warning", "No models found under 'data' key in the API response.")
                elif isinstance(data, list):
                    models = data
                else:
                    models = []

                if not models:
                    QMessageBox.warning(self, "Warning", "No models found in the API response.")
                else:
                    self.models = models
                    self.columns = self.get_columns_from_models(self.models)
                    self.initUI()  # Re-initialize UI to update columns
                    self.populate_table(models)
                    QMessageBox.information(self, "Success", f"Data successfully saved to {file_path}")
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to retrieve data. Status code: {response.status_code}"
                )
        except requests.RequestException as re:
            QMessageBox.critical(self, "Request Exception", f"An HTTP error occurred: {str(re)}")
        except json.JSONDecodeError as jde:
            QMessageBox.critical(self, "JSON Decode Error", f"Failed to parse API response: {str(jde)}")
        except Exception as e:
            QMessageBox.critical(self, "Exception", f"An unexpected error occurred: {str(e)}")

    def on_model_double_clicked(self, row, column):
        """
        Emits the model name, ID, context_length, and max_completion_tokens when a row is double-clicked and closes the window.
        """
        model_name = self.table.item(row, self.columns.index("name")).text()
        model_id = self.table.item(row, self.columns.index("id")).text()
        
        # Convert context_length to int, defaulting to 0 if not a valid number
        context_length_str = self.table.item(row, self.columns.index("context_length")).text()
        try:
            # Remove 'K' if present and multiply by 1000
            context_length = int(context_length_str.replace('K', '')) * 1000
        except ValueError:
            context_length = 0

        # Convert max_completion_tokens to int, defaulting to 0 if not a valid number
        max_completion_tokens_str = self.table.item(row, self.columns.index("max_completion_tokens")).text()
        try:
            max_completion_tokens = int(max_completion_tokens_str)
        except ValueError:
            max_completion_tokens = 0
        
        self.model_selected.emit(model_name, model_id, context_length, max_completion_tokens)
        self.close()  # Close the window after emitting the signal

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModelListWindow()
    window.show()
    sys.exit(app.exec_())