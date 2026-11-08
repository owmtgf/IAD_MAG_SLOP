def solve(data):
    left, right = data['day']
    out = []
    for a, b in sorted(data['intervals']):
        # Обрезаем интервал по [left, right)
        a = max(left, a)
        b = min(right, b)
        # Удаляем, если интервал пуст или полностью вне диапазона (после обрезки a > b)
        if a > b:
            continue
        # Убираем дубликаты и объединяем соседние/пересекающиеся интервалы
        if out and a <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out
