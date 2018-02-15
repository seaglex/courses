from __future__ import division, print_function
from collections import defaultdict
import argparse
import math


MAX_RARE_COUNT = 4
MIN_LN_PR = -10000.0


def read_counts(fin):
    y_x_counts = defaultdict(lambda :defaultdict(int))
    unigram = defaultdict(int)
    bigram = defaultdict(lambda :defaultdict(int))
    trigram = defaultdict(lambda :defaultdict(lambda :defaultdict(int)))
    while True:
        line = fin.readline()
        if not line:
            break
        elems = line.split()
        t_ = elems[1]
        count = int(elems[0])
        if t_ == "WORDTAG":
            tag = elems[2]
            word = elems[3]
            y_x_counts[tag][word] = count
        elif t_ == "1-GRAM":
            unigram[elems[2]] = count
        elif t_ == "2-GRAM":
            bigram[elems[2]][elems[3]] = count
        elif t_ == "3-GRAM":
            trigram[elems[2]][elems[3]][elems[4]] = count
        else:
            print("Unknown line:", line)
            raise Exception("unknown line %s" % line)
    return y_x_counts, unigram, bigram, trigram


def read_seqs(fin):
    xs = []
    while True:
        line = fin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            if xs:
                yield xs
                xs = []
            continue
        xs.append(line)
    if not xs:
        yield xs


class TransitionModel(object):
    def __init__(self, unigram, bigram, trigram):
        self.unigram = unigram
        self.bigram = bigram
        self.trigram = trigram

    def get_ln_pr(self, states, state):
        last2_s, last_s = states
        numerator = self.trigram[last2_s][last_s][state]
        denominator = self.bigram[last2_s][last_s]
        if not numerator:
            return MIN_LN_PR
        return math.log(numerator / denominator)


class EmissionModel1(object):
    def __init__(self, y_x_counts):
        self.y_total_counts = {
            y: sum(x_cnts.values()) for y, x_cnts in y_x_counts.items()
        }
        self.common_words, self.y_rare_counts = EmissionModel1.replace_rare(y_x_counts)
        self.y_x_counts = y_x_counts

    @staticmethod
    def replace_rare(y_x_counts):
        x_total_counts = defaultdict(int)
        for y, x_counts in y_x_counts.items():
            for x, cnt in x_counts.items():
                x_total_counts[x] += cnt
        common_words = set()
        for x, cnt in x_total_counts.items():
            if cnt > MAX_RARE_COUNT:
                common_words.add(x)
        # replace
        y_rare_counts = defaultdict(int)
        for y, x_counts in y_x_counts.items():
            total_cnt = 0
            for x, cnt in x_counts.items():
                if x not in common_words:
                    total_cnt += cnt
            y_rare_counts[y] = total_cnt
        return common_words, y_rare_counts

    def get_ln_pr(self, y, x):
        numerator = self.y_x_counts[y][x]
        if x not in self.common_words:
            numerator = self.y_rare_counts[y]
        if not numerator:
            return MIN_LN_PR
        return math.log(numerator / self.y_total_counts[y])


