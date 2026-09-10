def factorial(n: int) -> int: 
    if n < 0: 
        raise ValueError("Input must be a non negative integer")

    if n == 1 or n == 0:
        return 1
    return factorial(n - 1) * n

print(factorial(5))


