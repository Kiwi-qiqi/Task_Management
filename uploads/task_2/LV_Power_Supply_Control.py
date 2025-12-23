
import sys
import glob
import serial
import traceback
import serial.tools.list_ports


# Creat class for data storage
class DataContainer():
    def __init__(self, _PV=0.0, _PC=0.0, _MV=0.0, _MC=0.0, _POVP=0.0, _PUVL=0.0,
                       _SRCV=False,_SRCC=False, _SRNFLT=True, _SRFLT=False, _SRAST=False, _SRFDE=False, _SRLCL=False,
                       _FRAC=False, _FROTP=False, _FRFOLD=False, _FROVP=False, _FRSO=False, _FROFF=False, _FRENA=False,
                       _OUTPUT=False,
                       _DeviceIDN = "", _DeviceREV = "", _DeviceSN = "", _DeviceDATE = ""):
        self.PV = _PV         #Programmed Voltage
        self.PC = _PC         #Programmed Current
        self.MV = _MV         #Measured Voltage
        self.MC = _MC         #Measured Current
        self.POVP = _POVP     #Programmed Overvoltage Protection
        self.PUVL = _PUVL     #Programmed Untervoltage Protection
        self.SRCV = _SRCV     #Status Register Constant Voltage
        self.SRCC = _SRCC     #Status Register Constant Current
        self.SRNFLT = _SRNFLT #Status Register No Fault
        self.SRFLT = _SRFLT   #Status Register Fault
        self.SRAST = _SRAST   #Status Register Auto Start
        self.SRFDE = _SRFDE   #Status Register Fold Back Enabled
        self.SRLCL = _SRLCL   #Status Register Local Mode Enabled
        self.FRAC = _FRAC     #Fault Register AC Fail
        self.FROTP = _FROTP   #Fault Register Over Temperature
        self.FRFOLD = _FRFOLD #Fault Register Foldback 
        self.FROVP = _FROVP   #Fault Register Overvoltage
        self.FRSO = _FRSO     #Fault Register Shut OFF
        self.FROFF = _FROFF   #Fault Register Output Off
        self.FRENA = _FRENA   #Fault Register Enable
        self.OUTPUT = _OUTPUT #Status Output (True=ON, False=OFF)
        self.DeviceIDN  = _DeviceIDN
        self.DeviceREV   = _DeviceREV
        self.DeviceSN   = _DeviceSN
        self.DeviceDATE = _DeviceDATE
        
    @property
    def MP(self):
        return self.MV * self.MC
        
    @property
    def minPOVP(self):
        value = self.PV/100 * 105
        if value < 5.00:
            return 5.00
        else:
            return round(value, 2)# + 0.05
    @property            
    def maxPUVL(self):
        value = self.PV/100 * 95
        if value > 47.50:
            return 47.50
        else:
            return round(value, 2)# - 0.05
        
    @property
    def minPV(self):
        value = self.PUVL/95 * 100
        if value < 0.00:
            return 0.00
        else:
            return round(value , 2)# + 0.05
    @property            
    def maxPV(self):
        value = self.POVP/105 * 100
        if value > 50.00:
            return 50.00
        else:
            return round(value , 2)# - 0.05
########################################################################
GenData = DataContainer()
########################################################################


class ZSerial(serial.Serial):
    """
    A subclass of `serial.Serial` with an overridden `readline` method 
    that reads a line of data terminated by a carriage return (`\r`).
    """

    def readline(self):
        """
        Reads a line from the serial port until a carriage return (`\r`) is encountered.
        
        Returns:
            bytes: The line of data read from the serial port, including the carriage return character.
        """
        eol    = b'\r'  # End-of-line marker, which is a carriage return byte
        leneol = len(eol)  # Length of the end-of-line marker
        line   = bytearray()  # Bytearray to accumulate the bytes read

        while True:
            c = super().read(1)  # Read one byte from the serial port
            if c:
                line += c  # Append the byte to the line
                if line[-leneol:] == eol:  # Check if the end of the line is reached
                    break
            else:
                break  # Exit loop if no more bytes are available (e.g., timeout or end of stream)

        return bytes(line)  # Return the accumulated bytes as an immutable bytes object


