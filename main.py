# main.py
import os
import logging
import html
from datetime import datetime

from flask import Flask, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# ---------- Config ----------
# Use DATABASE_URL (Postgres) se existir, caso contrário fallback para SQLite local (útil para dev)
DATABASE_URL = os.getenv('DATABASE_URL')  # ex: postgres://user:pass@host:port/dbname
if not DATABASE_URL:
    # fallback para sqlite local (arquivo)
    SQLITE_PATH = os.getenv('DB_PATH', 'simulador.db')
    DATABASE_URL = f"sqlite:///{os.path.abspath(SQLITE_PATH)}"

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.secret_key = os.getenv('FLASK_SECRET', 'segredo123')
ADMIN_PASS = os.getenv('ADMIN_PASS', 'jm.eng2025')
PRAZO = int(os.getenv('PRAZO', '420'))

EMAIL_USER = os.getenv('EMAIL_USER', '')
EMAIL_PASS = os.getenv('EMAIL_PASS', '')
SEND_EMAIL = os.getenv('SEND_EMAIL', '0')  # '0' desativa

# ---------- DB ----------
db = SQLAlchemy(app)

# ---------- Models ----------
class Simulacao(db.Model):
    __tablename__ = 'simulacao'
    id = db.Column(db.Integer, primary_key=True)
    renda = db.Column(db.String(128), nullable=False)
    imovel = db.Column(db.String(128), nullable=False)
    juros = db.Column(db.Float, nullable=False, default=0.0)
    entrada = db.Column(db.Float, nullable=False, default=0.0)
    subsidio = db.Column(db.Float, nullable=False, default=0.0)
    valor_liberado = db.Column(db.Float, nullable=False, default=0.0)
    sac_primeira = db.Column(db.Float, nullable=False, default=0.0)
    sac_ultima = db.Column(db.Float, nullable=False, default=0.0)
    price_primeira = db.Column(db.Float, nullable=False, default=0.0)
    price_ultima = db.Column(db.Float, nullable=False, default=0.0)

    # convenience
    def to_tuple(self):
        return (self.renda, self.imovel, self.juros, self.entrada, self.subsidio,
                self.valor_liberado, self.sac_primeira, self.sac_ultima,
                self.price_primeira, self.price_ultima)

class Cliente(db.Model):
    __tablename__ = 'cliente'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(256))
    telefone = db.Column(db.String(64))
    renda = db.Column(db.String(128))
    valor_imovel = db.Column(db.String(128))
    entrada = db.Column(db.Float)
    entrada_calculada = db.Column(db.Float)
    valor_financiado = db.Column(db.Float)
    parcela_price = db.Column(db.Float)
    parcela_sac_ini = db.Column(db.Float)
    parcela_sac_fim = db.Column(db.Float)
    prazo = db.Column(db.Integer)
    faixa = db.Column(db.String(64))
    juros = db.Column(db.Float)
    subsidio = db.Column(db.Float)
    fgts = db.Column(db.Float)
    aprovado = db.Column(db.Integer)
    criado_em = db.Column(db.String(64))

# ---------- utilidades ----------
def fmt(v):
    try:
        return f"{float(v):,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except Exception:
        return v

def faixa_por_renda(r):
    m = {
        'até 1.500 reais':'Faixa 1','até 2.160 reais':'Faixa 1','até 2.850 reais':'Faixa 1',
        'até 3.500 reais':'Faixa 2','até 4.000 reais':'Faixa 2','até 4.700 reais':'Faixa 2',
        'até 8.600 reais':'Faixa 3','acima de 10.000 reais':'Faixa 4'
    }
    return m.get(r,'Faixa desconhecida')

# ---------- CSS/JS (mantive idêntico ao seu) ----------
STYLE = """<link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'>
<link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'>
<script src='https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js'></script>
<script src='https://cdnjs.cloudflare.com/ajax/libs/jquery.mask/1.14.16/jquery.mask.min.js'></script>
<style>
/* (use o mesmo CSS que você tinha - por brevidade aqui assume-se que seja idêntico) */
body { background: linear-gradient(135deg, #0d1117, #161b22); font-family: 'Segoe UI', sans-serif; color: #e6e6e6; }
.logo { display:block; margin:0 auto 20px; max-height:90px; filter: drop-shadow(0 0 4px rgba(0,191,255,0.4)); }
/* ... restantes do CSS ... */
.box { max-width:850px; margin:40px auto; padding:25px; border-radius:20px; background:#1e242c; }
.table { color:#e6e6e6; background-color:#1c2128; }
</style>
<script>$(function(){ $('#telefone').mask('(00) 00000-0000'); });</script>
"""

