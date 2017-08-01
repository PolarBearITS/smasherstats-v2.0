import requests
import json
import re
from bs4 import BeautifulSoup as bsoup
from datetime import datetime

class SmasherStats:
	def __init__(self, tags):
		self.CUR_YEAR = datetime.now().year
		self.tags = tags
		try:
			assert(isinstance(self.tags, list))
		except AssertionError:
			print('TagError: Make sure your tags are passsed as a list.')

	def getResults(self, game, year=0, event='', format=''):
		total_results = {}
		if year == 0:
			year = self.CUR_YEAR
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
				name = result[0]
				info = {}
				for i in range(len(keys)):
					info[keys[i]] = result[1:][i]
				player_results[result[0]] = info
			total_results[tag] = player_results
		if format == 'json':
			total_results = json.dumps(total_results, indent=4, ensure_ascii=False)
		return total_results

	def filterResultsByYear(self, total_results, year, year2=0):
		pass

	def printResults(self, total_results):
		try:
			assert(isinstance(total_results, dict))
		except AssertionError:
			try:
				total_results = json.loads(total_results)
			except ValueError:
				print('TagError: Make sure your results are passsed as a dictionary or JSON, with keys being tags and values being dictionaries of results.')
		for tag, results in total_results.items():
			place_counts = {}
			places = []
			for tourney, info in results.items():
				place = info['singles']
				p = re.match('\d', place)
				t = tourney
				year = info['date'][-4:]
				if year not in t:
					t += f' ({year})'
				if p:
					place = p.group(0)
				if place not in place_counts:
					place_counts[place] = [1, [t]]
				else:
					place_counts[place][0] += 1
					place_counts[place][1].append(t)
			# for place in places:
			# 	if place not in place_counts:
			# 		place_counts[place] = places.count(place)
			from pprint import pprint
			pprint(place_counts)


s = SmasherStats(['Mang0'])
r = s.getResults('Melee', event='singles', format='json')
s.printResults(r)