from antigravity.utils import format_token_amount, format_usdc


def test_format_usdc_uses_six_decimals():
    assert format_usdc(1_250_000) == 1.25


def test_format_token_amount_uses_six_decimals():
    assert format_token_amount(2_500_000) == 2.5
