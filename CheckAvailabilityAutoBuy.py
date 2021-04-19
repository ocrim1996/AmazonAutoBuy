import requests
from bs4 import BeautifulSoup
from twilio.rest import Client
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import os
import time
import secrets

# Insert the URLs of the products you want to check (These below are an example).
urls = ["https://www.amazon.it/dp/B08HN4DSTC", "https://www.amazon.fr/dp/B08HN4DSTC", "https://www.amazon.es/dp/B08HN4DSTC", "https://www.amazon.de/dp/B08HN4DSTC"]

# Set the maximum price, there is a maximum price for each url (replace my numbers with your maximum prices).
MAX_PRICE = [800, 900, 700, 1000]

# It is used later to check that availability is on Amazon and not at other sellers.
false_availability_list = ["Disponibile presso questi venditori.", "Voir les offres de ces vendeurs.", "Disponible a través de estos vendedores.", "Erhältlich bei diesen Anbietern.", "Available from these sellers."]

# Header is useful to spoof your request so that it looks like it comes from a legitimate browser.
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0'}

# Twilio data.
TWILIO_SID = secrets.twilio_sid
TWILIO_TOKEN = secrets.twilio_token
TWILIO_NUMBER = secrets.twilio_number
NUMBER_TO_CALL = secrets.number_to_call
TWILIO = Client(TWILIO_SID, TWILIO_TOKEN)

# Options for the auto-purchase function.
options = Options()
options.page_load_strategy = 'eager'


# Function to do the price conversion from string to float to be able to check.
def price_conversion(product_price):
    product_price = product_price.replace(" ", "")
    product_price = product_price.replace(".", "")
    product_price = product_price.replace(",", "")
    symbols_to_replace = "€$£"
    for symbol in symbols_to_replace:
        product_price = product_price.replace(symbol, "")
    product_price = product_price.replace(u'\xa0', u'')
    product_price = product_price[:-2] + '.' + product_price[-2:]
    product_price = float(product_price)
    return product_price


# Function to check the correct country of the product.
def get_country(url):
    if "amazon.it" in url:
        product_country = "Amazon.it"
    elif "amazon.fr" in url:
        product_country = "Amazon.fr"
    elif "amazon.es" in url:
        product_country = "Amazon.es"
    elif "amazon.de" in url:
        product_country = "Amazon.de"
    elif "amazon.co.uk" in url:
        product_country = "Amazon.co.uk"
    elif "amazon.com" in url:
        product_country = "Amazon.com"
    else:
        raise Exception("Error in product country")
    return product_country


# Function to send the message on Telegram.
def telegram_bot_sendtext(bot_message):
    bot_token = secrets.bot_token
    bot_chat_id = secrets.bot_chat_id
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chat_id + '&parse_mode=Markdown&text=' + bot_message

    response = requests.get(send_text)

    return response.json()


# Function to call the user via Twilio.
def call():
    TWILIO.calls.create(
        twiml='<Response><Say voice="alice" language="en-US">The product is available</Say></Response>',
        to=NUMBER_TO_CALL,
        from_=TWILIO_NUMBER)


# Function to purchase the product automatically.
def purchase(username, password, item_url, login_country):
    # Use the correct country login page.
    if login_country == "Amazon.it":
        login_url = secrets.login_url_it
    elif login_country == "Amazon.fr":
        login_url = secrets.login_url_fr
    elif login_country == "Amazon.es":
        login_url = secrets.login_url_es
    elif login_country == "Amazon.de":
        login_url = secrets.login_url_de
    elif login_country == "Amazon.co.uk":
        login_url = secrets.login_url_uk
    elif login_country == "Amazon.com":
        login_url = secrets.login_url_com
    else:
        raise Exception("Error in the link")

    '''
    If you are using MacOS, Windows or Linux, you must use this commented command, first downloading "chromedriver"
    from the following link "https://chromedriver.chromium.org" 
    and then copying the file to the project folder.
    '''
    driver = webdriver.Chrome(os.getcwd()+"/chromedriver", options=options)

    '''
    Otherwise if you are using a Raspberry, you have to use this command, but first you have to run the
    following command from the terminal "sudo apt-get install chromium-chromedriver" 
    [https://ivanderevianko.com/2020/01/selenium-chromedriver-for-raspberrypi]
    '''
    # driver = webdriver.Chrome('/usr/lib/chromium-browser/chromedriver', options=options)

    # For logging into Amazon.
    driver.get(login_url)
    driver.find_element_by_xpath(
        '//*[@id="ap_email"]').send_keys(username + Keys.RETURN)
    driver.find_element_by_xpath(
        '//*[@id="ap_password"]').send_keys(password + Keys.RETURN)
    # End of login code.

    # For getting into our product page.
    time.sleep(0.1)
    driver.get(item_url)

    # Once the button is activated, click the "Buy Now" button.
    driver.find_element_by_xpath(
        '//*[@id="buy-now-button"]').click()
    time.sleep(5)

    # After pressing the "Buy Now" button, a modal window opens and the bot confirms the purchase.
    driver.switch_to.frame("turbo-checkout-iframe")
    driver.find_element_by_xpath('//*[@id="turbo-checkout-pyo-button"]').click()
    time.sleep(15)


