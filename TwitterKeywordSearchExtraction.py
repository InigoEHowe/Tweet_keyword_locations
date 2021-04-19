# -*- coding: utf-8 -*-
"""
Created on Fri Apr 16 21:39:53 2021

@author: ih345
"""
import tweepy as tw
import pandas as pd
import pickle
import country_list
import numpy as np
import re
import country_converter  as coco
import geopandas
import plotly as plt

# Define keys needed to tweet (keep these secure)
# These need to be filled in
consumer_key= ''
consumer_secret= ''
access_token= ''
access_token_secret= ''

auth = tw.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tw.API(auth, wait_on_rate_limit=True)


def extract_twitter_data(search_words):
    # Define the search term and the date_since date as variables
    date_since = "2016-04-17"
    
    # Extract who is searching for the keyword
    tweets = tw.Cursor(api.search, 
                               q=search_words,
                               since=date_since).items(30000)
    
    users_locs = [[tweet.user.screen_name, tweet.user.location, tweet.user.followers_count, tweet.retweet_count, tweet.favorite_count, tweet.text ] for tweet in tweets]
    
    # Put the data into a pandas dataframe
    dataframe = pd.DataFrame(data=users_locs, 
                        columns=['user', "location","follower count","tweet retweets","tweet likes","tweet text"])
    
    return dataframe

word = 'immunology'
df = extract_twitter_data(word)
df.to_pickle(word)

# Method 1: do they have the country just written out
def process_location_names(dataframe):

  # create a copy of the dataframe to edit
  locations_dataframe_country_codes = dataframe.copy()

  # Track which rows have been converted
  not_converted = np.ones(locations_dataframe_country_codes.size)

  # Deal with those pesky americans
  states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA", 
          "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
          "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
          "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
          "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

  # loop over different languages
  for language in country_list.available_languages():
    # Make a dictionary that turns the locations into country codes
    my_map = dict(country_list .countries_for_language(language))
    country_codes = {v.upper(): k.upper() for k, v in my_map.items()}

    for i in range(dataframe['location'].size):
      # split the text by commas and dashes
      user_country = dataframe['location'][i]
      user_country_split = [x.strip().upper() for x in re.split('; |, |-',user_country)]
      for word in user_country_split:
        try:
          locations_dataframe_country_codes['location'][i] = country_codes[word]
          not_converted[i] = 0
        except KeyError:
            pass 

        # Check if they used states rather than country
        for state in states:
          if word == state:
            locations_dataframe_country_codes['location'][i] = 'US'
            not_converted[i] = 0

  return locations_dataframe_country_codes,not_converted 

def process_data(df):

    # Drop duplicate users
    locations_dataframe = df.drop_duplicates()
    
    # Get rid of empty cells
    locations_dataframe_cleaned = locations_dataframe.replace('', np.nan)
    locations_dataframe_cleaned = locations_dataframe_cleaned[locations_dataframe_cleaned['location'].notna()]
    
    # This messes up the indices so these need to be replaces
    locations_dataframe_cleaned = locations_dataframe_cleaned.reset_index(drop='True')
    
    # Process locations to attemp to turn them into something readable
    locations_dataframe_country_codes,not_converted =  process_location_names(locations_dataframe_cleaned)
    
    # make a list of the country codes
    english_country_code_dict = dict(country_list .countries_for_language('en'))
    country_codes = list(english_country_code_dict.keys())
    
    # If a row does not contain a valid country code then get rid of it
    for i in range(locations_dataframe_country_codes['location'].size):
      if locations_dataframe_country_codes['location'][i] not in country_codes:
        locations_dataframe_country_codes = locations_dataframe_country_codes.drop(labels=i, axis=0)
        
    # This messes up the indices so these need to be replaces
    locations_dataframe_country_codes = locations_dataframe_country_codes.reset_index(drop='True')
    
    # count the number of times each country comes up
    country_counts = locations_dataframe_country_codes['location'].value_counts()
    
    # Make new dataframe
    country_counts_list = pd.DataFrame(list(zip(country_counts.index, country_counts)),
                   columns =['country_code', 'count'])
    
    # Convert to iso-a3
    country_counts_list['country_code'] = coco.convert(names=country_counts_list['country_code'], to='ISO3')
    
    return locations_dataframe_country_codes,country_counts_list

processed,country_counts = process_data(df)


# Load in world map
world = geopandas.read_file(geopandas.datasets.get_path('naturalearth_lowres'))

# Normalise the data
country_counts['count'] = country_counts['count']/(country_counts['count'].max())

# Make new col with the data from the word
world_count = np.zeros(world.size)

for i in range(len(world_count)):
  for j in range(country_counts.size):
    if world['iso_a3'][i] == country_counts['country_code'][j]:
      world_count[i] = country_counts['country_code'][j]
      
      
# Load in world map
world = geopandas.read_file(geopandas.datasets.get_path('naturalearth_lowres'))

# Make new col with the data from the word
world['count'] = np.zeros(world['iso_a3'].size)

for i in range(country_counts['country_code'].size):
  index = world['iso_a3'][world['iso_a3']==country_counts['country_code'][i]].index.values
  world['count'][index] = np.log10(country_counts['count'][i])
  
# Plot map
fig, ax = plt.subplots(figsize=(10,10))

world.plot(column='count',
  ax=ax,
  cmap='Blues',
  legend=True,
  legend_kwds={'label': "log(Number of Twitter users)",
  'orientation': "horizontal"})
ax.axis('off')