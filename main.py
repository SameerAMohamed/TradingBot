import datetime
import time

import alpaca_trade_api as tradeapi
import pandas as pd
import sqlite3
import regex as re
import requests
from nltk.corpus import stopwords

from methodsFile import order_stuff
from sentiment import execute_sentiment, sentiment_analysis


runcount = 1
# twitter authentication
key = 'DH33Fyb6sSslFzV2zEbuHiKLn'
keySecret = 'Qw5i5xzDAMgnN4O1nSg58jMFKgk03CTfaKLoP648po1VsE4U8X'
bearerToken = 'AAAAAAAAAAAAAAAAAAAAAAVVIwEAAAAAv1Nr3WPg%2BkPaHNusA9Xgj1CGuig' \
              '%3DT6fqiFJchskx3gJnmAnSr9TLig4CbjvCvvQTZKJKLpNvwbuO7r '
auth = bearerToken
currentTime = time.time()
# Authentication stuff for Alpaca
base_endpoint = 'https://paper-api.alpaca.markets'
api_key_id = 'PKKSZY7HUXSG54X8GV2Q'
secret_key = 'WdqcOFVTPoPYxzzV0q8UW76ad0rpcjfz0vEucaj5'

api = tradeapi.REST(api_key_id, secret_key, base_url=base_endpoint)
account = api.get_account()
clock = api.get_clock()

