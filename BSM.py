import os
import shutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLabel, QWidget, QComboBox, QCheckBox, QMessageBox
)

def get_blender_path():
    if os.name == 'posix':
        config_path = os.path.expanduser('~/.config')
        return os.path.join(config_path, "blender")
    else:
        appdata_path = os.getenv('APPDATA')
        return os.path.join(appdata_path, "Blender Foundation", "Blender")

class BlenderManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Управление версиями Blender")
        self.resize(600, 400)

        self.blender_versions = {}
        self.ignore_files_dict = {"Последние пути": "bookmarks.txt, recent-files.txt, recent-searches.txt", "Аддоны": "addons", "Пресеты": "presets", "Стартовый файл": "startup.blend", "Настройки": "userpref.blend"}

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.version_list = QListWidget()
        main_layout.addWidget(QLabel("Найденные версии Blender:"))
        main_layout.addWidget(self.version_list)

        version_select_layout = QHBoxLayout()
        version_select_layout.addWidget(QLabel("Перенести из:"))
        self.source_version = QComboBox()
        self.source_version.currentTextChanged.connect(self.update_target_versions)
        version_select_layout.addWidget(self.source_version)

        version_select_layout.addWidget(QLabel("в:"))
        self.target_version = QComboBox()
        version_select_layout.addWidget(self.target_version)

        self.sync_new_files_checkbox = QCheckBox("Синхронизировать только новые файлы")
        version_select_layout.addWidget(self.sync_new_files_checkbox)

        main_layout.addLayout(version_select_layout)

        button_layout = QHBoxLayout()
        execute_button = QPushButton("Выполнить")
        execute_button.clicked.connect(self.execute_action)
        refresh_button = QPushButton("Обновить")
        refresh_button.clicked.connect(self.refresh_versions)
        button_layout.addWidget(execute_button)
        button_layout.addWidget(refresh_button)
        main_layout.addLayout(button_layout)

        ignore_layout = QVBoxLayout()
        ignore_layout.addWidget(QLabel("Выберите файлы для игнорирования:"))

        self.ignore_checkboxes = {}
        for category, value in self.ignore_files_dict.items():
            checkbox = QCheckBox(category)
            ignore_layout.addWidget(checkbox)
            self.ignore_checkboxes[checkbox] = value.split(", ")

        main_layout.addLayout(ignore_layout)
        self.refresh_versions()

    def refresh_versions(self):
        self.version_list.clear()
        self.source_version.clear()
        self.target_version.clear()

        blender_path = get_blender_path()
        self.blender_versions = {}

        if os.path.exists(blender_path):
            for version in os.listdir(blender_path):
                version_path = os.path.join(blender_path, version)
                if os.path.isdir(version_path) and version != "matlib":
                    self.blender_versions[version] = version_path

        sorted_versions = sorted(self.blender_versions.keys(), reverse=True)

        for version in sorted_versions:
            self.version_list.addItem(f"{version} — {self.blender_versions[version]}")
            self.source_version.addItem(version)

        self.target_version.addItem("всё")
        self.update_target_versions()

        if sorted_versions:
            self.source_version.setCurrentText(sorted_versions[0])

    def update_target_versions(self):
        current_source = self.source_version.currentText()
        self.target_version.clear()
        for version in self.blender_versions.keys():
            if version != current_source:
                self.target_version.addItem(version)

        self.target_version.addItem("всё")

    def execute_action(self):
        source = self.source_version.currentText()
        target = self.target_version.currentText()
        sync_only_new = self.sync_new_files_checkbox.isChecked()

        ignored_files = [
            item for checkbox, files in self.ignore_checkboxes.items() for item in files if checkbox.isChecked()
        ]

        if target == "всё":
            self.sync_one_to_all(source, ignored_files, sync_only_new)
        else:
            self.move_settings(source, target, ignored_files, sync_only_new)

    def move_settings(self, source, target, ignored_files, sync_only_new):
        source_path = self.blender_versions.get(source)
        target_path = self.blender_versions.get(target)

        if not source_path or not target_path:
            QMessageBox.critical(self, "Ошибка", "Выберите корректные версии для перемещения.")
            return

        if self.check_incompatibility(source, target):
            response = self.show_incompatibility_warning(source, target)
            if not response:
                return

        for root, dirs, files in os.walk(source_path):
            for name in files:
                if name in ignored_files or (sync_only_new and self.is_newer(os.path.join(root, name), target_path)):
                    continue
                relative_path = os.path.relpath(root, source_path)
                target_dir = os.path.join(target_path, relative_path)
                os.makedirs(target_dir, exist_ok=True)
                shutil.copy2(os.path.join(root, name), os.path.join(target_dir, name))

        QMessageBox.information(self, "Готово", "Настройки успешно перемещены.")

    def sync_one_to_all(self, source, ignored_files, sync_only_new):
        source_path = self.blender_versions.get(source)

        if not source_path:
            QMessageBox.critical(self, "Ошибка", "Выберите корректную исходную версию.")
            return

        for target, target_path in self.blender_versions.items():
            if target == source:
                continue

            if self.check_incompatibility(source, target):
                response = self.show_incompatibility_warning(source, target)
                if not response:
                    continue

            for root, dirs, files in os.walk(source_path):
                for name in files:
                    if name in ignored_files or (sync_only_new and self.is_newer(os.path.join(root, name), target_path)):
                        continue
                    relative_path = os.path.relpath(root, source_path)
                    target_dir = os.path.join(target_path, relative_path)
                    os.makedirs(target_dir, exist_ok=True)
                    shutil.copy2(os.path.join(root, name), os.path.join(target_dir, name))

        QMessageBox.information(self, "Готово", "Синхронизация завершена.")

    @staticmethod
    def is_newer(source_file, target_dir):
        target_file = os.path.join(target_dir, os.path.basename(source_file))
        return not os.path.exists(target_file) or os.path.getmtime(source_file) > os.path.getmtime(target_file)

    @staticmethod
    def check_incompatibility(source, target):
        source_major, source_minor = map(int, source.split('.')[:2])
        target_major, target_minor = map(int, target.split('.')[:2])

        # Правила несовместимости
        if source_major == 4 and source_minor >= 3 and target_major == 4 and target_minor <= 0:
            return True
        if source_major == 3 and source_minor >= 4 and target_major == 3 and target_minor <= 3:
            return True

        return False

    def show_incompatibility_warning(self, source, target):
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Warning)
        message_box.setWindowTitle("Предупреждение о несовместимости")
        message_box.setText(f"Файлы настроек из версии {source} могут быть несовместимы с версией {target}.\n\n"
                             f"Вы хотите продолжить?")
        message_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        response = message_box.exec()
        return response == QMessageBox.StandardButton.Yes

if __name__ == "__main__":
    app = QApplication([])
    window = BlenderManager()
    window.show()
    app.exec()
