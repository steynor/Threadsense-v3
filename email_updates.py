from dash import Output, Input, html, callback, dcc, Dash,State,callback_context,clientside_callback
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import pandas as pd
from selenium.webdriver.chrome.service import Service
from fake_useragent import UserAgent
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select,WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
import requests
from bs4 import BeautifulSoup
import concurrent.futures
from selenium.webdriver.common.keys import Keys
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time as time

def fetch_page_data(url):
    r = requests.get(url)
    data = r.text
    return data

# Function to extract part of the string after the first hyphen, replace hyphens with spaces, and capitalize each word
def process_string(text):
    parts = text.split('-', 1)  # Split at the first hyphen
    if len(parts) > 1:
        modified_string = parts[1].replace('-', ' ').title()
        if modified_string.endswith('/'):
            modified_string = modified_string[:-1]  # Remove the last hyphen if present
        return modified_string
    return text

############################################################
# Function to get ebay page data and isolate relevant fields
############################################################
def extract_page_data_ebay(data):
    ebay_extract_start = time.time()
    soup=BeautifulSoup(data, features = "lxml")
    listings = soup.find_all('li', attrs={'class': 's-item'})
    item_data = []
    for listing in listings:
        # Below if statement prevents shop on ebay items to come up
        if listing.find('div', attrs={'class':"s-item__title"}).text != 'Shop on eBay':
            # Fetches name and price of product
            prod_name = listing.find('div', attrs={'class':"s-item__title"}).text
            prod_price = listing.find('span', attrs={'class':"s-item__price"}).text

            # Fetches bidding time left if product is for bidding
            purchase_option_elem = listing.find('span', attrs={'class': 's-item__bids s-item__bidCount'})
            if purchase_option_elem:
                purchase_option = purchase_option_elem.text
                time_left_bids = listing.find('span', attrs={'class':'s-item__time-left'}).text
            else:
                purchase_option = 'Buy It Now'
                time_left_bids = ""

            # Fetches location data and accounts for 'From country' case
            location_elem = listing.find('span', attrs={"class": "s-item__location s-item__itemLocation"})
            if location_elem:
                location_text = location_elem.text
                if location_text[:4] == 'from':
                    locations = location_text[5:]
                else:
                    locations = location_text
            else:
                # Set default location (defaults to UK) when element is missing
                locations = 'United Kingdom'
            # Fetches image
            image_links = listing.find('img').get('src')
            # Fetches URL of product
            url_elem = listing.find('a').get('href')
            if url_elem:
                url = url_elem
            else:
                url = ""
            # Appends data into standardised dataframe
            item_data.append({'name': prod_name, 'price': prod_price, 'purchase_option': purchase_option, 
                                "time_left_bids":time_left_bids, "locations": locations,"image_links": image_links, 
                                "url": url})
    ebay_extract_end = time.time()
    print(f"Ebay data extraction took {ebay_extract_end - ebay_extract_start} seconds")
    return pd.DataFrame(item_data)

