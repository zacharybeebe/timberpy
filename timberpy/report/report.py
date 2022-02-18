from fpdf import FPDF

from timberpy.timber.timber_config import (
    ALL_SPECIES_NAMES,
    LENGTH_SORT
)

class Report(object):
    def __init__(self, stand):
        self._stand = stand
        self._sum_bkt = ['STAND METRICS', 'Not enough data']
        self._l_sum_bkt = ['LOG MERCHANDIZING']
        self._sum = self._stand.summary_df
        self._l_sum = self._stand.logs_summary_df
        self._stats = self._stand.stats_df
        self._spc = 15

    def console_report(self):
        self._console_print_bucket(self._sum_bkt)
        self._console_print_bucket(self._l_sum_bkt)

    def console_report_summary(self):
        self._console_print_bucket(self._sum_bkt)

    def console_report_logs_summary(self):
        self._console_print_bucket(self._l_sum_bkt)

    def _console_print_bucket(self, bucket):
        for line in bucket:
            if isinstance(line, list):
                print(''.join([self._f_data(i) for i in line]))
            else:
                print(line)
        print('\n\n\n')

    def _get_buckets(self):
        self._add_summary_to_bucket()
        for label, metric in [['BOARD FEET PER ACRE', 'net bf ac'], ['CUBIC FEET PER ACRE', 'net cf ac'], ['LOGS PER ACRE', 'lpa']]:
            self._add_logs_summary_to_bucket(label, metric)

    def _add_summary_to_bucket(self):
        if self._sum is not None:
            self._sum.pop(1)
            heads = ['species'] + list(self._sum.columns)
            self._sum_bkt += [
                (i for i in ['species'] + list(self._sum.columns)),
                '-' * len(heads) * self._spc,
            ]
            for spp in self._sum.index:
                if spp == 'TOTALS':
                    self._sum_bkt.append('-' * len(heads) * self._spc)
                self._sum_bkt.append([spp] + [self._sum.loc[spp, i] for i in self._sum.columns])

    def _add_logs_summary_to_bucket(self, summary_label: str, summary_stat: str in ['lpa', 'net bf ac', 'net cf ac']):
        if self._l_sum is not None:
            heads = ['LOG GRADES'] + sorted(set([col[0] for col in self._l_sum.columns]), key=lambda x: LENGTH_SORT[x])
            self._l_sum_bkt.append(summary_label)
            spp = None
            for index in self._l_sum.index:
                if index[0] != spp:
                    spp = index[0]
                    self._l_sum_bkt.append(self._f_spp_ctr(spp, len(heads)))
                    self._l_sum_bkt.append(heads)
                    self._l_sum_bkt.append('-' * len(heads) * self._spc)

    def _f_spp_ctr(self, value, heads_len):
        use_val = value
        split = 3
        if value != 'TOTALS':
            use_val = ALL_SPECIES_NAMES[value]
        return ('-' * int(heads_len * (split / heads_len)) * self._spc) + use_val + \
               ('-' * (int((heads_len * ((heads_len - split) / heads_len)) * self._spc) - len(use_val)))

    def _f_data(self, value):
        if isinstance(value, float):
            if value > 0:
                val = f'{value:,.1f}'
            else:
                val = '-'
        else:
            val = value
        return val + (' ' * (self._spc - len(val)))
