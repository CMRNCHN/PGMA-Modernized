# 8TeenBoy
import re, os, platform, urllib
from difflib import SequenceMatcher

PLUGIN_LOG_TITLE = '8TeenBoy'	# Log Title

VERSION_NO = '2019.03.02.1'

# Delay used when requesting HTML, may be good to have to prevent being
# banned from the site
REQUEST_DELAY = 0

# URLS
BASE_URL = 'https://www.8teenboy.com%s'

# Example Video Details URL
# https://www.helixstudios.net/video/3437/hosing-him-down.html
BASE_VIDEO_DETAILS_URL = 'https://www.8teenboy.com/video/%s/index.html'
BASE_MODEL_DETAILS_URL = 'https://www.8teenboy.com/model/%s/index.html'

# Example Search URL:
# https://www.helixstudios.net/videos/?q=Hosing+Him+Down
BASE_SEARCH_URL = 'https://www.helixstudios.net/videos/?q=%s'

# File names to match for this agent
file_name_pattern = re.compile(Prefs['regex'])

# Example File Name:
# https://media.helixstudios.com/scenes/hx111_scene2/hx111_scene2_member_1080p.mp4
# FILENAME_PATTERN = re.compile("")
# TITLE_PATTERN = re.compile("")

def Start():
	HTTP.CacheTime = CACHE_1WEEK
	HTTP.Headers['User-agent'] = 'Mozilla/4.0 (compatible; MSIE 8.0; ' \
        'Windows NT 6.2; Trident/4.0; SLCC2; .NET CLR 2.0.50727; ' \
        '.NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0)'

