from nltk.tokenize import sent_tokenize
from collections import Iterable
import pkgutil
import pymorphy2
import numpy as np
import spacy_udpipe

LANGS = ['be', 'ru']


class Extractor:
    """
    dependancy based prepositional phrases extraction;
    prepositions as parts of imported function words are ignored;
    """
    def __init__(self, udpipe_model, lang, functionals=None, derivatives=None, tag=False):
        self.lang = lang
        self.nlp = spacy_udpipe.load_from_path(self.lang, udpipe_model)
        if lang in LANGS:
            functionals = self.__load_from_path(lang, 'functionals')
            derivatives = self.__load_from_path(lang, 'derivatives')
            self.base_preps = self.__load_from_path(lang, 'simple')
        self.tag = tag
        if self.tag:
            self.morphy = pymorphy2.MorphAnalyzer()
        self.functionals, self.context_funct = self.__prep_entities(functionals)
        self.derivatives, self.context_der = self.__prep_entities(derivatives)

        if self.functionals is not None:
            self.derivatives = [t for t in self.derivatives
                                if t not in self.functionals]

    def __load_from_path(self, lang, filename):
        return pkgutil.get_data('pphrase', f'static/{lang}_{filename}.txt') \
                      .decode().splitlines()

    def __prep_cyr_words(self, tokens):
        tokens = [tok.lower().strip() for tok in tokens]
        for phrase in tokens:
            for char in ['ё', '-']:
                if char in phrase:
                    if char == 'ё':
                        replaced = phrase.replace('ё', 'е')
                    else:
                        replaced = phrase.replace('-', ' ')
                    if replaced not in tokens:
                        tokens.append(replaced)
        return tokens

    def __prep_entities(self, entity):
        if entity is None:
            return None, None
        max_context = max([len(p.split()) for p in entity]) - 1
        if self.lang in LANGS:
            entity = self.__prep_cyr_words(entity)
        return entity, max_context

    def __unpack(self, nested):
        return [item for sublist in nested for item in sublist]

    def __process_text(self, text: str):
        text = text.strip().strip('\n').strip().split('\n')
        text = self.__unpack([sent_tokenize(p) for p in text])
        for i in range(len(text)):
            tokens = text[i].split()
            for tok in tokens:
                if (len(tok) < 5 and
                   ((tok[0] == tok[-1] == '"') or
                    (tok[-1] == ')'))) or \
                 (len(tok) <= 2 and tok.endswith('.')):
                    tokens.remove(tok)
            text[i] = ' '.join([t for t in tokens if len(t)])
        return text

    def __get_context(self, token, window):
        left_window = token.i - window - 1
        if left_window < self.sent.start:
            left_window = self.sent.start
        right_window = token.i + window
        if right_window >= self.sent.end:
            right_window = self.sent.end
        return self.doc[left_window:right_window]

    def __is_part_functional(self, token):
        if self.functionals is None:
            return False
        context = self.__get_context(token, self.context_funct).text

        if len(context.split('.')) > 1:
            context = context.split('.')[1]
        candidates = list(filter(lambda x: x if x in context else None,
                                 self.functionals))
        if len(candidates) and list(filter(
                               lambda x: self.sent[token.i-1:token.i+1].text in x
                                         or self.sent[token.i:token.i+2].text in x,
                                        candidates)):
            return True
        return False

    def __is_order_consistent(self):
        return [word.text.lower() for word in self.deriv_context
                if word.text.lower() in self.found_derivative] == self.found_derivative

    def __is_part_derivative(self, token):
        if self.derivatives is None:
            return False
        context = self.__get_context(token, self.context_der)
        found_derivative = list(filter(lambda x: x in context.text.lower()
                                        and token.text.lower() in x.split(), self.derivatives))
        if found_derivative:
            self.found_derivative = max(found_derivative, key=len).split()
            self.deriv_context = context
            if self.__is_order_consistent():
                return True
        return False

    def __get_derivative(self):
        or_id = [0, len(self.deriv_context)-1]
        while self.deriv_context[or_id[0]].text.lower() != self.found_derivative[0]:
            or_id[0] += 1
        while self.deriv_context[or_id[1]].text.lower() != self.found_derivative[-1]:
            or_id[1] -= 1
        return self.deriv_context[or_id[0]:or_id[1]+1]

    def __get_dependant(self):
        iter = 0
        attempt = self.der_last
        while iter < len(self.derivative):
            iter += 1
            attempt = attempt.head
            if attempt not in self.derivative:
                return attempt
        return False

    def __get_host(self, ancestors, dependant):
        if 'VERB' in [t.pos_ for t in ancestors if t]:
            cands = [t for t in ancestors if (t and t.pos_ == 'VERB'
                                              and t not in self.derivative)]
        else:
            cands = [t for t in ancestors if (dependant and t != dependant
                     and t not in self.derivative and t)]
        return self.__get_closest(cands)

    def __get_closest(self, tokens):
        if not len(tokens):
            return False
        return tokens[np.argmin([abs(self.der_last.i - t.i) for t in tokens])]
    
    def __get_related_np(self, token, preposition):
        if not token:
            return False
        np = list(t for t in token.subtree)
        for t in np:
            if t.pos_ == 'ADP':
                self.extracted_idx.add(t.i)
        np = [t for t in np 
              if t not in preposition]
        if ',' in [t.text for t in np]:
            return False
        if len(np) <= 12:
            return np
        else:
            return [token]

    def __add_phrase_to_output(self, preposition, host, dependant, full_dependant):
        p = {}
        if isinstance(preposition, Iterable):
            phrase = [t for t in preposition]
        else:
            phrase = [preposition]
        phrase.extend(full_dependant)
        phrase.extend([host])
        phrase = [t.text for t in sorted(phrase, key=lambda x: x.i)]
        for tok in phrase:
            if any(char.isdigit() for char in tok):
                if len(tok) == 4:
                    phrase[phrase.index(tok)] = 'YEAR'
                else:
                    phrase[phrase.index(tok)] = 'NUM'
        phrase = ' '.join(phrase)
        p['phrase'] = phrase
        p['host'] = host.text
        p['prep'] = preposition.text
        p['dependant'] = dependant.text

        if self.tag:
            h = self.morphy.parse(host.text)[0]
            d = self.morphy.parse(dependant.text)[0]
            p['host_pos'] = h.tag.POS
            p['host_lemma'] = h.normal_form
            p['dependant_case'] = d.tag.case
            p['dependant_pos'] = d.tag.POS
            p['dependant_num'] = d.tag.number
            p['dependant_lemma'] = d.normal_form
        self.prep_phrases.append(p)

    def __mem_derivative(self):
        for tok in list(self.derivative):
            if tok.pos_ == 'ADP':
                self.extracted_idx.add(tok.i)
    
    def __leave_prep(self, prep):
        if len(prep.split()) == 1 and prep not in self.base_preps:
            return False
        return True

    def __remove_non_pphrases(self):
        if self.lang in LANGS:
            self.prep_phrases[:] = (k for k in self.prep_phrases
                                    if self.__leave_prep(k['prep']))

    def extract_phrases(self, text: str):
        self.prep_phrases = list()
        sents = self.__process_text(text)
        for sent in sents:
            self.extracted_idx = set()
            self.doc = self.nlp(sent)
            try:
                self.sent = next(self.doc.sents)
            except StopIteration:
                continue
            for token in self.sent:
                if token.pos_ != 'ADP' or \
                   token.i in self.extracted_idx or \
                   self.__is_part_functional(token):
                    continue
                if self.__is_part_derivative(token):
                    self.derivative = self.__get_derivative()
                    self.der_last = self.derivative[-1]
                    if self.der_last.pos_ == 'ADP':
                        dependant = self.__get_dependant()
                        host = self.__get_host(list(self.der_last.ancestors),
                                                   dependant)
                    else:
                        children = [t for t in self.der_last.children
                                    if t not in self.derivative]
                        dependant = self.__get_closest(children) 
                        host = self.__get_host(list(self.derivative[0].ancestors),
                                                        dependant)
                    full_dependant = self.__get_related_np(dependant, self.derivative)
                    if not all([dependant, host, full_dependant]):
                        continue
                    preposition = self.derivative
                    self.__mem_derivative()
                else:
                    preposition = token
                    dependant = preposition.head
                    host = dependant.head
                    if dependant == host:
                        continue
                    full_dependant = self.__get_related_np(dependant, self.sent[preposition.i:preposition.i+1])
                    if not full_dependant:
                        continue
                    self.extracted_idx.add(preposition.i)
                self.__add_phrase_to_output(preposition, host, dependant, full_dependant)
        self.__remove_non_pphrases()
        return self.prep_phrases
