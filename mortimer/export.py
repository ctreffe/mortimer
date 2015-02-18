import json
import csv
import re
import io
from tempfile import TemporaryFile

def to_json(cursor):
    sIO = io.BytesIO()
    l = list(cursor)
    json.dump(l, sIO)
    sIO.seek(0)
    return sIO

def to_csv(cursor, none_value=None, remove_linebreaks=False, dialect='excel', **writerparams):
    rows = cursor_to_rows(cursor, none_value)
    if remove_linebreaks:
        for i in range(1,len(rows)):
            for j in range(len(rows[i])):
                if isinstance(rows[i][j], str) or isinstance(rows[i][j], unicode):
                    rows[i][j].replace('\n', '')
    csvfile = io.BytesIO()
    writer = csv.writer(csvfile, dialect=dialect, **writerparams)
    for row in rows:
        writer.writerow([unicode(cell).encode('utf-8') for cell in row])
    csvfile.seek(0)
    return csvfile

def to_excel_csv(cursor, none_value=None, **writerparams):
    return to_csv(cursor, none_value=none_value, remove_linebreaks=True,
            delimiter=';', dialect='excel', **writerparams)

def to_excel(cursor, none_value=None):
    from openpyxl import Workbook
    wb = Workbook(encoding='utf-8')
    sheet = wb.get_active_sheet()
    docs = cursor_to_rows(cursor, none_value)
    for i in range(len(docs)):
        for j in range(len(docs[i])):
            tmp = docs[i][j]
            if not( isinstance(tmp, str) and isinstance(tmp, unicode) and \
                    isinstance(tmp, float) and isinstance(tmp, int)):
                tmp = unicode(tmp)
            sheet.cell(row=i, column=j).value = tmp
    #f = TemporaryFile()
    f = io.BytesIO()
    wb.save(f)
    f.seek(0)
    return f


def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key[0]) ]
    return sorted(l, key = alphanum_key)

def cursor_to_rows(cursor, none_value=None):
    docs = list(cursor)
    h = Header(*docs)
    rows = [h.getFlatHeaders(False)] + h.getDataFromDocs(docs)
    if none_value is not None:
        for i in range(1,len(rows)):
            for j in range(len(rows[i])):
                if rows[i][j] is None:
                    rows[i][j] = none_value
    return rows


class Header(object):
    def __init__(self, *docs):
        self.tag = docs[0]['tag']
        self.parent = None
        self.names = []
        self.children = []
        self.additional_data = None

        for doc in docs:
            self.addDoc(doc)

    def setParent(self, p):
        self.parent = p
        return self


    def addDoc(self, doc):
        assert(self.tag == doc['tag'])
        for k, v in natural_sort(doc.items()):
            if k in ['_id', 'tag', 'uid']:
                pass
            elif k == 'subtreeData':
                for subDoc in v:
                    if subDoc == {}:
                        continue
                    found = False
                    for child in self.children:
                        if subDoc['tag'] == child.tag:
                            child.addDoc(subDoc)
                            found = True
                            break
                    if not found:
                        self.children.append(Header(subDoc).setParent(self))
            elif k == 'additionalData':
                v['tag'] = 'additionalData'
                if self.additional_data is None:
                    self.additional_data = Header(v)
                else:
                    self.additional_data.addDoc(v)
            elif k not in self.names:
                self.names.append(k)

    def getFlatHeaders(self, with_root=True, deep=True, additional_data=True):
        rl = []
        pre = self.tag + '.' if with_root else ''
        for name in self.names:
            rl.append(pre + name)
        if deep:
            for child in self.children:
                for h in child.getFlatHeaders():
                    rl.append(pre + h)
        if self.additional_data and additional_data:
            for h in self.additional_data.getFlatHeaders():
                    rl.append(pre + h)
        return rl

    def getDataFromDoc(self, doc):
        rv = []
        assert(doc == {} or doc['tag'] == self.tag)
        headers = self.getFlatHeaders(False, False, False)
        for header in headers:
            rv.append(doc.get(header, None))
        for child in self.children:
            found = False
            for subDoc in doc.get('subtreeData', []):
                try:
                    if subDoc['tag'] == child.tag:
                        found = True
                        break
                except KeyError as e:
                    print(subDoc)
                    raise Exception("break")
            rv = rv + child.getDataFromDoc(subDoc if found else {})
        if self.additional_data:
            rv = rv + self.additional_data.getDataFromDoc(doc.get('additionalData', {}))
        return rv

    def getDataFromDocs(self, docs):
        rv = []
        for doc in docs:
            rv.append(self.getDataFromDoc(doc))
        return rv

    def __unicode__(self):
        if self.parent:
            return unicode(self.parent) + '.' + self.tag
        return unicode(self.tag)

    def __str__(self):
        return unicode(self).encode('utf-8')
