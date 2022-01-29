from SerCom32 import SerCom32
ser = SerCom32('/dev/ttyUSB0', 115200)


def main():
    while True:
        ser.read_byte_serial()
        ser.readConfig(readByteStartBit=[
                       0x54], packLengthMode=True, packLengthAdd=8, packLengthMulti=3, byteDataCheck='No')
        if ser.rx_byte_done():
            print("RADAR:"+ser.rx_byte_data())


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\nKeyboardInterrupt, serial port closed.')
        ser.close()
