from copy import copy
from typing import Literal
from numpy import byte
import serial
import time
from sys import byteorder as sysByteorder


class SerCom32:
    def __init__(self, port, baudrate, timeout=0.5, byteOrder=sysByteorder):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.readDoneFlag = False
        self.readTick = time.monotonic()
        self.readBuffer = bytes()
        self.readSaveBuffer = bytes()
        self.readByteDoneFlag = False
        self.readByteGoingFlag = False
        self.readByteBuffer = []
        self.readByteSaveBuffer = []
        self.sendConfig()
        self.readConfig()
        self.packCount = 0
        self.packLength = 0
        self.byteOrder = byteOrder

    def sendConfig(self, startBit=[], stopBit=[], optionBit=[], useSumCheck=True):
        self.startBit = startBit
        self.optionBit = optionBit
        self.stopBit = stopBit
        self.useSumCheck = useSumCheck

    def readConfig(
        self,
        readTimeout=0.01,
        packLengthMode=False,
        packLengthAdd=0,
        packLengthMulti=1,
        readByteStartBit=[],
        readByteStopBit=[],
        byteDataCheck: Literal["No", "Sum", "Crc"] = "No",
        failRetry=False,
        retryCommand=[],
    ):
        self.readOvertime = readTimeout
        self.readByteStartBit = readByteStartBit
        self.readByteStopBit = readByteStopBit
        self.byteDataCheck = byteDataCheck
        self.retryCommand = retryCommand
        self.failRetry = failRetry
        self.packLengthMode = packLengthMode
        self.packLengthAdd = packLengthAdd
        self.packLengthMulti = packLengthMulti

    def read_serial(self):
        if time.monotonic() - self.readTick > self.readOvertime and len(self.readBuffer) != 0:
            self.readDoneFlag = True
            self.readSaveBuffer = copy(self.readBuffer)
            self.readBuffer = bytes()
            return
        if self.ser.in_waiting > 0:
            self.readBuffer += self.ser.read(self.ser.in_waiting)
            self.ser.flushInput()
            self.readTick = time.monotonic()
        time.sleep(0.001)
        return 0

    def rx_done(self):
        return self.readDoneFlag

    def rx_data(self) -> bytes:
        self.readDoneFlag = False
        return self.readSaveBuffer

    def read_byte_serial(self):
        tmp = 0
        if self.packLengthMode == False:
            while self.ser.in_waiting > 0:
                tmp = self.ser.read(1)
                if tmp == self.readByteStartBit:
                    self.readByteGoingFlag = True
                    continue
                if tmp == self.readByteStopBit:
                    self.readByteGoingFlag = False
                    if self.byteDataCheck == "No":
                        self.readByteSaveBuffer = copy(self.readByteBuffer)
                        self.readByteBuffer = []
                        self.readByteDoneFlag = True
                        return 1
                    elif self.byteDataCheck == "Sum":
                        length = len(self.readByteBuffer)
                        checksum = 0
                        for i in self.readByteStartBit:
                            checksum += int.from_bytes(i, sysByteorder, signed=False)
                            checksum &= 0xFF
                        for i in self.readByteStopBit:
                            checksum += int.from_bytes(i, sysByteorder, signed=False)
                            checksum &= 0xFF
                        for i in range(0, length):
                            checksum += int.from_bytes(
                                self.readByteBuffer[i : i + 1], byteorder=sysByteorder, signed=False
                            )
                            checksum &= 0xFF
                        try:
                            receivedChecksum = self.ser.read(1)
                            if receivedChecksum == checksum:
                                self.readByteSaveBuffer = copy(self.readByteBuffer)
                                self.readByteBuffer = []
                                self.readByteDoneFlag = True
                                return 1
                        except:
                            pass
                        self.readByteBuffer = []
                        if self.failRetry:
                            self.write_bytes_serial(self.retryCommand)
                        return 0
                    elif self.byteDataCheck == "Crc":
                        pass
                    return 0
                if self.readByteGoingFlag:
                    self.readByteBuffer.append(tmp)
        else:  # packLengthMode
            while self.ser.in_waiting > 0:
                tmp = self.ser.read(1)
                if tmp == self.readByteStartBit:
                    self.readByteGoingFlag = True
                    self.packLength = -1
                    self.packCount = 0
                    continue
                if self.packLength == -1:
                    tmp &= 0b00011111  # LD radar
                    self.packLength = int.from_bytes(tmp, sysByteorder, signed=False)
                    continue
                if self.readByteGoingFlag:
                    self.packCount += 1
                    self.readByteBuffer.append(tmp)
                    if self.packCount == self.packLength * self.packLengthMulti + self.packLengthAdd:
                        self.readByteGoingFlag = False
                        if self.byteDataCheck == "No":
                            self.readByteSaveBuffer = copy(self.readByteBuffer)
                            self.readByteBuffer = []
                            self.readByteDoneFlag = True
                            return 1
                        elif self.byteDataCheck == "Sum":
                            length = len(self.readByteBuffer)
                            checksum = 0
                            checksum += self.packLength
                            for i in self.readByteStartBit:
                                checksum += int.from_bytes(i, sysByteorder, signed=False)
                                checksum &= 0xFF
                            for i in range(0, length):
                                checksum += int.from_bytes(
                                    self.readByteBuffer[i : i + 1], byteorder=sysByteorder, signed=False
                                )
                                checksum &= 0xFF
                            try:
                                receivedChecksum = self.ser.read(1)
                                if receivedChecksum == checksum:
                                    self.readByteSaveBuffer = copy(self.readByteBuffer)
                                    self.readByteBuffer = []
                                    self.readByteDoneFlag = True
                                    return 1
                            except:
                                pass
                            self.readByteBuffer = []
                            if self.failRetry:
                                self.write_bytes_serial(self.retryCommand)
                            return 0
                        elif self.byteDataCheck == "Crc":
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

    def write_str_serial(self, data: str):
        self.ser.write(data.encode("utf-8"))
        self.ser.flush()

    def write_bytes_serial(self, data: bytes):
        self.ser.write(data)
        self.ser.flush()

    def send_form_data(self, data):
        data_ = copy(data)
        if isinstance(data_, list):
            data_ = bytes(data_)
        if isinstance(data_, str):
            data_ = data_.encode("utf-8")
        if not isinstance(data_, bytes):
            raise TypeError("data must be bytes")
        len_as_byte = len(data_).to_bytes(1, self.byteOrder)
        send_data = bytes(self.startBit) + bytes(self.optionBit) + len_as_byte + data_ + bytes(self.stopBit)
        if self.useSumCheck:
            length = len(data)
            checksum = 0
            for i in range(0, length):
                checksum += int.from_bytes(data[i : i + 1], byteorder=self.byteOrder, signed=False)
                checksum &= 0xFF
            send_data += checksum.to_bytes(1, self.byteOrder)
        self.ser.write(send_data)
        self.ser.flush()
        return send_data


