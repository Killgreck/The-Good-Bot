from antigravity.monitor import TradeSignal


def test_trade_signal_string_redacts_long_identifiers():
    signal = TradeSignal(
        token_id="12345678901234567890",
        side="BUY",
        price=0.65,
        usdc_amount=25.0,
        token_amount=38.4615,
        tx_hash="0xabcdef1234567890abcdef",
        block_number=123,
        exchange="CTFExchange",
    )

    rendered = str(signal)

    assert "BUY" in rendered
    assert "token=1234567890123456..." in rendered
    assert "price=0.6500" in rendered
    assert "usdc=25.00" in rendered
    assert "tx=0xabcdef12345678..." in rendered
