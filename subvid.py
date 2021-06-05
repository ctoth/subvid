import os
import requests
import lxml.html
import lxml.cssselect


session = requests.session()
session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:77.0) Gecko/20190101 Firefox/77.0'

def find_mp4_links(page_html):
  tree = lxml.html.fromstring(page_html)
  vids = tree.cssselect('source[src*=".mp4"]')
  meta_vids = tree.cssselect('meta[property="og:video"]')
  urls = set([i.get('src') for i in vids] + [j.get('content') for j in meta_vids])
  mobile_urls = set()
  for url in urls:
    if url.endswith('-mobile.mp4') and url[:-11] + '.mp4' in urls:
      mobile_urls.add(url)
  return list(urls - mobile_urls)

def reddit_posts(subreddit):
  children = subreddit['data']['children']
  for c in children:
    c = c['data']
    media = c.get('media', {}) or {}
    media = media.get('oembed', {}) or {}
    yield {
      "title": c['title'],
      'url': c['url'],
      'author': c['author'],
      'slug': c['name'],
      'media_title': media.get('title'),
      'media_type': media.get('type'),
      'subreddit': c['subreddit'],
}

def retrieve_subreddit(sub):
  url = 'https://old.reddit.com/r/{sub}.json'.format(sub=sub)
  return session.get(url).json()

def download_videos(subreddit):
  data = retrieve_subreddit(subreddit)
  for post in reddit_posts(data):
    if post['media_type'] != 'video':
      continue
    vid_page = session.get(post['url']).content
    vid_links = find_mp4_links(vid_page)
    for link in vid_links:
      fname = determine_filename(post)
      fpath = os.path.dirname(fname)
      if not os.path.exists(fpath):
        os.makedirs(fpath)
      if os.path.exists(fname):
        continue
      print("Downloading {title} from {author}".format(**post))
      vid = session.get(link)

      with open(fname, 'wb') as f:
        f.write(vid.content)


def determine_filename(post):
  return os.path.abspath(os.path.join(post['subreddit'], safe_filename(post['author']), safe_filename(post['title'])+'.mp4'))


def safe_filename(filename):
	"""Given a filename, returns a safe version with no characters that would not work on different platforms."""
	SAFE_FILE_CHARS = "'-_.()[]{}!@#$%^&+=`~ "
	filename = str(filename)
	new_filename = ''.join(c for c in filename if c in SAFE_FILE_CHARS or c.isalnum())
	#Windows doesn't like directory names ending in space, macs consider filenames beginning with a dot as hidden, and windows removes dots at the ends of filenames.
	return new_filename.strip(' .')

if __name__ == '__main__':
  import io, os, sys
  what = sys.argv[1]
  if os.path.isfile(what):
    with io.open(what, 'rt') as f:
      for line in f:
        print(line)
        download_videos(line[:-1])
  else:
    download_videos(what)
