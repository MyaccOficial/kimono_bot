import subprocess
import sys
import threading
from watchfiles import run_process

def run_bot():
    return subprocess.Popen([sys.executable, "main.py"])

def monitor_terminal(process):
    """Fica escutando o terminal. Se você digitar 'exit' ou 'sair', ele desliga o bot."""
    while process.poll() is None:
        cmd = input()
        if cmd.lower() in ["exit", "sair", "desligar"]:
            print("🍂 Desligando o Kimono com segurança...")
            process.terminate()
            sys.exit(0)

if __name__ == "__main__":
    print("🌿 [Kimono Manager] Bot iniciado! Digite 'sair' ou 'exit' aqui no terminal a qualquer momento para desligá-lo.")
    print("🔄 O bot também reiniciará automaticamente se você salvar alterações no main.py.\n")
    
    # Inicia o bot
    bot_process = run_bot()
    
    # Roda a escuta do terminal em paralelo
    threading.Thread(target=monitor_terminal, args=(bot_process,), daemon=True).value = None
    
    # Mantém o watchfiles rodando para auto-reload ao salvar o main.py
    try:
        run_process('.', target=run_bot)
    except KeyboardInterrupt:
        print("\n🍂 Processo encerrado pelo usuário.")