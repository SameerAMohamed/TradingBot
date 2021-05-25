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
key = [API KEY]
keySecret = [API KEY]
bearerToken = [API KEY]
auth = bearerToken
currentTime = time.time()
# Authentication stuff for Alpaca
base_endpoint = 'https://paper-api.alpaca.markets'
api_key_id = [API KEY]
secret_key = [API KEY]

api = tradeapi.REST(api_key_id, secret_key, base_url=base_endpoint)
account = api.get_account()
clock = api.get_clock()

# Read in all common names of brands from CSVs
common_names_df = pd.read_csv('sp500name.csv', encoding='ISO-8859-1')
common_names_list = common_names_df.values.tolist()

# Read in all tickers of brands from csvs
commonTickersDF = pd.read_csv('sp500ticker.csv', encoding='ISO-8859-1')
commonTickersList = commonTickersDF.values.tolist()

# Create a dictionary for the tickers:names
company_dict = dict(zip(common_names_list, commonTickersList))

# Create database and cursor to store order information in
db = sqlite3.connect(":memory:")
cursor = db.cursor()
cursor.execute(
    'CREATE TABLE orders(runcount INTEGER PRIMARY KEY, tickers TEXT, time TEXT, shares TEXT, price TEXT, side TEXT)')
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

# Run the body of the program
while 1 == 1:
    clock = api.get_clock()
    is_market_open = clock.is_open
    while is_market_open:
        try:
            # Find out what time close will happen
            end_timer = time.time()
            if runcount == 0 or runcount == 1:
                clock = api.get_clock()
                closing_time = clock.next_close.replace(tzinfo=datetime.timezone.utc).timestamp()
                current_time = clock.timestamp.replace(tzinfo=datetime.timezone.utc).timestamp()
                time_to_close = closing_time - current_time
                start_timer = time.time()
            # Sell when it's 5 minutes to close
            if (time_to_close - (end_timer - start_timer)) < (60 * 5) and time_to_close > 0:
                while is_market_open:
                    print("Market closing soon.  Closing positions.")

                    order_stuff().close_all_positions(runcount, cursor)
                    clock = api.get_clock()
                    is_market_open = clock.is_open
                    time.sleep(5)
            if not is_market_open:
                break

            start_time = time.time()
            us_trends = requests.get(endpoint, headers=headers).json()
            us_trends = us_trends[0]
            stop_words = stopwords.words('english')

            # Find the names of the companies that are trending by checking if each company is trending within a list
            # We have to iterate through each list instead of checking sets because the trend may contain the company
            # name instead of matching the exact name

            nameList = []  # List of names that are trending to be populated

            for term in common_names_list:
                term = term[0].lower()
                for i in range(len(us_trends['trends'])):
                    sub_words = us_trends['trends'][i]['name'].lower().split(' ')
                    if term in sub_words:
                        nameList.append(term)

            # Filter out any replicates in nameList
            nameList = list(dict.fromkeys(nameList))

            # Now we use the dictionary to generate the ticker list
            tickerList = [company_dict[name] for name in nameList]

            # Now that we have the indices of the companies that are trending, we must search for each,
            # sample n tweets, and analyze them for sentiment. We will parse tweets that are searched for into a list
            # of strings before here sentiment.py will be used to analyze their sentiments

            # Create a list of lists in tweet_texts_final
            tweet_texts_final = []
            for names in nameList:
                names = names[0]
                numberOfTweets = 100  # Up to 100, but does not always have data to take
                searchEndpoint = f'https://api.twitter.com/1.1/search/tweets.json?q={names}&count={numberOfTweets}&lang=en&result_type=popular'
                searchedTweets = requests.get(searchEndpoint, headers=headers).json()

                # Get the text of the target tweets into a list
                tweet_texts = [searchedTweets['statuses'][i]['text'] for i in
                               range(len(searchedTweets['statuses'][:]) - 1)]

                for i in range(len(tweet_texts)):
                    tweetHolder = tweet_texts[i].split(': ')  # split into before and after the colon
                    if len(tweetHolder) > 1:
                        tweet_texts[i] = tweetHolder[1]
                    tweet_texts[i] = re.sub('\W+', ' ', tweet_texts[i])

                tweet_texts_final.append(tweet_texts)

            # tweet_texts_final is now a SENSIBLE list of lists of all strings to be processed for
            # sentiment----------------------------------------------------- Find the sentiment for the tweet texts

            # Generate a list of tickers we have bought
            portfolio = api.list_positions()
            portfolio_ticker_list = [position.symbol for position in portfolio]

            total_sentiment = []
            # Analyze sentiment of the tweets in tweet_texts_final and
            for i in range(len(tweet_texts_final)):
                ticker = tickerList[i][0]
                if tickerList[i] not in portfolio_ticker_list:  # Avoid overwriting current orders
                    print(f'Calculating total sentiment for {tickerList[i]}...')
                    before_time = time.time()
                    total_sentiment.append(execute_sentiment(tweet_texts_final[i], classifier))
                    print(f'total sentiment is {total_sentiment}')
                    print('it took ', (time.time() - before_time), 'seconds to determine the sentiment of this topic')

            # We now have total_sentiment as a measure of the sentiment around that brand. Now we must place an order
            # based on the sentiment

            for i in range(len(tickerList) - 1):
                targetTicker = tickerList[i][0]
                if targetTicker not in portfolio_ticker_list:
                    if total_sentiment[i] > 0.1:
                        print(
                            f"{targetTicker} has surpassed the sentiment threshold to buy and is not in the "
                            f"portfolio. Attempting to buy {targetTicker}.")
                        order_stuff().buying(targetTicker, portfolio_ticker_list, runcount, cursor)
                    elif total_sentiment[i] < -0.65:  # Look for what targetTicker and totalSentiment are
                        print(
                            f"{targetTicker} has surpassed the sentiment threshold to short and is not in the "
                            f"portfolio. Attempting to short {targetTicker}.")
                        order_stuff().shorting(targetTicker, portfolio_ticker_list, runcount, cursor)
                    else:
                        print("The sentiment is not outstanding enough to place a trade.")

            # ---------------------------------------------------------------------------------------------------------
            # Commit to the database
            db.commit()
            print("My program took", time.time() - start_time, "to run for the", runcount, " time")
            if (time.time() - start_time) < 30:
                print('sleeping until 30 seconds...')
                time.sleep(30 - (time.time() - start_time))

            runcount += 1

        except:
            print("There was an issue collecting or analyzing data. Sleeping for 10 seconds and retrying.")
            time.sleep(10)

    # When the market is not open
    else:
        opening_time = clock.next_open.replace(tzinfo=datetime.timezone.utc).timestamp()
        current_time = clock.timestamp.replace(tzinfo=datetime.timezone.utc).timestamp()
        timeToOpen = opening_time - current_time

        # Set time to sleep to 5 minutes, unless the market is about to open in 5 minutes in which case sleep for .5 sec
        if timeToOpen > 300:
            sleep_time = timeToOpen - 300.01
        else:
            sleep_time = 0.5

        print('Market is not open... Checking again in ', x_time, ' seconds')
        clock = api.get_clock()
        is_market_open = clock.is_open

        # Sleep until allotted time and reset the runcount
        time.sleep(x_time)
        runcount = 0
        clock = api.get_clock()
        
        # Check if market is open
        is_market_open = clock.is_open

        if timeToOpen < 0:
            is_market_open = True

        if is_market_open:
            print("Market has opened")
        else:
            print("Market is not open")
