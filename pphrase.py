from spacy.symbols import nsubj, nsubjpass, dobj, iobj, pobj
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
                 lang='ru', np_labels=[nsubj, nsubjpass, dobj, iobj, pobj],
                 function_words=None, derivative_prepositions=None):

        print('Initializing...')
        self.nlp = spacy_udpipe.load_from_path(lang, udpipe_model)
        self.np_labels = set(np_labels)

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
        text = '. '.join([re.sub('[^а-яёa-z]+', ' ', sent).strip() for sent in text])
        # unnecessary (remove)
        for gar in ['n ст.', ' n фз']:
            text = text.replace(gar, '')
        return text

    def __get_context(self, token, window):
        return self.doc[token.i-window-1:token.i+window]

    def __is_part_functional(self, token):
        # check if preposition is a part of any of functional words in
        # context_funct range
        context = self.__get_context(token, self.context_funct).text
        if len(context.split('.')) > 1:
            context = context.split('.')[1]
        candidates = list(filter(lambda x: x if x in context else None, self.function_words))
        if len(candidates) and list(filter(lambda x: self.doc[token.i-1:token.i+1].text in x or
                                                     self.doc[token.i:token.i+2].text in x, candidates)):
            return True
        return False

    def __is_part_derivative(self, token):
        context = self.__get_context(token, self.context_der)
        found_derivative = list(filter(lambda x: set(x.split()).issubset(context.text.split()),
                                                 self.derivative_prepositions))
        if found_derivative:
            self.deriv_context = context
            self.found_derivative = max(found_derivative, key=len).split()
            return True
        return False
    
    def __add_phrase_to_output(self, preposition, phrase):
        if preposition not in self.prep_phrases:
            self.prep_phrases[preposition] = list()
        self.prep_phrases[preposition].append(phrase)

    def extract_phrases(self, text: str):
        self.doc = self.nlp(self.__process_text(text))
        self.prep_phrases = {}
        for token in self.doc:
            if token.pos_ == 'ADP':

                if self.function_words is not None:
                    if self.__is_part_functional(token):
                        continue

                if self.derivative_prepositions is not None:
                    if self.__is_part_derivative(token):
                        # TODO: move to new function (__extract_derivative_from_context)
                        orig_con_idx = [self.deriv_context[0].i, self.deriv_context[-1].i]
                        while self.deriv_context[orig_con_idx[0]].text != self.found_derivative[0]:
                            orig_con_idx[0] += 1
                        print()
                        while self.deriv_context[orig_con_idx[1]].text != self.found_derivative[-1]:
                            orig_con_idx[1] -= 1
                        derivative = self.deriv_context[orig_con_idx[0]:orig_con_idx[1]+1]
                        if derivative[-1].pos_ != 'ADP':
                            slave_i = derivative[-1].i + 1
                            while self.doc[slave_i].head != derivative[-1]:
                                slave_i += 1
                            slave = self.doc[slave_i]
                            extracted_phrase = ' '.join([derivative[-1].head.text,
                                                         derivative.text,
                                                         slave.text])
                        else:
                            extracted_phrase = ' '.join([derivative[-1].head.head.text, 
                                                         derivative.text,
                                                         derivative[-1].head.text])
                        preposition = derivative.text
                        self.__add_phrase_to_output(preposition, extracted_phrase)
                        continue

                extracted_phrase = ' '.join([token.head.head.text, token.text, token.head.text])
                self.__add_phrase_to_output(token, extracted_phrase)
        return self.prep_phrases
