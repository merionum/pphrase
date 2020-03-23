# pphrase
pphrase is a UDPipe-based tool which extracts and (in the close future) semantically labels prepositional phrases in any given text.
For now only extraction is available.

It is a language agnostic tool but is primarily designed for slavic languages.

It is important to mention that the prepositional phrases here are considered to be a trinary union of the preposition, its host and the dependent (as in "jump over dog").


## Installation
1) Install dependancies from requirements
2) Download [UDPipe model](https://ufal.mff.cuni.cz/udpipe/models) for the target language
3) Download pphrase.py script
4) Run command :

```sh
$ python3 pphrase.py path-to-udpipe-model path-to-input path-to-output format

```
Available formats: json, csv, tsv

#### Example for Russian
input.txt contents:
"Я ехал на перекладных из Тифлиса."
```sh
$ python3 pphrase.py russian-syntagrus-ud-2.5-191206.udpipe input.txt output.json json

``` 
```
output.json contents:
>>>   [
        {
            "phrase": "ехал на перекладных из Тифлиса",
            "host": "ехал",
            "preposition": "на",
            "dependant": "перекладных",
            "full_dependant": "перекладных из Тифлиса",
            "host_tags": "PartOfSpeech=VERB|Aspect=Imp|Gender=Masc|Mood=Ind|Number=S
    ing|Tense=Past|VerbForm=Fin|Voice=Act",
            "dependant_tags": "PartOfSpeech=NOUN|Animacy=Inan|Case=Loc|Gender=Masc|N
    umber=Plur",
            "host_lemma": "ехать",
            "dependant_lemma": "перекладный"
        },
        ...
]
```
#### Example for English 
input.txt contents:
"The quick brown fox jumped over the lazy dog"
```sh
$ python3 pphrase.py english-ewt-ud-2.5-191206.udpipe input.txt output.json json

``` 
```
output.json contents:
>>>   [{
        "phrase": "jumped over the lazy dog",
        "host": "jumped",
        "preposition": "over",
        "dependant": "dog",
        "full_dependant": "the lazy dog",
        "host_tags": "PartOfSpeech=VERB|Mood=Ind|Tense=Past|VerbForm=Fin",
        "dependant_tags": "PartOfSpeech=NOUN|Number=Sing",
        "host_lemma": "jump",
        "dependant_lemma": "dog"
    }]

```

#### Todos

 - Add semantic processing
 - Add idiomatic phrasal verbs handling (compound attribute)
