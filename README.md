# pphrase
pphrase is a tool which extracts and (in the close future) semantically labels prepositional phrases in any given text.
For now only extraction is available.

It has been tested for Russian only for now but it is designed to be a language agnostic tool.

pphrase is capable of working with prepositions which are parts of funсtional words and derivative prepositions. In order to do so you should provide a list of any (or both) of them when initialzing the extractor.

Инструмент для извлечения и (в будущем) семантической разметки предложных конструкций. Есть возможность задавать список служебных слов с предлогами (для их исключения) и список производных предлогов (для их добавления).

  - Initialize pphrase extractor with model and lists of functional words and derivatives (if needed)
  - Start phrases extraction
  - Receive a dictionary of the following format:
    
    ```python
    {'preposition_1': ['phrase_1', 'phrase_2', ...],
     'preposition_2': ['phrase_1', 'phrase_2', ...]}
    ```


## Installation

Apart from the dependencies pphrase requires a [UDPipe model](https://ufal.mff.cuni.cz/udpipe/models) to run. Get one before initializing the extractor!

```sh
$ pip install pphrase
```

```
import pphrase

functionals = ['без умолку', 'в изобилии', 'во весь дух',  'за деньги']
derivatives = ['без согласования с', 'вблизи ото', 'в преддверье',
               'в одной из', 'лицом к лицу с']

text = 'В одной из отдаленных улиц Москвы, в сером доме с белыми колоннами, \
        антресолью и покривившимся балконом, жила некогда барыня, вдова, \
        окруженная многочисленною дворней. Сыновья ее служили в Петербурге, \
        дочери вышли замуж; она выезжала редко и уединенно доживала последние \
        годы своей скупой и скучающей старости. День ее, нерадостный и ненастный, \
        давно прошел; но и вечер ее был чернее ночи.'

udpipe_model='models/russian-syntagrus-ud-2.4-190531.udpipe'

ex = pphrase.Extractor(udpipe_model=udpipe_model, lang='ru',
                       functionals=function_words,
                       derivative_prepositions=derivative_prepositions)
ex.extract_phrases(text)

>>>   {'в одной из': ['жила в одной из улиц'],
       'в': ['жила в доме', 'служили в петербурге'],
       'с': ['доме с колоннами', 'доме с покривившимся']}
```

#### Todos

 - Add semantic processing
