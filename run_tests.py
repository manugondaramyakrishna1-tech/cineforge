#!/usr/bin/env python3
"""Run CineForge's unittest suite with a concise, reproducible exit status."""
import sys
import unittest

def main():
    suite = unittest.defaultTestLoader.discover("tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
