"""
Configuration module — loads .env and validates required variables.
All secrets stay local. No external data exfiltration.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env from project root ──────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"

if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    print(f"[CONFIG] WARNING: .env not found at {_ENV_PATH}. Using environment variables.")

# ── Required variables ───────────────────────────────────────────────
PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
FUNDER_ADDRESS: str = os.getenv("FUNDER_ADDRESS", "")
POLYGON_RPC_URL: str = os.getenv("POLYGON_RPC_URL", "https://1rpc.io/matic")

POLYMARKET_API_KEY: str = os.getenv("POLYMARKET_API_KEY", "")
POLYMARKET_API_SECRET: str = os.getenv("POLYMARKET_API_SECRET", "")
POLYMARKET_API_PASSPHRASE: str = os.getenv("POLYMARKET_API_PASSPHRASE", "")

# ── Wallet type (0=EOA, 1=Poly Proxy) ───────────────────────────────
SIGNATURE_TYPE: int = int(os.getenv("SIGNATURE_TYPE", "0"))

# ── Trading parameters ──────────────────────────────────────────────
MAX_USDC_PER_TRADE: float = float(os.getenv("MAX_USDC_PER_TRADE", "50"))
SLIPPAGE_TOLERANCE: float = float(os.getenv("SLIPPAGE_TOLERANCE", "0.01"))  # 1%

# ── Execution mode ──────────────────────────────────────────────────
DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")

# ── Logging ─────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = os.getenv("LOG_FILE", "copybot.log")

# ── Constants (hardcoded — not configurable) ────────────────────────
CHAIN_ID: int = 137  # Polygon Mainnet

# Target wallet to copy-trade
TARGET_WALLET: str = "0xbeD5b3Bc6B2254698047a5230489647d5fdb58a0"

# Polymarket CTF Exchange contracts on Polygon
CTF_EXCHANGE: str = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
NEGRISK_CTF_EXCHANGE: str = "0xC5d563A36AE78145C45a50134d48A1215220f80a"

# Conditional Tokens Framework contract
CTF_CONTRACT: str = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"

# Polymarket CLOB host
CLOB_HOST: str = "https://clob.polymarket.com"

# Polling interval for new blocks (seconds)
POLL_INTERVAL: float = float(os.getenv("POLL_INTERVAL", "2.0"))

# ── ABI path ────────────────────────────────────────────────────────
ABI_DIR: Path = Path(__file__).resolve().parent / "abi"
CTF_EXCHANGE_ABI_PATH: Path = ABI_DIR / "ctf_exchange.json"


def validate() -> None:
    """Validate that all required configuration is present. Exits on failure."""
    errors: list[str] = []

    if not PRIVATE_KEY or PRIVATE_KEY == "your_private_key_here":
        errors.append("PRIVATE_KEY is not set or still has placeholder value")
    if not FUNDER_ADDRESS or FUNDER_ADDRESS == "your_wallet_address_here":
        errors.append("FUNDER_ADDRESS is not set or still has placeholder value")
    if not POLYGON_RPC_URL:
        errors.append("POLYGON_RPC_URL is not set")

    # API creds are needed for authenticated CLOB operations
    if not DRY_RUN:
        if not POLYMARKET_API_KEY:
            errors.append("POLYMARKET_API_KEY is required when DRY_RUN=false")
        if not POLYMARKET_API_SECRET:
            errors.append("POLYMARKET_API_SECRET is required when DRY_RUN=false")
        if not POLYMARKET_API_PASSPHRASE:
            errors.append("POLYMARKET_API_PASSPHRASE is required when DRY_RUN=false")

    if MAX_USDC_PER_TRADE <= 0:
        errors.append(f"MAX_USDC_PER_TRADE must be > 0 (got {MAX_USDC_PER_TRADE})")

    if not (0 < SLIPPAGE_TOLERANCE < 1):
        errors.append(f"SLIPPAGE_TOLERANCE must be between 0 and 1 (got {SLIPPAGE_TOLERANCE})")

    if errors:
        print("\n[CONFIG] ❌ Configuration errors:")
        for e in errors:
            print(f"  • {e}")
        print(f"\n  Copy .env.example → .env and fill in your values.")
        sys.exit(1)
