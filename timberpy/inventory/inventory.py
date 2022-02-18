import os

from copy import deepcopy
from csv import reader, excel
from openpyxl import load_workbook
from xlrd import open_workbook

from timberpy.inventory.inventory_config import *
from timberpy.inventory.inventory_exceptions import InventoryImportError


class Inventory:
    possible_col_separators = [' ', '_', '-', '.', '']
    tree_attrs_is_error = {
        0: lambda value: Inventory._error_float(value, non_negative=False),
        1: lambda value: Inventory._error_int(value),
        2: lambda value: Inventory._error_string(value),
        3: lambda value: Inventory._error_float(value),
        4: lambda value: Inventory._error_float(value, required=False),
    }
    log_attrs_is_error = {
        0: lambda value: Inventory._error_int(value),
        1: lambda value: Inventory._error_int(value),
        2: lambda value: Inventory._error_string(value, required=False),
        3: lambda value: Inventory._error_int(value, required=False)

    }

    def __init__(self, filename):
        self.readers = {
            '.xlsx': self.read_xlsx,
            '.xls': self.read_xls,
            '.csv': self.read_csv
        }

        if not os.path.isfile(filename):
            raise InventoryImportError('not found', filename)

        elif not any([filename.endswith(i) for i in self.readers.keys()]):
            raise InventoryImportError('not ext', filename)

        self.required = {}

        self.filename = filename
        self.ext = f'.{self.filename.split(".")[-1]}'

        self.data_read = self.readers[self.ext]()

        # for stand in self.data_read:
        #     print(f'{stand=}')
        #     print('hdr=', self.data_read[stand]['hdr'])
        #     for plot in self.data_read[stand]['plots']:
        #         print(f'\t{plot=}')
        #         print(f'\tplot_factor={self.data_read[stand]["plots"][plot]["plot_factor"]}')
        #         for row in self.data_read[stand]["plots"][plot]['trees']:
        #             print(f'\t\t{row}')
        #     print()

    def read_xlsx(self):
        wb = load_workbook(self.filename, data_only=True)
        full_cruise = True
        for sheet in wb.sheetnames:
            self.required = {col_name: REQUIRED_COLS[col_name] for col_name in REQUIRED_COLS}
            ws = wb[sheet]
            headers = [i.upper() if i is not None else i for i in list(next(ws.values))]
            has_required = self._check_required_cols(headers, idx_offset=1)

            if not has_required:
                continue
            else:
                other_cols = self._get_log_cols(headers, idx_offset=1)
                if not other_cols:
                    full_cruise = False
                    other_cols = self._get_quick_cols(headers, idx_offset=1)
                self.required.update(**other_cols)

                master = {}
                stand = None
                plot_factor = None
                plot = None

                for i, row in enumerate(ws.iter_rows(), 2):
                    temp = []
                    all_logs = []
                    logs = []

                    for col_name in self.required:
                        idx = self.required[col_name]['idx']

                        if col_name == 'Stand':
                            stand = ws.cell(i, idx).value
                            if stand not in master:
                                master[stand] = {
                                    'hdr': None,
                                    'plots': {}
                                }

                        elif col_name == 'Plot Factor':
                            plot_factor = ws.cell(i, idx).value
                            temp.append(plot_factor)

                        elif col_name == 'Plot':
                            plot = ws.cell(i, idx).value
                            if plot not in master[stand]['plots']:
                                master[stand]['plots'][plot] = {
                                    'plot_factor': plot_factor,
                                    'trees': []
                                }

                        else:
                            if col_name.startswith('Log'):
                                append = logs
                            else:
                                append = temp

                            if idx is None:
                                append.append(self.required[col_name]['default'])
                            else:
                                cell = ws.cell(i, idx).value
                                if cell not in ['', ' ', None]:
                                    append.append(cell)
                                else:
                                    append.append(self.required[col_name]['default'])

                            if col_name.endswith('Defect'):
                                if any(logs):
                                    all_logs.append(logs)
                                    logs = []

                    if all_logs:
                        log_error, all_logs = self._check_logs(all_logs)
                        if log_error:
                            raise InventoryImportError('not logs', self.filename)
                        temp.append(all_logs)
                        temp.append(False)

                    elif not all_logs and full_cruise:
                        for col_name in QUICK_COLS:
                            temp.append(QUICK_COLS[col_name]['default'])
                        temp.append(True)

                    else:
                        temp.append(True)

                    master[stand]['plots'][plot]['trees'].append(temp)

                for delete in ['', ' ', None]:
                    if delete in master:
                        del master[delete]

                self._check_datatypes(master)
                return master

        raise InventoryImportError('not req', self.filename)

    def read_xls(self):
        wb = open_workbook(self.filename)
        full_cruise = True
        for sheet in wb.sheet_names():
            self.required = {col_name: REQUIRED_COLS[col_name] for col_name in REQUIRED_COLS}
            ws = wb.sheet_by_name(sheet)
            headers = [i.value.upper() if i is not None else i for i in ws.row(0)]
            has_required = self._check_required_cols(headers)

            if not has_required:
                continue
            else:
                other_cols = self._get_log_cols(headers)
                if not other_cols:
                    full_cruise = False
                    other_cols = self._get_quick_cols(headers)
                self.required.update(**other_cols)

                master = {}
                stand = None
                plot_factor = None
                plot = None

                for i in range(1, ws.nrows):
                    row = ws.row(i)
                    temp = []
                    all_logs = []
                    logs = []

                    for col_name in self.required:
                        idx = self.required[col_name]['idx']

                        if col_name == 'Stand':
                            stand = row[idx].value
                            if stand not in master:
                                master[stand] = {
                                    'hdr': None,
                                    'plots': {}
                                }

                        elif col_name == 'Plot Factor':
                            plot_factor = row[idx].value
                            temp.append(plot_factor)

                        elif col_name == 'Plot':
                            plot = row[idx].value
                            if plot not in master[stand]['plots']:
                                master[stand]['plots'][plot] = {
                                    'plot_factor': plot_factor,
                                    'trees': []
                                }

                        else:
                            if col_name.startswith('Log'):
                                append = logs
                            else:
                                append = temp

                            if idx is None:
                                append.append(self.required[col_name]['default'])
                            else:
                                cell = row[idx].value
                                if cell not in ['', ' ', None]:
                                    append.append(cell)
                                else:
                                    append.append(self.required[col_name]['default'])

                            if col_name.endswith('Defect'):
                                if any(logs):
                                    all_logs.append(logs)
                                    logs = []

                    if all_logs:
                        log_error, all_logs = self._check_logs(all_logs)
                        if log_error:
                            raise InventoryImportError('not logs', self.filename)
                        temp.append(all_logs)
                        temp.append(False)

                    elif not all_logs and full_cruise:
                        for col_name in QUICK_COLS:
                            temp.append(QUICK_COLS[col_name]['default'])
                        temp.append(True)

                    else:
                        temp.append(True)

                    master[stand]['plots'][plot]['trees'].append(temp)

                for delete in ['', ' ', None]:
                    if delete in master:
                        del master[delete]

                self._check_datatypes(master)
                return master

        raise InventoryImportError('not req', self.filename)

    def read_csv(self):
        with open(self.filename, 'r') as csv_file:
            csv_read = reader(csv_file, dialect=excel)
            full_cruise = True

            self.required = {col_name: REQUIRED_COLS[col_name] for col_name in REQUIRED_COLS}
            headers = [i.upper() for i in next(csv_read)]
            has_required = self._check_required_cols(headers)

            if not has_required:
                raise InventoryImportError('not req', self.filename)
            else:
                other_cols = self._get_log_cols(headers)
                if not other_cols:
                    full_cruise = False
                    other_cols = self._get_quick_cols(headers)

                self.required.update(**other_cols)

                master = {}
                stand = None
                plot_factor = None
                plot = None

                for i, row in enumerate(csv_read):
                    temp = []
                    all_logs = []
                    logs = []

                    for col_name in self.required:
                        idx = self.required[col_name]['idx']

                        if col_name == 'Stand':
                            stand = row[idx]
                            if stand not in master:
                                master[stand] = {
                                    'hdr': None,
                                    'plots': {}
                                }

                        elif col_name == 'Plot Factor':
                            plot_factor = row[idx]
                            temp.append(plot_factor)

                        elif col_name == 'Plot':
                            plot = row[idx]
                            if plot not in master[stand]['plots']:
                                master[stand]['plots'][plot] = {
                                    'plot_factor': plot_factor,
                                    'trees': []
                                }

                        else:
                            if col_name.startswith('Log'):
                                append = logs
                            else:
                                append = temp

                            if idx is None:
                                append.append(self.required[col_name]['default'])
                            else:
                                cell = row[idx]
                                if cell not in ['', ' ', None]:
                                    append.append(cell)
                                else:
                                    append.append(self.required[col_name]['default'])

                            if col_name.endswith('Defect'):
                                if any(logs):
                                    all_logs.append(logs)
                                    logs = []

                    if all_logs:
                        log_error, all_logs = self._check_logs(all_logs)
                        if log_error:
                            raise InventoryImportError('not logs', self.filename)
                        temp.append(all_logs)
                        temp.append(False)

                    elif not all_logs and full_cruise:
                        for col_name in QUICK_COLS:
                            temp.append(QUICK_COLS[col_name]['default'])
                        temp.append(True)

                    else:
                        temp.append(True)

                    master[stand]['plots'][plot]['trees'].append(temp)

                for delete in ['', ' ', None]:
                    if delete in master:
                        del master[delete]

                self._check_datatypes(master)
                return master

    def _check_datatypes(self, import_dict):
        for stand in import_dict:
            heights = []
            dbhs = []
            for plot in import_dict[stand]['plots']:
                if self._error_int(plot):
                    raise InventoryImportError('not data', self.filename)

                if self._error_float(import_dict[stand]['plots'][plot]['plot_factor'], non_negative=False):
                    raise InventoryImportError('not data', self.filename)

                for tree in import_dict[stand]['plots'][plot]['trees']:
                    for idx, err_func in self.tree_attrs_is_error.items():
                        if err_func(tree[idx]):
                            raise InventoryImportError('not data', self.filename)
                        if idx == 3:
                            if tree[4] not in ['', ' ', None]:
                                heights.append(float(tree[4]))
                                dbhs.append(float(tree[idx]))
                    if not tree[-1]:
                        for log in tree[-2]:
                            for idx, err_func in self.log_attrs_is_error.items():
                                if err_func(log[idx]):
                                    raise InventoryImportError('not data', self.filename)
            if not heights:
                raise InventoryImportError('not hgt', self.filename, stand=stand)
            else:
                hdrs = [height / (dbh / 12) for height, dbh in zip(heights, dbhs)]
                import_dict[stand]['hdr'] = sum(hdrs) / len(hdrs)

    def _check_required_cols(self, headers, idx_offset=0):
        has_required = True
        for col_name in self.required:
            pos_cols = self._possible_col_names(self.required[col_name]['iters'])
            full_cols = headers + pos_cols
            filtered = list(filter(lambda x: True if full_cols.count(x) == 2 and x in pos_cols else False, full_cols))
            if filtered:
                self.required[col_name]['idx'] = headers.index(filtered[0]) + idx_offset
            else:
                has_required = False
                break
        return has_required

    def _get_log_cols(self, headers, idx_offset=0):
        log_cols = {}

        # Next checking for log cols for full cruise, checks out to 21 logs but will break out if blanks is all True
        for log_num in range(1, 21):
            temp_cols = {}
            blanks = [False for _ in range(len(LOG_COLS))]
            temp_cols.update({col_name.format(log_num): deepcopy(LOG_COLS[col_name]) for col_name in LOG_COLS})
            for i, col_name in enumerate(temp_cols):
                pos_cols = self._possible_col_names(temp_cols[col_name]['iters'], fill=log_num)
                full_cols = headers + pos_cols
                filtered = list(filter(lambda x: True if full_cols.count(x) == 2 and x in pos_cols else False, full_cols))
                if filtered:
                    temp_cols[col_name]['idx'] = headers.index(filtered[0]) + idx_offset
                else:
                    blanks[i] = True
            if all(blanks):
                break
            else:
                log_cols.update(**temp_cols)
        return log_cols

    def _get_quick_cols(self, headers, idx_offset=0):
        quick_cols = {col_name: QUICK_COLS[col_name] for col_name in QUICK_COLS}
        for col_name in quick_cols:
            pos_cols = self._possible_col_names(quick_cols[col_name]['iters'])
            full_cols = headers + pos_cols
            filtered = list(filter(lambda x: True if full_cols.count(x) == 2 and x in pos_cols else False, full_cols))
            if filtered:
                quick_cols[col_name]['idx'] = headers.index(filtered[0]) + idx_offset
        return quick_cols

    def _possible_col_names(self, iterators, fill=None):
        master = []
        if len(iterators) == 1:
            for sep in self.possible_col_separators:
                master += [i.replace(' ', sep) for i in iterators[0]]

        elif len(iterators) == 2:
            for sep in self.possible_col_separators:
                for front in iterators[0]:
                    use_front = f'{front}' if front != '' else ''
                    for back in iterators[1]:
                        use_back = f'{sep}{back}' if back != '' else ''
                        if fill is not None:
                            master.append(f'{fill}{sep}{use_front}{use_back}')
                            master.append(f'{use_front}{sep}{fill}{use_back}')
                            master.append(f'{use_front}{use_back}{sep}{fill}')
                        else:
                            master.append(f'{use_front}{use_back}')
        else:
            for sep in self.possible_col_separators:
                for front in iterators[0]:
                    use_front = f'{front}' if front != '' else ''
                    for mid in iterators[1]:
                        use_mid = f'{sep}{mid}' if mid != '' else ''
                        for back in iterators[2]:
                            use_back = f'{sep}{back}' if back != '' else ''
                            if fill is not None:
                                master.append(f'{fill}{sep}{use_front}{use_mid}{use_back}')
                                master.append(f'{use_front}{sep}{fill}{use_mid}{use_back}')
                                master.append(f'{use_front}{use_mid}{sep}{fill}{use_back}')
                                master.append(f'{use_front}{use_mid}{use_back}{sep}{fill}')
                            else:
                                master.append(f'{use_front}{use_mid}{use_back}')
        master = list(set(master))
        return master

    @staticmethod
    def _check_logs(all_logs):
        log_error = False
        stem_height = 1
        for logs in all_logs:
            if logs[0] and logs[1]:
                continue
            elif not logs[0] and not logs[1]:
                log_error = True
            else:
                if not logs[0]:
                    stem_height += logs[1] + 1
                    logs[0] = stem_height
                else:
                    logs[1] = logs[0] - stem_height - 1
                    stem_height = logs[0]
        return log_error, all_logs

    @staticmethod
    def _error_float(value, required=True, non_negative=True):
        if not required and value in ['', ' ', None]:
            return False
        try:
            x = float(value)
            if non_negative and x < 0:
                return True
            else:
                return False
        except ValueError:
            return True

    @staticmethod
    def _error_int(value, required=True):
        if not required and value in ['', ' ', None]:
            return False
        else:
            try:
                x = int(value)
                if x < 0:
                    return True
                else:
                    return False
            except ValueError:
                return True

    @staticmethod
    def _error_string(value, required=True):
        if required and value in ['', ' ', None]:
            return True
        else:
            return False

    @staticmethod
    def _del_print_cols(cols):
        for col_name in cols:
            print(col_name)
            for sub in cols[col_name]:
                print(f'{sub}: {cols[col_name][sub]}')
            print()








if __name__ == '__main__':
    file = 'C:/ZBEE490/Dev/other/timberpy/timberpy/del_scratch/csv/csv_stand_data_full_both.csv'
    #file = 'C:/ZBEE490/Dev/other/timberpy/timberpy/del_scratch/xlsx/stand_data_full_with_quick.xlsx'
    #file = 'C:/ZBEE490/Dev/other/timberpy/timberpy/del_scratch/xlsx/normal_to_try_multistand_no_hgt.xlsx'
    #file = 'C:/ZBEE490/Dev/other/timberpy/timberpy/del_scratch/xls/stand_data_full_with_quick.xls'

    inv = Inventory(file)






