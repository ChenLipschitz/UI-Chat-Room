import socket
import packet
import sys
import threading
import time
from socket import SOCK_DGRAM
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont
from PyQt5.QtWidgets import QGridLayout, QScrollArea, QLabel, QListView, QProgressBar
from PyQt5.QtWidgets import QLineEdit, QComboBox, QGroupBox
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton
from PyQt5.QtWidgets import QVBoxLayout, QMessageBox, QTabWidget

FORMAT = "utf-8"


class MyTableWidget(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        # connection
        self.conn = socket.socket()
        self.connected = False

        # tab settings
        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.resize(300, 200)

        self.tabHome = QWidget()
        self.tabChat = QWidget()
        self.tabFiles = QWidget()

        self.tabs.addTab(self.tabHome, "Home")
        self.tabs.addTab(self.tabChat, "Chat Room")
        self.tabs.addTab(self.tabFiles, "Files")
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)

        # Home Page
        gridHome = QGridLayout()
        self.tabHome.setLayout(gridHome)
        self.IPBox = QGroupBox("IP")
        self.IPLineEdit = QLineEdit()
        self.IPLineEdit.setText(socket.gethostbyname(socket.gethostname()))
        IPBoxLayout = QVBoxLayout()
        IPBoxLayout.addWidget(self.IPLineEdit)
        self.IPBox.setLayout(IPBoxLayout)
        self.portBox = QGroupBox("port")
        self.portLineEdit = QLineEdit()
        self.portLineEdit.setText("5050")
        portBoxLayout = QVBoxLayout()
        portBoxLayout.addWidget(self.portLineEdit)
        self.portBox.setLayout(portBoxLayout)
        self.nameBox = QGroupBox("Name")
        self.nameLineEdit = QtWidgets.QLineEdit()
        nameBoxLayout = QVBoxLayout()
        nameBoxLayout.addWidget(self.nameLineEdit)
        self.nameBox.setLayout(nameBoxLayout)
        self.connStatus = QLabel("Status", self)

        font = QFont()
        font.setPointSize(16)

        self.connStatus.setFont(font)
        self.connButton = QPushButton("Connect")
        self.connButton.clicked.connect(self.connect_server)
        self.disconnButton = QPushButton("Disconnect")
        self.disconnButton.clicked.connect(self.disconnect_server)

        gridHome.addWidget(self.IPBox, 0, 0, 1, 1)
        gridHome.addWidget(self.portBox, 0, 1, 1, 1)
        gridHome.addWidget(self.nameBox, 1, 0, 1, 1)
        gridHome.addWidget(self.connStatus, 1, 1, 1, 1)
        gridHome.addWidget(self.connButton, 2, 0, 1, 1)
        gridHome.addWidget(self.disconnButton, 2, 1, 1, 1)
        gridHome.setColumnStretch(0, 1)
        gridHome.setColumnStretch(1, 1)
        gridHome.setRowStretch(0, 0)
        gridHome.setRowStretch(1, 0)
        gridHome.setRowStretch(2, 9)

        # Chat Room
        gridChatRoom = QGridLayout()
        self.tabChat.setLayout(gridChatRoom)
        self.messageRecords = QLabel("<font color=\"purple\">Welcome to chat room!</font>", self)
        self.messageRecords.setStyleSheet("background-color: white;")
        self.messageRecords.setAlignment(QtCore.Qt.AlignTop)
        self.messageRecords.setAutoFillBackground(True)
        self.scrollRecords = QScrollArea()
        self.scrollRecords.setWidget(self.messageRecords)
        self.scrollRecords.setWidgetResizable(True)
        self.sendTo = "ALL"
        self.sendChoice = QLabel("Send to :ALL", self)
        self.sendComboBox = QComboBox(self)
        self.sendComboBox.addItem("ALL")
        self.sendComboBox.activated[str].connect(self.send_choice)
        self.lineEdit = QLineEdit()
        self.lineEnterButton = QPushButton("Enter")
        self.lineEnterButton.clicked.connect(self.enter_line)
        self.lineEdit.returnPressed.connect(self.enter_line)
        self.friendList = QListView()
        self.friendList.setWindowTitle('Friends List')
        self.model = QStandardItemModel(self.friendList)
        self.friendList.setModel(self.model)

        gridChatRoom.addWidget(self.scrollRecords, 0, 0, 1, 3)
        gridChatRoom.addWidget(self.friendList, 0, 3, 1, 1)
        gridChatRoom.addWidget(self.sendComboBox, 1, 0, 1, 1)
        gridChatRoom.addWidget(self.sendChoice, 1, 2, 1, 1)
        gridChatRoom.addWidget(self.lineEdit, 2, 0, 1, 3)
        gridChatRoom.addWidget(self.lineEnterButton, 2, 3, 1, 1)
        gridChatRoom.setColumnStretch(0, 9)
        gridChatRoom.setColumnStretch(1, 9)
        gridChatRoom.setColumnStretch(2, 9)
        gridChatRoom.setColumnStretch(3, 1)
        gridChatRoom.setRowStretch(0, 9)

        # file page init
        FilePage = QGridLayout()
        self.tabFiles.setLayout(FilePage)
        self.dFile = QLabel("Download Files", self)
        self.dFile.setFont(font)
        self.download = QComboBox()
        self.start_download = QPushButton("Start download!")
        self.start_download.pressed.connect(self.getFileName)
        self.loadingbar = QProgressBar()
        self.start_download.clicked.connect(self.progressBarUI)
        self.start_download.clicked.connect(self.files_socket)

        FilePage.addWidget(self.dFile, 0, 0, 1, 1)
        FilePage.addWidget(self.download, 0, 1, 1, 1)
        FilePage.addWidget(self.start_download, 1, 1, 1, 1)
        FilePage.addWidget(self.loadingbar, 2, 0, 1, 3)
        FilePage.setRowStretch(0, 0)
        FilePage.setColumnStretch(0, 1)
        FilePage.setRowStretch(1, 0)
        FilePage.setColumnStretch(1, 1)

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    def files_socket(self):
        file_transfer_socket = socket.socket(socket.AF_INET, SOCK_DGRAM)
        file_transfer_socket.bind((socket.gethostbyname(socket.gethostname()), 8080))
        self.conn.send(("[FILEA]" + self.download.currentText()).encode())
        self.receiveFile(file_transfer_socket, self.download.currentText())

        file_transfer_socket.close()

    def receiveFile(self, sock, filename):
        # Open file for writing
        try:
            file = open(filename, 'wb')
        except IOError:
            print('Unable to open', filename)
            return
        expected_num = 0
        while True:
            # Get next packet from the sender
            pkt, addr = sock.recvfrom(1024)
            if not pkt:
                break
            seq_num, data = packet.extractPacket(pkt)
            print('Got packet', seq_num)

            # Send back an ACK
            if seq_num == expected_num:
                print('Got expected packet')
                print('Sending ACK', expected_num)
                pkt = packet.createPacket(expected_num)
                sock.sendto(pkt, addr)
                expected_num += 1
                file.write(data)
            else:
                print('Sending ACK', expected_num - 1)
                pkt = packet.createPacket(expected_num - 1)
                sock.sendto(pkt, addr)
        print('Downloaded!')

        file.close()

    def progressBarUI(self):
        for i in range(101):
            time.sleep(0.05)
            self.loadingbar.setValue(i)

    def getFileName(self):
        content = self.download.currentText()
        print("--DOWNLOADING-- " + content)

    def enter_line(self):
        # before sending, check if the receiver is the room
        if self.sendTo != self.sendComboBox.currentText():
            self.message_append_to_screen("The person has left.\nThe message was not delivered")
            self.lineEdit.clear()
            return
        line = self.lineEdit.text()
        if line == "":  # prevent empty message
            return
        if self.sendTo != "ALL":  # private message, first send to myself
            send_msg = bytes("[" + self.userName + "]" + line, FORMAT)
            self.conn.send(send_msg)
            time.sleep(0.1)  # this is important for not overlapping two sending
        send_msg = bytes("[" + self.sendTo + "]" + line, FORMAT)
        self.conn.send(send_msg)
        self.lineEdit.clear()
        self.scrollRecords.verticalScrollBar().setValue(self.scrollRecords.verticalScrollBar().maximum())

    def message_append_to_screen(self, newMessage, textColor="black"):
        oldText = self.messageRecords.text()
        appendText = oldText + "<br /><font color=\"" + textColor + "\">" + newMessage + "</font><font color=\"black\"></font>"
        self.messageRecords.setText(appendText)
        time.sleep(0.2)
        self.scrollRecords.verticalScrollBar().setValue(self.scrollRecords.verticalScrollBar().maximum())

    def updateRoom(self):
        counter = 0
        while self.connected:
            data = self.conn.recv(1024)
            data = data.decode(FORMAT)
            print(data)
            if data != "":
                if "[FILES]" in data:
                    names = data.split("[FILES]")
                    self.update_file_list(names[1])
                    counter += 1
                    continue
                if "[CLIENTS]" in data:
                    welcome = data.split("[CLIENTS]")
                    self.update_send_to_list(welcome[1])
                    self.update_room_list(welcome[1])
                    if not welcome[0][5:] == "":
                        self.message_append_to_screen(welcome[0][5:])
                        self.scrollRecords.verticalScrollBar().setValue(
                            self.scrollRecords.verticalScrollBar().maximum())
                elif data[:5] == "[MSG]":
                    self.message_append_to_screen(data[5:], "blue")
                    self.scrollRecords.verticalScrollBar().setValue(self.scrollRecords.verticalScrollBar().maximum())
                else:
                    self.message_append_to_screen("[private] " + data, "green")
                    self.scrollRecords.verticalScrollBar().setValue(self.scrollRecords.verticalScrollBar().maximum())
            # this is for saving thread cycle time
            time.sleep(0.1)

    def update_file_list(self, strList):
        L = strList.split(",")
        self.download.clear()
        for file in L:
            self.download.addItem(file)

    def connect_server(self):
        if self.connected:
            return
        name = self.nameLineEdit.text()
        if name == "":
            self.connStatus.setText("Status :" + "Please enter your name")
            return
        self.userName = name
        IP = self.IPLineEdit.text()
        if IP == "":
            IP = "127.0.0.1"
        port = self.portLineEdit.text()
        if port == "" or not port.isnumeric():
            self.portLineEdit.setText("5050")
            self.connStatus.setText("Status :" + "Port format invalid")
            return
        else:
            port = int(port)
        try:
            self.conn.connect((IP, port))
        except:
            self.connStatus.setText("Status :" + " Refused")
            self.conn = socket.socket()
            return
        send_msg = bytes("[REGISTER]" + name, FORMAT)
        self.conn.send(send_msg)
        self.connected = True
        self.connStatus.setText("Status :" + " Connected")
        self.nameLineEdit.setReadOnly(True)  # This setting is not functional well
        self.tabs.setTabEnabled(1, True)
        self.tabs.setTabEnabled(2, True)
        self.newThread = threading.Thread(target=self.updateRoom)
        self.newThread.start()

    def disconnect_server(self):
        if not self.connected:
            return
        send_msg = bytes("[QUIT]", FORMAT)
        self.conn.send(send_msg)
        self.connStatus.setText("Status :" + " Disconnected")
        self.nameLineEdit.setReadOnly(False)
        self.nameLineEdit.clear()
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        self.connected = False
        self.newThread.join()
        self.conn.close()

    def update_room_list(self, strList):
        L = strList.split(",")
        self.model.clear()
        for person in L:
            item = QStandardItem(person)
            item.setCheckable(False)
            self.model.appendRow(item)

    def update_send_to_list(self, strList):
        L = strList.split(",")
        self.sendComboBox.clear()
        self.sendComboBox.addItem("ALL")
        for person in L:
            if person != self.userName:
                self.sendComboBox.addItem(person)
        previous = self.sendTo
        index = self.sendComboBox.findText(previous)
        if index != -1:
            self.sendComboBox.setCurrentIndex(index)  # updating, maintain receiver
        else:
            self.sendComboBox.setCurrentIndex(0)  # updating, the receiver left, default to "ALL"

    def send_choice(self, text):
        self.sendTo = text
        print(self.sendTo)
        self.sendChoice.setText("Send to: " + text)


class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()
        self.setGeometry(50, 50, 500, 300)
        self.setWindowTitle("Best-Chat-Ever")
        self.table_widget = MyTableWidget(self)
        self.setCentralWidget(self.table_widget)
        self.show()

    def closeEvent(self, event):
        close = QMessageBox()
        close.setText("You sure?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        close = close.exec()
        if close == QMessageBox.Yes:
            self.table_widget.disconnect_server()  # disconnect to server before exit
            event.accept()
        else:
            event.ignore()


def run():
    app = QApplication(sys.argv)
    CLIENT = Window()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run()
