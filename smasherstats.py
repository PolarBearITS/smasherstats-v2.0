#Standard Library
import json
import re
import sys
import codecs
from collections import *
from datetime import datetime
from contextlib import redirect_stdout

#Dependencies
import requests
from bs4 import BeautifulSoup as bsoup

class SmasherStats:
	def __init__(self, tags):
		self.CUR_YEAR = datetime.now().year
		self.tags = tags
		self.game = ''
		self.event = ''
		try:
			assert(isinstance(self.tags, list))
		except AssertionError:
			print('TagError: Make sure your tags are passsed as a list.')

	def getResults(self, game, event, year=0, year2=0, format=''):
		total_results = {}
		self.game = game
		self.event = event
		for tag in self.tags:
			page = requests.get(f'http://www.ssbwiki.com/{tag}')
			soup = bsoup(page.content, 'html.parser')
			tables = soup.find_all('div', {'id': 'mw-content-text'})[0].contents[2].contents[1].contents[1]
			for header in tables.find_all('h3'):
				if game in header.contents[0].text:
					tables = tables.contents[tables.index(header) + 2]
					break
			tables.contents = [t for t in tables.contents if t != '\n']
			player_results = {}
			for row in tables.contents[1:]:
				row.contents = [r for r in row.contents if r != '\n']
				result = [r.text.strip('\n').strip(' ') for r in row.contents]
				keys = ['date']
				if event == 'singles':
					result = result[:-2]
					keys.append('singles')
				elif event == 'doubles':
					result = result[:-3] + result[-2:]
					keys.extend(('doubles', 'partner'))
				else:
					keys.extend(('singles', 'doubles', 'partner'))
				info = {}
				for i, key in enumerate(keys):
					info[key] = result[1:][i]
				player_results[result[0]] = info
			total_results[tag] = player_results
		if type(year) == int:
			total_results = self.filterResultsByYear(total_results, year, year2)
		if format == 'json':
			total_results = json.dumps(total_results, indent=4, ensure_ascii=False)
		return total_results

	def checkResults(self, total_results):
		try:
			assert(isinstance(total_results, dict))
		except AssertionError:
			try:
				total_results = json.loads(total_results)
			except ValueError:
				print('TagError: Make sure your results are passsed as a dictionary or JSON, with keys being tags and values being dictionaries of results.')
		return total_results

	def filterResultsByYear(self, total_results, year, year2=0):
		new_results = {}
		for tag, results, in total_results.items():
			new_tourneys = {}
			for tourney, info in results.items():
				tYear = int(info['date'][-4:])
				if year == 0:
					year = self.CUR_YEAR
				if year2 == 0:
					if tYear == year:
						new_tourneys[tourney] = info
				else:
					if year <= tYear <= year2:
						new_tourneys[tourney] = info
			new_results[tag] = new_tourneys
		return new_results

	def countResults(self, total_results):
		counts = {}
		total_results = self.checkResults(total_results)
		for tag, results in total_results.items():
			place_counts = defaultdict(list)
			for tourney, info in results.items():
				year = info['date'][-4:]
				if year not in tourney:
					tourney += f' ({year})'
				key = re.match('\d+', info['singles'])
				if key:
					key = key.group(0)
					place_counts[key].append(tourney)
			counts[tag] = dict(place_counts)
		return counts

	def prettifyResults(self, total_results):
		text = ''
		total_results = self.countResults(total_results)
		for tag, results in total_results.items():
			title = f'{tag}\'s {self.game} {self.event} results:'
			text += title + '\n' + '-'*len(title) + '\n'
			for place, counts in sorted(results.items()):
				text += f'{place} - {len(counts)}\n'
				for tourney in counts:
					text += f' - {tourney}\n'
				text += '\n'
			text += '\n'
		return text

	def outputResults(self, r, file=''):
		f = ''
		if file == '':
			f = sys.stdout
		else:
			f = open(file, 'a+', encoding='utf-8')
			if r in open(file).read():
				print('Results already in file.')
				return
		with f: f.write(r)
s = SmasherStats(['Mang0', 'Armada'])
r = s.getResults('Melee', event='singles', year='all')
t = s.prettifyResults(r)
s.outputResults(t)