# Read in all common names of brands from csvs
commonNamesDF = pd.read_csv('sp500name.csv', encoding='ISO-8859-1')
commonNamesList = commonNamesDF.values.tolist()
# Read in all tickers of brands from csvs
commonTickersDF = pd.read_csv('sp500ticker.csv', encoding='ISO-8859-1')
commonTickersList = commonTickersDF.values.tolist()
# Create database and cursor to store order information in
db = sqlite3.connect(":memory:")
cursor = db.cursor()
cursor.execute('CREATE TABLE orders(runcount INTEGER PRIMARY KEY, tickers TEXT, time TEXT, shares TEXT, price TEXT, side TEXT)')
db.commit()
# _____________________________________________________________________________________________________________________
headers = {"Authorization": f"Bearer {bearerToken}"}
data = {"ip": "1.1.2.3"}
woid_us = 23424977
woid_world = 1
print('-------------------------------------------------------------------------------------')
endpoint = f"https://api.twitter.com/1.1/trends/place.json?id={woid_us}"
# Train the sentiment analysis model
before_train_time = time.time()
classifier = sentiment_analysis()
print('It took ', time.time() - before_train_time, ' seconds to train the sentiment model.')
while 1 == 1:
    clock = api.get_clock()
    is_market_open = clock.is_open
    while is_market_open == True:
        try:
            # Find out what time close will happen - CALL CLOCK FEWER TIMES
            end_timer = time.time()
            if runcount == 0 or runcount == 1:
                clock = api.get_clock()
                closingTime = clock.next_close.replace(tzinfo=datetime.timezone.utc).timestamp()
                currTime = clock.timestamp.replace(tzinfo=datetime.timezone.utc).timestamp()
                timeToClose = closingTime - currTime
                start_timer = time.time()
            # Sell when it's 5 minutes to close
            if (timeToClose - (end_timer - start_timer)) < (60 * 5) and timeToClose > 0:
                while is_market_open == True:
                    print("Market closing soon.  Closing positions.")

                    order_stuff().close_all_positions(runcount, cursor)
                    clock = api.get_clock()
                    is_market_open = clock.is_open
                    time.sleep(5)
            if is_market_open == False:
                break

            start_time = time.time()
            us_trends = requests.get(endpoint, headers=headers).json()
            us_trends = us_trends[0]
            stop_words = stopwords.words('english')

            counter = 0
            counterMeasure = 0
            index = 0
            indexList = []
            for term in commonNamesList:
                term = term[0].lower()
                for i in range(0, len(us_trends['trends'])):
                    counterMeasure = counterMeasure + 1
                    # Split us_trends['trends'][i]['name'].lower() by space
                    subWords = us_trends['trends'][i]['name'].lower().split(' ')
                    if term in subWords:  # or us_trends['trends'][i]['name'].lower().startswith(term): DON'T KNOW IF
                        # I CAN GET THIS TO WORK PROPERLY
                        counter = counter + 1
                        indexList.append(index)
                index = index + 1

            # Filter out any replicates in indexList
            indexList = list(dict.fromkeys(indexList))

            tickerList = []
            nameList = []
            # We must identify each ticker for the company. We have organized the CSVs so they should have the same
            # index
            for placements in indexList:  # we generate tickerList which is a list of all the tickers that are trending
                tickerList.append(commonTickersList[placements])
                nameList.append(commonNamesList[placements])

            # Now that we have the indices of the companies that are trending, we must search for each,
            # sample n tweets, and analyze them for sentiment We will parse tweets that are searched for into a list
            # of strings before here sentiment.py will be used to analyze their sentiments
            tweetTexts = []
            tweetTexts2 = []
            for names in nameList:
                names = names[0]
                numberOfTweets = 100  # Up to 100, but does not always have data to take
                searchEndpoint = f'https://api.twitter.com/1.1/search/tweets.json?q={names}&count={numberOfTweets}&lang=en&result_type=popular'
                searchedTweets = requests.get(searchEndpoint, headers=headers).json()

                tweetTexts = []
                for i in range(0, len(searchedTweets['statuses'][:]) - 1):
                    tweetTexts.append(searchedTweets['statuses'][i]['text'])

                for i in range(0, len(tweetTexts)):
                    tweetHolder = tweetTexts[i].split(': ')  # split into before and after the colon
                    if len(tweetHolder) > 1:
                        tweetTexts[i] = tweetHolder[1]
                    tweetTexts[i] = re.sub('\W+', ' ', tweetTexts[i])
                tweetTexts2.append(tweetTexts)

            # tweetTexts is now a SENSIBLE list of all strings to be processed for
            # sentiment----------------------------------------------------- Find the sentiment for the tweet texts
            totalSentiment = []
            length_of_tweetTexts = len(tweetTexts2)
            # Generate a list of tickers we have bought
            portfolio_ticker_list = []
            portfolio = api.list_positions()
            for position in portfolio:
                portfolio_ticker_list.append(position.symbol)
            for i in range(0, len(tweetTexts2)):
                ticker = tickerList[i][0]
                if tickerList[i] not in portfolio_ticker_list:
                    print(f'Calculating total sentiment for {tickerList[i]}...')
                    before_time = time.time()
                    totalSentiment.append(execute_sentiment(tweetTexts2[i], classifier))
                    print(f'total sentiment is {totalSentiment}')
                    print('it took ', (time.time() - before_time), 'seconds to determine the sentiment of this topic')
            # We now have totalSentiment as a measure of the sentiment around that brand. Now we must place an order
            # based on the sentiment

            for i in range(0, len(tickerList)):
                if i == len(tickerList):
                    break
                targetTicker = tickerList[i][0]
                if targetTicker not in portfolio_ticker_list:
                    if totalSentiment[i] > 0.1:
                        print(
                            f"{targetTicker} has surpassed the sentiment threshold to buy and is not in the "
                            f"portfolio. Attempting to buy {targetTicker}.")
                        order_stuff().buying(targetTicker, portfolio_ticker_list, runcount, cursor)
                    if totalSentiment[i] < -0.65:  # Look for what targetTicker and totalSentiment are
                        print(
                            f"{targetTicker} has surpassed the sentiment threshold to short and is not in the "
                            f"portfolio. Attempting to short {targetTicker}.")
                        order_stuff().shorting(targetTicker, portfolio_ticker_list, runcount, cursor)

            # ---------------------------------------------------------------------------------------------------------
            # Commit to the database
            db.commit()
            print("My program took", time.time() - start_time, "to run for the", runcount, " time")
            if (time.time() - start_time) < 30:
                print('sleeping until 30 seconds...')
                time.sleep(30 - (time.time() - start_time))

            runcount = runcount + 1
        except:
            print("There was an issue collecting or analyzing data. Sleeping for 10 seconds and retrying.")
            time.sleep(10)
    while is_market_open == False:
        openingTime = clock.next_open.replace(tzinfo=datetime.timezone.utc).timestamp()
        currTime = clock.timestamp.replace(tzinfo=datetime.timezone.utc).timestamp()
        timeToOpen = openingTime - currTime

        if timeToOpen > 300:
            x_time = timeToOpen - 300.01
        else:
            x_time = 0.5
        print('Market is not open... Checking again in ', x_time, ' seconds')
        clock = api.get_clock()
        is_market_open = clock.is_open
        time.sleep(x_time)
        runcount = 0
        clock = api.get_clock()
        is_market_open = clock.is_open
        if timeToOpen < 0:
            is_market_open = True
        if is_market_open == True:
            print("Market has opened")
        else:
            print("Market is not open")
