import sys
from PySide2.QtWidgets import QApplication, QWidget, QPlainTextEdit, QVBoxLayout
from PySide2.QtCore import Qt, QPoint, QRect
from PySide2.QtGui import QFont, QPainterPath, QRegion, QMouseEvent

class HexagonWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)  # 无边框
        self.setAttribute(Qt.WA_TranslucentBackground) # 透明背景（为了遮罩生效）
        self.setGeometry(100, 100, 300, 400)          # 窗口大小（矩形区域）

        # 创建六边形遮罩
        self.setHexMask()

        # 内部布局：放置文本显示框
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)    # 内边距，让文本不贴边

        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        font = QFont("Courier New", 10)
        self.text_edit.setFont(font)
        self.text_edit.setStyleSheet("background: white; border: none;")  # 白色背景无边框
        self.text_edit.setCursorWidth(0)             # 隐藏光标
        
        layout.addWidget(self.text_edit)

        # 填充文本（同之前的顺序）
        lines = []
        for i in range(1, 7):
            lines.append(f"{i}a")
        for i in range(7, 20):
            lines.append(str(i))
        for i in range(1, 20):
            lines.append(f"{i}b")
        self.text_edit.setPlainText("\n".join(lines))

        # 为了支持拖动窗口，重写鼠标事件
        self.drag_pos = None

    def setHexMask(self):
        """根据窗口当前大小生成六边形遮罩"""
        rect = self.rect()  # 窗口的矩形区域
        w, h = rect.width(), rect.height()
        # 六边形顶点（正六边形，中心对称）
        # 这里使用六边形顶点比例，使六边形内切于矩形
        # 顶点顺序（顺时针或逆时针）：
        points = [
            QPoint(int(w * 0.5), 0),                # 上
            QPoint(w, int(h * 0.25)),               # 右上
            QPoint(w, int(h * 0.75)),               # 右下
            QPoint(int(w * 0.5), h),                # 下
            QPoint(0, int(h * 0.75)),               # 左下
            QPoint(0, int(h * 0.25)),               # 左上
        ]
        path = QPainterPath()
        path.moveTo(points[0])
        for p in points[1:]:
            path.lineTo(p)
        path.closeSubpath()
        # 转换为区域并设置遮罩
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def resizeEvent(self, event):
        """窗口大小改变时重新设置遮罩"""
        self.setHexMask()
        super().resizeEvent(event)

    # -------- 实现窗口拖动 ----------
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HexagonWindow()
    window.show()
    sys.exit(app.exec_())