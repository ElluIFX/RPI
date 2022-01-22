
from wiringpi import delayMicroseconds, millis, wiringPiSetup
import time
from SerCom32 import SerCom32
ser = SerCom32('/dev/ttyAMA0', 115200)
def main():
    while True:
        # print(millis())
        # delayMicroseconds(100*1000)
        ser.read_serial()
        if ser.rx_done():
            str = '------- R X -------\n'+ser.rx_data()
            print(str)
    
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\nKeyboardInterrupt, serial port closed.')
        ser.close()