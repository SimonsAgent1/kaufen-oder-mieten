"""Page and terminal entry points. Both call the same comparison."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from buy_vs_rent.api import evaluate
from buy_vs_rent.scenario import load_scenario


def _euro(amount: float) -> str:
    return f"{amount:,.0f} €".replace(",", ".")


def _print_result(payload: dict) -> None:
    buy = payload["buy_final_real"]
    rent = payload["rent_final_real"]
    gap = buy - rent
    print(f"Kaufen: {_euro(buy)}")
    print(f"Mieten: {_euro(rent)}")
    print("Beträge in Euro von heute.")
    if payload.get("care_buy_real") is not None and payload.get("care_rent_real") is not None:
        care_buy = payload["care_buy_real"]
        care_rent = payload["care_rent_real"]
        care_gap = care_buy - care_rent
        print(
            f"Bei Pflegebeginn: Kaufen {_euro(care_buy)}, Mieten {_euro(care_rent)}, "
            f"Abstand {_euro(abs(care_gap))}"
        )
    horizon_buy = payload["buy_final_real"]
    horizon_rent = payload["rent_final_real"]
    horizon_gap = horizon_buy - horizon_rent
    print(
        f"Am Horizontende: Kaufen {_euro(horizon_buy)}, Mieten {_euro(horizon_rent)}, "
        f"Abstand {_euro(abs(horizon_gap))}"
    )
    if payload.get("life_sentence"):
        print(payload["life_sentence"])
    if payload.get("purchase_date"):
        print(f"Kauf: {payload['purchase_date']}")
    else:
        print("Kauf: keiner im Horizont")
    for warning in payload.get("warnings") or []:
        print(f"Hinweis: {warning}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="buy-vs-rent")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Seite im Browser öffnen")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--ssl-certfile", default=os.environ.get("BUY_VS_RENT_SSL_CERT"))
    serve.add_argument("--ssl-keyfile", default=os.environ.get("BUY_VS_RENT_SSL_KEY"))
    run = commands.add_parser("run", help="Eine Szenario-Datei rechnen")
    run.add_argument("file")
    run.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "serve":
        import uvicorn

        ssl_cert = args.ssl_certfile
        ssl_key = args.ssl_keyfile
        if (ssl_cert or ssl_key) and not (ssl_cert and ssl_key):
            raise SystemExit("serve: set both --ssl-certfile and --ssl-keyfile (or BUY_VS_RENT_SSL_CERT and BUY_VS_RENT_SSL_KEY).")
        uvicorn.run(
            "buy_vs_rent.api:app",
            host=args.host,
            port=args.port,
            ssl_certfile=ssl_cert,
            ssl_keyfile=ssl_key,
        )
        return
    scenario = load_scenario(Path(args.file))
    payload = evaluate(scenario)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
        return
    _print_result(payload)
