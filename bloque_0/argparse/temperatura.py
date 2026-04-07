import argparse
import sys

parser = argparse.ArgumentParser(description="Combierte temperaturas entre Celcius y Fahrenheit")

parser.add_argument("valor",type=float,help="Temperatura a convertir")
parser.add_argument("-t", "--to",
    choices=["celsius", "fahrenheit"],  # solo acepta estos dos valores
    required=True,                      # es obligatorio
    help="Unidad de destino"
)
args = parser.parse_args()
 
if args.to == "fahrenheit":
    resultado = args.valor * 9/5 + 32
    print(f"{args.valor}°C = {resultado}°F")
else:
    resultado = (args.valor - 32) * 5/9
    resultado = round(resultado, 2)
    print(f"{args.valor}°F = {resultado}°C")