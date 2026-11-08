import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton

app = QApplication(sys.argv)

window = QWidget()
window.setWindowTitle("Hello PyQt6 - Tenzin Choden (29)")
window.resize(300, 150)

label = QLabel("Hello!")
button = QPushButton("Click me")
button.clicked.connect(lambda: label.setText("Button clicked!"))

layout = QVBoxLayout(window)
layout.addWidget(label)
layout.addWidget(button)

window.show()
sys.exit(app.exec())