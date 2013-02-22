import os
import time
from multiprocessing import Pool
from django.conf import settings
import requests
import logging
import json
import logging, logging.handlers
import sys

log=logging.getLogger(__name__)

logger = logging.getLogger('simple_example')
http_handler = logging.handlers.HTTPHandler('127.0.0.1:9022', '/event', method='GET')
logger.addHandler(http_handler)

from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    """
    Run registered cron jobs
    """

    def handle_noargs(self, **options):
        log_file_sizes = {}
        i=0
        while True:
            log_files = self.get_log_files()
            length = len(log_files)
            for l_file in log_files:
                file_size = 0
                if l_file in log_file_sizes:
                    file_size = log_file_sizes[l_file]
                file_size = handle_single_log_file_serial(l_file,file_size,i)
                log_file_sizes[l_file] = file_size
            i+=1

    def get_log_files(self):
        all_directories = []
        all_directories.append(settings.LOG_READ_DIRECTORY)
        for directory in settings.DIRECTORIES_TO_READ:
            full_dir = os.path.join(settings.LOG_READ_DIRECTORY, directory)
            if os.path.isdir(full_dir):
                all_directories.append(full_dir)

        all_files = []
        for directory in all_directories:
            files_in_dir = os.listdir(directory)
            log_files = []
            for dir_file in files_in_dir:
                joined_filename = os.path.join(directory,dir_file)
                if os.path.isfile(joined_filename):
                    #or
                    if joined_filename.endswith(".log") or (".log" in joined_filename and not ".gz" in joined_filename):
                        log_files.append(joined_filename)
            all_files = all_files + log_files

        return all_files

def handle_single_log_file(args):

    import logging, logging.handlers
    import sys

    logger = logging.getLogger('simple_example')
    http_handler = logging.handlers.HTTPHandler('127.0.0.1:9022', '/event', method='GET')
    logger.addHandler(http_handler)

    filename = args
    file = open(filename,'r')

    #Find the size of the file and move to the end
    st_results = os.stat(filename)
    st_size = st_results[6]
    file.seek(st_size)

    i=0
    while True:
        try:
            where = file.tell()
            line = file.readline()
            if not line:
                time.sleep(1)
                file.seek(where)
            else:
                json_dict= line
                #response_text = _http_get(session,settings.LOG_POST_URL,json_dict)
                logger.critical(line)
        except:
            file.close()
            file = open(filename,'r')
    file.close()

def handle_single_log_file_serial(filename, filesize=0, run_number=0):
    file = open(filename,'r')

    #Find the size of the file and move to the end
    st_results = os.stat(filename)
    st_size = st_results[6]
    if filesize>0 and filesize <= st_size:
        file.seek(min(st_size,filesize))
    elif run_number==0:
        file.seek(st_size)

    lines_processed = 0
    last_size=0
    lines = []
    while True:
        where = file.tell()
        line = file.readline()
        if not line:
            time.sleep(1)
            last_size = where
            break
        else:
            json_dict= line
            lines.append(json_dict)
            lines_processed+=1
        if lines_processed > 100:
            response_text = _http_post(settings.LOG_POST_URL,json.dumps(lines))
            lines_processed=0
            lines=[]
    file.close()
    if len(lines)>0:
        response_text = _http_post(settings.LOG_POST_URL,json.dumps(lines))
    return last_size

def _http_post(url, data, timeout=10):
    '''
    Contact grading controller, but fail gently.
    Takes following arguments:
    session - requests.session object
    url - url to post to
    data - dictionary with data to post
    timeout - timeout in settings

    Returns (success, msg), where:
        success: Flag indicating successful exchange (Boolean)
        msg: Accompanying message; Controller reply when successful (string)
    '''
    session = requests.session()
    data = {'msg' : data}
    try:
        r = session.post(url, data=data, timeout=timeout, verify=False)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        log.error('Could not connect to server at %s in timeout=%f' % (url, timeout))
        return (False, 'Cannot connect to server.')

    if r.status_code not in [200]:
        log.error('Server %s returned status_code=%d' % (url, r.status_code))
        return (False, 'Unexpected HTTP status code [%d]' % r.status_code)
    return (True, r.text)

