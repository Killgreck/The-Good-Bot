"""
Trade Executor — replicates trades via the Polymarket CLOB SDK.
Implements slippage control: skips orders if price moved > tolerance.
Only communicates with clob.polymarket.com (official API). No external exfiltration.
"""

import logging
from queue import Queue, Empty
from typing import Optional

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType

from . import config
from .monitor import TradeSignal
from .utils import setup_logger

logger = setup_logger("copybot.executor")


class TradeExecutor:
    """
    Consumes TradeSignal objects from the queue and replicates them
    on Polymarket via the CLOB SDK.
    """

    def __init__(self, signal_queue: Queue):
        self.signal_queue = signal_queue
        self._running = True

        # Initialize CLOB client
        self.client: Optional[ClobClient] = None
        if not config.DRY_RUN:
            self._init_clob_client()
        else:
            logger.info("🏜️  DRY_RUN mode — orders will be logged but NOT executed")

    def _init_clob_client(self) -> None:
        """Initialize the Polymarket CLOB client with credentials."""
        try:
            self.client = ClobClient(
                config.CLOB_HOST,
                key=config.PRIVATE_KEY,
                chain_id=config.CHAIN_ID,
                signature_type=config.SIGNATURE_TYPE,
                funder=config.FUNDER_ADDRESS,
            )

            # Set API credentials
            self.client.set_api_creds(self.client.create_or_derive_api_creds())

            # Verify connection
            server_time = self.client.get_server_time()
            logger.info(f"✅ CLOB client connected (server_time={server_time})")

        except Exception as e:
            logger.error(f"Failed to initialize CLOB client: {e}")
            raise

    def _get_current_price(self, token_id: str) -> Optional[float]:
        """
        Get the current best price for a token from the CLOB order book.
        Returns the best ask price for BUY, best bid for SELL.
        Returns None if no liquidity.
        """
        try:
            book = self.client.get_order_book(token_id)

            if not book:
                logger.warning(f"No order book found for token {token_id[:16]}...")
                return None

            # Best ask = lowest price someone is willing to sell at
            asks = book.asks if hasattr(book, 'asks') and book.asks else []
            bids = book.bids if hasattr(book, 'bids') and book.bids else []

            if asks:
                best_ask = float(asks[0].price)
                return best_ask
            elif bids:
                best_bid = float(bids[0].price)
                return best_bid
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to get order book for {token_id[:16]}...: {e}")
            return None

    def _check_slippage(self, signal: TradeSignal, current_price: float) -> bool:
        """
        Check if the price has moved too much since the target traded.
        Returns True if within tolerance, False if slippage exceeded.
        """
        if signal.price <= 0 or current_price <= 0:
            logger.warning(
                f"Invalid prices for slippage check: "
                f"signal={signal.price}, current={current_price}"
            )
            return False

        price_delta = abs(current_price - signal.price) / signal.price

        if price_delta > config.SLIPPAGE_TOLERANCE:
            logger.warning(
                f"⚠️  SLIPPAGE EXCEEDED — Skipping trade!\n"
                f"   Token:     {signal.token_id[:16]}...\n"
                f"   Side:      {signal.side}\n"
                f"   Price @tx: {signal.price:.4f}\n"
                f"   Price now: {current_price:.4f}\n"
                f"   Delta:     {price_delta:.4%} > {config.SLIPPAGE_TOLERANCE:.4%}"
            )
            return False

        logger.info(
            f"✅ Slippage OK: delta={price_delta:.4%} "
            f"(tolerance={config.SLIPPAGE_TOLERANCE:.4%})"
        )
        return True

    def _calculate_order_size(self, current_price: float) -> float:
        """
        Calculate the order size based on MAX_USDC_PER_TRADE and current price.
        Returns the number of tokens to buy/sell.
        """
        if current_price <= 0:
            return 0.0
        size = config.MAX_USDC_PER_TRADE / current_price
        return round(size, 2)  # Round to 2 decimals

    def _execute_order(self, signal: TradeSignal, current_price: float) -> bool:
        """
        Execute a copy-trade order via the CLOB SDK.
        Returns True on success, False on failure.
        """
        size = self._calculate_order_size(current_price)
        if size <= 0:
            logger.error("Calculated order size is 0 — skipping")
            return False

        logger.info(
            f"📤 Placing order:\n"
            f"   Side:     {signal.side}\n"
            f"   Token:    {signal.token_id[:16]}...\n"
            f"   Price:    {current_price:.4f}\n"
            f"   Size:     {size}\n"
            f"   USDC:     ~{size * current_price:.2f}\n"
            f"   Exchange: {signal.exchange}"
        )

        if config.DRY_RUN:
            logger.info("🏜️  DRY_RUN — Order NOT submitted")
            return True

        try:
            order_args = OrderArgs(
                token_id=signal.token_id,
                price=current_price,
                size=size,
                side=signal.side,
            )

            response = self.client.create_and_post_order(order_args)
            logger.info(f"✅ Order placed successfully: {response}")
            return True

        except Exception as e:
            logger.error(f"❌ Order execution failed: {e}")
            return False

    def process_signal(self, signal: TradeSignal) -> None:
        """Process a single trade signal with slippage control."""
        logger.info(f"📥 Processing signal: {signal}")

        # In dry-run mode without CLOB client, just log
        if config.DRY_RUN and self.client is None:
            logger.info(
                f"🏜️  DRY_RUN — Would {signal.side} token {signal.token_id[:16]}... "
                f"@ ~{signal.price:.4f} (max {config.MAX_USDC_PER_TRADE} USDC)"
            )
            return

        # Get current market price
        current_price = self._get_current_price(signal.token_id)
        if current_price is None:
            logger.warning(f"Cannot get current price — skipping signal")
            return

        # Slippage control
        if not self._check_slippage(signal, current_price):
            return

        # Execute the order
        self._execute_order(signal, current_price)

    def run(self) -> None:
        """
        Main executor loop. Consumes signals from the queue
        and processes them.
        """
        logger.info("🚀 Executor started — waiting for trade signals...")

        while self._running:
            try:
                signal = self.signal_queue.get(timeout=1.0)
                self.process_signal(signal)
                self.signal_queue.task_done()
            except Empty:
                continue  # No signal, keep waiting
            except Exception as e:
                logger.error(f"Error processing signal: {e}", exc_info=True)

        logger.info("Executor stopped")

    def stop(self) -> None:
        """Signal the executor to stop after current processing."""
        self._running = False
        logger.info("Executor stop requested")
