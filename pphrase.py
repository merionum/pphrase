from nltk.tokenize import sent_tokenize, word_tokenize
import spacy_udpipe
import re


def handle_cyrillic_yo(tokens):
    for phrase in tokens:
        if 'ё' in phrase:
            replaced_e = phrase.replace('ё', 'е')
            if replaced_e not in tokens:
                tokens.append(replaced_e)
    return tokens

class Extractor:
    """
    dependancy based prepositional phrases extraction;
    prepositions as parts of imported function words are ignored;
    the default UDPipe model for Russian is russian-syntagrus-2.4;
    """
    def __init__(self, udpipe_model='russian-syntagrus-ud-2.4-190531.udpipe',
                 lang='ru', function_words=None, derivative_prepositions=None):

        print('Initializing...')
        self.nlp = spacy_udpipe.load_from_path(lang, udpipe_model)
        self.function_words = function_words
        if self.function_words is not None:
            self.context_funct = max([len(p.split()) for p in self.function_words]) - 1
            if lang == 'ru':
                self.function_words = self.__prep_cyr_words(self.function_words)

        self.derivative_prepositions = derivative_prepositions
        if self.derivative_prepositions is not None:
            self.context_der = max([len(p.split()) for p in self.derivative_prepositions]) - 1
            if lang == 'ru':
                self.function_words = self.__prep_cyr_words(self.function_words)
            if self.function_words is not None:
                self.derivative_prepositions = [p for p in self.derivative_prepositions
                                                if p not in self.function_words]
        print('Ready!')

    def __prep_cyr_words(self, tokens):
        for tok_id in range(len(tokens)):
            tokens[tok_id] = re.sub('[^а-яё]+', ' ', tokens[tok_id].lower().strip())
        tokens = handle_cyrillic_yo(tokens)
        return tokens

    def __process_text(self, text: str):
        tokens = text.replace('\n', '.').strip().lower().split()
        for tok in tokens:
            if len(tok) < 5 and ((tok[0] == tok[-1] == '"') or \
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
        text = '. '.join([re.sub('[^а-яёa-z0-9]+', ' ', sent).strip() for sent in text])
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
        # check if preposition is a part of any of functional words in
        # context_funct range
        context = self.__get_context(token, self.context_funct).text
        if len(context.split('.')) > 1:
            context = context.split('.')[1]
        candidates = list(filter(lambda x: x if x in context else None, self.function_words))
        if len(candidates) and list(filter(lambda x: self.sent[token.i-1:token.i+1].text in x or
                                                     self.sent[token.i:token.i+2].text in x, candidates)):
            return True
        return False

    def __order_consistent(self):
        return [word.text for word in self.deriv_context
                if word.text in self.found_derivative] == self.found_derivative

    def __is_part_derivative(self, token):
        context = self.__get_context(token, self.context_der)
        found_derivative = list(filter(lambda x: set(x.split()).issubset(context.text.split()),
                                                 self.derivative_prepositions))
        if found_derivative:
            self.found_derivative = max(found_derivative, key=len).split()
            self.deriv_context = context
            if self.__order_consistent():
                return True
        return False
    
    def __add_phrase_to_output(self, preposition, phrase):
        if preposition not in self.prep_phrases:
            self.prep_phrases[preposition] = list()
        self.prep_phrases[preposition].append(phrase)

    def __positional_slave_extraction(self, derivative):
        slave_found = False
        pointer = derivative[-1].i
        while pointer < self.sent.end and not slave_found:
            pointer += 1
            if self.doc[pointer].pos_ in ['NOUN', 'NPRO', 'LATN']:
                slave = self.doc[pointer]
                slave_found = True
        if not slave_found:
            slave = False
        return slave

    def __remember_preps(self, derivative):
        for tok in derivative:
            if tok.pos_ == 'ADP':
                self.extracted_idx.add(tok.i)


    def extract_phrases(self, text: str):
        self.doc = self.nlp(self.__process_text(text))
        self.prep_phrases = {}
        self.extracted_idx = set()
        sents = self.doc.sents
        for sent in sents:
            self.sent = sent
            for token in self.sent:
                if token.pos_ != 'ADP' or token.i in self.extracted_idx or \
                   self.function_words is None or (self.function_words and self.__is_part_functional(token)):
                    continue
                if self.derivative_prepositions is not None and self.__is_part_derivative(token):
                    orig_con_idx = [0, len(self.deriv_context)-1]
                    while self.deriv_context[orig_con_idx[0]].text != self.found_derivative[0]:
                        orig_con_idx[0] += 1
                    while self.deriv_context[orig_con_idx[1]].text != self.found_derivative[-1]:
                        orig_con_idx[1] -= 1
                    derivative = self.deriv_context[orig_con_idx[0]:orig_con_idx[1]+1]
                    if derivative[-1].pos_ == 'ADP':
                        slave = derivative[-1].head
                    if derivative[-1].pos_ != 'ADP' or (derivative[-1].pos_ == 'ADP' and slave in derivative):
                        slave = self.__positional_slave_extraction(derivative)
                        if not slave:
                            continue
                    extracted_phrase = [slave.head.text, derivative.text, slave.text]
                    if slave.head in derivative:
                        extracted_phrase = extracted_phrase[1:]
                    preposition = ' '.join(self.found_derivative)
                    self.__add_phrase_to_output(preposition, ' '.join(extracted_phrase))
                    self.__remember_preps(derivative)
                    continue
                extracted_phrase = ' '.join([token.head.head.text, token.text, token.head.text])
                self.__add_phrase_to_output(token.text, extracted_phrase)
                self.__remember_preps([token])
        return self.prep_phrases
