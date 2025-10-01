import threading, time, requests
from datetime import datetime

def keep_alive():
    url = "https://simulador-de-financiamento.onrender.com"  # substitua pelo link do Render
    while True:
        agora = datetime.now()
        if not (2 <= agora.hour < 4):  # pausa entre 2h e 4h
            try:
                r = requests.get(url, timeout=10)
                print(f"[KEEP-ALIVE] Ping enviado às {agora:%H:%M}, status {r.status_code}")
            except Exception as e:
                print(f"[KEEP-ALIVE] Erro ao pingar: {e}")
        time.sleep(600)  # 10 minutos

# inicia o keep-alive em paralelo
threading.Thread(target=keep_alive, daemon=True).start()


from flask import Flask, request, session, redirect, url_for, g, render_template_string
import sqlite3
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import html
import threading

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# --- Configurações (levadas de variáveis de ambiente) ---
DB = os.getenv('DB_PATH', 'simulador.db')  # em Render prefira /var/data/simulador.db
_db_dir = os.path.dirname(DB)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)

app.secret_key = os.getenv('FLASK_SECRET', 'segredo123')
ADMIN_PASS = os.getenv('ADMIN_PASS', 'jm.eng2025')
PRAZO = int(os.getenv('PRAZO', '420'))

EMAIL_USER = os.getenv('EMAIL_USER', 'jmengenhariaobras@gmail.com')
EMAIL_PASS = os.getenv('EMAIL_PASS', 'vehg bguy tirc qfjm ')
SEND_EMAIL = os.getenv('SEND_EMAIL', '1')  # '0' desativa envio

# --- Estilo / HTML (cacheado em memória para evitar reconstrução constante) ---
STYLE = """
<link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'>
<link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'>
<script src='https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js'></script>
<script src='https://cdnjs.cloudflare.com/ajax/libs/jquery.mask/1.14.16/jquery.mask.min.js'></script>
<style>
  body { background: linear-gradient(135deg, #0d1117, #161b22); font-family: 'Segoe UI', sans-serif; color: #e6e6e6; }
  .logo { display: block; margin: 0 auto 20px; max-height: 90px; filter: drop-shadow(0 0 4px rgba(0, 191, 255, 0.4)); }
  .box { max-width: 850px; margin: 40px auto; padding: 25px; border-radius: 20px; background: #1e242c; box-shadow: 0 0 25px rgba(0, 191, 255, 0.08); transition: transform 0.3s ease, box-shadow 0.3s ease; }
  .box:hover { transform: translateY(-3px); box-shadow: 0 0 30px rgba(0, 191, 255, 0.15); }
  .btn-custom { border-radius: 50px; padding: 12px 24px; font-weight: 600; border: none; letter-spacing: 0.3px; transition: all 0.3s ease-in-out; box-shadow: 0 0 8px rgba(0, 0, 0, 0.3); }
  .btn-primary { background: linear-gradient(135deg, #001f3f, #0056b3); color: #fff; box-shadow: 0 0 12px rgba(0, 123, 255, 0.4); }
  .btn-primary:hover { background: linear-gradient(135deg, #0056b3, #00bfff); box-shadow: 0 0 20px rgba(0, 191, 255, 0.8); transform: scale(1.05); }
  .btn-danger { background: linear-gradient(135deg, #8b0000, #dc3545); color: #fff; box-shadow: 0 0 12px rgba(220, 53, 69, 0.4); }
  .btn-danger:hover { background: linear-gradient(135deg, #dc3545, #ff6b6b); box-shadow: 0 0 20px rgba(255, 99, 99, 0.7); transform: scale(1.05); }
  .btn-secondary { background: linear-gradient(135deg, #2c2f36, #3e434a); color: #fff; border: 1px solid #00bfff; box-shadow: 0 0 10px rgba(0, 191, 255, 0.2); }
  .btn-whatsapp { background: linear-gradient(135deg, #25D366, #128C7E); color: #fff; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 12px rgba(37, 211, 102, 0.4); }
  table { color: #e6e6e6; background-color: #1c2128; }
  table th, table td { vertical-align: middle !important; border-color: rgba(255,255,255,0.05); background-color: #1c2128; }
  table thead { background-color: #2a2f38; text-transform: uppercase; letter-spacing: 0.5px; }
  table tbody tr:hover { background-color: rgba(0, 191, 255, 0.08); }
</style>
<script>$(function(){ $('#telefone').mask('(00) 00000-0000'); });</script>
"""

