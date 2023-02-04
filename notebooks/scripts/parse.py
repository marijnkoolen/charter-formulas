from typing import Dict, Generator, List, Tuple, Union
import json
import re


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
                code_scheme[row_json['Code']] = row_json
            return code_scheme


def map_sent_sign(sent_sign: str) -> Union[str, None]:
    if sent_sign == '-':
        return None
    if sent_sign.isdigit() is False:
        raise TypeError(f"invalid sent_sign type #{sent_sign}#")
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


def map_pos_code(pos_code: str, code_scheme: Dict[str, Dict[str, str]]) -> Tuple[str, Union[str, None]]:
    if '+' in pos_code:
        code_parts = pos_code.split('+')
        pos, cql = zip(*[map_pos_code(code_part, code_scheme) for code_part in code_parts])
        print(pos_code, pos, cql)
        return pos, cql
    if pos_code in code_scheme:
        pos = code_scheme[pos_code]['Vertaling']
        cql = code_scheme[pos_code]['CQL']
        return pos, cql
    else:
        raise ValueError(f'unknown pos_code: {pos_code}')


def parse_token_line(line: str, code_scheme):
    fields = line.split(' ')
    if len(line.split(' ')) != 8:
        raise ValueError(f"unexpected number of elements in line: #{line}#")
    orig, lower, full, lemma, pos_code, field6, field7, sent_sign = fields
    if field6 != '-':
        print('field 6:', field6)
    if field7 != '-':
        print('field 7:', field6)
    try:
        pos, cql = map_pos_code(pos_code, code_scheme)
    except ValueError:
        print(line)
        raise
    try:
        sent_sign = map_sent_sign(sent_sign)
    except TypeError:
        print(line)
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


def read_docs(fname: str) -> Generator[List[str], None, None]:
    with open(fname, 'rt') as fh:
        doc_lines = []
        for li, line in enumerate(fh):
            line = line.strip()
            if li == 0:
                continue
            if len(line) == 0 or line.startswith('#'):
                continue
            if '  ' in line:
                line = re.sub(' +', ' ', line)
            # print(li, len(line), f'#{line}#')
            if line.startswith('@ @ @ _o:') or line.startswith('_o:'):
                if len(doc_lines) > 0:
                    yield doc_lines
                doc_lines = []
            doc_lines.append(line.strip())
        if len(doc_lines) > 0:
            yield doc_lines


def parse_metadata_line(line: str):
    # @ @ @ _o:I222p30601.RAAntwerpenStBernardHemiksem.Summarium113.VlpNr6 Markup(samp) - - -
    if line.startswith('@ @ @'):
        line = line.replace('@ @ @ ', '')
    m = re.match(r'^_o:(\S+) ', line)
    doc_id = m.group(1)
    m = re.match(r'^([A-Z])(\d+)([a-z])(\d{3})(\d+)\.(.*)$', doc_id)
    if not m:
        print('invalid metadata line:', line)
    metadata = {
        'doc_id': doc_id,
        'kloeke_letter': m.group(1),
        'kloeke_number': m.group(2),
        'separator': m.group(3),
        'year': f'1{m.group(4)}',
        'serial_number': m.group(5),
        'archive_ref': m.group(6)

    }
    return metadata


