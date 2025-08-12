#!/usr/bin/env python3
import argparse
import math
import os
import sys
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup


def fetch_contributions_matrix(username: str) -> List[List[int]]:
    url = f"https://github.com/users/{username}/contributions"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GameOfLifeSVG/1.0)"
    }
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    svg = soup.find("svg")
    if svg is None:
        raise RuntimeError("Could not find contributions SVG in response")

    # GitHub groups weeks in <g> with translate(x, 0). Each has up to 7 rects (days)
    weeks = svg.find_all("g")
    grid = []  # rows=7, cols=number of weeks
    # Initialize 7 rows
    rows = 7
    cols = 0
    columns: List[List[int]] = []  # column-major, each with up to 7 values

    for g in weeks:
        rects = g.find_all("rect")
        if not rects:
            continue
        col = [0] * rows
        for rect in rects:
            # y dictates day index increments by 10 usually; safer: use data-date's weekday? Not available.
            # GitHub ordering in each column is top->bottom Mon..Sun or Sun..Sat depending. We'll map by rect's 'y'.
            y = rect.get("y")
            try:
                yi = int(int(float(y)) / 10)
            except Exception:
                # fallback: enumerate order
                yi = len([r for r in rects if r == rect]) - 1
            count = int(rect.get("data-count", rect.get("data-level", "0")))
            col[yi] = 1 if count > 0 else 0
        columns.append(col)
    if not columns:
        raise RuntimeError("No contribution columns parsed")

    cols = len(columns)
    # Convert to row-major 7 x cols
    grid = [[columns[c][r] if r < len(columns[c]) else 0 for c in range(cols)] for r in range(rows)]
    return grid


def life_step(state: List[List[int]]) -> List[List[int]]:
    rows = len(state)
    cols = len(state[0]) if rows else 0

    def neighbors(r: int, c: int) -> int:
        s = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr = r + dr
                cc = c + dc
                if 0 <= rr < rows and 0 <= cc < cols:
                    s += state[rr][cc]
        return s

    nxt = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            n = neighbors(r, c)
            if state[r][c] == 1:
                nxt[r][c] = 1 if n == 2 or n == 3 else 0
            else:
                nxt[r][c] = 1 if n == 3 else 0
    return nxt


def simulate(state: List[List[int]], steps: int) -> List[List[List[int]]]:
    frames = [state]
    cur = state
    for _ in range(steps - 1):
        cur = life_step(cur)
        frames.append(cur)
    return frames


def render_animated_svg(frames: List[List[List[int]]], cell: int, gap: int, alive_color: str, dead_color: str,
                         frame_duration: float, out_path: str) -> None:
    if not frames:
        raise ValueError("No frames to render")
    rows = len(frames[0])
    cols = len(frames[0][0]) if rows else 0

    total_dur = frame_duration * len(frames)

    width = cols * (cell + gap) - gap
    height = rows * (cell + gap) - gap

    def rect(x, y, fill):
        return f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" ry="2" fill="{fill}"/>'

    parts = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">')
    # Background (dead cells grid)
    bg = []
    for r in range(rows):
        for c in range(cols):
            x = c * (cell + gap)
            y = r * (cell + gap)
            bg.append(rect(x, y, dead_color))
    parts.append(f'<g id="bg">{"".join(bg)}</g>')

    # Precompute keyTimes once
    key_times = [i / len(frames) for i in range(len(frames) + 1)]
    key_times_str = ";".join(f"{t:.6f}".rstrip('0').rstrip('.') if t not in (0, 1) else ("0" if t == 0 else "1") for t in key_times)

    # For each frame create a group with alive cells and animate its opacity discretely
    for k, frame in enumerate(frames):
        g_cells = []
        for r in range(rows):
            for c in range(cols):
                if frame[r][c] == 1:
                    x = c * (cell + gap)
                    y = r * (cell + gap)
                    g_cells.append(rect(x, y, alive_color))
        values = ["1" if i == k else "0" for i in range(len(frames) + 1)]  # last value equals first to keep cycle crisp
        values_str = ";".join(values)
        parts.append(f'<g id="f{k}" opacity="{1 if k==0 else 0}">{"".join(g_cells)}'
                     f'<animate attributeName="opacity" dur="{total_dur:.3f}s" repeatCount="indefinite" '
                     f'calcMode="discrete" keyTimes="{key_times_str}" values="{values_str}"/></g>')

    parts.append('</svg>')

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


def main():
    parser = argparse.ArgumentParser(description="Generate Game of Life animated SVG from GitHub contributions")
    parser.add_argument("--username", required=True, help="GitHub username")
    parser.add_argument("--steps", type=int, default=60, help="Number of frames to simulate")
    parser.add_argument("--frame-duration", type=float, default=0.08, help="Seconds per frame")
    parser.add_argument("--cell", type=int, default=10, help="Cell size in px")
    parser.add_argument("--gap", type=int, default=2, help="Gap between cells in px")
    parser.add_argument("--alive-color", default="#2ea043", help="Color for alive cells")
    parser.add_argument("--dead-color", default="#ebedf0", help="Color for dead cells")
    parser.add_argument("--out", default="assets/life.svg", help="Output SVG path")
    args = parser.parse_args()

    grid = fetch_contributions_matrix(args.username)
    frames = simulate(grid, args.steps)
    render_animated_svg(frames, args.cell, args.gap, args.alive_color, args.dead_color, args.frame_duration, args.out)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
