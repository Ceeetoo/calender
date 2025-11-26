# core/data_manager.py
import json
from PyQt6.QtCore import QObject, pyqtSignal
from config import DATA_FILE

class DataManager(QObject):
    """管理数据的加载和保存，继承 QObject 以支持信号（为未来扩展做准备）"""
    data_changed = pyqtSignal(str)  # 预留：当某天数据改变时发送信号

    def __init__(self):
        super().__init__()
        self.data = {}
        self.load_data()

    def load_data(self):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {}

    def save_data(self):
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存失败: {e}")

    def get_day_data(self, date_str):
        default = {"mood": "", "todos": [], "note": ""}
        return self.data.get(date_str, default)

    def set_day_data(self, date_str, mood=None, todos=None, note=None):
        current = self.get_day_data(date_str)
        if mood is not None: current['mood'] = mood
        if todos is not None: current['todos'] = todos
        if note is not None: current['note'] = note
        self.data[date_str] = current
        self.save_data()
        self.data_changed.emit(date_str)
