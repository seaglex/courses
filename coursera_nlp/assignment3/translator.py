# coding: utf-8
from __future__ import division, print_function, unicode_literals
import argparse
import sys
import numpy as np
import pickle
import math
from collections import defaultdict


def read_corpus(fsrc, fdst):
    corpus_pairs = []
    while True:
        src_line = fsrc.readline()
        dst_line = fdst.readline()
        if not src_line or not dst_line:
            break
        corpus_pairs.append((src_line.split(), dst_line.split()))
    return corpus_pairs


class WordModel(object):
    def __init__(self):
        self.ef_prs = None

    def is_initialized(self):
        return bool(self.ef_prs)

    def update(self, ef_counts):
        prs = {}
        for e, f_cnts in ef_counts.items():
            scale = 1.0 / sum(f_cnts.values())
            prs[e] = {f: cnt*scale for f, cnt in f_cnts.items()}
        self.ef_prs = prs

    def get_pr(self, e, f):
        if not self.ef_prs:
            return 1.0
        f_prs = self.ef_prs.get(e)
        if f_prs:
            return f_prs.get(f, 0.0)
        return 0.0


class MockPositionModel(object):
    def update(self, _):
        pass

    def get_pr(self, el, fm, e_j, f_i):
        return 1.0

class PositionModel(object):
    # fm: french length m
    # el: english length l
    def __init__(self):
        self.fm_el_fe_prs = None

    def update(self, fe_pos_counts):
        fm_el_fe_prs = {}
        for fm, el_fe_cnts in fe_pos_counts.items():
            el_fe_prs = {}
            fm_el_fe_prs[fm] = el_fe_prs
            for el, fe_cnts in el_fe_cnts.items():
                fe_prs = {}
                el_fe_prs[el] = fe_prs
                for f, e_cnts in fe_cnts.items():
                    scale = 1.0 / sum(e_cnts.values())
                    fe_prs[f] = {e: cnt*scale for e, cnt in e_cnts.items()}
        self.fm_el_fe_prs = fm_el_fe_prs

    def get_pr(self, el, fm, e_j, f_i):
        if not self.fm_el_fe_prs:
            return 1.0
        el_fe_prs = self.fm_el_fe_prs.get(fm)
        if not el_fe_prs:
            return 1.0
        fe_prs = el_fe_prs.get(el)
        if not fe_prs:
            return 1.0
        e_prs = fe_prs.get(f_i)
        if not e_prs:
            return 1.0 / (el + 1)
        return e_prs.get(e_j, 0.0)


class IBMModel(object):
    def __init__(self, word_model, pos_model):
        self.word_model = word_model
        self.pos_model = pos_model

    def _update(self, corpus):
        total_cnt = 0
        total_pr = 0
        ef_counts = defaultdict(lambda: defaultdict(int))
        fe_pos_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
        for n, (src, dst) in enumerate(corpus):
            el = len(src)
            fm = len(dst)
            for i, f in enumerate(dst):
                likelihood = np.zeros(el + 1)
                likelihood[0] = self.word_model.get_pr(None, f) * self.pos_model.get_pr(el, fm, 0, i+1)
                for j, e in enumerate(src):
                    likelihood[j+1] = self.word_model.get_pr(e, f) * self.pos_model.get_pr(el, fm, j+1, i+1)
                scale = 1.0 / likelihood.sum()
                deltas = scale * likelihood
                ef_counts[None][f] += deltas[0]
                fe_pos_counts[fm][el][i+1][0] += deltas[0]
                for j, e in enumerate(src):
                    ef_counts[e][f] += deltas[j+1]
                    fe_pos_counts[fm][el][i+1][j+1] += deltas[j+1]
                for j, pr in enumerate(likelihood):
                    if likelihood[j] > 0:
                        total_pr += deltas[j] * math.log(likelihood[j])
                total_cnt += 1
        self.word_model.update(ef_counts)
        self.pos_model.update(fe_pos_counts)
        return math.exp(total_pr / total_cnt)

    def fit(self, corpus, itr_num=5):
        if not self.word_model.is_initialized():
            print("initializing", file=sys.stderr)
            self._update(corpus)
        for itr in range(itr_num):
            print("iteration", itr, "word-pr", file=sys.stderr, end=" ")
            print(self._update(corpus), file=sys.stderr)
        return

    def get_alignment(self, corpus):
        results = []
        for n, (src, dst) in enumerate(corpus):
            el = len(src)
            fm = len(dst)
            for i, f in enumerate(dst):
                max_pr = self.word_model.get_pr(None, f) * self.pos_model.get_pr(el, fm, 0, i+1)
                max_index = 0
                for j, e in enumerate(src):
                    pr = self.word_model.get_pr(e, f) * self.pos_model.get_pr(el, fm, j+1, i+1)
                    if pr > max_pr:
                        max_pr = pr
                        max_index = j + 1
                results.append((n+1, max_index, i + 1))
        return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("fsrc")
    parser.add_argument("fdst")
    parser.add_argument("-s", "--store", default=None)
    parser.add_argument("-l", "--load", default=None)
    parser.add_argument("-u", "--update", action="store_true")
    parser.add_argument("-m", "--model", type=int, default=2)
    args = parser.parse_args()

    if args.load:
        with open(args.load, "rb") as fmodel:
            word_model = pickle.load(fmodel)
    else:
        word_model = WordModel()
    model = None
    if args.model == 1:
        model = IBMModel(word_model, MockPositionModel())
    elif args.model == 2:
        model = IBMModel(word_model, PositionModel())
    else:
        print("Only support model 1 and 2", file=sys.stderr)
        exit()
    with open(args.fsrc) as fsrc:
        with open(args.fdst) as fdst:
            corpus = read_corpus(fsrc, fdst)
            if args.update:
                model.fit(corpus)
            else:
                results = model.get_alignment(corpus)
                for index, e_j, f_i in results:
                    print(index, e_j, f_i)
    if args.store:
        with open(args.store, "wb") as fmodel:
            pickle.dump(word_model, fmodel)
