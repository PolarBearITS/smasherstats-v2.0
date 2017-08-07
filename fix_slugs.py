import pickle

new_slugs = {}
new_lines = []

with open('failed_slugs.txt', 'r') as f:
	lines = [l for l in f.readlines()]
	if lines == []:
		# pass
		quit()
	for line in lines:
		s = line.strip('\n').split(':')
		if len(s) == 2:
			new_slugs[s[0]] = s[1]
		else:
			new_lines.append(line)

with open('slugs.pk', 'rb') as sl:
	old_slugs = pickle.load(sl)
	print(old_slugs)
	new_slugs.update(old_slugs)

with open('slugs.pk', 'wb') as sl:
	pickle.dump(new_slugs, sl)

with open('failed_slugs.txt', 'w') as f:
	for line in new_lines:
		f.write(line)