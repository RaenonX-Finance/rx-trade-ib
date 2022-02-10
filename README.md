# rx-trade-ib

Personal trading tool.

This does some calculation tasks, also host a socket server at `/ws/socket.io/` for sending data.

Check [rx-trade-ib-ui](https://github.com/RaenonX/rx-trade-ib-ui) for the accompanying UI.

## Usage

- This requires local TWS (Trade WorkStation) API.

### Install dependencies

```shell
pip install -r requirements.txt
```

### Start the program

#### Start the server

The server will host at `localhost:5000`. No `http` endpoints available.
However, `/ws/socket.io/` is accessible with `socket.io` client.

Using Windows PowerShell:

```shell
.run_server.ps1
```

Using Terminal:

```shell
py -m uvicorn main:fast_api --reload
```
