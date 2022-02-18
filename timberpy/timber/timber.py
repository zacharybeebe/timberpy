import pandas as pd
from timberpy.timber.log import Log
from timberpy.timber.timber_config import (
    ALL_SPECIES_NAMES,
    TAPER_EQ,
    TAPER_HEIGHTS_EQ,
    TREE_SERIES
)
from timberpy.timber.timber_exceptions import (
    ReadOnlyAttributeError,
    SpeciesError,
)


class Timber(object):
    def __init__(self, tree_number: int, plot_factor: float, species: str, dbh: float, total_height: float,
                 auto_cruise: bool = False, preferred_log_length: int = 40, minimum_log_length: int = 16, utility_log_dib=3):
        """
        :param tree_number: int     -The number of the tree within the plot.
        :param plot_factor: float   -For fixed-area plots use the negative inverse of the plot size (1/30th ac = -30),
                                     for variable-area plots use the Basal Area Factor (BAF) (40 BAF = 40).
        :param species: str         -The species name or species code of the tree species. See documentation for valid species name/codes.
        :param dbh: float           -The Diameter at Breast Height of the tree in inches.
        :param total_height:        -The Total Height of the tree in feet.
        :param auto_cruise:         -If this is set to True, the tree will be virtually cruised. See below for more details.
        :param preferred_log_length:-This value is used by the auto-cruiser, default is industry standard of 40 feet.
        :param minimum_log_length:  -This value is used by the auto-cruiser, default is industry standard of 16 feet.
        :param utility_log_dib:     -This value is used by the auto-cruiser, default is industry minimum of 3 inches.

        The auto-cruiser uses stem-taper equations from Czaplewski, Kozak, or Wensel
        (depending on species) to calculate the DIB (diameter inside bark) at any stem height along the tree.

        To cruise the tree, first the auto-cruiser determines the merchantable DIB (diameter inside bark) of the tree,
        this is calculated from 40% of the DIB at a stem height of 17 feet (the FORM height). This is industry standard.

        The auto-cruiser then correlates that Merch DIB to a Merchantable Height. The tree is then split up into logs,
        up to this Merch Height with priority given to the Preferred Log Length and if Preferred Log Length
        cannot be achieved, then if the remaining length, up to Merch Height OR the height of the Utility Log DIB,
        is greater than or equal to the Minimum Log Length then that final log is added.

        Log metrics are sent to the Log Class, to which their volumes in Board Feet
        (using Scribner Coefficients based on Log Length and top DIB) and Cubic Feet (based on the Two-End Conic Cubic Foot Rule).
        Log grades are determined by species, minimum log lengths and minimum top DIBs set forth by the
        Official Rules for the Log Scaling and Grading Bureaus. Log defect is always 0.


        If you have your own log data from your own cruise, you can add that data to the tree by calling the Timber.add_log() method.
        The arguments for Timber.add_log() are...
            stem_height: int            -The height along the tree stem of the top of the log
            length: int                 -The length of the log in feet
            grade: str [optional] = ''  -The grade code or grade name of the log's grade. This may be omitted and will be automatically
                                         calculated. See the documentation for valid grade codes/names
            defect: int [optional] = 0  -The defect percentage of the log (as a whole number). 10 % defect = 10. This may be omitted and will
                                         default to 0.

        For inventory metrics, add this Timber Class to a Plot Class using the Plot's .add_tree() method.

        """

        self._number = int(tree_number)
        self._plot_factor = float(plot_factor)
        self._species = self._check_species(species)
        self._dbh = float(dbh)
        self._total_hgt = float(total_height)

        self._auto_cruise = bool(auto_cruise)
        self._pref_log = int(preferred_log_length)
        self._min_log = int(minimum_log_length)
        self._ut_log_dib = int(utility_log_dib)

        self._hdr = self._total_hgt / (self._dbh / 12)
        self._ba = self._dbh ** 2 * 0.005454
        self._rd = self._ba / (self._dbh ** (1 / 2))

        self._tpa, self._ba_ac, self._rd_ac = self._get_tpa_ba_ac_rd_ac()
        self._stem_dibs = TAPER_HEIGHTS_EQ[self._species](self._dbh, self._total_hgt)
        self._dib_heights = self._bucket_stem_dibs()

        self._merch_dib = (0.40 * self._stem_dibs[17][0]).__floor__()
        self._merch_hgt = self._dib_heights[self._merch_dib][-1]

        self._gross_bf = 0
        self._gross_cf = 0
        self._gross_bf_ac = 0
        self._gross_cf_ac = 0

        self._net_bf = 0
        self._net_cf = 0
        self._net_bf_ac = 0
        self._net_cf_ac = 0

        self._vbar = 0
        self._cbar = 0
        self._logs = {}
        self._series = None

        if self._auto_cruise:
            self._auto_cruise_add_logs()

        self._set_series()

    def __getitem__(self, item):
        _item = f'_{item}'
        if item in self.__dict__:
            return self.__dict__[item]
        elif _item in self.__dict__:
            return self.__dict__[_item]
        raise KeyError(f'{self.__class__.__name__} has no attribute {item}')

    def add_log(self, stem_height: int, length: int, grade: str = '', defect: int = 0):
        """
        Adds Log Class to the logs dictionary of Timber and recalculates the tree's volumes and
        volume-related metrics
        """
        stm_hgt = int(stem_height)
        lgt = int(length)
        grd = grade.upper()
        dft = int(defect)

        if not self._logs:
            self._logs[1] = Log(self, stm_hgt, lgt, grade=grd, defect=dft)
        else:
            num = max(self._logs) + 1
            self._logs[num] = Log(self, stm_hgt, lgt, grade=grd, defect=dft)
        self._get_volumes()
        self._set_series()

    def get_any_dib(self, stem_height: int):
        """
        Returns the diameter inside bark (DIB) at any given stem height
        """
        return TAPER_EQ[self._species](self._dbh, self._total_hgt, stem_height)

    def _auto_cruise_add_logs(self):
        """
        Method for virtually cruising the tree, this will determine the stem heights and lengths of the logs.
        Log Lengths are in multiples of 2 (24, 26, 28... feet).
        Stem Heights and Lengths are sent to the self.add_log() methosd which creates an instance
        of the Log Class for volume calculations.
        """
        stem_heights = self._auto_cruise_stem_heights()
        lengths = [(stem_heights[i + 1] - hgt) // 2 * 2 for i, hgt in enumerate(stem_heights[:-1])]

        for i, (stem_height, length) in enumerate(zip(stem_heights[1:], lengths), 1):
            self.add_log(stem_height, length)

    def _auto_cruise_log_stem(self, previous_log_stem_height):
        """
        Using the previous_log_stem_height arg, it will check if the minimum log length added to previous stem height plus
        1 foot of in-between is greater than the merch height, if it is, it will return None and no more logs can be added. If not
        it will check if the preferred log length added to the previous stem height plus 1 foot of in-between is less than
        or equal to the merch height, if it is then the new stem height is returned and a 40 foot (or user defined preferred length)
        log will added. If not then the merch height is the returned and a final log is added with a length determined by the difference
        between the merch height and previous stem height
        """
        min_log_check = previous_log_stem_height + self._min_log + 1

        if min_log_check > self._merch_hgt - 2:
            try:
                utility_height = self._dib_heights[self._ut_log_dib][-1]
            except KeyError:
                utility_height = self._dib_heights[self._ut_log_dib + 1][-1]
            if utility_height - previous_log_stem_height - 1 >= self._min_log:
                return True, utility_height
            else:
                return True, None
        else:
            if previous_log_stem_height + 1 + self._pref_log <= self._merch_hgt:
                return False, previous_log_stem_height + self._pref_log + 1
            else:
                return False, self._merch_hgt

    def _auto_cruise_stem_heights(self):
        """
        Starting at stem height of 1 (stump height), master is updated with the log stem height calculated from
        self._calc_log_stem(), if self._calc_log_stem returns (True, None), all logs have been found and iteration is complete
        """
        master = [1]
        for i in range(999):
            logs_complete, stem_height = self._auto_cruise_log_stem(master[i])
            if logs_complete:
                if stem_height is not None:
                    master.append(stem_height)
                break
            else:
                master.append(stem_height)
        return master

    def _bucket_stem_dibs(self):
        """
        Create a dictionary of DIB integers and appends a list with all of the stem heights that correspond to that DIB
        """
        dib_heights = {}
        for stem_height in self._stem_dibs:
            dib_int = self._stem_dibs[stem_height][0]
            if dib_int not in dib_heights:
                dib_heights[dib_int] = []
            dib_heights[dib_int].append(stem_height)
        return dib_heights

    def _get_tpa_ba_ac_rd_ac(self):
        """
        Calculates the Trees per Acre, Basal Area per Acre and Relative Density per Acre
        based on the plot factor
        """
        if self._plot_factor == 0:
            return 0, 0, 0
        else:
            if self._plot_factor > 0:
                tpa = self._plot_factor / self._ba
                ba_ac = self._plot_factor
                rd_ac = tpa * self._rd

            else:
                tpa = abs(self._plot_factor)
                ba_ac = abs(self._plot_factor) * self._ba
                rd_ac = tpa * self._rd
            return tpa, ba_ac, rd_ac

    def _get_volumes(self):
        """
        Calculates the tree's volume and volume-related metrics based on the log volumes
        """
        if not self._logs:
            return
        else:
            gross_bf, net_bf, gross_cf, net_cf = 0, 0, 0, 0
            for lnum in self._logs:
                log = self._logs[lnum]
                gross_bf += log.gross_bf
                gross_cf += log.gross_cf
                net_bf += log.net_bf
                net_cf += log.net_cf

            self._gross_bf = gross_bf
            self._gross_cf = gross_cf
            self._gross_bf_ac = self._gross_bf * self._tpa
            self._gross_cf_ac = self._gross_cf * self._tpa

            self._net_bf = net_bf
            self._net_cf = net_cf
            self._net_bf_ac = self._net_bf * self._tpa
            self._net_cf_ac = self._net_cf * self._tpa

            self._vbar = self._net_bf / self._ba
            self._cbar = self._net_cf / self._ba

    def _recalc_metrics(self, species_only=False):
        if not species_only:
            self._hdr = self._total_hgt / (self._dbh / 12)
            self._ba = self._dbh ** 2 * 0.005454
            self._rd = self._ba / (self._dbh ** (1 / 2))

        self._tpa, self._ba_ac, self._rd_ac = self._get_tpa_ba_ac_rd_ac()
        self._stem_dibs = TAPER_HEIGHTS_EQ[self._species](self._dbh, self._total_hgt)
        self._dib_heights = self._bucket_stem_dibs()

        self._merch_dib = (0.40 * self._stem_dibs[17][0]).__floor__()
        self._merch_hgt = self._dib_heights[self._merch_dib][-1]

        if self._logs:
            self._logs = {}
            logs = [[self._logs[log][i] for i in ['stem_height', 'length', 'grade', 'defect']] for log in self._logs]
            for log_args in logs:
                self.add_log(*log_args)

        self._set_series()

    def _set_series(self):
        self._series = pd.Series([self[f"_{i.replace(' ', '_')}"] for i in TREE_SERIES], index=TREE_SERIES)

    @staticmethod
    def _cannot_set():
        raise ReadOnlyAttributeError

    @staticmethod
    def _check_species(species):
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

    @property
    def number(self):
        return self._number

    @number.setter
    def number(self, value):
        self._number = int(value)

    @property
    def plot_factor(self):
        return self._plot_factor

    @plot_factor.setter
    def plot_factor(self, value):
        self._plot_factor = float(value)
        self._recalc_metrics()

    @property
    def species(self):
        return self._species

    @species.setter
    def species(self, value):
        self._species = self._check_species(value)
        self._recalc_metrics(species_only=True)

    @property
    def dbh(self):
        return self._dbh

    @dbh.setter
    def dbh(self, value):
        self._dbh = float(value)
        self._recalc_metrics()

    @property
    def total_hgt(self):
        return self._total_hgt

    @total_hgt.setter
    def total_hgt(self, value):
        self._total_hgt = float(value)
        self._recalc_metrics()

    @property
    def pref_log(self):
        return self._pref_log

    @pref_log.setter
    def pref_log(self, value):
        self._pref_log = int(value)
        if self._auto_cruise:
            self._auto_cruise_add_logs()
            self._recalc_metrics()

    @property
    def min_log(self):
        return self._min_log

    @min_log.setter
    def min_log(self, value):
        self._min_log = int(value)
        if self._auto_cruise:
            self._auto_cruise_add_logs()
            self._recalc_metrics()

    @property
    def ut_log_dib(self):
        return self._ut_log_dib

    @ut_log_dib.setter
    def ut_log_dib(self, value):
        self._ut_log_dib = int(value)
        if self._auto_cruise:
            self._auto_cruise_add_logs()
            self._recalc_metrics()

    @property
    def hdr(self):
        return self._hdr

    @hdr.setter
    def hdr(self, value):
        self._cannot_set()

    @property
    def ba(self):
        return self._ba

    @ba.setter
    def ba(self, value):
        self._cannot_set()

    @property
    def rd(self):
        return self._rd

    @rd.setter
    def rd(self, value):
        self._cannot_set()

    @property
    def tpa(self):
        return self._tpa

    @tpa.setter
    def tpa(self, value):
        self._cannot_set()

    @property
    def ba_ac(self):
        return self._ba_ac

    @ba_ac.setter
    def ba_ac(self, value):
        self._cannot_set()

    @property
    def rd_ac(self):
        return self._rd_ac

    @rd_ac.setter
    def rd_ac(self, value):
        self._cannot_set()

    @property
    def stem_dibs(self):
        return self._stem_dibs

    @stem_dibs.setter
    def stem_dibs(self, value):
        self._cannot_set()

    @property
    def dib_heights(self):
        return self._dib_heights

    @dib_heights.setter
    def dib_heights(self, value):
        self._cannot_set()

    @property
    def merch_dib(self):
        return self._merch_dib

    @merch_dib.setter
    def merch_dib(self, value):
        self._cannot_set()

    @property
    def merch_hgt(self):
        return self._merch_hgt

    @merch_hgt.setter
    def merch_hgt(self, value):
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
    def vbar(self):
        return self._vbar

    @vbar.setter
    def vbar(self, value):
        self._cannot_set()

    @property
    def cbar(self):
        return self._cbar

    @cbar.setter
    def cbar(self, value):
        self._cannot_set()

    @property
    def logs(self):
        return self._logs

    @logs.setter
    def logs(self, value):
        self._cannot_set()

    @property
    def series(self):
        return self._series

    @series.setter
    def series(self, value):
        self._cannot_set()


if __name__ == '__main__':
    from time import perf_counter

    def timer(func):
        def wrapper(*args, **kwargs):
            now = perf_counter()
            x = func(*args, **kwargs)
            after = perf_counter()
            print(f'{func.__name__} took {round(after - now, 10)} seconds\n')
            return x
        return wrapper

    @timer
    def speed_test(rng):
        tnum, pf, spp, dbh, hgt = [1, 40, 'df', 24.5, 123]
        for i in range(rng):
            Timber(tnum, pf, spp, dbh, hgt)

    # speed_test(100000)
    # speed_test(10000)
    # speed_test(1000)

    timber = Timber(1, 40, 'rc', 18.8, 103, auto_cruise=True)

    num = 150
    print('timber.series ' + ('#' * num) + '\n')
    print(timber.series.head(len(timber.series)))

    print('\n\ntimber.logs[1].series ' + ('#' * num) + '\n')
    print(timber.logs[1].series.head(len(timber.logs[1].series)))






























