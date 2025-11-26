import sys
import json
import calendar
from datetime import datetime

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QGridLayout,
                             QLabel, QPushButton, QTextEdit, QHBoxLayout, QFrame,
                             QGraphicsDropShadowEffect, QListWidget, QListWidgetItem,
                             QLineEdit, QAbstractItemView, QDialog, QSizePolicy,
                             QCheckBox, QSystemTrayIcon, QMenu)  # 新增 QSystemTrayIcon, QMenu
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QCursor, QAction, QIcon, QPixmap, QPainter  # 新增绘图相关类

# 数据文件路径
DATA_FILE = "calendar_data.json"


class DataManager:
    """管理数据的加载和保存"""

    def __init__(self):
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


class MoodSelector(QDialog):
    """双击弹出的心情选择小窗口"""

    def __init__(self, parent=None, current_mood=""):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.selected_mood = current_mood

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        container = QFrame()
        container.setStyleSheet("""
            QFrame { background: white; border-radius: 8px; border: 1px solid #eee; }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 50))
        container.setGraphicsEffect(shadow)

        inner_layout = QGridLayout(container)
        inner_layout.setSpacing(5)

        moods = ["😄", "😐", "🙁", "😡", "😴", "💪", "🎉", "🤔"]

        btn_clear = QPushButton("清除")
        btn_clear.setStyleSheet("border: none; color: #999; font-size: 10px;")
        btn_clear.clicked.connect(lambda: self.select_mood(""))
        inner_layout.addWidget(btn_clear, 0, 0, 1, 4)

        row, col = 1, 0
        for m in moods:
            btn = QPushButton(m)
            btn.setFixedSize(30, 30)
            btn.setFont(QFont("Segoe UI Emoji", 14))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { border: 1px solid #eee; border-radius: 15px; background: white; }
                QPushButton:hover { background: #f0f0f0; border-color: #ccc; }
            """)
            btn.clicked.connect(lambda checked, val=m: self.select_mood(val))
            inner_layout.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        layout.addWidget(container)

    def select_mood(self, mood):
        self.selected_mood = mood
        self.accept()


