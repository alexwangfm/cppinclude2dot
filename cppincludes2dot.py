#!/usr/bin/env python
# -*- coding: utf-8 -*-

# cppincludes2dot - An include dependency graph generator for C/C++
# Copyright (C) 2010, Michael Rueegg
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
import os
import re
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
C_FILE_SUFFIXES = ['c', 'cc', 'cxx', 'cpp', 'C', 'h', 'hpp', 'hxx']

debug = False

def show_version_info():
    """Prints the program name and version."""
    sys.stdout.write("%s v%s\n" % (PROGRAM_NAME, PROGRAM_VERSION))

def show_usage():
    """Prints information about program usage."""
    
    sys.stdout.write(
        r"""Usage: %s [OPTIONS]...
%s v%s (C) Michael Rueegg
Released under the terms of the GNU General Public license.
Report bugs to rueegg.michael@gmail.com

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
-q, --quotetypes Include files by strip quotes or angle brackets:
                    both - the default, parse all headers
                    angle - only system headers included by anglebrackets (<>)
                    quote - only "user" headers included by strip quotes ("")
-s, --src        Path to the source code, defaults to the current directory
-t, --type       Specifies the file type for the generated graph (ps, svg, fig, 
                 png, gif, dia); default is DOT file format
-v, --version    print program version
""" % (PROGRAM_NAME, PROGRAM_NAME, PROGRAM_VERSION, PROGRAM_NAME, PROGRAM_NAME))



def parse_cmdline_options(argv):
    from getopt import getopt, GetoptError

    try:
        options, remainder = getopt(argv, "de:m:ghi:o:p:q:s:v", \
                                    ["debug", "exclude=", "merge=", "groups", \
                                     "help", "include=", "output=", "paths=", \
                                     "quotepaths=", "src=", "type=", "version"])
    except GetoptError:
        show_usage()
        sys.exit(1)
        
    global debug
    debug = False
    include_paths = []
    exclude = ''
    paths = []
    merge = 'file'
    output = ''
    src = '.'
    quote_types = 'both'
    groups = ''
    
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
    
    return src, exclude, quote_types, include_paths, merge, paths, groups


def main(argv):
    src, exclude, quote_types, include_paths, merge, paths, groups = parse_cmdline_options(argv)

    write_header(src)
    files = collect_cfiles(src)
    all_links = {}
    all_notfound = {}

    for file_name in files:
        if exclude != '' and file_name in exclude:
            continue
                    
        def prep_file_name(file_name):
            file_name = file_name.rstrip('\n')
            file_name = re.sub(r'^\./', '', file_name)
            return file_name

        file_name = prep_file_name(file_name)    
        
        try:
            fp = open(file_name, 'r')
            links, notfound = collect_include_dependencies(fp, quote_types, include_paths, merge, paths, groups)
            all_links.update(links)
            all_notfound.update(notfound)
        except IOError:
            log("error while reading file_name '%s'" % file_name)
        else:
            fp.close()
    
    write_edge_definitions(all_links)    
    write_graph_end()
    alert_notfounds(all_notfound)
    
    
def write_edge_definitions(all_links):
    for key in all_links:
        num_dep = all_links[key]
        if num_dep > 1:
            key += " [penwidth=%s]" % num_dep
        sys.stdout.write(key + "\n")
    
    
def write_graph_end():
    return sys.stdout.write("}\n")


def alert_notfounds(all_notfound):
    for key in sorted(all_notfound.iterkeys()):
        sys.stderr.write("Include file_name not found: %s\n" % key)

        
def search_includes(incl_stmt, filename, include_paths):
    """"""

    def tidy_path(path):
        """Tidies up a path or filename, removing excess ./ and ../ parts."""
        return re.sub(r'[^/]+?/\.\./', '', os.path.normcase(path))
    
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


def to_string(filename, paths, merge):
    """Converts a filename to its display version."""
    if not paths:
        filename = os.path.basename(filename)

    if merge == 'module':
        filename = re.sub(r'\(%s)$' % '|'.join(C_FILE_SUFFIXES), '', filename)

    return re.sub(r'/', '/\\n', filename)


def log(msg):
    if debug: sys.stderr.write(msg)


def write_header(srcdir):
    def get_date():
        return time.strftime("%a, %d %b %Y %H:%M")
    
    sys.stdout.write(DOT_GRAPH_HEADER % (os.path.basename(os.path.realpath(srcdir)), \
                                         PROGRAM_NAME, PROGRAM_VERSION, get_date()))


def collect_cfiles(srcdir):
    c_file_regex = re.compile(r".*\.(%s)$" % '|'.join(C_FILE_SUFFIXES))
    files = []
    
    for dirpath, dirnames, filenames in os.walk(srcdir):
        files.extend([os.path.relpath(os.path.join(dirpath, name)) \
                       for name in filenames if c_file_regex.match(name)])
    return files


def collect_include_dependencies(file, quote_types, include_paths, merge, paths, groups):
    def build_include_regex(quote_types):
        if quote_types == 'angle':
            return re.compile(r"^#\s*include\s+<(\S+)>")
        elif quote_types == 'system':
            return re.compile(r'^#\s*include\s+"(\S+)"')
        else:
            return re.compile(r"^#\s*include\s+(\S+)") 
        
    include_regex = build_include_regex(quote_types)
    links = {}
    notfound = {}
    
    for line in file:
        matcher = include_regex.match(line)
        if matcher:
            included = matcher.group(1)
            raw_included = re.sub(r'[\<\>"]', '', included)
            include_file = search_includes(raw_included, file.name, include_paths)
            
            if not include_file:
                notfound["%s from %s" % (included, file.name)] = 1
                continue
            
            if merge == 'directory':
                origin = os.path.dirname(file.name)
                to = os.path.dirname(include_file)
                if origin != to:
                    edge = DOT_EDGE_DEFINITION % (origin, to)
                    links[edge] = links.get(edge, 0) + 1 
            else:
                includefile_display = to_string(include_file, paths, merge)
                file_display = to_string(file.name, paths, merge)
                
                if groups:
                    groupname = os.path.dirname(include_file)
                    sys.stdout.write(DOT_SUB_GRAPH % (groupname, groupname, includefile_display))
                    groupname = os.path.dirname(file.name)
                    sys.stdout.write(DOT_SUB_GRAPH % (groupname, groupname, file_display))
                    
                if file_display != includefile_display:
                    edge = DOT_EDGE_DEFINITION % (file_display, includefile_display)
                    links[edge] = links.get(edge, 0) + 1
                     
    return links, notfound


if __name__ == "__main__":
    main(sys.argv[1:])
