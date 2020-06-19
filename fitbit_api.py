""" 
Python wrapper class for the Fitbit API. 
Inspired by orcasgit/python-fitbit, written for practice as I learn oauth2.
"""  

import json  
import requests 
import time 
from ratelimit import limits, sleep_and_retry  

class Fitbit:     
	"""
	A simple class for calling the Fitbit WEB API, 
	see https://dev.fitbit.com/build/reference/web-api/

	Handles the oauth2 token refresh process automatically. 
	Rate limited at 145 calls/hour, sleeps and retries when limit reached.

	Attributes:  
	client_id: your Fitbit app client id. 

	client_secret: your Fitbit app client secret.

	access_token: an oauth2 access token.

	refresh_token: the corresponding refresh token.

	expires_at: the unix time at which access_token expires 
				(e.g. 1591749405.1234567). 

	token_update_method: a method accepting a token dict and storing it as a 
						 static file, used to refresh tokens as they expire. 
	""" 

	def __init__(self, client_id=None, client_secret=None, 
			     access_token=None, refresh_token=None, 
				 expires_at=None, token_update_method=None):       

		self.client_id = client_id  
		self.client_secret = client_secret 
		self.access_token = access_token 
		self.refresh_token = refresh_token 
		self.expires_at = expires_at  
		self.token_update_method = token_update_method

	def refresh_tokens(self): 
		""" 
		Called when access_token has expired. Use a valid refresh_token to 
		refresh the access_token, refresh_token and expires_at attributes. 
		Calls the token_update_method to store the updated token information. 
		"""  

		# Get new token dict from server 
		response = requests.post(
				url='https://api.fitbit.com/oauth2/token', 
				data={
					"client_id": self.client_id, 
					"grant_type": "refresh_token",
					"refresh_token": self.refresh_token  
					}, 
				auth=(self.client_id, self.client_secret)
				)    

		tokens = response.json()  

		# Add the "expires_at" key:value pair 
		expires_in = float(tokens['expires_in']) 
		tokens['expires_at'] = time.time() + expires_in 

		# Update tokens in Fitbit instance 
		self.access_token = tokens['access_token']
		self.refresh_token = tokens['refresh_token'] 
		self.expires_at = tokens['expires_at'] 
			
		# Update static tokens file 
		if self.token_update_method: 
			self.token_update_method(tokens)  

	@sleep_and_retry 
	@limits(calls=125, period=3600) 
	def make_request(self, *args, **kwargs): 
		""" Wrapper for the request method. """ 
		response = requests.request(*args, **kwargs)

		if response.status_code != 200:
			raise Exception('API response: {}'.format(response.status_code))
		return response 

	def get_resource(self, resource_url):   
		""" 
		Check and refresh token if invalid, then make GET request.
		See https://dev.fitbit.com/build/reference/web-api/ for endpoints. 
		""" 
		# Check if tokens are expired 
		if (not self.expires_at) or (time.time() >= float(self.expires_at)): 
			self.refresh_tokens() 

		# Make request, now with valid tokens 
		headers = {'Authorization': 'Bearer {}'.format(self.access_token)} 
		return self.make_request('GET', url=resource_url, headers=headers)   

