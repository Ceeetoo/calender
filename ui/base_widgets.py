# uii/base_widgets.py
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QCheckBox, QLabel, QPushButton,
                             QListWidget, QListWidgetItem, QAbstractItemView, QTextEdit, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal


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

    def add_task(self, data, update_layout=True):
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
        
        # 只有当需要更新布局时才调用调整高度
        if update_layout:
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

        # 1. 更新现有项
        for i in range(min(current_count, new_count)):
            item = self.item(i)
            data = todos[i]
            item.setData(Qt.ItemDataRole.UserRole, data)
            widget = self.itemWidget(item)
            if widget:
                display_text = self.format_text(data)
                widget.update_data(display_text, data.get('done', False))
                # 重新计算该项的尺寸提示，防止内容长度变化导致截断
                item.setSizeHint(widget.sizeHint())

        # 2. 添加新项 (关键：传入 update_layout=False)
        if new_count > current_count:
            for i in range(current_count, new_count):
                self.add_task(todos[i], update_layout=False)

        # 3. 删除多余项
        if current_count > new_count:
            for i in range(current_count - 1, new_count - 1, -1):
                self.takeItem(i)

        self.blockSignals(False)
        
        # 4. 最后统一调整一次高度
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
