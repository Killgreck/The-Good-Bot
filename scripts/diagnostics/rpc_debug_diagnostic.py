#!/usr/bin/env python3
"""
Diagnóstico completo: RPC + Monitor de wallet.
Prueba MUCHOS nodos RPC con headers apropiados, retries, y auto-configura.
"""
import re
import sys
import json
import time
import importlib
from pathlib import Path
from queue import Queue

print("=" * 60)
print("  DIAGNÓSTICO COMPLETO - RPC + MONITOR")
print("=" * 60)

# ── Step 1: Test internet ────────────────────────────────────────
print("\n[1/4] Verificando conexión a internet...")
import urllib.request
try:
    urllib.request.urlopen("https://httpbin.org/get", timeout=10)
    print("  ✅ Internet OK")
except Exception as e:
    print(f"  ❌ Sin internet: {e}")
    sys.exit(1)

# ── Step 2: Find working RPC ────────────────────────────────────
print("\n[2/4] Probando nodos RPC de Polygon (con retries)...\n")

RPC_ENDPOINTS = [
    ("1RPC",             "https://1rpc.io/matic"),
    ("Ankr",             "https://rpc.ankr.com/polygon"),
    ("PublicNode",       "https://polygon-bor-rpc.publicnode.com"),
    ("DrPC",             "https://polygon.drpc.org"),
    ("LlamaRPC",         "https://polygon.llamarpc.com"),
    ("Polygon Official", "https://polygon-rpc.com"),
    ("Blast API",        "https://polygon-mainnet.public.blastapi.io"),
    ("Unifra",           "https://polygon-mainnet-public.unifra.io"),
    ("BlockPI",          "https://polygon.blockpi.network/v1/rpc/public"),
    ("Chainnodes",       "https://polygon-mainnet.chainnodes.org"),
    ("Pokt",             "https://poly-rpc.gateway.pokt.network"),
    ("Alchemy Demo",     "https://polygon-mainnet.g.alchemy.com/v2/demo"),
    ("Chainstack",       "https://polygon-mainnet.core.chainstack.com"),
]

# Use browser-like headers to avoid being blocked
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "application/json",
}

payload = json.dumps({
    "jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1
}).encode("utf-8")

working_rpc = None
MAX_RETRIES = 3

for name, url in RPC_ENDPOINTS:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, data=payload, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())

            if "error" in data:
                print(f"  ❌ {name:20s} | RPC error: {data['error'].get('message','?')}")
                break

            block_num = int(data.get("result", "0x0"), 16)
            if block_num > 1000:
                print(f"  ✅ {name:20s} | Bloque: {block_num:,}")
                if working_rpc is None:
                    working_rpc = (name, url)
                break
            else:
                if attempt < MAX_RETRIES:
                    time.sleep(1)
                    continue
                print(f"  ⚠️  {name:20s} | Bloque: {block_num} (inválido)")
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(1)
                continue
            print(f"  ❌ {name:20s} | {str(e)[:60]}")

if not working_rpc:
    print("\n  ❌ Ningún nodo respondió correctamente.")
    print("\n  SOLUCIÓN: Necesitas un nodo RPC privado (gratuito).")
    print("  1. Ve a https://alchemy.com y crea una cuenta gratis")
    print("  2. Crea una app → selecciona 'Polygon PoS'")
    print("  3. Copia la URL del endpoint HTTPS")
    print("  4. Pega en tu .env: POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/TU_KEY")
    print("  5. Vuelve a ejecutar: python test_rpc_debug.py")
    sys.exit(1)

best_name, best_url = working_rpc
print(f"\n  🏆 Mejor nodo: {best_name} → {best_url}")

# ── Step 3: Auto-update .env and config.py ──────────────────────
print("\n[3/4] Actualizando configuración...")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    content = env_path.read_text()
    if "POLYGON_RPC_URL=" in content:
        content = re.sub(r"POLYGON_RPC_URL=.*", f"POLYGON_RPC_URL={best_url}", content)
    else:
        content = f"POLYGON_RPC_URL={best_url}\n" + content
    env_path.write_text(content)
    print(f"  ✅ .env → {best_name}")

config_path = PROJECT_ROOT / "antigravity" / "config.py"
if config_path.exists():
    cfg = config_path.read_text()
    cfg = re.sub(
        r'POLYGON_RPC_URL: str = os\.getenv\("POLYGON_RPC_URL", ".*?"\)',
        f'POLYGON_RPC_URL: str = os.getenv("POLYGON_RPC_URL", "{best_url}")',
        cfg,
    )
    config_path.write_text(cfg)
    print(f"  ✅ config.py → {best_name}")

# ── Step 4: Run monitor test ────────────────────────────────────
print("\n[4/4] Ejecutando test del monitor de wallet...\n")
print("-" * 60)

sys.path.insert(0, str(PROJECT_ROOT))
from dotenv import load_dotenv
load_dotenv(env_path, override=True)

from antigravity import config
importlib.reload(config)
from antigravity.monitor import BlockchainMonitor

print(f"Wallet objetivo (copy-trade): {config.TARGET_WALLET}")
print(f"RPC en uso: {config.POLYGON_RPC_URL}")

q = Queue()
try:
    print("\nInicializando BlockchainMonitor...")
    monitor = BlockchainMonitor(q)
    print("✅ Monitor conectado!")

    current_block = monitor._get_latest_block()
    print(f"Último bloque: {current_block:,}")

    blocks_to_check = 5000
    start_block = current_block - blocks_to_check
    print(f"\nEscaneando últimos {blocks_to_check} bloques...\n")

    total_signals = 0
    for i in range(start_block, current_block, 1000):
        end = min(i + 999, current_block)
        try:
            signals = monitor._process_block_range(i, end)
            total_signals += signals
            pct = min(100, int((i - start_block) / blocks_to_check * 100))
            print(f"  Bloques {i:,}→{end:,} ... {pct}% {'🔔' * signals if signals else '✓'}")
        except Exception as e:
            print(f"  ⚠️  Bloques {i:,}→{end:,}: {e}")

    print(f"\n{'=' * 60}")
    print(f"  RESULTADO FINAL")
    print(f"{'=' * 60}")
    print(f"  ✅ Conexión RPC: OK ({best_name})")
    print(f"  ✅ Monitor de wallet: FUNCIONAL")
    print(f"  ✅ Wallet objetivo: {config.TARGET_WALLET}")

    if total_signals > 0:
        print(f"  🔔 Trades detectados: {total_signals}")
        while not q.empty():
            print(f"     → {q.get()}")
    else:
        print(f"  ℹ️  Sin trades recientes (normal si no operó en las últimas horas)")

    print(f"\n  🚀 Todo listo. Puedes ejecutar: python main.py")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
