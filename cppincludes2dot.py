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


def main(argv):
    context = parse_cmdline_options(argv)
    edges, clusters, not_found = collect_dependencies(context)
    output_dependencies(context, edges, clusters, not_found)


def parse_cmdline_options(argv):
    """ """
    from getopt import getopt, GetoptError

    try:
        options, remainder = getopt(argv, "de:m:ghi:o:pq:s:t:v", \
                                    ["debug", "exclude=", "merge=", "groups", \
                                     "help", "include=", "output=", "paths", \
                                     "quotepaths=", "src_dir=", "type=", "version"])
    except GetoptError:
        show_usage()
        sys.exit(1)
    
    program_options = { 'include_paths' : [], 'exclude': '', 'paths': [], \
                       'merge': 'file', 'output': '', 'src_dir': '.', \
                       'quote_types': 'both', 'type': 'dot', 'groups': '' }
    
    for opt, arg in options:
        if opt in ('-h', '--help'):
            show_usage()
            sys.exit(0)
        elif opt in ('-d', '--debug'):
            global debug
            debug = True
        elif opt in ('-e', '--exclude'):
            program_options['exclude'] = arg
        elif opt in ('-m', '--merge'):
            program_options['merge'] = arg
        elif opt in ('-p', '--paths'):
            program_options['paths'] = True
        elif opt in ('-g', '--groups'):
            program_options['groups'] = True
        elif opt in ('-i', '--include'):
            program_options['include_paths'] = arg.split(',')
        elif opt in ('-o', '--output'):
            program_options['output'] = arg
        elif opt in ('-q', '--quotepaths'):
            program_options['quote_types'] = arg
        elif opt in ('-s', '--source'):
            program_options['src_dir'] = arg
        elif opt in ('-t', '--type'):
            program_options['type'] = arg
        elif opt in ('-v', '--version'):
            show_version_info()
            sys.exit(0)
    
    return program_options


def collect_dependencies(context):
    """ """
    all_edges = {}
    all_clusters = set()
    all_notfound = set()
    exclude_regexes = build_exclude_regexes(context['exclude'])
    files = collect_cfiles(context['src_dir'])
    files = [file_name for file_name in files \
             if not should_file_be_excluded(file_name, exclude_regexes)]
    
    for file_name in files:
        file_name = re.sub(r'^\./', '', file_name.rstrip('\n'))
        try:
            fp = open(file_name, 'r')
            edges, clusters, notfound = collect_include_dependencies(fp, context)
            all_edges.update(edges)
            all_clusters.update(clusters)
            all_notfound.update(notfound)
        except IOError:
            log("error while reading file_name '%s'" % file_name)
        else:
            fp.close()
    
    return all_edges, all_clusters, all_notfound


