import pandas as pd
from timberpy.timber.timber_config import (
    GRADE_NAMES,
    LOG_LENGTHS,
    LOG_SERIES,
    OFFICIAL_GRADES,
    SCRIBNER_DICT
)
from timberpy.timber.timber_exceptions import (
    LogGradeError,
    ReadOnlyAttributeError,
    TimberArgError
)


class Log(object):
    def __init__(self, timber, stem_height: int, length: int, grade: str = '', defect: int = 0):
        """
        Log Class calculates the volume of an individual log from the Timber Class
        :param timber: Timber   -The parent Timber Class of log, needs to be an instance of Timber
        :param stem_height: int -The height along the tree stem of the top of the log
        :param length: int      -The length of the log in feet
        :param grade: str       -The grade code or grade name of the log's grade. This may be omitted and will be automatically
                                 calculated. See the documentation for valid grade codes/names
        :param defect: int      -The defect percentage of the log (as a whole number). 10 % defect = 10. This may be omitted and will
                                 default to 0.
        """
        self._tree = self._check_timber_arg(timber)
        self._stem_hgt = int(stem_height)
        self._length = int(length)
        self._defect = int(defect)

        self._species = self._tree.species
        self._lpa = self._tree._tpa

        self._top_dib = self._calc_top_dib()
        if grade != '':
            self._grade = self._check_log_grade(grade)
        else:
            self._grade = self._calc_log_grade()

        self._scrib = self._calc_scribner()
        self._gross_bf, self._net_bf = self._calc_board_feet()
        self._gross_cf, self._net_cf = self._calc_cubic_feet()

        self._gross_bf_ac = self._gross_bf * self._lpa
        self._net_bf_ac = self._net_bf * self._lpa
        self._gross_cf_ac = self._gross_cf * self._lpa
        self._net_cf_ac = self._net_cf * self._lpa

        self._grade_name = GRADE_NAMES[self._grade]
        self._length_range = self._get_length_range()

        self._series = pd.Series([self[f"_{i.replace(' ', '_')}"] for i in LOG_SERIES], index=LOG_SERIES)

    def __getitem__(self, item):
        _item = f'_{item}'
        if item in self.__dict__:
            return self.__dict__[item]
        elif _item in self.__dict__:
            return self.__dict__[_item]
        raise KeyError(f'{self.__class__.__name__} has no attribute {item}')

    def _get_length_range(self):
        """
        Gets the length range that the log's length is in
        """
        for rng in LOG_LENGTHS:
            if LOG_LENGTHS[rng][0] <= self._length <= LOG_LENGTHS[rng][1]:
                return rng

    def _calc_top_dib(self):
        """
        Uses the Timber Class' stem dibs dictionary to return the diameter inside bark (DIB) of its own stem height
        """
        return self._tree.stem_dibs[self._stem_hgt][0]

    def _calc_log_grade(self):
        """
        Returns the grade of the log based on species, minimum log lengths,
        and minimum log top DIBs set forth in the Official Rules for the Log Scaling and Grading Bureaus.
        Used when the grade argument is omitted.
        """
        for i, rules in enumerate(OFFICIAL_GRADES[self._species]):
            if self._top_dib >= rules[0] and self._length >= rules[1]:
                if self._defect > 5 and i < len(OFFICIAL_GRADES[self._species]) - 1:
                    return OFFICIAL_GRADES[self._species][i + 1][2]
                else:
                    return rules[2]

    def _calc_board_feet(self):
        """
        Returns the board feet (gross and net) of the log based on log length and the corresponding Scribner coefficient
        """
        gross = self._length * self._scrib
        return gross.__floor__(), (gross * (1 - (self._defect / 100))).__floor__()

    def _calc_cubic_feet(self):
        """
        Return the cubic feet (gross and net) of the log based on the Two-End Conic Cubic Foot Rule
        """
        if self._length < 17:
            x = self._length * 0.67
        else:
            x = self._length + 1
        gross = ((.005454 * x) * (((2 * ((self._top_dib + 0.7) ** 2)) + (2 * (self._top_dib + 0.7))) / 3))
        return gross, gross * (1 - (self._defect / 100))

    def _calc_scribner(self):
        """
        Return the Scribner coefficient for board foot calculation based on log length and log top DIB
        """
        if self._top_dib in range(6, 12):
            if 0 < self._length < 16:
                return SCRIBNER_DICT[self._top_dib][0]
            elif 16 <= self._length < 32:
                return SCRIBNER_DICT[self._top_dib][1]
            else:
                return SCRIBNER_DICT[self._top_dib][2]
        else:
            return SCRIBNER_DICT[self._top_dib]

    def _recalc_metrics(self):
        self._top_dib = self._calc_top_dib()
        self._scrib = self._calc_scribner()

        self._gross_bf, self._net_bf = self._calc_board_feet()
        self._gross_cf, self._net_cf = self._calc_cubic_feet()
        self._gross_bf_ac = self._gross_bf * self._lpa
        self._net_bf_ac = self._net_bf * self._lpa
        self._gross_cf_ac = self._gross_cf * self._lpa
        self._net_cf_ac = self._net_cf * self._lpa

        self._length_range = self._get_length_range()

    @staticmethod
    def _cannot_set():
        raise ReadOnlyAttributeError

    @staticmethod
    def _check_log_grade(grade):
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

    @staticmethod
    def _check_timber_arg(timber_arg):
        if timber_arg.__class__.__name__ == 'Timber':
            return timber_arg
        else:
            raise TimberArgError(timber_arg, Log.__class__.__name__)

    @property
    def tree(self):
        return self._tree

    @tree.setter
    def tree(self, value):
        self._cannot_set()

    @property
    def stem_hgt(self):
        return self._stem_hgt

    @stem_hgt.setter
    def stem_hgt(self, value):
        new_stem_height = int(value)
        difference = self._stem_hgt - new_stem_height
        self._length -= difference
        self._stem_hgt = new_stem_height
        self._recalc_metrics()

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, value):
        new_length = int(value)
        difference = self._length - new_length
        self._stem_hgt -= difference
        self._length = new_length
        self._recalc_metrics()

    @property
    def defect(self):
        return self._defect

    @defect.setter
    def defect(self, value):
        self._defect = int(value)
        self._recalc_metrics()

    @property
    def species(self):
        return self._species

    @species.setter
    def species(self, value):
        self._cannot_set()

    @property
    def lpa(self):
        return self._lpa

    @lpa.setter
    def lpa(self, value):
        self._cannot_set()

    @property
    def top_dib(self):
        return self._top_dib

    @top_dib.setter
    def top_dib(self, value):
        self._top_dib = int(value)
        self._recalc_metrics()

    @property
    def scrib(self):
        return self._scrib

    @scrib.setter
    def scrib(self, value):
        self._cannot_set()

    @property
    def grade(self):
        return self._grade

    @grade.setter
    def grade(self, value):
        self._grade = self._check_log_grade(value)
        self._grade_name = GRADE_NAMES[self._grade]

    @property
    def grade_name(self):
        return self._grade_name

    @grade_name.setter
    def grade_name(self, value):
        self._cannot_set()

    @property
    def gross_bf(self):
        return self._gross_bf

    @gross_bf.setter
    def gross_bf(self, value):
        self._cannot_set()

    @property
    def gross_cf(self):
        return self._gross_cf

    @gross_cf.setter
    def gross_cf(self, value):
        self._cannot_set()

    @property
    def gross_bf_ac(self):
        return self._gross_bf_ac

    @gross_bf_ac.setter
    def gross_bf_ac(self, value):
        self._cannot_set()

    @property
    def gross_cf_ac(self):
        return self._gross_cf_ac

    @gross_cf_ac.setter
    def gross_cf_ac(self, value):
        self._cannot_set()

    @property
    def net_bf(self):
        return self._net_bf

    @net_bf.setter
    def net_bf(self, value):
        self._cannot_set()

    @property
    def net_cf(self):
        return self._net_cf

    @net_cf.setter
    def net_cf(self, value):
        self._cannot_set()

    @property
    def net_bf_ac(self):
        return self._net_bf_ac

    @net_bf_ac.setter
    def net_bf_ac(self, value):
        self._cannot_set()

    @property
    def net_cf_ac(self):
        return self._net_cf_ac

    @net_cf_ac.setter
    def net_cf_ac(self, value):
        self._cannot_set()

    @property
    def length_range(self):
        return self._length_range

    @length_range.setter
    def length_range(self, value):
        self._cannot_set()

    @property
    def series(self):
        return self._series

    @series.setter
    def series(self, value):
        self._cannot_set()


