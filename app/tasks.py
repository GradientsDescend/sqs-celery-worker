from celery import Celery
from celery import Task
import logging
from requests import Session
import requests
import time
import re
from xml.dom import minidom
import boto3

app = Celery('tasks')
app.config_from_object('celeryconfig')



class ResilientSession(Session):
    """
    This class is supposed to retry requests that return temporary errors.
    At this moment it supports: 502, 503, 504
    """

    def request(self, method, url, **kwargs):
        counter = 0

        while True and counter <= 5:
            counter += 1

            try:
                r = super(ResilientSession, self).request(method, url, **kwargs)

                if r.status_code in [ 502, 503, 504, 429]:
                    delay = 10 * counter
                    logging.error("Got recoverable error [%s] from %s %s, retry #%s in %ss" % (r.status_code, method, url, counter, delay))
                    time.sleep(delay)
                    continue
            except requests.exceptions.ConnectionError as err:
                logging.info("Got connection error on [%s]" % (url))
                if counter <=5:
                    logging.error("Got connection error on [%s], retry #%s in %ss" % (url, counter, delay))
                    delay = 10 * counter
                    time.sleep(delay)
                    continue
                else:
                    logging.error("Got connection error on [%s], retry #%s in %ss" % (url, counter, delay))
                    raise err
            return r

class SessionHandler(Task):
    _session = None
    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582'}
    @property
    def session(self):
        if self._session is None:

            session = ResilientSession()
            session.headers.update(self.headers)

            self._session = session
        return self._session

@app.task(base=SessionHandler, bind=True)
def get_recipe(self, url):
    recipe_url = 'https://www.brewersfriend.com/homebrew/recipe/beerxml1.0/' + url
    api = self.session
    recipe = api.get(recipe_url)
    recipe_cleaned = cleanXML(recipe.text, url)
    if recipe_cleaned != "":
        upload(recipe_cleaned, url)
        logging.info("SUCCESS: %s uploaded to s3" % (url))
        time.sleep(5)

@app.task
def add(x, y):
    logging.info("add success")
    return x + y

def cleanXML(data, url):
    data = re.sub(r'[\x00-\x1f]', '', data)
    r = assertXML(data, url)
    if r == 1 :
        return data
    else:
        return ""

def upload(input, url):
    data_string = str(input)
    session = boto3.Session()
    s3 = session.client("s3")

    s3.put_object(Body=data_string, Bucket='brewxml', Key="data/{}.xml".format(url))

def assertXML(data, url):
    try:
        file = minidom.parseString(data)
        if file.firstChild.tagName != "RECIPES":
            logging.error("XML FAILED on %s" % (url))
            return 0
        else:
            return 1
    except:
        logging.error("XML FAILED on %s" % (url))
        return 0