# Dropdown options (constantes cacheadas)
RENDA_OPTS = [
    'até 1.500 reais','até 2.160 reais','até 2.850 reais','até 3.500 reais',
    'até 4.000 reais','até 4.700 reais','até 8.600 reais','acima de 10.000 reais'
]
IMOVEL_OPTS = ['imovel ate 210k','imovel ate 350k','imovel ate 500k']
RENDA_HTML = ''.join(f"<option value='{r}'>{r}</option>" for r in RENDA_OPTS)
IMOVEL_HTML = ''.join(f"<option value='{i}'>{i}</option>" for i in IMOVEL_OPTS)

# --- Utils rápidos ---
def fmt(v):
    # formata número para "x.xxx,xx" sem lançar exceção em strings/None
    try:
        return f"{float(v):,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except Exception:
        return v if v is not None else ""

# --- Database helpers: conexões por request, pragmas para melhor desempenho ---
def get_db():
    if 'db' not in g:
        conn = sqlite3.connect(DB, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Pragmas que melhoram concorrência em muitos cenários de leitura/escrita em SQLite
        try:
            conn.execute('PRAGMA journal_mode=WAL;')
            conn.execute('PRAGMA synchronous=NORMAL;')
        except Exception:
            # Pragmas podem falhar em alguns ambientes; não interromper a aplicação
            logging.debug('Pragmas SQLite não aplicados (ambiente pode não suportar).')
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Inicialização do DB (mantive a lógica e dados originais) ---
def init_db():
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS cliente (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT, telefone TEXT, renda TEXT, valor_imovel TEXT,
            entrada REAL, entrada_calculada REAL, valor_financiado REAL,
            parcela_price REAL, parcela_sac_ini REAL, parcela_sac_fim REAL,
            prazo INTEGER, faixa TEXT, juros REAL, subsidio REAL, fgts REAL,
            aprovado INTEGER, criado_em TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS simulacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            renda TEXT, imovel TEXT,
            juros REAL, entrada REAL, subsidio REAL, valor_liberado REAL,
            sac_primeira REAL, sac_ultima REAL, price_primeira REAL, price_ultima REAL
        )''')

        expected = [
            # (mesmas linhas que você tinha — preserved)
            ('até 1.500 reais','imovel ate 210k',4.85,131243.97,13090.00,65666.03,450.00,156.97,354.74,321.01),
            ('até 2.160 reais','imovel ate 210k',4.85,107186.00,6313.00,96501.00,647.99,230.67,508.00,471.75),
            ('até 2.850 reais','imovel ate 210k',5.12,83279.90,2028.00,124692.10,855.00,298.12,667.88,629.31),
            ('até 3.500 reais','imovel ate 210k',5.64,68555.16,0.00,141444.84,1050.00,363.32,824.52,784.58),
            ('até 4.000 reais','imovel ate 210k',6.17,56352.99,0.00,153647.01,1200.00,392.66,942.02,901.08),
            ('até 4.700 reais','imovel ate 210k',7.23,46473.70,0.00,163526.30,1410.00,416.62,1111.45,1069.70),
            ('até 8.600 reais','imovel ate 210k',8.47,42000.00,0.00,168000.00,1609.51,427.71,1279.93,1237.81),
            ('acima de 10.000 reais','imovel ate 210k',10.47,42000.00,0.00,168000.00,1867.11,428.32,1511.37,1469.25),

            ('até 1.500 reais','imovel ate 350k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),
            ('até 2.160 reais','imovel ate 350k',8.47,287842.70,0.00,62157.30,647.99,174.01,526.05,473.72),
            ('até 2.850 reais','imovel ate 350k',8.47,265495.61,2028.00,84504.39,855.00,22.58,689.22,635.05),
            ('até 3.500 reais','imovel ate 350k',8.47,244444.00,0.00,105556.00,1049.99,278.03,842.91,787.02),
            ('até 4.000 reais','imovel ate 350k',8.47,228250.45,0.00,121749.55,1200.00,316.85,961.14,903.92),
            ('até 4.700 reais','imovel ate 350k',8.47,205579.49,0.00,144420.51,1410.00,371.20,1126.67,1067.59),
            ('até 8.600 reais','imovel ate 350k',8.47,79269.84,0.00,270730.16,2580.00,673.98,2048.87,1979.43),
            ('acima de 10.000 reais','imovel ate 350k',10.47,70000.00,0.00,280000.00,3095.19,697.22,2502.28,2432.08),

            ('até 1.500 reais','imovel ate 500k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),
            ('até 2.160 reais','imovel ate 500k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),
            ('até 2.850 reais','imovel ate 500k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),
            ('até 3.500 reais','imovel ate 500k',10.47,389670.37,0.00,110329.93,0.00,0.00,1050.00,973.47),
            ('até 4.000 reais','imovel ate 500k',10.47,397416.52,0.00,102583.48,1200.00,271.28,982.77,906.88),
            ('até 4.700 reais','imovel ate 500k',10.47,348189.60,0.00,151810.40,1410.00,317.98,1151.59,1074.10),
            ('até 8.600 reais','imovel ate 500k',10.47,269594.72,0.00,230405.28,2580.00,578.15,2580.00,2489.02),
            ('acima de 10.000 reais','imovel ate 500k',10.47,100000.00,0.00,400000.00,3600.00,804.98,3563.97,3463.69),
        ]

        inserted = 0
        for row in expected:
            cur.execute('SELECT COUNT(*) FROM simulacao WHERE renda=? AND imovel=?', (row[0], row[1]))
            if cur.fetchone()[0] == 0:
                cur.execute('''INSERT INTO simulacao (renda,imovel,juros,entrada,subsidio,valor_liberado,
                               sac_primeira,sac_ultima,price_primeira,price_ultima)
                               VALUES (?,?,?,?,?,?,?,?,?,?)''', row)
                inserted += 1

        if inserted:
            conn.commit()
            logging.info('Inseridas %d simulações faltantes na tabela simulacao', inserted)
        conn.close()
    except Exception as e:
        logging.exception('Erro ao inicializar DB: %s', e)

# chama inicialização uma vez ao start
init_db()

# --- Pequena função de mapeamento (mantida) ---
def faixa_por_renda(r):
    m = {
        'até 1.500 reais':'Faixa 1','até 2.160 reais':'Faixa 1','até 2.850 reais':'Faixa 1',
        'até 3.500 reais':'Faixa 2','até 4.000 reais':'Faixa 2','até 4.700 reais':'Faixa 2',
        'até 8.600 reais':'Faixa 3','acima de 10.000 reais':'Faixa 4'
    }
    return m.get(r,'Faixa desconhecida')

# --- Envio de email (agora rodando em thread para não bloquear resposta) ---
def _send_email_blocking(nome, tel, renda, imovel, price, sac_ini, sac_fim, faixa):
    if SEND_EMAIL == '0' or not EMAIL_USER or not EMAIL_PASS:
        logging.info('Envio de email desativado por variável de ambiente ou credenciais ausentes')
        return
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER
    msg['Subject'] = 'Nova simulação'
    body = f"""
Nova simulação realizada:
Nome: {nome}
Telefone: {tel}
Renda: {renda}
Imóvel: {imovel}
Faixa: {faixa}
1ª Parcela PRICE (parcela fixa): R$ {fmt(price)}
1ª Parcela SAC: R$ {fmt(sac_ini)}
Última Parcela SAC: R$ {fmt(sac_fim)}
"""
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
            logging.info('Email enviado para %s', EMAIL_USER)
    except Exception:
        logging.exception('Falha ao enviar email (verifique credenciais/SMTP)')

def send_email_async(nome, tel, renda, imovel, price, sac_ini, sac_fim, faixa):
    # Dispara thread daemon para não bloquear o request. Erros são logados dentro da função blocking.
    try:
        t = threading.Thread(target=_send_email_blocking, args=(nome, tel, renda, imovel, price, sac_ini, sac_fim, faixa), daemon=True)
        t.start()
    except Exception:
        logging.exception('Falha ao iniciar thread de envio de email')

# --- Rotas (otimizadas: queries mínimas e uso de get_db) ---
@app.route('/')
def home():
    logo_url = url_for('static', filename='logo.jpg')
    # Renderiza com render_template_string para ter menos concatenação manual
    html_doc = STYLE + f"""
        <img src="{logo_url}" class="logo">
        <div class="box">
          <h3>Simulador Minha Casa Minha Vida</h3>
          <form method='post' action='/simular'>
            <input name='nome' placeholder='Nome*' class='form-control mb-2' required>
            <input name='telefone' placeholder='Telefone*' id='telefone' class='form-control mb-2' required>
            <select name='renda' class='form-select mb-2' required>{RENDA_HTML}</select>
            <select name='valor_imovel' class='form-select mb-2' required>{IMOVEL_HTML}</select>
            <button class='btn-custom btn-primary w-100'>Simular</button>
          </form>
        </div>"""
    return render_template_string(html_doc)

@app.route('/simular', methods=['POST'])
def simular():
    form = request.form
    nome, tel = form.get('nome'), form.get('telefone')
    renda, imovel = form.get('renda'), form.get('valor_imovel')

    if not all([nome, tel, renda, imovel]):
        return 'Dados incompletos', 400

    conn = get_db()
    cur = conn.cursor()
    # busca única, evita abrir nova conexão
    cur.execute('SELECT * FROM simulacao WHERE renda=? AND imovel=?', (renda, imovel))
    s = cur.fetchone()
    if s is None:
        return "Simulação não encontrada para a combinação selecionada.", 400

    price, sac_ini, sac_fim = s['price_primeira'], s['sac_primeira'], s['sac_ultima']
    faixa = faixa_por_renda(renda)
    criado = datetime.now().strftime('%d/%m/%Y %H:%M')

    # Insere cliente — usa cursor.lastrowid para obter id sem nova query
    cur.execute(
        '''INSERT INTO cliente (nome, telefone, renda, valor_imovel, entrada, entrada_calculada, valor_financiado,
                               parcela_price, parcela_sac_ini, parcela_sac_fim, prazo, faixa, juros, subsidio, fgts, aprovado, criado_em)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (nome, tel, renda, imovel, s['entrada'], s['entrada'], s['valor_liberado'],
         price, sac_ini, sac_fim, PRAZO, faixa, s['juros'], s['subsidio'], 0, 1, criado)
    )
    conn.commit()
    cid = cur.lastrowid

    # Envia email de forma assíncrona (thread) — não altera lógica do email em si
    try:
        send_email_async(nome, tel, renda, imovel, price, sac_ini, sac_fim, faixa)
    except Exception:
        logging.exception('Erro ao iniciar envio de email (ignorado para não afetar UX)')

    return redirect(url_for('resultado', id=cid))

