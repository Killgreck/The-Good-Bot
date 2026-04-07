#!/usr/bin/env python3
"""
Polymarket Copy-Trading Bot — Entry Point

Monitors gabagool22's wallet on Polygon for trades and replicates them
using the Polymarket CLOB SDK. All configuration via .env file.

Usage:
    python main.py
"""

import signal
import sys
import threading
from queue import Queue

# Ensure the project root is in the path
sys.path.insert(0, ".")

from dotenv import load_dotenv


def main():
    """Main entry point — orchestrates monitor and executor."""

    # Import config first (triggers .env load)
    from antigravity import config
    from antigravity.utils import setup_logger
    from antigravity.monitor import BlockchainMonitor
    from antigravity.executor import TradeExecutor

    logger = setup_logger("copybot")

    # ── Banner ──────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("  🤖 POLYMARKET COPY-TRADING BOT")
    logger.info("  Target: gabagool22")
    logger.info(f"  Wallet: {config.TARGET_WALLET}")
    logger.info(f"  Max/Trade: {config.MAX_USDC_PER_TRADE} USDC")
    logger.info(f"  Slippage: {config.SLIPPAGE_TOLERANCE:.1%}")
    logger.info(f"  Mode: {'🏜️  DRY RUN' if config.DRY_RUN else '🔴 LIVE'}")
    logger.info("=" * 60)

    # ── Validate config ─────────────────────────────────────────────
    config.validate()
    logger.info("✅ Configuration validated")

    # ── Shared queue for monitor → executor communication ────────
    signal_queue: Queue = Queue()

    # ── Initialize components ────────────────────────────────────
    try:
        monitor = BlockchainMonitor(signal_queue)
    except ConnectionError as e:
        logger.error(f"Cannot start monitor: {e}")
        sys.exit(1)

    executor = TradeExecutor(signal_queue)

    # ── Graceful shutdown handler ────────────────────────────────
    def shutdown(signum, frame):
        sig_name = signal.Signals(signum).name
        logger.info(f"\n🛑 Received {sig_name} — shutting down gracefully...")
        monitor.stop()
        executor.stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── Start monitor in a separate thread ───────────────────────
    monitor_thread = threading.Thread(
        target=monitor.run,
        name="blockchain-monitor",
        daemon=True,
    )
    monitor_thread.start()
    logger.info("Monitor thread started")

    # ── Run executor in main thread ──────────────────────────────
    try:
        executor.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
    finally:
        monitor.stop()
        monitor_thread.join(timeout=5)
        logger.info("👋 Bot shutdown complete")


if __name__ == "__main__":
    main()
