from trade_ibkr.app import run_ib_server
from trade_ibkr.model import OnExecutionFetchedEvent
from trade_ibkr.utils import print_log


def main():
    def store_executions():
        app = run_ib_server()

        async def fetched(e: OnExecutionFetchedEvent):
            for identifier, df in e.executions.execution_dataframes.items():
                dest = f"execution-{identifier}.csv"
                print_log(f"Saved to: {dest}")
                df.to_csv(dest)

            app.disconnect()

        app.set_on_executions_fetched(
            on_execution_fetched=fetched,
            on_execution_fetched_params=app._execution_on_fetched_params
        )
        app.request_all_executions()

    store_executions()


if __name__ == '__main__':
    main()
