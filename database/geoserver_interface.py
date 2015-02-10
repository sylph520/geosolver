import json
import logging
import os
import tempfile
import urllib
import urlparse
import requests
from geosolver import settings
from geosolver.database.states import Question

__author__ = 'minjoon'

class GeoserverInterface(object):
    def __init__(self, server_url):
        self.server_url = server_url

    def download_questions(self, key="all"):
        sub_url = "/questions/download/%s" % str(key)
        request_url = urlparse.urljoin(self.server_url, sub_url)
        r = requests.get(request_url)
        data = json.loads(r.text, object_hook=_decode_dict)
        questions = {}
        for pair in data:
            diagram_url = pair['diagram_url']
            temp_dir = tempfile.mkdtemp()
            temp_name = os.path.basename(urlparse.urlparse(diagram_url).path)
            temp_filepath = os.path.join(temp_dir, temp_name)
            urllib.urlretrieve(diagram_url, temp_filepath)
            choices = {int(key): pair['choices'][key] for key in pair['choices']}
            question = Question(pair['pk'], pair['text'], temp_filepath, choices)
            questions[question.key] = question
        return questions

    def upload_question(self, text, diagram_path, choices, answer=""):
        """

        :param str text: text describing the question
        :param str diagram_path: path to the diagram image
        :param list choices: ex. ['5', '4', '2', '3', 'Cannot be determined']
        :return:
        """
        suburl = "/questions/upload/"
        request_url = urlparse.urljoin(self.server_url, suburl)
        if len(choices) > 0:
            has_choices = True
        else:
            has_choices = False
        valid = True

        # Get request
        r = requests.get(request_url)
        csrftoken = r.cookies['csrftoken']

        # Post request
        files = {'diagram': open(diagram_path, 'rb')}
        data = dict(text=text, has_choices=has_choices, answer=answer, valid=valid,
                    csrfmiddlewaretoken=csrftoken, html='false')
        cookies = dict(csrftoken=csrftoken)
        r = requests.post(request_url, files=files, data=data, cookies=cookies)
        if r.text == "-1":
            logging.error("Failed upload question: %s" %text)
            return False
        pk = r.text

        for idx, choice_text in enumerate(choices):
            result = self._upload_choice(idx+1, choice_text, pk)
            if not result:
                logging.error("Failed upload question: %s" %text)
                return False

        return True

    def _upload_choice(self, number, text, question_pk):
        '''
        Upload choice
        '''
        suburl = "/questions/upload/choice"
        request_url = urlparse.urljoin(self.server_url, suburl)

        # Get request
        r = requests.get(request_url)
        csrftoken = r.cookies['csrftoken']

        # Post request
        data = dict(number=number, text=text, question=question_pk,
                    csrfmiddlewaretoken=csrftoken, html='false')
        cookies = dict(csrftoken=csrftoken)
        r = requests.post(request_url, data=data, cookies=cookies)
        if r.text == "-1":
            logging.error("Failed to upload choice %d: %s" %(number, text))
            return False
        return True


def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv


def _decode_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv


geoserver_interface = GeoserverInterface(settings.GEOSERVER_URL)