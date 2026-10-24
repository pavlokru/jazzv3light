FROM python:3.12-slim

# Evita la creación de archivos .pyc y fuerza buffer de salida inmediato para logs de Streamlit
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Instalar dependencias esenciales de sistema (SQLite3 con soporte FTS5, Git y herramientas básicas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    libsqlite3-dev \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no root para desarrollo seguro en VS Code
RUN useradd -ms /bin/bash vscode

WORKDIR /workspace

# Copiar requirements.txt e instalar dependencias Python iniciales
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

USER vscode

# Puerto por defecto de Streamlit
EXPOSE 8502

CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0"]