from machine import Pin, I2C
from utime import sleep
from MCP342x import MCP342x
from Ntc import NTC
from loopCtrl import PIController

i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=50000)
pin = Pin("LED", Pin.OUT)

def writeToDac(value):
    buf = bytearray(2)
    buf[0] = (int(value) >> 8) & 0xFF
    buf[1] = int(value) & 0xFF
    i2c.writeto(0x60, buf)

def GetAdcValue(config):
    buf = bytearray(2)
    buf[0] = (int(config) >> 8) & 0xFF
    buf[1] = int(config) & 0xFF
    i2c.writeto(0x69, buf)
    sleep(0.1)  # wait for DAC to process
    val = i2c.readfrom(0x69, 2)
    return (val[0] << 8) | val[1]
    return i2c.readfrom(0x69, 2)


ntc = NTC(r_0=10000.0, beta=3950.0)

print("LED starts flashing...")

dev = i2c.scan()  # scan for devices on the I2C bus
for d in dev:
    print("I2C device found at address: ", hex(d))

if len(dev) == 0:
    print("No I2C devices found. Check your connections.")

addr69_ch0 = MCP342x(i2c, 0x69, device='MCP3422', channel=0, resolution=18, gain=1,
                    scale_factor=1.0)
addr69_ch1 = MCP342x(i2c, 0x69, device='MCP3422', channel=1, resolution=18, gain=1,
                    scale_factor=1.0)

# PI control (example parameters)
pi = PIController(
    kp=30.0,
    ki=0.8,
    output_min=0,
    output_max=4095,
    meas_min=0.0,
    meas_max=5.0,
    anti_windup=True,
    integrator_min=-10000,
    integrator_max=10000,
)
pi.set_setpoint(30.0)  # target temperature
pi.enable()
while True:
    adc_values = [-1.0, -1.0]
    try:
        adc_values[0] = addr69_ch0.convert_and_read()# * addr69_ch0.config_to_lsb(addr69_ch0.config) / addr69_ch0.config_to_gain(addr69_ch0.config) * addr69_ch0.scale_factor + addr69_ch0.offset
        adc_values[1] = addr69_ch1.convert_and_read()# * addr69_ch1.config_to_lsb(addr69_ch1.config) / addr69_ch1.config_to_gain(addr69_ch1.config) * addr69_ch1.scale_factor + addr69_ch1.offset
    except Exception as error:
        print("ADC read error:", error)
        

    print("ADC:{ch0:<10.6f},{ch1:<10.2f}".format(
        ch0=adc_values[0], ch1=adc_values[1]))
    print("Temperature: {temp:.2f} °C".format(temp=ntc.V_to_T(adc_values[0]) if adc_values[0] >= 0 else -999.0))
    sleep(1.0)

while True:
    adc_values = [-1.0, -1.0]
    try:
        adc_values[0] = addr68_ch0.convert_and_read() * addr68_ch0.config_to_lsb(addr68_ch0.config) / addr68_ch0.config_to_gain(addr68_ch0.config) * addr68_ch0.scale_factor + addr68_ch0.offset
        adc_values[1] = addr68_ch1.convert_and_read() * addr68_ch1.config_to_lsb(addr68_ch1.config) / addr68_ch1.config_to_gain(addr68_ch1.config) * addr68_ch1.scale_factor + addr68_ch1.offset

    except Exception as error:
        print("ADC read error:", error)

    if not pi.is_enabled():
        control_output = 0
    else:
        try:
            temp = ntc.V_to_T(adc_values[1])
            control_output = pi.update(temp, dt=1.0)
        except Exception as err:
            print("Control update error:", err)
            pi.force_fault("open loop sensor failure")
            control_output = 0

    if pi.is_fault():
        print("Controller fault:", pi.fault_reason)
        pi.disable()
        control_output = 0

    writeToDac(control_output)

    print("ADC:{ch0:<10.2f},{ch1:<10.2f}".format(
        ch0=adc_values[0], ch1=adc_values[1]))
    print("Temperature: {temp:.2f} °C".format(temp=ntc.V_to_T(adc_values[1]) if adc_values[1] >= 0 else -999.0))
    print("PI: state={}, setpoint={:.2f}, output={:.1f}, integral={:.1f}".format(
        pi.status(), pi.setpoint, pi.last_output, pi.integral))

    sleep(1.0)

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
writeToDac(1000)  # reset DAC to 0
print("Finished.")


