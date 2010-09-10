from distutils.core import setup

setup(name='cppincludes2dot',
      version='0.1',
      description = 'An include dependency graph generator for C/C++',
      keywords = 'include, dependency, graph, c, c++',
      license = 'GNU LESSER GENERAL PUBLIC LICENSE',
      author = 'Michael Rueegg',
      author_email = 'rueegg.michael@gmail.com',
      url = 'http://github.com/mrueegg/cppincludes2dot/',
      dependency_links = [],
      scripts = ['cppincludes2dot.py'],
      )