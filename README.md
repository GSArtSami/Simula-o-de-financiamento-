# Simulador Minha Casa Minha Vida (Flask + SQLite)

Este repositório contém o app Flask do simulador, já preparado para deploy em **Render.com** ou execução local via Docker/venv. O código já inclui as simulações (linha `expected`) — elas são inseridas automaticamente na primeira execução se não existirem.

---

## Estrutura de arquivos importantes

- `main.py` — aplicação Flask principal (já contém CSS/JS/HTML e a lógica do DB).
- `requirements.txt` — dependências Python (`Flask`, `gunicorn`).
- `Dockerfile` — imagem Docker para produção.
- `docker-compose.yml` — para testes locais com volume persistente.
- `.env.example` — template de variáveis de ambiente (NUNCA commitar credenciais reais).
- `static/` — assets (coloque `logo.jpg` aqui).

---

## Variáveis de ambiente necessárias

Defina essas variáveis no ambiente do host ou no painel do Render:

- `DB_PATH` — caminho absoluto do arquivo SQLite. **Recomendado**: `/var/data/simulador.db`
- `FLASK_SECRET` — segredo do Flask (sessões).
- `ADMIN_PASS` — senha para área administrativa.
- `EMAIL_USER` — (opcional) e-mail remetente para notificação.
- `EMAIL_PASS` — (opcional) senha ou app password.
- `SEND_EMAIL` — `0` para desativar envio, `1` para ativar.
- `PRAZO` — (opcional) prazo padrão em meses (ex: `420`).

---

## Executando localmente (modo rápido)

### Usando Python virtualenv (para desenvolvimento rápido)

```bash
# criar e ativar venv (Linux/macOS)
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt

# exporte variáveis (exemplo Linux/mac)
export DB_PATH=./simulador.db
export FLASK_SECRET=troque_este_valor
export ADMIN_PASS=minha_senha
export SEND_EMAIL=0

python main.py
# o app estará disponível em http://127.0.0.1:5000
