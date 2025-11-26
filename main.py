# main.py
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from ui.main_window import DesktopCalendar

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 关键设置：关闭最后一个窗口时不退出程序（为了托盘功能）
    app.setQuitOnLastWindowClosed(False)

    app.setFont(QFont("Microsoft YaHei", 9))

    window = DesktopCalendar()
    window.show()

    sys.exit(app.exec())
