#!/usr/bin/env python3
"""
Seed generator utility.
Generates N cryptographically strong 32-bit seeds, same method as main.py.
Usage: python seed_gen.py --num=20
"""

import argparse
import secrets


def main():
    parser = argparse.ArgumentParser(description='Generate random seeds (32-bit)')
    parser.add_argument('--num', type=int, default=1, help='Number of seeds to generate')
    args = parser.parse_args()

    if args.num <= 0:
        raise SystemExit('num must be > 0')

    for _ in range(args.num):
        seed = secrets.randbits(32)
        print(seed)


if __name__ == '__main__':
    main()