class DayWidget(QFrame):
    """日历格子"""

    def __init__(self, day, date_str, parent_calendar):
        super().__init__()
        self.day = day
        self.date_str = date_str
        self.parent_calendar = parent_calendar
        self.current_mood = ""
        self.todo_count = 0

        self.click_timer = QTimer()
        self.click_timer.setSingleShot(True)
        self.click_timer.setInterval(250)
        self.click_timer.timeout.connect(self.execute_single_click)

        self.setFixedSize(40, 45)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 2, 0, 2)
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self.lbl_date = QLabel(str(day))
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_date.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        self.lbl_date.setFixedHeight(16)

        self.lbl_emoji = QLabel("")
        self.lbl_emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_emoji.setFont(QFont("Segoe UI Emoji", 10))
        self.lbl_emoji.setFixedHeight(16)

        self.dot_container = QWidget()
        self.dot_container.setFixedHeight(6)
        dot_layout = QHBoxLayout(self.dot_container)
        dot_layout.setContentsMargins(0, 0, 0, 0)
        dot_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_dot = QLabel()
        self.lbl_dot.setFixedSize(4, 4)
        self.lbl_dot.setStyleSheet("background-color: #4a90e2; border-radius: 2px;")
        self.lbl_dot.hide()

        dot_layout.addWidget(self.lbl_dot)

        self.layout.addWidget(self.lbl_date)
        self.layout.addWidget(self.lbl_emoji)
        self.layout.addStretch()
        self.layout.addWidget(self.dot_container)

        self.update_style(False)

    def update_display(self, mood, todo_count=0):
        self.current_mood = mood
        self.todo_count = todo_count

        if not mood:
            self.lbl_emoji.hide()
            self.lbl_date.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        else:
            self.lbl_emoji.show()
            self.lbl_emoji.setText(mood)
            self.lbl_date.setFont(QFont("Microsoft YaHei", 9))

        is_selected = (self.parent_calendar.selected_date_str == self.date_str)
        self.update_style(is_selected)

    def get_heatmap_color(self):
        if self.todo_count == 0:
            return "transparent"
        elif self.todo_count <= 2:
            return "rgba(155, 233, 168, 0.5)"
        elif self.todo_count <= 4:
            return "rgba(64, 196, 99, 0.6)"
        else:
            return "rgba(33, 110, 57, 0.7)"

    def update_style(self, is_selected):
        is_today = (self.date_str == datetime.now().strftime("%Y-%m-%d"))

        if is_today:
            self.lbl_dot.show()
        else:
            self.lbl_dot.hide()

        style = "DayWidget { border-radius: 10px; margin: 2px; "
        heatmap_bg = self.get_heatmap_color()

        if is_selected:
            style += f"border: 1.5px solid #4a90e2; background-color: {heatmap_bg if self.todo_count > 0 else 'rgba(74, 144, 226, 0.1)'}; }}"
            date_color = "#4a90e2"
        else:
            style += f"border: 1.5px solid transparent; background-color: {heatmap_bg}; }}"
            date_color = "#333"

        self.setStyleSheet(style)
        self.lbl_date.setStyleSheet(f"background: transparent; color: {date_color};")

    def execute_single_click(self):
        self.parent_calendar.select_date(self.date_str)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.click_timer.start()

    def mouseDoubleClickEvent(self, event):
        self.click_timer.stop()
        if event.button() == Qt.MouseButton.LeftButton:
            dialog = MoodSelector(self.window(), self.current_mood)
            dialog.move(QCursor.pos().x() - 60, QCursor.pos().y() - 60)
            if dialog.exec():
                new_mood = dialog.selected_mood
                self.parent_calendar.data_manager.set_day_data(self.date_str, mood=new_mood)
                self.parent_calendar.refresh_calendar()


class TodoItemWidget(QWidget):
    def __init__(self, text, is_done, status_callback, delete_callback):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 8, 0, 8)
        layout.setSpacing(10)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(is_done)
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.setStyleSheet("QCheckBox::indicator { width: 18px; height: 18px; }")
        self.checkbox.stateChanged.connect(status_callback)
        layout.addWidget(self.checkbox)

        self.lbl_text = QLabel(text)
        self.lbl_text.setStyleSheet("background: transparent; border: none; font-size: 14px;")
        layout.addWidget(self.lbl_text)

        layout.addStretch()

        self.btn_delete = QPushButton("删除")
        self.btn_delete.setFixedSize(44, 24)
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setStyleSheet("""
            QPushButton { background-color: #ff4d4f; color: white; border-radius: 4px; font-size: 12px; border: none; }
            QPushButton:hover { background-color: #ff7875; }
        """)
        self.btn_delete.clicked.connect(delete_callback)
        self.btn_delete.hide()
        layout.addWidget(self.btn_delete)

        self.update_style(is_done)

    def update_data(self, text, is_done):
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(is_done)
        self.checkbox.blockSignals(False)
        self.update_text(text)
        self.update_style(is_done)

    def update_style(self, is_done):
        font = self.lbl_text.font()
        if is_done:
            font.setStrikeOut(True)
            self.lbl_text.setStyleSheet("color: #999999; background: transparent; font-size: 14px;")
        else:
            font.setStrikeOut(False)
            self.lbl_text.setStyleSheet("color: #333333; background: transparent; font-size: 14px;")
        self.lbl_text.setFont(font)
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(is_done)
        self.checkbox.blockSignals(False)

    def update_text(self, text):
        self.lbl_text.setText(text)

    def enterEvent(self, event):
        self.btn_delete.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.btn_delete.hide()
        super().leaveEvent(event)


