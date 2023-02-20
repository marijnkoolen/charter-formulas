from typing import Dict
import json
import re


def map_word_form(word_form, rewrite_map: Dict[str, str]):
    """Replace escaped characters by their unescaped representation."""
    if '(' in word_form:
        word_form = re.sub(r'\w+\((.*?)\)', '&\1;', word_form)

    if word_form in {'&period;', '&lp;', '&lpr;'}:
        word_form = '.'
    elif word_form in {'&l2p;', '&2periods;', '&l3p;'}:
        word_form = '..'
    elif word_form in {'&lk;', '&lpk;', '&ldk;', '&duitsekomma;', '&komma;', '&lpkr;', '&lkt;', '&lpkt;'}:
        word_form = ','
    elif word_form in {'&lsc;', '&semi;'}:
        word_form = ';'
    elif word_form in {'&ldp;', '&colon;'}:
        word_form = ':'
    elif word_form in {'&ls;', '&hyph;'}:
        word_form = '-'
    elif word_form in {'&l2s;', '&l3s;', '&l4s;', '&l5s;'}:
        word_form = '--'
    elif word_form in {'&lt;', '&lpt;', '&tilde;'}:
        word_form = '~'
    if word_form in rewrite_map:
        word_form = rewrite_map[word_form]
    return word_form


class CharterReader:

    def __init__(self, charter_files, form, as_sentences: bool = False, as_clauses: bool = False,
                 rewrite_map: Dict[str, str] = None):
        if isinstance(charter_files, str):
            charter_files = [charter_files]
        self.charter_files = charter_files
        self.form = form
        self.as_clauses = as_clauses
        self.forms = ['orig', 'lower', 'full', 'lemma']
        self.as_sentences = as_sentences
        self.rewrite_map = rewrite_map if rewrite_map is not None else {}

    def _map_word_form(self, token):
        if self.form == 'token':
            for form in self.forms:
                token[form] = map_word_form(token[form], self.rewrite_map)
            return token
        elif isinstance(self.form, str):
            return map_word_form(token[self.form], self.rewrite_map)
        elif isinstance(self.form, list) or isinstance(self.form, tuple):
            return tuple([map_word_form(token[form], self.rewrite_map) for form in self.form])

    def _generate_doc(self, doc):
        return {
            'doc_id': doc['metadata']['doc_id'],
            'words': [self._map_word_form(token) for token in doc['tokens']]
        }

    def _generate_sentence_doc(self, doc, sent_tokens, sent_num):
        return {
            'doc_id': f"{doc['metadata']['doc_id']}____{sent_num}",
            'charter_id': doc['metadata']['doc_id'],
            'words': [self._map_word_form(token) for token in sent_tokens]
        }

    def _generate_sentence_docs(self, doc):
        sent_docs = []
        sent_tokens = []
        for token in doc['tokens']:
            is_doc_start = False
            if self.as_clauses and token['sent_sign'] is not None:
                is_doc_start = True
            elif self.as_sentences and token['sent_sign'] == 'start_main_sent':
                is_doc_start = True
            if is_doc_start is True:
                if len(sent_tokens) > 0:
                    sent_doc = self._generate_sentence_doc(doc, sent_tokens, len(sent_docs)+1)
                    sent_docs.append(sent_doc)
                sent_tokens = []
            sent_tokens.append(token)
        if len(sent_tokens) > 0:
            sent_doc = self._generate_sentence_doc(doc, sent_tokens, len(sent_docs) + 1)
            sent_docs.append(sent_doc)
        return sent_docs

    def __iter__(self):
        for charter_file in self.charter_files:
            with open(charter_file, 'rt') as fh:
                doc = json.load(fh)
                remove_lemmas = {'_l', '&scheider;'}
                doc['tokens'] = [token for token in doc['tokens'] if token['lemma'] not in remove_lemmas]
                if self.as_sentences is True or self.as_clauses is True:
                    for sent in self._generate_sentence_docs(doc):
                        yield sent
                else:
                    yield self._generate_doc(doc)
