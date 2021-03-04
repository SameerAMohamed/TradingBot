## Trading Bot Based on Sentiment Analysis of Tweets
#How it works:

The program first trains a sentiment analysis model for the tweets and checks to see if the market is open. If the market is open, it requests all trending topics using the Twitter RESTful API, and checks to see if any companies appear on trending according to the list in sp500name.csv.
Afterwards, the program searches Twitter for a mix of the most recent and most popular tweets, extracts the tweet strings, and transforms them into strings useful for sentiment analysis, and loads them into a list for each company.
The strings associated with each company are then loaded into the sentiment analysis model, and the average of the sentiment for each tweet per company is then returned.
If a companies' sentiment then exceeds a threshold, it is either bought or short-bought using the tickers in sp500ticker.csv and calling the Alpaca brokerage RESTful API.
This repeats until 5 minutes before the end of the trading day where it sends a request to close all positions. Once the trading day closes, the program sleeps until 5 minutes before opening where it begins to check every 5 seconds if the market is open.

# File structure
The sp500name.csv file contains the names of all the companies watched.

The sp500ticker.csv file contains the names of all companies watched.

Note: These are not the SP500. The contain many high-profile companies from there though.


sentiment.py contains methods used for sentiment analysis.

methods.py contains methods used for interacting with trading API.

main.py is the main file and connects to the Twitter API.