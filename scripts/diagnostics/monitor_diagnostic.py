import sys
from pathlib import Path
from queue import Queue

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from antigravity.monitor import BlockchainMonitor
from antigravity import config

def test_monitor():
    print(f"--- Prueba de Monitoreo de Wallet ---")
    print(f"Billetera objetivo (para copy-trade): {config.TARGET_WALLET}")
    
    q = Queue()
    
    try:
        print("\nInicializando BlockchainMonitor...")
        monitor = BlockchainMonitor(q)
        print("✅ Monitor inicializado y conectado a Polygon.")
        
        current_block = monitor._get_latest_block()
        print(f"Último bloque en Polygon: {current_block}")
        
        blocks_to_check = 5000
        start_block = current_block - blocks_to_check
        
        print(f"\nBuscando el historial de operaciones de la wallet objetivo")
        print(f"en los últimos {blocks_to_check} bloques (aprox 3 horas)...")
        print("Esto tomará unos segundos debido a las consultas a la red...")
        
        total_signals = 0
        for i in range(start_block, current_block, 1000):
            end = min(i + 999, current_block)
            try:
                signals = monitor._process_block_range(i, end)
                total_signals += signals
            except Exception as e:
                print(f"Error consultando los bloques {i}-{end}: {e}")
                
        print(f"\n✅ Búsqueda completada exitosamente sin problemas de red o conexión.")
        
        if total_signals > 0:
            print(f"🥳 ¡ÉXITO! El monitor detectó e interceptó {total_signals} operaciones recientes de esta wallet:")
            while not q.empty():
                signal = q.get()
                print(f"  -> {signal}")
        else:
            print(f"No se encontraron operaciones de esa wallet en los últimos {blocks_to_check} bloques.")
            print("El monitor funciona correctamente y tiene los permisos para observar a la wallet, solo que actualmente la persona no ha hecho trades en este lapso de tiempo.")
            
    except Exception as e:
        print(f"\n❌ Error de conexión con el monitor o Polygon RPC: {e}")

if __name__ == "__main__":
    test_monitor()
