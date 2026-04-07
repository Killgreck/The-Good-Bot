# 🤖 Polymarket Copy-Trading Bot — gabagool22

Bot de copy-trading que monitorea la wallet **gabagool22** (`0xbeD5b3Bc6B2254698047a5230489647d5fdb58a0`) en la red Polygon y replica sus operaciones en Polymarket usando el SDK oficial `py-clob-client`.

## 🏗️ Arquitectura

```
The good Bot/
├── antigravity/            # Módulo principal
│   ├── __init__.py
│   ├── config.py           # Configuración (.env + validación)
│   ├── monitor.py          # Listener de eventos OrderFilled (web3.py)
│   ├── executor.py         # Replicación de órdenes (py-clob-client)
│   ├── utils.py            # Logging + helpers
│   └── abi/
│       └── ctf_exchange.json
├── tests/                  # Tests unitarios offline para pytest
├── scripts/
│   └── diagnostics/        # Scripts manuales con red/credenciales
├── main.py                 # Entry point
├── .env.example            # Template de configuración
├── .env                    # ⚠️ TU archivo de config (NO commitear)
└── requirements.txt
```

## ⚡ Quickstart

### 1. Instalar dependencias

```bash
cd "The good Bot"
pip install -r requirements.txt
```

### 2. Configurar `.env`

```bash
cp .env.example .env
nano .env  # Rellenar PRIVATE_KEY, FUNDER_ADDRESS, etc.
```

### 3. Ejecutar en modo prueba (DRY_RUN)

```bash
python main.py
```

El bot arrancará con `DRY_RUN=true` por defecto — solo loguea las operaciones que *haría* sin ejecutarlas.

### 4. Ejecutar tests

```bash
python -m pytest
```

Los tests bajo `tests/` son offline. Los scripts en `scripts/diagnostics/` son diagnósticos manuales y pueden usar red o credenciales.

### 5. Activar modo LIVE

En `.env`, cambiar:
```
DRY_RUN=false
```

> ⚠️ **PRECAUCIÓN**: El modo LIVE ejecuta órdenes reales con fondos USDC.

## 🔧 Configuración

| Variable | Descripción | Default |
|---|---|---|
| `POLYGON_RPC_URL` | Endpoint RPC de Polygon | `https://polygon-rpc.com` |
| `PRIVATE_KEY` | Llave privada de tu wallet | — |
| `FUNDER_ADDRESS` | Dirección de tu wallet | — |
| `POLYMARKET_API_KEY` | API key del CLOB | — |
| `POLYMARKET_API_SECRET` | API secret del CLOB | — |
| `POLYMARKET_API_PASSPHRASE` | Passphrase del CLOB | — |
| `SIGNATURE_TYPE` | 0=EOA, 1=Proxy | `0` |
| `MAX_USDC_PER_TRADE` | Límite USDC/operación | `50` |
| `SLIPPAGE_TOLERANCE` | Tolerancia al deslizamiento | `0.01` (1%) |
| `DRY_RUN` | Solo loguear, no ejecutar | `true` |
| `POLL_INTERVAL` | Intervalo de polling (seg) | `2.0` |

## 🛡️ Seguridad

- Las llaves privadas se leen **exclusivamente** del `.env` local
- **Cero** funciones que envíen datos a servidores externos
- Comunicación solo con: Polygon RPC + `clob.polymarket.com` (API oficial)
- El `.env` debe estar en `.gitignore`

## 🔄 Slippage Control

Si el precio del token se ha movido más del `SLIPPAGE_TOLERANCE` (1% por defecto) desde que gabagool22 operó, el bot **rechaza la orden** y loguea un warning. Esto previene entrar en trades a precios desfavorables.

## 🖥️ Deployment en GCP

```bash
# En tu instancia GCP:
git clone <tu-repo> && cd "The good Bot"
pip install -r requirements.txt
cp .env.example .env && nano .env

# Ejecutar con nohup para que sobreviva cierre de sesión:
nohup python main.py > /dev/null 2>&1 &

# O con tmux/screen:
tmux new -s copybot
python main.py
# Ctrl+B, D para detach
```

## 📊 Logs

Los logs se escriben en consola y en el archivo configurado en `LOG_FILE` (default: `copybot.log`):

```
[2026-04-03 12:00:01] [INFO   ] [copybot.monitor] 🔔 Trade detected! [Signal] BUY token=71321045289... price=0.6500 usdc=250.00 tokens=384.62 tx=0xabc123...
[2026-04-03 12:00:01] [INFO   ] [copybot.executor] ✅ Slippage OK: delta=0.31% (tolerance=1.00%)
[2026-04-03 12:00:02] [INFO   ] [copybot.executor] ✅ Order placed successfully: {...}
```
