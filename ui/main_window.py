# ui/main_window.py
import calendar
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFrame, QGraphicsDropShadowEffect,
                             QHBoxLayout, QLabel, QPushButton, QGridLayout, QApplication,
                             QSystemTrayIcon, QMenu, QStackedWidget)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap, QPainter, QAction

from ui.pomodoro_page import PomodoroPage
from core.data_manager import DataManager
from ui.calendar_items import DayWidget
from ui.detail_panel import DetailPanel


class DesktopCalendar(QWidget):
    def __init__(self):
        super().__init__()

        # 1. 设置应用程序名称 (解决通知栏显示 Python 的问题)
        app = QApplication.instance()
        if app:
            app.setApplicationName("桌面日历")
            app.setApplicationDisplayName("桌面日历")

        self.data_manager = DataManager()
        self.current_date = datetime.now()
        self.year = self.current_date.year
        self.month = self.current_date.month
        self.selected_date_str = self.current_date.strftime("%Y-%m-%d")
        self.drag_active = False
        self.old_pos = None

        self.init_ui()
        self.init_tray()

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

        self.stack = QStackedWidget()
        self.container_layout.addWidget(self.stack)

        # 1. 构建日历页面
        self.calendar_page = QWidget()
        self.setup_calendar_layout(self.calendar_page)
        self.stack.addWidget(self.calendar_page)

        # 2. 构建番茄钟页面
        self.pomodoro_page = PomodoroPage()
        self.pomodoro_page.back_clicked.connect(self.show_calendar)

        # 连接倒计时结束信号 -> 弹出通知
        self.pomodoro_page.timer_finished.connect(self.show_pomodoro_notification)

        self.stack.addWidget(self.pomodoro_page)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 380, 60)

    def show_pomodoro_notification(self):
        """当番茄钟结束时调用"""
        if not self.tray_icon.isVisible():
            self.tray_icon.show()

        self.tray_icon.showMessage(
            "专注完成！🎉",
            "你刚刚完成了一个番茄钟，快起来活动一下吧！",
            QSystemTrayIcon.MessageIcon.Information,
            5000
        )

    def setup_calendar_layout(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.calendar_frame = QFrame()
        self.calendar_frame.setStyleSheet("background: transparent;")
        cal_layout = QVBoxLayout(self.calendar_frame)
        cal_layout.setContentsMargins(15, 15, 15, 5)
        cal_layout.setSpacing(5)

        nav_layout = QHBoxLayout()

        self.btn_pomodoro = QPushButton("🍅")
        self.btn_pomodoro.setFixedSize(24, 24)
        self.btn_pomodoro.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pomodoro.setToolTip("进入专注模式")
        self.btn_pomodoro.setStyleSheet("""
            QPushButton { border: none; font-size: 14px; } 
            QPushButton:hover { background: #eee; border-radius: 12px; }
        """)
        self.btn_pomodoro.clicked.connect(self.show_pomodoro)
        nav_layout.addWidget(self.btn_pomodoro)

        self.prev_btn = self.create_nav_btn("◀", self.prev_month)
        self.next_btn = self.create_nav_btn("▶", self.next_month)
        self.lbl_month = QLabel(f"{self.year}年 {self.month}月")
        self.lbl_month.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        self.lbl_month.setStyleSheet("color: #333; border: none;")

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

        layout.addWidget(self.calendar_frame)

        self.detail_panel = DetailPanel(self.data_manager, self)
        self.detail_panel.data_changed.connect(self.refresh_calendar_styles_only)
        layout.addWidget(self.detail_panel)

        self.detail_panel.setVisible(False)
        self.toggle_btn.setText("﹀")

        self.refresh_calendar()
        self.detail_panel.load_date(self.selected_date_str)

    def show_pomodoro(self):
        self.stack.setCurrentIndex(1)

    def show_calendar(self):
        self.stack.setCurrentIndex(0)

    # === 修复后的 init_tray 方法 (合并了图标修复和菜单显示) ===
    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)

        # 1. 绘制图标
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

        # 2. 设置主窗口图标和托盘图标 (解决通知栏图标问题)
        app_icon = QIcon(pixmap)
        self.setWindowIcon(app_icon)
        self.tray_icon.setIcon(app_icon)
        self.tray_icon.setToolTip("桌面日历")

        # 3. 创建右键菜单 (之前缺失的部分)
        menu = QMenu()
        action_show = QAction("显示日历", self)
        action_show.triggered.connect(self.show_and_activate)
        menu.addAction(action_show)
        menu.addSeparator()
        action_quit = QAction("退出程序", self)
        action_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(action_quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)

        # 4. 关键：显示托盘图标 (之前缺失的部分)
        self.tray_icon.show()

    def show_and_activate(self):
        self.showNormal()
        self.activateWindow()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_and_activate()

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
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
                    day_widget = DayWidget(day, date_str, self.data_manager)
                    day_widget.clicked.connect(self.select_date)
                    day_widget.data_updated.connect(self.refresh_calendar)

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
