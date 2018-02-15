#! /usr/bin/python
#coding: utf-8

__author__="Alexander Rush <srush@csail.mit.edu>"
__date__ ="$Sep 12, 2012"

import sys, json

"""
Count rule frequencies in a binarized CFG.
"""

class Counts:
  def __init__(self):
    self.unary = {}
    self.binary = {} 
    self.nonterm = {}

  def show(self):
    for symbol, count in self.nonterm.iteritems():
      print count, "NONTERMINAL", symbol

    for (sym, word), count in self.unary.iteritems():
      print count, "UNARYRULE", sym, word

    for (sym, y1, y2), count in self.binary.iteritems():
      print count, "BINARYRULE", sym, y1, y2

  def count(self, tree): #存储的数据中有［sym＋sym，word］的形式
    """
    Count the frequencies of non-terminals and rules in the tree.
    """
    #这个if有和没有一样，因为已经将只有一个symbol连接另一个symbol，然后一个word的
    #改成［‘symbol＋symbol’， ‘string’］的形式了
    if isinstance(tree, basestring): 
      #print("basestring, %s\n" % tree)
      return 
    #judge the instance(tree) is a string or not
    #if tree is string, it means the last UNARYRULE

    # Count the non-terminal symbol. 
    symbol = tree[0] #start symbol -> S
    self.nonterm.setdefault(symbol, 0) 
    #insert the dict item: (symbol, 0), if exists, return the value.
    self.nonterm[symbol] += 1
    
    if len(tree) == 3:
      # It is a binary rule.
      y1, y2 = (tree[1][0], tree[2][0])
      key = (symbol, y1, y2)
      self.binary.setdefault(key, 0)
      self.binary[(symbol, y1, y2)] += 1
      
      # Recursively count the children.
      self.count(tree[1])
      self.count(tree[2])
    elif len(tree) == 2:
      # It is a unary rule.
      y1 = tree[1]
      key = (symbol, y1)
      self.unary.setdefault(key, 0)
      self.unary[key] += 1
      #self.count(tree[1])，如果这样，那么35-37行code有用
      #self.count(tree[2])，因为考虑［‘symbol’，［‘symbol‘，’string'］］的情况

def main(parse_file):
  counter = Counts() 
  for l in open(parse_file):
    t = json.loads(l)
    counter.count(t)
  counter.show()

def usage():
    sys.stderr.write("""
    Usage: python count_cfg_freq.py [tree_file]
        Print the counts of a corpus of trees.\n""")

if __name__ == "__main__": 
  if len(sys.argv) != 2:
    usage()
    sys.exit(1)
  main(sys.argv[1])
  
