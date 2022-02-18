import os

import numpy as np
import pandas as pd
import plotly.express as plt
from datetime import datetime, date
from statistics import mean, stdev, variance
from io import BytesIO

from timberpy.report.report import Report
from timberpy.inventory.inventory import Inventory
from timberpy.timber.plot import Plot
from timberpy.timber.timber import Timber
from timberpy.timber.log import Log
# from treetopper.thin import (
#     ThinTPA,
#     ThinBA,
#     ThinRD
# )
# from treetopper._exceptions import TargetDensityError
# from treetopper.fvs import FVS
from timberpy.timber.timber_config import (
    ALL_SPECIES_NAMES,
    GRADE_SORT,
    INVENTORY_SERIES,
    LENGTH_SORT,
    LOG_INVENTORY_SERIES,
    LOG_LENGTHS,
    PLOT_SERIES,
    SPECIES_SORT,
    SUMMARY_SERIES_INIT,
    SUMMARY_SERIES_FINAL,
    STAND_SERIES,
    STATS_SERIES,
    TREE_SERIES
)
from timberpy.timber.timber_exceptions import (
    DatetimeError,
    ImportStandError,
    PlotArgError,
    ReadOnlyAttributeError
)


class Stand(object):
    """The Stand Class represents a stand of timber that has had an inventory conducted on it. It should made up of plots (Plot Class)
       which contain trees (Timber Classes).

       The Stand class will run calculations and statistics of the current stand conditions and it will run calculations of the log
       merchantabilty for three metrics: logs per acre, log board feet per acre, and log cubic feet per acre, based on log grades,
       log length ranges and species.

       """

    def __init__(self, name: str, acres: float = 0, date_inventory: str = date.today()):
        """
        The Stand Class represents a stand of timber that has had an inventory conducted on it. It should made up of plots (Plot Class)
        which contain trees (Timber Class).

        The Stand class will run calculations and statistics of the current stand conditions and it will run calculations of the log
        merchantabilty for three metrics: logs per acre, log board feet per acre, and log cubic feet per acre, based on log grades,
        log length ranges and species.

        Multiple pandas DataFrames are created that give plot/tree/log lists, summarize the stand and summarize the log merchandizing

        ####################################################

        :param name: str                     -The stand's name or identifier eg "EX1"
        :param acres: float                  -The acres of the stand
        :param date_inventory: str/datetime  -The date that the inventory was taken can be a string date or datetime object
        """
        self._name = name.upper()
        self._acres = float(acres)
        self._date_inventory = self._check_date_arg(date_inventory)

        self._plots_df = None
        self._trees_df = None
        self._summary_df = None
        self._dbh_df = None
        self._stats_df = None
        self._logs_df = None
        self._logs_summary_df = None

        self._plots = []
        self._plot_count = 0

        self._tree_count = 0
        self._species = ()
        self._species_count = 0

        self._tpa = 0
        self._ba_ac = 0
        self._qmd = 0
        self._rd_ac = 0
        self._gross_bf_ac = 0
        self._gross_cf_ac = 0
        self._net_bf_ac = 0
        self._net_cf_ac = 0
        self._total_hgt = 0
        self._merch_hgt = 0
        self._hdr = 0
        self._vbar = 0
        self._cbar = 0
        self._series = None

        self._spc = 13
        self._report = Report(self)
        self._rpt_bkt = []

    def __getitem__(self, item):
        _item = f'_{item}'
        if item in self.__dict__:
            return self.__dict__[item]
        elif _item in self.__dict__:
            return self.__dict__[_item]
        raise KeyError(f'{self.__class__.__name__} has no attribute {item}')

    # def console_report(self):
    #     """Prints a console-formatted string of the complete stand report"""
    #     print(self._compile_report_text())
    #
    # def get_pdf_report_bytes_io(self):
    #     pdf = self._compile_pdf_report()
    #     return BytesIO(pdf.output(dest='S').encode('latin-1'))
    #
    # def pdf_report(self, filename: str, directory: str = None, start_file_upon_creation: bool = False):
    #     """Exports a pdf of the complete stand report to a user specified directory or if directory is None,
    #     to the current working directory. Will open the created pdf report if start_file_upon_creation is True"""
    #     check = filename if filename[-4:] == '.pdf' else f'{filename}.pdf'
    #     if directory:
    #         file = join(directory, check)
    #     else:
    #         file = join(getcwd(), check)
    #
    #     pdf = self._compile_pdf_report()
    #     pdf.output(file, 'F')
    #     if start_file_upon_creation:
    #         startfile(file)

    def add_plot(self, plot: Plot):
        """
        Adds a plot to the stand's plots list and re-runs the calculations and statistics of the stand.
        plot argument needs to be the a Plot Class
        """
        plt = self._check_plot_arg(plot)
        self._plots.append(plt)
        self._set_dataframes()
        self._set_series()

    def console_report(self):
        self._report.console_report()

    def import_sheet(self, filename):
        inv = Inventory(filename)
        if self._name not in inv.data_read:
            raise ImportStandError(self._name, filename)

        data = inv.data_read[self._name]
        hdr = data['hdr']
        for plot_num in data['plots']:
            pf1 = data['plots'][plot_num]['plot_factor']
            plot = Plot(plot_num, pf1)
            for tree_row in data['plots'][plot_num]['trees']:
                pf2, tree_num, species, dbh, total_height = tree_row[:5]
                if total_height in ['', ' ', None]:
                    total_height = (float(dbh) / 12) * hdr
                if tree_row[-1]:
                    plog, mlog, ut_dib = tree_row[5:-1]
                    tree = Timber(tree_num, pf2, species, dbh, total_height, True, plog, mlog, ut_dib)
                else:
                    tree = Timber(tree_num, pf2, species, dbh, total_height, False)
                    for log in tree_row[-2]:
                        tree.add_log(*log)
                plot.add_tree(tree)
            self.add_plot(plot)

    def plotly_dbh_range(self, column_name, show=True):
        """
        Returns a plot.express.bar chart of the data corresponding to the column name arg broken out by
        diameter range.
        :param column_name:             -The column name of the data to be graphed ['tpa', 'net bf ac', 'vbar', etc.]
        :param show:                    -If this is set to True, it will call plotly.express.bar.show() to display the graph
        :return: plotly.express.bar
        """
        fig = self._get_plotly('dbh', column_name)
        if show:
            fig.show()
        return fig

    def plotly_summary(self, column_name, show=True):
        """
        Returns a plot.express.bar chart of the data corresponding to the column name arg broken out by species.
        :param column_name:             -The column name of the data to be graphed ['tpa', 'net bf ac', 'vbar', etc.]
        :param show:                    -If this is set to True, it will call plotly.express.bar.show() to display the graph
        :return: plotly.express.bar
        """
        fig = self._get_plotly('summary', column_name)
        if show:
            fig.show()
        return fig

    def _get_plotly(self, from_type, column_name):
        """
        Formats the plotly bar chart from either stand.summary_df or stand.dbh_df depending on the from_type arg,
        and gets the column data from the column_name arg.
        :param from_type: str           -The code for the DataFrame to graph, either 'summary' or 'dbh'
        :param column_name:             -The column name corresponding to the DataFrame columns to get the data
        :return: plotly.express.bar
        """
        if from_type == 'summary':
            df = self._summary_df[column_name][:-1].copy()
            df.index = df.index.map(lambda x: ALL_SPECIES_NAMES[x])
            title = f'<b>Stand {self._name}: {column_name.upper()} by Species</b>'
            xaxis = '<b>Species</b>'
        else:
            df = self._dbh_df[column_name][:-1].copy()
            df.index = df.index.map(lambda x: str(x.left) if x != 'TOTALS' else x)
            title = f'<b>Stand {self._name}: {column_name.upper()} by Diameter Distribution</b>'
            xaxis = '<b>Diameter Distribution (inches)</b>'

        df_text = [f'<b>{i:,.1f}</b>' for i in df.values]
        fig = plt.bar(df, x=df.index, y=column_name, text=df_text)
        fig.update_layout(
            title=title,
            xaxis_title=xaxis,
            yaxis_title=f'<b>{column_name.upper()}</b>'
        )
        fig.update_traces(textposition='outside')
        return fig

    def _get_statistics(self, data):
        """
        Runs the statistical calculations on a set of the stand conditions data, returns an updated sub dict
        """
        m = mean(data)
        no = 'Not enough data'
        go = False
        if len(data) >= 2:
            go = True

        std = stdev(data)                                           if go else no
        var = variance(data)                                        if go else no
        ste = std / (self.plot_count ** (1 / 2))                    if go else no
        stepct = (ste / m) * 100                                    if go else no
        low, avg, high = [max(round(m - ste, 1), 0), m, m + ste]    if go else [no, no, no]

        d = {
            'mean': m,
            'variance': var,
            'stdev': std,
            'stderr': ste,
            'stderr pct': stepct,
            'low': low,
            'avg': avg,
            'high': high
        }
        return d

    def _get_summaries_df(self, groupby, start_summaries=0):
        """
        Creates a summary DataFrame depending on the groupby argument
        The initial data are the data that need to be summed, the final data adds the data that needs to be averaged or calculated.
        Summed data are averaged by the number of plots within the stand

        :param groupby:             -A column name or pandas.cut of a range of values
        :param start_summaries:     -The index to start the SUMMARY_SERIES_INIT list for column names
        :return: pandas DataFrame
        """
        df = self._trees_df[SUMMARY_SERIES_INIT[start_summaries:]].groupby(by=groupby).sum()
        df.loc['TOTALS'] = df.sum()
        df = df.div(len(self._plots))

        df['qmd'] = df['ba ac'].div(df['tpa']).div(0.005454) ** (1 / 2)
        df['vbar'] = df['net bf ac'].div(df['ba ac'])
        df['cbar'] = df['net cf ac'].div(df['ba ac'])

        if isinstance(groupby, str):
            subs = {sub: [groupby, sub] for sub in ['total hgt', 'merch hgt', 'hdr']}
        else:
            subs = {sub: sub for sub in ['total hgt', 'merch hgt', 'hdr']}

        for column, slicer in subs.items():
            df[column] = self._trees_df[slicer].groupby(by=groupby).mean()
            df.loc['TOTALS', column] = self._trees_df[column].mean()

        return df[SUMMARY_SERIES_FINAL]

    def _set_dataframes(self):
        self._set_plot_df()
        self._set_tree_df()
        self._set_summary_df()
        self._set_dbh_df()
        self._set_stats_df()
        self._set_logs_df()
        self._set_logs_sum_df()
        self._set_inventory_df()

    def _set_plot_df(self):
        """
        This DataFrame is a collection of the plot's pandas Series within the stand, transposed
        so that the Series' indexes become the columns
        """
        data = {plot.series['number']: plot.series for plot in self._plots}
        self._plots_df = pd.DataFrame(data, index=PLOT_SERIES[1:]).transpose()

    def _set_tree_df(self):
        """
        This DataFrame is a collection of the tree's pandas Series within the stand, transposed
        so that the Series' indexes become the columns
        """
        data = {}
        for plot in self._plots:
            for tree in plot.trees:
                tree_series = tree.series
                tree_series['plot number'] = plot.number
                tree_series['tree number'] = tree.number
                data.update({f'{plot.number}_{tree.number}': tree.series})
        self._trees_df = pd.DataFrame(data, index=TREE_SERIES[1:]).transpose()

        self._plot_count = len(self._plots_df)
        self._tree_count = len(self._trees_df)
        self._species = tuple(sorted(set(self._trees_df['species'].to_list()), key=lambda x: SPECIES_SORT[x]))
        self._species_count = len(self._species)

    def _set_summary_df(self):
        """
        This DataFrame is a summary of the tree data within the stand. It is grouped by species and adds a totals row.
        Stand properties are also updated after the creation of the summary DataFrame
        """
        self._summary_df = self._get_summaries_df('species')

        for attr in STAND_SERIES[3:]:
            setattr(self, f"_{attr.replace(' ', '_')}", self._summary_df.loc['TOTALS', attr])

    def _set_dbh_df(self):
        """
        This DataFrame is a summary of the tree data within the stand. It is grouped by DBH ranges, every 2 inches,
        and adds a totals row.
        """
        min_dbh = self._trees_df['dbh'].min().__floor__() * 2 // 2
        max_dbh = (self._trees_df['dbh'].max().__ceil__() * 2 // 2) + 2
        groupby = pd.cut(self._trees_df['dbh'], np.arange(min_dbh, max_dbh, 2))

        self._dbh_df = self._get_summaries_df(groupby, start_summaries=1)
        #self._dbh_df.index = self._dbh_df.index.map(lambda x: x.left if x != 'TOTALS' else x)

    def _set_stats_df(self):
        """
        This DataFrame is a summary of the statistics for the stand.
        Described metrics are 'tpa', 'ba ac', 'rd ac', 'gross bf ac', 'gross cf ac', 'net bf ac', and 'net cf ac'.
        The Statistics include mean, variance, standard deviation, standard error, standard error percent, and the low, avg, and high
        value estimates of each metric.
        """
        t = 'TOTALS'
        data = {}
        totals = {}
        for plot in self._plots:
            for metric in STATS_SERIES:
                for spp in self._species:
                    if (spp, metric) not in data:
                        data[(spp, metric)] = []
                    data[(spp, metric)].append(plot.trees_df[metric].loc[plot.trees_df['species'] == spp].sum())
                if (t, metric) not in totals:
                    totals[(t, metric)] = []
                totals[(t, metric)].append(plot.trees_df[metric].sum())
        data.update(totals)

        stats = {}
        for key, metric_vals in data.items():
            stats[key] = self._get_statistics(metric_vals)

        stats = {key: stats[key] for key in sorted(stats, key=lambda x: SPECIES_SORT[x[0]])}
        self._stats_df = pd.DataFrame.from_dict(stats, orient='index')

    def _set_logs_df(self):
        """
        This DataFrame is a collection of each tree's log's pandas Series, adding plot number, tree number and log number
        to the log Series and then transposing so that the log Series' indexes become the columns
        """
        data = {}
        for plot in self._plots:
            for tree in plot.trees:
                for lnum, log in tree.logs.items():
                    log_series = log.series
                    log_series['plot number'] = plot.number
                    log_series['tree number'] = tree.number
                    log_series['log number'] = lnum
                    data.update({f'{plot.number}_{tree.number}_{lnum}': log.series})
        self._logs_df = pd.DataFrame(data).transpose()

    def _set_logs_sum_df(self):
        """
        This DataFrame is a summary of the log merchandizing data. The final Dataframe is grouped
        by species and log grade as the indexes. The log length ranges are the columns. The table data consists of
        logs per acre (lpa), net board feet per acre, and net cubic feet per acre. Totals for grades and length ranges are calculated
        as well.
        """
        t = 'TOTALS'
        length_ranges = list(LOG_LENGTHS) + [t]
        table_values = ['lpa', 'net bf ac', 'net cf ac']

        data = {}
        totals = {}
        grpd_logs = self.logs_df.groupby(by=['species', 'grade', 'length range'], as_index=False).sum()

        for i in grpd_logs.index:
            spp, grade, lrng, lpa, bf_ac, cf_ac = (grpd_logs.loc[i, 'species'], grpd_logs.loc[i, 'grade'], grpd_logs.loc[i, 'length range'],
                                                   grpd_logs.loc[i, 'lpa'], grpd_logs.loc[i, 'net bf ac'], grpd_logs.loc[i, 'net cf ac'])

            for sheet, key in [[totals, (t, t)], [totals, (spp, t)], [data, (spp, grade)]]:
                if key not in sheet:
                    sheet[key] = {}
                    for value_type in table_values:
                        sheet[key].update({(length_range, value_type): 0 for length_range in length_ranges})

                for val_type, val in zip(table_values, [lpa, bf_ac, cf_ac]):
                    corrected_val = val / len(self._plots)
                    sheet[key][(lrng, val_type)] += corrected_val
                    sheet[key][(t, val_type)] += corrected_val
        data.update(totals)

        data = {key: {sub: data[key][sub]
                      for sub in sorted(data[key], key=lambda a: LENGTH_SORT[a[0]])}
                for key in sorted(data, key=lambda z: (SPECIES_SORT[z[0]], GRADE_SORT[z[1]]))}

        self._logs_summary_df = pd.DataFrame.from_dict(data, orient='index')
        self._logs_summary_df.columns = pd.MultiIndex.from_tuples([(c[0], c[1]) for c in self._logs_summary_df.columns])

    def _set_inventory_df(self):
        data = [[i for i in INVENTORY_SERIES]]
        max_logs = max([max([len(tree.logs) for tree in plot.trees]) for plot in self._plots])
        for i in range(1, max_logs + 1):
            for j in LOG_INVENTORY_SERIES:
                data[0].append(j.format(i))
        for plot in self._plots:
            for tree in plot.trees:
                temp = [self._name, plot.number, plot.plot_factor, tree.number] + [tree[i.replace(' ', '_')] for i in INVENTORY_SERIES[4:]]
                for i in range(1, max_logs + 1):
                    if i in tree.logs:
                        log = tree.logs[i]
                        temp += [log.stem_hgt, log.length, log.top_dib, log.grade, log.defect]
                    else:
                        temp += [np.nan for _ in range(5)]
                data.append(temp)
        self._inventory_df = pd.DataFrame(data[1:], columns=data[0])

    def _set_series(self):
        self._series = pd.Series([self[f"_{i.replace(' ', '_')}"] for i in STAND_SERIES], index=STAND_SERIES)

    @staticmethod
    def _cannot_set():
        raise ReadOnlyAttributeError

    @staticmethod
    def _check_date_arg(date_inventory):
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

    @staticmethod
    def _check_plot_arg(plot_arg):
        if isinstance(plot_arg, Plot):
            return plot_arg
        else:
            raise PlotArgError(plot_arg)


    # def import_sheet_quick(self, file_path: str):
    #     """Imports tree and plot data from a CSV or XLSX file for a quick cruise and adds that data to the stand"""
    #     plots = import_from_sheet(file_path, self.name, 'q')
    #     for plot_num in plots:
    #         plot = Plot()
    #         for tree in plots[plot_num]:
    #             plot.add_tree(TimberQuick(self.plot_factor, *tree))
    #         self.add_plot(plot)
    #
    # def import_sheet_full(self, file_path: str):
    #     """Imports tree and plot data from a CSV or XLSX file for a full cruise and adds that data to the stand"""
    #     plots = import_from_sheet(file_path, self.name, 'f')
    #     for plot_num in plots:
    #         plot = Plot()
    #         for tree_data in plots[plot_num]:
    #             args = tree_data[: -1]
    #             logs = tree_data[-1]
    #             tree = TimberFull(self.plot_factor, *args)
    #             for log in logs:
    #                 tree.add_log(*log)
    #             plot.add_tree(tree)
    #         self.add_plot(plot)
    #
    # def table_to_csv(self, filename: str, directory: str = None):
    #     """Creates or appends a CSV file with tree data from self.table_data"""
    #     check = extension_check(filename, '.csv')
    #     if directory:
    #         file = join(directory, check)
    #     else:
    #         file = join(getcwd(), check)
    #
    #     if isfile(file):
    #         allow = 'a'
    #         start = 1
    #     else:
    #         allow = 'w'
    #         start = 0
    #
    #     with open(file, allow, newline='') as csv_file:
    #         csv_write = writer(csv_file, dialect=excel)
    #         for i in self.table_data[start:]:
    #             csv_write.writerow(i)
    #
    # def table_to_excel(self, filename: str, directory: str = None):
    #     """Creates or appends an Excel file with tree data from self.table_data"""
    #     check = extension_check(filename, '.xlsx')
    #     if directory:
    #         file = join(directory, check)
    #     else:
    #         file = join(getcwd(), check)
    #
    #     if isfile(file):
    #         wb = load_workbook(file)
    #         ws = wb.active
    #         for i in self.table_data[1:]:
    #             ws.append(i)
    #         wb.save(file)
    #     else:
    #         wb = Workbook()
    #         ws = wb.active
    #         for i in self.table_data:
    #             ws.append(i)
    #         wb.save(file)





    # def _compile_report_text(self):
    #     """Compiles the console-formatted report of all stand data and stats, used internally"""
    #     n = '\n' * 4
    #     console_text = f'{print_stand_species(self.summary_stand)}{n}'
    #     console_text += f'{print_stand_logs(self.summary_logs)}{n}'
    #     console_text += f'{print_stand_stats(self.summary_stats)}'
    #     return console_text
    #
    # def _compile_pdf_report(self):
    #     pdf = PDF()
    #     pdf.alias_nb_pages()
    #     pdf.add_page()
    #     pdf.compile_stand_report(self)
    #     return pdf

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value.upper()

    @property
    def acres(self):
        return self._acres

    @acres.setter
    def acres(self, value):
        self._acres = float(value)

    @property
    def date_inventory(self):
        return self._date_inventory

    @date_inventory.setter
    def date_inventory(self, value):
        self._date_inventory = self._check_date_arg(value)

    @property
    def plots_df(self):
        return self._plots_df

    @plots_df.setter
    def plots_df(self, value):
        self._cannot_set()

    @property
    def trees_df(self):
        return self._trees_df

    @trees_df.setter
    def trees_df(self, value):
        self._cannot_set()

    @property
    def summary_df(self):
        return self._summary_df

    @summary_df.setter
    def summary_df(self, value):
        self._cannot_set()

    @property
    def dbh_df(self):
        return self._dbh_df

    @dbh_df.setter
    def dbh_df(self, value):
        self._cannot_set()

    @property
    def stats_df(self):
        return self._stats_df

    @stats_df.setter
    def stats_df(self, value):
        self._cannot_set()

    @property
    def logs_df(self):
        return self._logs_df

    @logs_df.setter
    def logs_df(self, value):
        self._cannot_set()

    @property
    def logs_summary_df(self):
        return self._logs_summary_df

    @logs_summary_df.setter
    def logs_summary_df(self, value):
        self._cannot_set()

    @property
    def inventory_df(self):
        return self._inventory_df

    @inventory_df.setter
    def inventory_df(self, value):
        self._cannot_set()

    @property
    def plots(self):
        return self._plots

    @plots.setter
    def plots(self, value):
        self._cannot_set()

    @property
    def plot_count(self):
        return self._plot_count

    @plot_count.setter
    def plot_count(self, value):
        self._cannot_set()

    @property
    def tree_count(self):
        return self._tree_count

    @tree_count.setter
    def tree_count(self, value):
        self._cannot_set()

    @property
    def species(self):
        return self._species

    @species.setter
    def species(self, value):
        self._cannot_set()

    @property
    def species_count(self):
        return self._species_count

    @species_count.setter
    def species_count(self, value):
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
    def total_hgt(self):
        return self._total_hgt

    @total_hgt.setter
    def total_hgt(self, value):
        self._cannot_set()

    @property
    def merch_hgt(self):
        return self._merch_hgt

    @merch_hgt.setter
    def merch_hgt(self, value):
        self._cannot_set()

    @property
    def hdr(self):
        return self._hdr

    @hdr.setter
    def hdr(self, value):
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
    def series(self):
        return self._series

    @series.setter
    def series(self, value):
        self._cannot_set()



if __name__ == '__main__':
    from timberpy.timber.timber import Timber
    from timberpy.timber.plot import Plot

    #file = 'C:/ZBEE490/Dev/other/timberpy/timberpy/del_scratch/xlsx/stand_data_full_with_quick.xlsx'
    file = 'C:/ZBEE490/Dev/other/timberpy/timberpy/del_scratch/fvs/NRF_HQ.xlsx'
    stand = Stand('NRF_HQ', acres=22.4, date_inventory='01/01/00')
    stand.import_sheet(file)
    #stand.plotly_dbh_range('net bf ac')


    # pf1 = 40
    # pf2 = 33.61
    # pf3 = -20
    # pf4 = -30
    # pf5 = 20
    #
    # tree_data = [
    #     # Plot 1
    #     [[Timber(1, pf1, 'DF', 29.5, 119), [[42, 40, 'S2', 5], [83, 40, 'S3', 0], [102, 18, 'S4', 10]]],
    #      [Timber(2, pf1, 'WH', 18.9, 102), [[42, 40, 'S2', 0], [79, 36, 'S4', 5]]],
    #      [Timber(3, pf1, 'WH', 20.2, 101), [[42, 40, 'S2', 5], [83, 40, 'S4', 0]]],
    #      [Timber(4, pf1, 'WH', 19.9, 100), [[42, 40, 'S2', 0], [83, 40, 'S4', 15]]],
    #      [Timber(5, pf1, 'DF', 20.6, 112), [[42, 40, 'S2', 0], [83, 40, 'S3', 5], [100, 16, 'UT', 10]]]],
    #     # Plot 2
    #     [[Timber(1, pf2, 'DF', 25.0, 117), [[42, 40, 'SM', 0], [83, 40, 'S3', 5], [100, 16, 'S4', 0]]],
    #      [Timber(2, pf2, 'DF', 14.3, 105), [[42, 40, 'S3', 0], [79, 36, 'S4', 0]]],
    #      [Timber(3, pf2, 'DF', 20.4, 119), [[42, 40, 'S2', 5], [83, 40, 'S3', 5], [100, 16, 'S4', 5]]],
    #      [Timber(4, pf2, 'DF', 16.0, 108), [[42, 40, 'S3', 5], [83, 40, 'S3', 10]]],
    #      [Timber(5, pf2, 'RC', 20.2, 124), [[42, 40, 'CR', 5], [83, 40, 'CR', 5], [104, 20, 'CR', 5]]],
    #      [Timber(6, pf2, 'RC', 19.5, 116), [[42, 40, 'CR', 10], [83, 40, 'CR', 5], [100, 16, 'CR', 0]]],
    #      [Timber(7, pf2, 'RC', 23.4, 121), [[42, 40, 'CR', 0], [83, 40, 'CR', 0], [106, 22, 'CR', 5]]],
    #      [Timber(8, pf2, 'DF', 17.8, 116), [[42, 40, 'S2', 0], [83, 40, 'S3', 0], [100, 16, 'S4', 10]]],
    #      [Timber(9, pf2, 'DF', 22.3, 125), [[42, 40, 'SM', 0], [83, 40, 'S3', 5], [108, 24, 'S4', 0]]]],
    #     # Plot 3
    #     [[Timber(1, pf3, 'DF', 29.5, 119, auto_cruise=True)],
    #      [Timber(2, pf3, 'SF', 18.9, 102, auto_cruise=True)],
    #      [Timber(3, pf3, 'SF', 20.2, 101, auto_cruise=True)],
    #      [Timber(4, pf3, 'SF', 19.9, 100, auto_cruise=True)],
    #      [Timber(5, pf3, 'DF', 20.6, 112, auto_cruise=True)]],
    #     # Plot 4
    #     [[Timber(1, pf4, 'DF', 25.0, 117, auto_cruise=True)],
    #      [Timber(2, pf4, 'SF', 14.3, 105, auto_cruise=True)],
    #      [Timber(3, pf4, 'SF', 20.4, 119, auto_cruise=True)],
    #      [Timber(4, pf4, 'SF', 16.0, 108, auto_cruise=True)],
    #      [Timber(5, pf4, 'RC', 20.2, 124, auto_cruise=True)]],
    #     # Plot 5
    #     [[Timber(1, pf5, 'rc', 40.5, 175), [[112, 110, 'PL', 0], [143, 40, 'S3', 0]]],
    #      [Timber(2, pf5, 'rc', 33.3, 142), [[72, 70, 'PL', 0], [113, 40, 'S3', 5]]],
    #      [Timber(3, pf5, 'rc', 41.7, 177), [[112, 110, 'PL', 0], [143, 40, 'S3', 0]]],
    #      [Timber(4, pf5, 'rc', 32.3, 140), [[72, 70, 'PL', 0], [113, 40, 'S3', 15]]],
    #      [Timber(5, pf5, 'rc', 39.8, 165), [[112, 110, 'PL', 0], [143, 40, 'S3', 5]]]],
    # ]
    #
    # for plot_num, (plot_trees, plot_factor) in enumerate(zip(tree_data, [pf1, pf2, pf3, pf4, pf5]), 1):
    #     plot = Plot(plot_num, plot_factor)
    #     for data in plot_trees:
    #         if len(data) == 1:
    #             plot.add_tree(data[0])
    #         else:
    #             tree, logs = data
    #             for log in logs:
    #                 tree.add_log(*log)
    #             plot.add_tree(tree)
    #     stand.add_plot(plot)

    num = 150
    hd = 20
    pd.set_option('display.max_columns', None, 'display.width', None, 'display.max_rows', None)

    #stand.console_report()


    stand.plotly_dbh_range('net bf ac')
    #stand.to_excel('test')

    print('stand.series ' + ('#' * num) + '\n')
    print(stand.series.head(len(stand.series)))

    print('\n\n\nstand.plots_df ' + ('#' * num) + '\n')
    print(stand.plots_df.head(len(stand.plots_df)))

    print('\n\n\nstand.trees_df ' + ('#' * num) + '\n')
    print(stand.trees_df.head(len(stand.trees_df)))

    print('\n\n\nstand.summary_df ' + ('#' * num) + '\n')
    print(stand.summary_df.head(len(stand.summary_df)))

    print('\n\n\nstand.dbh_df ' + ('#' * num) + '\n')
    print(stand.dbh_df.head(len(stand.dbh_df)))

    print('\n\n\nstand.stats_df ' + ('#' * num) + '\n')
    print(stand.stats_df.head(len(stand.stats_df)))

    print('\n\n\nstand.logs_df ' + ('#' * num) + '\n')
    print(stand.logs_df.head(len(stand.logs_df)))

    print('\n\n\nstand.logs_summary_df ' + ('#' * num) + '\n')
    print(stand.logs_summary_df.head(len(stand.logs_summary_df)))

    print('\n\n\nstand.inventory_df ' + ('#' * num) + '\n')
    print(stand.inventory_df.head(len(stand.inventory_df)))

    # print(stand.plot_count)
    #
    #
    # # x = stand.trees_df[stand.trees_df['plot number'] == 1]
    # # print(x.head(20))
    # # print('\n\n')
    # # print(x[['tpa', 'ba ac', 'rd ac', 'bf ac', 'cf ac']].describe())



