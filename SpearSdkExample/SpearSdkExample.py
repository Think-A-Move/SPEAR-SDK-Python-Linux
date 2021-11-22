# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QComboBox
)
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QWidgetItem
from spear import SpearRecognizer
from spear import SpearWakeUp
from utils import ModifyConfig
from commands.CommandList import DemoCommandList
from commands.CommandList import LabelCommandList
import argparse
import os
import queue
import sounddevice as sd
import numpy as np
import sys

TAM_PROFILE_INDEPENDENT = 0
TAM_SAMPLERATE_16000 = 0

default_demo_prompt = """
  Please say the following commands:
      1. Say "STOP SPEAR" to put back SPEAR in wake-up grammar OR
      2. Say "SWITCH GRAMMAR" to switch to pre-compiled aviation commands grammar OR
      3. Say "SWITCH LABEL GRAMMAR" to switch to label commands grammar OR
      4. [ALPHA, BRAVO, CHARLIE, DELTA, ECHO, FOXTROT, GOLF, HOTEL, INDIA, JULIET, KILO,
         LIMA, MIKE, NOVEMBER, OSCAR, PAPA, QUEBEC, ROMEO, SIERRA, TANGO, UNIFORM, VICTOR,
         WHISKEY, XRAY, YANKEE, ZULU, KWA BEK, KEI BEK, SWITCH GRAMMAR, SWITCH LABEL GRAMMAR]
"""

aviation_command_prompt = """
  Please say the following commands:
      1. Say "STOP SPEAR" to put back SPEAR in wake-up grammar OR
      2. [SET HEADING, SET COURSE, TUNE COM, SET COM, SELECT COM, TUNE CHANNEL, SET CHANNEL,
         SELECT CHANNEL, TUNE V H F, SELECT V H F, SET ALTITUDE, FLIGHT LEVEL, PROCEED DIRECT,
         SELECT DIRECT, CENTER MAP, SET RANGE, RANGE CLICK, MAP ZOOM IN, MAP ZOOM OUT]
"""

label_command_prompt = """
  Please say the following commands:
      1. Say "STOP SPEAR" to put back SPEAR in wake-up grammar OR
      2. I have a [dog, cat, rabbit, bird],
         [turn on, turn off] light,
         volume [up, off],
         My [dog, cat, rabbit, bird] weight 24.5 lb,
         Her [bicycle, ship, car, plane] values [any integer number] dollars,
         CLE stands for cleveland
"""

trial_time_up_prompt = """
  Trial time limit is reached. Please update your license.
"""

wakeup_prompt = """
  Please say "HEY SPEAR" to change grammar to Demo Commands.
"""

class WakeUpCallback(SpearWakeUp.SpearWakeUpCallback):
    def __init__(self):
        super().__init__()
        self.is_wakeup = False

    def onCommitResult(self, arg0):
        if (arg0.retval == 1):
            self.is_wakeup = True
        else:
            self.is_wakeup = False

    def wakeup(self):
        return self.is_wakeup

class RecognizerCallback(SpearRecognizer.SpearRecognizerCallback):
    def __init__(self):
        SpearRecognizer.SpearRecognizerCallback.__init__(self)
        self.result = ""

    def onCommitResult(self, arg0, arg1):
        self.result = arg1.transcriptionPairs.transcription

q = queue.Queue()

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

# Create a worker class
class WakeUpWorker(QObject):
    triggered = pyqtSignal()
    is_initialized_triggered = pyqtSignal(str)

    def __init__(self, parent=None):
        QObject.__init__(self, parent=parent)
        self.continue_run = True
        
        self.data_folder = 'assets/resources/SPEAR-DATA-EN/SPEAR-WakeUp'
        ModifyConfig('{}/SpearWakeUp.config'.format(self.data_folder), self.data_folder)
        self.engine = SpearWakeUp.SpearWakeUpEngine()
        self.engine.InitWithFst("assets/resources/SPEAR-DATA-EN/SPEAR-WakeUp", "assets/resources/Fsts/heyspear.fst")
        self.wakeup_callback = WakeUpCallback()
        self.callback_wrapper = self.wakeup_callback.createWrapper() 

    @pyqtSlot()
    def run(self):
        self.is_initialized_triggered.emit("Unknown")

        with sd.RawInputStream(samplerate=16000, blocksize = 8000, device=None, dtype='int16',
                                channels=1, callback=callback):
            print('WakeUpWorker: press Ctrl+C to stop the recording')

            while self.continue_run:
                data = q.get()
                data_samples = np.frombuffer(data, np.int16).tolist()
                self.engine.ProcessTask(data_samples, self.callback_wrapper)
                if (self.wakeup_callback.wakeup()):
                    print("WakeUp!!!")
                    self.triggered.emit()
                    break

    def stop(self):
        self.continue_run = False

