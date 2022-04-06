from SerCom32 import SerCom32

ser = SerCom32("/dev/serial0", 115200)
print("start")
ser.sendConfig(startBit=[0xAA, 0x22],optionBit = [0x01], stopBit=[], useSumCheck=False)
while True:
    s = input("send: ")
    sended = ser.send_form_data(s)
    print(f"sended: {' '.join([hex(i) for i in sended])}")