class EmissionModel2(object):
    def __init__(self, y_x_counts):
        self.y_total_counts = {
            y: sum(x_cnts.values()) for y, x_cnts in y_x_counts.items()
        }
        self.y_x_counts = y_x_counts
        self.common_words, self.y_rare_counts = EmissionModel2.count_rare(y_x_counts)

    @staticmethod
    def categorize_rare_words(word):
        for x in word:
            if x.isdigit():
                return 'numeric_'
        if word.isupper():
            return "all_capitals_"
        if word[-1].isupper():
            return "last_capital_"
        return "rare_"

    @staticmethod
    def count_rare(y_x_counts):
        x_total_counts = defaultdict(int)
        for y, x_counts in y_x_counts.items():
            for x, cnt in x_counts.items():
                x_total_counts[x] += cnt
        common_words = set()
        for x, cnt in x_total_counts.items():
            if cnt > MAX_RARE_COUNT:
                common_words.add(x)
        # replace rare words
        y_rare_counts = {}
        for y, x_counts in y_x_counts.items():
            c_counts = defaultdict(int)
            for x, cnt in x_counts.items():
                if x not in common_words:
                    category = EmissionModel2.categorize_rare_words(x)
                    c_counts[category] += cnt
            y_rare_counts[y] = c_counts
        return common_words, y_rare_counts

    def get_ln_pr(self, y, x):
        if x in self.common_words:
            numerator = self.y_x_counts[y][x]
        else:
            numerator = self.y_rare_counts[y][EmissionModel2.categorize_rare_words(x)]
        denominator = self.y_total_counts[y]
        if numerator:
            return math.log(numerator / denominator)
        return MIN_LN_PR


class NaiveDecoder(object):
    def __init__(self, states, emission_model):
        self.states = states
        self.emission_model = emission_model

    def decode(self, xs):
        ys = [None] * len(xs)
        for index, x in enumerate(xs):
            max_lnpr = None
            max_s = None
            for s in self.states:
                lnpr = self.emission_model.get_ln_pr(s, x)
                if max_lnpr is None or max_lnpr < lnpr:
                    max_lnpr = lnpr
                    max_s = s
            ys[index] = max_s
        return ys


class ViterbiDecoder(object):
    STATE_STOP = "STOP"
    def __init__(self, states, transition_model, emission_model):
        self.states = states
        self.transition_model = transition_model
        self.emission_model = emission_model

    def decode(self, xs):
        last_lnprs = {("*", "*"): 1.0}
        back_traces = []
        for x in xs:
            s_x_lgprs = {}
            for s in self.states:
                s_x_lgprs[s] = self.emission_model.get_ln_pr(s, x)
            max_states = {}
            max_lgprs = {}
            for last_s, last_lnpr in last_lnprs.items():
                for s in self.states:
                    new_s = (last_s[-1], s)
                    lnpr = last_lnpr + self.transition_model.get_ln_pr(last_s, s) + s_x_lgprs[s]
                    if new_s not in max_lgprs or max_lgprs[new_s] < lnpr:
                        max_lgprs[new_s] = lnpr
                        max_states[new_s] = last_s
            last_lnprs = max_lgprs
            back_traces.append(max_states)
        # end of states
        max_s = None
        max_lgpr = None
        for last_s, last_lnpr in last_lnprs.items():
            lnpr = last_lnpr + self.transition_model.get_ln_pr(last_s, self.STATE_STOP)
            if max_lgpr is None or max_lgpr < lnpr:
                max_lgpr = lnpr
                max_s = last_s
        # back-trace
        results = []
        for last_states in reversed(back_traces):
            results.append(max_s[-1])
            max_s = last_states[max_s]
        return list(reversed(results))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("fcount")
    parser.add_argument("fseq")
    parser.add_argument("-t", "--transition", action="store_true")
    parser.add_argument("-c", "--category", action="store_true")
    args = parser.parse_args()
    fn_count = args.fcount
    fn_seq = args.fseq
    with open(fn_count) as fin:
        y_x_counts, unigram, bigram, trigram = read_counts(fin)
    transition_model = TransitionModel(unigram, bigram, trigram)
    if not args.category:
        emission_model = EmissionModel1(y_x_counts)
    else:
        emission_model = EmissionModel2(y_x_counts)
    if not args.transition:
        decoder = NaiveDecoder(list(unigram.keys()), emission_model)
    else:
        decoder = ViterbiDecoder(list(unigram.keys()), transition_model, emission_model)
    with open(fn_seq) as fin:
        for xs in read_seqs(fin):
            ys = decoder.decode(xs)
            assert len(xs) == len(ys)
            for n, x in enumerate(xs):
                print(x, ys[n])
            print()
        fin.close()
