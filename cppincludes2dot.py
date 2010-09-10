#!/usr/bin/env python

import getopt
import sys
import os.path
import re
import pdb
import datetime
import time

PROGRAM_VERSION = '0.1'
PROGRAM_NAME = os.path.basename(sys.argv[0])

DOT_GRAPH_HEADER = """
digraph "source tree" {
    overlap=scale;
    size="8,10";
    ratio="fill";
    fontsize="16";
    fontname="Helvetica";
    clusterrank="local";
    label="Include dependency diagram for '%s'; created by %s v%s at %s";
"""

DOT_SUB_GRAPH = """
subgraph "cluster%s" {
    label="%s";
    "%s";
}
"""

DOT_EDGE_DEFINITION = "    \"%s\" -> \"%s\""


debug = False
include_paths = []
exclude = ''
paths = []
merge = 'file'
output = ''
src = '.'
quote_types = 'both'
groups = ''

def show_version_info():
    """Prints the program name and version."""
    sys.stdout.write("%s v%s\n" % (PROGRAM_NAME, PROGRAM_VERSION))

def show_usage():
    """Prints information about program usage."""
    
    sys.stdout.write(
        r"""Usage: %s [OPTIONS]...
%s v%s (C) Michael Rueegg
Released under the terms of the GNU General Public license.
Report bugs to rueegg.michael\@gmail.com

Visualizes #include relationships between every C/C++ source and header file
under the current directory as a graph in DOT syntax. To generate a dependency
graph, type the following:

1. \$ cd ~/program/src

2. \$ %s > include_dep.dot
3. \$ dot -Tpng include_dep.dot > include_dep.png
or more easy: \$ %s -t png -o include_dep.png 
   
Options:
-d, --debug      Display various debug info
-e, --exclude    Specify a regular expression of filenames to ignore
                 For example, ignore your test harnesses.
-m, --merge      Granularity of the diagram:     
                    file - the default, treats each file as separate
                    module - merges .c/.cc/.cpp/.cxx and .h/.hpp/.hxx pairs
                    directory - merges directories into one node
-g, --groups     Cluster files or modules into directory groups
-h, --help       Print this help
-i, --include    Followed by a comma separated list of include search paths
-o, --output     Outputs the DOT graph to the specified file
-p, --paths      Leaves relative paths in displayed filenames
-q, --quotetypes Select for parsing the files included by strip quotes or angle brackets:
                    both - the default, parse all headers
                    angle - include only system headers included by anglebrackets (<>)
                    quote - include only "user" headers included by strip quotes ("")
-s, --src        Followed by a path to the source code, defaults to the current directory
-t, --type       Specifies the file type for the generated graph (e.g., png or pdf); default
                 is DOT file format
-v, --version    print program version
""" % (PROGRAM_NAME, PROGRAM_NAME, PROGRAM_VERSION, PROGRAM_NAME))


def main(argv):
    global debug, exclude, paths, include_paths, output, quote_types, src

    try:
        options, remainder = getopt.getopt(argv, "de:m:ghi:o:p:q:s:v", \
                ["debug", "exclude=", "merge=", "groups", "help", "include=", \
                "output=", "paths=", "quotepaths=", "src=", "type=", "version"])
    except getopt.GetoptError:
        show_usage()
        sys.exit(1)

    for opt, arg in options:
        if opt in ('-h', '--help'):
            show_usage()
            sys.exit(0)
        elif opt in ('-d', '--debug'):
            debug = True
        elif opt in ('-e', '--exclude'):
            exclude = arg
        elif opt in ('-p', '--paths'):
            paths = arg
        elif opt in ('-i', '--include'):
            include_paths = arg.split(',')
        elif opt in ('-o', '--output'):
            output = arg
        elif opt in ('-q', '--quotepaths'):
            quote_types = arg
        elif opt in ('-s', '--source'):
            src = arg
        elif opt in ('-v', '--version'):
            show_version_info()
            sys.exit(0)

    do_it()

def tidy_path(path):
    """Tidies up a path or filename, removing excess ./ and ../ parts."""
    return re.sub(r'[^/]+?/\.\./', '', os.path.normcase(path))

