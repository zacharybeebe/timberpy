REQUIRED_COLS = {
    'Stand': {
        'iters': [['S', 'ST', 'STD', 'STND', 'STAND', 'PUNIT'], ['ID', 'CN', 'NM', 'NAME', '']],
        'idx': None,
        'required': True,
        'type': 'base',
        'default': None,
    },

    'Plot Factor': {
        'iters': [['P', 'PT', 'PLT', 'PLOT', 'X', 'EX', 'EXP', 'EXPANSION'], ['F', 'FAC', 'FACT', 'FACTOR']],
        'idx': None,
        'required': True,
        'type': 'base',
        'default': None,
    },

    'Plot': {
        'iters': [['P', 'PT', 'PLT', 'PLOT'], ['#', 'ID', 'N', 'NUM', 'NUMBER', '']],
        'idx': None,
        'required': True,
        'type': 'base',
        'default': None,
    },

    'Tree': {
        'iters': [['T', 'TR', 'TRE', 'TREE'], ['#', 'ID', 'N', 'NUM', 'NUMBER', '']],
        'idx': None,
        'required': True,
        'type': 'base',
        'default': None,
    },

    'Species': {
        'iters': [['SP', 'SPP', 'SPC', 'SPECIE', 'SPECIES'], ['CD', 'CODE', '']],
        'idx': None,
        'required': True,
        'type': 'base',
        'default': None,
    },

    'DBH': {
        'iters': [['D', 'DB', 'DBH', 'DIA', 'DIAM', 'DIAMETER', 'DIAMETER BREAST HEIGHT']],
        'idx': None,
        'required': True,
        'type': 'base',
        'default': None,
    },

    'Total Height': {
        'iters': [['T', 'TT', 'TTL', 'TOT', 'TOTAL', ''], ['H', 'HT', 'HGT', 'HEIGHT']],
        'idx': None,
        'required': True,
        'type': 'base',
        'default': None,
    },
}

QUICK_COLS = {

    'Pref Log Length': {
        'iters': [['PREF', 'PREFERRED', 'PLOG', 'PSEG'], ['LG', 'LOG', 'SG', 'SEG', 'SEGMENT', ''], ['LGT', 'LENGTH', '']],
        'idx': None,
        'required': False,
        'type': 'quick',
        'default': 40
    },

    'Min Log Length': {
        'iters': [['MIN', 'MINIMUM', 'MLOG', 'MSEG'], ['LG', 'LOG', 'SG', 'SEG', 'SEGMENT', ''], ['LGT', 'LENGTH', '']],
        'idx': None,
        'required': False,
        'type': 'quick',
        'default': 16
    },

    'Utility Log DIB': {
        'iters': [['UT', 'UTILITY', 'PLP', 'PULP'], ['LG', 'LOG', 'SG', 'SEG', 'SEGMENT', ''], ['D', 'DIB', 'DIA', '']],
        'idx': None,
        'required': False,
        'type': 'quick',
        'default': 3
    }
}

LOG_COLS = {
    'Log {} Stem Height': {
        'iters': [['LG', 'LOG', 'SG', 'SEG', 'SEGMENT'], ['ST', 'STM', 'STEM'], ['HT', 'HGT', 'HEIGHT']],
        'idx': None,
        'required': False,
        'type': 'full',
        'default': False
    },

    'Log {} Length': {
        'iters': [['LG', 'LOG', 'SG', 'SEG', 'SEGMENT'], ['LGT', 'LENGTH']],
        'idx': None,
        'required': False,
        'type': 'full',
        'default': False
    },

    'Log {} Grade': {
        'iters': [['LG', 'LOG', 'SG', 'SEG', 'SEGMENT'], ['GR', 'GRD', 'GRADE']],
        'idx': None,
        'required': False,
        'type': 'full',
        'default': False
    },

    'Log {} Defect': {
        'iters': [['LG', 'LOG', 'SG', 'SEG', 'SEGMENT'], ['DF', 'DFT', 'DEFECT']],
        'idx': None,
        'required': False,
        'type': 'full',
        'default': False
    }
}