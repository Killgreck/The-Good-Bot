import os
from pathlib import Path
from dotenv import load_dotenv
from py_clob_client.client import ClobClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

private_key = os.getenv("PRIVATE_KEY")
funder_address = os.getenv("WALLET_ADDRESS")  # or FUNDER_ADDRESS depending on env
host = "https://clob.polymarket.com"
chain_id = 137

print("Initializing ClobClient...")
# Initialize the client with just the private key
client = ClobClient(host, key=private_key, chain_id=chain_id)

try:
    print("Deriving API credentials (API Key, Secret, Passphrase)...")
    client.set_api_creds(client.create_or_derive_api_creds())
    
    print("\n✅ Conectado exitosamente!")
    
    print("\n-- Probando leer información del servidor --")
    # Quick connectivity test by getting the server time or markets
    server_time = client.get_server_time()
    print(f"Hora del servidor: {server_time}")
    
    print("\nTodo funciona bien. Tienes conectividad con Polymarket y las credenciales se derivaron correctamente.")
    print("No necesitas buscar el 'Secret' o 'Passphrase' manualmente porque la librería lo genera por ti a partir de la Private Key.")
except Exception as e:
    print(f"\n❌ Error de conexión: {e}")
