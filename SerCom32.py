from asyncore import write
from copy import copy, deepcopy
from itertools import count
from numpy import byte
import serial
import time
from sys import byteorder as sysByteorder


class SerCom32:
    def __init__(self, port, baudrate, timeout=0.5, readOvertime=0.01):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.readDoneFlag = False
        self.readBuffer = ''
        self.readTick = time.monotonic()
        self.readOvertime = readOvertime
        self.readBuffer = ''
        self.readSaveBuffer = ''
        self.readDoneFlag = False
        self.form_config()

    def form_config(self, startBit=[0xfe], stopBit=[0xef], useSumCheck=True):
        self.startBit = startBit
        self.stopBit = stopBit
        self.useSumCheck = useSumCheck

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
                checksum += int.from_bytes(data[i:i+1],byteorder=
                                           sysByteorder, signed=False)
                checksum &= 0xFF
            data.append(checksum)
        self.write_bytes_serial(data)
        return 0


if __name__ == '__main__':
    ser = SerCom32('/dev/ttyAMA0', 115200)
    print('go')
    try:
        while True:
            ser.read_serial()
            if ser.rx_done():
                str = ser.rx_data()
                ser.write_str_serial(str)
                print(str)
                time.sleep(0.2)
                ser.send_form_data([0x12,0x13,0x14])
    except KeyboardInterrupt:
        print('\n\nKeyboardInterrupt, serial port closed.')
        ser.close()
