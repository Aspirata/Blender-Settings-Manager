import os
import shutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLabel, QWidget, QComboBox, QCheckBox, QMessageBox
)

# Определение пути до каталога Blender
def get_blender_path():
    if os.name == 'posix':  # Linux systems
        config_path = os.path.expanduser('~/.config')
        return os.path.join(config_path, "blender")
    else:
        appdata_path = os.getenv('APPDATA')  # Путь до AppData\Roaming
        return os.path.join(appdata_path, "Blender Foundation", "Blender")
# Класс главного окна
class BlenderManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Управление версиями Blender")
        self.resize(800, 600)

        self.blender_versions = {}  # Словарь для хранения найденных версий

        # Данные для игнорируемых файлов
        self.ignore_files_dict = {
            "Последние пути": "bookmarks.txt, recent-files.txt",
        }

        # Основной виджет и макет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Список версий Blender
        self.version_list = QListWidget()
        main_layout.addWidget(QLabel("Найденные версии Blender:"))
        main_layout.addWidget(self.version_list)

        # Поля выбора версий
        version_select_layout = QVBoxLayout()

        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Перенести из:"))
        self.source_version = QComboBox()
        self.source_version.currentTextChanged.connect(self.update_target_versions)
        source_layout.addWidget(self.source_version)

        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("в:"))
        self.target_version = QComboBox()
        target_layout.addWidget(self.target_version)

        version_select_layout.addLayout(source_layout)
        version_select_layout.addLayout(target_layout)
        main_layout.addLayout(version_select_layout)

        # Галочка "Синхронизировать только новые файлы"
        self.sync_new_files_checkbox = QCheckBox("Синхронизировать только новые файлы")
        main_layout.addWidget(self.sync_new_files_checkbox)

        # Кнопки
        button_layout = QHBoxLayout()
        execute_button = QPushButton("Выполнить")
        execute_button.clicked.connect(self.execute_action)
        refresh_button = QPushButton("Обновить")
        refresh_button.clicked.connect(self.refresh_versions)
        button_layout.addWidget(execute_button)
        button_layout.addWidget(refresh_button)
        main_layout.addLayout(button_layout)

        # Раздел для игнорируемых файлов
        ignore_layout = QVBoxLayout()
        ignore_layout.addWidget(QLabel("Выберите файлы для игнорирования:"))

        # Добавление динамических флажков для игнорируемых файлов
        self.ignore_checkboxes = {}  # Словарь для хранения состояний флажков
        for category, value in self.ignore_files_dict.items():
            checkbox = QCheckBox(category)
            ignore_layout.addWidget(checkbox)
            self.ignore_checkboxes[checkbox] = value.split(", ")

        main_layout.addLayout(ignore_layout)

        # Загрузка версий Blender
        self.refresh_versions()

    def refresh_versions(self):
        """Обновление списка версий Blender."""
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

        # Добавляем опцию "всё" для целевой версии
        self.target_version.addItem("всё")
        self.update_target_versions()

        # Установка значений по умолчанию
        if sorted_versions:
            self.source_version.setCurrentText(sorted_versions[0])  # Самая новая версия

    def update_target_versions(self):
        """Обновление списка целевых версий на основе выбранной исходной."""
        current_source = self.source_version.currentText()
        self.target_version.clear()
        for version in self.blender_versions.keys():
            if version != current_source:
                self.target_version.addItem(version)

        self.target_version.addItem("всё")

    def execute_action(self):
        """Выполнение выбранного действия."""
        source = self.source_version.currentText()
        target = self.target_version.currentText()
        sync_only_new = self.sync_new_files_checkbox.isChecked()

        # Составим список игнорируемых файлов и папок
        ignored_files = [
            item for checkbox, files in self.ignore_checkboxes.items() for item in files if checkbox.isChecked()
        ]

        if target == "всё":
            self.sync_one_to_all(source, ignored_files, sync_only_new)
        else:
            self.move_settings(source, target, ignored_files, sync_only_new)

    def move_settings(self, source, target, ignored_files, sync_only_new):
        """Перемещение настроек с одной версии на другую."""
        source_path = self.blender_versions.get(source)
        target_path = self.blender_versions.get(target)

        if not source_path or not target_path:
            QMessageBox.critical(self, "Ошибка", "Выберите корректные версии для перемещения.")
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
        """Синхронизация одной версии с другими."""
        source_path = self.blender_versions.get(source)

        if not source_path:
            QMessageBox.critical(self, "Ошибка", "Выберите корректную исходную версию.")
            return

        for target, target_path in self.blender_versions.items():
            if target == source:
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
        """Проверяет, является ли файл новым."""
        target_file = os.path.join(target_dir, os.path.basename(source_file))
        return not os.path.exists(target_file) or os.path.getmtime(source_file) > os.path.getmtime(target_file)

if __name__ == "__main__":
    app = QApplication([])
    window = BlenderManager()
    window.show()
    app.exec()
