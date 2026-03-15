from math import exp, log

# CONSTANTS
''' resistor divider circuit with NTC and bias resistor, powered by VCC reference voltage '''
VCC = 2.8  # Voltage In
R_BIAS = 20030.0  # Ohms, bias resistor value

T_0 = 298.15  # Kelvin
THERM_MIN = 263  # Kelvin, min expected thermistor value
THERM_MAX = 333  # Kelvin, max expected thermistor value
KELVIN_AT_0_CELSIUS = 273.15

class NTC:
    def __init__(self, r_0, beta):
        self.r_0 = r_0
        self.beta = beta
        self.r_min = r_0 * exp(self.beta * (1.0 / THERM_MIN - 1.0 / T_0))
        self.r_max = r_0 * exp(self.beta * (1.0 / THERM_MAX - 1.0 / T_0))

    def voltage_to_resistance(self, voltage):
        ''' compute NTC resisance from measured voltage ''' 
        return R_BIAS * voltage / (VCC - voltage)

    def resistance_to_kelvin(self, resistance):
        return 1.0 / (log(resistance / self.r_0) / self.beta + 1.0 / T_0)

    def kelvin_to_celsius(self, kelvin):
        return kelvin - KELVIN_AT_0_CELSIUS

    def resistance_to_celsius(self, resistance):
        return self.kelvin_to_celsius(self.resistance_to_kelvin(resistance))

    def V_to_T(self, voltage):
        resistance = self.voltage_to_resistance(voltage)
        return self.resistance_to_celsius(resistance)

    def read_T(self, get_voltage_func):
        voltage = get_voltage_func()
        return self.V_to_T(voltage)