##############################################################################
# Searches different part of eBay depending on category selected
# 'search_input' is what is searched by user
# 'num_pages' is how many pages are being scraped
# 'category' is what category has been chosen by user, eg mens/womens
##############################################################################
def ebay_df_maker(search_input, num_pages, category):
    # Set a default value for num_pages if it is None or an empty string
    ebay_df_maker_start = time.time()
    if num_pages is None or num_pages == '':
        num_pages = 1
    url_search_input = search_input.replace(" ", "+")

    if category == 'all':
        ebay_base_url = "https://www.ebay.co.uk/sch/i.html?_from=R40&_nkw={}&_pgn={}"
    elif category == 'mens':
        ebay_base_url = "https://www.ebay.co.uk/sch/260012/i.html?_from=R40&_nkw={}&_pgn={}"
    elif category == 'mens_clothes':
        ebay_base_url = "https://www.ebay.co.uk/sch/1059/i.html?_from=R40&_nkw={}&_pgn={}"
    elif category == 'mens_shoes':
        ebay_base_url = "https://www.ebay.co.uk/sch/93427/i.html?_from=R40&_nkw={}&_pgn={}"

    elif category == 'womens_clothes':
        ebay_base_url = "https://www.ebay.co.uk/sch/15724/i.html?_from=R40&_nkw={}&_pgn={}"
    elif category == 'womens_shoes':
        ebay_base_url = "https://www.ebay.co.uk/sch/3034/i.html?_from=R40&_nkw={}&_pgn={}"
    elif category == 'womens':
        ebay_base_url = "https://www.ebay.co.uk/sch/260010/i.html?_from=R40&_nkw={}&_pgn={}"
    # TODO find where bag filter is on ebay
    elif category == 'bags':
        ebay_base_url = "https://www.ebay.co.uk/sch/i.html?_from=R40&_nkw={}&_pgn={}"
    elif category == 'watches':
        ebay_base_url = "https://www.ebay.co.uk/sch/260324/i.html?_from=R40&_nkw={}&_pgn={}"
    elif category == 'jewellery':
        ebay_base_url = "https://www.ebay.co.uk/sch/281/i.html?_from=R40&_nkw={}&_pgn={}"


    # Generates URLs to scrape for the number of pages specified
    urls = [ebay_base_url.format(url_search_input, page_num) for page_num in range(1, int(num_pages) + 1)]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        page_data_list = list(executor.map(fetch_page_data, urls))
    with concurrent.futures.ThreadPoolExecutor() as executor:
        data_frames = list(executor.map(extract_page_data_ebay, page_data_list))
    df = pd.concat(data_frames)
    # Sets columns to eBay
    df['source'] = 'eBay'
    df['logo_url'] = '/static/ebay_logo.png'
    df['size'] = ''
    ebay_df_maker_end = time.time()
    print(f"Ebay df creation took {ebay_df_maker_end - ebay_df_maker_start} seconds")
    return df, ebay_df_maker_end - ebay_df_maker_start


