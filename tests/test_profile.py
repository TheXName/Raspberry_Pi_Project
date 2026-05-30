from furnacepi.profile import Segment, TemperatureProgram, ProportionalHeater


def test_temperature_program_ramp_and_hold():
    program = TemperatureProgram(25.0, [Segment(target_c=85.0, ramp_c_per_min=60.0, hold_s=10.0)])

    assert program.setpoint_at(0.0) == 25.0
    assert program.setpoint_at(30.0) == 55.0
    assert program.setpoint_at(60.0) == 85.0
    assert program.setpoint_at(65.0) == 85.0


def test_proportional_heater_limits_duty():
    controller = ProportionalHeater(band_c=20.0)

    assert controller.compute_duty(100.0, 110.0) == 0.0
    assert controller.compute_duty(100.0, 80.0) == 1.0
    assert controller.compute_duty(100.0, 90.0) == 0.5
