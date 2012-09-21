#!/usr/bin/env python

"""Pre-commit hook for mercurial that does lint testing.

It runs the lint checker (runlint.py) on all the open files in
the current commit.

To install, add the following line to your .hgrc:
  [hooks]
  pretxncommit.lint = /path/to/khan-linter/hghook.py

"""

import os
import re
import subprocess
import sys

import runlint


def main():
    """Run a Mercurial pre-commit lint-check."""
    # If we're a merge, don't try to do a lint-check.
    try:
        # We just want to know how many parents there are.
        # This will output one x for one parent, and two xs for two parents
        # (i.e. a merge)
        heads_output = subprocess.check_output([
            'hg', 'parents', '--template', 'x'
        ])
    except subprocess.CalledProcessError:
        # hg heads must have bonked. Just proceed and do the lint.
        heads_output = ''
    if len(heads_output) > 1:
        print "Skipping lint on merge..."
        return 0

    # Go through all modified or added files.
    try:
        status_output = subprocess.check_output(['hg', 'status', '-a', '-m',
                                                 '--change', 'tip'])
    except subprocess.CalledProcessError, e:
        print >> sys.stderr, "Error calling 'hg status':", e
        return 1

    files_to_lint = []
    if status_output:
        for line in status_output.strip().split('\n'):
            # each line has the format "M path/to/filename.js"
            status, filename = line.split(' ', 1)
            files_to_lint.append(filename)

    num_errors = runlint.main(files_to_lint, blacklist='yes')

    # Lint the commit message itself!  Every non-merge commit must
    # list either a test plan or a review that it's part of (the first
    # commit in a review must have a test plan, but subsequent ones
    # don't need to restate it).  TODO(csilvers): should we do anything
    # special with substate-update commits?
    commit_message = subprocess.check_output(['hg', 'tip',
                                              '--template', '{desc}'])
    if not re.search('^(test plan|review):', commit_message, re.I | re.M):
        print >> sys.stderr, ('Missing "Test plan:" or "Review:" section '
                              'in the commit message.')
        num_errors += 1
    elif re.search('^    <see below>$', commit_message, re.M):
        print >> sys.stderr, ('Must enter a "Test plan:" (or "Review:") '
                              'in the commit message.')
        num_errors += 1
    if re.search('^<one-line summary, followed by ', commit_message, re.M):
        print >> sys.stderr, 'Must enter a summary in the commit message.'
        num_errors += 1
    # TODO(csilvers): verify the first-line summary is actually 1 line long?

    if num_errors:
        # save the commit message so we don't need to retype it
        f = open(os.path.join('.hg', 'commit.save'), 'w')
        f.write(commit_message)
        f.close()
        print >> sys.stderr, ('\n--- %s lint errors ---\n'
                              'Commit message saved to .hg/commit.save'
                              % num_errors)
        return 1
    return 0


if __name__ == '__main__':
    suppress_lint = os.getenv('FORCE_COMMIT', '')
    if suppress_lint.lower() not in ('1', 'true'):
        sys.exit(main())
