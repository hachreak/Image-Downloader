""" Crawl image urls from image search engine. """
# -*- coding: utf-8 -*-
# author: Yabin Zheng
# Email: sczhengyabin@hotmail.com

from __future__ import print_function

import re
import time
import sys
import os
import json
import codecs
import shutil

from urllib.parse import unquote, quote
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
import requests
from concurrent import futures

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
else:
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

dcap = dict(DesiredCapabilities.PHANTOMJS)
dcap["phantomjs.page.settings.userAgent"] = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.100"
)


def my_print(msg, quiet=False):
    if not quiet:
        print(msg)


def google_gen_query_url(keywords, face_only=False, safe_mode=False, image_type=None, color=None):
    base_url = "https://www.google.com/search?tbm=isch&hl=en"
    keywords_str = "&q=" + quote(keywords)
    query_url = base_url + keywords_str

    if safe_mode is True:
        query_url += "&safe=on"
    else:
        query_url += "&safe=off"

    filter_url = "&tbs="

    if color is not None:
        if color == "bw":
            filter_url += "ic:gray%2C"
        else:
            filter_url += "ic:specific%2Cisc:{}%2C".format(color.lower())

    if image_type is not None:
        if image_type.lower() == "linedrawing":
            image_type = "lineart"
        filter_url += "itp:{}".format(image_type)

    if face_only is True:
        filter_url += "itp:face"

    query_url += filter_url
    return query_url


def google_image_url_from_webpage(driver, max_number, quiet=False):
    thumb_elements_old = []
    thumb_elements = []
    while True:
        try:
            thumb_elements = driver.find_elements_by_class_name("rg_i")
            my_print("Find {} images.".format(len(thumb_elements)), quiet)
            if len(thumb_elements) >= max_number:
                break
            if len(thumb_elements) == len(thumb_elements_old):
                break
            thumb_elements_old = thumb_elements
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            show_more = driver.find_elements_by_class_name("mye4qd")
            if len(show_more) == 1 and show_more[0].is_displayed() and show_more[0].is_enabled():
                my_print("Click show_more button.", quiet)
                #  show_more[0].click()
                driver.execute_script("arguments[0].click();", show_more[0])
            time.sleep(3)
        except Exception as e:
            print("Exception ", e)
            pass

    if len(thumb_elements) == 0:
        return []

    my_print("Click on each thumbnail image to get image url, may take a moment ...", quiet)

    retry_click = []
    for i, elem in enumerate(thumb_elements):
        try:
            if i != 0 and i % 50 == 0:
                my_print("{} thumbnail clicked.".format(i), quiet)
            if not elem.is_displayed() or not elem.is_enabled():
                retry_click.append(elem)
                continue
            #  elem.click()
            driver.execute_script("arguments[0].click();", elem)
        except Exception as e:
            print("Error while clicking in thumbnail:", e)
            retry_click.append(elem)

    if len(retry_click) > 0:
        my_print("Retry some failed clicks ...", quiet)
        for elem in retry_click:
            try:
                if elem.is_displayed() and elem.is_enabled():
                    #  elem.click()
                    driver.execute_script("arguments[0].click();", elem)
            except Exception as e:
                print("Error while retrying click:", e)

    image_elements = driver.find_elements_by_class_name("islib")
    image_urls = list()
    url_pattern = r"imgurl=\S*&amp;imgrefurl"
    webpage_urls = []

    for idx in range(len(image_elements[:max_number])):
        # reload to be sure
        image_elements = driver.find_elements_by_class_name("islib")
        try:
            image_element = image_elements[idx]
        except:
            import ipdb; ipdb.set_trace()
            print('ok')
        outer_html = image_element.get_attribute("outerHTML")
        re_group = re.search(url_pattern, outer_html)
        if re_group is not None:
            image_url = unquote(re_group.group()[7:-14])
            image_urls.append(image_url)
            webpage_urls.append(google_get_webpage_url(driver, image_element))
    return image_urls, webpage_urls


def google_get_webpage_url(driver, image_element):
    webpage_pattern = r"href=\"http\S*\""
    #image_element.click()
    driver.execute_script("arguments[0].click();", image_element)
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    try:
        elem = driver.find_elements_by_id("islsp")[0]
        inner_html = elem.get_attribute("innerHTML")
        re_group = re.findall(webpage_pattern, inner_html)
        groups = [g for g in re_group if "google" not in g]
        return groups[0][6:-1]
    except IndexError:
        return ""


