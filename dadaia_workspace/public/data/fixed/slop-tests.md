### Slop — tests (fixed)
- A test is born with `Intent:`, fails for a real regression and asserts a value that comes from outside the code under test.
- A mock exists only at the system boundary (network, clock, randomness); an own module is tested through its interface.
- A test name states current behavior; a tombstone (a test of an absence) and an expired SCAFFOLD die at closure.
- Pruning is a `qa-engineer` verdict executed by `software-engineer`; a deletion cites its criterion and its replacement `file:line`.
- Detection: `dd-code-review` SLOP.md S3; measured by ratchet V31 and `test_test_suite_ratchets.py`.