class RecognizerWorker(QObject):
    recognized_result = pyqtSignal(str)
    switch_grammar_triggered = pyqtSignal(str)
    switch_label_grammar_triggered = pyqtSignal(str)
    is_initialized_triggered = pyqtSignal(str)
    stop_triggered = pyqtSignal()
    trial_time_up = pyqtSignal()
    
    def __init__(self, parent=None):
        QObject.__init__(self, parent=parent)
        self.continue_run = True
        
        self.data_folder = 'assets/resources/SPEAR-DATA-EN/SPEAR-ASR/'
        ModifyConfig('{}/Spear.config'.format(self.data_folder), self.data_folder)
        self.engine = SpearRecognizer.Initialize(self.data_folder)


        self.profile = SpearRecognizer.ProfileLoadUntrained(self.engine, TAM_PROFILE_INDEPENDENT, TAM_SAMPLERATE_16000)
        
        aviation_grammar_path = 'assets/resources/Fsts/aviation_JL16k-NA_v4.fst'
        self.aviation_grammar = SpearRecognizer.GrammarLoad(aviation_grammar_path)

        demoCommandList = DemoCommandList()
        demo_command_list = demoCommandList.getCommandList()
        demo_command_list_regex = demoCommandList.getRegexFromCommandList(demo_command_list)
        self.demo_grammar = SpearRecognizer.GrammarCompile(self.engine, demo_command_list_regex, 0, 0, 0)

        labelCommandList = LabelCommandList()
        label_command_list = labelCommandList.getCommandList()
        label_command_list_regex = labelCommandList.getRegexFromCommandList(label_command_list)
        self.label_grammar = SpearRecognizer.GrammarCompile(self.engine, label_command_list_regex, 0, 0, 0)
        
        self.recognizer = SpearRecognizer.RecognizerInit(self.engine, self.profile, self.demo_grammar, 0)
        
        self.handler = RecognizerCallback()

        self.current_grammar = "demo_grammar"
        
        status = SpearRecognizer.CheckRegistration(self.engine)
        if status == 0:
            self.registration_status = "Unregistred"
        elif status == 1:
            self.registration_status = "Registred"
        elif status == 2:
            self.registration_status = "Expired"
        else:
            self.registration_status = "Unknown"

    def run(self):
        self.is_initialized_triggered.emit(self.registration_status)
        print("emit self.registration_status")
        with sd.RawInputStream(samplerate=16000, blocksize = 8000, device=None, dtype='int16',
                                channels=1, callback=callback):
            
            print('RecognizerWorker: press Ctrl+C to stop the recording')

            while self.continue_run:
                data = q.get()
                data_samples = np.frombuffer(data, np.int16).tolist()
                is_recognizer_process_ok = SpearRecognizer.RecognizerContinuousProcess_wrapper(self.recognizer, data_samples, self.handler)
                if (is_recognizer_process_ok != 0):
                    error_message = SpearRecognizer.GetLastError()
                    if "Trial limit is reached. Please update your license" in error_message:
                        self.trial_time_up.emit()
                        break

                if (self.handler.result != ""):
                    if (self.handler.result.upper() == "STOP SPEAR"):
                        print("RecognizerWorker: triggered!")
                        self.stop_triggered.emit()
                        break
                    elif (self.handler.result.upper() == "SWITCH GRAMMAR"):
                        SpearRecognizer.ChangeGrammar(self.recognizer, self.aviation_grammar)
                        self.current_grammar = "aviation_grammar"
                        self.switch_grammar_triggered.emit(aviation_command_prompt)
                        self.handler.result = ""
                        continue
                    elif (self.handler.result.upper() ==  "SWITCH LABEL GRAMMAR"):
                        SpearRecognizer.ChangeGrammar(self.recognizer, self.label_grammar)
                        self.current_grammar = "label_grammar"
                        self.switch_label_grammar_triggered.emit(label_command_prompt)
                        self.handler.result = ""
                        continue
                    else:
                        self.recognized_result.emit(self.handler.result)
                        self.handler.result = ""

    def stop(self):
        self.continue_run = False

    def updateConfig(self, config_list):
        is_update_ok = SpearRecognizer.UpdateConfig(self.engine, config_list)
        print("Update config: {}".format(config_list))

