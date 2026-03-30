from machine import Pin, I2C
from utime import sleep
from MCP342x import MCP342x
from Ntc import NTC
from loopCtrl import PIController
from Peltier import PeltierBase

i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=50000)
pin = Pin("LED", Pin.OUT)

def setVoltage(voltage):
    value = int(2162.8  - voltage * 186.07)  # 12-bit DAC (4096 levels)
    if(value < 0):
        value = 0
    elif(value > 4095):
        value = 4095
    writeToDac(value)
#ntc = NTC(r_0=10000.0, beta=3950.0)


class NTCreader(NTC):
    def __init__(self, r_0, beta, adc_channel):
        super().__init__(r_0, beta)
        self.adc_channel = adc_channel
        self.T = 25.0  # Initial guess for temperature
    def read_temperature(self):
        try:
            adc_value = self.adc_channel.convert_and_read()
            voltage = adc_value #* self.adc_channel.config_to_lsb(self.adc_channel.config) / self.adc_channel.config_to_gain(self.adc_channel.config) * self.adc_channel.scale_factor + self.adc_channel.offset
            self.V = voltage
            self.T = self.V_to_T(voltage)
            return self.T
        except Exception as error:
            print("NTC read error:", error)
            return None
    def print_temperature(self):
         print("ADC Voltage: {voltage:.6f} V".format(voltage=self.V))
         print("Temperature: {temp:.2f} °C".format(temp=self.T if self.T is not None else -999.0))

class Peltier(PeltierBase):
    def __init__(self, R_joul = 0.5, R_thermal = 1, adc_channel=None):
        super().__init__(R_joul, R_thermal)
        self.adc_channel = adc_channel
        self.current = 0.0  # Initial guess for current
        self.voltage = 0.0  # Initial guess for voltage
    def read_current(self):
        if self.adc_channel is None:
            return None
        try:
            adc_value = self.adc_channel.convert_and_read()
            voltage = adc_value # * self.adc_channel.config_to_lsb(self.adc_channel.config) / self.adc_channel.config_to_gain(self.adc_channel.config) * self.adc_channel.scale_factor + self.adc_channel.offset
            current = voltage / 0.02  # Assuming a shunt resistor of 0.02 Ohm
            return current
        except Exception as error:
            print("Current measurement error:", error)
            return None
    def correct_resistance(self, set_voltage, read_current):
        # This is a placeholder for a more complex model that would adjust the effective thermal resistance based on current and temperature
        # For now, it just returns the base thermal resistance

        if(set_voltage is None or read_current is None):
            return self._R_joul 
        if(set_voltage < 0.5 or read_current < 0.1):  # accuracy thresholds for when to apply correction
            return self._R_joul
        corected_Rjoul = set_voltage/read_current  # Return default if we can't measure
        self._R_joul = corected_Rjoul  # Update the Joule resistance based on the latest measurement
        #print("Resistance correction: set_voltage={:.2f} V, read_current={:.2f} A, corrected_Rjoul={:.2f} Ohm".format(set_voltage, read_current, corected_Rjoul))
        return corected_Rjoul
    def correct_heat_loss(self, set_voltage, read_current):
        Qtot = read_current / 0.05  # Assuming a Seebeck coefficient of 0.05 V/K
        Qconduct = Qtot - read_current * read_current * self._R_joul  # Subtract estimated Joule heat loss from total heat transfer
        if(Qconduct > 0):
            calculated_heat_loss = (self.process_temp - self.setpoint_temp) / Qconduct 
            print("Heat loss correction: Qtot={:.2f} W, Qconduct={:.2f} W, calculated_heat_loss={:.2f} K".format(Qtot, Qconduct, calculated_heat_loss))
            return calculated_heat_loss

def writeToDac(value):
    buf = bytearray(2)
    buf[0] = (int(value) >> 8) & 0xFF
    buf[1] = int(value) & 0xFF
    i2c.writeto(0x60, buf)




#print("LED starts flashing...")

dev = i2c.scan()  # scan for devices on the I2C bus
for d in dev:
    print("I2C device found at address: ", hex(d))

if len(dev) == 0:
    print("No I2C devices found. Check your connections.")

ntc_Voltage_channel = MCP342x(i2c, 0x69, device='MCP3422', channel=0, resolution=18, gain=1,
                    scale_factor=1.0)
shunt_voltage = MCP342x(i2c, 0x69, device='MCP3422', channel=1, resolution=18, gain=1,
                    scale_factor=1.0)

