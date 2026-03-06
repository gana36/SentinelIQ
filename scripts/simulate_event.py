"""
Inject a scripted market event into the live pipeline for demo purposes.
Run: python scripts/simulate_event.py --ticker TSLA --event earnings_beat
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

EVENTS = {
    "earnings_beat": {
        "TSLA": "$TSLA just crushed Q4 earnings! EPS beat by 30%, revenue up 25% YoY. Elon Musk hinting at major product announcements. Cybertruck production ramping! 🚀",
        "NVDA": "$NVDA obliterates earnings estimates again. Data center revenue up 122% YoY. AI chip demand shows no signs of slowing. Blackwell GPU orders fully booked.",
        "AAPL": "Apple beats on revenue and EPS. iPhone 16 demand stronger than expected. Services segment at all-time high margins. Tim Cook raises guidance.",
    },
    "analyst_upgrade": {
        "TSLA": "Goldman Sachs upgrades $TSLA to Strong Buy, $350 price target. Autonomous driving progress ahead of schedule. Full Self-Driving v13 getting rave reviews.",
        "NVDA": "Morgan Stanley raises $NVDA price target to $1,500. AI infrastructure buildout accelerating faster than any prior tech supercycle.",
        "META": "JPMorgan upgrades $META to Overweight. Threads gaining traction. AI ad targeting improvements showing 15-20% ROAS improvements for advertisers.",
    },
    "earnings_miss": {
        "TSLA": "$TSLA misses on deliveries — only 425K vs 480K expected. Price wars intensifying. Margin compression continues. Bears vindicated?",
        "AMZN": "Amazon misses Q3 estimates. AWS growth slows to 17%. Increasing competition from Azure and Google Cloud. Stock dropping 8% after hours.",
        "NFLX": "Netflix disappoints — subscriber additions only 4M vs 9M expected. Password sharing crackdown hurting more than helping?",
    },
    "macro_event": {
        "SPY": "BREAKING: CPI comes in hotter than expected at 3.9% vs 3.5% forecast. Rate cut expectations slashed. $SPY selling off hard. Bonds also getting crushed.",
        "SPY2": "Fed Chair Powell signals rate cut at next FOMC meeting — inflation cooling faster than expected. Markets pricing in 3 cuts in 2025. Risk-on!",
    },
}

BASE_URL = "http://localhost:8000"


def get_token(email: str, password: str) -> str:
    resp = httpx.post(f"{BASE_URL}/api/v1/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json()["access_token"]


def inject(token: str, ticker: str, text: str, event_type: str) -> dict:
    resp = httpx.post(
        f"{BASE_URL}/api/v1/dev/inject-signal",
        json={"ticker": ticker, "text": text, "event_type": event_type},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="TSLA")
    parser.add_argument("--event", default="earnings_beat")
    parser.add_argument("--email", default="demo@sentineliq.ai")
    parser.add_argument("--password", default="demo1234")
    parser.add_argument("--text", default="")
    args = parser.parse_args()

    print(f"Authenticating as {args.email}...")
    token = get_token(args.email, args.password)

    text = args.text
    if not text:
        event_map = EVENTS.get(args.event, {})
        text = event_map.get(args.ticker) or event_map.get(list(event_map.keys())[0] if event_map else "")
        if not text:
            text = f"Breaking market signal for ${args.ticker}: {args.event} detected."

    print(f"Injecting signal: {args.ticker} / {args.event}")
    result = inject(token, args.ticker, text, args.event)
    print(f"Success! Signal ID: {result['signal_id']}")
    print("Watch your WebSocket connection for the alert...")


if __name__ == "__main__":
    main()
