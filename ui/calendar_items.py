# uii/calendar_items.py
from datetime import datetime
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QLabel, QWidget, QHBoxLayout, QDialog, QGraphicsDropShadowEffect, QGridLayout, QPushButton)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QCursor

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
        container.setStyleSheet("QFrame { background: white; border-radius: 8px; border: 1px solid #eee; }")
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
                col = 0; row += 1
        layout.addWidget(container)

    def select_mood(self, mood):
        self.selected_mood = mood
        self.accept()


class DayWidget(QFrame):
    """日历格子"""
    # 定义信号：点击时发送日期字符串，数据刷新时发送信号
    clicked = pyqtSignal(str)
    data_updated = pyqtSignal()

    def __init__(self, day, date_str, data_manager):
        super().__init__()
        self.day = day
        self.date_str = date_str
        self.data_manager = data_manager # 持有数据管理器引用
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
        self.update_style(False) # 默认非选中，由外部控制选中态

    def get_heatmap_color(self):
        if self.todo_count == 0: return "transparent"
        elif self.todo_count <= 2: return "rgba(155, 233, 168, 0.5)"
        elif self.todo_count <= 4: return "rgba(64, 196, 99, 0.6)"
        else: return "rgba(33, 110, 57, 0.7)"

    def update_style(self, is_selected):
        is_today = (self.date_str == datetime.now().strftime("%Y-%m-%d"))
        if is_today: self.lbl_dot.show()
        else: self.lbl_dot.hide()

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
        # 发送信号给主窗口，而不是直接调用主窗口的方法
        self.clicked.emit(self.date_str)

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
                self.data_manager.set_day_data(self.date_str, mood=new_mood)
                self.data_updated.emit()
