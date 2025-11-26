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

        # 样式：深色背景，圆角，白色文字 (模仿图一效果)
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
        # 分钟可以一直加，秒数在 0-59 循环
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

            # 设置灵敏度，每移动 10 像素变 1 个数值
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

    def __init__(self):
        super().__init__()
        self.default_minutes = 25
        self.current_seconds = self.default_minutes * 60
        self.is_running = False

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

        # --- 3. 时间显示区域 (核心修改) ---
        time_container = QWidget()
        time_layout = QHBoxLayout(time_container)
        time_layout.setContentsMargins(0, 10, 0, 10)
        time_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_layout.setSpacing(10)

        # 分钟组件
        self.dial_min = DraggableNumber(25, 99, is_minute=True)
        self.dial_min.valueChanged.connect(self.on_time_dial_changed)

        # 冒号
        lbl_colon = QLabel(":")
        lbl_colon.setFont(QFont("Segoe UI", 40, QFont.Weight.Bold))
        lbl_colon.setStyleSheet("color: #333; margin-bottom: 10px;")  # 微调位置

        # 秒钟组件
        self.dial_sec = DraggableNumber(0, 59, is_minute=False)
        self.dial_sec.valueChanged.connect(self.on_time_dial_changed)

        time_layout.addWidget(self.dial_min)
        time_layout.addWidget(lbl_colon)
        time_layout.addWidget(self.dial_sec)

        layout.addWidget(time_container)

        # 提示文字
        lbl_hint = QLabel("滚动或拖动数字调整时间")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hint.setStyleSheet("color: #ccc; font-size: 10px;")
        layout.addWidget(lbl_hint)

        layout.addStretch()

        # --- 4. 底部控制按钮 (胶囊形状) ---
        self.btn_start = QPushButton("开始专注")
        self.btn_start.setFixedSize(180, 50)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.toggle_timer)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self.btn_start)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(74, 144, 226, 80))
        shadow.setOffset(0, 5)
        self.btn_start.setGraphicsEffect(shadow)

        self.btn_start.setStyleSheet("""
            QPushButton { 
                background-color: #4a90e2; 
                color: white; 
                border-radius: 25px; 
                font-weight: bold; 
                font-size: 16px;
                font-family: "Microsoft YaHei";
            }
            QPushButton:hover { background-color: #357abd; }
        """)

        # 居中放置按钮
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        btn_container.addWidget(self.btn_start)
        btn_container.addStretch()
        layout.addLayout(btn_container)

        layout.addStretch()

    # === 逻辑处理 ===

    def on_time_dial_changed(self):
        """当拖动数字时，更新内部时间变量"""
        if not self.is_running:
            m = self.dial_min.value
            s = self.dial_sec.value
            self.current_seconds = m * 60 + s
            # 拖动时更新状态文字
            self.lbl_status.setText("设定时间")

    def toggle_timer(self):
        if self.is_running:
            # 暂停
            self.timer.stop()
            self.is_running = False
            self.btn_start.setText("继续专注")
            self.btn_start.setStyleSheet("""
                QPushButton { background-color: #4a90e2; color: white; border-radius: 25px; font-weight: bold; font-size: 16px;}
                QPushButton:hover { background-color: #357abd; }
            """)
            self.lbl_status.setText("已暂停")
            # 恢复数字组件的可交互性
            self.dial_min.setEnabled(True)
            self.dial_sec.setEnabled(True)
        else:
            # 开始
            self.timer.start()
            self.is_running = True
            self.btn_start.setText("暂停")
            self.btn_start.setStyleSheet("""
                QPushButton { background-color: #333; color: white; border-radius: 25px; font-weight: bold; font-size: 16px;}
                QPushButton:hover { background-color: #555; }
            """)
            self.lbl_status.setText("正在专注...")
            # 计时过程中禁止修改时间
            self.dial_min.setEnabled(False)
            self.dial_sec.setEnabled(False)

    def update_timer(self):
        if self.current_seconds > 0:
            self.current_seconds -= 1
            self.update_display_from_timer()
        else:
            self.timer.stop()
            self.is_running = False
            self.lbl_status.setText("🎉 专注完成！")
            self.btn_start.setText("开始新专注")
            self.btn_start.setStyleSheet("""
                QPushButton { background-color: #67c23a; color: white; border-radius: 25px; font-weight: bold; font-size: 16px;}
                QPushButton:hover { background-color: #529b2e; }
            """)
            self.dial_min.setEnabled(True)
            self.dial_sec.setEnabled(True)

    def update_display_from_timer(self):
        """倒计时过程中更新 UI"""
        mins, secs = divmod(self.current_seconds, 60)
        # 暂时断开信号，防止循环调用
        self.dial_min.blockSignals(True)
        self.dial_sec.blockSignals(True)

        self.dial_min.set_value(mins)
        self.dial_sec.set_value(secs)

        self.dial_min.blockSignals(False)
        self.dial_sec.blockSignals(False)

    def stop_and_back(self):
        if self.is_running:
            self.toggle_timer()
        self.back_clicked.emit()