class LVPowerSupplyControl():
    def __init__(self):
        self.port_desc = 'Z+ serial port'
        
        self.baudrate  = 9600
        self.address   = 6
        self.Connected = False

        self.get_z_serial_port()
        self.connect_z_serial_port()
        self.connect_device()

    def get_z_serial_port(self):
        # 获取当前系统中所有的串口
        ports = serial.tools.list_ports.comports()

        # 打印每个串口的名称和描述信息
        for port, desc, hwid in sorted(ports):
            if self.port_desc in desc:
                self.z_serial_COM_port = port
                break
            else:
                pass

    def connect_z_serial_port(self):
        try:
            self.z_serial = ZSerial(
                port=self.z_serial_COM_port,
                baudrate=self.baudrate,
                timeout=1,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            self.z_serial.isOpen()
            self.Connected = True
            # print ('Port ' + self.z_serial_COM_port + ' is opened!')

        except IOError: # if port is already opened, close it and open it again and print message
            print ('Port ' + self.z_serial_COM_port + ' was already open, was closed and opened again!')    
            self.z_serial.close()
            self.z_serial.open()
            self.Connected = True
            print ('Port ' + self.z_serial_COM_port + ' was already open, was closed and opened again!')    
        except:
            traceback_info = traceback.format_exc()
            print('LV power error: ', traceback_info)
            pass

    def connect_device(self):
        if self.z_serial.isOpen():
            self.z_serial.write(('ADR 0' + str(self.address) +'\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            #while test != 'OK\r':
            #    self.ConnectDevice()
            if test == 'OK\r':
                # print('Answer: ' + test)
                return True
            else:
                print('Answer: No reaction from Device.')
                return False
        else:
            print('Answer: No connection to Port.')
            return False

    def get_device_data(self):
        if self.connect_device() == True:
            self.QuerySetupGUI()

    def set_power_ON(self):
        status = self.SetOutputON()
        if status:
            print('Power ON')
        else:
            print('Power OFF')

    def set_power_OFF(self):
        status = self.SetOutputOFF()
        if status:
            print('Power OFF Success')
        else:
            print('Power OFF Failed')
        self.z_serial.close()
        self.z_serial = None
        

    def set_Voltage(self, voltage):
        status = self.SetVoltage(voltage)
        # if status:
        #     print('Set Voltage Success')
        # else:
        #     print('Set Voltage Failed')

    #=================================Utils============================
    def SetOutputON(self):
        # print("Start: Send OUT 1")
        if self.z_serial.isOpen():
            self.z_serial.write(('OUT 1\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            #while test != 'OK\r':
            #    self.SetOutputON()
            if test == 'OK\r':
                # print('Answer: ' + test)
                return True
            else:
                print('Answer: No reaction from Device.')
                return False
        else:
            print('Answer: No connection to Port.')
            return False

    def SetOutputOFF(self):
        # print("Start: Send OUT 0")
        if self.z_serial.isOpen():
            self.z_serial.write(('OUT 0\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            #while test != 'OK\r':
            #    self.SetOutputOFF()
            if test == 'OK\r':
                # print('Answer: ' + test)
                return True
            else:
                print('Answer: No reaction from Device.')
                return False
        else:
            print('Answer: No connection to Port.')
            return False

    def SetFLDON(self):
        print("Start: Send FLD 1")
        if self.z_serial.isOpen():
            self.z_serial.write(('FLD 1\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            #while test != 'OK\r':
            #    self.SetOutputON()
            if test == 'OK\r':
                # print('Answer: ' + test)
                return True
            else:
                print('Answer: No reaction from Device.')
                return False
        else:
            print('Answer: No connection to Port.')
            return False

    def SetFLDOFF(self):
        print("Start: Send FLD 0")
        if self.z_serial.isOpen():
            self.z_serial.write(('FLD 0\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            #while test != 'OK\r':
            #    self.SetOutputOFF()
            if test == 'OK\r':
                # print('Answer: ' + test)
                return True
            else:
                # print('Answer: No reaction from Device.')
                return False
        else:
            print('Answer: No connection to Port.')
            return False
           
    def SetVoltage(self, voltage):
        # print("Start: Send PV n")
        if self.z_serial.isOpen():
            self.z_serial.write(('PV ' + str(voltage) + '\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            #while test != 'OK\r':
            #    self.SetVoltage(voltage)
            if test == 'OK\r':
                # print('Answer: ' + test)
                return True
            else:
                # print('Answer: No reaction from Device.')
                return False
        else:
            print('Answer: No connection to Port.')
            return False

    def SetCurrent(self, current):
        print("Start: Send PC n")
        if self.z_serial.isOpen():
            self.z_serial.write(('PC ' + str(current) + '\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            #while test != 'OK\r':
            #    self.SetCurrent(current)
            if test == 'OK\r':
                # print('Answer: ' + test)
                return True
            else:
                print('Answer: No reaction from Device.')
                return False
        else:
            print('Answer: No connection to Port.')
            return False
           
    def SetOVP(self, voltage):
        print("Start: Send OVP n")   
        if self.z_serial.isOpen():
            self.z_serial.write(('OVP ' + str(voltage) + '\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            #while test != 'OK\r':
            #    self.SetOVP(voltage)
            if test == 'OK\r':
                # print('Answer: ' + test)
                self.QueryOVP()
                return True
            else:
                print('Answer: No reaction from Device.')
                return False
        else:
            print('Answer: No connection to Port.')
            return False
   
    def SetUVL(self, voltage):
        print("Start: Send UVL n")   
        if self.z_serial.isOpen():
            self.z_serial.write(('UVL ' + str(voltage) + '\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            #while test != 'OK\r':
            #    self.SetUVL(voltage)
            if test == 'OK\r':
                # print('Answer: ' + test)
                self.QueryUVL()
                return True
            else:
                print('Answer: No reaction from Device.')
                return False
        else:
            print('Answer: No connection to Port.')
            return False                   
            
    def QueryOUT(self):
        print("Start: Query OUT?")   
        if self.z_serial.isOpen():
            self.z_serial.write(('OUT?\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            #while test != ('ON\r' or 'OFF\r'):
            #    self.QueryOUT() 
            if test == 'ON\r':
                # print('Answer: ' + test)
                GenData.OUTPUT = True
            if test == 'OFF\r':
                # print('Answer: ' + test)
                GenData.OUTPUT = False 
        else:
            print('Anser: No connection to Port.')
                
                
    def QueryOVP(self): 
        print("Start: Query OVP?")                      
        if self.z_serial.isOpen():
            self.z_serial.write(('OVP?\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            # print('Answer: ' + test)
            GenData.POVP = float(test)
        else:
            print('Anser: No connection to Port.')
            
    def QueryUVL(self):  
        print("Start: Query UVL?")                     
        if self.z_serial.isOpen():
            self.z_serial.write(('UVL?\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            # print('Answer: ' + test)
            GenData.PUVL = float(test)  
        else:
            print('Anser: No connection to Port.')
            
    def QueryPC(self):    
        print("Start: Query PC?")                   
        if self.z_serial.isOpen():
            self.z_serial.write(('PC?\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            # print('Answer: ' + test)
            GenData.PC = float(test)
        else:
            print('Anser: No connection to Port.')
                    
    def QueryPV(self):   
        print("Start: Query PV?")                    
        if self.z_serial.isOpen():
            self.z_serial.write(('PV?\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            # print('Answer: ' + test)
            GenData.PV = float(test)
        else:
            print('Anser: No connection to Port.')
            
    def QueryFLD(self):  
        print("Start: Query FLD?")                  
        if self.z_serial.isOpen():
            self.z_serial.write(('FLD?\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            #while test != 'ON\r' or 'ON\r':
            #    self.QueryOUT()
            if test == 'ON\r':
                # print('Answer: ' + test)
                GenData.SRFDE = True
            if test == 'OFF\r':
                # print('Answer: ' + test)
                GenData.SRFDE = False
        else:
            print('Anser: No connection to Port.')
            
    def QueryDeviceData(self):
        print("Start: Query IDN?, REV?, SN? and DATE?")
        if self.z_serial.isOpen():
            self.z_serial.write(('IDN?\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")  
            GenData.DeviceIDN = test
            self.z_serial.write(('REV?\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")  
            GenData.DeviceREV = test            
            self.z_serial.write(('SN?\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")  
            GenData.DeviceSN = test
            self.z_serial.write(('DATE?\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")  
            GenData.DeviceDATE = test
        else:
            print('Anser: No connection to Port.')
               
    def QuerySTT(self):
        print("Start: Query STT?")
        if self.z_serial.isOpen():
            self.z_serial.write(('STT?\r').encode())
            test=self.z_serial.readline()
            test=test.decode("utf-8")
            # print('Answer: ' + test)
            
            mv_in=test.find('MV(')
            mv_end=test.find('),PV')
            m_voltage=float(test[(mv_in+3):mv_end]) # Measured Voltage

            pv_in=test.find('PV(')
            pv_end=test.find('),MC')
            p_voltage=float(test[(pv_in+3):pv_end]) # Programmed Voltage

            mc_in=test.find('MC(')
            mc_end=test.find('),PC')
            m_current=float(test[(mc_in+3):mc_end]) # Measured Current

            pc_in=test.find('PC(')
            pc_end=test.find('),SR')
            p_current=float(test[(pc_in+3):pc_end]) # Measured Current
            
            sr_in=test.find('SR(')
            sr_end=test.find('),FR')
            status_reg=int(test[(sr_in+3):sr_end],16) # Status Register
            
            fr_in=test.find('FR(')
            fault_reg=int(test[(fr_in+3):(fr_in+5)],16) # Fault Register

            #Messages
            GenData.MV = m_voltage
            GenData.PV = p_voltage
            GenData.MC = m_current
            GenData.PC = p_current
            # Status register
            GenData.SRCV   = bool(status_reg & 0x01)
            GenData.SRCC   = bool(status_reg & 0x02)
            GenData.SRNFLT = bool(status_reg & 0x04)
            GenData.SRFLT  = bool(status_reg & 0x08)
            GenData.SRAST  = bool(status_reg & 0x10)
            GenData.SRFDE  = bool(status_reg & 0x20)
            GenData.SRLCL  = bool(status_reg & 0x80)
            # Fault Register
            GenData.FRAC   = bool(fault_reg & 0x02)
            GenData.FROTP  = bool(fault_reg & 0x04)
            GenData.FRFOLD = bool(fault_reg & 0x08)
            GenData.FROVP  = bool(fault_reg & 0x10)
            GenData.FRSO   = bool(fault_reg & 0x20)
            GenData.FROFF  = bool(fault_reg & 0x40)
            GenData.FRENA  = bool(fault_reg & 0x80)
        else:
            print('Anser: No connection to Port.')
        
    def QuerySetupGUI(self):
        print("Start: Setup GUI data acquisition.")
        self.QuerySTT()
        self.QueryOVP()
        self.QueryUVL()
        self.QueryOUT()
        self.QueryDeviceData()
        print("End: Setup GUI data acquisition.")
        
    def QueryRefreshGUI(self):
        print("Start: Refresh GUI data acquisition.")
        self.QuerySTT()
        self.QueryOUT()
        print("End: Refresh GUI data acquisition.")

def power_off():
    lv_power_control = LVPowerSupplyControl()
    lv_power_control.set_power_ON()
    lv_power_control.set_power_OFF()

def main():
    lv_power_control = LVPowerSupplyControl()
    lv_power_control.set_power_ON()
    lv_power_control.set_power_OFF()
    
    lv_power_control = LVPowerSupplyControl()
    lv_power_control.set_power_ON()
    lv_power_control.set_Voltage(12)

if __name__ == '__main__':
    # power_off()
    main()
    # power_off()
    # on = 1
    # if on:
    #     lv_power_control.set_Voltage(12)
    # else:
    #     lv_power_control.set_power_OFF()
