from PCANBasic import *
import os
import sys
import time
import random
import cantools
import traceback
import threading
from DBC_BaseOperator import DBC_BaseOperator

power = r'C:\Users\M0194858\Desktop\Automation_Case_Executor\automated_test_executor'
sys.path.append(power)
import LV_Power_Supply_Control

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.Qt import *
from PyQt5.QtCore import *

class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:
    finished:  No data
    error:     `tuple` (exctype, value, traceback.format_exc() )
    result:    `object` data returned from processing, anything
    terminate: No data
    """
    finished  = pyqtSignal()
    error     = pyqtSignal(tuple)
    result    = pyqtSignal(object)
    terminate = pyqtSignal()

class Sender(QRunnable):
    """
    Worker thread responsible for sending messages.

    Args:
    method (function): The method to be executed by the thread.
    message (object): The message object containing cycle time and other properties.
    counter (int): A counter to track the number of sends.
    """
    def __init__(self, method, message, counter):
        super().__init__()
        self.signals    = WorkerSignals()  # Signals to communicate with the main thread
        self.cycle_time   = float(message.cycle_time)/1000  # Cycle time in seconds
        self.method       = method  # Method to be executed
        self._message     = message  # Message object
        self.counter      = counter  # Counter to track the number of sends
        self.send_running = True  # Flag to control thread execution

    @property
    def message(self):
        """Getter for the message property."""
        return self._message

    @message.setter
    def message(self, value):
        """Setter for the message property."""
        self._message = value
        # self.message_changed.emit(value)

    def run(self):
        """
        Runs the thread. Executes the method in a loop with a delay of cycle_time.
        Stops execution when send_running is set to False.
        """
        # print(self._message.name, ' start_send ', self.counter)
        try:
            while self.send_running:
                if not self.send_running:
                    self.signals.finished.emit()
                    break
                else:
                    self.method(self._message)  # Execute the method
                    time.sleep(self.cycle_time)  # Simulate work with a delay
            else:
                pass
                # print(f'{self._message.name} Sender stopped')
        except Exception as e:
            traceback_info = traceback.format_exc()
            print('Catch Error', traceback_info)

    def stop(self):
        """Stops the thread execution by setting send_running to False."""
        self.send_running = False

class Reader(QRunnable):
    """
    Worker thread responsible for reading data.

    Args:
    method (function): The method to be executed by the thread.
    """
    def __init__(self, method):
        super().__init__()
        self.signals    = WorkerSignals()  # Signals to communicate with the main thread
        self.method     = method  # Method to be executed
        self.read_running = True  # Flag to control thread execution

    def run(self):
        """
        Runs the thread. Executes the method in a loop.
        Stops execution when read_running is set to False.
        """
        try:
            while self.read_running:
                if not self.read_running:
                    self.signals.finished.emit()
                    break
                else:
                    self.method()  # Execute the method

        except Exception as e:
            self.signals.error.emit((type(e), e.args, traceback.format_exc()))


    def stop(self):
        """Stops the thread execution by setting read_running to False."""
        self.read_running = False

class CANProc():
    # Sets the PCANHandle (Hardware Channel)
    PcanHandle = PCAN_USBBUS1

    # Shows if DLL was found
    m_DLLFound = False

    def __init__(self, dbc_name):
        self.is_init_OK = False
        self.dbc_name = dbc_name

        self.stop_read = False
        self.TracePath = b'Traces'

        self.init_dbc()

        self.receive_msgs_id_list = list(msg.frame_id for msg in self.dbc.receive_messages.values())
        # Checks if PCANBasic.dll is available, if not, the program terminates
        try:
            self.m_objPCANBasic = PCANBasic()
            self.m_DLLFound = True
        except :
            print("Unable to find the library: PCANBasic.dll !")
            self.m_DLLFound = False
            self.is_init_OK = False

        ## Initialization of the selected channel
        if self.IsFD:
            stsResult = self.m_objPCANBasic.InitializeFD(self.PcanHandle,self.BitrateFD)
        else:
            stsResult = self.m_objPCANBasic.Initialize(self.PcanHandle,self.Bitrate)

        # if stsResult != PCAN_ERROR_OK:
        #     print("Can not initialize. Please check the defines in the code.")
        #     self.is_init_OK = False
        self.is_init_OK = True

        self.msgs = set()

        self.threadpool_send = QThreadPool()
        self.threadpool_read = QThreadPool()

        # Init msg data dict to store data
        self.msg_id_data_dict   = {}
        self.msg_name_data_dict = {}

        self.send_msgs_periodic()
        self.read_msgs_periodic()
    
    
    def config_trace(self, log_folders):
        # Init periodiclly send msgs, read msgs, and trace logs
        print(log_folders)
        self.TracePath = log_folders.encode()
        self.start_trace()
        

    def init_dbc(self):
        # According to input msg to config dbc
        if self.dbc_name == 'BEV_E0X_CDU':
            dbc_file = 'DBC_Files/BEV_E0X_OT_Car_V4_100_R1.dbc'
            dbc_file = 'can_control/DBC_Files/BEV_E0X_OT_Car_V4_100_R1.dbc'
            self.dbc = DBC_BaseOperator(dbc_file)
            self.init_CANFD()
        elif self.dbc_name == 'Int_CAN':
            dbc_file = 'DBC_Files/Internal_Can_20240419.dbc'
            dbc_file = 'can_control/DBC_Files/Internal_Can_20240419.dbc'
            self.dbc = DBC_BaseOperator(dbc_file)
            self.init_CAN()


    def init_CANFD(self):
        # Sets the desired connection mode (CAN = false / CAN-FD = true)
        self.IsFD = True

        # Sets the bitrate for CAN devices. 
        # Example - Bitrate Nom: 500bit/s Data: 2Mbit/s:
        # self.BitrateFD = b'f_clock_mhz=20, nom_brp=5, nom_tseg1=5, nom_tseg2=2, nom_sjw=1, data_brp=2, data_tseg1=3, data_tseg2=1, data_sjw=1'
        self.BitrateFD = b'f_clock_mhz=80, nom_brp=2, nom_tseg1=63, nom_tseg2=16, nom_sjw=16, data_brp=2, data_tseg1=13, data_tseg2=6, data_sjw=6'

    def init_CAN(self):
        # Sets the desired connection mode (CAN = false / CAN-FD = true)
        self.IsFD = False

        # Sets the bitrate for normal CAN devices
        self.Bitrate = PCAN_BAUD_1000K


    def get_dlc_from_length(self, length):
        """
        Gets the data length of a CAN message

        Parameters:
            dlc = Data length code of a CAN message

        Returns:
            Data length as integer represented by the given DLC code
        """
        CAN_FD_DLC = [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64]
        if length <= 8:
            return length
        for dlc, nof_bytes in enumerate(CAN_FD_DLC):
            if nof_bytes >= length:
                return dlc
        dlc = 15
        return dlc


    #==========================Read Messages and Signals =================================================================
    def read_msgs_periodic(self):
        # Init periodiclly read msgs
        self.msg_reader = Reader(self.read_all_messages)
        self.threadpool_read.start(self.msg_reader)
        # self.read_all_messages()
        # print(f"Active Read Threads: {self.threadpool_read.activeThreadCount()}")

    def read_all_messages(self):
        """
        Reads all messages periodically if initialization is successful.
        """
        if self.is_init_OK:
            while not self.stop_read:
                stsResult = PCAN_ERROR_OK
                if self.IsFD:
                    stsResult = self.m_objPCANBasic.ReadFD(self.PcanHandle)
                    msg = stsResult[1]
                else:
                    stsResult = self.m_objPCANBasic.Read(self.PcanHandle)
                    msg = stsResult[1]

                if msg.ID in self.receive_msgs_id_list:
                    message = self.dbc.get_message_by_ID(msg.ID)
                    if int(hex(msg.ID), 16) == 0x7BD:
                        diag_msg = bytes(msg.DATA).hex().upper().rstrip('0')
                        # print("diag_msg: ", diag_msg)
                        # phase_DTC = {}

                        if len(diag_msg) > 16:
                            # Multi Frame Process
                            phase_DTC = self.proc_diag_multi_frame(diag_msg)
                        else:
                            # Single Frame Process
                            phase_DTC = self.proc_diag_single_frame(diag_msg)

                        self.msg_id_data_dict[msg.ID] = phase_DTC
                        self.msg_name_data_dict[message.name] = phase_DTC
                    else:
                        decoded_signal = message.decode(msg.DATA)
                        self.msg_id_data_dict[message.frame_id] = decoded_signal
                        self.msg_name_data_dict[message.name] = decoded_signal

    def proc_diag_multi_frame(self, diag_msg):
        """
        Processes multi-frame diagnostic messages.

        Args:
            diag_msg (str): The diagnostic message in hexadecimal format.

        Returns:
            dict: A dictionary containing the processed diagnostic information.
        """
        # Multi Frame Process
        # In multi-frame, diag_msg[0:2] is the first frame,
        # diag_msg[2:4] is the length of the multi-frame,
        # diag_msg[4:6] is the response of SID.
        if diag_msg[4:6] == '59':  # and diag_msg[6:8] == '02'
            phase_DTC = {}
            # SID 19 response
            phase_DTC['DTC_Length'] = diag_msg[2:4]
            phase_DTC['SID_19'] = f'{diag_msg[4:6]}{diag_msg[6:8]}'
            DTC_Code_Status_map = {}
            DTC_start_bit = 10
            while self.msg_reader.read_running and (DTC_start_bit < len(diag_msg)):
                if diag_msg[DTC_start_bit + 6:DTC_start_bit + 8] == '2F' or \
                diag_msg[DTC_start_bit + 6:DTC_start_bit + 8] == '2E':
                    DTC_Code_Status_map[diag_msg[DTC_start_bit:DTC_start_bit + 6]] = diag_msg[DTC_start_bit + 6:DTC_start_bit + 8]
                DTC_start_bit += 8
            phase_DTC['DTC_Code'] = DTC_Code_Status_map
            phase_DTC['DTC_Status'] = DTC_Code_Status_map
            return phase_DTC

        elif diag_msg[4:6] == '62':
            convert_version = lambda version: '.'.join(chr(int(version[i:i+2], 16)) for i in range(0, len(version), 2))
            # SID 22 response
            if diag_msg[6:10] == 'F189':
                DCDC_SW_version = diag_msg[10:14]
                OBC_SW_version  = diag_msg[16:20]
                SUP_SW_version  = diag_msg[22:26]
                SW_Version = {
                    "DCDC_SW_version": convert_version(DCDC_SW_version),
                    "OBC_SW_version": convert_version(OBC_SW_version),
                    "SUP_SW_version": convert_version(SUP_SW_version)
                }
                return SW_Version

            elif diag_msg[6:10] == "F089":
                DCDC_HW_version = diag_msg[10:12]
                OBC_HW_version  = diag_msg[14:16]
                SUP_HW_version  = diag_msg[18:20]
                HW_Version = {
                    "DCDC_HW_version": convert_version(DCDC_HW_version),
                    "OBC_HW_version" : convert_version(OBC_HW_version),
                    "SUP_HW_version" : convert_version(SUP_HW_version)
                }
                return HW_Version
            

    def proc_diag_single_frame(self, diag_msg):
        """
        Processes single-frame diagnostic messages.

        Args:
            diag_msg (str): The diagnostic message in hexadecimal format.

        Returns:
            dict: A dictionary containing the processed diagnostic information.
        """
        phase_DTC = {}
        # Single Frame Process
        # 1. Judge Response Type
        # Negative response
        if diag_msg[2:4] == '7F':
            phase_DTC['DTC_Length'] = diag_msg[0:2]
            if diag_msg[4:6] == '14':  # 14 service
                phase_DTC['SID_14'] = f'{diag_msg[2:4]} {diag_msg[4:6]} {diag_msg[6:8]}'
            else:  # 19 service
                phase_DTC['SID_19'] = f'{diag_msg[2:4]} {diag_msg[4:6]} {diag_msg[6:8]}'
        # Positive response
        else:
            if diag_msg[0:2] == "00":
                # 19 Service Response
                phase_DTC['DTC_Length'] = diag_msg[2:4]

                if diag_msg[4:6] == '59':  # 19 service positive response
                    phase_DTC['SID_19'] = f'{diag_msg[4:6]}{diag_msg[6:8]}'
                    DTC_start_bit = 8
                    DTC_Code_Status_map = {}
                    DTC_Code_Status_map[diag_msg[DTC_start_bit:DTC_start_bit + 6]] = diag_msg[DTC_start_bit + 6:DTC_start_bit + 8]
                    phase_DTC['DTC_Code'] = DTC_Code_Status_map
                    phase_DTC['DTC_Status'] = DTC_Code_Status_map
            else:
                # 14 Service Response
                phase_DTC['DTC_Length'] = diag_msg[0:2]
                if diag_msg[2:4] == '54':  # 14 service positive response
                    phase_DTC['SID_14'] = diag_msg[2:4]
        return phase_DTC

                
    def read_message(self, message_name):
        decoded_signal = self.msg_name_data_dict[message_name]
        return decoded_signal


    def read_signal(self, signal_name):
        signal         = self.dbc.signals[signal_name]
        decoded_signal = self.read_message(signal.parent_msg)
        actual_value   = decoded_signal[signal_name]
        return actual_value

    def read_diag_msg(self):
        diag_msg_name  = 'Diag_CDU_RES'
        diag_msg_value = self.msg_name_data_dict[diag_msg_name]
        # print(diag_msg_value)
        return diag_msg_value


    #====================Cycle Time Write Messages and Signals=================
    def write_signal(self, signal_name, value):
        # print('orignal value: ', value)
        signal = self.dbc.signals[signal_name]
        message = self.dbc.get_message_by_name(signal.parent_msg)
        if signal.choices != None:
            for choice, state in signal.choices.items():
                if '.' in str(state):
                    # process special string like: "CP signal is abnormal."
                    proc_state = str(state).replace('.', '')
                    if value in proc_state:
                        value = str(state)
        message.signal_values[signal_name] = value

        
    def write_message(self, message):
        self.dbc.update_rolling_counter(message)
        self.dbc.update_crc(message)

        data = message.encode(message.signal_values)

        if self.is_init_OK:
            stsResult = PCAN_ERROR_OK
            if message.is_fd:
                msgCanMessageFD         = TPCANMsgFD()
                msgCanMessageFD.ID      = int(hex(message.frame_id), 16)
                msgCanMessageFD.DLC     = self.get_dlc_from_length(message.length)
                msgCanMessageFD.MSGTYPE = PCAN_MESSAGE_FD.value | PCAN_MESSAGE_BRS.value
                for i in range(message.length):
                    msgCanMessageFD.DATA[i] = data[i]
                self.m_objPCANBasic.WriteFD(self.PcanHandle, msgCanMessageFD)
            else:
                msgCanMessage         = TPCANMsg()
                msgCanMessage.ID      = int(hex(message.frame_id), 16)
                msgCanMessage.LEN     = self.get_dlc_from_length(message.length)
                msgCanMessage.MSGTYPE = PCAN_MESSAGE_EXTENDED.value
                for i in range(8):
                    msgCanMessage.DATA[i] = data[i]
                self.m_objPCANBasic.Write(self.PcanHandle, msgCanMessage)
        else:
            print('Error Write')


    def send_msgs_periodic(self):
        self.msgs_sender = {}
        self.counter = 1
        for message_name, message_obj in self.dbc.send_messages.items():
            data   = message_obj.encode(message_obj.signal_values)
            sender = Sender(self.write_message, message_obj, self.counter)
            self.threadpool_send.start(sender)
            time.sleep(0.001)

            self.msgs_sender[message_name] = sender

            self.counter += 1
        # print(f"Active Send Threads: {self.threadpool_send.activeThreadCount()}")


    # Stop Thread and Reset Write
    def reset_msgs(self):
        for message_name, message_obj in self.dbc.send_messages.items():
            self.dbc.init_msg_signal_values(message_obj)
            # if message_obj.name == 'EVCC_1':
            #     print(message_obj.signal_values)
    
    def send_diagnostic_signal(self, service_ID):
        diag_data = self.dbc.diag_signals[service_ID]
        if self.is_init_OK:
            stsResult = PCAN_ERROR_OK
            msgCanMessageFD     = TPCANMsgFD()
            msgCanMessageFD.ID  = 0x73D
            msgCanMessageFD.DLC = 8
            msgCanMessageFD.MSGTYPE = PCAN_MESSAGE_FD.value | PCAN_MESSAGE_BRS.value
            for i in range(len(diag_data)):
                msgCanMessageFD.DATA[i] = diag_data[i]
            self.m_objPCANBasic.WriteFD(self.PcanHandle, msgCanMessageFD)


    # ===============================Stop and Reset===========================
    # Stop CAN Porc
    def stop_CAN_Proc(self):
        try:
            self.reset_msgs()
            time.sleep(1)   

            self.stop_msgs_send()
            self.stop_msgs_read()
        except Exception as e:
            print(f"解析诊断消息失败: {str(e)}", "error")


    def stop_msgs_send(self):
        try:
            if self.msgs_sender:
                for message_name, msg_sender in self.msgs_sender.items():
                    msg_sender.stop()
                    msg_sender = None

                self.msgs_sender.clear()
                self.msgs_sender = None
                if self.threadpool_send.activeThreadCount() > 0:
                    self.threadpool_send.waitForDone()
                else:
                    self.threadpool_send = None
        except Exception as e:
            print(f"stop_msgs_send: {str(e)}", "error")

        # print(f"After Stop, Active Send Threads: {self.threadpool_send.activeThreadCount()}")
    
    def stop_msgs_read(self):
        self.stop_read = True

        if self.msg_reader:
            self.msg_reader.stop()
            self.msg_reader = None
        # self.threadpool_read.waitForDone()
        
        # print(f"After Stop, Active Read Threads: {self.threadpool_read.activeThreadCount()}")
        


    def get_SW_HW_version(self):
        self.send_diagnostic_signal('22_SW')
        time.sleep(0.1)
        SW_version = self.read_diag_msg()
        time.sleep(1)

        self.send_diagnostic_signal('22_HW')
        time.sleep(0.1)
        HW_version = self.read_diag_msg()
        time.sleep(0.1)
        self.stop_CAN_Proc()

        return SW_version, HW_version


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('CAN 通信控制器')
        self.setGeometry(200, 200, 800, 600)
        
        # 初始化UI组件
        self.init_ui()
        
        # 初始化状态
        self.can_proc = None
        self.count = 0
        self.current_mode = "停止"
        
        # 应用样式
        self.apply_styles()

    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout()
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("就绪 | 状态: 停止")
        main_layout.addWidget(self.status_bar)
        
        # 主分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 控制面板
        control_panel = QWidget()
        control_layout = QGridLayout()
        
        # 基础控制按钮
        self.start_button = self.create_button('启动 CAN', self.start_can, "#4CAF50")
        self.stop_button = self.create_button('停止 CAN', self.stop_send, "#F44336")
        self.modify_button = self.create_button('修改信号', self.modify_signal, "#2196F3")
        self.read_button = self.create_button('读取信号', self.read_signal, "#009688")
        
        # 充电控制按钮组
        charge_group = QGroupBox("充放电控制")
        charge_layout = QGridLayout()
        
        self.three_phase_charge_button = self.create_button('三相充电', self.three_phase_charge, "#673AB7")
        self.single_phase_charge_button = self.create_button('单相充电', self.single_phase_charge, "#3F51B5")
        self.single_phase_discharge_button = self.create_button('单相放电', self.single_phase_discharge, "#FF5722")
        self.elock_button = self.create_button('电子锁状态', self.change_elock, "#607D8B")
        
        charge_layout.addWidget(self.three_phase_charge_button, 0, 0)
        charge_layout.addWidget(self.single_phase_charge_button, 0, 1)
        charge_layout.addWidget(self.single_phase_discharge_button, 1, 0)
        charge_layout.addWidget(self.elock_button, 1, 1)
        charge_group.setLayout(charge_layout)
        
        # 诊断控制按钮组
        diag_group = QGroupBox("诊断控制")
        diag_layout = QGridLayout()
        
        self.SID_14 = self.create_button('SID_14', self.send_SID_14, "#795548")
        self.SID_19 = self.create_button('SID_19', self.send_SID_19, "#795548")
        self.SID_22_SW = self.create_button('SID_22_SW', self.send_SID_22_SW, "#795548")
        self.SID_22_HW = self.create_button('SID_22_HW', self.send_SID_22_HW, "#795548")
        self.read_diag = self.create_button('读取诊断', self.parse_diag_msg, "#795548")
        
        diag_layout.addWidget(self.SID_14, 0, 0)
        diag_layout.addWidget(self.SID_19, 0, 1)
        diag_layout.addWidget(self.SID_22_SW, 1, 0)
        diag_layout.addWidget(self.SID_22_HW, 1, 1)
        diag_layout.addWidget(self.read_diag, 2, 0, 1, 2)
        diag_group.setLayout(diag_layout)
        
        # 测试按钮
        self.other_button = self.create_button('测试诊断', self.test_diag, "#E91E63")
        
        # 添加到控制布局
        control_layout.addWidget(self.start_button, 0, 0)
        control_layout.addWidget(self.stop_button, 0, 1)
        control_layout.addWidget(self.modify_button, 1, 0)
        control_layout.addWidget(self.read_button, 1, 1)
        control_layout.addWidget(charge_group, 2, 0, 1, 2)
        control_layout.addWidget(diag_group, 0, 2, 2, 1)
        control_layout.addWidget(self.other_button, 2, 2)
        
        control_panel.setLayout(control_layout)
        
        # 日志区域
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 10pt;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
            }
        """)
        
        # 添加到分割器
        splitter.addWidget(control_panel)
        splitter.addWidget(self.log_area)
        splitter.setSizes([300, 300])
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def create_button(self, text, callback, color):
        """创建带样式的按钮"""
        button = QPushButton(text)
        button.clicked.connect(callback)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 8px;
                min-height: 30px;
            }}
            QPushButton:hover {{
                background-color: {self.darker_color(color)};
            }}
            QPushButton:disabled {{
                background-color: #BDBDBD;
            }}
        """)
        return button

    def darker_color(self, hex_color, factor=0.7):
        """生成更深的颜色"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = max(0, int(r * factor))
        g = max(0, int(g * factor))
        b = max(0, int(b * factor))
        
        return f"#{r:02x}{g:02x}{b:02x}"

    def apply_styles(self):
        """应用全局样式"""
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F5F5;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #BDBDBD;
                border-radius: 5px;
                margin-top: 1ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QStatusBar {
                background-color: #E0E0E0;
                border-top: 1px solid #BDBDBD;
            }
        """)
        
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(240, 240, 240))
        self.setPalette(palette)

    def log_message(self, message, level="info"):
        """记录消息到日志区域"""
        if level == "error":
            color = "#FF5252"  # 红色
            prefix = "[错误] "
        elif level == "warning":
            color = "#FFC107"  # 黄色
            prefix = "[警告] "
        elif level == "success":
            color = "#4CAF50"  # 绿色
            prefix = "[成功] "
        else:
            color = "#2196F3"  # 蓝色
            prefix = "[信息] "
        
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        formatted_message = f'<font color="#9E9E9E">[{timestamp}]</font> <font color="{color}">{prefix}{message}</font>'
        
        self.log_area.appendHtml(formatted_message)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def update_status(self, message):
        """更新状态栏消息"""
        self.status_bar.showMessage(f"{message} | 当前模式: {self.current_mode}")

    def start_can(self):
        """启动CAN通信"""
        try:
            self.log_message("启动电源控制...")
            LV_Power_Supply_Control.main()
            
            dbc_name = 'BEV_E0X_CDU'
            self.log_message(f"初始化CAN通信 (DBC: {dbc_name})...")
            self.can_proc = CANProc(dbc_name)
            
            if self.can_proc.is_init_OK:
                self.log_message("CAN通信初始化成功", "success")
                self.update_status("CAN通信已启动")
                self.current_mode = "待机"
            else:
                self.log_message("CAN通信初始化失败", "error")
                self.update_status("初始化失败")
        except Exception as e:
            self.log_message(f"启动CAN时发生错误: {str(e)}", "error")
            self.update_status("错误")

    def stop_send(self):
        """停止CAN通信"""
        if not hasattr(self, 'can_proc') or self.can_proc is None:
            self.log_message("CAN通信尚未启动", "warning")
            return
            
        try:
            self.log_message("正在停止CAN通信...")
            self.can_proc.stop_CAN_Proc()
            self.log_message("CAN通信已停止", "success")
            self.update_status("已停止")
            self.current_mode = "停止"
        except Exception as e:
            self.log_message(f"停止CAN时发生错误: {str(e)}", "error")

    def modify_signal(self):
        """修改随机信号"""
        if not self.can_proc:
            self.log_message("CAN通信尚未启动", "warning")
            return
        
        signal_list = ['VCU_OBCChgCurrentReq', 'VCU_OBCChgVoltageReq', 'VCU_OBCDischgPwrLimit']
        signal_name = random.choice(signal_list)
        value = random.randint(10, 20)
        
        self.log_message(f"修改信号: {signal_name} = {value}")
        self.can_proc.write_signal(signal_name, value)

    def three_phase_charge(self):
        """三相充电模式"""
        if not self.can_proc:
            self.log_message("CAN通信尚未启动", "warning")
            return
        
        signal_value_dict = {
            'EVCC_GunConnectSt'     : 'Connect',
            'EVCC_CC_ConnectSts'    : 'Connected',
            'EVCC_CP_DutyCycleValue': 85,
            'EVCC_CPSts'            : 'CP is 9V PWM',
            'EVCC_CC_RCR4_Sts'      : 680,
            'EVCC_CPMaxVolt'        : 9,
            'EVCC_ElectronicLockSts': 'Lock',
            'VCU_BMSAcChrgPerm'     : 'Allow',
            'EVCC_S2Swtsts'         : 'close',
            'EVCC_CPMaxVolt'        : 6,
            'VCU_OBCChgVoltageReq'  : 750,
            'VCU_OBCChgCurrentReq'  : 16.3,
        }
        
        for signal_name, value in signal_value_dict.items():
            self.can_proc.write_signal(signal_name, value)
            self.log_message(f"设置信号: {signal_name} = {value}")
        
        self.current_mode = "三相充电"
        self.update_status(f"已切换到{self.current_mode}模式")
        self.log_message("已配置为三相充电模式", "success")

    def single_phase_charge(self):
        """单相充电模式"""
        if not self.can_proc:
            self.log_message("CAN通信尚未启动", "warning")
            return
        
        signal_value_dict = {
            'EVCC_GunConnectSt'     : 'Connect',
            'EVCC_CC_ConnectSts'    : 'Connected',
            'EVCC_CP_DutyCycleValue': 85,
            'EVCC_CPSts'            : 'CP is 9V PWM',
            'EVCC_CC_RCR4_Sts'      : 220,
            'EVCC_CPMaxVolt'        : 9,
            'EVCC_ElectronicLockSts': 'Lock',
            'VCU_BMSAcChrgPerm'     : 'Allow',
            'EVCC_S2Swtsts'         : 'close',
            'EVCC_CPMaxVolt'        : 6,
            'VCU_OBCChgVoltageReq'  : 450,
            'VCU_OBCChgCurrentReq'  : 16.3,
        }
        
        for signal_name, value in signal_value_dict.items():
            self.can_proc.write_signal(signal_name, value)
            self.log_message(f"设置信号: {signal_name} = {value}")
        
        self.current_mode = "单相充电"
        self.update_status(f"已切换到{self.current_mode}模式")
        self.log_message("已配置为单相充电模式", "success")

    def single_phase_discharge(self):
        """单相放电模式"""
        if not self.can_proc:
            self.log_message("CAN通信尚未启动", "warning")
            return
        
        signal_value_dict = {
            'EVCC_GunConnectSt': 'Connect',
            'EVCC_CC_ConnectDischarSts': 'Connected',
            'EVCC_ElectronicLockSts': 'Lock',
            'EVCC_CC_RCR4_Sts': 350,
            'VCU_OBCDischgReq': 'Req',
            'VCU_OBCDischgPwrLimit': 6,
        }
        
        for signal_name, value in signal_value_dict.items():
            self.can_proc.write_signal(signal_name, value)
            self.log_message(f"设置信号: {signal_name} = {value}")
        
        self.current_mode = "单相放电"
        self.update_status(f"已切换到{self.current_mode}模式")
        self.log_message("已配置为单相放电模式", "success")

    def change_elock(self):
        """切换电子锁状态"""
        if not self.can_proc:
            self.log_message("CAN通信尚未启动", "warning")
            return
        
        signal_name = 'EVCC_ElectronicLockSts'
        if self.count % 3 == 0:
            value = 'Lock'
        elif self.count % 3 == 1:
            value = 'Unlock'
        else:
            value = 'Error'
        
        self.count += 1
        
        self.can_proc.write_signal(signal_name, value)
        self.log_message(f"设置电子锁状态: {value}")
        self.status_bar.showMessage(f"电子锁状态: {value}")

    def read_signal(self):
        """读取随机信号"""
        if not self.can_proc:
            self.log_message("CAN通信尚未启动", "warning")
            return
        
        signal_list = ['OBC_CC_ConnectSts', 'OBC_CCResisdent', 
                       'OBC_CPLineSts', 'OBC_CP_DutyCycleValue', 'OBC_CPMaxVolt', 'OBC_ElectronicLockSts']

        
        self.log_message("读取信号值:")
        for signal_name in signal_list:
            try:
                actual_value = self.can_proc.read_signal(signal_name)
                self.log_message(f"  {signal_name} = {actual_value}")
            except Exception as e:
                self.log_message(f"读取信号失败: {signal_name} - {str(e)}", "error")

    def send_SID_14(self):
        """发送SID 14诊断请求"""
        if not self.can_proc:
            self.log_message("CAN通信尚未启动", "warning")
            return
            
        self.log_message("发送SID 14诊断请求...")
        self.can_proc.send_diagnostic_signal('14')
        time.sleep(1)
        self.parse_diag_msg()

    def send_SID_19(self):
        """发送SID 19诊断请求"""
        if not self.can_proc:
            self.log_message("CAN通信尚未启动", "warning")
            return
            
        self.log_message("发送SID 19诊断请求...")
        self.can_proc.send_diagnostic_signal('19')
        time.sleep(1)
        self.parse_diag_msg()

    def send_SID_22_SW(self):
        """发送SID 22软件版本请求"""
        if not self.can_proc:
            self.log_message("CAN通信尚未启动", "warning")
            return
            
        self.log_message("发送SID 22软件版本请求...")
        self.can_proc.send_diagnostic_signal('22_SW')
        time.sleep(0.5)
        self.log_message(f"软件版本: {self.can_proc.read_diag_msg()}")

    def send_SID_22_HW(self):
        """发送SID 22硬件版本请求"""
        if not self.can_proc:
            self.log_message("CAN通信尚未启动", "warning")
            return
            
        self.log_message("发送SID 22硬件版本请求...")
        self.can_proc.send_diagnostic_signal('22_HW')
        time.sleep(0.5)
        self.log_message(f"硬件版本: {self.can_proc.read_diag_msg()}")

    def parse_diag_msg(self):
        """解析诊断消息"""
        if not self.can_proc:
            self.log_message("CAN通信尚未启动", "warning")
            return
            
        try:
            diag_data = self.can_proc.read_diag_msg()
            self.log_message("诊断消息详情:", "success")
            for key, value in diag_data.items():
                self.log_message(f"  {key}: {value}")
        except Exception as e:
            self.log_message(f"解析诊断消息失败: {str(e)}", "error")

    def test_diag(self):
        """测试诊断功能"""
        self.log_message("启动诊断测试...")
        self.start_can()
        time.sleep(0.1)
        
        try:
            self.log_message("获取软件和硬件版本...")
            SW_version, HW_version = self.can_proc.get_SW_HW_version()
            self.log_message(f"软件版本: {SW_version}", "success")
            self.log_message(f"硬件版本: {HW_version}", "success")
        except Exception as e:
            self.log_message(f"诊断测试失败: {str(e)}", "error")
        finally:
            self.stop_send()

    def closeEvent(self, event):
        """关闭窗口事件处理"""
        try:
            if hasattr(self, 'can_proc') and self.can_proc:
                self.log_message("正在清理资源...")
                self.can_proc.stop_CAN_Proc()
                self.log_message("资源清理完成", "success")
        except Exception as e:
            self.log_message(f"资源清理时发生错误: {str(e)}", "error")
        
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 设置默认字体
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())