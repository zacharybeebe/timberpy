from datetime import datetime, date
from timberpy.timber._config import (
    ALL_SPECIES_NAMES,
    GRADE_NAMES
)


def cannot_set(affected_cls_name, attr_name):
    raise ReadOnlyAttributeError(affected_cls_name, attr_name)


def check_stand_arg(stand_arg, caller_class_name):
    if stand_arg.__class__.__name__ == 'Stand':
        return stand_arg
    else:
        raise StandArgError(stand_arg, caller_class_name)


def check_plot_arg(plot_arg, caller_class_name):
    if plot_arg.__class__.__name__ == 'Plot':
        return plot_arg
    else:
        raise PlotArgError(plot_arg, caller_class_name)


def check_timber_arg(timber_arg, caller_class_name):
    if timber_arg.__class__.__name__ == 'Timber':
        return timber_arg
    else:
        raise TimberArgError(timber_arg, caller_class_name)


def check_date_arg(date_inventory):
    if isinstance(date_inventory, datetime):
        return date_inventory
    elif isinstance(date_inventory, date):
        return datetime(date_inventory.year, date_inventory.month, date_inventory.day)
    elif isinstance(date_inventory, str):
        delimiters = ['/', '.', ',', '|', '-', '_']
        formats = ['%m{}%d{}%Y', '%Y{}%m{}%d', '%Y{}%d{}%m', '%d{}%m{}%Y', '%d{}%Y{}%m', '%m{}%Y{}%d']
        len_dt = len(date_inventory)
        if len_dt not in [6, 7, 8, 10]:
            raise DatetimeError(date_inventory)
        for i in delimiters:
            if i in date_inventory:
                if any([True if not j.isdigit() else False for j in [f'0{j}' if len(j) < 2 else j for j in date_inventory.split(i)]]):
                    raise DatetimeError(date_inventory)
                for f in formats:
                    x = [f'0{j}' if len(j) < 2 else j for j in date_inventory.split(i)]
                    idx_y = f.split('{}').index('%Y')
                    yy = x[idx_y]
                    if len(yy) == 2:
                        if int(yy) <= int(str(datetime.now().year)[3:]):
                            x[idx_y] = f'20{yy}'
                        else:
                            x[idx_y] = f'19{yy}'
                    check_date = i.join(x)
                    try:
                        return datetime.strptime(check_date, f.format(i, i))
                    except ValueError:
                        continue
    raise DatetimeError(date_inventory)


def check_species(species):
    spp_upper = species.upper()
    if spp_upper in ALL_SPECIES_NAMES:
        return spp_upper
    else:
        full_name_vals = {val: key for key, val in ALL_SPECIES_NAMES.items()}
        for sep in ['.', '_', '-']:
            full_name_vals.update({val.replace(' ', sep): key for key, val in ALL_SPECIES_NAMES.items()})
        if spp_upper in full_name_vals:
            return full_name_vals[spp_upper]
        else:
            raise SpeciesError(species)


def check_log_grade(grade):
    grd_upper = grade.upper()
    rev_grd = grd_upper[::-1]
    if grd_upper in GRADE_NAMES:
        return grd_upper
    elif rev_grd in GRADE_NAMES:
        return rev_grd
    else:
        full_name_vals = {val: key for key, val in GRADE_NAMES.items()}
        for sep in ['.', '_', '-']:
            full_name_vals.update({val.replace(' ', sep): key for key, val in GRADE_NAMES.items()})
        if grd_upper in full_name_vals:
            return full_name_vals[grd_upper]
        else:
            raise LogGradeError(grade)


def get_error_message(error_val: str, valid_codes: dict):
    valids = '\n'.join([f'{key} - {value}' for key, value in valid_codes.items()])
    return f"""\n\n[{error_val}] is not a valid species code. Valid Species Codes are...\n{valids}"""


class DatetimeError(Exception):
    def __init__(self, arg):
        super(DatetimeError, self).__init__(f'\n\nIncorrect Arg [{arg}] - Could not create a new datetime object from the provided arg')


class InvalidPlotNumberError(Exception):
    def __init__(self, number):
        super(InvalidPlotNumberError, self).__init__(f'\n\nIncorrect Arg [{number}] - Plot number cannot be less than 1')


class InvalidTreeNumberError(Exception):
    def __init__(self, number):
        super(InvalidTreeNumberError, self).__init__(f'\n\nIncorrect Arg [{number}] - Tree number cannot be less than 1')


class LogGradeError(Exception):
    def __init__(self, log_grade):
        super(LogGradeError, self).__init__(get_error_message(log_grade, GRADE_NAMES))


class PlotArgError(Exception):
    def __init__(self, arg, caller_cls_name):
        super(PlotArgError, self).__init__(f'\n\nIncorrect Arg [{arg}] - Plot Argument for {caller_cls_name} class needs to be class Plot')


class ReadOnlyAttributeError(Exception):
    def __init__(self, affected_cls_name, attr_name):
        super(ReadOnlyAttributeError, self).__init__(f'\n\nCannot modify attribute [{attr_name}] for class {affected_cls_name}, as it is READONLY')


class ImportStandError(Exception):
    def __init__(self, stand_name, filename):
        super(ImportStandError, self).__init__(f'\n\nCannot find Stand Name: {stand_name} within sheet: {filename}')


class SpeciesError(Exception):
    def __init__(self, species):
        super(SpeciesError, self).__init__(get_error_message(species, ALL_SPECIES_NAMES))


class StandArgError(Exception):
    def __init__(self, arg, caller_cls_name):
        super(StandArgError, self).__init__(f'\n\nIncorrect Arg [{arg}] - Stand Argument for {caller_cls_name} class needs to be Stand class')


class TimberArgError(Exception):
    def __init__(self, arg, caller_cls_name):
        super(TimberArgError, self).__init__(f'\n\nIncorrect Arg [{arg}] - Timber Argument for {caller_cls_name} class needs to be Timber class')


