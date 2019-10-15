from spacy.symbols import *
from nltk.tokenize import sent_tokenize, word_tokenize
import spacy_udpipe
import re

# TODO move function_words to extract_phrases

def handle_cyrillic_yo(tokens):
    for phrase in tokens:
        if 'ё' in phrase:
            tokens.append(phrase.replace('ё', 'е'))
    return tokens

class Extractor:
    """
    dependancy based prepositional phrases extraction;
    prepositions as parts of imported function words are ignored;
    the default UDPipe model for Russian is russian-syntagrus-2.4;
    """
    def __init__(self, udpipe_model='russian-syntagrus-ud-2.4-190531.udpipe',
                 lang='ru', np_labels=[nsubj, nsubjpass, dobj, iobj, pobj],
                 function_words_path=None):

        print('Initializing...')
        self.nlp = spacy_udpipe.load_from_path(lang, udpipe_model)
        self.np_labels = set(np_labels)

        if function_words_path is not None:
            self.check_functional = True
            with open(function_words_path, 'r') as f:
                self.function_words = handle_cyrillic_yo(

                                      [re.sub('[^А-Яа-яЁё]+', ' ', w.strip('\n').lower()).strip() \
                                       for w in f.readlines() if not w.endswith(':') \
                                       and len(w.split()) > 1])

                self.context_window = max([len(p.split()) for p in self.function_words]) - 1

        print('Ready!')

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
        text = '. '.join([re.sub('[^А-Яа-яЁёA-Za-z]+', ' ', sent).strip() for sent in text])
        for gar in ['n ст.', ' n фз']:
            text = text.replace(gar, '')
        return text

    def __iter_nps(self, doc):
        # TODO
        for word in doc:
            if word.dep in self.np_labels:
                yield word.subtree

    def __is_part_functional(self, token):
        # check if preposition is a part of any of functional words in
        # context_window range
        context = self.doc[token.i-self.context_window:token.i+self.context_window].text
        if len(context.split('.')) > 1:
            context = context.split('.')[1]
        candidates = list(filter(lambda x: x if x in context else None, self.function_words))
        if len(candidates) and list(filter(lambda x: self.doc[token.i-1:token.i+1].text in x or
                                                     self.doc[token.i:token.i+2].text in x, candidates)):
            return True
        return False

    def __is_part_derivative(self, token):
        return

    def extract_phrases(self, text: str):
        self.doc = self.nlp(self.__process_text(text))
        self.prep_phrases = {}
        for token in self.doc:
            if token.pos_ == 'ADP':

                if self.check_functional:
                    if self.__is_part_functional(token):
                        continue

                if self.__is_part_derivative(token):
                    pass

                # constr_idx = [token.head.head.i, token.i, token.head.i]

                # if token.text not in self.prep_phrases:
                #     self.prep_phrases[token.text] = list()
                # constr_idx = [token.head.head.i, token.i, token.head.i]

                # # get nps
                # context = self.doc[min(constr_idx):max(constr_idx)+1].text

                # if not self.__is_part_extracted(extracted_context):
                #     self.prep_phrases[token.text].append(extracted_context)
        return 'Okay'
        # self.prep_phrases
