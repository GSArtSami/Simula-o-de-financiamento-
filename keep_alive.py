import time
import requests
from datetime import datetime

# URL do seu site no Render
URL ="https://simulador-de-financiamento.onrender.com"  
while True:

 def esta_no_horario_de_pausa():
    """Retorna True se estiver entre 02:00 e 04:00 (não envia ping nesse intervalo)."""
    agora = datetime.now()
    return 2 <= agora.hour < 4

 while True:
    if not esta_no_horario_de_pausa():
        try:
            r = requests.get(URL, timeout=10)
            print(f"[{datetime.now()}] Ping enviado - Status: {r.status_code}")
        except Exception as e:
            print(f"[{datetime.now()}] Erro ao pingar: {e}")
    else:
        print(f"[{datetime.now()}] Horário de pausa, não envia ping.")

    # Espera 10 minutos antes de repetir
    time.sleep(600)
