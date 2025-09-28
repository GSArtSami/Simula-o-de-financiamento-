# main.py
from flask import Flask, request, session, redirect, url_for# main.py
from flask import Flask, request, session, redirect, url_for
import sqlite3
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import html

# logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Configurações por ENV (em produção configure no Render)
DB = os.getenv('DB_PATH', 'simulador.db')  # em Render, prefira: /var/data/simulador.db
# garante que o diretório do DB exista (se for um path com diretório)
_db_dir = os.path.dirname(DB)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)

app.secret_key = os.getenv('FLASK_SECRET', 'segredo123')
ADMIN_PASS = os.getenv('ADMIN_PASS', 'jm.eng2025')
PRAZO = int(os.getenv('PRAZO', '420'))

# e-mail (por padrão vazio; configure no painel)
EMAIL_USER = os.getenv('EMAIL_USER', 'jmengenhariaobras@gmail.com')
EMAIL_PASS = os.getenv('EMAIL_PASS', 'vehg bguy tirc qfjm ')
SEND_EMAIL = os.getenv('SEND_EMAIL', '1')  # '0' desativa envio por padrão

# CSS global, logo e FontAwesome (coloque logo.jpg em /static)
STYLE = """
<link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'>
<link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'>
<script src='https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js'></script>
<script src='https://cdnjs.cloudflare.com/ajax/libs/jquery.mask/1.14.16/jquery.mask.min.js'></script>


<style>
  body {
      background: linear-gradient(135deg, #0d1117, #161b22);
      font-family: 'Segoe UI', sans-serif;
      color: #e6e6e6;

    }
    /* Logo */
    .logo {
        display: block;
        margin: 50 auto 25px;
        max-height: 110px; 
        width: auto;       
       border: 2px solid rgba(0, 191, 255, 0.6);
        border-radius: 6px;
       
    }
    /* Caixa do formulário */
    .box {
        max-width: 400px;
        background: #fff;
        padding: 25px;
        margin: 0 auto;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .btn-custom {
        background-color: #00bfff;
        border: none;
        color: #fff;
    }
    .btn-custom:hover {
        background-color: #009acd;
    }


  /* Container */
  .box {
      max-width: 850px;
      margin: 40px auto;
      padding: 25px;
      border-radius: 20px;
      background: #1e242c;
      box-shadow: 0 0 25px rgba(0, 191, 255, 0.08);
      transition: transform 0.3s ease, box-shadow 0.3s ease;
  }
  .box:hover {
      transform: translateY(-3px);
      box-shadow: 0 0 30px rgba(0, 191, 255, 0.15);
  }

  /* Logo */
  .logo {
      display: block;
      margin: 0 auto 20px;
      max-height: 90px;
      filter: drop-shadow(0 0 4px rgba(0, 191, 255, 0.4));
  }

  /* Botões base */
  .btn-custom {
      border-radius: 50px;
      padding: 12px 24px;
      font-weight: 600;
      border: none;
      letter-spacing: 0.3px;
      transition: all 0.3s ease-in-out;
      box-shadow: 0 0 8px rgba(0, 0, 0, 0.3);
  }

  /* Botão primário */
  .btn-primary {
      background: linear-gradient(135deg, #001f3f, #0056b3);
      color: #fff;
      box-shadow: 0 0 12px rgba(0, 123, 255, 0.4);
  }
  .btn-primary:hover {
      background: linear-gradient(135deg, #0056b3, #00bfff);
      box-shadow: 0 0 20px rgba(0, 191, 255, 0.8);
      transform: scale(1.05);
  }

  /* Botão de perigo */
  .btn-danger {
      background: linear-gradient(135deg, #8b0000, #dc3545);
      color: #fff;
      box-shadow: 0 0 12px rgba(220, 53, 69, 0.4);
  }
  .btn-danger:hover {
      background: linear-gradient(135deg, #dc3545, #ff6b6b);
      box-shadow: 0 0 20px rgba(255, 99, 99, 0.7);
      transform: scale(1.05);
  }

  /* Botão secundário */
  .btn-secondary {
      background: linear-gradient(135deg, #2c2f36, #3e434a);
      color: #fff;
      border: 1px solid #00bfff;
      box-shadow: 0 0 10px rgba(0, 191, 255, 0.2);
  }
  .btn-secondary:hover {
      background: linear-gradient(135deg, #00bfff, #0056b3);
      color: #fff;
      box-shadow: 0 0 20px rgba(0, 191, 255, 0.6);
      transform: scale(1.05);
  }

  /* Botão WhatsApp */
  .btn-whatsapp {
      background: linear-gradient(135deg, #25D366, #128C7E);
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 12px rgba(37, 211, 102, 0.4);
  }
  .btn-whatsapp i {
      margin-right: 8px;
      font-size: 1.1em;
  }
  .btn-whatsapp:hover {
      background: linear-gradient(135deg, #128C7E, #25D366);
      box-shadow: 0 0 20px rgba(37, 211, 102, 0.7);
      transform: scale(1.05);
  }

    /* Tabelas */
  table {
      color: #e6e6e6;
      background-color: #1c2128; /* fundo cinza-escuro */
  }
  table th, table td {
      vertical-align: middle !important;
      border-color: rgba(255,255,255,0.05);
      background-color: #1c2128; /* aplica cinza-escuro em todas as células */
  }
  table thead {
      background-color: #2a2f38; /* cinza um pouco mais claro para o cabeçalho */
      text-transform: uppercase;
      letter-spacing: 0.5px;
  }
  table tbody tr:hover {
      background-color: rgba(0, 191, 255, 0.08); /* realce suave no hover */
  }

</style>
<script>
  $(function(){ $('#telefone').mask('(00) 00000-0000'); });
</script>
"""

