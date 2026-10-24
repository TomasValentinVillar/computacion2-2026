# 1. Imagen base: Python 3.11 sobre un Linux liviano.
FROM python:3.11-slim

# 2. Carpeta de trabajo dentro de la imagen.
WORKDIR /app

# 3. Dependencias primero: si solo cambia el código, Docker reusa esta capa
#    y no vuelve a instalar todo.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. El código fuente.
COPY src/ ./src/

# 5. Pararse en src/ para que los imports planos funcionen (igual que en el TP1).
WORKDIR /app/src

# 6. Puerto donde escucha la API (documentativo; el mapeo real va en el compose).
EXPOSE 8000

# 7. Forma exec (lista): python es el PID 1 y recibe directo el SIGTERM de
#    "docker compose stop". Con forma shell lo recibiría /bin/sh y no python.
CMD ["python", "main.py"]
