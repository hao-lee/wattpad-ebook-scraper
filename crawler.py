#!/usr/bin/env python3

import sys
import io
import re

import requests
#import dateutil.parser
#from genshi.input import HTML
#import smartypants
from bs4 import BeautifulSoup

# Setup session to not hit Android download app page
session = requests.session()
# No user agent. Wattpad now blocks all user agents containing "Python".
session.headers['User-Agent'] = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36"
session.proxies = {
        'http': 'socks5://127.0.0.1:1080',
        'https': 'socks5://127.0.0.1:1080'
}

# Used by Android app normally
# Example parameters are what Android provides
API_STORYINFO = 'https://www.wattpad.com/api/v3/stories/' #9876543?drafts=0&include_deleted=1

# Used by website and Android app normally
API_STORYTEXT = 'https://www.wattpad.com/apiv2/storytext' # ?id=23456789
# Webpage uses a page parameter: ?id=23456789&page=1
# Android uses these parameters: ?id=23456789&increment_read_count=1&include_paragraph_id=1&output=text_zip
# Now (2015-06-15), returns HTML instead of JSON. output=json will get JSON again

API_CHAPTERINFO = 'https://www.wattpad.com/apiv2/info' # ?id=23456789

# Documented api
API_GETCATEGORIES = 'https://www.wattpad.com/apiv2/getcategories'

ILLEAGAL_FILENAME_CHARACTERS = str.maketrans(r'.<>:"/\|?*^', '-----------')

# Fixup the categories data, this could probably be cached too
categories = session.get(API_GETCATEGORIES).json()
categories = {int(k): v for k, v in categories.items()}

def download_story(story_id):
	# TODO: probably use {'drafts': 0, 'include_deleted': 0}
	storyinfo = session.get(API_STORYINFO + story_id, params={'drafts': 1, 'include_deleted': 1}).json()

	story_title = storyinfo['title']
	story_description = storyinfo['description']
	story_createDate = storyinfo['createDate']
	story_modifyDate = storyinfo['modifyDate']
	story_author = storyinfo['user']['name']
	story_categories = [categories[c] for c in storyinfo['categories'] if c in categories] # category can be 0
	story_rating = storyinfo['rating'] # TODO: I think 4 is adult?
	story_url = storyinfo['url']

	print('Story "{story_title}": {story_id}'.format(story_title=story_title, story_id=story_id))

	txt_content = ""
	for chapter_index, part in enumerate(storyinfo['parts']):
		chapter_title = part['title']

		if part['draft']:
			print('Skipping "{chapter_title}": {chapter_id}, part is draft'.format(chapter_title=chapter_title, chapter_id=chapter_id))
			continue

		if 'deleted' in part and part['deleted']:
			print('Skipping "{chapter_title}": {chapter_id}, part is deleted'.format(chapter_title=chapter_title, chapter_id=chapter_id))
			continue

		chapter_id = part['id']

		chapter_modifyDate = part['modifyDate']

		print('Downloading "{chapter_title}": {chapter_id}'.format(chapter_title=chapter_title, chapter_id=chapter_id))

		chapter_html = session.get(API_STORYTEXT, params={'id': chapter_id, 'output': 'json'}).json()['text']
		pure_text = BeautifulSoup(chapter_html, 'lxml').get_text()
		txt_content += "Chapter %d %s %s\n\n%s\n\n\n\n" %(chapter_index,
		                chapter_title, chapter_modifyDate, pure_text)

	book = "%s\n\nCreate: %s\nModified: %s\nAuthor: %s\nCategory: %s\n\n\n%s"\
	        %(story_title, story_createDate, story_modifyDate, story_author,
	          story_categories, txt_content)
	print('Saving TXT')
	with open(story_title + ".txt", 'wt', encoding='utf-8', newline='\n') as fd:
		fd.write(book)


def get_story_id(url):
	# Extract the id number from the url
	match = re.search(r'\d+', url)
	if not match:
		return None

	# Check if it's a valid id of a story
	url_id = match.group()
	storyinfo_req = session.get(API_STORYINFO + url_id)
	if storyinfo_req.ok:
		return url_id

	# If not, check if it's a chapter id and retrieve the story id
	chapterinfo_req = session.get(API_CHAPTERINFO, params={'id': url_id})
	if not chapterinfo_req.ok:
		return None
	story_url = chapterinfo_req.json()['url']
	story_id = re.search(r'\d+', story_url).group()
	return story_id


if __name__ == '__main__':
	story_url = "https://www.wattpad.com/story/20738183-expiration-date-duology"
	story_id = get_story_id(story_url)
	if story_id:
		download_story(story_id)
	else:
		print('ERROR: could not retrieve story', story_url)