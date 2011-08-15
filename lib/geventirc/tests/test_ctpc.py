from geventirc import message


def test_low_level_quoting():
    data = "some mess\r\0age with\nspecial\0charaters"
    encoded = message.low_level_quote(data)
    assert encoded == 'some mess\x10r\x100age with\x10nspecial\x100charaters'
    assert data == message.low_level_dequote(data)

def test_ctcp_quoting():
    data = "some mess\r\0age with\nspeci:al\0charaters"
    encoded = message.low_level_quote(data)
    encoded = message.ctcp_quote(encoded)
    print repr(encoded)
    assert encoded == 'some mess\x10r\x100age with\x10nspeci :al\x100charaters'

