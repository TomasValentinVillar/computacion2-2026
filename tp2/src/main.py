"""Punto de entrada: la app FastAPI y el arranque del servidor."""
import uvicorn
from fastapi import FastAPI

app = FastAPI(title='Plataforma de tareas')


@app.get('/')
async def raiz():
    return {'servicio': 'tareas', 'docs': '/docs'}


# La guarda importa: con spawn (macOS/Windows) los procesos del
# ProcessPoolExecutor re-importan este módulo y sin ella arrancarían
# otro servidor cada uno.
if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
