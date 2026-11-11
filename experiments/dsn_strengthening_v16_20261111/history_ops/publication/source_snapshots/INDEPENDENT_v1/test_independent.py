import unittest,itertools
from independent_verify import distance
class IndependentControls(unittest.TestCase):
 def test_known_unicode(self):
  self.assertEqual(distance('中😀文','中😀国文'),1);self.assertEqual(distance('中😀文','中😀国'),1)
 def test_empty_and_suffix(self):
  self.assertEqual(distance('','abc'),3);self.assertEqual(distance('abc',''),3)
  self.assertEqual(distance('prefixcatsuffix','prefixcutsuffix'),1)
 def test_trimming_against_untrimmed_rolling(self):
  def other(a,b):
   row=list(range(len(b)+1))
   for i,x in enumerate(a,1):
    nxt=[i]
    for j,y in enumerate(b,1):nxt.append(min(row[j]+1,nxt[-1]+1,row[j-1]+(x!=y)))
    row=nxt
   return row[-1]
  words=[''.join(x) for n in range(4) for x in itertools.product('ab',repeat=n)]
  for a in words:
   for b in words:self.assertEqual(distance(a,b),other(a,b))
