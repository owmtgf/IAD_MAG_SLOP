from contextlib import contextmanager


@contextmanager
def atomic(state):
    snapshot = (state.stock.copy(), state.orders.copy(), state.ledger[:], state.shipments[:])
    try:
        yield
    except Exception:
        state.stock, state.orders, state.ledger, state.shipments = snapshot
        raise
