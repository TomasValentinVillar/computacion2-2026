from multiprocessing import shared_memory

# Probemos con un slot pequeño y vamos creciendo
sl = shared_memory.ShareableList(["abc"], name="test_3")
print(f"Slot inicial: 3 chars")

intentos = [
    "ab",                    # 2 chars
    "abcd",                  # 4 chars
    "abcdefghij",            # 10 chars
    "abcdefghijklmnopqrst",  # 20 chars
]

for s in intentos:
    try:
        sl[0] = s
        print(f"OK   - {len(s):2} chars: '{sl[0]}'")
    except ValueError as e:
        print(f"FAIL - {len(s):2} chars: {e}")

sl.shm.close()
sl.shm.unlink()