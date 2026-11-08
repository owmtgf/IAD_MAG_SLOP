def solve(data):
    total = 0
    for amount, numerator, denominator in data:
        scaled = amount * numerator
        # Округление половины вверх: (x + 0.5) // 1 для целых x, но здесь x = scaled / denominator
        # Используем формулу: floor((scaled + denominator/2) / denominator) = (scaled + denominator//2) // denominator
        # Но нужно быть осторожным с чётностью denominator. Правильная формула для округления вверх до целого:
        # round_half_up(x) = floor(x + 0.5)
        # x = scaled / denominator
        # x + 0.5 = (scaled + 0.5 * denominator) / denominator
        # floor(...) = (scaled + (denominator + 1) // 2) // denominator ? Нет.
        # Правильный подход без float: (scaled + denominator // 2) // denominator работает только если denominator чётное? Нет.
        # Формула: (scaled + (denominator + 1) // 2) // denominator - это для округления вверх? Проверим.
        # Пример: scaled=1, den=2 -> 1/2 = 0.5 -> 1. (1 + (2+1)//2) // 2 = (1+1)//2 = 1. OK.
        # scaled=1, den=3 -> 1/3 = 0.33 -> 0. (1 + 4//2) // 3 = (1+2)//3 = 1. WRONG. Нужно 0.
        # Формула для round half up: (scaled + denominator // 2) // denominator НЕ работает для нечётных denominators.
        # Правильная формула: (scaled + (denominator + 1) // 2) // denominator? Нет, это тоже не то.
        # Давайте используем: (scaled * 2 + denominator) // (2 * denominator) ? Нет, это для другой задачи.
        # Округление x = a/b до ближайшего целого с округлением 0.5 вверх:
        # result = floor((a + b/2) / b) = floor((2a + b) / (2b)) = (2a + b) // (2b) ?
        # Проверим: a=1, b=2 -> (2+2)//4 = 1. OK.
        # a=1, b=3 -> (2+3)//6 = 5//6 = 0. OK.
        # a=2, b=3 -> 2/3 = 0.66 -> 1. (4+3)//6 = 7//6 = 1. OK.
        # a=1, b=4 -> 0.25 -> 0. (2+4)//8 = 0. OK.
        # a=2, b=4 -> 0.5 -> 1. (4+4)//8 = 1. OK.
        # Формула: (2 * scaled + denominator) // (2 * denominator)
        term = 2 * scaled + denominator
        rounded = term // (2 * denominator)
        total += rounded
    return total
