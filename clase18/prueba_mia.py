
def acumulador():
    total = 0
    while True:
        n = yield total     # produce total, y RECIBE el próximo n
        total += n


a = acumulador()
next(a)                        # arrancarlo hasta el primer yield
print(a.send(10))              # 10
print(a.send(5))               # 15
print(a.send(20))
print()

# Qué pasa si te olvidás el next() inicial:
b = acumulador()
try:
    b.send(10)
except TypeError as e:
    print('TypeError:', e)
