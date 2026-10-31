#!/bin/bash
mkdir -p /logs/verifier
if python3 /tests/test_grade.py organise; then echo 1; else echo 0; fi > /logs/verifier/reward.txt
