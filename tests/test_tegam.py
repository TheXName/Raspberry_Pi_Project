from furnacepi.tegam3550 import parse_tegam_response


def test_parse_tegam_numeric_formats():
    reading = parse_tegam_response("C=1.2345E-09 D=-3.21E-04")

    assert reading.primary == 1.2345e-9
    assert reading.secondary == -3.21e-4
    assert reading.raw == "C=1.2345E-09 D=-3.21E-04"
