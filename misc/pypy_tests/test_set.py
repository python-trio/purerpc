import random

s = set()
for i in range(100000000):
    s.add(i % 1000000)

print(len(s))
