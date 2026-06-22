
import time
#from amplifier import Amplifier

#amp = Amplifier("/dev/ttyr00", 0, 2.0)
#time.sleep(1)
#for _ in range(10):
#    res = amp.read_data()
#    print(res)
#    time.sleep(1)


from gsv86lib import gsv86

com = gsv86("/dev/ttyr00", 115200)
com.writeDataRate(2.0)
com.StartTransmission()

while True:
    rawdata = com.ReadValue()
    print(rawdata.data)
    if rawdata.data:
        ts = rawdata.getTimestamp()
        val3 = rawdata.getChannel1()
        val4 = rawdata.getChannel4()
        val7 = rawdata.getChannel5()
        val8 = rawdata.getChannel8()
        print(f"[{ts}]: motor_2={val3:0.3f}, motor_3={val4:0.3f}, motor_6={val7:0.3f}, motor_7={val8:0.3f}")
    time.sleep(2)