def bing_gen_query_url(keywords, face_only=False, safe_mode=False, image_type=None, color=None):
    base_url = "https://www.bing.com/images/search?"
    keywords_str = "&q=" + quote(keywords)
    query_url = base_url + keywords_str
    filter_url = "&qft="
    if face_only is True:
        filter_url += "+filterui:face-face"

    if image_type is not None:
        filter_url += "+filterui:photo-{}".format(image_type)

    if color is not None:
        if color == "bw" or color == "color":
            filter_url += "+filterui:color2-{}".format(color.lower())
        else:
            filter_url += "+filterui:color2-FGcls_{}".format(color.upper())

    query_url += filter_url

    return query_url


def bing_image_url_from_webpage(driver):
    image_urls = list()

    time.sleep(10)
    img_count = 0

    while True:
        image_elements = driver.find_elements_by_class_name("iusc")
        if len(image_elements) > img_count:
            img_count = len(image_elements)
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
        else:
            smb = driver.find_elements_by_class_name("btn_seemore")
            if len(smb) > 0 and smb[0].is_displayed():
                #  smb[0].click()
                driver.execute_script("arguments[0].click();", smb[0])
            else:
                break
        time.sleep(3)
    for image_element in image_elements:
        m_json_str = image_element.get_attribute("m")
        m_json = json.loads(m_json_str)
        image_urls.append(m_json["murl"])
    return image_urls


baidu_color_code = {
    "white": 1024, "bw": 2048, "black": 512, "pink": 64, "blue": 16, "red": 1,
    "yellow": 2, "purple": 32, "green": 4, "teal": 8, "orange": 256, "brown": 128
}

def baidu_gen_query_url(keywords, face_only=False, safe_mode=False, color=None):
    base_url = "https://image.baidu.com/search/index?tn=baiduimage"
    keywords_str = "&word=" + quote(keywords)
    query_url = base_url + keywords_str
    if face_only is True:
        query_url += "&face=1"
    if color is not None:
        print(color, baidu_color_code[color.lower()])
    if color is not None:
        query_url += "&ic={}".format(baidu_color_code[color.lower()])
    print(query_url)
    return query_url


def baidu_image_url_from_webpage(driver):
    time.sleep(10)
    image_elements = driver.find_elements_by_class_name("imgitem")
    image_urls = list()

    for image_element in image_elements:
        image_url = image_element.get_attribute("data-objurl")
        image_urls.append(image_url)
    return image_urls


