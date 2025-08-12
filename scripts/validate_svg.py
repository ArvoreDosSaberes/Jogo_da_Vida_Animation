#!/usr/bin/env python3
import sys
from xml.etree import ElementTree as ET


def main(path: str) -> int:
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception as e:
        print(f"ERROR: Failed to parse SVG: {e}")
        return 2

    if root.tag.lower().endswith('svg'):
        # basic checks
        w = root.get('width')
        h = root.get('height')
        if not w or not h:
            print("ERROR: SVG missing width/height")
            return 3
    else:
        print("ERROR: Root element is not SVG")
        return 4

    # Look for at least one animate element (SMIL)
    nsless = [elem.tag.split('}')[-1] for elem in root.iter()]
    if 'animate' not in nsless:
        print("ERROR: No <animate> elements found; animation may not work")
        return 5

    print("OK: SVG parsed and contains animation")
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("usage: validate_svg.py path/to.svg")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
