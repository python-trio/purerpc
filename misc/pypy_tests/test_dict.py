import random

s = {}
for i in range(100000000):
    s[i % 1000000] = i

print(len(s))
