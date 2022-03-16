class ExecutionDataCol:
    TIME_COMPLETED = "time_completed"
    EPOCH_SEC = "epoch_sec"
    SIDE = "side"
    QUANTITY = "quantity"
    AVG_PX = "avg_price"
    REALIZED_PNL = "realized_pnl"

    # Values above must match the field name of `GroupedOrderExecution`

    REALIZED_PNL_SUM = "realized_pnl_sum"

    PX_SIDE = "px_side"
    PX_SIDE_SUM = "px_side_sum"
    PX_SIDE_DIFF_SMA_RATIO = "px_side_diff_sma_ratio"

    PROFIT = "profit"
    LOSS = "loss"
    WIN_RATE = "wr"

    PROFIT_ON_LONG = "profit_long"
    LOSS_ON_LONG = "loss_long"
    WIN_RATE_ON_LONG = "wr_long"

    PROFIT_ON_SHORT = "profit_short"
    LOSS_ON_SHORT = "loss_short"
    WIN_RATE_ON_SHORT = "wr_short"

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
