from nltk.tokenize import sent_tokenize, word_tokenize
import pkgutil
import numpy as np
import spacy_udpipe
import re


class Extractor:
    """
    dependancy based prepositional phrases extraction;
    prepositions as parts of imported function words are ignored;
    """
    def __init__(self, udpipe_model, lang, functionals=None, derivatives=None):
        self.lang = lang
        self.nlp = spacy_udpipe.load_from_path(self.lang, udpipe_model)
        self.functionals, self.context_funct = self.__prep_entities(functionals)
        self.derivatives, self.context_der = self.__prep_entities(derivatives)

        if self.functionals is not None:
            self.derivatives = [t for t in self.derivatives
                                if t not in self.functionals]
        if self.lang == 'ru':
            self.base_preps = pkgutil.get_data('pphrase', 'ru_simple.txt') \
                                     .decode().splitlines()

    def __prep_cyr_words(self, tokens):
        for tok_id in range(len(tokens)):
            tokens[tok_id] = re.sub('[^а-яё]+', ' ',
                                    tokens[tok_id].lower().strip())
        for phrase in tokens:
            if 'ё' in phrase:
                replaced_e = phrase.replace('ё', 'е')
                if replaced_e not in tokens:
                    tokens.append(replaced_e)
        return tokens

    def __prep_entities(self, entity):
        if entity is None:
            return None, None
        max_context = max([len(p.split()) for p in entity]) - 1
        if self.lang == 'ru':
            entity = self.__prep_cyr_words(entity)
        return entity, max_context

    def __process_text(self, text: str):
        tokens = text.replace('\n', '.').strip().lower().split()
        for tok in tokens:
            if len(tok) < 5 and ((tok[0] == tok[-1] == '"') or
                                 (tok.endswith(')'))):
                tokens.remove(tok)
        text = [sent.split('...') for sent in sent_tokenize(' '.join(tokens))]
        text = [item for sublist in text for item in sublist]
        new_text = []
        for sent in text:
            new_sent = []
            for word in word_tokenize(sent):
                if len(word) <= 2 and word.endswith('.'):
                    continue
                new_sent.append(word)
            if len(new_sent):
                new_text.append(' '.join(new_sent))
        text = new_text
        text = '. '.join([re.sub('[^а-яёa-z0-9\-]+', ' ', sent).strip()
                          for sent in text])
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
                               lambda x: self.sent[token.i-1:token.i+1].text in x or
                                         self.sent[token.i:token.i+2].text in x,
                                    candidates)):
            return True
        return False

    def __is_order_consistent(self):
        return [word.text for word in self.deriv_context
                if word.text in self.found_derivative] == self.found_derivative

    def __is_part_derivative(self, token):
        if self.derivatives is None:
            return False
        context = self.__get_context(token, self.context_der)
        found_derivative = list(filter(
                           lambda x: set(x.split()).issubset(context.text.split()),
                                self.derivatives))
        if found_derivative:
            self.found_derivative = max(found_derivative, key=len).split()
            self.deriv_context = context
            if self.__is_order_consistent():
                return True
        return False

    def __get_derivative(self):
        or_id = [0, len(self.deriv_context)-1]
        while self.deriv_context[or_id[0]].text != self.found_derivative[0]:
            or_id[0] += 1
        while self.deriv_context[or_id[1]].text != self.found_derivative[-1]:
            or_id[1] -= 1
        return self.deriv_context[or_id[0]:or_id[1]+1]

    def __get_slave(self):
        iter = 0
        attempt = self.der_last
        while iter < len(self.derivative):
            iter += 1
            attempt = attempt.head
            if attempt not in self.derivative:
                return attempt
        return False

    def __get_master(self, ancestors, slave):
        if 'VERB' in [t.pos_ for t in ancestors if t]:
            cands = [t for t in ancestors if (t and t.pos_ == 'VERB')]
        else:
            cands = [t for t in ancestors if (slave and t != slave
                     and t not in self.derivative and t)]
        return self.__get_closest(cands)

    def __get_closest(self, tokens):
        if not len(tokens):
            return False
        return tokens[np.argmin([abs(self.der_last.i - t.i) for t in tokens])]

    def __add_phrase_to_output(self, preposition, phrase):
        phrase = ' '.join([t.text for t in phrase])
        if type(preposition) != str:
            preposition = preposition.text
        if preposition not in self.prep_phrases:
            self.prep_phrases[preposition] = list()
        self.prep_phrases[preposition].append(phrase)

    def __mem_derivative(self):
        for tok in list(self.derivative):
            if tok.pos_ == 'ADP':
                self.extracted_idx.add(tok.i)

    def __add_conjuncted(self, preposition, phrase):
        conjuncts = phrase[-1].conjuncts
        if len(conjuncts):
            for c in conjuncts:
                output = phrase[:2] + [c]
                self.__add_phrase_to_output(preposition, output)

    def __remove_non_pphrases(self):
        if self.lang == 'ru':
            for k in list(self.prep_phrases):
                if len(k.split()) == 1 and k not in self.base_preps:
                    del self.prep_phrases[k]

    def extract_phrases(self, text: str):
        self.doc = self.nlp(self.__process_text(text))
        self.prep_phrases = dict()
        self.extracted_idx = set()
        sents = self.doc.sents
        for sent in sents:
            self.sent = sent
            for token in self.sent:
                if token.pos_ != 'ADP' or \
                   token.i in self.extracted_idx or \
                   self.__is_part_functional(token):
                    continue
                if self.__is_part_derivative(token):
                    self.derivative = self.__get_derivative()
                    self.der_last = self.derivative[-1]
                    if self.der_last.pos_ == 'ADP':
                        slave = self.__get_slave()
                        master = self.__get_master(list(self.der_last.ancestors),
                                                   slave)
                    else:
                        children = [t for t in self.der_last.children
                                    if t not in self.derivative]
                        slave = self.__get_closest(children)
                        master = self.__get_master(list(self.derivative[0].ancestors),
                                                        slave)
                    if not all([slave, master]):
                        continue
                    phrase = [master, self.derivative, slave]
                    preposition = ' '.join(self.found_derivative)
                    self.__mem_derivative()
                else:
                    preposition = token
                    slave = preposition.head
                    master = slave.head
                    phrase = [master, preposition, slave]
                self.__add_phrase_to_output(preposition, phrase)
                self.__add_conjuncted(preposition, phrase)
        self.__remove_non_pphrases()
        return self.prep_phrases