class EightTeenBoy(Agent.Movies):
	name = '8TeenBoy'
	languages = [Locale.Language.NoLanguage, Locale.Language.English]
	primary_provider = False
	fallback_agent = ['com.plexapp.agents.gayporncollector']
	contributes_to = ['com.plexapp.agents.cockporn']

	def Log(self, message, *args):
		if Prefs['debug']:
			Log(PLUGIN_LOG_TITLE + ' - ' + message, *args)

	def intTest(self, s):
		try:
			int(s)
			return int(s)
		except ValueError:
			return False

	def similar(self, a, b):
		return SequenceMatcher(None, a, b).ratio()

	def search(self, results, media, lang, manual):
		self.Log('-----------------------------------------------------------------------')
		self.Log('SEARCH CALLED v.%s', VERSION_NO)
		self.Log('SEARCH - Platform: %s %s', platform.system(), platform.release())
		self.Log('SEARCH - media.title - %s', media.title)
		self.Log('SEARCH - media.items[0].parts[0].file - %s', media.items[0].parts[0].file)
		self.Log('SEARCH - media.primary_metadata.title - %s', media.primary_metadata.title)
		self.Log('SEARCH - media.items - %s', media.items)
		self.Log('SEARCH - media.filename - %s', media.filename)
		self.Log('SEARCH - lang - %s', lang)
		self.Log('SEARCH - manual - %s', manual)
		self.Log('SEARCH - Prefs->cover - %s', Prefs['cover'])
		self.Log('SEARCH - Prefs->folders - %s', Prefs['folders'])
		self.Log('SEARCH - Prefs->regex - %s', Prefs['regex'])

		if not media.items[0].parts[0].file:
			return

		path_and_file = media.items[0].parts[0].file.lower()
		self.Log('SEARCH - File Path: %s', path_and_file)

		(file_dir, basename) = os.path.split(os.path.splitext(path_and_file)[0])
		final_dir = os.path.split(file_dir)[1]

		self.Log('SEARCH - Enclosing Folder: %s', final_dir)

		if Prefs['folders'] != "*":
			folder_list = re.split(',\s*', Prefs['folders'].lower())
			if final_dir not in folder_list:
				self.Log('SEARCH - Skipping %s because the folder %s is not in the acceptable folders list: %s', basename, final_dir, ','.join(folder_list))
				return

		m = file_name_pattern.search(basename)
		if not m:
			self.Log('SEARCH - Skipping %s because the file name is not in the expected format.', basename)
			return

		self.Log('SEARCH - File Name: %s', basename)

		groups = m.groupdict()
		clip_name = groups['clip_name']
		movie_url_name = re.sub('\s+', '+', clip_name)
		movie_url = BASE_VIDEO_DETAILS_URL % movie_url_name
		search_query_raw = list()
		for piece in clip_name.split(' '):
			if re.search('^[0-9A-Za-z]*$', piece.replace('!', '')) is not None:
				search_query_raw.append(piece)

		self.Log('SEARCH - Video URL: %s', movie_url)
		html = HTML.ElementFromURL(movie_url, sleep=REQUEST_DELAY)
		video_title = html.xpath('//h2[@class="pull-left"]/text()')
		results.Append(MetadataSearchResult(id = movie_url, name = video_title, score = 100, lang = lang))

	def update(self, metadata, media, lang, force=False):
		self.Log('UPDATE CALLED')

		if not media.items[0].parts[0].file:
			return

		file_path = media.items[0].parts[0].file
		self.Log('UPDATE - File Path: %s', file_path)
		self.Log('UPDATE - Video URL: %s', metadata.id)
		url = metadata.id

		# Fetch HTML
		html = HTML.ElementFromURL(url, sleep=REQUEST_DELAY)

		# Set tagline to URL
		metadata.tagline = url
		valid_image_names = list()
		valid_art_names = list()

		video_title = html.xpath('//h2[@class="pull-left"]/text()')[0]
		self.Log('UPDATE - video_title: "%s"', video_title)
		metadata.title = video_title

		# External 	https://cdn.helixstudios.com/img/300h/media/stills/hx109_scene52_001.jpg
		# Member 	https://cdn.helixstudios.com/img/250w/media/stills/hx109_scene52_001.jpg

		i = 0
		video_image_list = html.xpath("//a[@class='jg-entry entry-visible']/img")
		Log(video_image_list)
		try:
			coverPrefs = Prefs['cover']
			for image in video_image_list:
				if i <= (self.intTest(coverPrefs)-1) or coverPrefs == "all available":
					i = i + 1
					thumb_url = image.get('src')
					self.Log(thumb_url)
					poster_url = thumb_url.replace('250h', '1920w')
					valid_image_names.append(poster_url)
					if poster_url not in metadata.posters:
						try:
							metadata.posters[poster_url]=Proxy.Preview(HTTP.Request(thumb_url), sort_order = i)
						except: pass
		except Exception as e:
			self.Log('UPDATE - Error getting posters: %s', e)
			pass

		#Try to get scene background art
		try:
			bg_image = html.xpath("//div[@class='section-mini hide-md']/img")[0].get("src")
			bg_image = bg_image.replace("480w","1920w")
			valid_art_names.append(bg_image)
			metadata.art[bg_image] = Proxy.Media(HTTP.Request(bg_image), sort_order=1)
			metadata.art.validate_keys(valid_art_names)
		except Exception as e:
			self.Log('UPDATE - Error getting art: %s', e)
			pass

		# Try to get description text
		try:
			about_text=html.xpath('//p[@class="scene-description hide-md"]/text()')[0]
			metadata.summary=about_text
		except Exception as e:
			self.Log('UPDATE - Error getting description text: %s', e)
			pass

		# Try to get and process the video cast
		metadata.roles.clear()
		rolethumbs = list();
		cast_img_list = html.xpath('//div[@class="pure-u-1-3"]/div[@class="grid-item-wrapper"]/a/div/img')
		for cast_img in cast_img_list:
			thumb_url = cast_img.get('src')
			cast_img_url = thumb_url.replace('300h', '1920w')
			rolethumbs.append(thumb_url);
		htmlcast = html.xpath('//div[@class="pure-u-1-3"]/div[@class="grid-item-wrapper"]/a/div[@class="thumbnail-bottom-text"]/div/text()')
		self.Log('UPDATE - cast: "%s"', htmlcast)
		index = 0
		for cast in htmlcast:
			cname = cast.strip()
			if (len(cname) > 0):
				role = metadata.roles.new()
				role.name = cname
				role.photo = rolethumbs[index]
			index += 1

		metadata.posters.validate_keys(valid_image_names)
		metadata.collections.add("8TeenBoy")
		metadata.content_rating = 'X'
		metadata.title = video_title
		metadata.studio = "8TeenBoy"
