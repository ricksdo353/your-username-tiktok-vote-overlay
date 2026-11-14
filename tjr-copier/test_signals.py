import unittest
from signals import detect

def kinds(t): return [(k, s) for k, s, _ in detect(t)]

class T(unittest.TestCase):
    def test_entries(self):
        self.assertEqual(kinds("Okay I'm long here"), [("entry", "long")])
        self.assertEqual(kinds("we’re short, stop above the high"), [("entry", "short")])
        self.assertEqual(kinds("just entered a long on NQ"), [("entry", "long")])
        self.assertEqual(kinds("I shorted that"), [("entry", "short")])
        self.assertEqual(kinds("I just got long"), [("entry", "long")])
    def test_ignored(self):
        for t in ["if I'm long here I want the FVG", "I'm not long yet", "I would be long if it sweeps",
                  "looking to get long", "how long is this", "I was long yesterday", "I'm looking to go short",
                  "we want to get short here", "don't short this"]:
            self.assertEqual(kinds(t), [], t)
    def test_exits(self):
        for t in ["got stopped out", "I'm out", "we're flat now", "hit my TP", "target hit", "I closed it", "took profit"]:
            self.assertEqual(kinds(t), [("exit", None)], t)
        self.assertEqual(kinds("I'm not out yet"), [])

if __name__ == "__main__":
    unittest.main()
