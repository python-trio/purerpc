import random

def main():
    b = bytes(random.randrange(0, 256) for _ in range(50000))
    x = bytearray(b)
    for i in range(50000):
        x.extend(b)
        x = x[1:]
        print(len(x))


if __name__ == "__main__":
    main()