from __future__ import division, print_function, generators
from collections import defaultdict
import argparse
import sys


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


def read_seq_tags(fin):
    xs = []
    tags = []
    while True:
        line = fin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            if xs:
                yield xs, tags
                xs = []
                tags = []
            continue
        elems = line.split()
        assert len(elems) == 2
        xs.append(elems[0])
        tags.append(elems[1])
    if not xs:
        yield xs, tags


class GLM(object):
    def __init__(self):
        self.weights = {}

    def load(self, fin):
        self.weights = {}
        for line in fin.readlines():
            elems = line.split()
            self.weights[elems[0]] = float(elems[1])
        return

    def store(self, fout):
        for k, v in self.weights.items():
            print(k, v, file=fout)
        return

    def predict(self, features):
        return sum(self.weights.get(f, 0.0) for f in features)


class PreTrainedModel(object):
    def __init__(self, glm):
        self.glm = glm

    @staticmethod
    def get_features(last_state, state, index, xs):
        features = ["TRIGRAM:%s:%s:%s" % (last_state[0], last_state[1], state)]
        if index >= len(xs):
            return features
        features.append("TAG:%s:%s" % (xs[index], state))
        return features

    def get_score(self, last_state, state, index, xs):
        return self.glm.predict(self.get_features(last_state, state, index, xs))


class SuffixModel(object):
    def __init__(self, glm):
        self.glm = glm

    @staticmethod
    def get_features(last_state, state, index, xs):
        features = PreTrainedModel.get_features(last_state, state, index, xs)
        if index >= len(xs):
            return features
        x = xs[index]
        for j in range(1, min(len(xs[index]) + 1, 4)):
            features.append("SUFFIX:%d:%s:%s" % (j, x[-j:], state))
        return features

    def get_all_features(self, xs, ys):
        last_state = ("*", "*")
        all_features = defaultdict(float)
        for n, x in enumerate(xs):
            features = SuffixModel.get_features(last_state, ys[n], n, xs)
            for f in features:
                all_features[f] += 1
            last_state = (last_state[-1], ys[n])
        features = SuffixModel.get_features(last_state, ViterbiDecoder.STATE_STOP, len(xs), xs)
        for f in features:
            all_features[f] += 1
        return all_features

    def get_score(self, last_state, state, index, xs):
        return self.glm.predict(self.get_features(last_state, state, index, xs))

    def update(self, best_features, gold_features):
        for f, v in best_features.items():
            w = self.glm.weights.get(f, 0)
            self.glm.weights[f] = w - v
        for f, v in gold_features.items():
            w = self.glm.weights.get(f, 0)
            self.glm.weights[f] = w + v

class ViterbiDecoder(object):
    STATE_STOP = "STOP"
    def __init__(self, states, model):
        self.states = states
        self.model = model

    def decode(self, xs):
        last_lnprs = {("*", "*"): 0.0}
        back_traces = []
        for k, x in enumerate(xs):
            max_states = {}
            max_lgprs = {}
            for last_s, last_lnpr in last_lnprs.items():
                for s in self.states:
                    new_s = (last_s[-1], s)
                    lnpr = last_lnpr + self.model.get_score(last_s, s, k, xs)
                    if new_s not in max_lgprs or max_lgprs[new_s] < lnpr:
                        max_lgprs[new_s] = lnpr
                        max_states[new_s] = last_s
            last_lnprs = max_lgprs
            back_traces.append(max_states)
        # end of states
        max_s = None
        max_lgpr = None
        for last_s, last_lnpr in last_lnprs.items():
            lnpr = last_lnpr + self.model.get_score(last_s, self.STATE_STOP, len(xs), xs)
            if max_lgpr is None or max_lgpr < lnpr:
                max_lgpr = lnpr
                max_s = last_s
        # back-trace
        results = []
        for last_states in reversed(back_traces):
            results.append(max_s[-1])
            max_s = last_states[max_s]
        return list(reversed(results))


class GLMTrainer(object):
    def __init__(self, model):
        self.model = model

    def fit(self, corpus, itr_num=5):
        decoder = ViterbiDecoder(["O", "I-GENE"], self.model)
        for itr in range(itr_num):
            total_cnt = 0
            total_accuracy = 0.0
            for xs, tags in corpus:
                gold_features = self.model.get_all_features(xs, tags)
                ys = decoder.decode(xs)
                best_features = self.model.get_all_features(xs, ys)
                self.model.update(best_features, gold_features)
                total_cnt += len(xs)
                total_accuracy += sum(tag==ys[n] for n, tag in enumerate(tags))
            print("Itr", itr, "Accuracy", total_accuracy / total_cnt, file=sys.stderr)
        return self.model


def load_decode(fn_load, fn_seq):
    glm = GLM()
    if fn_load:
        with open(args.load) as fin:
            glm.load(fin)
    decoder = ViterbiDecoder(["O", "I-GENE"], SuffixModel(glm))
    with open(fn_seq) as fin:
        for xs in read_seqs(fin):
            ys = decoder.decode(xs)
            assert len(xs) == len(ys)
            for n, x in enumerate(xs):
                print(x, ys[n])
            print()
        fin.close()


def train_store(fn_seq_tag, fn_store):
    with open(fn_seq_tag) as fin:
        seq_tags = list(read_seq_tags(fin))
        trainer = GLMTrainer(SuffixModel(GLM()))
        model = trainer.fit(seq_tags)
        with open(fn_store, "w") as fout:
            model.glm.store(fout)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--load")
    parser.add_argument("-s", "--store")
    parser.add_argument("fseq")
    args = parser.parse_args()

    if args.load:
        load_decode(args.load, args.fseq)
    elif args.store:
        train_store(args.fseq, args.store)
