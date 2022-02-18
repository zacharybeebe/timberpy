from timberpy.timber.timber_config import (
    ALL_SPECIES_NAMES,
    GRADE_NAMES
)


def get_error_message(error_val: str, valid_codes: dict):
    valids = '\n'.join([f'{key} - {value}' for key, value in valid_codes.items()])
    return f"""\n[{error_val}] is not a valid species code. Valid Species Codes are...\n{valids}"""


class DatetimeError(Exception):
    def __init__(self, arg):
        super(DatetimeError, self).__init__(f'\nIncorrect Arg [{arg}] - Could not create a new datetime object from the provided arg')


class LogGradeError(Exception):
    def __init__(self, log_grade):
        super(LogGradeError, self).__init__(get_error_message(log_grade, GRADE_NAMES))


class PlotArgError(Exception):
    def __init__(self, arg):
        super(PlotArgError, self).__init__(f'\nIncorrect Arg [{arg}] - Plot Argument for Stand class needs to be class Plot')


class ReadOnlyAttributeError(Exception):
    def __init__(self):
        super(ReadOnlyAttributeError, self).__init__('\nCannot modify this attribute value as it is readonly')


class ImportStandError(Exception):
    def __init__(self, stand_name, filename):
        super(ImportStandError, self).__init__(f'\nCannot find Stand Name: {stand_name} within sheet: {filename}')


class SpeciesError(Exception):
    def __init__(self, species):
        super(SpeciesError, self).__init__(get_error_message(species, ALL_SPECIES_NAMES))


class TimberArgError(Exception):
    def __init__(self, arg, affected_class_name):
        super(TimberArgError, self).__init__(f'\nIncorrect Arg [{arg}] - Timber Argument for {affected_class_name} class needs to be TimberQuick or TimberFull')


