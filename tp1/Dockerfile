# 1. Imagen base: Python 3.11 sobre un Linux liviano.
#    "slim" = version reducida (menos peso).
FROM python:3.11-slim

# 2. Carpeta de trabajo dentro de la imagen.
WORKDIR /app

# 3. Instalar dependencias primero (aprovecha la cache de Docker: si no cambian
#    los requirements, no reinstala en cada build). El TP usa solo stdlib, pero
#    se incluye por completitud y por si se agrega alguna dependencia.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar el codigo fuente y la config.
COPY src/ ./src/
COPY config.json .

# 5. Pararse en src/ para que los imports planos funcionen.
WORKDIR /app/src

# 6. Comando que se ejecuta al arrancar el contenedor.
CMD ["python", "main.py"]