import math


# TAPER EQUATION FUNCTIONS
def czaplewski(dbh: float, total_height: float, stem_height: int, a: float, b: float, c: float, d: float, e: float, f: float):
    Z = stem_height / total_height
    Z2 = (stem_height ** 2) / (total_height ** 2)
    I1 = int(Z < a)
    I2 = int(Z < b)
    dib = dbh * math.sqrt((c * (Z - 1)) + (d * (Z2 - 1)) + (e * ((a - Z) ** 2) * I1) + (f * ((b - Z) ** 2) * I2))
    return math.floor(dib)


def kozak1969(dbh: float, total_height: float, stem_height: int, a: float, b: float, c: float):
    Z = stem_height / total_height
    Z2 = (stem_height ** 2) / (total_height ** 2)
    dib = dbh * math.sqrt(a + (b * Z) + (c * Z2))
    return math.floor(dib)


def kozak1988(dbh: float, total_height: float, stem_height: int, a: float, b: float, c: float, d: float, e: float, f: float, g: float, h: float, i: float):
    Z = stem_height / total_height
    dib = (a * (dbh ** b) * (c ** dbh)) * ((1 - (Z ** 0.5)) / (1 - (d ** 0.5))) ** ((e * (Z ** 2)) + (f * math.log(Z + 0.001)) + (g * (Z ** 0.5)) + (h * math.exp(Z)) + (i * (dbh / total_height)))
    return math.floor(dib)


def wensel(dbh: float, total_height: float, stem_height: int, a: float, b: float, c: float, d: float, e: float):
    Z = (stem_height - 1) / (total_height - 1)
    X = (c + (d * dbh) + (e * total_height))
    dib = dbh * (a - (X * (math.log(1 - (Z ** b) * (1 - math.exp(a / X))))))
    return math.floor(dib)


