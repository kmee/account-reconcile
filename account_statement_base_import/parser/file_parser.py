# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright Camptocamp SA
#    Author Nicolas Bessi, Joel Grand-Guillaume
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.tools.translate import _
import tempfile
import datetime
from parser import BankStatementImportParser
from parser import UnicodeDictReader
try:
    import xlrd
except:
    raise Exception(_('Please install python lib xlrd'))

class FileParser(BankStatementImportParser):
    """
    Generic abstract class for defining parser for .csv or .xls file format.
    """
    
    def __init__(self, parse_name, keys_to_validate=[], ftype='csv', convertion_dict=None, header=None, *args, **kwargs):
        """
            :param char: parse_name : The name of the parser
            :param list: keys_to_validate : contain the key that need to be present in the file
            :param char ftype: extension of the file (could be csv or xls)
            :param: convertion_dict : keys and type to convert of every column in the file like 
                {
                    'ref': unicode,
                    'label': unicode,
                    'date': datetime.datetime,
                    'amount': float,
                    'commission_amount': float
                }
            :param list: header : specify header fields if the csv file has no header
            """
        
        super(FileParser, self).__init__(parse_name, *args, **kwargs)
        if ftype in ('csv', 'xls'):
            self.ftype = ftype
        else:
            raise Exception(_('Invalide file type %s. please use csv or xls') % (ftype))
        self.keys_to_validate = keys_to_validate
        self.convertion_dict = convertion_dict
        self.fieldnames = header

    def _custom_format(self, *args, **kwargs):
        """
        No other work on data are needed in this parser.
        """
        return True

    def _pre(self, *args, **kwargs):
        """
        No pre-treatment needed for this parser.
        """
        return True

    def _parse(self, *args, **kwargs):
        """
        Launch the parsing through .csv or .xls depending on the
        given ftype
        """
        
        res = None
        if self.ftype == 'csv':
            res = self._parse_csv()
        else:
            res = self._parse_xls()
        self.result_row_list = res
        return True

    def _validate(self, *args, **kwargs):
        """
        We check that all the key of the given file (means header) are present
        in the validation key provided. Otherwise, we raise an Exception.
        We skip the validation step if the file header is provided separately
        (in the field: fieldnames).
        """
        if self.fieldnames is None:
            parsed_cols = self.result_row_list[0].keys()
            for col in self.keys_to_validate:
                if col not in parsed_cols:
                    raise Exception(_('Column %s not present in file') % (col))
        return True

    def _post(self, *args, **kwargs):
        """
        Cast row type depending on the file format .csv or .xls after parsing the file.
        """
        self.result_row_list = self._cast_rows(*args, **kwargs)
        return True


    def _parse_csv(self, delimiter=';'):
        """
        :return: list of dict from csv file (line/rows)
        """
        csv_file = tempfile.NamedTemporaryFile()
        csv_file.write(self.filebuffer)
        csv_file.flush()
        with open(csv_file.name, 'rU') as fobj: 
            reader = UnicodeDictReader(fobj, delimiter=delimiter, fieldnames=self.fieldnames)
            return list(reader)

    def _parse_xls(self):
        """
        :return: dict of dict from xls file (line/rows)
        """
        wb_file = tempfile.NamedTemporaryFile()
        wb_file.write(self.filebuffer)
        # We ensure that cursor is at beginig of file
        wb_file.seek(0)
        wb = xlrd.open_workbook(wb_file.name)
        sheet = wb.sheet_by_index(0)
        header = sheet.row_values(0)
        res = []
        for rownum in range(1, sheet.nrows):
            res.append(dict(zip(header, sheet.row_values(rownum))))
        try:
            wb_file.close()
        except Exception, e:
            pass #file is allready closed
        return res

    def _from_csv(self, result_set, conversion_rules):
        """
        Handle the converstion from the dict and handle date format from
        an .csv file.
        """
        for line in result_set:
            for rule in conversion_rules:
                if conversion_rules[rule] == datetime.datetime:
                    date_string = line[rule].split(' ')[0]
                    line[rule] = datetime.datetime.strptime(date_string,
                                                            '%Y-%m-%d')
                else:
                    line[rule] = conversion_rules[rule](line[rule])
        return result_set

    def _from_xls(self, result_set, conversion_rules):
        """
        Handle the converstion from the dict and handle date format from
        an .xls file.
        """
        for line in result_set:
            for rule in conversion_rules:
                if conversion_rules[rule] == datetime.datetime:
                    t_tuple = xlrd.xldate_as_tuple(line[rule], 1)
                    line[rule] = datetime.datetime(*t_tuple)
                else:
                    line[rule] = conversion_rules[rule](line[rule])
        return result_set

    def _cast_rows(self, *args, **kwargs):
        """
        Convert the self.result_row_list using the self.convertion_dict providen.
        We call here _from_xls or _from_csv depending on the self.ftype variable.
        """
        func =  getattr(self, '_from_%s'%(self.ftype))
        res = func(self.result_row_list, self.convertion_dict)
        return res
