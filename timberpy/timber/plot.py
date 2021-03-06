import numpy as np
import pandas as pd
import plotly.express as plt
from timberpy.timber._config import (
    ALL_SPECIES_NAMES,
    GRADE_SORT,
    LENGTH_SORT,
    LOG_LENGTHS,
    PLOT_SERIES,
    SPECIES_SORT,
    SUMMARY_SERIES_INIT,
    SUMMARY_SERIES_FINAL,
    TREE_SERIES,

)
from timberpy.timber._exceptions import (
    cannot_set,
    check_stand_arg,
    check_timber_arg,
    InvalidPlotNumberError
)


class Plot(object):
    def __init__(self, expansion_factor: float, stand=None):
        """
        :param expansion_factor: float      -For fixed-area plots use the negative inverse of the plot size (1/30th ac = -30),
                                             for variable-area plots use the Basal Area Factor (BAF) (40 BAF = 40)
        :param stand: Stand                 -The stand (Stand class) that the plot will be added to

        Use the plot.add_tree() method to add trees to the plot's inventory. Trees should be instances of the Timber Class
        Alternatively you can add an instanstiated plot to the Timber __init__ as the plot arg
        """
        self._xfac = float(expansion_factor)

        self._trees_df = None
        self._summary_df = None
        self._dbh_df = None
        self._logs_df = None
        self._logs_summary_df = None

        self._trees = []
        self._tree_count = 0
        self._species = ()
        self._species_count = 0

        self._tpa = 0
        self._ba_ac = 0
        self._qmd = 0
        self._rd_ac = 0

        self._net_bf_ac = 0
        self._net_cf_ac = 0
        self._gross_bf_ac = 0
        self._gross_cf_ac = 0

        self._total_hgt = 0
        self._merch_hgt = 0
        self._hdr = 0
        self._vbar = 0
        self._cbar = 0
        self._series = None

        if stand is None:
            self._stand = None
            self._number = 1
        else:
            check_stand_arg(stand, self.__class__.__name__)
            self._number = len(stand._plots)
            stand.add_plot(self)  # Sets self._stand

    def __getitem__(self, item):
        _item = f'_{item}'
        if item in self.__dict__:
            return self.__dict__[item]
        elif _item in self.__dict__:
            return self.__dict__[_item]
        raise KeyError(f'{self.__class__.__name__} has no attribute {item}')

    def __repr__(self):
        first = f'<Plot {self._number} | {self._tree_count} trees'
        if self._stand is not None:
            return f'{first} (Stand {self._stand._name})>'
        else:
            return f'{first} (Transient)>'

    def add_tree(self, timber):
        """
        The timber argument needs to be an instance of the Timber Class
        The Timber Class is added to the plot's trees list and plot calculations and statistics are re-run
        """
        timber = check_timber_arg(timber, self.__class__.__name__)
        timber._plot = self
        self._trees.append(timber)
        timber._number = len(self._trees)
        timber._series['number'] = timber._number
        self._recalc_metrics()

    def add_trees(self, timbers: list):
        """
        Add a list of trees at one time, items within list should be Timber class
        :param timbers:                   -A list containing Timber class objects
        :return: None
        """
        for i, timber in enumerate(timbers, 1):
            timber = check_timber_arg(timber, self.__class__.__name__)
            timber._plot = self
            self._trees.append(timber)
            timber._number = i
            timber._series['number'] = i
        self._recalc_metrics()

    def remove_tree(self, tree_number):
        """
        Removes a tree from the tree list and recalculates metrics
        :param tree_number:             -The number of the tree (Timber.number) to be removed
        :return: None
        """
        self._trees.pop(tree_number - 1)
        for i, tree in enumerate(self._trees, 1):
            tree._number = i
            tree._series['number'] = i
        self._recalc_metrics()

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
            title = f'<b>Plot {self._number}: {column_name.upper()} by Species</b>'
            xaxis = '<b>Species</b>'
        else:
            df = self._dbh_df[column_name][:-1].copy()
            df.index = df.index.map(lambda x: str(x.left) if x != 'TOTALS' else x)
            title = f'<b>Plot {self._number}: {column_name.upper()} by Diameter Distribution</b>'
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

    def _get_summaries_df(self, groupby, start_summaries=0):
        """
        Creates a summary DataFrame depending on the groupby argument
        The initial data are the data that need to be summed, the final data adds the data that needs to be averaged or calculated.
        :param groupby:             -A column name or pandas.cut of a range of values
        :param start_summaries:     -The index to start the SUMMARY_SERIES_INIT list for column names
        :return: pandas DataFrame
        """
        df = self._trees_df[SUMMARY_SERIES_INIT[start_summaries:]].groupby(by=groupby).sum()
        df.loc['TOTALS'] = df.sum()

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

    def _recalc_metrics(self):
        self._set_dataframes()
        self._set_attrs()
        self._set_series()

    def _set_dataframes(self):
        """
        Setting the pandas DataFrames for the plot
        """
        self._set_tree_df()
        self._set_summary_df()
        self._set_dbh_df()
        self._set_logs_df()
        self._set_logs_summary_df()

    def _set_tree_df(self):
        """
        This DataFrame is a collection of the tree's pandas Series within the plot, transposed
        so that the Series' indexes become the columns
        """
        data = {tree.series['number']: tree.series for tree in self._trees}
        self._trees_df = pd.DataFrame(data, index=TREE_SERIES[1:]).transpose()

    def _set_summary_df(self):
        """
        This DataFrame is a summary of the tree data within the plot. It is grouped by species and adds a totals row.
        """
        self._summary_df = self._get_summaries_df('species')

    def _set_dbh_df(self):
        """
        This DataFrame is a summary of the tree data within the plot. It is grouped by DBH ranges, every 2 inches,
        and adds a totals row.
        """
        min_dbh = self._trees_df['dbh'].min().__floor__() * 2 // 2
        max_dbh = (self._trees_df['dbh'].max().__ceil__() * 2 // 2) + 2
        groupby = pd.cut(self._trees_df['dbh'], np.arange(min_dbh, max_dbh, 2))

        self._dbh_df = self._get_summaries_df(groupby, start_summaries=1)

    def _set_logs_df(self):
        """
        This DataFrame is a collection of each tree's log's pandas Series, adding tree number and log number
        to the log Series and then transposing so that the log Series' indexes become the columns
        """
        data = {}
        for tree in self._trees:
            for lnum, log in tree.logs.items():
                log_series = log.series
                log_series['tree number'] = tree.number
                log_series['log number'] = lnum
                data.update({f'{tree.number}_{lnum}': log.series})
        self._logs_df = pd.DataFrame(data).transpose()

    def _set_logs_summary_df(self):
        """
        This DataFrame is a summary of the log merchandizing data. The final Dataframe is grouped
        by species and log grade as the indexes. The log length ranges are the columns. The table data consists of
        logs per acre (lpa), net board feet per acre, and net cubic feet per acre. Totals for grades and length ranges are calculated
        as well.
        """
        t = 'TOTALS'
        length_ranges = list(LOG_LENGTHS) + [t]
        table_values = ['lpa', 'bf ac', 'cf ac']

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
                    sheet[key][(lrng, val_type)] += val
                    sheet[key][(t, val_type)] += val
        data.update(totals)

        # Sorting the data by length range, species, and grade
        data = {key: {sub: data[key][sub]
                      for sub in sorted(data[key], key=lambda a: LENGTH_SORT[a[0]])}
                for key in sorted(data, key=lambda z: int(f'{SPECIES_SORT[z[0]]}{GRADE_SORT[z[1]]}'))}

        self._logs_summary_df = pd.DataFrame.from_dict(data, orient='index')
        self._logs_summary_df.columns = pd.MultiIndex.from_tuples([(c[0], c[1]) for c in self._logs_summary_df.columns])

    def _set_attrs(self):
        """
        Setting the plot's attributes to be called by the plot's properties
        """
        self._tree_count = len(self._trees_df)
        self._species = tuple(sorted(set(self._trees_df['species'].to_list()), key=lambda x: SPECIES_SORT[x]))
        self._species_count = len(self._species)

        for attr in PLOT_SERIES[4:]:
            setattr(self, f"_{attr.replace(' ', '_')}", self._summary_df.loc['TOTALS', attr])

    def _set_series(self):
        self._series = pd.Series([self[f"_{i.replace(' ', '_')}"] for i in PLOT_SERIES], index=PLOT_SERIES)

    """
    SET INVENTORY DB
    """

    @property
    def number(self):
        return self._number

    @number.setter
    def number(self, value):
        value = int(value)
        if value < 1:
            raise InvalidPlotNumberError(value)
        else:
            if self._stand is None:
                self._number = int(value)
            else:
                if value > len(self._stand._plots):
                    value = len(self._stand._plots)
                self._stand._plots.insert(value - 1, self._stand._plots.pop(self._number - 1))
                self._number = value

    @property
    def stand(self):
        return self._stand

    @stand.setter
    def stand(self, value):
        check_stand_arg(value, self.__class__.__name__)
        if self._stand is None:
            value.add_plot(self)
        else:
            self._stand.remove_plot(self._number)
            value.add_plot(self)

    @property
    def xfac(self):
        return self._xfac

    @xfac.setter
    def xfac(self, value):
        self._xfac = float(value)
        for tree in self._trees:
            tree.xfac = self._xfac
        self._recalc_metrics()

    @property
    def trees_df(self):
        return self._trees_df

    @trees_df.setter
    def trees_df(self, value):
        cannot_set(self.__class__.__name__, 'trees_df')

    @property
    def summary_df(self):
        return self._summary_df

    @summary_df.setter
    def summary_df(self, value):
        cannot_set(self.__class__.__name__, 'summary_df')

    @property
    def dbh_df(self):
        return self._dbh_df

    @dbh_df.setter
    def dbh_df(self, value):
        cannot_set(self.__class__.__name__, 'dbh_df')

    @property
    def logs_df(self):
        return self._logs_df

    @logs_df.setter
    def logs_df(self, value):
        cannot_set(self.__class__.__name__, 'logs_df')

    @property
    def logs_summary_df(self):
        return self._logs_summary_df

    @logs_summary_df.setter
    def logs_summary_df(self, value):
        cannot_set(self.__class__.__name__, 'logs_summary_df')

    @property
    def trees(self):
        return self._trees

    @trees.setter
    def trees(self, value):
        cannot_set(self.__class__.__name__, 'trees')

    @property
    def tree_count(self):
        return self._tree_count

    @tree_count.setter
    def tree_count(self, value):
        cannot_set(self.__class__.__name__, 'tree_count')

    @property
    def species(self):
        return self._species

    @species.setter
    def species(self, value):
        cannot_set(self.__class__.__name__, 'species')

    @property
    def species_count(self):
        return self._species_count

    @species_count.setter
    def species_count(self, value):
        cannot_set(self.__class__.__name__, 'species_count')

    @property
    def tpa(self):
        return self._tpa

    @tpa.setter
    def tpa(self, value):
        cannot_set(self.__class__.__name__, 'tpa')

    @property
    def ba_ac(self):
        return self._ba_ac

    @ba_ac.setter
    def ba_ac(self, value):
        cannot_set(self.__class__.__name__, 'ba_ac')

    @property
    def rd_ac(self):
        return self._rd_ac

    @rd_ac.setter
    def rd_ac(self, value):
        cannot_set(self.__class__.__name__, 'rd_ac')

    @property
    def gross_bf_ac(self):
        return self._gross_bf_ac

    @gross_bf_ac.setter
    def gross_bf_ac(self, value):
        cannot_set(self.__class__.__name__, 'gross_bf_ac')

    @property
    def gross_cf_ac(self):
        return self._gross_cf_ac

    @gross_cf_ac.setter
    def gross_cf_ac(self, value):
        cannot_set(self.__class__.__name__, 'gross_cf_ac')

    @property
    def net_bf_ac(self):
        return self._net_bf_ac

    @net_bf_ac.setter
    def net_bf_ac(self, value):
        cannot_set(self.__class__.__name__, 'net_bf_ac')

    @property
    def net_cf_ac(self):
        return self._net_cf_ac

    @net_cf_ac.setter
    def net_cf_ac(self, value):
        cannot_set(self.__class__.__name__, 'net_cf_ac')

    @property
    def total_hgt(self):
        return self._total_hgt

    @total_hgt.setter
    def total_hgt(self, value):
        cannot_set(self.__class__.__name__, 'total_hgt')

    @property
    def merch_hgt(self):
        return self._merch_hgt

    @merch_hgt.setter
    def merch_hgt(self, value):
        cannot_set(self.__class__.__name__, 'merch_hgt')

    @property
    def hdr(self):
        return self._hdr

    @hdr.setter
    def hdr(self, value):
        cannot_set(self.__class__.__name__, 'hdr')

    @property
    def vbar(self):
        return self._vbar

    @vbar.setter
    def vbar(self, value):
        cannot_set(self.__class__.__name__, 'vbar')

    @property
    def cbar(self):
        return self._cbar

    @cbar.setter
    def cbar(self, value):
        cannot_set(self.__class__.__name__, 'cbar')

    @property
    def series(self):
        return self._series

    @series.setter
    def series(self, value):
        cannot_set(self.__class__.__name__, 'series')


if __name__ == '__main__':
    from timberpy.timber.timber import Timber
    plot = Plot(33.61)
    plot_factor = plot.xfac
    tree_data = [
        [Timber(plot_factor, 'DF', 25.0, 117), [[42, 40, 'SM', 0], [83, 40, 'S3', 5], [100, 16, 'S4', 0]]],
        [Timber(plot_factor, 'DF', 14.3, 105), [[42, 40, 'S3', 0], [79, 36, 'S4', 0]]],
        [Timber(plot_factor, 'DF', 20.4, 119), [[42, 40, 'S2', 5], [83, 40, 'S3', 5], [100, 16, 'S4', 5]]],
        [Timber(plot_factor, 'DF', 16.0, 108), [[42, 40, 'S3', 5], [83, 40, 'S3', 10]]],
        [Timber(plot_factor, 'RC', 20.2, 124), [[42, 40, 'CR', 5], [83, 40, 'CR', 5], [104, 20, 'CR', 5]]],
        [Timber(plot_factor, 'RC', 19.5, 116), [[42, 40, 'CR', 10], [83, 40, 'CR', 5], [100, 16, 'CR', 0]]],
        [Timber(plot_factor, 'RC', 23.4, 121), [[42, 40, 'CR', 0], [83, 40, 'CR', 0], [106, 22, 'CR', 5]]],
        [Timber(plot_factor, 'DF', 17.8, 116), [[42, 40, 'S2', 0], [83, 40, 'S3', 0], [100, 16, 'S4', 10]]],
        [Timber(plot_factor, 'DF', 22.3, 125), [[42, 40, 'SM', 0], [83, 40, 'S3', 5], [108, 24, 'S4', 0]]]
    ]

    for timber, logs in tree_data:
        for log in logs:
            timber.add_log(*log)
    plot.add_trees([i[0] for i in tree_data])
    print(plot)
    print(plot.trees[4])

    # for timber in plot.trees:
    #     print(timber.number)
    #     print(timber.species)
    #
    # pd.set_option('display.max_columns', None, 'display.width', None)
    #
    # num = 150
    # hd = 20
    #
    # plot.plotly_dbh_range('net bf ac')
    #
    # print('plot.series ' + ('#' * num) + '\n')
    # print(plot.series.head(len(plot.series)))
    #
    # print('\n\n\nplot.trees_df ' + ('#' * num) + '\n')
    # print(plot.trees_df.head(len(plot.trees_df)))
    #
    # print('\n\n\nplot.summary_df ' + ('#' * num) + '\n')
    # print(plot.summary_df.head(len(plot.summary_df)))
    #
    # print('\n\n\nplot.dbh_df ' + ('#' * num) + '\n')
    # print(plot.dbh_df.head(len(plot.dbh_df)))
    #
    # print('\n\n\nplot.logs_df ' + ('#' * num) + '\n')
    # print(plot.logs_df.head(len(plot.logs_df)))
    #
    # print('\n\n\nplot.logs_summary_df ' + ('#' * num) + '\n')
    # print(plot.logs_summary_df.head(len(plot.logs_summary_df)))