def baidu_get_image_url_using_api(keywords, max_number=10000, face_only=False,
                                  proxy=None, proxy_type=None):
    def decode_url(url):
        in_table = '0123456789abcdefghijklmnopqrstuvw'
        out_table = '7dgjmoru140852vsnkheb963wtqplifca'
        translate_table = str.maketrans(in_table, out_table)
        mapping = {'_z2C$q': ':', '_z&e3B': '.', 'AzdH3F': '/'}
        for k, v in mapping.items():
            url = url.replace(k, v)
        return url.translate(translate_table)

    base_url = "https://image.baidu.com/search/acjson?tn=resultjson_com&ipn=rj&ct=201326592"\
               "&lm=7&fp=result&ie=utf-8&oe=utf-8&st=-1"
    keywords_str = "&word={}&queryWord={}".format(
        quote(keywords), quote(keywords))
    query_url = base_url + keywords_str
    query_url += "&face={}".format(1 if face_only else 0)

    init_url = query_url + "&pn=0&rn=30"

    proxies = None
    if proxy and proxy_type:
        proxies = {"http": "{}://{}".format(proxy_type, proxy),
                   "https": "{}://{}".format(proxy_type, proxy)}

    # headers = {
    #     #'Accept-Encoding': 'gzip, deflate, sdch',
    #     #'Accept-Language': 'en-US,en;q=0.8',
    #     #'Upgrade-Insecure-Requests': '1',
    #     'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
    #     #'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,/;q=0.8',
    #     #'Cache-Control': 'max-age=0',
    #     #'Connection': 'keep-alive',
    # }
    headers = {
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    res = requests.get(init_url, proxies=proxies, headers=headers)
    init_json = json.loads(res.text.replace(r"\'", "").encode("utf-8"), strict=False)
    total_num = init_json['listNum']

    target_num = min(max_number, total_num)
    crawl_num = min(target_num * 2, total_num)

    crawled_urls = list()
    batch_size = 30

    with futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_list = list()

        def process_batch(batch_no, batch_size):
            image_urls = list()
            url = query_url + \
                "&pn={}&rn={}".format(batch_no * batch_size, batch_size)
            try_time = 0
            while True:
                try:
                    response = requests.get(url, proxies=proxies, headers=headers)
                    break
                except Exception as e:
                    try_time += 1
                    if try_time > 3:
                        print(e)
                        return image_urls
            response.encoding = 'utf-8'
            res_json = json.loads(response.text.replace(r"\'", "").encode("utf-8"), strict=False)
            for data in res_json['data']:
                if 'objURL' in data.keys():
                    image_urls.append(decode_url(data['objURL']))
                elif 'replaceUrl' in data.keys() and len(data['replaceUrl']) == 2:
                    image_urls.append(data['replaceUrl'][1]['ObjURL'])

            return image_urls

        for i in range(0, int((crawl_num + batch_size - 1) / batch_size)):
            future_list.append(executor.submit(process_batch, i, batch_size))
        for future in futures.as_completed(future_list):
            if future.exception() is None:
                crawled_urls += future.result()
            else:
                print(future.exception())

    return crawled_urls[:min(len(crawled_urls), target_num)]


def crawl_image_urls(keywords, engine="Google", max_number=10000,
                     face_only=False, safe_mode=False, proxy=None,
                     proxy_type="http", quiet=False, browser="phantomjs", image_type=None, color=None):
    """
    Scrape image urls of keywords from Google Image Search
    :param keywords: keywords you want to search
    :param engine: search engine used to search images
    :param max_number: limit the max number of image urls the function output, equal or less than 0 for unlimited
    :param face_only: image type set to face only, provided by Google
    :param safe_mode: switch for safe mode of Google Search
    :param proxy: proxy address, example: socks5 127.0.0.1:1080
    :param proxy_type: socks5, http
    :param browser: browser to use when crawl image urls from Google & Bing
    :return: list of scraped image urls
    """

    my_print("\nScraping From {0} Image Search ...\n".format(engine), quiet)
    my_print("Keywords:  " + keywords, quiet)
    if max_number <= 0:
        my_print("Number:  No limit", quiet)
        max_number = 10000
    else:
        my_print("Number:  {}".format(max_number), quiet)
    my_print("Face Only:  {}".format(str(face_only)), quiet)
    my_print("Safe Mode:  {}".format(str(safe_mode)), quiet)

    if engine == "Google":
        query_url = google_gen_query_url(keywords, face_only, safe_mode, image_type, color)
    elif engine == "Bing":
        query_url = bing_gen_query_url(keywords, face_only, safe_mode, image_type, color)
    elif engine == "Baidu":
        query_url = baidu_gen_query_url(keywords, face_only, safe_mode, color)
    else:
        return

    my_print("Query URL:  " + query_url, quiet)

    if engine != "Baidu":
        browser = str.lower(browser)
        if "chrome" in browser:
            chrome_path = shutil.which("chromedriver")
            chrome_path = "./bin/chromedriver" if chrome_path is None else chrome_path
            chrome_options = webdriver.ChromeOptions()
            if "headless" in browser:
                chrome_options.add_argument("headless")
            if proxy is not None and proxy_type is not None:
                chrome_options.add_argument("--proxy-server={}://{}".format(proxy_type, proxy))
            driver = webdriver.Chrome(chrome_path, chrome_options=chrome_options)
        else:
            phantomjs_path = shutil.which("phantomjs")
            phantomjs_path = "./bin/phantomjs" if phantomjs_path is None else phantomjs_path
            phantomjs_args = []
            if proxy is not None and proxy_type is not None:
                phantomjs_args += [
                    "--proxy=" + proxy,
                    "--proxy-type=" + proxy_type,
                ]
            driver = webdriver.PhantomJS(executable_path=phantomjs_path,
                                        service_args=phantomjs_args, desired_capabilities=dcap)

    if engine == "Google":
        driver.set_window_size(1920, 1080)
        driver.get(query_url)
        image_urls, webpage_urls = google_image_url_from_webpage(driver, max_number, quiet)
    elif engine == "Bing":
        driver.set_window_size(1920, 1080)
        driver.get(query_url)
        image_urls = bing_image_url_from_webpage(driver)
    else:   # Baidu
        # driver.set_window_size(10000, 7500)
        # driver.get(query_url)
        # image_urls = baidu_image_url_from_webpage(driver)
        image_urls = baidu_get_image_url_using_api(keywords, max_number=max_number, face_only=face_only,
                                                   proxy=proxy, proxy_type=proxy_type)
    if engine != "Baidu":
        driver.close()

    if max_number > len(image_urls):
        output_num = len(image_urls)
    else:
        output_num = max_number

    my_print("\n== {0} out of {1} crawled images urls will be used.\n".format(
        output_num, len(image_urls)), quiet)

    return image_urls[0:output_num], webpage_urls[:output_num]