class AutoResizingListWidget(QListWidget):
    list_changed = pyqtSignal()
    todo_status_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setStyleSheet("""
            QListWidget { border: none; background: transparent; }
            QListWidget::item { border: none; } 
            QListWidget::item:hover { background: #f9f9f9; }
        """)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def add_task(self, data):
        self.blockSignals(True)
        item = QListWidgetItem()
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setData(Qt.ItemDataRole.UserRole, data)
        self.addItem(item)

        is_done = data.get('done', False)
        display_text = self.format_text(data)

        widget = TodoItemWidget(
            text=display_text,
            is_done=is_done,
            status_callback=lambda state: self.toggle_task_status(item, state),
            delete_callback=lambda: self.delete_task(item)
        )

        self.setItemWidget(item, widget)
        item.setSizeHint(widget.sizeHint())
        self.blockSignals(False)
        self.adjust_height()

    def toggle_task_status(self, item, state):
        data = item.data(Qt.ItemDataRole.UserRole)
        is_checked = (state == Qt.CheckState.Checked.value or state == 2)

        data['done'] = is_checked
        data['completed_at'] = datetime.now().strftime("%H:%M") if is_checked else ""
        item.setData(Qt.ItemDataRole.UserRole, data)

        widget = self.itemWidget(item)
        if widget:
            new_text = self.format_text(data)
            widget.update_text(new_text)
            widget.update_style(is_checked)

        self.todo_status_changed.emit()

    def delete_task(self, item):
        row = self.row(item)
        self.takeItem(row)
        self.adjust_height()
        self.list_changed.emit()

    def format_text(self, data):
        text = data.get('text', '')
        created = data.get('created_at', '')
        completed = data.get('completed_at', '')
        is_done = data.get('done', False)
        if is_done and completed:
            return f"[{created} → {completed}] {text}"
        elif created:
            return f"[{created}] {text}"
        else:
            return text

    def get_todos(self):
        todos = []
        for i in range(self.count()):
            item = self.item(i)
            todos.append(item.data(Qt.ItemDataRole.UserRole))
        return todos

    def adjust_height(self):
        count = self.count()
        if count == 0:
            self.setFixedHeight(0)
            self.setVisible(False)
        else:
            row_height = 46
            total_height = count * row_height + 2
            self.setFixedHeight(total_height)
            self.setVisible(True)

        self.updateGeometry()
        if self.parentWidget() and self.parentWidget().layout():
            self.parentWidget().layout().activate()

    def load_todos(self, todos):
        self.blockSignals(True)
        current_count = self.count()
        new_count = len(todos)

        for i in range(min(current_count, new_count)):
            item = self.item(i)
            data = todos[i]
            item.setData(Qt.ItemDataRole.UserRole, data)
            widget = self.itemWidget(item)
            if widget:
                display_text = self.format_text(data)
                widget.update_data(display_text, data.get('done', False))

        if new_count > current_count:
            for i in range(current_count, new_count):
                self.add_task(todos[i])

        if current_count > new_count:
            for i in range(current_count - 1, new_count - 1, -1):
                self.takeItem(i)

        self.blockSignals(False)
        self.adjust_height()