def output_dependencies(context, edges, clusters, not_found):
    """ """
    import subprocess
    
    fout = sys.stdout
    
    if context['output'] and context['type'] == 'dot':
        fout = open(context['output'], 'w')
    elif context['type'] != 'dot':
        p = subprocess.Popen('dot -T%s -o %s' % (context['type'], context['output']), 
            shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        fout = p.stdin
        
    write_header(fout, context['src_dir'])
    write_edge_definitions(fout, edges)
    write_cluster_definitions(fout, clusters)
    write_footer(fout)
    alert_notfounds(not_found)
    
    fout.close()


def build_exclude_regexes(excludes):
    """Builds a list or regex expressions for excluding certain files.
    
    excludes -- a string with a comma separated list of file patterns
    """
    import fnmatch

    excludes = excludes.split(',')
    exclude_regex_list = []
    
    for each_exclude in excludes:
        exclude_regex_list.append(re.compile(fnmatch.translate(each_exclude)))
    
    return exclude_regex_list


def should_file_be_excluded(file_name, exclude_regexes):
    """Checks whether the given file should be excluded.
    
    file_name -- the file name that should be checked
    exclude_regexes -- a list of exclude regular expressions
    """
    for each_exclude in exclude_regexes:
        if each_exclude.match(file_name):
            return True
    return False


def show_version_info():
    """Prints the program name and version."""
    sys.stdout.write("%s v%s\n" % (PROGRAM_NAME, PROGRAM_VERSION))


def show_usage():
    """Prints information about program usage."""
    
    sys.stdout.write(
        """Usage: %s [OPTIONS]...
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
-g, --groups     Cluster files or modules into directory groups
-h, --help       Print this help
-i, --include    Followed by a comma separated list of include search paths
-m, --merge      Granularity of the diagram:     
                    file - the default, treats each file as separate
                    module - merges .c/.cc/.cpp/.cxx and .h/.hpp/.hxx pairs
                    directory - merges directories into one node
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


def write_header(fout, srcdir):
    if srcdir == '.': 
        srcdir = os.path.basename(os.path.realpath(srcdir))
        
    fout.write(DOT_GRAPH_HEADER % (srcdir, PROGRAM_NAME, PROGRAM_VERSION, \
               time.strftime("%a, %d %b %Y %H:%M")))
    
    
def write_edge_definitions(fout, edges):
    for edge_def in edges:
        num_dep = edges[edge_def]
        if num_dep > 1:
            edge_def += " [penwidth=%s]" % num_dep
        fout.write(edge_def + '\n')
    
    
def write_cluster_definitions(fout, clusters):
    map(lambda cluster_def: fout.write(cluster_def + '\n'), clusters)
    
    
def write_footer(fout):
    fout.write("}\n")


def alert_notfounds(not_found):
    map(lambda msg: sys.stderr.write("Include file_name not found: %s\n" % msg), \
        sorted(not_found))

        
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


def to_display_version(filename, paths, merge):
    """Converts a filename to its display version."""
    if not paths:
        filename = os.path.basename(filename)

    if merge == 'module':
        filename = re.sub(r'\.(%s)$' % '|'.join(C_FILE_SUFFIXES), '', filename)

    return filename


def log(msg):
    """Print a log message on stderr."""
    if debug: sys.stderr.write(msg + '\n')


def collect_cfiles(srcdir):
    """Collects all C/C++ files in the given source directory.""" 
    c_file_regex = re.compile(r".*\.(%s)$" % '|'.join(C_FILE_SUFFIXES))
    files = []
    
    for dirpath, dirnames, filenames in os.walk(srcdir):
        files.extend([os.path.relpath(os.path.join(dirpath, name)) \
                       for name in filenames if c_file_regex.match(name)])
    return files


def collect_include_dependencies(file, context):
    """ """
    
    def put_edge_def(edges, source, dest):
        edge = DOT_EDGE_DEFINITION % (dest, source)
        edges[edge] = edges.get(edge, 0) + 1
    
    def put_cluster_def(clusters, group_name, file_name):
        group_name = os.path.dirname(group_name)
        clusters.add(DOT_SUB_GRAPH % (group_name, group_name, file_name))
    
    def build_include_regex(quote_types):
        if quote_types == 'angle':
            return re.compile(r"^#\s*include\s+<(\S+)>")
        elif quote_types == 'system':
            return re.compile(r'^#\s*include\s+"(\S+)"')
        else:
            return re.compile(r"^#\s*include\s+(\S+)") 
    
    def merge_directory(file, edges, include_file):
        origin = os.path.dirname(include_file)
        destination = os.path.dirname(file.name)
        
        if origin != destination:
            put_edge_def(edges, origin, destination)
        
    include_regex = build_include_regex(context['quote_types'])
    edges = {}
    notfound = set()
    clusters = set()
    
    for line in file:
        matcher = include_regex.match(line)
        
        if matcher:
            included = matcher.group(1)
            raw_included = re.sub(r'[\<\>"]', '', included)
            include_file = search_includes(raw_included, file.name, \
                                            context['include_paths'])
            
            if not include_file:
                notfound.add("%s from %s" % (included, file.name))
                continue
            
            if context['merge'] == 'directory':
                merge_directory(file, edges, include_file) 
            else:
                includefile_display = to_display_version(include_file, \
                                                         context['paths'], \
                                                         context['merge'])
                file_display = to_display_version(file.name, context['paths'], \
                                                   context['merge'])
                
                if context['groups']:
                    put_cluster_def(clusters, include_file, includefile_display)
                    put_cluster_def(clusters, file.name, file_display)
                    
                if file_display != includefile_display:
                    put_edge_def(edges, includefile_display, file_display)
                     
    return edges, clusters, notfound


if __name__ == "__main__":
    main(sys.argv[1:])
