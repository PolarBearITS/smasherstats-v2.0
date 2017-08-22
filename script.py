import sys
from smasherstats import SmasherStats

s = SmasherStats(sys.argv[3:])
s.getResults(sys.argv[1], sys.argv[2])
s.prettifyResults()
s.outputData()