# The Good Bot

Este bot mira una billetera de Polymarket y copia sus operaciones.

La billetera que mira es:

```text
0xbeD5b3Bc6B2254698047a5230489647d5fdb58a0
```

Por defecto el bot NO compra ni vende. Arranca en modo prueba.

## Cuidado

Esto puede usar dinero real si activas el modo real.

No compartas tu archivo `.env`.

No subas tu llave privada a GitHub.

No pongas `DRY_RUN=false` si no entiendes el riesgo.

## Que Hace

El bot hace esto:

1. Mira la red Polygon.
2. Busca operaciones de la billetera objetivo.
3. Calcula si la operación se puede copiar.
4. Revisa que el precio no haya cambiado demasiado.
5. En modo prueba solo escribe logs.
6. En modo real puede enviar órdenes a Polymarket.

## Carpetas

```text
The good Bot/
├── antigravity/             Motor del bot
│   ├── config.py            Lee configuración
│   ├── monitor.py           Mira la blockchain
│   ├── executor.py          Copia operaciones
│   ├── utils.py             Logs y helpers
│   └── abi/                 Datos del contrato
├── scripts/diagnostics/     Pruebas manuales con internet
├── tests/                   Pruebas automáticas
├── main.py                  Archivo para arrancar el bot
├── .env.example             Ejemplo de configuración
├── requirements.txt         Librerías necesarias
└── README.md                Este archivo
```

## Instalar

Entra a la carpeta:

```bash
cd "The good Bot"
```

Instala librerías:

```bash
pip install -r requirements.txt
```

## Configurar

Copia el archivo de ejemplo:

```bash
cp .env.example .env
```

Abre `.env` y rellena tus datos:

```bash
nano .env
```

Datos importantes:

```text
PRIVATE_KEY=tu_llave_privada
FUNDER_ADDRESS=tu_wallet
DRY_RUN=true
```

Deja esto así al principio:

```text
DRY_RUN=true
```

Eso significa modo prueba.

## Probar Que Todo Vive

Corre los tests:

```bash
python -m pytest
```

Si todo está bien, debes ver algo parecido:

```text
10 passed
```

## Arrancar En Modo Prueba

```bash
python main.py
```

En modo prueba el bot mira y escribe logs, pero no manda órdenes reales.

## Activar Modo Real

Solo si sabes lo que haces.

Edita `.env`:

```text
DRY_RUN=false
```

Luego corre:

```bash
python main.py
```

Con `DRY_RUN=false`, el bot puede operar con dinero real.

## Logs

El bot escribe logs en consola y también en:

```text
copybot.log
```

Ese archivo no se sube a GitHub.

## Diagnósticos Manuales

Estos scripts pueden usar internet y credenciales:

```text
scripts/diagnostics/monitor_diagnostic.py
scripts/diagnostics/polymarket_diagnostic.py
scripts/diagnostics/rpc_debug_diagnostic.py
```

No son tests normales.

Úsalos solo cuando quieras revisar conexión con Polygon o Polymarket.

Ejemplo:

```bash
python scripts/diagnostics/monitor_diagnostic.py
```

## Seguridad Simple

Haz esto:

```text
Mantén .env privado.
Usa DRY_RUN=true para probar.
Lee logs antes de operar real.
Usa poco dinero si activas real.
```

No hagas esto:

```text
No subas .env.
No pegues tu PRIVATE_KEY en chats.
No operes real sin revisar configuración.
```