if __name__ == '__main__':
    # For each product I set the "not_available" variable to True
    not_available = [True for i in range(len(urls))]
    t = time.time()

    # Run the program until all the products are available.
    while any(not_available):

        # All urls are checked cyclically.
        for i in range(len(urls)):
            if not_available[i]:

                # Open the session.
                s = requests.session()
                r = s.get(urls[i], headers=headers)
                r.cookies.clear()
                page_html = r.text

                # Scraping the html page.
                soup = BeautifulSoup(page_html, features="lxml")

                # checking if there is "Out of stock" on a first possible position of html page.
                try:
                    soup.select('#availability .a-color-state')[0].get_text().strip()
                    stock = "Out of Stock"
                    availability_text = "foo"

                except:
                    # checking if there is "Out of stock" on a second possible position of html page.
                    try:
                        soup.select('#availability .a-color-price')[0].get_text().strip()
                        stock = "Out of Stock"
                        availability_text = "foo"

                    except:
                        # checking if there is "Available" on html page.
                        try:
                            soup.select('#availability .a-color-success')[0].get_text().strip()
                            stock = "Available"
                            availability_text = soup.select('#availability .a-color-success')[0].get_text().strip()

                        except:
                            # checking if there is "Buy Now" button on html page.
                            try:
                                buy_now_button_text = soup.find('span', {'id': 'submit.buy-now-announce'}).get_text()
                                stock = "Available"
                                availability_text = "foo"

                            # Error due to amazon anti-scraping.
                            except:
                                stock = "Request Error"
                                availability_text = "foo"

                # checking if the price is present in the html page.
                try:
                    price = soup.select('#priceblock_ourprice')[0].get_text().strip()
                    is_there_price = True
                except:
                    is_there_price = False

                # If the product is available and the availability is on Amazon and not from other sellers.
                if "Available" in stock and availability_text not in false_availability_list and is_there_price is True:

                    # Get correct product country.
                    country = get_country(urls[i])

                    # It takes the price of the product from html page and then does the conversion.
                    price = soup.select('#priceblock_ourprice')[0].get_text().strip()
                    price = price_conversion(price)

                    # It checks that the price of the product is lower than the maximum established.
                    if price <= MAX_PRICE[i]:
                        print("The available product is: " + urls[i])
                        telegram_bot_sendtext("The available product is:\n" + urls[i])
                        telegram_bot_sendtext("The Bot is buying the product \U0001F504 \U0001F6D2")
                        purchase(secrets.email, secrets.password, urls[i], country)
                        telegram_bot_sendtext("The Bot bought the product \U00002705 \U0001F6D2")
                        not_available[i] = False

                        '''
                        The call with Twilio is not necessary, it is used to give a further notification. 
                        If you are not interested, delete the "call()" function.
                        '''
                        call()

        # Every hour the Telegram bot sends you a message that it is working correctly.
        if time.time() - t > 3600:
            now = time.ctime(int(time.time()))
            message_to_me = "Bot is Running \U00002699 \U00002699 \U00002699:\n" + "\U0001F5D3" + str(now)
            telegram_bot_sendtext(message_to_me)
            t = time.time()

    telegram_bot_sendtext("The bot stopped because all the products were bought \U0001F3C1 \U0001F3C1 \U0001F3C1.\n"
                          "If you want to check other products rerun the script \U0001F680 \U0001F680 \U0001F680")
