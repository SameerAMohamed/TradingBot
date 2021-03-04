# Trading Bot Based on Sentiment Analysis of Tweets
## How it works:

The program first trains a sentiment analysis model for the tweets and checks to see if the market is open. If the market is open, it requests all trending topics using the Twitter RESTful API, and checks to see if any companies appear on trending according to the list in sp500name.csv.
Afterwards, the program searches Twitter for any company that appeared on trending and returns a mix of the most recent and most popular tweets for that company. After, it extracts the tweet strings from the returned JSON, and transforms them into strings useful for sentiment analysis. Finally loads those strings into a list corresponding to each trending company.

The strings associated with each company are then loaded into the sentiment analysis model, and the average of the sentiment for each tweet per company is then returned.
If a companies' average sentiment then exceeds a threshold (positive or negative), it is either bought or short-sold using the tickers in sp500ticker.csv and calling the Alpaca brokerage RESTful API. When these orders are made, the resulting order will be stored in a NoSQL database using an SQL Query.

This repeats until 5 minutes before the end of the trading day where it sends a request to close all positions. Once the trading day closes, the program sleeps until 5 minutes before opening where it begins to check every 5 seconds if the market is open.

## File structure
The sp500name.csv file contains the names of all the companies watched.

The sp500ticker.csv file contains the names of all companies watched.

Note: These are not the SP500. The contain many high-profile companies from there though.


sentiment.py contains methods used for sentiment analysis.

methods.py contains methods used for interacting with trading API.

main.py is the main file and connects to the Twitter API.
