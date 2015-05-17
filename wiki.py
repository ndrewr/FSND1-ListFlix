#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# WIKI app -> editable content pages for logged-in users
#
#import sys
#sys.path.insert(0, 'modules')
#sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib')) #using 'os' method to get filepath


import webapp2
import jinja2
import logging, os
import time
from datetime import datetime
from google.appengine.api import users, memcache
from google.appengine.ext import db
#from bs4 import BeautifulSoup
#import scrubber  #for safe escaping html input in Post content
from user_accounts import *
from memcache_tools import *

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA_ENV = jinja2.Environment(loader = jinja2.FileSystemLoader(TEMPLATE_DIR), autoescape=True)
#scrubber = Scrubber(autolink = True)

LOGGED_IN = False
#Regular expressions
PAGE_RE = r'(/(?:[a-zA-Z0-9_-]+/?)*)'
LOGOUT_RE = r'(/(?:[a-zA-Z0-9_-]+/?)*)?'
HISTORY_RE = r'(/(?:[a-zA-Z0-9_-]+/?)*)(/(?:[0-9]+/?)*)?'
#QUESTION: is this version re even needed!? if I remove the version string from logout_re2 the handler still works...
VERSION = r'(\?v=[0-9]+)?' # it turns out this is not even needed...
#query type params are auto handled/not matched OR handler mapping defaults to closest match

class User(db.Model):
	name = db.StringProperty(required = True)
	password = db.StringProperty(required = True)
	email = db.StringProperty(required = False)

class Post(db.Model):
	title = db.StringProperty(required = True)
	content = db.TextProperty(required = False)
	created = db.DateTimeProperty(auto_now_add = True)
	last_modified = db.DateTimeProperty(auto_now = True)
	creator = db.StringProperty(required = True)

	@classmethod
	def newPost(cls, title, creator, content=""):
		newPost = Post(title=title, content=content, creator=creator)
		newPost.put()
		time.sleep(1)
		updatePostList(newPost)

	#Steve makes this a static method; needs no ref to 'self'
	@staticmethod
	def parentKey(topic):
		return db.Key.from_path('Post', topic or 'default_post')

	def prettyDate(self):
		return self.created.strftime('%c')
	def render(self):
		self._render_text(self.content.replace('/n', '<br>'))
		return render_str("post.html", p = self)

# Helper functions
def postTitleFromPath(editPage=False):
	if editPage: 
		return self.request.path.split('edit/')[1]
	else:
		return self.request.path.split('/')[1]
	#return post_title.split('/')[1]

def login(self, username):
	self.response.headers.add_header('Set-Cookie', 'user_id=%s; Path=/' %str(makeSecure(username)))
	loggedInState(True)
def logout(self):
	self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')
	loggedInState(False)
#if param is passed in the method sets new state and returns; else simply returns current state
def loggedInState(state=None):
	global LOGGED_IN
	if state != None:
		LOGGED_IN = state
	return LOGGED_IN

'''global values are accessible anywhere...but only modifiable with the 'global borabora' statement
	this means the extra functionality in loggedInState is actually unneeded. Classes below could just directly
	access the value of state''' 
def logcheck():
	return LOGGED_IN

def startTopic(self, title, content):
	#create a new list initilized with Post entity
	logging.error("StartTopic: setting up a new topic called %s!" %title)
	new_topic = Post(title=title, parent=Post.parentKey(title), content=content, creator=getUsername(self))
	new_topic.put()
	time.sleep(1)
	#put this topic list in memcache
	post_list = memcache.get('allPosts')
	post_list[title] = [new_topic]
	memcache.set('allPosts', post_list)

# Handlers
class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)
	def render_str(self, template, **params):
		t = JINJA_ENV.get_template(template)
		return t.render(params)
	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))
	def not_found(self):
		self.error(404)
		self.write('<h1>404; Not Found</h1>Sorry, valiant valued visitor, but that page does not exist.')

class MainHandler(Handler):
    def get(self):
    	welcome_string = 'Welcome, %s' %getUsername(self)
    	print('from main...loginCheck is %s' %logcheck())
        self.render('front.html', logged_in=loggedInState(), welcome_string=welcome_string, posts=topPosts())

class HistoryPage(Handler):
	def get(self, post_title=""):
		title = post_title.split('/')[1]
		topic_list = memcache.get('allPosts')[title]
		#change db structure to save LISTS under each title key.
		#wikipage, when accessing content then only takes first item in list
		#BUT history page takes whole list and renders out similar to how current front page does with topPosts
		#Utilize the 'created' date in the page layout, order will be built by adding newest items to top (PUSH op) 
		#this means every '_edit' action now creates a new entity; must be inserted both into db and memcache topic list
		self.render("history.html", title=title, username=getUsername(self), logged_in=loggedInState(), posts=topic_list)

	#sends user to a permalink where content can be edited and submitted
	# question: how is 'post_title' auto-magically supplied to the template render w/o me specifying
