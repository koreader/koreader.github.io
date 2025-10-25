#!/usr/bin/env python3

# Generate KOReader logo gallery using GitHub API
# 
# Usage:
# generate-gallery.py > gallery.html

import re
import requests
import sys

print('''<!DOCTYPE html>
<title>KOReader logo gallery</title>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width">
<link rel="stylesheet" href="style.css" type="text/css">
<link rel="icon" href="koreader.png" sizes="244x244">
<style>
/* See <https://eev.ee/media/2020-02-css/thumbnail-grids.html> for some inspiration. */
.thumbnail-grid {
  display: grid;
  padding: 0;
  align-items: baseline;
  gap: 1rem;
  list-style: none;
}
.thumbnail-grid h2 {
  margin-top: 0;
  margin-bottom: 1rem;
}
.thumbnail-grid li {
  text-align: center;
  padding: 1rem;
  margin-left: 0;
  background: #fafafa;
  border: 1px solid #eee;
}
.thumbnail-grid li:target {
  background: yellow;
}
.thumbnail-grid img {
  max-width: 100%;
}
</style>
<h1>KOReader logo gallery</h1>
<p class="standout">Since October 2018, we've tried to spruce up the montly stable releases with a code name and an illustration to go with it. This gallery showcases all of the creations.</p>
''')

repo = 'koreader/koreader'

ignore_tag_list = (
  'v2017.08.21-nightly',
  'v2017.10.04-nightly',
  'v2018.01.10-nightly',
  'v2018.02.12-nightly',
  'v2018.03.14-beta',
  'v2018.04.10-beta',
  'v2018.07.29-beta',
  'v2019.01',
  'v2019.02',
  'v2019.03',
  'v2019.05',
  'v2019.10',
  'v2019.12',
  'v2020.02',
  'v2020.07',
  'v2020.10',
  'v2020.12',
  'v2021.02',
  'v2021.08',
)

# Automatically grab all the logos.
r = requests.get(f'https://api.github.com/repos/{repo}/releases?per_page=100')
if r.status_code != 200:
  print(f'Error: GitHub API returned status {r.status_code}')
  sys.exit(1)

def find_image_url(body):
  """Try several heuristics to find an image URL in release body."""
  if not body:
    return None
  # Markdown: ![alt](https://...)
  m = re.search(r'!\[[^\]]*\]\((https://[^)\s]+)\)', body)
  if m:
    return m.group(1)
  # HTML: <img src="https://...">
  m = re.search(r'<img[^>]+src=(?:["\'])?(https://[^\s"\'>]+)', body)
  if m:
    return m.group(1)
  return None

releases = []
for t in r.json():
  tag = t.get('tag_name')
  if not tag or tag in ignore_tag_list:
    continue
  img = find_image_url(t.get('body') or '')
  if not img:
    continue
  releases.append((t.get('html_url'), tag, t.get('name') or tag, img))
releases = releases[::-1]

print('<ul class="thumbnail-grid">')

# The original logo.
print('<li><h2>Original KOReader logo</h2><a href="https://github.com/koreader/koreader/pull/201" target="_blank"><img src="https://cloud.githubusercontent.com/assets/14007369/24885152/89f97930-1e12-11e7-9b3a-0d899af96e90.png" alt="Original KOReader logo" title="Original KOReader logo" loading="lazy"></a></li>', end='')

for r in releases:
  print(f'''
  <li id="{r[1]}">
    <h2>{r[2]}</h2>
    <a href="{r[0]}" target="_blank"><img src="{r[3]}" alt="{r[1]}" title="{r[1]}" loading="lazy"></a>
  </li>''', end='')

print('</ul>')