# ---------- seed: contém todas as simulações (os "valores de simulações" solicitados) ----------
def seed_simulacoes():
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
        ('até 1.500 reais','imovel ate 350k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),
        ('até 2.160 reais','imovel ate 350k',8.47,287842.70,0.00,62157.30,647.99,174.01,526.05,473.72),
        ('até 2.850 reais','imovel ate 350k',8.47,265495.61,2028.00,84504.39,855.00,22.58,689.22,635.05),
        ('até 3.500 reais','imovel ate 350k',8.47,244444.00,0.00,105556.00,1049.99,278.03,842.91,787.02),
        ('até 4.000 reais','imovel ate 350k',8.47,228250.45,0.00,121749.55,1200.00,316.85,961.14,903.92),
        ('até 4.700 reais','imovel ate 350k',8.47,205579.49,0.00,144420.51,1410.00,371.20,1126.67,1067.59),
        ('até 8.600 reais','imovel ate 350k',8.47,79269.84,0.00,270730.16,2580.00,673.98,2048.87,1979.43),
        ('acima de 10.000 reais','imovel ate 350k',10.47,70000.00,0.00,280000.00,3095.19,697.22,2502.28,2432.08),

        # Imóvel até 500k
        ('até 1.500 reais','imovel ate 500k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),
        ('até 2.160 reais','imovel ate 500k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),
        ('até 2.850 reais','imovel ate 500k',0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00),
        ('até 3.500 reais','imovel ate 500k',10.47,389670.37,0.00,110329.93,0.00,0.00,1050.00,973.47),
        ('até 4.000 reais','imovel ate 500k',10.47,397416.52,0.00,102583.48,1200.00,271.28,982.77,906.88),
        ('até 4.700 reais','imovel ate 500k',10.47,348189.60,0.00,151810.40,1410.00,317.98,1151.59,1074.10),
        ('até 8.600 reais','imovel ate 500k',10.47,269594.72,0.00,230405.28,2580.00,578.15,2580.00,2489.02),
        ('acima de 10.000 reais','imovel ate 500k',10.47,100000.00,0.00,400000.00,3600.00,804.98,3563.97,3463.69),
    ]

    for row in expected:
        renda, imovel = row[0], row[1]
        exists = Simulacao.query.filter_by(renda=renda, imovel=imovel).first()
        if not exists:
            s = Simulacao(
                renda = renda, imovel = imovel,
                juros = row[2], entrada = row[3], subsidio = row[4], valor_liberado = row[5],
                sac_primeira = row[6], sac_ultima = row[7],
                price_primeira = row[8], price_ultima = row[9]
            )
            db.session.add(s)
    db.session.commit()
    logging.info("Seed de simulações finalizada.")

# ---------- inicialização DB (cria tabelas e seeds) ----------
with app.app_context():
    db.create_all()
    seed_simulacoes()

# ---------- email ----------
def send_email(nome, tel, renda, imovel, price, sac_ini, sac_fim, faixa):
    if SEND_EMAIL == '0' or not EMAIL_USER or not EMAIL_PASS:
        logging.info('Envio de email desativado ou credenciais ausentes')
        return
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER
    msg['Subject'] = 'Nova simulação'
    body = f"""Nova simulação realizada:
Nome: {nome}
Telefone: {tel}
Renda: {renda}
Imóvel: {imovel}
Faixa: {faixa}
1ª Parcela PRICE: R$ {fmt(price)}
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

# ---------- rotas (mantive a UX do seu app) ----------
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

@app.route('/simular', methods=['POST'])
def simular():
    nome = request.form.get('nome')
    tel = request.form.get('telefone')
    renda = request.form.get('renda')
    imovel = request.form.get('valor_imovel')
    if not all([nome, tel, renda, imovel]):
        return 'Dados incompletos', 400

    s = Simulacao.query.filter_by(renda=renda, imovel=imovel).first()
    if s is None:
        return "Simulação não encontrada para a combinação selecionada.", 400

    price, sac_ini, sac_fim = s.price_primeira, s.sac_primeira, s.sac_ultima
    faixa = faixa_por_renda(renda)
    criado = datetime.now().strftime('%d/%m/%Y %H:%M')

    cliente = Cliente(
        nome = nome,
        telefone = tel,
        renda = renda,
        valor_imovel = imovel,
        entrada = s.entrada,
        entrada_calculada = s.entrada,
        valor_financiado = s.valor_liberado,
        parcela_price = price,
        parcela_sac_ini = sac_ini,
        parcela_sac_fim = sac_fim,
        prazo = PRAZO,
        faixa = faixa,
        juros = s.juros,
        subsidio = s.subsidio,
        fgts = 0,
        aprovado = 1,
        criado_em = criado
    )
    db.session.add(cliente)
    db.session.commit()
    cid = cliente.id

    try:
        send_email(nome, tel, renda, imovel, price, sac_ini, sac_fim, faixa)
    except Exception:
        logging.exception('Erro no envio de email (ignorado)')

    return redirect(url_for('resultado', id=cid))

@app.route('/resultado/<int:id>')
def resultado(id):
    c = Cliente.query.get(id)
    if not c:
        return 'Simulação não encontrada', 404

    nome = html.escape(c.nome)
    telefone = html.escape(c.telefone)
    renda_txt = html.escape(c.renda)
    imovel_txt = html.escape(c.valor_imovel)
    faixa_txt = html.escape(c.faixa)
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
        <tr><th>1ª Parcela PRICE (parcela fixa)</th><td>R$ {fmt(c.parcela_price)}</td></tr>
        <tr><th>1ª Parcela SAC</th><td>R$ {fmt(c.parcela_sac_ini)}</td></tr>
        <tr><th>Última Parcela SAC</th><td>R$ {fmt(c.parcela_sac_fim)}</td></tr>
        <tr><th>Prazo</th><td>{c.prazo} meses</td></tr>
        <tr><th>Data/Hora</th><td>{html.escape(c.criado_em)}</td></tr>
      </table>
      <a href="https://api.whatsapp.com/send?phone=5538998721022&text=Ol%C3%A1,%20podemos%20conversar%20sobre%20minha%20futura%20casa?%20nome:%20{nome},%20Renda:%20{renda_txt},%20Im%C3%B3vel:%20{imovel_txt},%20Faixa:%20{faixa_txt},%201%C2%AA%20Parcela%20PRICE:%20R$%20{fmt(c.parcela_price)},%201%C2%AA%20Parcela%20SAC:%20R$%20{fmt(c.parcela_sac_ini)},%20%C3%9Altima%20SAC:%20{fmt(c.parcela_sac_fim)}" target="_blank" class="btn-custom btn-whatsapp w-100 mb-2"><i class="fab fa-whatsapp"></i>Começar Consultoria</a>
      <a href='/' class='btn-custom btn-primary w-100 mb-2 d-flex align-items-center justify-content-center'>Nova Simulação</a>
    </div>"""

@app.route('/login', methods=['GET','POST'])
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

@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect(url_for('login'))
    rows = Cliente.query.order_by(Cliente.criado_em.desc()).all()
    trs = ''
    for r in rows:
        trs += f"""
        <tr>
          <td>{r.id}</td><td>{html.escape(str(r.nome))}</td><td>{html.escape(str(r.telefone))}</td><td>{html.escape(str(r.renda))}</td><td>{html.escape(str(r.valor_imovel))}</td>
          <td>R$ {fmt(r.parcela_price)}</td><td>R$ {fmt(r.parcela_sac_ini)}</td><td>R$ {fmt(r.parcela_sac_fim)}</td>
          <td>{html.escape(str(r.faixa))}</td><td>{r.prazo}</td><td>{html.escape(str(r.criado_em))}</td>
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

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

@app.route('/excluir/<int:id>')
def excluir(id):
    if 'admin' in session:
        c = Cliente.query.get(id)
        if c:
            db.session.delete(c)
            db.session.commit()
    return redirect(url_for('admin'))

def get_dados():
    sims = Simulacao.query.all()
    return [(s.id, s.renda, s.imovel, s.juros, s.entrada, s.subsidio, s.valor_liberado) for s in sims]

if __name__ == '__main__':
    host = os.getenv('HOST','127.0.0.1')
    port = int(os.getenv('PORT','5000'))
    debug = os.getenv('FLASK_DEBUG','0') == '1'
    logging.info('Iniciando app em %s:%s — DB=%s', host, port, DATABASE_URL)
    app.run(host=host, port=port, debug=debug)
