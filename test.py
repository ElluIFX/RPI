from typing import Literal
def readConfig( readOvertime=0.01,readByteStartBit=[0xfe],readByteStopBit=[0xef],byteDataCheck: Literal['No','Sum','Crc']='No',retryCommand=[0xff]):
    readOvertime = readOvertime
    readByteStartBit = readByteStartBit
    readByteStopBit = readByteStopBit
    byteDataCheck = byteDataCheck
    retryCommand = retryCommand
    print(byteDataCheck)
    
readConfig()