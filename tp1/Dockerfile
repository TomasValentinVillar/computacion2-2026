# 1. Imagen base: Python 3.11 sobre un Linux liviano.
FROM python:3.11-slim

# 2. Instalar procps (ps, pkill, top) para poder enviar señales de control
#    al monitor desde dentro del contenedor (pkill -USR1/-USR2/-HUP -f main.py).
RUN apt-get update && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

# 3. Carpeta de trabajo dentro de la imagen.
WORKDIR /app

# 4. Instalar dependencias primero (cache de Docker). El TP usa solo stdlib.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el codigo fuente y la config.
COPY src/ ./src/
COPY config.json .

# 6. Pararse en src/ para que los imports planos funcionen.
WORKDIR /app/src

# 7. Comando que se ejecuta al arrancar el contenedor.
CMD ["python", "main.py"]