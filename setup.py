from setuptools import find_packages, setup

print find_packages()

setup(
	entry_points = {
		"console_scripts": [
			"dime = dime.start:main",
		],
	},
	install_requires = [
		"pyzmq",
		"numpy>=1.7",
	],
	name = "dime",
	packages = [
		"dime",
		"dime_messenger",
	],
	package_dir = {
		"dime": "src/dime",
		"dime_messenger": "src/messenger",
	},
	version = "1.0.0",
)