class EditPageHandler(Handler):
	def get(self, post_title=""):
		#check first if user is logged in
		if not loggedInState():
			self.redirect('/login')
		else:	#get the post user wants to edit
			title = (self.request.path).split('edit/')[1]
			post_body = ""
			if checkWiki(title):  #wiki page already exists; fetch content and write to page
				#v2.0 uses lists of Post entities...so modify accordingly. retrieve version# from query param?
				version_index = self.request.get('v')
				if version_index:
					logging.error("EditPH: Found the post! Fetching the post content...old post index is %s" %version_index)
					post_body = memcache.get('allPosts').get(title)[int(version_index)].content 
				else:
					post_body = memcache.get('allPosts').get(title)[0].content 
			else: #This is the first instance of this title...create a list initialized with 1st entity
				logging.error("EditPH: New post! Preparing a new list in db with 1st entry...")
			#render the page with content (if prior content exists, blank otherwise)
			self.render('postedit.html', post_title=title, post_body=post_body, edit_mode=True, logged_in=loggedInState(), username=getUsername(self))
	def post(self, post_title=""):
		title = post_title.split('/')[1]
		new_content = self.request.get('content')
		if checkWiki(title):
			logging.error("EditPH POST method: update of topic! Appending....")
			#existing topic: append to the list in memcache and add new same-parent entity in db
			topic_update = Post(title=title, parent=Post.parentKey(title), content=new_content, creator=getUsername(self))
			topic_update.put()
			time.sleep(1)
			post_list = memcache.get('allPosts')
			post_list[title].insert(0, topic_update)
			memcache.set('allPosts', post_list)
		else: #new topic
			logging.error("EditPH POST method: New post! Creating list in db with 1st entry...")
			startTopic(self, title, new_content)
		#updatePostContent(title, new_content)
		topPosts(True)
		self.redirect('%s' %post_title)

class WikiPageHandler(Handler):
	def get(self, *args):
		#check if the page exists in the db...if not, create a new Post object and redirect to EditPageHandler
		title = (self.request.path).split('/')[1]
		version = self.request.get('v')
		logging.error("WikiPH: looking for version variable...value is %s" %version)
		if not checkWiki(title):
			if loggedInState():
				logging.error("WikiPH: New post! Preparing to create db entry...%s" %title)
				if not version:
					logging.error("WikiPH: There is no version number specified...default to 0")
					self.redirect('/_edit/%s' %title)
				else:
					#construct a query url for edit handler
					self.redirect('/_edit/%s/?v=%s' %(title, version))
			else:
				#self.not_found()
				self.redirect('/login')
		else:
			if not version:
				post_body = memcache.get('allPosts').get(title)[0].content 
			else:
				post_body = memcache.get('allPosts').get(title)[int(version)].content
				logging.error('WikiPH: will redirect to version %s of %s topic' %(version, title))
			self.render('postedit.html', post_title=title, post_body=post_body, edit_mode=False, logged_in=loggedInState(), username=getUsername(self), version=version)
		
class SignupHandler(Handler):
	def get(self, username="", email="", error=""):
		self.render('signup.html', username=username, email=email, error=error)
	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')
		verify = self.request.get('verify')
		email = self.request.get('email')
		
		all_OK, error = check_SignUp(username, password, verify, email)
		if(all_OK):
			newUser = User(name=username, password=makeExtraSecure(password), email=email)
			User.put(newUser)
			updateUserList(newUser)
			login(self, username)
			self.redirect('/')
		else:
			self.render("signup.html", username=username, email=email, error=error)

#login system will return user to page they login by using passed in url agr 'post_title'
#want to transition to 'invisible' system using http 'referer' header ...success?
class LoginHandler(Handler):
	def get(self, *args):
		if loggedInState():
			self.redirect('/')
		else: self.render('login.html')
	def post(self, *args):
		username = self.request.get('username')
		password = self.request.get('password')
		loginCheck = verifyLogin(username, password)
		if loginCheck == 'OK':
			login(self, username)
			#POST method referer addy is actually the login url...so modify it by strippin '/login'
			next_url = self.request.headers.get('referer', '/').split('/login')[1]
			self.redirect(next_url)
		else:
			self.render('login.html', error=loginCheck)

class LogoutHandler(Handler):
	def get(self, post_title="/"):
		logout(self)
		#check if logout request was sent from wiki page. If so, redirect back. Else goto front		
		if post_title is None:
			self.redirect('/')
		else:
			next_url = self.request.headers.get('referer', '/')
			self.redirect(next_url)
	
class PostDeleteHandler(Handler):
	def get(self, post_title=""):
		title = post_title.split('/')[1]
		#remove from the main db ...
		q = Post.all().filter("title =", title)
		db_post = q[0] #same as q.get() for first index value
		db_post.delete()
		#...then from cache entries
		post_list = memcache.get('allPosts')
		del post_list[title]
		memcache.set('allPosts', post_list)
		#delete from top posts cache...will need to try/catch an index() search in the list
		key = 'topPosts'
		posts = memcache.get(key)		
		for post in posts:
			#LBYL - look before you leap style of coding
			#if post.title == title:

			#EAFP - Easier Ask for Forgiveness than Permission style of coding (more pythonic)
			try:
				#del posts[posts.index(post)] #roundabout way to delete the object at certain index
				posts.remove(post) #should be fine since if conditional tests for presence
				memcache.set('topPosts', posts)
				topPosts(update=True)
			except ValueError:
				pass
		self.redirect('/')

app = webapp2.WSGIApplication([
    ('/', MainHandler), 
    ('/signup', SignupHandler), 
    ('/login'+ LOGOUT_RE, LoginHandler), 
    ('/logout' + LOGOUT_RE, LogoutHandler),
    ('/delete' + PAGE_RE, PostDeleteHandler), 
    ('/_edit' + PAGE_RE, EditPageHandler), 
    ('/_history' + PAGE_RE, HistoryPage), 
    #(PAGE_RE + VERSION, WikiPageHandler), 
    (PAGE_RE, WikiPageHandler), 
], debug=True)
