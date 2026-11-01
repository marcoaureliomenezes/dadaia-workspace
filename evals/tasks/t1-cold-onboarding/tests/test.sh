#!/bin/bash
mkdir -p /logs/verifier
if python3 /tests/test_grade.py; then echo 1; else echo 0; fi > /logs/verifier/reward.txt
