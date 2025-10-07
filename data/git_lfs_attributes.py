#!/usr/bin/env python
u"""
git_lfs_attributes.py
"""
import os
import re
import inspect
import argparse

# get filepath
filename = inspect.getframeinfo(inspect.currentframe()).filename
filepath = os.path.dirname(os.path.dirname(os.path.abspath(filename)))

# PURPOSE: find files in directory matching pattern and print to git attributes
def git_lfs_attributes(d, regex):
    # find files matching pattern
    lfs_files = [os.path.join(d,f) for f in os.listdir(d) if regex.match(f)]
    # open git attributes file
    attributes_file = os.path.join(filepath, '.gitattributes')
    with open(attributes_file, 'w') as fid:
        # print pixi header
        fid.write('# SCM syntax highlighting & preventing 3-way merges\n')
        fid.write('pixi.lock merge=binary linguist-language=YAML linguist-generated=true\n')
        # print files in order
        for f in sorted(lfs_files):
            fid.write('{0} filter=lfs diff=lfs merge=lfs -text\n'.format(f))

def main():
    # Read the system arguments listed after the program
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory','-D', type=str,
        default=os.getcwd(), help='Working data directory')
    parser.add_argument('--regex','-R', type=str,
        default='(.*?)', help='Regular expression pattern')
    args = parser.parse_args()
    # run git lfs attributes program
    git_lfs_attributes(args.directory, re.compile(args.regex))

# run main program
if __name__ == '__main__':
    main()
