from distutils.core import setup
setup(
	name = 'smasherstats',
	packages = ['smasherstats'],
	version = '2.0.0',
    description = 'Library for stats gathering on smash players using web scrapers',
    author = 'Michael Krasnitski',
    author_email = 'michael.krasnitski@gmail.com',
    license = 'MIT',
    url = 'https://github.com/PolarBearITS/smasherstats-v2.0'
    download_url = 'https://github.com/PolarBearITS/smasherstats-v2.0/tarball/2.0'
    install_requires = [
    	'requests',
    	'beautifulsoup4',
    	'prettytable',
    	'pysmash',
    ]
)