##############################################################################
# Scraping for grailed, depop and vinted where we are combining into one 
# function so just one chrome browser opens (faster)
# 'grailed_flag' depends on if user selects grailed to be searched
# 'depop_flag' depends on if user selects depop to be searched
# 'vinted_flag' depends on if user selects vinted to be searched
##############################################################################
def grailed_depop_vinted_ves_df_maker(search_input, category, grailed_flag, depop_flag, vinted_flag,vestiaire_flag):

    ################################################
    #  SET UP FOR SCRAPING
    ################################################
    scrape_set_up_start = time.time()
    scrape_set_up_start2 = time.time()
    # Below needed so IP doesn't get blocked
    ua = UserAgent()
    userAgent = ua.random
    service = Service()
    scrape_set_up_end2 = time.time()
    print(f"Scraping set up IP took {scrape_set_up_end2 - scrape_set_up_start2} seconds")

    # Set up the Selenium driver with appropriate settings
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("disable-infobars"); # disabling infobars
    chrome_options.add_argument("--disable-extensions"); # disabling extensions
    chrome_options.add_argument("--headless")
    chrome_options.add_argument(f'user-agent={userAgent}')
    driver = webdriver.Chrome(service = service, options=chrome_options)
    scrape_set_up_end = time.time()
    print(f"Scraping set up took {scrape_set_up_end - scrape_set_up_start} seconds")

    ################################################################################################
    #  DEPOP SOURCE SCRAPING - NOTE: div classes are not constant so need to be updated regularly
    #  DEPOP SCRAPING SLOW BC SCROLLING REQUIRED
    ################################################################################################

    if depop_flag:
        depop_scrape_start = time.time()
        # Navigate to the URL using f-string to insert the value of url_search_input
        depop_url_search_input = search_input.replace(" ", "+")
        # Different categories used at end of URL depending on which cateogry chosen
        if category == 'all':
            depop_base_url = f"https://www.depop.com/search/?q={depop_url_search_input}"
        elif category == 'mens':
            depop_base_url = f"https://www.depop.com/search/?q={depop_url_search_input}&categories=1"
        elif category == 'mens_clothes':
            depop_base_url = f"https://www.depop.com/search/?q={depop_url_search_input}&categories=1&subcategories=2%2C3%2C4%2C5"
        elif category == 'mens_shoes':
            depop_base_url = f"https://www.depop.com/search/?q={depop_url_search_input}&categories=6"

        elif category == 'womens_clothes':
            depop_base_url = f"https://www.depop.com/search/?q={depop_url_search_input}&categories=8&subcategories=11%2C12%2C13%2C9%2C10%2C211"
        elif category == 'womens_shoes':
            depop_base_url = f"https://www.depop.com/search/?q={depop_url_search_input}&categories=14"
        elif category == 'womens':
            depop_base_url = f"https://www.depop.com/search/?q={depop_url_search_input}&categories=8"
        elif category == 'jewellery':
            depop_base_url = f"https://www.depop.com/search/?q={depop_url_search_input}&categories=17"
        # TODO figure out if i want to filter on mens bags/womens bags since no bags filter
        elif category == 'bags':
            depop_base_url = f"https://www.depop.com/search/?q={depop_url_search_input}"
        # TODO figure out if i want to filter on mens watches/womens watches since no watches filter
            depop_base_url = f"https://www.depop.com/search/?q={depop_url_search_input}"
        
        depop_scrape_start1 = time.time()
        # Scrapes data from appropriate URL
        driver.get(depop_base_url)
        depop_scrape_end1 = time.time()
        print(f"Depop driver get took {depop_scrape_end1 - depop_scrape_start1} seconds")

        depop_scrape_start2 = time.time()
        # Removes cookies button so scrolling can take place
        depop_cookies_accept_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'sc-hjcAab bpwLYJ sc-gshygS fFJfAu')]"))
        )
        depop_cookies_accept_button.click()

        # Select country dropdown as gb
        select_location = Select(WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.NAME, "select__location"))
        ))
        select_location.select_by_value('gb')
        depop_scrape_end2 = time.time()
        print(f"Depop country + cookies click took {depop_scrape_end2 - depop_scrape_start2} seconds")

        depop_scrape_start3 = time.time()
        # Get the initial body scroll height
        body_height = driver.execute_script("return document.body.scrollHeight")

        # Scrolls down by partial body scroll height due to not scraping all products with full body height 
        scroll_height = body_height // 2

        # Scroll down the page multiple times to trigger lazy loading
        # Adjust the number of times to scroll based on the page length - more scrolls needed for smaller scroll height
        for _ in range(8):  
            driver.execute_script(f"window.scrollBy(0, {scroll_height});")
            # Wait for the page to load completely
            WebDriverWait(driver, 10).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
        depop_scrape_end3 = time.time()
        print(f"Depop scrolling took {depop_scrape_end3 - depop_scrape_start3} seconds")
        # Assigns depop source data to depop_page_source
        depop_page_source = driver.page_source
        depop_scrape_end = time.time()
        print(f"Depop scraping took {depop_scrape_end - depop_scrape_start} seconds")

    ################################################################################################
    #  VESTIAIRE SOURCE SCRAPING
    #  VESTIAIRE SCRAPING REQUIRES SCROLLING
    #  TODO: VESTIAIRE NOT WORKING
    ################################################################################################
    
    if vestiaire_flag:
        vestiaire_scrape_start = time.time()
        if category == 'all':
            vestiaire_base_url = f"https://www.vestiairecollective.com/search/?q={search_input}"
        vestiaire_scrape_start2 = time.time()
        driver.get(vestiaire_base_url)
        vestiaire_scrape_end2 = time.time()
        print(f"Vestiaire driver get took {vestiaire_scrape_end2 - vestiaire_scrape_start2} seconds")

        vestiaire_scrape_start3 = time.time()
        # Removes cookies button so scrolling can take place
        vestiaire_cookies_accept_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@id,'popin_tc_privacy_button_2')]"))
        )
        vestiaire_cookies_accept_button.click()
        vestiaire_scrape_end3 = time.time()
        print(f"Vestiaire cookies click took {vestiaire_scrape_end3 - vestiaire_scrape_start3} seconds")

        vestiaire_scrape_start4 = time.time()
        # Get the initial body scroll height
        body_height = driver.execute_script("return document.body.scrollHeight")

        # Scrolls down by partial body scroll height due to not scraping all products with full body height 
        scroll_height = body_height

        # Scroll down the page multiple times to trigger lazy loading
        # Adjust the number of times to scroll based on the page length - more scrolls needed for smaller scroll height
        for _ in range(2):  
            driver.execute_script(f"window.scrollBy(0, {scroll_height});")
            # Wait for the page to load completely
            WebDriverWait(driver, 10).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
        vestiaire_scrape_end4 = time.time()
        print(f"Vestiaire scrolling took {vestiaire_scrape_end4 - vestiaire_scrape_start4} seconds")
        vestiaire_page_source = driver.page_source
        vestiaire_scrape_end = time.time()
        print(f"Vestiaire scraping took {vestiaire_scrape_end - vestiaire_scrape_start} seconds")
    ################################################
    #  VINTED SOURCE SCRAPING
    #  VINTED SCRAPING DOESN'T REQUIRE SCROLLING
    ################################################

    if vinted_flag:
        vinted_scrape_start = time.time()
        vinted_url_search_input = search_input.replace(" ", "%20")
        # Navigate to the URL using f-string to insert the value of url_search_input
        # Catalog at end changes depending on category chosen
        if category == 'all':
            vinted_base_url = f"https://www.vinted.co.uk/catalog?search_text={vinted_url_search_input}"
        elif category == 'mens':
            vinted_base_url = f"https://www.vinted.co.uk/catalog?search_text={vinted_url_search_input}&catalog[]=5"
        elif category == 'mens_clothes':
            vinted_base_url = f"https://www.vinted.co.uk/catalog?search_text={vinted_url_search_input}&catalog[]=2050"
        elif category == 'mens_shoes':
            vinted_base_url = f"https://www.vinted.co.uk/catalog?search_text={vinted_url_search_input}&catalog[]=1231"
        elif category == 'womens_clothes':
            vinted_base_url = f"https://www.vinted.co.uk/catalog?search_text={vinted_url_search_input}&catalog[]=4"
        elif category == 'womens_shoes':
            vinted_base_url = f"https://www.vinted.co.uk/catalog?search_text={vinted_url_search_input}&catalog[]=16"
        elif category == 'womens':
            vinted_base_url = f"https://www.vinted.co.uk/catalog?search_text={vinted_url_search_input}&catalog[]=1904"
        # TODO figure out if i want to filter on mens bags/womens bags since no bags filter
        elif category == 'bags':
            vinted_base_url = f"https://www.vinted.co.uk/catalog?search_text={vinted_url_search_input}"
        # TODO figure out if i want to filter on mens watches/womens watches since no watches filter
        elif category == 'watches':
            vinted_base_url = f"https://www.vinted.co.uk/catalog?search_text={vinted_url_search_input}"
        # TODO figure out if i want to filter on mens watches/womens watches since no jewellery filter
        elif category == 'jewellery':
            vinted_base_url = f"https://www.vinted.co.uk/catalog?search_text={vinted_url_search_input}"

        vinted_scrape_start2 = time.time()
        driver.get(vinted_base_url)
        vinted_scrape_end2 = time.time()
        print(f"Vinted driver get took {vinted_scrape_end2 - vinted_scrape_start2} seconds")

        # Removes cookies button
        vinted_scrape_start3 = time.time()
        WebDriverWait(driver, 20).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
        vinted_cookies_accept_button = WebDriverWait(driver,20).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        # vinted_cookies_accept_button.click()
        vinted_scrape_end3 = time.time()
        print(f"Vinted wait load time took {vinted_scrape_end3 - vinted_scrape_start3} seconds")

        # Assigns vinted source data to vinted_page_source
        vinted_page_source = driver.page_source
        vinted_scrape_end = time.time()
        print(f"Vinted scraping took {vinted_scrape_end - vinted_scrape_start} seconds")

    ################################################################################################
    #  GRAILED SOURCE SCRAPING
    #  GRAILED SCRAPING DOESN'T REQUIRE SCROLLING - GETS 40 ENTRIES INSTANTLY
    #  TODO: GRAILED NOT WORKING
    ################################################################################################

    if grailed_flag:

        # Navigate to grailed url
        # TODO: Categories
        grailed_url = f"https://www.grailed.com/shop/"

        driver.get(grailed_url)
        
        # Below searches for given URL by typing in and clicking enter using webdriver, required becuase nothing in URL shows search
        grailed_search_bar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[contains(@class,'Form-module__input___mDyy5')]"))
        )
        search_query = f"{search_input}"
        # Types in search into grailed search bar
        grailed_search_bar.send_keys(search_query)
        # TODO: This step not working
        grailed_search_bar.send_keys(Keys.RETURN)  # Press Enter to perform the search
        popup_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(@class,'Button-module__button___fE9iu Button-module__large___wYagY Button-module__secondary___gYP5i AuthModal-Button _facebook _signup')]"))
        )
        # Simulate pressing the "Escape" key to dismiss the pop-up after triggering pop up by doing following
        popup_element.send_keys(Keys.ESCAPE)
        # Search for correct element
        grailed_search_bar.send_keys(search_query)
        grailed_search_bar.send_keys(Keys.RETURN)  # Press Enter to perform the search

        # Assigns grailed source data to grailed_page_source
        grailed_page_source = driver.page_source
        
        # Close the driver since searches on browser has completed
        driver.quit()

    ################################################
    #  DEPOP DATAFRAME CREATION
    #  NOTE: div classes are not constant so need to be updated regularly
    ################################################

    if depop_flag:
        depop_df_start = time.time()
        # Parse the page source using BeautifulSoup
        depop_soup = BeautifulSoup(depop_page_source, 'lxml')

        # listings is list of products found
        listings = depop_soup.find_all('li', attrs={"class": "styles__ProductCardContainer-sc-9691b5f-7 NKdpy"})
        # item_data is list for list of dictionaries
        item_data = []

        # Ensures website doesn't break if div class tags are out of date
        if not listings:
            depop_df = pd.DataFrame()

        # Iterates through each product to extract relevant data
        # depop_update
        for listing in listings:
            image_links_elem = listing.find('img', attrs={'class': 'sc-htehQK fmdgqI'})
            if image_links_elem:
                image_links = image_links_elem.get('src')
                url_elem = listing.find('a',attrs={'class':'styles__ProductCard-sc-9691b5f-4 eLNNjp'})
                if url_elem:
                    url = url_elem.get('href')
                else:
                    url = ""
                size_elem = listing.find('p',attrs={'class':'sc-eDnWTT styles__StyledSizeText-sc-9691b5f-12 kcKICQ glohkc'})
                if size_elem:
                    size = size_elem.text
                else:
                    size = ""
                # prod_price_elem is price which ISN'T CROSSED OUT
                prod_price_elem = listing.find('p',attrs={'class':'sc-eDnWTT Price-styles__FullPrice-sc-88086281-0 fRxqiS jHCqsV'})
                prod_price_discount_elem = listing.find('p',attrs={'class':'sc-eDnWTT Price-styles__DiscountPrice-sc-88086281-1 fRxqiS buybSP'})
                if prod_price_elem:
                    prod_price = prod_price_elem.text
                elif prod_price_discount_elem: 
                    prod_price = prod_price_discount_elem.text
                else:
                    prod_price=""
                item_data.append({'url': url, 'image_links': image_links, 'price': prod_price, 'size': size})

        # depop_df contains standardised depop data from source
        depop_df = pd.DataFrame(item_data)

        # Sets columns to depop values
        if not depop_df.empty:
            depop_df = depop_df.dropna(subset=['image_links'])
            # Have to use description (from url) for product name since this is only available in inspect code
            depop_df['name'] = depop_df['url'].apply(process_string)
            depop_df['url'] = 'https://www.depop.com' + depop_df['url']
            depop_df['source'] = 'Depop'
            depop_df['purchase_option'] = 'Buy It Now'
            depop_df['logo_url'] = '/static/depop_logo.png'
            depop_df['locations'] = 'United Kingdom'

    else:
        depop_df = pd.DataFrame()
    depop_df_end = time.time()
    print(f"Depop dataframe creation took {depop_df_end - depop_df_start} seconds")
    print(f"Depop: {len(depop_df)} listings")

    ################################################
    #  VINTED DATAFRAME CREATION
    ################################################
    vinted_df_start = time.time()

    if vinted_flag:    
        # Parse the page source using BeautifulSoup
        vinted_soup = BeautifulSoup(vinted_page_source, 'lxml')

        # listings is list of products found
        listings = vinted_soup.find_all('div', attrs={"class": "new-item-box__container"})

        # item_data is list for list of dictionaries
        item_data = []

        # Ensures website doesn't break if there is bug where no products fetched
        if not listings:
            vinted_df = pd.DataFrame()

        # Used to extract name and sizes from product description
        name_substring = ", price:"
        size_substring = "size: "
        price_substring = " incl."

        # Iterates through each product to extract relevant data
        for listing in listings:
            url_elem = listing.find('a',attrs={'class':'new-item-box__overlay'}).get('href')
            if url_elem:
                url = url_elem
            else:
                url = ""
            prod_desc_elem = listing.find('a',attrs={'class':'new-item-box__overlay'})
            # Scrapes product name and size from description
            if prod_desc_elem:
                prod_desc_elem_text = prod_desc_elem.get('title')
                prod_name = prod_desc_elem_text.split(name_substring)[0]
                size = prod_desc_elem_text.split(size_substring)[1]
            else:
                prod_name = ""
                size = ""
            prod_price_elem = listing.find('span',attrs={'class':'web_ui__Text__text web_ui__Text__caption web_ui__Text__left web_ui__Text__clickable web_ui__Text__underline-none'})
            # Scrapes product price accounting for case where 'incl.' is shown
            if prod_price_elem:
                prod_price_text = prod_price_elem.text
                prod_price = prod_price_text.split(price_substring)[0]
            else:
                prod_price = ""
            image_links = listing.find('img',attrs={'alt':prod_name}).get('src')
        
            item_data.append({'url': url, 'image_links': image_links, 'price': prod_price, 'size': size, 'name': prod_name})

        # vinted_df contains standardised vinted data from source
        vinted_df = pd.DataFrame(item_data)

        # Sets columns to vinted values
        if not vinted_df.empty:
            vinted_df = vinted_df.dropna(subset=['image_links'])
            vinted_df['source'] = 'Vinted'
            vinted_df['purchase_option'] = 'Buy It Now'
            vinted_df['logo_url'] = '/static/vinted_logo.jpeg'
            vinted_df['locations'] = 'United Kingdom'

    else:
        vinted_df = pd.DataFrame()
    vinted_df_end = time.time()
    print(f"Vinted dataframe creation took {vinted_df_end - vinted_df_start} seconds")
    print(f"Vinted: {len(vinted_df)} listings")

    ################################################
    #  GRAILED DATAFRAME CREATION
    ################################################
    
    if grailed_flag:

        # Parse the page source using BeautifulSoup
        grailed_soup = BeautifulSoup(grailed_page_source, 'lxml')

        # listings is list of products found
        listings = grailed_soup.find_all('div', attrs={"class": "feed-item"})

        item_data = []

        # Ensures website doesn't break if there is bug where no products fetched
        if not listings:
            grailed_df = pd.DataFrame()

        # Used to extract name and sizes from product description

        for listing in listings:
            image_links_elem = listing.find('img')
            if image_links_elem:
                image_links = image_links_elem.get('srcset')
                url_elem = listing.find('a',attrs={'class':'listing-item-link'})
                if url_elem:
                    url = url_elem.get('href')
                else:
                    url = ''
                prod_name_element = listing.find('p',attrs={'class':'ListingMetadata-module__title___Rsj55'})
                if prod_name_element:
                    prod_name = prod_name_element.text
                else:
                    prod_name = ""
                size_elem = listing.find('p',attrs={'class':'ListingMetadata-module__size___e9naE'})
                if size_elem:
                    size = size_elem.text
                else:
                    size = ""
                prod_price_elem_reduced = listing.find('span',attrs={'class':'Money-module__root___jRyq5 Price-module__onSale___1pIHp'})
                prod_price_elem = listing.find('span',attrs={'class':'Money-module__root___jRyq5'})
                if prod_price_elem_reduced:
                    prod_price = prod_price_elem.text
                elif prod_price_elem:
                    prod_price = prod_price_elem.text
                else:
                    prod_price = ""
                image_links = listing.find('img').get('src')
            
                item_data.append({'url': url, 'price': prod_price, 'size': size, 'name': prod_name, 'image': image_links})

        # grailed_df contains standardised grailed data from source
        grailed_df = pd.DataFrame(item_data)

        if not grailed_df.empty:
            grailed_df['source'] = 'Grailed'
            grailed_df['purchase_option'] = 'Buy It Now'
            grailed_df['logo_url'] = '/static/vinted_logo.png'
            # TODO: Get location where grailed products being sold from
            grailed_df['locations'] = 'TBD'
            grailed_df['url'] = 'https://www.grailed.com' + grailed_df['url']

    else:
        grailed_df = pd.DataFrame()

    ################################################
    #  VESTIAIRE DATAFRAME CREATION
    ################################################
    vestiaire_df_start = time.time()
    if vestiaire_flag:
        vestiaire_soup = BeautifulSoup(vestiaire_page_source, 'lxml')
        listings = vestiaire_soup.find("ul",attrs={'class': 'product-search_catalog__flexContainer__Dg0eL'})
        item_data = []
        for listing in listings.find_all("li"):
            # Fetches name and price of product
            prod_name_elem = listing.find('span', attrs={'class':"product-card_productCard__text__jqjuJ product-card_productCard__text--brand__QybC2"})
            if prod_name_elem:
                prod_name = prod_name_elem.text
                prod_price_elem = listing.find('span', attrs={'class':"product-card_productCard__text__jqjuJ product-card_productCard__text--price__RmfRd"})
                prod_price_discount_elem = listing.find('span', attrs={'class':"product-card_productCard__text__jqjuJ product-card_productCard__text--price__RmfRd product-card_productCard__text--price--discount__Oo_Pa"})
                if prod_price_discount_elem:
                    prod_price2 = prod_price_discount_elem.text
                    prod_price = '£' + prod_price2.split('£')[2]
                else:
                    if prod_price_elem:
                        prod_price = prod_price_elem.text
                    else:
                        prod_price = ""
                # Fetches location data and accounts for 'From country' case
                location_elem = listing.find('span', attrs={"class": "product-card-location-icon_locationIcon__yBhE_"})
                if location_elem:
                    locations = location_elem.text
                else:
                    # Set default location (defaults to UK) when element is missing
                    locations = 'United Kingdom'
                # Fetches image
                image_links_elem = listing.find('img',attrs={"class": "vc-images_image__TfKYE"})
                if image_links_elem:
                    image_links = image_links_elem.get('src')
                # Fetches URL of product
                url_elem = listing.find('a', attrs={"class": "product-card_productCard__image__40WNk"})
                if url_elem:
                    url_elem2 = url_elem.get('href')
                    url = f"https://www.vestiairecollective.com{url_elem2}"
                else:
                    url = ""
                size_elem = listing.find('p',attrs={'class':'product-card_productCard__text--size__qI2Mi'})
                if size_elem:
                    size = size_elem.text
                else:
                    size = ""
                # Appends data into standardised dataframe
                item_data.append({'name': prod_name, 'price': prod_price, 
                                    "locations": locations, "image_links": image_links, 
                                    "url": url, "size": size})
        # vestiaire_df contains standardised grailed data from source
        vestiaire_df = pd.DataFrame(item_data)

        # Sets columns to vestiaire values
        if not vestiaire_df.empty:
                vestiaire_df = vestiaire_df.dropna(subset=['image_links'])
                vestiaire_df['source'] = 'Vestiaire'
                vestiaire_df['purchase_option'] = 'Buy It Now'
                vestiaire_df['logo_url'] = '/static/vestiaire_logo.jpeg'
    else:
        vestiaire_df = pd.DataFrame()
        print(f"Vestiaire: {len(vestiaire_df)} listings")
    vestiaire_df_end = time.time()

    print(f"Vestiaire dataframe creation took {vestiaire_df_end - vestiaire_df_start} seconds")

    return len(vestiaire_df), vestiaire_df_end - vestiaire_df_start, vestiaire_scrape_end - vestiaire_scrape_start, len(vinted_df), vinted_df_end - vinted_df_start, vinted_scrape_end - vinted_scrape_start, len(depop_df), depop_df_end - depop_df_start,depop_scrape_end - depop_scrape_start

