from typing import Dict, Generator, List, Tuple, Union
import json
import re


def extend_code_scheme(code_scheme: Dict[str, any]) -> Dict[str, any]:
    extended_scheme = {}
    unknown_scheme = {}
    for code in code_scheme:
        extended_scheme[code] = code_scheme[code]
        if code.isdigit() is False:
            continue
        for i in range(0, 10):
            unknown_code = f'{code[:2]}{i}'
            if unknown_code not in code_scheme:
                # print('adding unknown code:', unknown_code)
                unknown_scheme[unknown_code] = code
    for unknown_code in unknown_scheme:
        map_code = unknown_scheme[unknown_code]
        pos = re.sub(r'\(.*\)', '(unknown)', code_scheme[map_code]['pos'])
        cql_parts = code_scheme[map_code]['cql'].split(', ')
        mapped_parts = []
        for cql_part in cql_parts:
            if cql_part.startswith('pos='):
                mapped_parts.append(cql_part)
            else:
                cql_part = re.sub(r'=.*', '=unknown', cql_part)
                mapped_parts.append(cql_part)
        cql = ', '.join(mapped_parts)
        extended_scheme[unknown_code] = {'code': unknown_code, 'pos': pos, 'cql': cql}
    return extended_scheme


def read_code_scheme(code_scheme_file: str):
    with open(code_scheme_file, 'rt') as fh:
        if code_scheme_file.endswith('.json'):
            return json.load(fh)
        elif code_scheme_file.endswith('.tsv'):
            code_scheme = {}
            headers = next(fh).strip().split('\t')
            for line in fh:
                row = line.strip('\n').split('\t')
                try:
                    row_json = {header: row[hi] for hi, header in enumerate(headers)}
                except IndexError:
                    print(line)
                    raise
                code_scheme[row_json['code']] = row_json
            return code_scheme


def map_sent_sign(line: Dict[str, any], sent_sign: str) -> Union[str, None]:
    if sent_sign == '-':
        return None
    if len(sent_sign) == 2 and sent_sign[0].isdigit():
        sent_sign = sent_sign[0]
    if sent_sign.isdigit() is False:
        raise TypeError(f"WARNING {line['num']} - invalid sent_sign type #{sent_sign}#")
    sent_sign = int(sent_sign)
    if sent_sign == 1:
        return 'start_main_sent'
    if sent_sign == 2:
        return 'continue_sent'
    if sent_sign == 4:
        return 'start_relative_clause'
    if sent_sign == 5:
        return 'start_adverbial_clause'
    if sent_sign == 8:
        return 'start_conj_clause'
    if sent_sign == 9:
        return 'uncodeable'


def get_digits(code: str) -> str:
    return ''.join([char for char in code if char.isdigit()])


def map_pos_code(line: Dict[str, any], pos_code: str,
                 code_scheme: Dict[str, Dict[str, str]]) -> Tuple[str, Union[str, None]]:
    if pos_code[0].isalpha() and pos_code[0].islower():
        # print(f'Changing pos_code {pos_code} to title case')
        pos_code = f'{pos_code[0].upper()}{pos_code[1:]}'
    if re.match(r'[A-Z]\w+\(\w+\).+', pos_code):
        print(f'WARNING line {line["num"]} - Removing trailing characters from pos_code {pos_code}')
        pos_code = re.sub(r'\).*', r')', pos_code)
    if pos_code[0] == 'X':
        print(f'WARNING line {line["num"]} - Removing X from pos_code {pos_code}')
        pos_code = pos_code[1:]
    elif len(pos_code) == 2:
        print(f'WARNING line {line["num"]} - Adding missing digit 9 to pos_code {pos_code}')
        pos_code = f'{pos_code}9'
    elif len(pos_code) > 3 and len(get_digits(pos_code)) == 3:
        # print(f'Removing non-digit from pos_code {pos_code}')
        pos_code = get_digits(pos_code)
    if '+' in pos_code:
        pos_code = re.sub(r'\++', r'+', pos_code)
        code_parts = pos_code.split('+')
        pos, cql = zip(*[map_pos_code(line, code_part, code_scheme) for code_part in code_parts])
        # print(pos_code, pos, cql)
        return pos, cql
    if pos_code.isdigit() and len(pos_code) != 3:
        print(f'WARNING line {line["num"]} - Changing invalid pos_code {pos_code} to 999')
        pos_code = '999'
    elif pos_code.isalpha() and len(pos_code) > 4:
        print(f'WARNING line {line["num"]} - Changing invalid pos_code {pos_code} to 999')
        pos_code = '999'
    pos, cql = None, None
    if pos_code in code_scheme:
        pos = code_scheme[pos_code]['pos']
        cql = code_scheme[pos_code]['cql']
    elif pos_code.startswith('Punc('):
        pos = 'Punc(unknown)'
        cql = 'Punc(unknown)'
    else:
        print(f'WARNING line {line["num"]} - Changing invalid pos_code {pos_code} to 999')
        pos_code = '999'
        pos = code_scheme[pos_code]['pos']
        cql = code_scheme[pos_code]['cql']
    if pos is None or cql is None:
        raise ValueError(f'ERROR line {line["num"]} - unknown pos_code: {pos_code}')
    else:
        return pos, cql


