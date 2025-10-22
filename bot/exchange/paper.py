from dataclasses import dataclass


@dataclass
class Fill:
    side: str
    qty: int
    price: float
    cost: float


class PaperExchange:
    def __init__(self, starting_cash: float) -> None:
        self.cash = float(starting_cash)
        self.position = 0
        self.trades: list[Fill] = []
        self.avg_entry_price: float | None = None

    def market_buy(self, symbol: str, qty: int, price: float) -> Fill:
        cost = qty * price
        if cost > self.cash:
            qty = int(self.cash // price)
            cost = qty * price
            if qty <= 0:
                return Fill(side="buy", qty=0, price=price, cost=0.0)
        self.cash -= cost
        # Update average entry price using weighted average
        if self.position <= 0:
            self.avg_entry_price = price
        else:
            assert self.avg_entry_price is not None
            total_qty = self.position + qty
            self.avg_entry_price = (self.avg_entry_price * self.position + price * qty) / total_qty
        self.position += qty
        fill = Fill(side="buy", qty=qty, price=price, cost=cost)
        self.trades.append(fill)
        return fill

    def market_sell(self, symbol: str, qty: int, price: float) -> Fill:
        qty = min(qty, self.position)
        proceeds = qty * price
        self.cash += proceeds
        self.position -= qty
        fill = Fill(side="sell", qty=qty, price=price, cost=-proceeds)
        self.trades.append(fill)
        if self.position == 0:
            self.avg_entry_price = None
        return fill

    def unrealized_pnl(self, price: float) -> float:
        if self.position <= 0 or self.avg_entry_price is None:
            return 0.0
        return (price - self.avg_entry_price) * self.position
