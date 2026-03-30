

class PeltierBase:
    def __init__(self, R_joul = 0.5, R_thermal = 1):
        self._R_joul = R_joul
        self._R_thermal = R_thermal
        self.setpoint_temp = 25.0
        self.process_temp = 25.0
    
    def updateSetpoint(self, setpoint):
        self.setpoint_temp = setpoint
    
    def feedforwardVoltage(self):
        Q_conduct = (self.process_temp - self.setpoint_temp) / self._R_thermal
        required_current = Q_conduct *0.05  # Assuming a Seebeck coefficient of 0.05 V/K
        Qloss = required_current * required_current * self._R_joul
        # very rough approximation of heat losses due to Joule heating, which is proportional to the square of the current and the Joule resistance

        required_current = (Q_conduct + Qloss) *0.05  # Assuming a Seebeck coefficient of 0.05 V/K

        required_voltage = required_current * self._R_joul
        print("Feedforward voltage calculation: Q_conduct={:.2f} W, Qloss={:.2f} W, required_current={:.2f} A, required_voltage={:.2f} V".format(Q_conduct, Qloss, required_current, required_voltage))
        return required_voltage



    def feedforwardCurrent(self):
        Q_conduct = (self.process_temp - self.setpoint_temp) / self._R_thermal
        required_current = Q_conduct *0.05  # Assuming a Seebeck coefficient of 0.05 V/K
        Qloss = required_current * required_current * self._R_joul
        # very rough approximation of heat losses due to Joule heating, which is proportional to the square of the current and the Joule resistance

        required_current = (Q_conduct + Qloss) *0.05  # Assuming a Seebeck coefficient of 0.05 V/K
        #print("Feedforward current calculation: Q_conduct={:.2f} W, Qloss={:.2f} W, required_current={:.2f} A".format(Q_conduct, Qloss, required_current))
        return required_current