def parse_token_line(line: Dict[str, any], code_scheme):
    if len(line['text'].split(' ')) == 9 and line['text'].startswith('@ @ @ '):
        print(f'WARNING line {line["num"]} - Removing @ from line {line["text"]}')
        line['text'] = line['text'][2:]
    if len(line['text'].split(' ')) == 5:
        orig, lower, full, lemma, pos_code = line['text'].split(' ')
        if lemma.isalpha() and pos_code.isdigit():
            print(f'WARNING line {line["num"]} - Assume missing fields 6, 7, 8, add - - - in line {line["text"]}')
            line["text"] = f'{line["text"]} - - -'
    if len(line["text"].split(' ')) == 7:
        orig, lower, full, lemma, pos_code, field6, field7 = line["text"].split(' ')
        if pos_code.isdigit() and field6 == '-' and field7 == '-':
            print(f'WARNING line {line["num"]} - Adding sent_sign field to line {line["text"]}')
            line["text"] = f'{line["text"]} -'
        elif pos_code.isdigit() and field6 == '-' and field7.isdigit():
            print(f'WARNING line {line["num"]} - Adding field 7 - to line {line["text"]}')
            line["text"] = f'{orig} {lower} {full} {lemma} {pos_code} {field6} - {field7}'
        elif pos_code == '-' or pos_code == '???':
            print(f'WARNING line {line["num"]} - Inserting unknown POS 999 to line {line["text"]}')
            line["text"] = f'{orig} {lower} {full} {lemma} 999 {pos_code} {field6} {field7}'
    if len(line["text"].split(' ')) != 8:
        raise ValueError(f"ERROR line {line['num']} - unexpected number of elements in line #{line['text']}#")
    fields = line["text"].split(' ')
    orig, lower, full, lemma, pos_code, field6, field7, sent_sign = fields
    if field6 != '-':
        # print('field 6:', field6)
        pass
    if field7 != '-':
        # print('field 7:', field6)
        pass
    if pos_code == '-' or pos_code == '???':
        pos_code = '999'
        print(f'WARNING line {line["num"]} - Inserting unknown POS 999 to line["text"] {line["text"]}')
    try:
        pos, cql = map_pos_code(line, pos_code, code_scheme)
    except ValueError:
        raise
    try:
        sent_sign = map_sent_sign(line, sent_sign)
    except TypeError:
        print(f'WARNING line {line["num"]} - {line["text"]}')
        raise
    token = {
        'orig': orig,
        'lower': lower,
        'full': full,
        'lemma': lemma,
        'pos_code': pos_code,
        'pos': pos,
        'cql': cql,
        'sent_sign': sent_sign
    }
    return token


