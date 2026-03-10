from machine import Pin, I2C
from utime import sleep


i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=50000)
pin = Pin("LED", Pin.OUT)

def writeToDac(value):
    buf=bytearray(2)
    buf[0]=(value >> 8) & 0xFF
    buf[1]=value & 0xFF
    i2c.writeto(0x60,buf)


print("LED starts flashing...")

dev = i2c.scan() # scan for devices on the I2C bus
for d in dev:
    print("I2C device found at address: ", hex(d))

if len(dev) == 0:
    print("No I2C devices found. Check your connections.")

while False:
    try:
        for i in range(0, 4096, 256):
            writeToDac(i)
            print("DAC value set to: ", i)
            sleep(1) # sleep 1sec
            pin.toggle()
    except KeyboardInterrupt:
        break
pin.off()
writeToDac(1000) # reset DAC to 0
print("Finished.")


