"""
Blockchain Monitor — listens for OrderFilled events on Polygon.
Detects trades by gabagool22 and pushes signals to the executor queue.
"""

import json
import time
import threading
from dataclasses import dataclass
from queue import Queue
from typing import Optional

from web3 import Web3
from web3.contract import Contract

from . import config
from .utils import setup_logger, retry_with_backoff, format_usdc, format_token_amount

logger = setup_logger("copybot.monitor")


# ── Trade Signal dataclass ──────────────────────────────────────────
@dataclass
class TradeSignal:
    """Represents a detected trade from the target wallet."""

    token_id: str           # Conditional token ID (the market outcome)
    side: str               # "BUY" or "SELL"
    price: float            # Price per token at detection time
    usdc_amount: float      # Total USDC involved in the trade
    token_amount: float     # Total tokens involved
    tx_hash: str            # Transaction hash for reference
    block_number: int       # Block where the trade was detected
    exchange: str           # Which exchange contract emitted the event

    def __str__(self) -> str:
        return (
            f"[Signal] {self.side} token={self.token_id[:16]}... "
            f"price={self.price:.4f} usdc={self.usdc_amount:.2f} "
            f"tokens={self.token_amount:.2f} tx={self.tx_hash[:16]}..."
        )


class BlockchainMonitor:
    """
    Monitors the Polygon blockchain for OrderFilled events
    from the CTFExchange and NegRisk CTFExchange contracts.
    Filters for trades involving the target wallet (gabagool22).
    """

    def __init__(self, signal_queue: Queue):
        self.signal_queue = signal_queue
        self._stop_event = threading.Event()

        # Connect to Polygon (with timeout to avoid hanging on bad nodes)
        self.w3 = Web3(Web3.HTTPProvider(
            config.POLYGON_RPC_URL,
            request_kwargs={"timeout": 15},
        ))

        # NOTE: We avoid w3.is_connected() because it calls web3_clientVersion
        # which many public Polygon RPC nodes do NOT support/allow.
        # Instead, we verify connectivity with a real eth_blockNumber call.
        try:
            block = self.w3.eth.block_number
            if block == 0:
                raise ConnectionError("RPC returned block 0 — node may be broken")
            chain_id = self.w3.eth.chain_id
            logger.info(f"✅ Connected to Polygon RPC (chain_id={chain_id}, block={block})")
        except Exception as e:
            logger.error(f"Failed to connect to Polygon RPC: {config.POLYGON_RPC_URL} — {e}")
            raise ConnectionError(f"Cannot connect to Polygon RPC: {e}")

        # Load ABI
        with open(config.CTF_EXCHANGE_ABI_PATH, "r") as f:
            self.abi = json.load(f)

        # Create contract instances
        self.ctf_exchange = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.CTF_EXCHANGE),
            abi=self.abi,
        )
        self.negrisk_exchange = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.NEGRISK_CTF_EXCHANGE),
            abi=self.abi,
        )

        # Target wallet (checksummed)
        self.target = Web3.to_checksum_address(config.TARGET_WALLET)

        # Track last processed block
        self._last_block: Optional[int] = None

        logger.info(
            f"🎯 Monitoring target wallet: {self.target}\n"
            f"   CTF Exchange:     {config.CTF_EXCHANGE}\n"
            f"   NegRisk Exchange: {config.NEGRISK_CTF_EXCHANGE}\n"
            f"   Poll interval:    {config.POLL_INTERVAL}s"
        )

    def stop(self) -> None:
        """Signal the monitor to stop."""
        self._stop_event.set()
        logger.info("Monitor stop requested")

    @retry_with_backoff(max_retries=5, base_delay=2.0)
    def _get_latest_block(self) -> int:
        """Get the latest block number with retry."""
        return self.w3.eth.block_number

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def _get_events(
        self, contract: Contract, from_block: int, to_block: int
    ) -> list:
        """Fetch OrderFilled events from a contract in a block range."""
        event_filter = contract.events.OrderFilled.create_filter(
            fromBlock=from_block,
            toBlock=to_block,
        )
        return event_filter.get_all_entries()

    def _parse_trade(self, event, exchange_name: str) -> Optional[TradeSignal]:
        """
        Parse an OrderFilled event and determine if gabagool22 is the
        maker or taker. Returns a TradeSignal or None if not relevant.
        """
        args = event["args"]
        maker = args["maker"]
        taker = args["taker"]
        maker_asset_id = args["makerAssetId"]
        taker_asset_id = args["takerAssetId"]
        maker_amount = args["makerAmountFilled"]
        taker_amount = args["takerAmountFilled"]
        tx_hash = event["transactionHash"].hex()
        block_number = event["blockNumber"]

        # Check if target wallet is involved
        is_maker = (maker == self.target)
        is_taker = (taker == self.target)

        if not is_maker and not is_taker:
            return None

        # ── Determine BUY vs SELL ────────────────────────────────────
        # In CTFExchange:
        #   - makerAssetId = 0 means maker is providing USDC (collateral)
        #     → maker is BUYING conditional tokens
        #   - takerAssetId = 0 means taker is providing USDC
        #     → taker is BUYING conditional tokens
        #
        # We care about what gabagool22 is doing:
        if is_maker:
            if maker_asset_id == 0:
                # Maker provides USDC → BUYING tokens
                side = "BUY"
                token_id = str(taker_asset_id)
                usdc_amount = format_usdc(maker_amount)
                token_amount = format_token_amount(taker_amount)
            else:
                # Maker provides tokens → SELLING tokens
                side = "SELL"
                token_id = str(maker_asset_id)
                token_amount = format_token_amount(maker_amount)
                usdc_amount = format_usdc(taker_amount)
        else:  # is_taker
            if taker_asset_id == 0:
                # Taker provides USDC → BUYING tokens
                side = "BUY"
                token_id = str(maker_asset_id)
                usdc_amount = format_usdc(taker_amount)
                token_amount = format_token_amount(maker_amount)
            else:
                # Taker provides tokens → SELLING tokens
                side = "SELL"
                token_id = str(taker_asset_id)
                token_amount = format_token_amount(taker_amount)
                usdc_amount = format_usdc(maker_amount)

        # Calculate price per token
        price = usdc_amount / token_amount if token_amount > 0 else 0.0

        return TradeSignal(
            token_id=token_id,
            side=side,
            price=price,
            usdc_amount=usdc_amount,
            token_amount=token_amount,
            tx_hash=tx_hash,
            block_number=block_number,
            exchange=exchange_name,
        )

    def _process_block_range(self, from_block: int, to_block: int) -> int:
        """
        Process a range of blocks for OrderFilled events.
        Returns the number of signals detected.
        """
        signals_found = 0

        for contract, name in [
            (self.ctf_exchange, "CTFExchange"),
            (self.negrisk_exchange, "NegRiskCTFExchange"),
        ]:
            try:
                events = self._get_events(contract, from_block, to_block)
            except Exception as e:
                logger.error(f"Failed to fetch events from {name}: {e}")
                continue

            for event in events:
                signal = self._parse_trade(event, name)
                if signal:
                    logger.info(f"🔔 Trade detected! {signal}")
                    self.signal_queue.put(signal)
                    signals_found += 1

        return signals_found

    def run(self) -> None:
        """
        Main monitoring loop. Polls for new blocks and processes events.
        Runs until stop() is called.
        """
        logger.info("🚀 Monitor started — listening for gabagool22 trades...")

        # Initialize to current block
        try:
            self._last_block = self._get_latest_block()
            logger.info(f"Starting from block {self._last_block}")
        except Exception as e:
            logger.error(f"Cannot get initial block number: {e}")
            return

        while not self._stop_event.is_set():
            try:
                current_block = self._get_latest_block()

                if current_block > self._last_block:
                    from_block = self._last_block + 1
                    to_block = current_block

                    # Cap range to avoid oversized queries (max 1000 blocks)
                    if to_block - from_block > 1000:
                        to_block = from_block + 1000

                    signals = self._process_block_range(from_block, to_block)

                    if signals > 0:
                        logger.info(
                            f"Processed blocks {from_block}→{to_block}: "
                            f"{signals} signal(s) detected"
                        )

                    self._last_block = to_block

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)

            # Wait before next poll
            self._stop_event.wait(config.POLL_INTERVAL)

        logger.info("Monitor stopped")
