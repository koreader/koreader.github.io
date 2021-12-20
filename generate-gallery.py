#!/usr/bin/env python3

# Generate KOReader logo gallery using GitHub API
# 
# Usage:
# generate-gallery.py > gallery.html

import re
import requests

print('''
<!DOCTYPE html>
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
releases = [ 
  (t['html_url'], t['tag_name'], t['name'], re.search(r'https://.*\.(jpg|png)', t['body'])[0]) 
  for t in r.json()
  if not t['tag_name'] in ignore_tag_list and ('jpg' in t['body'] or 'png' in t['body'])
][::-1]

print('<ul class="thumbnail-grid">')

# The original logo.
print('<li><h2>Original KOReader logo</h2><a href="https://github.com/koreader/koreader/pull/201" target="_blank"><img src="https://cloud.githubusercontent.com/assets/14007369/24885152/89f97930-1e12-11e7-9b3a-0d899af96e90.png" alt="Original KOReader logo" title="Original KOReader logo" loading="lazy"></a></li>')

for r in releases:
  print(f'<li id="{r[1]}"><h2>{r[2]}</h2><a href="{r[0]}" target="_blank"><img src="{r[3]}" alt="{r[2]}" title="{r[2]}" loading="lazy"></a></li>')

print('</ul>')
