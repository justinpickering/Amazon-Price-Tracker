import os
import re

from flask import redirect, render_template, request, session

def check_email(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    if(re.match(regex, email)):
        return True
    else:
        return False
