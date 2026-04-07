from antigravity.executor import TradeExecutor
from antigravity.monitor import TradeSignal


def make_signal(price=0.50):
    return TradeSignal(
        token_id="123",
        side="BUY",
        price=price,
        usdc_amount=10.0,
        token_amount=20.0,
        tx_hash="0xabc",
        block_number=1,
        exchange="CTFExchange",
    )


def test_calculate_order_size_respects_max_usdc(monkeypatch):
    monkeypatch.setattr("antigravity.config.MAX_USDC_PER_TRADE", 50)

    executor = TradeExecutor.__new__(TradeExecutor)

    assert executor._calculate_order_size(0.25) == 200.0


def test_calculate_order_size_rejects_invalid_price():
    executor = TradeExecutor.__new__(TradeExecutor)

    assert executor._calculate_order_size(0) == 0.0
    assert executor._calculate_order_size(-1) == 0.0


def test_slippage_accepts_price_inside_tolerance(monkeypatch):
    monkeypatch.setattr("antigravity.config.SLIPPAGE_TOLERANCE", 0.10)
    executor = TradeExecutor.__new__(TradeExecutor)

    assert executor._check_slippage(make_signal(price=1.0), 1.05) is True


def test_slippage_rejects_price_outside_tolerance(monkeypatch):
    monkeypatch.setattr("antigravity.config.SLIPPAGE_TOLERANCE", 0.10)
    executor = TradeExecutor.__new__(TradeExecutor)

    assert executor._check_slippage(make_signal(price=1.0), 1.20) is False
