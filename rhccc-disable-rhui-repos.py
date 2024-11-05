#!/usr/bin/python3

import configparser
import pathlib
import sys


def process_repo(p):
    config = configparser.ConfigParser(interpolation=None)
    try:
        with p.open() as f:
            config.read_file(f, str(p))
        changed = 0
        for section in config.sections():
            try:
                url = config.get(section, "mirrorlist", fallback=None) or config.get(
                    section, "baseurl"
                )
                if "/rhui/" in url and config.getboolean(
                    section, "enabled", fallback=True
                ):
                    config.set(section, "enabled", "0")
                    changed += 1
            except configparser.NoOptionError as e:
                print(f"Warning when processing {p}: {e}", file=sys.stderr)
        if changed > 0:
            with p.open("w") as f:
                config.write(f, space_around_delimiters=False)
            print(f"Disabled {changed} repositories in {p}")
    except Exception as e:
        print(f"Error when processing {p}: {e}", file=sys.stderr)


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        p = pathlib.Path(arg)
        if p.is_file():
            process_repo(p)
        elif p.is_dir():
            for child in p.iterdir():
                if child.suffix == ".repo":
                    process_repo(child)
