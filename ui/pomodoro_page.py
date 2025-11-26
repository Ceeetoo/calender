# ui/pomodoro_page.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
                             QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QFont, QColor, QCursor


class DraggableNumber(QLabel):
    """
    自定义数字组件：
    1. 支持滚轮滚动修改数值
    2. 支持鼠标上下拖拽修改数值
    3. 带有圆角背景
    """
    valueChanged = pyqtSignal(int)

    def __init__(self, initial_value, max_value, min_value=0, is_minute=True):
        super().__init__()
        self.value = initial_value
        self.max_value = max_value
        self.min_value = min_value
        self.is_minute = is_minute
        self.last_y = 0
        self.is_dragging = False

        # UI 初始化
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(100, 120)  # 数字框的大小
        self.setFont(QFont("Segoe UI", 48, QFont.Weight.Bold))  # 现代字体
        self.setCursor(Qt.CursorShape.SizeVerCursor)  # 鼠标放上去显示上下箭头

        # 样式：深色背景，圆角，白色文字
        self.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d; 
                color: #ffffff;
                border-radius: 16px;
            }
            QLabel:hover {
                background-color: #3d3d3d;
            }
        """)

        self.update_text()

    def update_text(self):
        self.setText(f"{self.value:02d}")

    def set_value(self, val):
        self.value = max(self.min_value, min(val, self.max_value))
        self.update_text()
        self.valueChanged.emit(self.value)

    # === 滚轮事件 ===
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        step = 1 if delta > 0 else -1
        new_val = self.value + step
        if not self.is_minute:
            if new_val > 59: new_val = 0
            if new_val < 0: new_val = 59
            self.set_value(new_val)
        else:
            self.set_value(new_val)

    # === 拖拽事件 ===
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.last_y = event.globalPosition().y()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            current_y = event.globalPosition().y()
            delta = self.last_y - current_y  # 向上拖动是增加

            if abs(delta) > 10:
                step = 1 if delta > 0 else -1
                new_val = self.value + step

                if not self.is_minute:
                    if new_val > 59: new_val = 0
                    if new_val < 0: new_val = 59
                    self.set_value(new_val)
                else:
                    self.set_value(new_val)

                self.last_y = current_y

    def mouseReleaseEvent(self, event):
        self.is_dragging = False


class PomodoroPage(QWidget):
    back_clicked = pyqtSignal()
    timer_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        # [修改 1] 默认时间改为 0
        self.default_minutes = 0
        self.current_seconds = self.default_minutes * 60
        self.is_running = False
        self.is_paused = False

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_timer)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 30)
        layout.setSpacing(20)

        # --- 1. 顶部导航 ---
        nav_layout = QHBoxLayout()
        self.btn_back = QPushButton("◀ 返回")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setStyleSheet("""
            QPushButton { border: none; color: #999; font-weight: bold; font-size: 14px; }
            QPushButton:hover { color: #333; }
        """)
        self.btn_back.clicked.connect(self.stop_and_back)
        nav_layout.addWidget(self.btn_back)
        nav_layout.addStretch()
        layout.addLayout(nav_layout)

        # --- 2. 状态提示 ---
        layout.addStretch()
        self.lbl_status = QLabel("准备专注")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("color: #4a90e2; letter-spacing: 2px;")
        layout.addWidget(self.lbl_status)

        # --- 3. 时间显示区域 ---
        time_container = QWidget()
        time_layout = QHBoxLayout(time_container)
        time_layout.setContentsMargins(0, 10, 0, 10)
        time_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_layout.setSpacing(10)

        # [修改 2] 初始化分钟组件时，默认值改为 0
        self.dial_min = DraggableNumber(0, 99, is_minute=True)
        self.dial_min.valueChanged.connect(self.on_time_dial_changed)

        lbl_colon = QLabel(":")
        lbl_colon.setFont(QFont("Segoe UI", 40, QFont.Weight.Bold))
        lbl_colon.setStyleSheet("color: #333; margin-bottom: 10px;")

        self.dial_sec = DraggableNumber(0, 59, is_minute=False)
        self.dial_sec.valueChanged.connect(self.on_time_dial_changed)

        time_layout.addWidget(self.dial_min)
        time_layout.addWidget(lbl_colon)
        time_layout.addWidget(self.dial_sec)
        layout.addWidget(time_container)

        lbl_hint = QLabel("滚动或拖动数字调整时间")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hint.setStyleSheet("color: #ccc; font-size: 10px;")
        layout.addWidget(lbl_hint)

        layout.addStretch()

        # --- 4. 底部控制按钮组 ---
        btn_container = QHBoxLayout()
        btn_container.setSpacing(15)
        btn_container.setContentsMargins(10, 0, 10, 0)

        # [重置按钮]
        self.btn_reset = QPushButton("重置")
        self.btn_reset.setFixedSize(100, 50)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.clicked.connect(self.reset_timer)
        self.btn_reset.setStyleSheet("""
            QPushButton { 
                background-color: #f0f0f0; 
                color: #666; 
                border-radius: 25px; 
                font-weight: bold; 
                font-size: 15px;
                font-family: "Microsoft YaHei";
                border: 1px solid #e0e0e0;
            }
            QPushButton:hover { background-color: #e0e0e0; color: #333; }
            QPushButton:pressed { background-color: #d0d0d0; }
        """)

        # [开始/暂停按钮]
        self.btn_start = QPushButton("开始专注")
        self.btn_start.setFixedSize(160, 50)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.toggle_timer)

        shadow = QGraphicsDropShadowEffect(self.btn_start)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(74, 144, 226, 80))
        shadow.setOffset(0, 5)
        self.btn_start.setGraphicsEffect(shadow)

        self.update_start_btn_style("start")

        btn_container.addStretch()
        btn_container.addWidget(self.btn_reset)
        btn_container.addWidget(self.btn_start)
        btn_container.addStretch()

        layout.addLayout(btn_container)
        layout.addStretch()

    # === 样式辅助方法 ===
    def update_start_btn_style(self, state):
        if state == "start":
            self.btn_start.setText("开始专注")
            self.btn_start.setStyleSheet("""
                QPushButton { background-color: #4a90e2; color: white; border-radius: 25px; font-weight: bold; font-size: 16px; font-family: "Microsoft YaHei";}
                QPushButton:hover { background-color: #357abd; }
            """)
        elif state == "pause":
            self.btn_start.setText("暂停")
            self.btn_start.setStyleSheet("""
                QPushButton { background-color: #f5a623; color: white; border-radius: 25px; font-weight: bold; font-size: 16px; font-family: "Microsoft YaHei";}
                QPushButton:hover { background-color: #d48e1b; }
            """)
        elif state == "continue":
            self.btn_start.setText("继续专注")
            self.btn_start.setStyleSheet("""
                QPushButton { background-color: #4a90e2; color: white; border-radius: 25px; font-weight: bold; font-size: 16px; font-family: "Microsoft YaHei";}
                QPushButton:hover { background-color: #357abd; }
            """)

    # === 逻辑处理 ===

    def on_time_dial_changed(self):
        if not self.is_running and not self.is_paused:
            m = self.dial_min.value
            s = self.dial_sec.value
            self.current_seconds = m * 60 + s
            self.default_minutes = m
            self.lbl_status.setText("设定时间")

    def toggle_timer(self):
        # [保护逻辑] 如果时间是 0，点击开始不应该有反应，或者提示用户设置时间
        if self.current_seconds == 0 and not self.is_running:
            self.lbl_status.setText("请先设置时间")
            return

        if self.is_running:
            self.timer.stop()
            self.is_running = False
            self.is_paused = True
            self.update_start_btn_style("continue")
            self.lbl_status.setText("已暂停")
            self.dial_min.setEnabled(True)
            self.dial_sec.setEnabled(True)
        else:
            if not self.is_paused:
                m = self.dial_min.value
                s = self.dial_sec.value
                self.current_seconds = m * 60 + s

            self.timer.start()
            self.is_running = True
            self.is_paused = False
            self.update_start_btn_style("pause")
            self.lbl_status.setText("正在专注...")
            self.dial_min.setEnabled(False)
            self.dial_sec.setEnabled(False)

    def reset_timer(self):
        self.timer.stop()
        self.is_running = False
        self.is_paused = False

        # 重置回 0 (因为 default_minutes 现在是 0)
        self.default_minutes = 0
        self.current_seconds = 0

        self.update_display_from_timer()
        self.update_start_btn_style("start")
        self.lbl_status.setText("准备专注")

        self.dial_min.setEnabled(True)
        self.dial_sec.setEnabled(True)

    def update_timer(self):
        if self.current_seconds > 0:
            self.current_seconds -= 1
            self.update_display_from_timer()
        else:
            self.timer.stop()
            self.is_running = False
            self.is_paused = False

            self.lbl_status.setText("🎉 专注完成！")
            self.btn_start.setText("再来一次")
            self.btn_start.setStyleSheet("""
                QPushButton { background-color: #67c23a; color: white; border-radius: 25px; font-weight: bold; font-size: 16px;}
                QPushButton:hover { background-color: #529b2e; }
            """)
            self.dial_min.setEnabled(True)
            self.dial_sec.setEnabled(True)

            self.timer_finished.emit()

    def update_display_from_timer(self):
        mins, secs = divmod(self.current_seconds, 60)
        self.dial_min.blockSignals(True)
        self.dial_sec.blockSignals(True)
        self.dial_min.set_value(mins)
        self.dial_sec.set_value(secs)
        self.dial_min.blockSignals(False)
        self.dial_sec.blockSignals(False)

    def stop_and_back(self):
        self.back_clicked.emit()
