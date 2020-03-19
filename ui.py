# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'douyintool.ui'
#
# Created by: PyQt5 UI code generator 5.13.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def onclick_clear(self):
        self.textEdit.clear()
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(438, 303)
        MainWindow.setAnimated(True)
        MainWindow.setDocumentMode(False)
        MainWindow.setUnifiedTitleAndToolBarOnMac(False)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        # self.lcdNumber = QtWidgets.QLCDNumber(self.centralwidget)
        # self.lcdNumber.setGeometry(QtCore.QRect(340, 0, 64, 23))
        # self.lcdNumber.setObjectName("lcdNumber")
        # self.lcdNumber.setWindowIconText('123')
        self.textEdit = QtWidgets.QTextEdit(self.centralwidget)
        self.textEdit.setGeometry(QtCore.QRect(100, 40, 251, 41))
        self.textEdit.setObjectName("textEdit")
        # self.textEdit.insertPlainText('123')
        self.textEdit.setAcceptRichText(False)
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(40, 40, 81, 41))
        self.label.setObjectName("label")
        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(120, 100, 75, 23))
        self.pushButton.setObjectName("pushButton")
        self.pushButton.clicked.connect(lambda: self.onclick_clear())
        self.pushButton_2 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_2.setGeometry(QtCore.QRect(250, 100, 75, 23))
        self.pushButton_2.setObjectName("pushButton_2")
        # self.pushButton_2.clicked.connect(lambda : onclick1)
        self.plainTextEdit = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.plainTextEdit.setGeometry(QtCore.QRect(100, 150, 251, 101))
        self.plainTextEdit.setDocumentTitle("")
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.plainTextEdit.setReadOnly(True)
        # self.plainTextEdit.insertPlainText("123\n")
        # self.plainTextEdit.insertPlainText("456")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(60, 190, 54, 12))
        self.label_2.setObjectName("label_2")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 438, 23))
        self.menubar.setObjectName("menubar")
        self.menu = QtWidgets.QMenu(self.menubar)
        self.menu.setObjectName("menu")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionv1_0_by_DLWangSan = QtWidgets.QAction(MainWindow)
        self.actionv1_0_by_DLWangSan.setObjectName("actionv1_0_by_DLWangSan")
        self.menu.addAction(self.actionv1_0_by_DLWangSan)
        self.menubar.addAction(self.menu.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "开源抖音小工具V1"))
        self.label.setText(_translate("MainWindow", "分享链接"))
        self.pushButton.setText(_translate("MainWindow", "清空输入框"))
        self.pushButton_2.setText(_translate("MainWindow", "下载"))
        self.label_2.setText(_translate("MainWindow", "日志"))
        self.menu.setTitle(_translate("MainWindow", "版本"))
        self.actionv1_0_by_DLWangSan.setText(_translate("MainWindow", "v1.0 by DLWangSan"))
