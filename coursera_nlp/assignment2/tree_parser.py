# coding: utf8
from __future__ import print_function, division, generators, unicode_literals
from collections import defaultdict
import math
import argparse
import json


MAX_RARE_COUNT = 4
MIN_LN_PR = -1000


def read_counts(fin):
    nonterminal_counts = defaultdict(int)
    binary_rules = defaultdict(lambda: defaultdict(int))
    unary_rules = defaultdict(lambda: defaultdict(int))
    while True:
        line = fin.readline()
        if not line:
            break
        elems = line.split()
        cnt = int(elems[0])
        if elems[1] == "NONTERMINAL":
            nonterminal_counts[elems[2]] = cnt
        elif elems[1] == "BINARYRULE":
            binary_rules[elems[2]][(elems[3], elems[4])] = cnt
        elif elems[1] == "UNARYRULE":
            unary_rules[elems[2]][elems[3]] = cnt
    return nonterminal_counts, binary_rules, unary_rules


def read_seqs(fin):
    while True:
        line = fin.readline()
        if not line:
            break
        yield line.split()


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

    def get_state_ln_prs(self, x):
        if x not in self.common_words:
            return {
                y: math.log(cnt/self.y_total_counts[y]) if cnt > 0 else MIN_LN_PR
                for y, cnt in self.y_rare_counts.items()
            }
        return {
            y: math.log(self.y_x_counts[y][x] / total_cnt) if self.y_x_counts[y][x] > 0 else MIN_LN_PR
            for y, total_cnt in self.y_total_counts.items()
        }


class BinaryModel(object):
    def __init__(self, nonterminal_counts, binary_rules):
        self.binary_rules = binary_rules
        self.nontermianl_counts = nonterminal_counts
        self.rule_ln_prs = {
            src: {k: math.log(cnt/nonterminal_counts[src]) for k, cnt in dst.items()}
            for src, dst in binary_rules.items()
        }

    def get_rule_ln_prs(self, t):
        return self.rule_ln_prs.get(t, {})

    def get_rules(self):
        return self.rule_ln_prs

class TreeParser(object):
    S_TAG = "SBARQ"
    def __init__(self, binary_model, unary_model):
        self.binary_model = binary_model
        self.unary_model = unary_model

    def parse(self, xs):
        num = len(xs)
        # π(n, m, non-terminal) represents that non-terminal spans [n, m], inclusively
        pi_ln_prs = [[{} for n in range(num)] for m in range(num)]
        back_traces = [[{} for n in range(num)] for m in range(num)]
        # init
        for n, x in enumerate(xs):
            pi_ln_prs[n][n] = {
                k: v for k, v in self.unary_model.get_state_ln_prs(x).items() if v > MIN_LN_PR
            }
        # recursive
        rule_ln_prs = self.binary_model.get_rules()
        for length in range(2, num+1):
            for beg in range(0, num-length+1):
                max_ln_prs = {}
                max_derivations = {}
                for end in range(beg+1, beg+length):
                    # left [beg: end-1]
                    # right [end: beg+length-1]
                    for high, low_ln_prs in rule_ln_prs.items():
                        for (y1, y2), d_ln_pr in low_ln_prs.items():
                            left_ln_pr = pi_ln_prs[beg][end-1].get(y1)
                            if left_ln_pr is None:
                                continue
                            right_ln_pr = pi_ln_prs[end][beg+length-1].get(y2)
                            if right_ln_pr is None:
                                continue
                            ln_pr = d_ln_pr + left_ln_pr + right_ln_pr
                            if high not in max_ln_prs or max_ln_prs[high] < ln_pr:
                                max_ln_prs[high] = ln_pr
                                max_derivations[high] = (y1, y2, beg, end, beg+length)
                pi_ln_prs[beg][beg+length-1] = max_ln_prs
                back_traces[beg][beg+length-1] = max_derivations
        # result
        if TreeParser.S_TAG not in pi_ln_prs[0][num-1]:
            raise "illegal grammer for %s" + " ".join(xs)
        return TreeParser._get_tree(back_traces, xs, 0, num, TreeParser.S_TAG)

    @staticmethod
    def _get_tree(back_traces, xs, beg, end, tag):
        bp = back_traces[beg][end-1].get(tag)
        if not bp:
            assert beg+1 == end
            return [tag, xs[beg]]
        y1, y2, b, m, e = bp
        return [
            tag,
            TreeParser._get_tree(back_traces, xs, b, m, y1),
            TreeParser._get_tree(back_traces, xs, m, e, y2),
        ]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("fcount")
    parser.add_argument("fseq")
    args = parser.parse_args()
    fn_count = args.fcount
    fn_seq = args.fseq
    with open(fn_count) as fin:
        nonterminal_counts, binary_rules, unary_rules = read_counts(fin)
    binary_model = BinaryModel(nonterminal_counts, binary_rules)
    emission_model1 = EmissionModel1(unary_rules)
    parser = TreeParser(binary_model, emission_model1)
    with open(fn_seq) as fin:
        for xs in read_seqs(fin):
            tree = parser.parse(xs)
            print(json.dumps(tree))
        fin.close()