import asyncio
import httpx
limite = asyncio.Semaphore(10)

async def bajar(cliente, url):
    async with limite:
        respuesta = await cliente.get(url)
    return url, respuesta.status_code, len(respuesta.content)

async def main():
    async with httpx.AsyncClient(timeout=10) as cliente:
        urls = ['https://example.com', 'https://httpbin.org/get']
        resultados = await asyncio.gather(*(bajar(cliente, u) for u in urls))
        for url, codigo, tam in resultados:
            print(f'{codigo}  {tam:>6} bytes  {url}')

asyncio.run(main())
