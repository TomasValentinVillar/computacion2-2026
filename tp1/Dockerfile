# 1. Imagen base: ya trae Python 3.11 instalado sobre un Linux liviano.
#    "slim" = version reducida (menos peso, menos cosas que no necesitamos).
FROM python:3.11-slim

# 2. Carpeta de trabajo DENTRO de la imagen. A partir de aca, todo pasa en /app.
#    Si no existe, Docker la crea.
WORKDIR /app

# 3. Copiamos nuestro archivo desde la maquina (izquierda) a la imagen (derecha).
#    El "." destino significa "la carpeta actual", que es /app por el WORKDIR.
COPY smoke_test.py .

# 4. Comando que se ejecuta cuando el contenedor arranca.
#    Cada palabra va como elemento de una lista (forma recomendada).
CMD ["python", "smoke_test.py"]