def hideWidgets(layout):
    items = (layout.itemAt(i) for i in range(layout.count()))
    for item in items:
        if isinstance(item, QHBoxLayout) or isinstance(item, QVBoxLayout):
            hideWidgets(item)
        elif isinstance(item, QWidgetItem):
            item.widget().hide()

def showWidgets(layout):
    items = (layout.itemAt(i) for i in range(layout.count()))
    for item in items:
        if isinstance(item, QHBoxLayout) or isinstance(item, QVBoxLayout):
            showWidgets(item)
        elif isinstance(item, QWidgetItem):
            item.widget().show()

class Window(QMainWindow):

    stop_wakeup_signal = pyqtSignal()
    stop_recognizer_signal = pyqtSignal()
    update_config_clicked_signal = pyqtSignal(list)

    def __init__(self, parent=None):
        self.registration_status = ""
        super().__init__(parent)
        self.setupUi()

    def setupUi(self):
        self.setWindowTitle("SpearSdkExample")
        self.resize(800, 500)
        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)

        # create widgets for centralWidget
        self.statusLabel = QLabel("SPEAR Status: Loading...", self)
        self.statusLabel.setStyleSheet("color: blue")
        self.promptLabel = QLabel(wakeup_prompt, self)
        self.promptLabel.setStyleSheet("color: #090; line-height: 150%;")
        self.resultLabel = QLabel('SPEAR Transcribed Text', self)

        layout = QVBoxLayout()
        layout.addWidget(self.statusLabel)
        layout.addWidget(self.promptLabel)
        layout.addWidget(self.resultLabel)

        # create layout and widgets for config section
        self.config_layout = QVBoxLayout()
        self.config_layout_1 = QHBoxLayout()
        #self.config_layout_2 = QHBoxLayout()

        self.configLabel_1 = QLabel("--case-preference", self)
        self.configCombo_1 = QComboBox(self)
        self.configCombo_1.addItems(["--", "upper", "lower", "raw"])
        self.config_layout_1.addWidget(self.configLabel_1)
        self.config_layout_1.addWidget(self.configCombo_1)

        """
        self.configLabel_2 = QLabel("--g2p-abbreviation-threshold", self)
        self.configCombo_2 = QComboBox(self)
        self.configCombo_2.addItems(["--", "3", "5"])
        self.config_layout_2.addWidget(self.configLabel_2)
        self.config_layout_2.addWidget(self.configCombo_2)
        """

        self.config_btn_layout = QHBoxLayout()
        self.config_message_layout = QHBoxLayout()
        self.config_btn_layout.setAlignment(Qt.AlignCenter)
        self.config_message_layout.setAlignment(Qt.AlignCenter)
        self.config_btn = QPushButton("update", self)
        self.config_btn.setMaximumWidth(200)
        self.config_message = QLabel("", self)

        self.config_layout.addLayout(self.config_layout_1)
        #self.config_layout.addLayout(self.config_layout_2)
        self.config_layout.addLayout(self.config_btn_layout)
        self.config_layout.addLayout(self.config_message_layout)

        self.config_btn_layout.addWidget(self.config_btn)
        self.config_message_layout.addWidget(self.config_message)

        layout.addLayout(self.config_layout)

        self.centralWidget.setLayout(layout)

        hideWidgets(self.config_layout) 
        self.runWakeUp()

    def reportWakeUpStatus(self):
        self.promptLabel.setText(default_demo_prompt)
        self.promptLabel.adjustSize()
        showWidgets(self.config_layout)
        print("Now call runRecognizer()")
        self.runRecognizer()

    def changePrompt(self, prompt):
        self.promptLabel.setText(prompt)
    
    def reportRecognizerStatus(self, res):
        self.resultLabel.setText(res)
        #self.resultLabel.adjustSize()
    
    def exit_recognizer(self):
        self.resultLabel.setText("")
        self.promptLabel.setText(wakeup_prompt)
        self.promptLabel.adjustSize()
        print("Now call runWakeUp()")
        hideWidgets(self.config_layout)
        self.runWakeUp()

    def runWakeUp(self):
        # Create a QThread object
        self.wakeup_thread = QThread(parent=self)
        # Create a worker object
        self.wakeup_worker = WakeUpWorker()
        self.stop_wakeup_signal.connect(self.wakeup_worker.stop)
        # Move worker to the thread
        self.wakeup_worker.moveToThread(self.wakeup_thread)
        # Connect signals and slots
        self.wakeup_thread.started.connect(self.wakeup_worker.run)
        self.wakeup_worker.triggered.connect(self.wakeup_thread.quit)
        self.wakeup_worker.is_initialized_triggered.connect(self.updateWakeUpStatusMessage)
        self.wakeup_worker.triggered.connect(self.wakeup_worker.deleteLater)
        self.wakeup_thread.finished.connect(self.wakeup_thread.deleteLater)
        self.wakeup_worker.triggered.connect(self.reportWakeUpStatus)
        self.wakeup_worker.triggered.connect(self.stop_wakeup_thread)
        # Start the thread
        self.wakeup_thread.start()

    def runRecognizer(self):
        # Create a QThread object
        self.recognizer_thread = QThread(parent=self)
        # Create a worker object
        self.recognizer_worker = RecognizerWorker()
        self.stop_recognizer_signal.connect(self.recognizer_worker.stop)
        self.update_config_clicked_signal.connect(self.recognizer_worker.updateConfig)
        # Move worker to the thread
        self.recognizer_worker.moveToThread(self.recognizer_thread)
        # Connect signals and slots
        self.recognizer_thread.started.connect(self.recognizer_worker.run)
        self.recognizer_worker.is_initialized_triggered.connect(self.updateStatusMessage)
        self.recognizer_worker.stop_triggered.connect(self.recognizer_thread.quit)
        self.recognizer_worker.stop_triggered.connect(self.recognizer_worker.deleteLater)
        self.recognizer_worker.trial_time_up.connect(self.recognizer_trial_time_up)
        self.recognizer_thread.finished.connect(self.recognizer_thread.deleteLater)
        self.recognizer_worker.recognized_result.connect(self.reportRecognizerStatus)
        self.recognizer_worker.switch_grammar_triggered.connect(self.changePrompt)
        self.recognizer_worker.switch_label_grammar_triggered.connect(self.changePrompt)
        self.recognizer_worker.stop_triggered.connect(self.stop_recognizer_thread)
        self.recognizer_worker.stop_triggered.connect(self.exit_recognizer)

        self.config_btn.clicked.connect(self.updateConfig)
        # Start the thread
        self.recognizer_thread.start()

    def updateStatusMessage(self, status):
        if self.registration_status == "":
            self.registration_status = status
        self.statusLabel.setText("SPEAR Status: {}, Listening...".format(status))
    
    def updateWakeUpStatusMessage(self):
        if self.registration_status != "":
            self.statusLabel.setText("SPEAR Status: {}, Listening...".format(self.registration_status))
        else:
            self.statusLabel.setText("SPEAR Status: Listening...")

    def stop_wakeup_thread(self):
        self.stop_wakeup_signal.emit()
    
    def stop_recognizer_thread(self):
        self.stop_recognizer_signal.emit()

    def updateConfig(self):
        self.config_message.setText("")
        update_configs = []
        config1 = self.configCombo_1.currentText()
        #config2 = self.configCombo_2.currentText()
        if (config1 == "--"):
            self.config_message.setStyleSheet("color: red")
            self.config_message.setText("Warning: No config parameter passed to update config!")
        else:
            update_configs.append(str.encode("--case-preference={}".format(config1)))
            self.config_message.setText("LOG: config {} has been passed to Spear-recognizer.".format(config1))
            self.update_config_clicked_signal.emit(update_configs)

    def recognizer_trial_time_up(self):
        self.resultLabel.setText("")
        self.promptLabel.setStyleSheet("color: red")
        self.promptLabel.setText(trial_time_up_prompt)
        if self.registration_status != "":
            self.statusLabel.setText("SPEAR Status: {}, Terminated".format(self.registration_status))
        else:
            self.statusLabel.setText("SPEAR Status: Terminated")
            
        self.promptLabel.adjustSize()
        hideWidgets(self.config_layout)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())
