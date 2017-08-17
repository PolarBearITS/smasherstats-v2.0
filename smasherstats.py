# Standard Library
import codecs
import json
import pickle
import re
import sys
from collections import defaultdict
from datetime import datetime

# Dependencies
import pysmash
import requests
from prettytable import PrettyTable, ALL
from bs4 import BeautifulSoup as bsoup

smash = pysmash.SmashGG()


class SmasherStats:
	def __init__(self, tags):
		self.CUR_YEAR = datetime.now().year
		self.tags = tags
		self.game = ''
		self.event = ''
		self.format = ''
		self.year_range = []

		self.total_results = {}
		self.pretty_results = ''

		self.total_records = {}
		self.pretty_records = ''
		self.set_counts = dict((tag, 0) for tag in self.tags)
		self.game_counts = dict((tag, 0) for tag in self.tags)

		self.set_table = {}
		try:
			assert(isinstance(self.tags, list))
		except AssertionError:
			print('TagError: Make sure your tags are passsed as a list.')

	def getResults(self, game, event, year=0, year2=0, results_format='', types = ''):
		total_results = {}
		self.game = game
		self.event = event
		self.format = results_format
		results_filter = False
		if isinstance(year, str):
			if year.lower() != 'all':
				raise ValueError("Make sure you pass in the year either as an integer or as 'all'")
		elif isinstance(year, int):
			results_filter = True
			if year == 0:
				self.year_range = [self.CUR_YEAR]
			else:
				self.year_range = [year]
				if year2 != 0:
					self.year_range.append(year2)
		if not isinstance(year2, int):
			raise ValueError("Make sure you pass in the second year as an integer")
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
				result = [r.text.strip('\n').strip(' ') for r in row.contents if r != '\n']
				keys = []
				if event == 'singles':
					result = result[:-2]
					keys = ['singles']
				elif event == 'doubles':
					result = result[:2] + result[-2:]
					keys = ['doubles', 'partner']
				keys = ['date'] + keys
				try:
					assert(any(c.isdigit() for c in result[2]))
					info = {}
					for i, key in enumerate(keys):
						info[key] = result[1:][i]
					player_results[result[0]] = info
				except:
					continue
			total_results[tag] = player_results

		self.total_results = total_results

		if results_filter:
			self.filterResultsByYear()

		if self.format == 'json':
			return json.dumps(self.total_results, indent=4, ensure_ascii=False)
		
		return self.total_results

	def checkResults(self):
		try:
			assert(isinstance(self.total_results, dict))
		except AssertionError:
			# if self.format == 'json':
			# 	self.total_results = json.loads(self.total_results)
			# else:
			print('TagError: Make sure your results are passsed as a dictionary or JSON, with keys being tags and values being dictionaries of results.')
			return False
		return True

	def filterResultsByYear(self):
		new_results = {}
		for tag, results, in self.total_results.items():
			new_tourneys = {}
			for tourney, info in results.items():
				if int(info['date'][-4:]) in list(range(self.year_range[0], self.year_range[-1]+1)):
					new_tourneys[tourney] = info
			new_results[tag] = new_tourneys

		self.total_results = new_results

		return self.total_results

	def countResults(self):
		counts = {}
		self.checkResults()
		for tag, results in self.total_results.items():
			place_counts = defaultdict(list)
			for tourney, info in results.items():
				year = info['date'][-4:]
				if year not in tourney and len(self.year_range) != 1:
					tourney += f' ({year})'
				if self.event == 'doubles':
					tourney += f' \n\t{info["partner"]}'
				key = re.match('\d+', info[self.event])
				if key:
					key = int(key.group(0))
					place_counts[key].append(tourney)
			counts[tag] = dict(place_counts)
		return counts

	def prettifyResults(self):
		text = ''
		endings = ['th', 'st', 'nd', 'rd'] + ['th']*6
		counts = self.countResults()
		for tag, results in list(counts.items()):
			title = f'{tag}\'s {self.game} {self.event} results'
			if len(self.year_range) == 1:
				title += f' for {self.year_range[0]}:'
			elif len(self.year_range) == 2:
				str_range = ' through '.join(map(str, self.year_range))
				title += f' from {str_range}:'
			else:
				title += ':'
			text += '-'*(len(title)+2) + '\n ' + title + '\n' + '-'*(len(title)+2) + '\n'
			for place, counts in sorted(results.items()):
				text += f'{place}{endings[place % 10]} - {len(counts)}\n'
				for tourney in counts:
					text += f' - {tourney}\n'
				text += '\n'
		self.pretty_results = text
		return self.pretty_results

	def getRecords(self, game, event, year=0, year2=0):
		if len(self.tags) > 2:
			raise Exception("Records can only be retrieved for 1 or 2 players; no more, no less.")
		self.getResults(game, event, year, year2)
		tourneys = []
		for tag, results in self.total_results.items():
			tourneys.append([tourney for tourney in results])
		if len(self.tags) == 1:
			tourneys = tourneys[0]
		elif len(self.tags) == 2:
			tourneys = [t for t in tourneys[0] if t in tourneys[1]]

		slugs = {}
		with open('slugs.pk', 'rb') as s:
			slugs = pickle.load(s)

		event_slugs = [self.getEventSlug(game, event), 
					   self.getEventSlug(game, event) + '-1', 
					   '-'.join(['super', 'smash', 'bros'] + ['for']*(game=='Wii U') + [game.lower()])]

		records = []

		for i, tourney in enumerate(tourneys):
			ret = f'Retrieving tournament {i+1}/{len(tourneys)}'
			self.std_flush(ret + '.  ')

			slug = ''
			newSlug = False
			newSuccessfulSlug = False

			if tourney in slugs:
				slug = slugs[tourney]
			else:
				slug = self.getTourneySlug(tourney)
				newSlug = True

			for event_slug in event_slugs:
				try:
					t = smash.tournament_show_event_brackets(slug, event_slug)
					if newSlug:
						slugs[tourney] = slug
						newSuccessfulSlug = True
					break
				except Exception as e:
					continue
			else:
				# print(tourney)
				if tourney not in open('failed_slugs.txt', 'r', encoding='utf-8').read():
					with open('failed_slugs.txt', 'a+', encoding='utf-8') as f:
						f.write(tourney + '\n')

			self.std_flush(ret + '.. ')

			for bracket in reversed(t['bracket_ids']):
				players = smash.bracket_show_players(bracket)
				self.std_flush(ret + '...')
				final_bracket = False
				ltags = list(map(str.lower, self.tags))
				if set(ltags).issubset((p['tag'].lower() for p in players)):
					player_ids = {str(p['entrant_id']):p['tag'] for p in players}
					ids = [i for i, player in player_ids.items() if player.lower() in ltags]
					# print(ids)
					sets = smash.bracket_show_sets(bracket)
					found = False
					for match in sets:
						entrants = [match['entrant_1_id'], match['entrant_2_id']]
						win_counts = [match['entrant_1_score'], match['entrant_2_score']]
						if all(i in entrants for i in ids):
							found = True
							if ids[0] != entrants[0]:
								entrants.reverse()
								win_counts.reverse()

							record = [tourney, match['full_round_text']]
							if any(round in match['full_round_text'].lower() for round in ['winner', 'pools']):
								final_bracket = True
							
							outcome = ''
							if len(self.tags) == 1:
								tag = player_ids[match['entrant_1_id']]
								if tag.lower() == ltags[0]:
									tag = player_ids[match['entrant_2_id']]
								record.append(tag)
								if ids[0] == match['winner_id']:
									outcome = 'WIN'
								else:
									outcome = 'LOSS'
							else:
								num_winner = ids.index(match['winner_id'])
								outcome = self.tags[num_winner]
								self.set_counts[outcome] += 1
								self.game_counts = dict((pair[0], pair[1]+win_counts[i]) for i, pair in enumerate(self.game_counts.items()))
							record += [win_counts, outcome]
							records.append(record)
					if not found:
						break
				if final_bracket:
					break

		if newSuccessfulSlug:
			with open('slugs.pk', 'wb') as s:
				pickle.dump(slugs, s)

		self.total_records = records
		return self.total_records
			
	def getTourneySlug(self, name):
		return '-'.join(re.sub(r'\'|\"', '', name.lower()).split())

	def getEventSlug(self, game, event):
		return '-'.join(game.lower().split()) + '-' + event.lower()

	def prettifyRecords(self):
		pt = PrettyTable()
		fnames = ['Tournament', 'Round']
		if len(self.tags) == 1:
			fnames += [f'{self.tags[0]} vs. ↓', 'Score', 'Outcome']
		else:
			fnames += [' vs. '.join(self.tags), 'Winner']
		pt.field_names = fnames

		for i, record in enumerate(self.total_records):
			pretty_record = record.copy()
			if i != 0:
				if self.total_records[i-1][0] == record[0]:
					pretty_record[0] = ''
				else:
					pt.add_row(['']*len(pt.field_names))
			pt.add_row([' - '.join(map(str, rec)) if isinstance(rec, list) else rec for rec in pretty_record])

		s_counts = list(list(map(str, s)) for s in self.set_counts.items())
		g_counts = list(list(map(str, g)) for g in self.game_counts.items())
		extra = 'Total Set Count: ' + ' '.join(s_counts[0]) + ' - ' + ' '.join(reversed(s_counts[1])) + '\n'
		extra += 'Total Game Count: ' + ' '.join(g_counts[0]) + ' - ' + ' '.join(reversed(g_counts[1])) + '\n'
		self.pretty_records = pt.get_string() + '\n\n' + extra

		return self.pretty_records

	def getSetTable(self, game, event, year=0, year2=0):
		print(self.getRecords(game, event, year, year2)[1])

	def prettifyData(self):
		self.prettifyResults()
		self.prettifyRecords()

	def outputData(self, file=''):
		if self.pretty_results != '':
			self.output(self.pretty_results, file)
		if self.pretty_records != '':
			self.output(self.pretty_records, file)

	
	def output(self, data, file):
		if file != '':
			path = re.sub(r'\/|\\', ' ', file).split()[-1]
			if data in open(file).read():
				print(f'Results already in {path}.')
				return None
			with open(file, 'a+', encoding='utf-8'):
				f.write(data)
				print(f'Data written to {path}.')
		else:
			print(data)

	def std_flush(self, t):
		# pass
		sys.stdout.write(t)
		sys.stdout.write('\r')
		sys.stdout.flush()

s = SmasherStats(['Mang0', 'Armada'])
# t = s.getSetTable('Melee', 'singles')

### Records
s.getRecords('Melee', 'singles')
s.prettifyRecords()

### Results
s.getResults('Melee', 'singles')
s.prettifyResults()


s.outputData()