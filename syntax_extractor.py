import spacy_udpipe

class Extractor:
    """
    dependancy based prepositional constructions extraction;
    """

    def __init__(self, udpipe_model='russian-syntagrus-ud-2.4-190531.udpipe'):
        print('Initializing model...')
        self.nlp = spacy_udpipe.load_from_path('ru', udpipe_model)
        
        # import files with prepositions

        print('Model ready!')

    def extract_constructions(self, input):
        self.doc = self.nlp(input)
        self.constructions = {}
        for token in self.doc:
            if token.pos_ == 'ADP':

            	# check if homonym / complex prepos / part of auxillary

                if token.text not in self.constructions:
                    self.constructions[token.text] = set()
                constr_idx = [token.head.head.i, token.i, token.head.i]
                extracted_context = str(self.doc[min(constr_idx):max(constr_idx)+1])
                if not len(list(filter(lambda x: extracted_context in x,
                                        self.constructions[token.text]))):
                    self.constructions[token.text].add(extracted_context)
        return self.constructions