@app.route('/resultado/<int:id>')
def resultado(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM cliente WHERE id=?', (id,))
    c = cur.fetchone()
    if not c:
        return 'Simulação não encontrada', 404

    # escape para evitar XSS básico
    nome = html.escape(c['nome'])
    telefone = html.escape(c['telefone'])
    renda_txt = html.escape(c['renda'])
    imovel_txt = html.escape(c['valor_imovel'])
    faixa_txt = html.escape(c['faixa'])
    # índices preservados conforme esquema original
    # OBS: dentro do cliente, parcela_price é 'parcela_price' -> índice 8 no esquema inicial; porém usamos dict access acima
    parcela_price = c['parcela_price']
    parcela_sac_ini = c['parcela_sac_ini']
    parcela_sac_fim = c['parcela_sac_fim']
    criado_txt = html.escape(c['criado_em'])

    logo_url = url_for('static', filename='logo.jpg')

    html_doc = STYLE + f"""
        <img src="{logo_url}" class="logo">
        <div class="box">
          <h3>Resultado da Simulação</h3>
          <table class='table'>
            <tr><th>Nome</th><td>{nome}</td></tr>
            <tr><th>Telefone</th><td>{telefone}</td></tr>
            <tr><th>Renda</th><td>{renda_txt}</td></tr>
            <tr><th>Imóvel</th><td>{imovel_txt}</td></tr>
            <tr><th>Faixa</th><td>{faixa_txt}</td></tr>
            <tr><th>1ª Parcela PRICE (parcela fixa)</th><td>R$ {fmt(parcela_price)}</td></tr>
            <tr><th>1ª Parcela SAC</th><td>R$ {fmt(parcela_sac_ini)}</td></tr>
            <tr><th>Última Parcela SAC</th><td>R$ {fmt(parcela_sac_fim)}</td></tr>
            <tr><th>Prazo</th><td>{c['prazo']} meses</td></tr>
            <tr><th>Data/Hora</th><td>{criado_txt}</td></tr>
          </table>

          <a href="https://api.whatsapp.com/send?phone=5538998721022&text=Ol%C3%A1,%20podemos%20conversar%20sobre%20minha%20futura%20casa?%20nome:%20{nome},%20Renda:%20{renda_txt},%20Im%C3%B3vel:%20{imovel_txt},%20Faixa:%20{faixa_txt},%201%C2%AA%20Parcela%20PRICE:%20R$%20{fmt(parcela_price)},%201%C2%AA%20Parcela%20SAC:%20R$%20{fmt(parcela_sac_ini)},%20%C3%9Altima%20SAC:%20{fmt(parcela_sac_fim)}" target="_blank" class="btn-custom btn-whatsapp w-100 mb-2">
            <i class="fab fa-whatsapp"></i>Começar Consultoria
          </a>

          <a href='/' class='btn-custom btn-primary w-100 mb-2 d-flex align-items-center justify-content-center'>Nova Simulação</a>
        </div>"""
    return render_template_string(html_doc)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and request.form.get('senha') == ADMIN_PASS:
        session['admin'] = True
        return redirect(url_for('admin'))
    logo_url = url_for('static', filename='logo.jpg')
    html_doc = STYLE + f"""
    <div class='box'>
      <img src='{logo_url}' class='logo'>
      <h3>Login Administrativo</h3>
      <form method='post'>
        <input type='password' name='senha' class='form-control mb-2' placeholder='Senha' required>
        <button class='btn-custom btn-primary w-100'>Entrar</button>
      </form>
    </div>"""
    return render_template_string(html_doc)

@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor()
    # busca ordenada; se a tabela for gigante, considere paginação (melhoria possível)
    cur.execute('SELECT * FROM cliente ORDER BY criado_em DESC')
    rows = cur.fetchall()

    trs = []
    for r in rows:
        trs.append(f"""
        <tr>
          <td>{r['id']}</td><td>{html.escape(str(r['nome']))}</td><td>{html.escape(str(r['telefone']))}</td><td>{html.escape(str(r['renda']))}</td><td>{html.escape(str(r['valor_imovel']))}</td>
          <td>R$ {fmt(r['parcela_price'])}</td><td>R$ {fmt(r['parcela_sac_ini'])}</td><td>R$ {fmt(r['parcela_sac_fim'])}</td>
          <td>{html.escape(str(r['faixa']))}</td><td>{r['prazo']}</td><td>{html.escape(str(r['criado_em']))}</td>
        </tr>""")
    trs_html = ''.join(trs)

    logo_url = url_for('static', filename='logo.jpg')
    html_doc = STYLE + f"""
    <img src='{logo_url}' class='logo'>
    <div class='box'>
      <h3>Área Administrativa</h3>
      <table class='table table-hover'>
        <thead><tr><th>ID</th><th>Nome</th><th>Telefone</th><th>Renda</th><th>Imóvel</th>
        <th>PRICE</th><th>SAC ini</th><th>SAC fim</th><th>Faixa</th><th>Prazo</th><th>Data/Hora</th></tr></thead>
        <tbody>{trs_html}</tbody>
      </table>
    </div>"""
    return render_template_string(html_doc)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

@app.route('/excluir/<int:id>')
def excluir(id):
    if 'admin' in session:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('DELETE FROM cliente WHERE id=?', (id,))
        conn.commit()
    return redirect(url_for('admin'))

# helper para consultar simulacoes (usado possivelmente em outras partes)
def get_dados():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, renda, imovel, juros, entrada, subsidio, valor_liberado FROM simulacao")
    dados = cur.fetchall()
    conn.close()
    return dados

# --- Main (mantive a lógica de host/port/debug via env) ---
if __name__ == '__main__':
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    logging.info('Iniciando app em %s:%s (debug=%s) — DB=%s', host, port, debug, DB)
    app.run(host=host, port=port, debug=debug)