class ClickToEditTextEdit(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setPlaceholderText("点击此处开始记录...")
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(35)
        self.textChanged.connect(self.adjust_height)
        self.disable_edit_mode()

    def adjust_height(self):
        doc_height = self.document().size().height()
        new_height = int(doc_height + 10)
        if new_height < 35: new_height = 35
        if new_height > 150: new_height = 150
        if new_height != self.height():
            self.setFixedHeight(new_height)

    def enable_edit_mode(self):
        self.setReadOnly(False)
        self.setStyleSheet(
            "QTextEdit { border: 1px solid #4a90e2; border-radius: 4px; padding: 5px; background: white; color: #333; }")
        self.setFocus()
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.setTextCursor(cursor)

    def disable_edit_mode(self):
        self.setReadOnly(True)
        self.setStyleSheet(
            "QTextEdit { border: 1px solid transparent; border-radius: 4px; padding: 5px; background: transparent; color: #555; }")
        self.clearFocus()
        self.repaint()

    def mousePressEvent(self, event):
        if self.isReadOnly():
            self.enable_edit_mode()
        super().mousePressEvent(event)


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
                if isinstance(t, str):
                    t = {'text': t, 'done': False, 'created_at': '', 'completed_at': ''}
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


class DesktopCalendar(QWidget):
    def __init__(self):
        super().__init__()
        self.data_manager = DataManager()
        self.current_date = datetime.now()
        self.year = self.current_date.year
        self.month = self.current_date.month
        self.selected_date_str = self.current_date.strftime("%Y-%m-%d")
        self.drag_active = False
        self.old_pos = None

        self.init_ui()
        self.init_tray()  # 初始化托盘

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        self.setLayout(self.main_layout)

        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet(
            "#MainContainer { background-color: rgba(255, 255, 255, 0.98); border-radius: 16px; }")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 0)
        self.container.setGraphicsEffect(shadow)

        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        self.main_layout.addWidget(self.container)

        self.calendar_frame = QFrame()
        self.calendar_frame.setStyleSheet("background: transparent;")
        cal_layout = QVBoxLayout(self.calendar_frame)
        cal_layout.setContentsMargins(15, 15, 15, 5)
        cal_layout.setSpacing(5)

        nav_layout = QHBoxLayout()
        self.prev_btn = self.create_nav_btn("◀", self.prev_month)
        self.next_btn = self.create_nav_btn("▶", self.next_month)
        self.lbl_month = QLabel(f"{self.year}年 {self.month}月")
        self.lbl_month.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        self.lbl_month.setStyleSheet("color: #333; border: none;")

        # 注意：这里的关闭按钮现在会触发 closeEvent，从而隐藏窗口到托盘
        close_btn = self.create_nav_btn("×", self.close)
        close_btn.setStyleSheet(
            "QPushButton { color: #999; font-size: 18px; border:none; } QPushButton:hover { color: red; }")

        nav_layout.addWidget(self.prev_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.lbl_month)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_btn)
        nav_layout.addWidget(close_btn)
        cal_layout.addLayout(nav_layout)

        week_layout = QGridLayout()
        week_days = ["一", "二", "三", "四", "五", "六", "日"]
        for i, day in enumerate(week_days):
            lbl = QLabel(day)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #999; font-size: 11px; border: none;")
            week_layout.addWidget(lbl, 0, i)
        cal_layout.addLayout(week_layout)

        self.calendar_grid = QGridLayout()
        self.calendar_grid.setSpacing(4)
        cal_layout.addLayout(self.calendar_grid)

        self.toggle_btn = QPushButton("﹀")
        self.toggle_btn.setFixedHeight(20)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setStyleSheet(
            "QPushButton { border: none; color: #ccc; background: transparent; font-weight: bold; font-size: 14px;} QPushButton:hover { color: #4a90e2; background: rgba(0,0,0,0.02); border-radius: 4px;}")
        self.toggle_btn.clicked.connect(self.toggle_panel)
        cal_layout.addWidget(self.toggle_btn)

        self.container_layout.addWidget(self.calendar_frame)
        self.detail_panel = DetailPanel(self.data_manager, self)
        self.detail_panel.data_changed.connect(self.refresh_calendar_styles_only)
        self.container_layout.addWidget(self.detail_panel)

        self.detail_panel.setVisible(False)
        self.toggle_btn.setText("﹀")

        self.refresh_calendar()
        self.detail_panel.load_date(self.selected_date_str)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 380, 60)

    # === 新增：初始化托盘图标 ===
    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)

        # 1. 创建一个简单的程序图标 (蓝色方块，中间有个C)
        # 如果你有图片文件，可以使用: icon = QIcon("your_icon.png")
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#4a90e2"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 32, 32, 8, 8)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "C")
        painter.end()

        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("桌面日历")

        # 2. 创建右键菜单
        menu = QMenu()

        action_show = QAction("显示日历", self)
        action_show.triggered.connect(self.show_and_activate)
        menu.addAction(action_show)

        menu.addSeparator()

        action_quit = QAction("退出程序", self)
        # 注意：这里调用 QApplication.quit() 才是真正的退出
        action_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(action_quit)

        self.tray_icon.setContextMenu(menu)

        # 3. 处理托盘点击事件 (左键点击显示/隐藏)
        self.tray_icon.activated.connect(self.on_tray_activated)

        self.tray_icon.show()

    def show_and_activate(self):
        self.showNormal()
        self.activateWindow()

    def on_tray_activated(self, reason):
        # 如果是单击 (Trigger)
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_and_activate()

    # === 修改：关闭事件 ===
    def closeEvent(self, event):
        # 拦截关闭事件，改为隐藏窗口
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()  # 忽略关闭信号，保持程序运行
        else:
            event.accept()

    def create_nav_btn(self, text, func):
        btn = QPushButton(text)
        btn.setFixedSize(24, 24)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { border: none; color: #666; font-weight: bold; } QPushButton:hover { color: #333; background: #eee; border-radius: 12px;}")
        btn.clicked.connect(func)
        return btn

    def refresh_calendar(self):
        for i in reversed(range(self.calendar_grid.count())):
            self.calendar_grid.itemAt(i).widget().setParent(None)

        self.lbl_month.setText(f"{self.year}年 {self.month}月")
        month_matrix = calendar.monthcalendar(self.year, self.month)

        row = 0
        for week in month_matrix:
            col = 0
            for day in week:
                if day != 0:
                    date_str = f"{self.year}-{self.month:02d}-{day:02d}"
                    day_widget = DayWidget(day, date_str, self)
                    data = self.data_manager.get_day_data(date_str)
                    todo_count = len(data.get('todos', []))
                    day_widget.update_display(data.get('mood', ''), todo_count)
                    self.calendar_grid.addWidget(day_widget, row, col)
                col += 1
            row += 1

    def refresh_calendar_styles_only(self):
        for i in range(self.calendar_grid.count()):
            item = self.calendar_grid.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, DayWidget):
                    data = self.data_manager.get_day_data(widget.date_str)
                    todo_count = len(data.get('todos', []))
                    widget.todo_count = todo_count
                    is_selected = (widget.date_str == self.selected_date_str)
                    widget.update_style(is_selected)

    def select_date(self, date_str):
        previous_date = self.selected_date_str
        self.selected_date_str = date_str

        for i in range(self.calendar_grid.count()):
            item = self.calendar_grid.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, DayWidget):
                    is_selected = (widget.date_str == date_str)
                    widget.update_style(is_selected)

        if date_str == previous_date:
            self.toggle_panel()
            if self.detail_panel.isVisible():
                self.detail_panel.load_date(date_str)
        else:
            self.detail_panel.load_date(date_str)
            if not self.detail_panel.isVisible() or self.detail_panel.maximumHeight() == 0:
                self.toggle_panel()

    def toggle_panel(self):
        is_visible = self.detail_panel.isVisible() and self.detail_panel.maximumHeight() > 0
        self.detail_panel.animate_toggle(not is_visible)
        self.toggle_btn.setText("﹀" if is_visible else "︿")

    def prev_month(self):
        self.month -= 1
        if self.month == 0:
            self.month = 12
            self.year -= 1
        self.refresh_calendar()

    def next_month(self):
        self.month += 1
        if self.month == 13:
            self.month = 1
            self.year += 1
        self.refresh_calendar()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.pos().y() < 50:
                self.drag_active = True
                self.old_pos = event.globalPosition().toPoint()
            else:
                self.drag_active = False

    def mouseMoveEvent(self, event):
        if self.drag_active and event.buttons() == Qt.MouseButton.LeftButton:
            delta = QPoint(event.globalPosition().toPoint() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.drag_active = False


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # === 关键设置：关闭最后一个窗口时不退出程序 ===
    app.setQuitOnLastWindowClosed(False)

    app.setFont(QFont("Microsoft YaHei", 9))
    window = DesktopCalendar()
    window.show()
    sys.exit(app.exec())
