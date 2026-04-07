import sys

try:
    n = 0
    r = 0
    for i in sys.argv[1: ]:

        n = float(i)
        r = r + n
    print(f"La suma es: {r}")
except:
    ValueError(print("Ingerese unicamente numeros"))

sys.exit(1)

