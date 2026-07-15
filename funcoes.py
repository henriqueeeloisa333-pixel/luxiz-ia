def definir_cor(nota):
    if nota == 0: return "gray"
    if nota <= 1.9: return "red"
    if nota <= 3.9: return "orange"
    if nota <= 4.5: return "green"
    return "blue"
