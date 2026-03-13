from trading_system.execution.orders import OrderRequest, OrderSide
from trading_system.strategy.base import SignalSide, StrategySignal


def signal_to_order_request(symbol: str, signal: StrategySignal) -> OrderRequest | None:
    if signal.side == SignalSide.HOLD or signal.quantity <= 0:
        return None

    side = OrderSide.BUY if signal.side == SignalSide.BUY else OrderSide.SELL
    return OrderRequest(symbol=symbol, side=side, quantity=signal.quantity)
