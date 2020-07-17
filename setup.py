from setuptools import setup, find_packages

try:
    with open('README.md') as file:
        long_desc = file.read()
except IOError:
    long_desc = ''


setup(
    name='python-strava',
    version='0.1.7',
    description=('Strava API client supporting high level integration with Django.'),
    author='Lincolwn Martins',
    author_email='lincolwn@gmail.com',
    url='https://github.com/lincolwn/python-strava',
    keywords='strava client django',
    packages=find_packages(),
    license='MIT License',
    long_description=long_desc,
    install_requires=['requests']
)
