This repo is the assignments of my online courses.

### Coursera NLP (Michael Collins)

#### Assignment 1 - Gene tagging
 - It's a simplified tagging problem
   - Only 2 tags (I-Gene, O)
 - Solution
   - HMM

| dev-scores | precision | recall | F1-score |
|-------|-------|------|-------|
| emission model | 0.158861 | 0.660436 | 0.256116 |
| + transition model | 0.541555 | 0.314642 | 0.398030 |
| + categorized rare | 0.534940 | 0.345794 | 0.420057 |

#### Assignment 2 - Treebank parsing
 - It's Chomsky norm form grammer
 - Solution
   - CYK dynamic programming algorithm

| dev-scores | precision | recall | F1-score |
|-------|-------|------|-------|
| normal                 | 0.813 | 0.786 | 0.800 |
| vertical markovization | 0.840 | 0.829 | 0.835 |

#### Assignment 3 - translation
 - IBM translation model
 - No language model included
 - The word alignment is tested instead of translation quality
 - Commands
   - python translator.py -s results/ibm1.model -u -m 1 data/corpus.en  data/corpus.es
   - python translator.py -l results/ibm1.model data/dev.en data/dev.es > results/dev.p1.out
   - python translator.py -l results/ibm1.model -s results/ibm2.model -u -m 2 data/corpus.en  data/corpus.es
   - python translator.py -l results/ibm2.model data/dev.en data/dev.es > results/dev.p2.out

| dev-scores | precision | recall | F1-score |
|-------|-------|------|-------|
| IBM-1 | 0.419 | 0.432 | 0.425 |
| IBM-2 | 0.431 | 0.445 | 0.438 |