grailed_depop_vinted_ves_df_maker_output = grailed_depop_vinted_ves_df_maker("stussy", "all", False, True, True,True)

len_ebay_df = len(ebay_df_maker("stussy","","all")[0])
len_vestiaire_df = grailed_depop_vinted_ves_df_maker_output[0]
vestiaire_df_time = round(grailed_depop_vinted_ves_df_maker_output[1],2)
vestiaire_scrape_time = round(grailed_depop_vinted_ves_df_maker_output[2],2)
len_vinted_df = grailed_depop_vinted_ves_df_maker_output[3]
vinted_df_time = round(grailed_depop_vinted_ves_df_maker_output[4],2)
vinted_scrape_time = round(grailed_depop_vinted_ves_df_maker_output[5],2)
len_depop_df = grailed_depop_vinted_ves_df_maker_output[6]
depop_df_time = round(grailed_depop_vinted_ves_df_maker_output[7],2)
depop_scrape_time = round(grailed_depop_vinted_ves_df_maker_output[8],2)

################################################
#  EMAIL SET UP FOR CASES WHEN DATAFRAMES ARE EMPTY TO LET ME KNOW TO UPDATE TAGS
################################################

smtp_server = "smtp.gmail.com"
port = 587  # For starttls
sender_email = "william.steynor@gmail.com"
receiver_email = "william.steynor@gmail.com"
password = "zhwj mqvl kbvc ntir"
nl = '\n'
message_body = f"eBay: {len_ebay_df} listings{nl}{nl}Vestiaire: {len_vestiaire_df} listings, {nl}Scraping took {vestiaire_scrape_time} seconds, df creation took {vestiaire_df_time} seconds{nl}{nl}Depop: {len_depop_df} listings, {nl}Scraping took {depop_scrape_time} seconds, df creation took {depop_df_time} seconds{nl}{nl}Vinted: {len_vinted_df} listings, {nl}Scraping took {vinted_scrape_time} seconds, df creation took {vinted_df_time} seconds{nl}{nl}Total number of listings: {len_ebay_df+len_depop_df+len_vinted_df+len_vestiaire_df}{nl}Total time taken for scraping and df creation: {round(vinted_df_time+vinted_scrape_time+depop_df_time+depop_scrape_time+vestiaire_df_time+vestiaire_scrape_time,2)}"
subject = "Threadsense Daily Check"
message = 'Subject: {}\n\n{}'.format(subject, message_body)

def send_email(subject, message_body, sender_email, receiver_email, password):
    msg = MIMEText(message_body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
       smtp_server.login(sender_email, password)
       smtp_server.sendmail(sender_email, receiver_email, msg.as_string())
    print("Message sent!")

send_email(subject, message_body, sender_email, receiver_email, password)