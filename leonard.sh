#!/bin/bash

# Leonard
# My CI thing

# Good code?
echo "PEP8 check"
flake8 *.py

# Tests pass?
echo "Tests:"
python tests.py

# What branch?
echo "Current branch:"
git branch
