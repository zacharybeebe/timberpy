from libc.math cimport sqrt, log, exp

# TAPER EQUATION FUNCTIONS
cpdef dict czaplewski_heights(float dbh, float total_height, float a, float b, float c, float d, float e, float f):
    cdef dict stem_heights = {}
    cdef int top_height = int(total_height)
    cdef int stem_height
    cdef float Z
    cdef float Z2
    cdef int I1
    cdef int I2
    cdef float dib
    cdef int dib_int
    cdef list dibs

    for stem_height in range(1, top_height + 1):
        Z = stem_height / total_height
        Z2 = (stem_height ** 2) / (total_height ** 2)
        I1 = int(Z < a)
        I2 = int(Z < b)
        dib = dbh * sqrt((c * (Z - 1)) + (d * (Z2 - 1)) + (e * ((a - Z) ** 2) * I1) + (f * ((b - Z) ** 2) * I2))
        dib_int = int(dib)
        dibs = [dib_int, dib, dib / 12.0]
        stem_heights[stem_height] = dibs

    return stem_heights


cpdef dict kozak1969_heights(float dbh, float total_height, float a, float b, float c):
    cdef dict stem_heights = {}
    cdef int top_height = int(total_height)
    cdef int stem_height
    cdef float Z
    cdef float Z2
    cdef float dib
    cdef int dib_int
    cdef list dibs

    for stem_height in range(1, top_height + 1):
        Z = stem_height / total_height
        Z2 = (stem_height ** 2) / (total_height ** 2)
        dib = dbh * sqrt(a + (b * Z) + (c * Z2))
        dib_int = int(dib)
        dibs = [dib_int, dib, dib / 12.0]
        stem_heights[stem_height] = dibs

    return stem_heights


cpdef dict kozak1988_heights(float dbh, float total_height, float a, float b, float c, float d, float e, float f, float g, float h, float i):
    cdef dict stem_heights = {}
    cdef int top_height = int(total_height)
    cdef int stem_height
    cdef float Z
    cdef float dib
    cdef int dib_int
    cdef list dibs

    for stem_height in range(1, top_height + 1):
        Z = stem_height / total_height
        dib = (a * (dbh ** b) * (c ** dbh)) * ((1 - (Z ** 0.5)) / (1 - (d ** 0.5))) ** ((e * (Z ** 2)) + (f * log(Z + 0.001)) + (g * (Z ** 0.5)) + (h * exp(Z)) + (i * (dbh / total_height)))
        dib_int = int(dib)
        dibs = [dib_int, dib, dib / 12.0]
        stem_heights[stem_height] = dibs

    return stem_heights


cpdef dict wensel_heights(float dbh, float total_height, float a, float b, float c, float d, float e):
    cdef dict stem_heights = {}
    cdef int top_height = int(total_height)
    cdef int stem_height
    cdef float Z
    cdef float X
    cdef float dib
    cdef int dib_int
    cdef list dibs

    for stem_height in range(1, top_height + 1):
        Z = (stem_height - 1) / (total_height - 1)
        X = (c + (d * dbh) + (e * total_height))
        dib = dbh * (a - (X * (log(1 - (Z ** b) * (1 - exp(a / X))))))
        dib_int = int(dib)
        dibs = [dib_int, dib, dib / 12.0]
        stem_heights[stem_height] = dibs

    return stem_heights
