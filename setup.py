from setuptools import find_packages, setup

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
	],
	package_dir = {
		"dime": "dime",
	},
	version = "1.0.1",
)