def search_includes(incl_stmt, filename):
    """"""
    log("include_search scanning for %s from %s" % (incl_stmt, filename))
    
    # Try relative to the including file
    rel_path = tidy_path(os.path.join(os.path.dirname(filename), incl_stmt))
    log('include_search trying %s (dirname "%s")' % (rel_path, os.path.dirname(filename)))
    if os.path.exists(rel_path):
        return rel_path
   
    # Try user-specified include paths
    for path in include_paths:
        tmp = tidy_path(os.path.join(path, incl_stmt))
        log("include_search trying %s" % tmp)

        if os.path.exists(tmp):
            return tmp
    
    # Try relative to current directory
    if os.path.exists(incl_stmt):
        return incl_stmt
    
    log("incluse_search failed for %s from %s" % (incl_stmt, filename))
    return None

def to_string(filename):
    """Converts a filename to its display version."""
    if not paths:
        filename = os.path.basename(filename)

    if merge == 'module':
        filename = re.sub(r'\.c$', '', filename)
        filename = re.sub(r'\.cc$', '', filename)
        filename = re.sub(r'\.cxx$', '', filename)
        filename = re.sub(r'\.cpp$', '', filename)
        filename = re.sub(r'\.C$', '', filename)
        filename = re.sub(r'\.h$', '', filename)
        filename = re.sub(r'\.hpp$', '', filename)
        filename = re.sub(r'\.hxx$', '', filename)

    return re.sub(r'/', '/\\n', filename)

def log(msg):
    if debug: sys.stderr.write(msg)

def get_date():
    now = datetime.datetime.now()
    return time.strftime("%a, %d %b %Y %H:%M")

def do_it():
    links = {}
    notfound = {}
    c_file_regex = re.compile(r".*\.(c|cc|cxx|cpp|C|h|hpp|hxx)$")
    sys.stdout.write(DOT_GRAPH_HEADER % (os.path.basename(os.path.realpath(src)), PROGRAM_NAME, PROGRAM_VERSION, get_date()))

    if quote_types == 'angle':
        include_regex = re.compile(r"^#\s*include\s+<(\S+)>")
    elif quote_types == 'system':
        include_regex = re.compile(r'^#\s*include\s+"(\S+)"')
    else:
        include_regex = re.compile(r"^#\s*include\s+(\S+)")

    files = []

    for dirpath, dirnames, filenames in os.walk(src):
        for name in filenames:
            if c_file_regex.match(name):
                files.append(os.path.relpath(os.path.join(dirpath, name)))
        # [file for file in filenames if c_file_regex.match(file)]

    for file in files:
        if exclude != '' and file in exclude:
            continue
        file = file.rstrip('\n')
        file = re.sub(r'^\./', '', file)

        try:
            fileobj = open(file, 'r')

            for line in fileobj:
                mo = include_regex.match(line)
                if mo:
                    included = mo.group(1)
                    raw_included = re.sub(r'[\<\>"]', '', included)
                    include_file = search_includes(raw_included, file)
                    
                    if not include_file:
                        notfound["%s from %s" % (included, file)] = 1
                        continue

                    if merge == 'directory':
                        origin = os.path.dirname(file) 
                        to = os.path.dirname(include_file)
                        if origin != to:
                            edge = DOT_EDGE_DEFINITION % (origin, to)
                            
                            if links.has_key(edge):
                                links[edge] += 1
                            else:
                                links[edge] = 1
                    else:
                        includefile_display = to_string(include_file)
                        file_display = to_string(file)

                        if groups:
                            groupname = os.path.dirname(include_file)
                            sys.stdout.write(DOT_SUB_GRAPH % (groupname, groupname, includefile_display))
                            groupname = os.path.dirname(file)
                            sys.stdout.write(DOT_SUB_GRAPH % (groupname, groupname, file_display))
                        
                        if file_display != includefile_display:
                            edge = DOT_EDGE_DEFINITION % (file_display, includefile_display)
                            
                            if links.has_key(edge):
                                links[edge] += 1
                            else:
                                links[edge] = 1
            fileobj.close()
        except IOError:
            pass
    
    for key in links.iterkeys():
        num_dep = links[key]
        if num_dep > 1:
            key += " [penwidth=%s]" % num_dep 
        sys.stdout.write(key+"\n")
        

    for key in sorted(notfound.iterkeys()):
        sys.stderr.write("Include file not found: %s\n" % key)

    sys.stdout.write("}\n")
    

if __name__ == "__main__":
    main(sys.argv[1:])

