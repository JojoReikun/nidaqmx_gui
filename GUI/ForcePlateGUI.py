"""
Locations of required executables and how to use them:
"""

# qt designer located at:
# C:\Users\JojoS\Miniconda3\Lib\site-packages\pyqt5_tools\Qt\bin\designer.exe
# pyuic5 to convert UI to executable python code is located at:
# C:\Users\JojoS\Miniconda3\Scripts\pyuic5.exe
# to convert the UI into the required .py file run:
# -x = input     -o = output
# pyuic5.exe -x "C:\Users\JojoS\Documents\phd\JumpingRobot\nidaqmx\GUI\nidaqmx.ui" -o "C:\Users\JojoS\Documents\phd\JumpingRobot\nidaqmx\GUI\nidaqmx.py"

"""
imports
"""
import sys
import traceback
import datetime
from time import sleep
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import *
from tkinter import filedialog, Tk
import os
from pathlib import Path
from GUI.nidaqmx_gui import Ui_MainWindow
from GUI.calibration.calibration import calibration
import nidaqmx
from nidaqmx import constants, Task
from nidaqmx import stream_readers
from nidaqmx import stream_writers
import numpy as np


class WorkerSignals(QtCore.QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress

    '''
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(tuple)
    result = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal(int)


class Worker(QtCore.QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @QtCore.pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


"""
Initialize nidaqmx/ForcePlateGUI main window:
"""
class nidaqmx_gui_mainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(nidaqmx_gui_mainWindow, self).__init__()

        self.ui = Ui_MainWindow()

        self.ui.setupUi(self)

        self.threadpool = QtCore.QThreadPool()

        self.setWindowTitle("Force Plate GUI - Python is the best")
        ###
        # variables
        ###
        self.sample_frequency = ""
        self.buffer_size = ""
        self.post_trigger_samples = ""

        self.device_number = "Dev1"
        self.first_channel = "0"
        self.number_of_gages = "6"
        self.calib_file = ""
        self.force_units = ""
        self.torque_units = ""
        self.calibration_matrix = None

        """
        Add items to combo boxes:
        """
        self.ui.comboBox_ForceUnits.addItems(["N", "None"])     # first item = default unit
        self.ui.comboBox_TorqueUnits.addItems(["N-mm", "N-m", "None"])      # first item = default unit
        self.ui.comboBox_DAQCard.addItems(["Dev1", ""])

        """
        # assign button / lineEdit functions
        """
        self.ui.pushButton_OpenCalib.pressed.connect(self.open_calib_file)
        self.ui.pushButton_Record.setDisabled(True)
        self.ui.pushButton_Record.pressed.connect(self.record_forces) #TODO: eventually make this "engaged" instead of "pressed"

        # self.ui.Project_name_lineEdit.textChanged.connect(self.set_project_name)
        # self.ui.Project_experimenter_lineEdit.textChanged.connect(self.set_project_experimenter)
        # self.ui.Project_species_lineEdit.textChanged.connect(self.set_project_species)
        #
        # self.ui.Project_openDLCFiles_pushButton.pressed.connect(self.choose_DLC_folder)
        # self.ui.Project_confirmNew_pushButton.pressed.connect(self.confirmNew)
        #
        # self.ui.Project_openConfig_pushButton.pressed.connect(self.choose_Existing_Project)
        # self.ui.Project_confirm_pushButton.pressed.connect(self.confirmExistingProject)
        #
        # self.ui.Animal_lizard_pushButton.pressed.connect(self.select_Lizard)
        # self.ui.Animal_spider_pushButton.pressed.connect(self.select_Spider)
        # self.ui.Animal_ant_pushButton.pressed.connect(self.select_Ant)
        # self.ui.Animal_stick_pushButton.pressed.connect(self.select_Stick)
        #
        # self.ui.letsGo_pushButton.pressed.connect(self.start_analysis)

    """
    set user input values:
    """
    def set_timing_variables(self):
        self.sample_frequency = self.ui.lineEdit_SampleFreq.text()
        self.buffer_size = self.ui.lineEdit_BufferSize.text()
        self.post_trigger_samples = self.ui.lineEdit_PostTriggerSamples.text()

    def set_units(self):
        self.force_units = self.ui.comboBox_ForceUnits.currentText()
        self.torque_units = self.ui.comboBox_TorqueUnits.currentText()

    def get_channel_params(self):
        self.device_number = self.ui.comboBox_DAQCard.currentText()
        self.first_channel = self.ui.lineEdit_ChannelFirst.text()

    def open_calib_file_threaded(self, progress_callback):
        root = Tk()
        root.withdraw()  # use to hide tkinter window

        current_path = os.getcwd()
        self.set_units()

        if self.ui.lineEdit_OpenCalib.text is not None:
            current_path = self.calib_file

        selected_path = filedialog.askopenfilename(parent=root, initialdir=current_path,
                                                   filetypes=[("calibration files", "*.cal; *.txt")],
                                                   title='Please select the calibration file for the forceplate')
        if len(selected_path) > 0:
            self.calib_file = selected_path
            self.log_info("opened calibration file at: \n" + self.calib_file)

        root.destroy()

        # overwrites force and torque units with calib file units if user chose 'None'
        self.calibration_matrix, self.force_units, self.torque_units, self.number_of_gages = calibration(
            self.calib_file, self.force_units, self.torque_units)

    def open_calib_file(self):
        worker = Worker(self.open_calib_file_threaded)
        self.threadpool.start(worker)

        self.ui.lineEdit_OpenCalib.setText(self.calib_file)
        # read calibration file and calibrate

        self.log_info("\nforce units: " + self.force_units +
                      "\ntorque units: " + self.torque_units)

        # enable record button:
        self.ui.pushButton_Record.setEnabled(True)


    """
    RECORDING FORCES/TORQUES
    """

    def record_forces_threaded(self, progress_callback):
        """
        activated when engaging the RECORD button. Will continuously record data until Stopped/triggered.
        :return:
        """
        self.set_timing_variables()

        with nidaqmx.Task() as task:
            for i in range(int(self.number_of_gages)):
                first_channel = int(self.first_channel)
                channel = self.device_number + "/" + "ai" + str(first_channel+i)
                print(channel)
                task.ai_channels.add_ai_voltage_chan(self.device_number + "/" + "ai" + str(int(self.first_channel)+i),
                                                 min_val=-10, max_val=10)

            # task.ai_channels.add_ai_voltage_chan(self.device_number + "/" + "ai" + self.first_channel + ":" + self.number_of_gages,
            #                                      min_val=-10, max_val=10)

            task.timing.cfg_samp_clk_timing(rate=float(self.sample_frequency), samps_per_chan=int(self.buffer_size),
                                            sample_mode=constants.AcquisitionType.FINITE)

            data = task.read(number_of_samples_per_channel=int(self.buffer_size))
            data = np.array(data)
            print("data in voltage: ", data)

            # calibrate data:
            data_calib = self.calibration_matrix.dot(data)      # TODO: debug
            print("data in hopefully N: ", data_calib)


    def record_forces(self):
        print("pressed")
        worker = Worker(self.record_forces_threaded)
        self.threadpool.start(worker)


    """
    INFO LOGS:
    """
    def log_info(self, info):
        now = datetime.datetime.now()
        # TODO add item colour (red for warnings)
        self.ui.listWidget_info.addItem(now.strftime("%H:%M:%S") + " [INFO]  " + info)
        self.ui.listWidget_info.sortItems(QtCore.Qt.DescendingOrder)

    def log_warning(self, info):
        now = datetime.datetime.now()
        self.ui.listWidget_info.addItem(now.strftime("%H:%M:%S") + " [WARNING]  " + info)
        self.ui.listWidget_info.sortItems(QtCore.Qt.DescendingOrder)



app = QtWidgets.QApplication([])

application = nidaqmx_gui_mainWindow()

application.show()

sys.exit(app.exec())