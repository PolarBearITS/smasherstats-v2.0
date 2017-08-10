# Standard Library
import codecs
import json
import pickle
import re
import sys
from collections import *
from contextlib import redirect_stdout
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
		# self.tags = list(map(str.lower, tags))
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

		if isinstance(year, str):
			if year.lower() != 'all':
				raise ValueError("Make sure you pass in the year either as an integer or as 'all'")
		elif isinstance(year, int):
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
		if year == 0:
			year = self.CUR_YEAR
		for tag, results, in total_results.items():
			new_tourneys = {}
			if year2 == 0:
				new_tourneys = {tourney:info for (tourney, info) in results.items() if int(info['date'][-4:]) == year}
			else:
				new_tourneys = {tourney:info for (tourney, info) in results.items() if year <= int(info['date'][-4:]) <= year2}
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
				if self.event == 'doubles':
					tourney += f' \n\t{info["partner"]}'
				key = re.match('\d+', info[self.event])
				if key:
					key = int(key.group(0))
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

	def getRecords(self, game, event, year=0, year2=0):
		if len(self.tags) > 2:
			raise Exception("Records can only be retrieved for 1 or 2 players; no more, no less.")
		total_results = self.getResults(game, event, year, year2)
		tourneys = []
		for tag, results in total_results.items():
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

		set_counts = dict(zip(self.tags, [0]*len(self.tags)))
		game_counts = {}

		for i, tourney in enumerate(tourneys):
			# print(tourney)
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
								set_counts[outcome] += 1
								game_counts = dict(zip(self.tags, list(map(str, win_counts))))
							record += [win_counts, outcome]
							records.append(record)
					if not found:
						break
				if final_bracket:
					break

		if newSuccessfulSlug:
			with open('slugs.pk', 'wb') as s:
				pickle.dump(slugs, s)

		return records, set_counts, game_counts
			
	def getTourneySlug(self, name):
		return '-'.join(re.sub(r'\'|\"', '', name.lower()).split())

	def getEventSlug(self, game, event):
		return '-'.join(game.lower().split()) + '-' + event.lower()

	def prettifyRecords(self, records):
		pt = PrettyTable()
		fnames = ['Tournament', 'Round']
		if len(self.tags) == 1:
			fnames += [f'{self.tags[0]} vs. ↓', 'Score', 'Outcome']
		else:
			fnames += [' vs. '.join(self.tags), 'Winner']
		pt.field_names = fnames

		table = records[0]
		s_counts = records[1]
		g_counts = records[2]

		for i, record in enumerate(table):
			pretty_record = record.copy()
			if i != 0:
				if table[i-1][0] == record[0]:
					pretty_record[0] = ''
				else:
					pt.add_row(['']*len(pt.field_names))
			pt.add_row([' - '.join(map(str, rec)) if isinstance(rec, list) else rec for rec in pretty_record])
		
		return pt, s_counts, g_counts

	def getSetTable(self, game, event, year=0, year2=0):
		print(self.getRecords(game, event, year, year2)[1])


	def outputData(self, r, file=''):
		f = ''
		path = ''
		table = None
		extra = ''
		if len(r) > 1:
			table = r[0]
			s_counts = list(list(map(str, r)) for r in r[1].items())
			g_counts = list(r[2].items())
			extra = 'Total Set Count: ' + ' '.join(s_counts[0]) + ' - ' + ' '.join(reversed(s_counts[1])) + '\n'
			extra += 'Total Game Count: ' + ' '.join(g_counts[0]) + ' - ' + ' '.join(reversed(g_counts[1])) + '\n'
		else:
			table = r
		if isinstance(table, PrettyTable):
			table = table.get_string() + '\n\n' + extra
		if file == '':
			f = sys.stdout
		else:
			path = re.sub(r'\/|\\', ' ', file).split()[-1]
			f = open(file, 'a+', encoding='utf-8')
			if table in open(file).read():
				print(f'Results already in {path}.')
				return
		with f:
			f.write(table)
			if file != '':
				print(f'Data written to {path}.')

	def std_flush(self, t):
		# pass
		sys.stdout.write(t)
		sys.stdout.write('\r')
		sys.stdout.flush()

s = SmasherStats(['Mang0', 'Leffen'])
# t = s.getSetTable('Melee', 'singles')

### Records
rec = s.getRecords('Melee', 'singles')
t = s.prettifyRecords(rec)
s.outputData(t)

### Results
# r = s.getResults('Melee', 'singles')
# t = s.prettifyResults(r)
# s.outputData(t)