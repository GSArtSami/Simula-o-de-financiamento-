# Dockerfile — imagem leve para rodar o Flask + SQLite com Gunicorn
FROM python:3.11-slim

# Metadados
LABEL maintainer="Você <seu-email@exemplo.com>"

# Variáveis de ambiente para evitar buffers e para o pip
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Diretório de trabalho
WORKDIR /app

# Instala dependências do sistema necessárias (build deps mínimos)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements e instala
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# Copia o código
COPY . /app

# Cria diretório onde o SQLite será persistido por volume
RUN mkdir -p /var/data && chown -R root:root /var/data

# Expõe porta (documentação) — Render usa $PORT variável em runtime
EXPOSE 5000

# Define variáveis padrão (podem ser sobrescritas no ambiente do host/Render)
ENV DB_PATH=/var/data/simulador.db
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV FLASK_SECRET=segredo123

# Volume para persistência do banco local (quando executar com -v /docker volumes)
VOLUME ["/var/data"]

# Comando de arranque: Gunicorn com 4 workers (ajuste se necessário)
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120"]
