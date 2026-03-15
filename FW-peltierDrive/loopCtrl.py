"""MicroPython PI Controller library with state-machine, anti-windup, and sensor-failure detection."""

class PIController:
    STATE_DISABLED = 0
    STATE_ENABLED = 1
    STATE_FAULT = 2

    def __init__(
        self,
        kp,
        ki,
        output_min=0.0,
        output_max=4095.0,
        setpoint=0.0,
        meas_min=None,
        meas_max=None,
        anti_windup=True,
        integrator_min=None,
        integrator_max=None,
    ):
        self.kp = float(kp)
        self.ki = float(ki)
        self.output_min = float(output_min)
        self.output_max = float(output_max)
        self.setpoint = float(setpoint)

        self.meas_min = None if meas_min is None else float(meas_min)
        self.meas_max = None if meas_max is None else float(meas_max)

        self.anti_windup = bool(anti_windup)
        self.integrator_min = integrator_min
        self.integrator_max = integrator_max

        self.state = PIController.STATE_DISABLED
        self.fault_reason = ""
        self.integral = 0.0
        self.last_output = 0.0
        self.last_error = 0.0

    def enable(self):
        if self.state == PIController.STATE_FAULT:
            return False
        self.state = PIController.STATE_ENABLED
        self.fault_reason = ""
        return True

    def disable(self):
        self.state = PIController.STATE_DISABLED

    def reset(self):
        self.integral = 0.0
        self.last_output = 0.0
        self.last_error = 0.0
        self.fault_reason = ""
        if self.state == PIController.STATE_FAULT:
            self.state = PIController.STATE_DISABLED

    def force_fault(self, reason="fault"):
        self.state = PIController.STATE_FAULT
        self.fault_reason = str(reason)

    def clear_fault(self):
        if self.state == PIController.STATE_FAULT:
            self.state = PIController.STATE_DISABLED
            self.fault_reason = ""

    def set_setpoint(self, setpoint):
        self.setpoint = float(setpoint)

    def _is_valid_measurement(self, measurement):
        if measurement is None:
            return False
        try:
            # micropython may not have isnan if from math, so use self-check
            if measurement != measurement:
                return False
        except Exception:
            return False

        if self.meas_min is not None and measurement < self.meas_min:
            return False
        if self.meas_max is not None and measurement > self.meas_max:
            return False
        return True

    def update(self, measurement, dt=1.0):
        """Compute PI output from measurement with optional time step dt.

        Returns:
            float: controller output (clamped between output_min and output_max)
        """
        if self.state != PIController.STATE_ENABLED:
            return self.last_output

        if not self._is_valid_measurement(measurement):
            self.force_fault("sensor invalid or open loop")
            return self.last_output

        if dt is None or dt <= 0:
            dt = 1.0

        error = float(self.setpoint) - float(measurement)
        self.last_error = error

        self.integral += error * dt
        if self.integrator_min is not None and self.integral < self.integrator_min:
            self.integral = self.integrator_min
        if self.integrator_max is not None and self.integral > self.integrator_max:
            self.integral = self.integrator_max

        u_unsat = self.kp * error + self.ki * self.integral
        u = u_unsat
        if u > self.output_max:
            u = self.output_max
        elif u < self.output_min:
            u = self.output_min

        if self.anti_windup and self.ki != 0.0 and u != u_unsat:
            # Integrator back-calculation to prevent windup
            self.integral = (u - self.kp * error) / self.ki
            if self.integrator_min is not None and self.integral < self.integrator_min:
                self.integral = self.integrator_min
            if self.integrator_max is not None and self.integral > self.integrator_max:
                self.integral = self.integrator_max

        self.last_output = u
        return u

    def status(self):
        if self.state == PIController.STATE_ENABLED:
            return "enabled"
        if self.state == PIController.STATE_DISABLED:
            return "disabled"
        return "fault"

    def is_fault(self):
        return self.state == PIController.STATE_FAULT

    def is_enabled(self):
        return self.state == PIController.STATE_ENABLED

    def is_open_loop(self):
        return self.is_fault() and "open loop" in self.fault_reason.lower()
