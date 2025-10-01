import time, requests
from datetime import datetime

URL = "https://simulador-de-financiamento.onrender.com"

while True:
    agora = datetime.now()
    # pausa os pings entre 2h e 4h da madrugada
    if not (2 <= agora.hour < 4):
        try:
            requests.get(URL, timeout=10)
            print(f"Ping enviado às {agora}")
        except Exception as e:
            print(f"Erro ao pingar: {e}")
    time.sleep(600)  # 10 minutos
