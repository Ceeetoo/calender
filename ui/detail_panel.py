# uii/detail_panel.py
from datetime import datetime
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEasingCurve, QPropertyAnimation
from PyQt6.QtGui import QFont
from ui.base_widgets import AutoResizingListWidget, ClickToEditTextEdit

class DetailPanel(QFrame):
    data_changed = pyqtSignal()

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.current_date_str = None
        self.is_loading = False

        self.setObjectName("DetailPanel")
        self.setStyleSheet("""
            #DetailPanel { 
                background-color: #fcfcfc; 
                border-top: 1px solid #e0e0e0; 
                border-bottom-left-radius: 16px; 
                border-bottom-right-radius: 16px;
            }
            QLineEdit { 
                border: 1px solid #ddd; 
                border-radius: 4px; 
                padding: 5px; 
                background: white; 
            }
        """)

        self.animation = QPropertyAnimation(self, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.animation.finished.connect(self.on_animation_finished)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 15)
        layout.setSpacing(0)

        lbl_todo = QLabel("待办事项:")
        lbl_todo.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        lbl_todo.setStyleSheet("color: #333; border: none; margin-bottom: 5px;")
        layout.addWidget(lbl_todo)

        self.input_todo = QLineEdit()
        self.input_todo.setPlaceholderText("输入待办，回车添加...")
        self.input_todo.returnPressed.connect(self.add_todo_item)
        layout.addWidget(self.input_todo)

        self.todo_list = AutoResizingListWidget()
        self.todo_list.todo_status_changed.connect(self.on_todo_status_changed)
        self.todo_list.list_changed.connect(self.save_todos_and_notify)
        layout.addWidget(self.todo_list)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #eee; margin-top: 2px; margin-bottom: 2px;")
        layout.addWidget(line)

        lbl_note = QLabel("想法记录")
        lbl_note.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        lbl_note.setStyleSheet("color: #333; border: none; margin-bottom: 2px;")
        layout.addWidget(lbl_note)

        self.note_edit = ClickToEditTextEdit()
        layout.addWidget(self.note_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_publish = QPushButton("发布")
        self.btn_publish.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_publish.setFixedSize(60, 28)
        self.btn_publish.setStyleSheet("""
            QPushButton { background-color: #4a90e2; color: white; border-radius: 4px; border: none; font-weight: bold; font-size: 12px;}
            QPushButton:hover { background-color: #357abd; }
        """)
        self.btn_publish.clicked.connect(self.publish_note)
        btn_layout.addWidget(self.btn_publish)
        layout.addLayout(btn_layout)

    def animate_toggle(self, show):
        if show:
            self.show()
            self.setMaximumHeight(16777215)
            self.todo_list.adjust_height()
            self.note_edit.adjust_height()
            self.layout().activate()
            self.adjustSize()
            target_height = self.sizeHint().height()
            self.setMaximumHeight(0)
            self.animation.setStartValue(0)
            self.animation.setEndValue(target_height)
            self.animation.start()
        else:
            self.animation.setStartValue(self.height())
            self.animation.setEndValue(0)
            self.animation.start()

    def on_animation_finished(self):
        if self.maximumHeight() == 0:
            self.hide()
            self.setMaximumHeight(16777215)
        else:
            self.setMaximumHeight(16777215)

    def save_todos_and_notify(self):
        if self.current_date_str and not self.is_loading:
            todos = self.todo_list.get_todos()
            self.data_manager.set_day_data(self.current_date_str, todos=todos)
            self.data_changed.emit()

    def on_todo_status_changed(self):
        if self.is_loading: return
        todos = self.todo_list.get_todos()
        todos.sort(key=lambda x: x['done'])
        if self.current_date_str:
            self.data_manager.set_day_data(self.current_date_str, todos=todos)
        QTimer.singleShot(300, lambda: self.refresh_todo_list_ui(todos))

    def refresh_todo_list_ui(self, todos):
        self.is_loading = True
        self.todo_list.load_todos(todos)
        self.is_loading = False

    def publish_note(self):
        if not self.current_date_str: return
        note_content = self.note_edit.toPlainText()
        self.data_manager.set_day_data(self.current_date_str, note=note_content)
        self.note_edit.disable_edit_mode()
        original_text = self.btn_publish.text()
        self.btn_publish.setText("已发布")
        self.btn_publish.setStyleSheet("background-color: #67c23a; color: white; border-radius: 4px;")
        QTimer.singleShot(1500, lambda: self.reset_publish_btn(original_text))

    def reset_publish_btn(self, text):
        self.btn_publish.setText(text)
        self.btn_publish.setStyleSheet(
            "QPushButton { background-color: #4a90e2; color: white; border-radius: 4px; } QPushButton:hover { background-color: #357abd; }")

    def load_date(self, date_str):
        self.is_loading = True
        self.current_date_str = date_str
        data = self.data_manager.get_day_data(date_str)
        raw_todos = data.get('todos', [])
        clean_todos = []
        if isinstance(raw_todos, list):
            raw_todos.sort(key=lambda x: x.get('done', False) if isinstance(x, dict) else False)
            for t in raw_todos:
                if isinstance(t, str): t = {'text': t, 'done': False, 'created_at': '', 'completed_at': ''}
                clean_todos.append(t)
        self.todo_list.load_todos(clean_todos)
        self.note_edit.setReadOnly(False)
        note_text = data.get('note', '')
        self.note_edit.setText(note_text)
        self.note_edit.adjust_height()
        self.note_edit.disable_edit_mode()
        self.is_loading = False
        if self.isVisible() and self.maximumHeight() > 0:
            self.updateGeometry()
            if self.parentWidget() and self.parentWidget().layout():
                self.parentWidget().layout().activate()
                self.parentWidget().adjustSize()

    def add_todo_item(self):
        text = self.input_todo.text().strip()
        if text:
            new_task = {"text": text, "done": False, "created_at": datetime.now().strftime("%H:%M"), "completed_at": ""}
            self.todo_list.add_task(new_task)
            self.input_todo.clear()
            self.save_todos_and_notify()
            self.todo_list.adjust_height()
            if self.parent():
                self.parent().adjustSize()
