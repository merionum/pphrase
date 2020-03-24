from ufal.udpipe import Model, Pipeline
import networkx as nx
from argparse import ArgumentParser
import json
from tqdm import tqdm
import pandas as pd


class Token():

    def __init__(self, token: list):
        self.id = int(token[0])
        self.form = token[1]
        self.lemma = token[2]
        self.upos = token[3]
        self.xpos = token[4]
        self.feats = token[5]
        self.head = int(token[6])
        self.dep = token[7]
        self.misc = token[8]


def get_preps(sent):
    preps = dict()
    fixed = set()
    for tok in sent:
        if not tok.dep =='fixed':
            continue
        if tok.head not in preps:
            preps[tok.head] = [[tok]]
        else:
            preps[tok.head][0].append(tok)
        fixed.add(tok)

    for tok in sent:
        if tok.id in preps:
            preps[tok.id][0].append(tok)
            preps[tok.id].append(tok.head)
        elif tok.upos == 'ADP' and tok not in fixed:
            preps[tok.id] = [[tok], tok.head]

    preps = {k: v for k, v in preps.items()
             if any([tok.upos == 'ADP' for tok in v[0]])}
    return preps

def get_succesors_by_id(sent, id):
    G = nx.DiGraph()
    G.add_edges_from([(tok.head, tok.id) for tok in sent])
    return nx.dfs_successors(G, source=id)

def get_sorted_sent(tokens):
    return ' '.join([tok.form for tok in sorted(tokens,
                     key=lambda x: x.id, reverse=False)])

def get_tok_tags(token):
    return f'PartOfSpeech={token.upos}|{token.feats}'

def get_phrase(prep, dep_id, sent):
    dep = sent[dep_id-1]
    host = sent[dep.head-1]
    bad_host = False
    members = [dep, host]
    if host == dep or host.upos == 'PUNCT':
        bad_host = True
        members.pop()    

    prep_ids = {p.id for p in prep}
    members_ids = {t.id for t in members}

    dep_succesors = get_succesors_by_id(sent, dep.id)

    dep_subtree = [sent[i-1] for i in set().union(*dep_succesors.values())
                                   if i not in prep_ids|members_ids]

    phrase = {'phrase': get_sorted_sent(prep + dep_subtree + members),
              'host': host.form if not bad_host else None,
              'preposition': get_sorted_sent(prep),
              'dependant': dep.form,
              'full_dependant': get_sorted_sent([dep] + dep_subtree),
              'host_tags': get_tok_tags(host) if not bad_host else None,
              'dependant_tags': get_tok_tags(dep),
              'host_lemma': host.lemma if not bad_host else None,
              'dependant_lemma': dep.lemma}

    return phrase

def run(model_file, text_file):
    print('Loading model...')
    model = Model.load(model_file)
    pipeline = Pipeline(model, 'tokenize', Pipeline.DEFAULT,
                                Pipeline.DEFAULT, 'conllu')
    print('Reading corpus...')
    with open(text_file) as f:
        text = f.read()

    print('Analyzing text...')
    processed = pipeline.process(text)

    print('Extracting phrases...')
    phrases = []
    sent = []
    for line in tqdm((processed+'#').splitlines()):
        if line.startswith('#') and len(sent):
            preps = get_preps(sent)
            for prep, dep_id in preps.values():
                pphrase = get_phrase(prep, dep_id, sent)
                phrases.append(pphrase)
            sent.clear()
        elif len(line) > 1:
            try:
                sent.append(
                        Token(
                            line.split('\t')
                        )
                )
            except ValueError:
                continue
    print('Done!')
    return phrases


if __name__ == '__main__':

    parser = ArgumentParser()
    parser.add_argument('model_file')
    parser.add_argument('input_file')
    parser.add_argument('output_file')
    parser.add_argument('output_format')
    args = parser.parse_args()

    if args.output_format not in ('json', 'csv', 'tsv'):
        raise RuntimeError ('Not available format. JSON / CSV / TSV are available') 
    phrases = run(args.model_file, args.input_file)

    print('Writing output...')
    if args.output_format == 'json':
        with open(args.output_file, 'w', encoding='utf8') as f:
            json.dump(phrases, f, indent=4, ensure_ascii=False)

    elif args.output_format == 'csv':
        pd.DataFrame(phrases).to_csv(args.output_file)

    elif args.output_format == 'tsv':
        pd.DataFrame(phrases).to_csv(args.output_file, sep='\t')
