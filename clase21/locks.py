import asyncio

# --- Pregunta 2: incrementar sin await adentro ---
contador = 0

async def incrementar():
    global contador
    contador += 1

# --- Pregunta 3 y 4: transferir con un await en el medio ---
cuentas = {}

async def log(monto):
    await asyncio.sleep(0.001)          # simula escribir el log: cede el control

async def transferir(a, b, monto):
    saldo = cuentas[a]
    await log(monto)
    cuentas[a] = saldo - monto

lock = asyncio.Lock()

async def transferir_con_lock(a, b, monto):
    async with lock:
        saldo = cuentas[a]
        await log(monto)
        cuentas[a] = saldo - monto


async def main():
    N = 100

    print('=== Pregunta 2: incrementar, sin lock ===')
    await asyncio.gather(*(incrementar() for _ in range(N)))
    print(f'  contador = {contador}  (esperado {N})')

    print('\n=== Pregunta 3: transferir, sin lock ===')
    cuentas.update({'a': 10_000, 'b': 0})
    await asyncio.gather(*(transferir('a', 'b', 1) for _ in range(N)))
    print(f'  saldo final = {cuentas["a"]}  (esperado {10_000 - N})')
    print(f'  operaciones perdidas: {cuentas["a"] - (10_000 - N)}')

    print('\n=== Pregunta 4: transferir, con asyncio.Lock ===')
    cuentas.update({'a': 10_000, 'b': 0})
    await asyncio.gather(*(transferir_con_lock('a', 'b', 1) for _ in range(N)))
    print(f'  saldo final = {cuentas["a"]}  (esperado {10_000 - N})')
    print(f'  operaciones perdidas: {cuentas["a"] - (10_000 - N)}')


asyncio.run(main())
