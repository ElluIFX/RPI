from copy import copy
from typing import Literal
from numpy import byte
import serial
import time
from sys import byteorder as sysByteorder


class SerCom32:
    def __init__(self, port, baudrate, timeout=0.5):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.readDoneFlag = False
        self.readTick = time.monotonic()
        self.readBuffer = ''
        self.readSaveBuffer = ''
        self.readByteDoneFlag = False
        self.readByteGoingFlag = False
        self.readByteBuffer = []
        self.readByteSaveBuffer = []
        self.sendConfig()
        self.readConfig()
        self.packCount = 0
        self.packLength = 0

    def sendConfig(self, startBit=[0xfe], stopBit=[0xef], useSumCheck=True):
        self.startBit = startBit
        self.stopBit = stopBit
        self.useSumCheck = useSumCheck

    def readConfig(self, readOvertime=0.01, packLengthMode=False, packLengthAdd=0, packLengthMulti=1, readByteStartBit=[0xfe], readByteStopBit=[0xef], byteDataCheck: Literal['No', 'Sum', 'Crc'] = 'No', failRetry=False, retryCommand=[0xff]):
        self.readOvertime = readOvertime
        self.readByteStartBit = readByteStartBit
        self.readByteStopBit = readByteStopBit
        self.byteDataCheck = byteDataCheck
        self.retryCommand = retryCommand
        self.failRetry = failRetry
        self.packLengthMode = packLengthMode
        self.packLengthAdd = packLengthAdd
        self.packLengthMulti = packLengthMulti

    def read_serial(self):
        if(time.monotonic() - self.readTick > self.readOvertime and len(self.readBuffer) != 0):
            self.readDoneFlag = True
            self.readSaveBuffer = copy(self.readBuffer)
            self.readBuffer = ''
            return
        if(self.ser.in_waiting > 0):
            self.readBuffer += self.ser.read(
                self.ser.in_waiting).decode('utf-8')
            self.readTick = time.monotonic()
            self.ser.flushInput()
        time.sleep(0.002)
        return 0

    def rx_done(self):
        return self.readDoneFlag

    def rx_data(self):
        self.readDoneFlag = False
        return self.readSaveBuffer

    def read_byte_serial(self):
        tmp = 0
        if self.packLengthMode == False:
            while(self.ser.in_waiting > 0):
                tmp = self.ser.read(1)
                if(tmp == self.readByteStartBit):
                    self.readByteGoingFlag = True
                    continue
                if(tmp == self.readByteStopBit):
                    self.readByteGoingFlag = False
                    if(self.byteDataCheck == 'No'):
                        self.readByteSaveBuffer = copy(self.readByteBuffer)
                        self.readByteBuffer = []
                        self.readByteDoneFlag = True
                        return 1
                    elif(self.byteDataCheck == 'Sum'):
                        length = len(self.readByteBuffer)
                        checksum = 0
                        for i in self.readByteStartBit:
                            checksum += int.from_bytes(i,
                                                       sysByteorder, signed=False)
                            checksum &= 0xFF
                        for i in self.readByteStopBit:
                            checksum += int.from_bytes(i,
                                                       sysByteorder, signed=False)
                            checksum &= 0xFF
                        for i in range(0, length):
                            checksum += int.from_bytes(self.readByteBuffer[i:i+1],
                                                       byteorder=sysByteorder, signed=False)
                            checksum &= 0xFF
                        try:
                            receivedChecksum = self.ser.read(1)
                            if(receivedChecksum == checksum):
                                self.readByteSaveBuffer = copy(
                                    self.readByteBuffer)
                                self.readByteBuffer = []
                                self.readByteDoneFlag = True
                                return 1
                        except:
                            pass
                        self.readByteBuffer = []
                        if self.failRetry:
                            self.write_bytes_serial(self.retryCommand)
                        return 0
                    elif(self.byteDataCheck == 'Crc'):
                        pass
                    return 0
                if(self.readByteGoingFlag):
                    self.readByteBuffer.append(tmp)
        else:  # packLengthMode
            while(self.ser.in_waiting > 0):
                tmp = self.ser.read(1)
                if(tmp == self.readByteStartBit):
                    self.readByteGoingFlag = True
                    self.packLength = -1
                    self.packCount = 0
                    continue
                if(self.packLength == -1):
                    tmp &= 0b00011111  # LD radar
                    self.packLength = int.from_bytes(
                        tmp, sysByteorder, signed=False)
                    continue
                if(self.readByteGoingFlag):
                    self.packCount += 1
                    self.readByteBuffer.append(tmp)
                    if(self.packCount == self.packLength*self.packLengthMulti + self.packLengthAdd):
                        self.readByteGoingFlag = False
                        if(self.byteDataCheck == 'No'):
                            self.readByteSaveBuffer = copy(self.readByteBuffer)
                            self.readByteBuffer = []
                            self.readByteDoneFlag = True
                            return 1
                        elif(self.byteDataCheck == 'Sum'):
                            length = len(self.readByteBuffer)
                            checksum = 0
                            checksum += self.packLength
                            for i in self.readByteStartBit:
                                checksum += int.from_bytes(i,
                                                        sysByteorder, signed=False)
                                checksum &= 0xFF
                            for i in range(0, length):
                                checksum += int.from_bytes(self.readByteBuffer[i:i+1],
                                                        byteorder=sysByteorder, signed=False)
                                checksum &= 0xFF
                            try:
                                receivedChecksum = self.ser.read(1)
                                if(receivedChecksum == checksum):
                                    self.readByteSaveBuffer = copy(
                                        self.readByteBuffer)
                                    self.readByteBuffer = []
                                    self.readByteDoneFlag = True
                                    return 1
                            except:
                                pass
                            self.readByteBuffer = []
                            if self.failRetry:
                                self.write_bytes_serial(self.retryCommand)
                            return 0
                        elif(self.byteDataCheck == 'Crc'):
                            pass
                        return 0
        time.sleep(0.002)
        return 0

    def rx_byte_done(self):
        return self.readByteDoneFlag

    def rx_byte_data(self):
        self.readByteDoneFlag = False
        return self.readByteSaveBuffer

    def close(self):
        if self.ser != None:
            self.ser.close()

    def write_str_serial(self, data):
        self.ser.write(data.encode('utf-8'))
        self.ser.flush()
        return 0

    def write_bytes_serial(self, data):
        self.ser.write(data)
        self.ser.flush()
        return 0

    def send_form_data(self, data):
        data = self.startBit+[len(data)]+data+self.stopBit
        if(self.useSumCheck):
            length = len(data)
            checksum = 0
            for i in range(0, length):
                checksum += int.from_bytes(data[i:i+1],
                                           byteorder=sysByteorder, signed=False)
                checksum &= 0xFF
            data.append(checksum)
        self.write_bytes_serial(data)
        return 0


if __name__ == '__main__':
    print('This Module can not be run alone.')
