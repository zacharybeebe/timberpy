# Exception messages
FILE_NOT_FOUND = """
[{}] could not be located, check the file path and try again.
"""

INCORRECT_EXTENSION = """
[{}] has the incorrect file type. Acceptable file types are...

.xlsx
.xls
.csv
"""

NOT_ALL_REQUIRED_COLS = """
Could not find required columns in [{}]
TimberPy tries to find a variety of different column names when importing a sheet,
but it was unable to locate all of the required columns from the sheet.
The required columns for import are...

Stand ID
Plot Factor
Plot Number
Tree Number
Species
DBH

Total Height is not required for every tree record, 
but there needs to be at least one total height for each stand.
"""

NOT_ONE_HEIGHT = """
Total Height Error in sheet [{}]
Could not find a least one total height for stand [{}].
There needs to be at least one Total Height for each stand.
"""

NOT_LOGS = """
[{}] did not contain the correct log data.
The logs found within the sheet did not have all of the required data for each log.
The required data needed for each log are...

Log Stem Height 
OR
Log Length
"""

NOT_DATA = """
Incorrect data types found in [{}]
Please check your data and retry.
The correct column datatypes are...
REQUIRED-----------------------------------------
Stand:                  string
Plot Factor:            float (can be negative)
Plot Number:            integer
Tree Number:            integer
Species:                string
DBH:                    float

OPTIONAL----------------------------------------
Total Height:           float
Preferred Log Length:   integer
Minimum Log Length:     integer
Utility Log DIB:        integer
Log Stem Height:        integer
Log Length:             integer
Log Grade:              string
Log Defect:             integer
"""


class InventoryImportError(Exception):
    messages = {
        'not found': FILE_NOT_FOUND,
        'not ext': INCORRECT_EXTENSION,
        'not req': NOT_ALL_REQUIRED_COLS,
        'not hgt': NOT_ONE_HEIGHT,
        'not logs': NOT_LOGS,
        'not data': NOT_DATA

    }

    def __init__(self, err_string, filename, stand=None):
        if stand is None:
            super(InventoryImportError, self).__init__(self.messages[err_string].format(filename))
        else:
            super(InventoryImportError, self).__init__(self.messages[err_string].format(filename, stand))

