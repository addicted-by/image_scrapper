import selenium
import os
from tqdm import tqdm
import warnings
warnings.simplefilter("ignore", DeprecationWarning)
warnings.simplefilter("ignore", UserWarning)

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time
import urllib
import requests
from bs4 import BeautifulSoup


class ImageScrapper():
    def __init__(self, 
                    webdriver_path='./', browser={'edge', 'chrome'},
                    source={'yandex', 'google'},
                    output_path='', headless=False):
        assert browser in {'edge', 'chrome'}, 'browser not comparable'
        options = webdriver.edge.options.Options() if browser == 'edge' \
                                                else webdriver.chrome.options.Options()
        if headless:
            options.add_argument("--headless")
        try:
            if webdriver_path == './':
                self.driver = webdriver.Edge(options=options) if browser == 'edge' \
                                        else webdriver.Chrome(options=options)
            else:
                self.driver = webdriver.Edge(webdriver_path, 
                                    options=options) if browser=='edge' \
                            else webdriver.Chrome(webdriver_path, options=options) 
        except:
            print("webdriver can't be found with that input path")
        self.output_path = output_path
        assert source in {'yandex', 'google'}
        self.source = source


    def scroll_to_bottom(self, limit=None, time_sleep=3):
        last_height = self.driver.execute_script('\
        return document.body.scrollHeight')
        current = 1
        limit_check = lambda x: True if x > limit else False
        while True:
            self.driver.execute_script('\
            window.scrollTo(0,document.body.scrollHeight)')
    
            # waiting for the results to load
            # Increase the sleep time if your internet is slow
            time.sleep(time_sleep)
    
            new_height = self.driver.execute_script('\
            return document.body.scrollHeight')
    
            # click on "Show more results" (if exists)
            try:
                self.driver.find_element_by_css_selector(".YstHxe input").click()
    
                # waiting for the results to load
                # Increase the sleep time if your internet is slow
                time.sleep(time_sleep)
    
            except:
                pass
    
            # checking if we have reached the bottom of the page or set limit
            if new_height == last_height:
                break
            if limit:
                if limit_check(current):
                    break
                current += 1
            last_height = new_height


    def get_tags(self, query: str, limit=None) -> list:
        # Maximize the screen
        self.driver.maximize_window()
        # Open Google Images in the browser
        self.driver.get('https://images.google.com/')
        # Finding the search box
        box = self.driver.find_element_by_xpath('//*[@id="sbtc"]/div/div[2]/input') 
        # Type the search query in the search box
        box.send_keys(query)
        # Pressing enter
        box.send_keys(Keys.ENTER)
        self.scroll_to_bottom(limit=limit)
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        img_tags = soup.find_all("img", class_="rg_i")
        self.driver.close()
        return list(img_tags)
   

    def get_links(self, query: str, limit=6000, time_sleep=3) -> list:
        links = []
        self.driver.maximize_window()
        # Open Google Images in the browser
        self.driver.get('https://yandex.ru/images/?')
        # Finding the search box
        box = self.driver.find_element_by_xpath('//*[@class="serp-header__search2"]/form/div/span/span/input')
        # # # Type the search query in the search box
        box.send_keys(query)
        # # # Pressing enter
        box.send_keys(Keys.ENTER)
        time.sleep(time_sleep)
        # first image
        self.driver.find_element_by_class_name('serp-item__preview').click()
        time.sleep(time_sleep)
        # getting image link
        try:
            link = self.driver.find_element_by_class_name('MMImageWrapper').find_element_by_tag_name('img').get_attribute('src')
            links.append(link)
            with tqdm(range(limit), unit='link') as tepoch:
                tepoch.set_description("Getting links")
                for i in tepoch:
                    # pressing next image
                    self.driver.find_element_by_xpath('//*[@class="MediaViewer-LayoutScene MediaViewer_theme_fiji-LayoutScene"]/div[3]').click()
                    time.sleep(time_sleep//2)
                    try:
                        link = self.driver.find_element_by_class_name('MMImageWrapper').find_element_by_tag_name('img').get_attribute('src')
                    except:
                        print("can't get src attribute")
                    assert link != links[-1], "link haven't changed. not enough time sleep, try to change parameter"
                    links.append(link)
        except Exception as e:
            print("can't reach the photo")
            print(str(e))
        return links
    
    
    def scrape_images(self, query: str, photos_limit=50, scroll_limit=None, time_sleep=3):
        if self.output_path == '':
            if os.path.exists(query) and len(os.listdir(query))== 0:
                os.rmdir(query)
            try:
                # print(1)
                os.mkdir(f'./{query}/')
                self.output_path = query
            except:
                print('path already exists and non-clear. check it please')
        if self.source == 'google':
            img_tags = self.get_tags(query=query, limit=scroll_limit, time_sleep=time_sleep)
            len_dir = len(os.listdir(self.output_path))
            with tqdm(img_tags[:min(len(img_tags), photos_limit)], unit="image") as tepoch:
                tepoch.set_description("Getting images")
                for i, tag in enumerate(tepoch):
                    i += len_dir
                    im_path = f'image{i+1}'+".jpg"
                    try:
                        urllib.request.urlretrieve(tag['src'],
                            os.path.join(self.output_path, im_path))
                        tepoch.set_postfix(image_path=os.path.join(self.output_path, im_path))
                    except:
                        try:
                            urllib.request.urlretrieve(tag['data-src'],
                            os.path.join(self.output_path, im_path))
                            tepoch.set_postfix(image_path=os.path.join(self.output_path, im_path))
                        except:
                            print("can't reach url. check url:\n" + tag)
        elif self.source == 'yandex':
            img_links = self.get_links(query=query, limit=photos_limit, time_sleep=time_sleep)
            with tqdm(img_links[:min(len(img_links), photos_limit)], unit="image") as tepoch:
                for i, link in enumerate(tepoch):
                    im_path = os.path.join(self.output_path, f'image{i+1}'+".jpg")
                    try:
                        img_data = requests.get(link).content
                        with open(im_path, 'wb') as file:
                            file.write(img_data)
                        tepoch.set_postfix(image_path=os.path.join(self.output_path, im_path))
                    except:
                        print("can't reach url. check url:\n" + link)
                self.driver.close()