if __name__ == "__main__":
    print("This Module can not be run alone.")
from copy import copy
from typing import Literal
from numpy import byte
import serial
import time
from sys import byteorder as sysByteorder


class SerCom32:
    def __init__(self, port, baudrate, timeout=0.5, byteOrder=sysByteorder):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.readDoneFlag = False
        self.readTick = time.monotonic()
        self.readBuffer = bytes()
        self.readSaveBuffer = bytes()
        self.readByteDoneFlag = False
        self.readByteGoingFlag = False
        self.readByteBuffer = []
        self.readByteSaveBuffer = []
        self.sendConfig()
        self.readConfig()
        self.packCount = 0
        self.packLength = 0
        self.byteOrder = byteOrder

    def sendConfig(self, startBit=[], stopBit=[], optionBit=[], useSumCheck=True):
        self.startBit = startBit
        self.optionBit = optionBit
        self.stopBit = stopBit
        self.useSumCheck = useSumCheck

    def readConfig(
        self,
        readTimeout=0.01,
        packLengthMode=False,
        packLengthAdd=0,
        packLengthMulti=1,
        readByteStartBit=[],
        readByteStopBit=[],
        byteDataCheck: Literal["No", "Sum", "Crc"] = "No",
        failRetry=False,
        retryCommand=[],
    ):
        self.readOvertime = readTimeout
        self.readByteStartBit = readByteStartBit
        self.readByteStopBit = readByteStopBit
        self.byteDataCheck = byteDataCheck
        self.retryCommand = retryCommand
        self.failRetry = failRetry
        self.packLengthMode = packLengthMode
        self.packLengthAdd = packLengthAdd
        self.packLengthMulti = packLengthMulti

    def read_serial(self):
        if time.monotonic() - self.readTick > self.readOvertime and len(self.readBuffer) != 0:
            self.readDoneFlag = True
            self.readSaveBuffer = copy(self.readBuffer)
            self.readBuffer = bytes()
            return
        if self.ser.in_waiting > 0:
            self.readBuffer += self.ser.read(self.ser.in_waiting)
            self.readTick = time.monotonic()
            self.ser.flushInput()
        time.sleep(0.002)
        return 0

    def rx_done(self):
        return self.readDoneFlag

    def rx_data(self) -> bytes:
        self.readDoneFlag = False
        return self.readSaveBuffer

    def read_byte_serial(self):
        tmp = 0
        if self.packLengthMode == False:
            while self.ser.in_waiting > 0:
                tmp = self.ser.read(1)
                if tmp == self.readByteStartBit:
                    self.readByteGoingFlag = True
                    continue
                if tmp == self.readByteStopBit:
                    self.readByteGoingFlag = False
                    if self.byteDataCheck == "No":
                        self.readByteSaveBuffer = copy(self.readByteBuffer)
                        self.readByteBuffer = []
                        self.readByteDoneFlag = True
                        return 1
                    elif self.byteDataCheck == "Sum":
                        length = len(self.readByteBuffer)
                        checksum = 0
                        for i in self.readByteStartBit:
                            checksum += int.from_bytes(i, sysByteorder, signed=False)
                            checksum &= 0xFF
                        for i in self.readByteStopBit:
                            checksum += int.from_bytes(i, sysByteorder, signed=False)
                            checksum &= 0xFF
                        for i in range(0, length):
                            checksum += int.from_bytes(
                                self.readByteBuffer[i : i + 1], byteorder=sysByteorder, signed=False
                            )
                            checksum &= 0xFF
                        try:
                            receivedChecksum = self.ser.read(1)
                            if receivedChecksum == checksum:
                                self.readByteSaveBuffer = copy(self.readByteBuffer)
                                self.readByteBuffer = []
                                self.readByteDoneFlag = True
                                return 1
                        except:
                            pass
                        self.readByteBuffer = []
                        if self.failRetry:
                            self.write_bytes_serial(self.retryCommand)
                        return 0
                    elif self.byteDataCheck == "Crc":
                        pass
                    return 0
                if self.readByteGoingFlag:
                    self.readByteBuffer.append(tmp)
        else:  # packLengthMode
            while self.ser.in_waiting > 0:
                tmp = self.ser.read(1)
                if tmp == self.readByteStartBit:
                    self.readByteGoingFlag = True
                    self.packLength = -1
                    self.packCount = 0
                    continue
                if self.packLength == -1:
                    tmp &= 0b00011111  # LD radar
                    self.packLength = int.from_bytes(tmp, sysByteorder, signed=False)
                    continue
                if self.readByteGoingFlag:
                    self.packCount += 1
                    self.readByteBuffer.append(tmp)
                    if self.packCount == self.packLength * self.packLengthMulti + self.packLengthAdd:
                        self.readByteGoingFlag = False
                        if self.byteDataCheck == "No":
                            self.readByteSaveBuffer = copy(self.readByteBuffer)
                            self.readByteBuffer = []
                            self.readByteDoneFlag = True
                            return 1
                        elif self.byteDataCheck == "Sum":
                            length = len(self.readByteBuffer)
                            checksum = 0
                            checksum += self.packLength
                            for i in self.readByteStartBit:
                                checksum += int.from_bytes(i, sysByteorder, signed=False)
                                checksum &= 0xFF
                            for i in range(0, length):
                                checksum += int.from_bytes(
                                    self.readByteBuffer[i : i + 1], byteorder=sysByteorder, signed=False
                                )
                                checksum &= 0xFF
                            try:
                                receivedChecksum = self.ser.read(1)
                                if receivedChecksum == checksum:
                                    self.readByteSaveBuffer = copy(self.readByteBuffer)
                                    self.readByteBuffer = []
                                    self.readByteDoneFlag = True
                                    return 1
                            except:
                                pass
                            self.readByteBuffer = []
                            if self.failRetry:
                                self.write_bytes_serial(self.retryCommand)
                            return 0
                        elif self.byteDataCheck == "Crc":
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

    def write_str_serial(self, data: str):
        self.ser.write(data.encode("utf-8"))
        self.ser.flush()

    def write_bytes_serial(self, data: bytes):
        self.ser.write(data)
        self.ser.flush()

    def send_form_data(self, data):
        data_ = copy(data)
        if isinstance(data_, list):
            data_ = bytes(data_)
        if isinstance(data_, str):
            data_ = data_.encode("utf-8")
        if not isinstance(data_, bytes):
            raise TypeError("data must be bytes")
        len_as_byte = len(data_).to_bytes(1, self.byteOrder)
        send_data = bytes(self.startBit) + bytes(self.optionBit) + len_as_byte + data_ + bytes(self.stopBit)
        if self.useSumCheck:
            length = len(data)
            checksum = 0
            for i in range(0, length):
                checksum += int.from_bytes(data[i : i + 1], byteorder=self.byteOrder, signed=False)
                checksum &= 0xFF
            send_data += checksum.to_bytes(1, self.byteOrder)
        self.ser.write(send_data)
        self.ser.flush()
        return send_data


