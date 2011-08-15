from geventirc import message


def test_low_level_encode(self):
    data = "some mess\rage with\nspecial\0charaters"
    encoded = message.low_level_encode(data)
    assert encoded == ""



