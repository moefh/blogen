
import pathlib
import datetime
import re
import os

def url_join(*parts):
    ret = '/'.join([ p.strip().strip('/') for p in parts if p.strip().strip('/') ])
    if (not ret.startswith('/')) and parts[0].startswith('/'):
        return '/' + ret
    return ret
