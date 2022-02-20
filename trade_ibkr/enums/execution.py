class ExecutionDataCol:
    EPOCH_SEC = "epoch_sec"
    SIDE = "side"
    QUANTITY = "quantity"
    AVG_PX = "avg_price"
    REALIZED_PNL = "realized_pnl"

    # Names above must match the field name of `GroupedOrderExecution`

    REALIZED_PNL_SUM = "realized_pnl_sum"

    PX_SIDE = "px_side"
    PX_SIDE_SUM = "px_side_sum"

    PROFIT = "profit"
    LOSS = "loss"
    WIN_RATE = "wr"

    TOTAL_PROFIT = "total_profit"
    TOTAL_LOSS = "total_loss"

    AVG_PNL_PROFIT = "avg_pnl_profit"
    AVG_PNL_LOSS = "avg_pnl_loss"
    AVG_PNL_RR_RATIO = "avg_pnl_rr"
    AVG_PNL_EWR = "avg_pnl_ewr"

    TOTAL_PX_PROFIT = "total_px_profit"
    TOTAL_PX_LOSS = "total_px_loss"

    AVG_PX_PROFIT = "avg_px_profit"
    AVG_PX_LOSS = "avg_px_loss"
    AVG_PX_RR_RATIO = "avg_px_rr"
    AVG_PX_EWR = "avg_px_ewr"
