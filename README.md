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
| normal | 0.813 | 0.786 | 0.800 |
| vertical markovization | 0.840 | 0.829 | 0.835 |