def fmt(v):
    try:
        return f"{float(v):,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except Exception:
        return v

# Inicializa banco de dados e simulações
def init_db():
    try:
        with sqlite3.connect(DB) as con:
            cur = con.cursor()
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
                # Imóvel até 210k
                ('até 1.500 reais','imovel ate 210k',4.85,131243.97,13090.00,65666.03,450.00,156.97,354.74,321.01),
                ('até 2.160 reais','imovel ate 210k',4.85,107186.00,6313.00,96501.00,647.99,230.67,508.00,471.75),
                ('até 2.850 reais','imovel ate 210k',5.12,83279.90,2028.00,124692.10,855.00,298.12,667.88,629.31),
                ('até 3.500 reais','imovel ate 210k',5.64,68555.16,0.00,141444.84,1050.00,363.32,824.52,784.58),
                ('até 4.000 reais','imovel ate 210k',6.17,56352.99,0.00,153647.01,1200.00,392.66,942.02,901.08),
                ('até 4.700 reais','imovel ate 210k',7.23,46473.70,0.00,163526.30,1410.00,416.62,1111.45,1069.70),
                ('até 8.600 reais','imovel ate 210k',8.47,42000.00,0.00,168000.00,1609.51,427.71,1279.93,1237.81),
                ('acima de 10.000 reais','imovel ate 210k',10.47,42000.00,0.00,168000.00,1867.11,428.32,1511.37,1469.25),

                # Imóvel até 350k
                ('até 1.500 reais','imovel ate 350k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),  # renda insuficiente
                ('até 2.160 reais','imovel ate 350k',8.47,287842.70,0.00,62157.30,647.99,174.01,526.05,473.72),
                ('até 2.850 reais','imovel ate 350k',8.47,265495.61,2028.00,84504.39,855.00,22.58,689.22,635.05),
                ('até 3.500 reais','imovel ate 350k',8.47,244444.00,0.00,105556.00,1049.99,278.03,842.91,787.02),
                ('até 4.000 reais','imovel ate 350k',8.47,228250.45,0.00,121749.55,1200.00,316.85,961.14,903.92),
                ('até 4.700 reais','imovel ate 350k',8.47,205579.49,0.00,144420.51,1410.00,371.20,1126.67,1067.59),
                ('até 8.600 reais','imovel ate 350k',8.47,79269.84,0.00,270730.16,2580.00,673.98,2048.87,1979.43),
                ('acima de 10.000 reais','imovel ate 350k',10.47,70000.00,0.00,280000.00,3095.19,697.22,2502.28,2432.08),

                # Imóvel até 500k
                ('até 1.500 reais','imovel ate 500k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),  # renda insuficiente
                ('até 2.160 reais','imovel ate 500k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),  # renda insuficiente
                ('até 2.850 reais','imovel ate 500k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),  # renda insuficiente
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
                con.commit()
                logging.info('Inseridas %d simulações faltantes na tabela simulacao', inserted)
    except Exception as e:
        logging.exception('Erro ao inicializar DB: %s', e)

init_db()

# Mapeia faixa somente 1-4
def faixa_por_renda(r):
    m = {
        'até 1.500 reais':'Faixa 1','até 2.160 reais':'Faixa 1','até 2.850 reais':'Faixa 1',
        'até 3.500 reais':'Faixa 2','até 4.000 reais':'Faixa 2','até 4.700 reais':'Faixa 2',
        'até 8.600 reais':'Faixa 3','acima de 10.000 reais':'Faixa 4'
    }
    return m.get(r,'Faixa desconhecida')

# Envia email (pode falhar se credenciais/SMTP não estiverem corretos)
def send_email(nome, tel, renda, imovel, price, sac_ini, sac_fim, faixa):
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
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
            logging.info('Email enviado para %s', EMAIL_USER)
    except Exception:
        logging.exception('Falha ao enviar email (verifique credenciais/SMTP)')

# Home: formulário completo
@app.route('/')
def home():
    renda_opts = [
          'até 1.500 reais','até 2.160 reais','até 2.850 reais','até 3.500 reais',
        'até 4.000 reais','até 4.700 reais','até 8.600 reais','acima de 10.000 reais'
    ]

    imovel_opts = ['imovel ate 210k','imovel ate 350k','imovel ate 500k']
    renda_html = ''.join(f"<option value='{r}'>{r}</option>" for r in renda_opts)
    imovel_html = ''.join(f"<option value='{i}'>{i}</option>" for i in imovel_opts)
    logo_url = url_for('static', filename='logo.jpg')

    return STYLE + f"""
        <img src="{logo_url}" class="logo">
        <div class="box">
      

      <h3>Simulador Minha Casa Minha Vida</h3>
      <form method='post' action='/simular'>
        <input name='nome' placeholder='Nome*' class='form-control mb-2' required>
        <input name='telefone' placeholder='Telefone*' id='telefone' class='form-control mb-2' required>
        <select name='renda' class='form-select mb-2' required>{renda_html}</select>
        <select name='valor_imovel' class='form-select mb-2' required>{imovel_html}</select>
        <button class='btn-custom btn-primary w-100'>Simular</button>
      </form>
    </div>"""

# Simular: grava e envia email
@app.route('/simular', methods=['POST'])
def simular():
    form = request.form
    nome, tel = form.get('nome'), form.get('telefone')
    renda, imovel = form.get('renda'), form.get('valor_imovel')

    if not all([nome, tel, renda, imovel]):
        return 'Dados incompletos', 400

    with sqlite3.connect(DB) as con:
        s = con.execute('SELECT * FROM simulacao WHERE renda=? AND imovel=?', (renda, imovel)).fetchone()
        if s is None:
            return "Simulação não encontrada para a combinação selecionada.", 400

        # índices conforme CREATE TABLE simulacao: id(0), renda(1), imovel(2), juros(3), entrada(4), subsidio(5), valor_liberado(6),
        # sac_primeira(7), sac_ultima(8), price_primeira(9), price_ultima(10)
        price, sac_ini, sac_fim = s[9], s[7], s[8]
        faixa = faixa_por_renda(renda)
        criado = datetime.now().strftime('%d/%m/%Y %H:%M')

        con.execute(
            '''INSERT INTO cliente (nome, telefone, renda, valor_imovel, entrada, entrada_calculada, valor_financiado,
                               parcela_price, parcela_sac_ini, parcela_sac_fim, prazo, faixa, juros, subsidio, fgts, aprovado, criado_em)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (nome, tel, renda, imovel, s[4], s[4], s[6], price, sac_ini, sac_fim, PRAZO, faixa, s[3], s[5], 0, 1, criado)
        )
        cid = con.execute('SELECT last_insert_rowid()').fetchone()[0]

    # tenta enviar email, mas não quebra a resposta ao usuário em caso de falha
    try:
        send_email(nome, tel, renda, imovel, price, sac_ini, sac_fim, faixa)
    except Exception:
        logging.exception('Erro no envio de email (ignorado)')

    return redirect(url_for('resultado', id=cid))

# Resultado: exibe tudo em ordem
@app.route('/resultado/<int:id>')
def resultado(id):
    with sqlite3.connect(DB) as con:
        c = con.execute('SELECT * FROM cliente WHERE id=?', (id,)).fetchone()

    if not c:
        return 'Simulação não encontrada', 404

    # escape para evitar XSS básico
    nome = html.escape(c[1])
    telefone = html.escape(c[2])
    renda_txt = html.escape(c[3])
    imovel_txt = html.escape(c[4])
    faixa_txt = html.escape(c[12])


    logo_url = url_for('static', filename='logo.jpg')

    return STYLE + f"""
        <img src="{logo_url}" class="logo">
        <div class="box">

        <h3>Resultado da Simulação</h3>
        <table class='table'>
        <tr><th>Nome</th><td>{nome}</td></tr>
        <tr><th>Telefone</th><td>{telefone}</td></tr>
        <tr><th>Renda</th><td>{renda_txt}</td></tr>
        <tr><th>Imóvel</th><td>{imovel_txt}</td></tr>
        <tr><th>Faixa</th><td>{faixa_txt}</td></tr>
        <tr><th>1ª Parcela PRICE (parcela fixa)</th><td>R$ {fmt(c[8])}</td></tr>
        <tr><th>1ª Parcela SAC</th><td>R$ {fmt(c[9])}</td></tr>
        <tr><th>Última Parcela SAC</th><td>R$ {fmt(c[10])}</td></tr>
        <tr><th>Prazo</th><td>{c[11]} meses</td></tr>
        <tr><th>Data/Hora</th><td>{html.escape(c[17])}</td></tr>
      </table>

      <!-- botão WhatsApp -->
      <a href="https://api.whatsapp.com/send?phone=5538998721022&text=Ol%C3%A1,%20podemos%20conversar%20sobre%20minha%20futura%20casa?%20nome:%20{nome},%20Renda:%20{renda_txt},%20Im%C3%B3vel:%20{imovel_txt},%20Faixa:%20{faixa_txt},%201%C2%AA%20Parcela%20PRICE:%20R$%20{fmt(c[8])},%201%C2%AA%20Parcela%20SAC:%20R$%20{fmt(c[9])},%20%C3%9Altima%20SAC:%20{fmt(c[10])}" target="_blank" class="btn-custom btn-whatsapp w-100 mb-2">
        <i class="fab fa-whatsapp"></i>Começar Consultoria
      </a>

      <!-- botão Nova Simulação ajustado -->
      <a href='/'
         class='btn-custom btn-primary w-100 mb-2 d-flex align-items-center justify-content-center'>
        Nova Simulação
      </a>
    </div>"""

# Login admin
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and request.form.get('senha') == ADMIN_PASS:
        session['admin'] = True
        return redirect(url_for('admin'))
    logo_url = url_for('static', filename='logo.jpg')
    return STYLE + f"""
    <div class='box'>
      <img src='{logo_url}' class='logo'>
      <h3>Login Administrativo</h3>
      <form method='post'>
        <input type='password' name='senha' class='form-control mb-2' placeholder='Senha' required>
        <button class='btn-custom btn-primary w-100'>Entrar</button>
      </form>
    </div>"""

# Área administrativa
@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect(url_for('login'))

    with sqlite3.connect(DB) as con:
        rows = con.execute('SELECT * FROM cliente ORDER BY criado_em DESC').fetchall()

    trs = ''
    for r in rows:
        # r índice conforme CREATE TABLE cliente
        trs += f"""
        <tr>
          <td>{r[0]}</td><td>{html.escape(str(r[1]))}</td><td>{html.escape(str(r[2]))}</td><td>{html.escape(str(r[3]))}</td><td>{html.escape(str(r[4]))}</td>
          <td>R$ {fmt(r[8])}</td><td>R$ {fmt(r[9])}</td><td>R$ {fmt(r[10])}</td>
          <td>{html.escape(str(r[12]))}</td><td>{r[11]}</td><td>{html.escape(str(r[17]))}</td>
        </tr>"""

    logo_url = url_for('static', filename='logo.jpg')
    return STYLE + f"""
    <img src='{logo_url}' class='logo'>
    <div class='box'>
      <h3>Área Administrativa</h3>
      <table class='table table-hover'>
        <thead><tr><th>ID</th><th>Nome</th><th>Telefone</th><th>Renda</th><th>Imóvel</th>
        <th>PRICE</th><th>SAC ini</th><th>SAC fim</th><th>Faixa</th><th>Prazo</th><th>Data/Hora</th></tr></thead>
        <tbody>{trs}</tbody>
      </table>
    </div>"""

# Logout
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

# Excluir via URL direta
@app.route('/excluir/<int:id>')
def excluir(id):
    if 'admin' in session:
        with sqlite3.connect(DB) as con:
            con.execute('DELETE FROM cliente WHERE id=?', (id,))
    return redirect(url_for('admin'))

# helper para consultar simulacoes
def get_dados():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT id, renda, imovel, juros, entrada, subsidio, valor_liberado FROM simulacao")
    dados = cursor.fetchall()
    conn.close()
    return dados

if __name__ == '__main__':
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    logging.info('Iniciando app em %s:%s (debug=%s) — DB=%s', host, port, debug, DB)
    app.run(host=host, port=port, debug=debug)

import sqlite3
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import html

# logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Configurações por ENV (em produção configure no Render)
DB = os.getenv('DB_PATH', 'simulador.db')  # em Render, prefira: /var/data/simulador.db
# garante que o diretório do DB exista (se for um path com diretório)
_db_dir = os.path.dirname(DB)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)

app.secret_key = os.getenv('FLASK_SECRET', 'segredo123')
ADMIN_PASS = os.getenv('ADMIN_PASS', 'jm.eng2025')
PRAZO = int(os.getenv('PRAZO', '420'))

# e-mail (por padrão vazio; configure no painel)
EMAIL_USER = os.getenv('EMAIL_USER', 'jmengenhariaobras@gmail.com')
EMAIL_PASS = os.getenv('EMAIL_PASS', 'vehg bguy tirc qfjm ')
SEND_EMAIL = os.getenv('SEND_EMAIL', '1')  # '0' desativa envio por padrão

# CSS global, logo e FontAwesome (coloque logo.jpg em /static)
STYLE = """
<link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'>
<link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'>
<script src='https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js'></script>
<script src='https://cdnjs.cloudflare.com/ajax/libs/jquery.mask/1.14.16/jquery.mask.min.js'></script>


<style>
  body {
      background: linear-gradient(135deg, #0d1117, #161b22);
      font-family: 'Segoe UI', sans-serif;
      color: #e6e6e6;

    }
    /* Logo */
    .logo {
        display: block;
        margin: 50 auto 25px;
        max-height: 110px; 
        width: auto;       
       border: 2px solid rgba(0, 191, 255, 0.6);
        border-radius: 6px;
       
    }
    /* Caixa do formulário */
    .box {
        max-width: 400px;
        background: #fff;
        padding: 25px;
        margin: 0 auto;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .btn-custom {
        background-color: #00bfff;
        border: none;
        color: #fff;
    }
    .btn-custom:hover {
        background-color: #009acd;
    }


  /* Container */
  .box {
      max-width: 850px;
      margin: 40px auto;
      padding: 25px;
      border-radius: 20px;
      background: #1e242c;
      box-shadow: 0 0 25px rgba(0, 191, 255, 0.08);
      transition: transform 0.3s ease, box-shadow 0.3s ease;
  }
  .box:hover {
      transform: translateY(-3px);
      box-shadow: 0 0 30px rgba(0, 191, 255, 0.15);
  }

  /* Logo */
  .logo {
      display: block;
      margin: 0 auto 20px;
      max-height: 90px;
      filter: drop-shadow(0 0 4px rgba(0, 191, 255, 0.4));
  }

  /* Botões base */
  .btn-custom {
      border-radius: 50px;
      padding: 12px 24px;
      font-weight: 600;
      border: none;
      letter-spacing: 0.3px;
      transition: all 0.3s ease-in-out;
      box-shadow: 0 0 8px rgba(0, 0, 0, 0.3);
  }

  /* Botão primário */
  .btn-primary {
      background: linear-gradient(135deg, #001f3f, #0056b3);
      color: #fff;
      box-shadow: 0 0 12px rgba(0, 123, 255, 0.4);
  }
  .btn-primary:hover {
      background: linear-gradient(135deg, #0056b3, #00bfff);
      box-shadow: 0 0 20px rgba(0, 191, 255, 0.8);
      transform: scale(1.05);
  }

  /* Botão de perigo */
  .btn-danger {
      background: linear-gradient(135deg, #8b0000, #dc3545);
      color: #fff;
      box-shadow: 0 0 12px rgba(220, 53, 69, 0.4);
  }
  .btn-danger:hover {
      background: linear-gradient(135deg, #dc3545, #ff6b6b);
      box-shadow: 0 0 20px rgba(255, 99, 99, 0.7);
      transform: scale(1.05);
  }

  /* Botão secundário */
  .btn-secondary {
      background: linear-gradient(135deg, #2c2f36, #3e434a);
      color: #fff;
      border: 1px solid #00bfff;
      box-shadow: 0 0 10px rgba(0, 191, 255, 0.2);
  }
  .btn-secondary:hover {
      background: linear-gradient(135deg, #00bfff, #0056b3);
      color: #fff;
      box-shadow: 0 0 20px rgba(0, 191, 255, 0.6);
      transform: scale(1.05);
  }

  /* Botão WhatsApp */
  .btn-whatsapp {
      background: linear-gradient(135deg, #25D366, #128C7E);
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 12px rgba(37, 211, 102, 0.4);
  }
  .btn-whatsapp i {
      margin-right: 8px;
      font-size: 1.1em;
  }
  .btn-whatsapp:hover {
      background: linear-gradient(135deg, #128C7E, #25D366);
      box-shadow: 0 0 20px rgba(37, 211, 102, 0.7);
      transform: scale(1.05);
  }

    /* Tabelas */
  table {
      color: #e6e6e6;
      background-color: #1c2128; /* fundo cinza-escuro */
  }
  table th, table td {
      vertical-align: middle !important;
      border-color: rgba(255,255,255,0.05);
      background-color: #1c2128; /* aplica cinza-escuro em todas as células */
  }
  table thead {
      background-color: #2a2f38; /* cinza um pouco mais claro para o cabeçalho */
      text-transform: uppercase;
      letter-spacing: 0.5px;
  }
  table tbody tr:hover {
      background-color: rgba(0, 191, 255, 0.08); /* realce suave no hover */
  }

</style>
<script>
  $(function(){ $('#telefone').mask('(00) 00000-0000'); });
</script>
"""

def fmt(v):
    try:
        return f"{float(v):,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except Exception:
        return v

# Inicializa banco de dados e simulações
def init_db():
    try:
        with sqlite3.connect(DB) as con:
            cur = con.cursor()
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
                # Imóvel até 210k
                ('até 1.500 reais','imovel ate 210k',4.85,131243.97,13090.00,65666.03,450.00,156.97,354.74,321.01),
                ('até 2.160 reais','imovel ate 210k',4.85,107186.00,6313.00,96501.00,647.99,230.67,508.00,471.75),
                ('até 2.850 reais','imovel ate 210k',5.12,83279.90,2028.00,124692.10,855.00,298.12,667.88,629.31),
                ('até 3.500 reais','imovel ate 210k',5.64,68555.16,0.00,141444.84,1050.00,363.32,824.52,784.58),
                ('até 4.000 reais','imovel ate 210k',6.17,56352.99,0.00,153647.01,1200.00,392.66,942.02,901.08),
                ('até 4.700 reais','imovel ate 210k',7.23,46473.70,0.00,163526.30,1410.00,416.62,1111.45,1069.70),
                ('até 8.600 reais','imovel ate 210k',8.47,42000.00,0.00,168000.00,1609.51,427.71,1279.93,1237.81),
                ('acima de 10.000 reais','imovel ate 210k',10.47,42000.00,0.00,168000.00,1867.11,428.32,1511.37,1469.25),

                # Imóvel até 350k
                ('até 1.500 reais','imovel ate 350k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),  # renda insuficiente
                ('até 2.160 reais','imovel ate 350k',8.47,287842.70,0.00,62157.30,647.99,174.01,526.05,473.72),
                ('até 2.850 reais','imovel ate 350k',8.47,265495.61,2028.00,84504.39,855.00,22.58,689.22,635.05),
                ('até 3.500 reais','imovel ate 350k',8.47,244444.00,0.00,105556.00,1049.99,278.03,842.91,787.02),
                ('até 4.000 reais','imovel ate 350k',8.47,228250.45,0.00,121749.55,1200.00,316.85,961.14,903.92),
                ('até 4.700 reais','imovel ate 350k',8.47,205579.49,0.00,144420.51,1410.00,371.20,1126.67,1067.59),
                ('até 8.600 reais','imovel ate 350k',8.47,79269.84,0.00,270730.16,2580.00,673.98,2048.87,1979.43),
                ('acima de 10.000 reais','imovel ate 350k',10.47,70000.00,0.00,280000.00,3095.19,697.22,2502.28,2432.08),

                # Imóvel até 500k
                ('até 1.500 reais','imovel ate 500k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),  # renda insuficiente
                ('até 2.160 reais','imovel ate 500k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),  # renda insuficiente
                ('até 2.850 reais','imovel ate 500k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),  # renda insuficiente
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
                con.commit()
                logging.info('Inseridas %d simulações faltantes na tabela simulacao', inserted)
    except Exception as e:
        logging.exception('Erro ao inicializar DB: %s', e)

init_db()

# Mapeia faixa somente 1-4
def faixa_por_renda(r):
    m = {
        'até 1.500 reais':'Faixa 1','até 2.160 reais':'Faixa 1','até 2.850 reais':'Faixa 1',
        'até 3.500 reais':'Faixa 2','até 4.000 reais':'Faixa 2','até 4.700 reais':'Faixa 2',
        'até 8.600 reais':'Faixa 3','acima de 10.000 reais':'Faixa 4'
    }
    return m.get(r,'Faixa desconhecida')

# Envia email (pode falhar se credenciais/SMTP não estiverem corretos)
def send_email(nome, tel, renda, imovel, price, sac_ini, sac_fim, faixa):
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
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
            logging.info('Email enviado para %s', EMAIL_USER)
    except Exception:
        logging.exception('Falha ao enviar email (verifique credenciais/SMTP)')

# Home: formulário completo
@app.route('/')
def home():
    renda_opts = [
          'até 1.500 reais','até 2.160 reais','até 2.850 reais','até 3.500 reais',
        'até 4.000 reais','até 4.700 reais','até 8.600 reais','acima de 10.000 reais'
    ]

    imovel_opts = ['imovel ate 210k','imovel ate 350k','imovel ate 500k']
    renda_html = ''.join(f"<option value='{r}'>{r}</option>" for r in renda_opts)
    imovel_html = ''.join(f"<option value='{i}'>{i}</option>" for i in imovel_opts)
    logo_url = url_for('static', filename='logo.jpg')

    return STYLE + f"""
        <img src="{logo_url}" class="logo">
        <div class="box">
      

      <h3>Simulador Minha Casa Minha Vida</h3>
      <form method='post' action='/simular'>
        <input name='nome' placeholder='Nome*' class='form-control mb-2' required>
        <input name='telefone' placeholder='Telefone*' id='telefone' class='form-control mb-2' required>
        <select name='renda' class='form-select mb-2' required>{renda_html}</select>
        <select name='valor_imovel' class='form-select mb-2' required>{imovel_html}</select>
        <button class='btn-custom btn-primary w-100'>Simular</button>
      </form>
    </div>"""

# Simular: grava e envia email
@app.route('/simular', methods=['POST'])
def simular():
    form = request.form
    nome, tel = form.get('nome'), form.get('telefone')
    renda, imovel = form.get('renda'), form.get('valor_imovel')

    if not all([nome, tel, renda, imovel]):
        return 'Dados incompletos', 400

    with sqlite3.connect(DB) as con:
        s = con.execute('SELECT * FROM simulacao WHERE renda=? AND imovel=?', (renda, imovel)).fetchone()
        if s is None:
            return "Simulação não encontrada para a combinação selecionada.", 400

        # índices conforme CREATE TABLE simulacao: id(0), renda(1), imovel(2), juros(3), entrada(4), subsidio(5), valor_liberado(6),
        # sac_primeira(7), sac_ultima(8), price_primeira(9), price_ultima(10)
        price, sac_ini, sac_fim = s[9], s[7], s[8]
        faixa = faixa_por_renda(renda)
        criado = datetime.now().strftime('%d/%m/%Y %H:%M')

        con.execute(
            '''INSERT INTO cliente (nome, telefone, renda, valor_imovel, entrada, entrada_calculada, valor_financiado,
                               parcela_price, parcela_sac_ini, parcela_sac_fim, prazo, faixa, juros, subsidio, fgts, aprovado, criado_em)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (nome, tel, renda, imovel, s[4], s[4], s[6], price, sac_ini, sac_fim, PRAZO, faixa, s[3], s[5], 0, 1, criado)
        )
        cid = con.execute('SELECT last_insert_rowid()').fetchone()[0]

    # tenta enviar email, mas não quebra a resposta ao usuário em caso de falha
    try:
        send_email(nome, tel, renda, imovel, price, sac_ini, sac_fim, faixa)
    except Exception:
        logging.exception('Erro no envio de email (ignorado)')

    return redirect(url_for('resultado', id=cid))

# Resultado: exibe tudo em ordem
@app.route('/resultado/<int:id>')
def resultado(id):
    with sqlite3.connect(DB) as con:
        c = con.execute('SELECT * FROM cliente WHERE id=?', (id,)).fetchone()

    if not c:
        return 'Simulação não encontrada', 404

    # escape para evitar XSS básico
    nome = html.escape(c[1])
    telefone = html.escape(c[2])
    renda_txt = html.escape(c[3])
    imovel_txt = html.escape(c[4])
    faixa_txt = html.escape(c[12])


    logo_url = url_for('static', filename='logo.jpg')

    return STYLE + f"""
        <img src="{logo_url}" class="logo">
        <div class="box">

        <h3>Resultado da Simulação</h3>
        <table class='table'>
        <tr><th>Nome</th><td>{nome}</td></tr>
        <tr><th>Telefone</th><td>{telefone}</td></tr>
        <tr><th>Renda</th><td>{renda_txt}</td></tr>
        <tr><th>Imóvel</th><td>{imovel_txt}</td></tr>
        <tr><th>Faixa</th><td>{faixa_txt}</td></tr>
        <tr><th>1ª Parcela PRICE (parcela fixa)</th><td>R$ {fmt(c[8])}</td></tr>
        <tr><th>1ª Parcela SAC</th><td>R$ {fmt(c[9])}</td></tr>
        <tr><th>Última Parcela SAC</th><td>R$ {fmt(c[10])}</td></tr>
        <tr><th>Prazo</th><td>{c[11]} meses</td></tr>
        <tr><th>Data/Hora</th><td>{html.escape(c[17])}</td></tr>
      </table>

      <!-- botão WhatsApp -->
      <a href="https://api.whatsapp.com/send?phone=5538998721022&text=Ol%C3%A1,%20podemos%20conversar%20sobre%20minha%20futura%20casa?%20nome:%20{nome},%20Renda:%20{renda_txt},%20Im%C3%B3vel:%20{imovel_txt},%20Faixa:%20{faixa_txt},%201%C2%AA%20Parcela%20PRICE:%20R$%20{fmt(c[8])},%201%C2%AA%20Parcela%20SAC:%20R$%20{fmt(c[9])},%20%C3%9Altima%20SAC:%20{fmt(c[10])}" target="_blank" class="btn-custom btn-whatsapp w-100 mb-2">
        <i class="fab fa-whatsapp"></i>Começar Consultoria
      </a>

      <!-- botão Nova Simulação ajustado -->
      <a href='/'
         class='btn-custom btn-primary w-100 mb-2 d-flex align-items-center justify-content-center'>
        Nova Simulação
      </a>
    </div>"""

# Login admin
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and request.form.get('senha') == ADMIN_PASS:
        session['admin'] = True
        return redirect(url_for('admin'))
    logo_url = url_for('static', filename='logo.jpg')
    return STYLE + f"""
    <div class='box'>
      <img src='{logo_url}' class='logo'>
      <h3>Login Administrativo</h3>
      <form method='post'>
        <input type='password' name='senha' class='form-control mb-2' placeholder='Senha' required>
        <button class='btn-custom btn-primary w-100'>Entrar</button>
      </form>
    </div>"""

# Área administrativa
@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect(url_for('login'))

    with sqlite3.connect(DB) as con:
        rows = con.execute('SELECT * FROM cliente ORDER BY criado_em DESC').fetchall()

    trs = ''
    for r in rows:
        # r índice conforme CREATE TABLE cliente
        trs += f"""
        <tr>
          <td>{r[0]}</td><td>{html.escape(str(r[1]))}</td><td>{html.escape(str(r[2]))}</td><td>{html.escape(str(r[3]))}</td><td>{html.escape(str(r[4]))}</td>
          <td>R$ {fmt(r[8])}</td><td>R$ {fmt(r[9])}</td><td>R$ {fmt(r[10])}</td>
          <td>{html.escape(str(r[12]))}</td><td>{r[11]}</td><td>{html.escape(str(r[17]))}</td>
        </tr>"""

    logo_url = url_for('static', filename='logo.jpg')
    return STYLE + f"""
    <img src='{logo_url}' class='logo'>
    <div class='box'>
      <h3>Área Administrativa</h3>
      <table class='table table-hover'>
        <thead><tr><th>ID</th><th>Nome</th><th>Telefone</th><th>Renda</th><th>Imóvel</th>
        <th>PRICE</th><th>SAC ini</th><th>SAC fim</th><th>Faixa</th><th>Prazo</th><th>Data/Hora</th></tr></thead>
        <tbody>{trs}</tbody>
      </table>
    </div>"""

# Logout
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

# Excluir via URL direta
@app.route('/excluir/<int:id>')
def excluir(id):
    if 'admin' in session:
        with sqlite3.connect(DB) as con:
            con.execute('DELETE FROM cliente WHERE id=?', (id,))
    return redirect(url_for('admin'))

# helper para consultar simulacoes
def get_dados():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT id, renda, imovel, juros, entrada, subsidio, valor_liberado FROM simulacao")
    dados = cursor.fetchall()
    conn.close()
    return dados

if __name__ == '__main__':
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    logging.info('Iniciando app em %s:%s (debug=%s) — DB=%s', host, port, debug, DB)
    app.run(host=host, port=port, debug=debug)