def read_docs(fname: str) -> Generator[List[Dict[str, any]], None, None]:
    with open(fname, 'rt') as fh:
        doc_lines = []
        for li, line in enumerate(fh):
            # print('parsing line', line)
            line = line.strip()
            # if li == 0:
            #     continue
            if len(line) == 0 or line.startswith('#'):
                continue
            if '  ' in line:
                line = re.sub(' +', ' ', line)
            # print(li, len(line), f'#{line}#')
            if line.startswith('_n:'):
                print(f'WARNING line {li+1} - skipping line {line}')
                continue
            if re.match('@ @ @ _[co]:', line) or re.match('_[co]:', line):
                if len(doc_lines) > 0:
                    yield doc_lines
                doc_lines = []
            # print('appending line', line)
            doc_lines.append({'num': li+1, 'text': line.strip()})
        if len(doc_lines) > 0:
            yield doc_lines


def parse_metadata_line(line: Dict[str, any]):
    # @ @ @ _o:I222p30601.RAAntwerpenStBernardHemiksem.Summarium113.VlpNr6 Markup(samp) - - -
    if line['text'].startswith('@ @ @'):
        line['text'] = line['text'].replace('@ @ @ ', '')
    m = re.match(r'^(_[co]):(\S+) ', line['text'])
    doc_id_prefix = m.group(1)
    doc_id = m.group(2)
    if m := re.match(r'^([A-Z])(\d+)([a-zA-Z])(\d{3})(\d+)\.(.*)$', doc_id):
        metadata = {
            'kloeke_letter': m.group(1),
            'kloeke_number': m.group(2),
            'separator': m.group(3),
            'year': f'1{m.group(4)}',
            'serial_number': m.group(5),
            'archive_ref': m.group(6)
        }
    elif m := re.match(r'([A-Z])(\d+)([a-zA-Z])(\d{3})(\d+)', doc_id):
        metadata = {
            'kloeke_letter': m.group(1),
            'kloeke_number': m.group(2),
            'separator': m.group(3),
            'year': f'1{m.group(4)}',
            'serial_number': m.group(5)
        }
    elif m := re.match(r'([A-Z])(\d+)([a-zA-Z])(\d{3})(\d+)(_n:\d+-\d+)', doc_id):
        metadata = {
            'kloeke_letter': m.group(1),
            'kloeke_number': m.group(2),
            'separator': m.group(3),
            'year': f'1{m.group(4)}',
            'serial_number': m.group(5),
            'extra': m.group(6)
        }
    elif m := re.match(r'(GrHol|GrVla|HerBr|Latij|NoLoc)(\d{3})(\d+)_(I)(\d+)', doc_id):
        metadata = {
            'kloeke_letter': m.group(4),
            'kloeke_number': m.group(5),
            'separator': m.group(1),
            'year': f'1{m.group(2)}',
            'serial_number': m.group(3)
        }
    elif m := re.match(r'(GrHol|GrVla|HerBr|Latij|NoLoc)(\d{3})(\d+)(_n:.*?)_([A-Z])(\d+)', doc_id):
        metadata = {
            'kloeke_letter': m.group(5),
            'kloeke_number': m.group(6),
            'separator': m.group(1),
            'year': f'1{m.group(2)}',
            'serial_number': m.group(3),
            'extra': m.group(4)
        }
    elif m := re.match(r'(GrHol|GrVla|HerBr|Latij|NoLoc)(\d{3})(\d+)[-_](.*)', doc_id):
        metadata = {
            'extra': m.group(4),
            'separator': m.group(1),
            'year': f'1{m.group(2)}',
            'serial_number': m.group(3)
        }
    elif m := re.match(r'(GrHol|GrVla|HerBr|Latij|NoLoc)(\d{3})(\d+)$', doc_id):
        metadata = {
            'separator': m.group(1),
            'year': f'1{m.group(2)}',
            'serial_number': m.group(3)
        }
    else:
        print('doc_id:', doc_id)
        raise ValueError(f'ERROR line {line["num"]} - invalid metadata line: {line["text"]}')
    metadata['doc_id_prefix'] = doc_id_prefix
    metadata['doc_id'] = f'{doc_id_prefix}_{doc_id}'
    return metadata