#ntc = NTC(r_0=10000.0, beta=3950.0)
ntc = NTCreader(r_0=10000.0, beta=3950.0, adc_channel=ntc_Voltage_channel)
peltier = Peltier(R_joul=1.5, R_thermal=1, adc_channel=shunt_voltage)

# PI control (example parameters)
pi = PIController(
    kp=0.2,
    ki=0.0005,
    output_min=-4095,
    output_max=4095,
    meas_min=-10.0,
    meas_max=85.0,
    anti_windup=True,
    integrator_min=-10000,
    integrator_max=10000,
)
#pi.set_setpoint(30.0)  # target temperature
pi.enable()

V = 0.0
I = 0.0
I_ff = 0.0
I_set = 0.0
T = 0.0

T_set = 5.0  # Desired setpoint temperature in Celsius

setVoltage(0.0)  # Start with 0V output

peltier.updateSetpoint(T_set)  # Update the setpoint for the Peltier controller
#while True:
#    T = ntc.read_temperature() 

while True:

    if not pi.is_enabled():
        control_output = 0
    else:
        try:
            T = ntc.read_temperature() 

            sleep(0.5)  # Small delay to allow for ADC stabilization
            I = peltier.read_current()  # Update current measurement for potential resistance correction
            print("Measured temperature: {:.3f} °C, Current: {:.3f} A".format(T, I))
            # old volate
            R = peltier.correct_resistance(set_voltage=V, read_current=I)  # Update thermal resistance based on current conditions
            #V = peltier.feedforwardVoltage()  # Calculate feedforward voltage based on current temperature
            I_ff = peltier.feedforwardCurrent()  # Calculate feedforward current based on current temperature
            #i.update()
            u = - pi.update(T, dt=0.5)  # Update the PI controller with the current temperature measurement
            I_set = I_ff + u  # Combine feedforward current with PI controller output
            V = I_set * R  # Calculate the voltage needed to achieve the desired current based on the corrected resistance
            setVoltage(V)  # Apply feedforward voltage to the Peltier device
            #print("PI controller output (after feedforward): {:.2f}".format(u))
            print("T={:.3f} °C, I={:.3f} A, V={:.2f} V, R={:.2f} ohm".format(T, I, V, R))
            #print("Feedforward current: {:.3f} A, PI output: {:.2f}, Total set current: {:.3f} A".format(I_ff, u, I_set))
            #print("T={:.3f} °C, T_set={:.2f} °C, I={:.2f} A, I_ff={:.2f} A, I_set={:.2f} A, V={:.2f} V".format(T, T_set, I, I_ff, I_set, V))
             
            #control_output = pi.update(temp, dt=1.0)
        except Exception as err:
            print("Control update error:", err)
            pi.force_fault("open loop sensor failure")
            control_output = 0



while False:

    if not pi.is_enabled():
        control_output = 0
    else:
        try:
            T = ntc.read_temperature() 
            I = peltier.read_current()  # Update current measurement for potential resistance correction
            # old volate
            R = peltier.correct_resistance(set_voltage=V, read_current=I)  # Update thermal resistance based on current conditions

            V = peltier.feedforwardVoltage()  # Calculate feedforward voltage based on current temperature
             
            #control_output = pi.update(temp, dt=1.0)
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

# DAC test loop
while False:
    try:
        for i in range(0, 4096, 256):
            writeToDac(i)
            print("DAC value set to: ", i)
            sleep(1) # sleep 1sec
            pin.toggle()
    except KeyboardInterrupt:
        break

# adc test loop
while False:
    adc_values = [-1.0, -1.0]
    ntc = NTC(r_0=10000.0, beta=3950.0)
    try:
        adc_values[0] = ntc_Voltage_channel.convert_and_read()# * addr69_ch0.config_to_lsb(addr69_ch0.config) / addr69_ch0.config_to_gain(addr69_ch0.config) * addr69_ch0.scale_factor + addr69_ch0.offset
        adc_values[1] = shunt_voltage.convert_and_read()# * addr69_ch1.config_to_lsb(addr69_ch1.config) / addr69_ch1.config_to_gain(addr69_ch1.config) * addr69_ch1.scale_factor + addr69_ch1.offset
        print("ADC:{ch0:<10.6f},{ch1:<10.2f}".format(ch0=adc_values[0], ch1=adc_values[1]))
        print("Temperature: {temp:.2f} °C".format(temp=ntc.V_to_T(adc_values[0]) if adc_values[0] >= 0 else -999.0))
    except Exception as error:
        print("ADC read error:", error)
        
    sleep(1.0)

pin.off()
writeToDac(3000)  # disable output by setting to a safe value
print("Finished.")