if __name__ == "__main__":
    print("This Module can not be run alone.")
from copy import copy
from typing import Literal
from numpy import byte
import serial
import time
from sys import byteorder as sysByteorder


class SerCom32:
    def __init__(self, port, baudrate, timeout=0.5, byteOrder=sysByteorder):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.readDoneFlag = False
        self.readTick = time.monotonic()
        self.readBuffer = bytes()
        self.readSaveBuffer = bytes()
        self.readByteDoneFlag = False
        self.readByteGoingFlag = False
        self.readByteBuffer = []
        self.readByteSaveBuffer = []
        self.sendConfig()
        self.readConfig()
        self.packCount = 0
        self.packLength = 0
        self.byteOrder = byteOrder

    def sendConfig(self, startBit=[], stopBit=[], optionBit=[], useSumCheck=True):
        self.startBit = startBit
        self.optionBit = optionBit
        self.stopBit = stopBit
        self.useSumCheck = useSumCheck

    def readConfig(
        self,
        readTimeout=0.01,
        packLengthMode=False,
        packLengthAdd=0,
        packLengthMulti=1,
        readByteStartBit=[],
        readByteStopBit=[],
        byteDataCheck: Literal["No", "Sum", "Crc"] = "No",
        failRetry=False,
        retryCommand=[],
    ):
        self.readOvertime = readTimeout
        self.readByteStartBit = readByteStartBit
        self.readByteStopBit = readByteStopBit
        self.byteDataCheck = byteDataCheck
        self.retryCommand = retryCommand
        self.failRetry = failRetry
        self.packLengthMode = packLengthMode
        self.packLengthAdd = packLengthAdd
        self.packLengthMulti = packLengthMulti

    def read_serial(self):
        if time.monotonic() - self.readTick > self.readOvertime and len(self.readBuffer) != 0:
            self.readDoneFlag = True
            self.readSaveBuffer = copy(self.readBuffer)
            self.readBuffer = bytes()
            return
        if self.ser.in_waiting > 0:
            self.readBuffer += self.ser.read(self.ser.in_waiting)
            self.readTick = time.monotonic()
            self.ser.flushInput()
        time.sleep(0.002)
        return 0

    def rx_done(self):
        return self.readDoneFlag

    def rx_data(self) -> bytes:
        self.readDoneFlag = False
        return self.readSaveBuffer

    def read_byte_serial(self):
        tmp = 0
        if self.packLengthMode == False:
            while self.ser.in_waiting > 0:
                tmp = self.ser.read(1)
                if tmp == self.readByteStartBit:
                    self.readByteGoingFlag = True
                    continue
                if tmp == self.readByteStopBit:
                    self.readByteGoingFlag = False
                    if self.byteDataCheck == "No":
                        self.readByteSaveBuffer = copy(self.readByteBuffer)
                        self.readByteBuffer = []
                        self.readByteDoneFlag = True
                        return 1
                    elif self.byteDataCheck == "Sum":
                        length = len(self.readByteBuffer)
                        checksum = 0
                        for i in self.readByteStartBit:
                            checksum += int.from_bytes(i, sysByteorder, signed=False)
                            checksum &= 0xFF
                        for i in self.readByteStopBit:
                            checksum += int.from_bytes(i, sysByteorder, signed=False)
                            checksum &= 0xFF
                        for i in range(0, length):
                            checksum += int.from_bytes(
                                self.readByteBuffer[i : i + 1], byteorder=sysByteorder, signed=False
                            )
                            checksum &= 0xFF
                        try:
                            receivedChecksum = self.ser.read(1)
                            if receivedChecksum == checksum:
                                self.readByteSaveBuffer = copy(self.readByteBuffer)
                                self.readByteBuffer = []
                                self.readByteDoneFlag = True
                                return 1
                        except:
                            pass
                        self.readByteBuffer = []
                        if self.failRetry:
                            self.write_bytes_serial(self.retryCommand)
                        return 0
                    elif self.byteDataCheck == "Crc":
                        pass
                    return 0
                if self.readByteGoingFlag:
                    self.readByteBuffer.append(tmp)
        else:  # packLengthMode
            while self.ser.in_waiting > 0:
                tmp = self.ser.read(1)
                if tmp == self.readByteStartBit:
                    self.readByteGoingFlag = True
                    self.packLength = -1
                    self.packCount = 0
                    continue
                if self.packLength == -1:
                    tmp &= 0b00011111  # LD radar
                    self.packLength = int.from_bytes(tmp, sysByteorder, signed=False)
                    continue
                if self.readByteGoingFlag:
                    self.packCount += 1
                    self.readByteBuffer.append(tmp)
                    if self.packCount == self.packLength * self.packLengthMulti + self.packLengthAdd:
                        self.readByteGoingFlag = False
                        if self.byteDataCheck == "No":
                            self.readByteSaveBuffer = copy(self.readByteBuffer)
                            self.readByteBuffer = []
                            self.readByteDoneFlag = True
                            return 1
                        elif self.byteDataCheck == "Sum":
                            length = len(self.readByteBuffer)
                            checksum = 0
                            checksum += self.packLength
                            for i in self.readByteStartBit:
                                checksum += int.from_bytes(i, sysByteorder, signed=False)
                                checksum &= 0xFF
                            for i in range(0, length):
                                checksum += int.from_bytes(
                                    self.readByteBuffer[i : i + 1], byteorder=sysByteorder, signed=False
                                )
                                checksum &= 0xFF
                            try:
                                receivedChecksum = self.ser.read(1)
                                if receivedChecksum == checksum:
                                    self.readByteSaveBuffer = copy(self.readByteBuffer)
                                    self.readByteBuffer = []
                                    self.readByteDoneFlag = True
                                    return 1
                            except:
                                pass
                            self.readByteBuffer = []
                            if self.failRetry:
                                self.write_bytes_serial(self.retryCommand)
                            return 0
                        elif self.byteDataCheck == "Crc":
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

    def write_str_serial(self, data: str):
        self.ser.write(data.encode("utf-8"))
        self.ser.flush()

    def write_bytes_serial(self, data: bytes):
        self.ser.write(data)
        self.ser.flush()

    def send_form_data(self, data):
        data_ = copy(data)
        if isinstance(data_, list):
            data_ = bytes(data_)
        if isinstance(data_, str):
            data_ = data_.encode("utf-8")
        if not isinstance(data_, bytes):
            raise TypeError("data must be bytes")
        len_as_byte = len(data_).to_bytes(1, self.byteOrder)
        send_data = bytes(self.startBit) + bytes(self.optionBit) + len_as_byte + data_ + bytes(self.stopBit)
        if self.useSumCheck:
            length = len(data)
            checksum = 0
            for i in range(0, length):
                checksum += int.from_bytes(data[i : i + 1], byteorder=self.byteOrder, signed=False)
                checksum &= 0xFF
            send_data += checksum.to_bytes(1, self.byteOrder)
        self.ser.write(send_data)
        self.ser.flush()
        return send_data


if __name__ == "__main__":
    print("This Module can not be run alone.")
