import os
from sqlite3.dbapi2 import Cursor

import requests
import validators
import sqlite3
import re
import smtplib
from bs4 import BeautifulSoup
from lxml import etree as et
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from validators.url import url
from werkzeug.useragents import UserAgent
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from flask_sqlalchemy import SQLAlchemy
import atexit
from helpers import check_email



def compare():

    # conn = sqlite3.connect('data.db', check_same_thread=False)
    # c = conn.cursor()
    
    # d = c.execute("SELECT * FROM emails")
    # d = c.fetchall()

    d = db.session.query(Amazon).all()

    for entry in d:
        email = entry.email
        url = entry.url
        price = entry.priceAlert
        useragent = entry.useragent

        currentPrice = check_price(url, useragent)

        if currentPrice <= price:
            send_email(email, url, price)

    conn.close()


conn = sqlite3.connect('data.db', check_same_thread=False)

c = conn.cursor()

# c.execute("""CREATE TABLE emails (
#             email TEXT,
#             url TEXT,
#             priceAlert REAL
#             )""")
            
# c.execute("""INSERT INTO emails VALUES ('justin.picks88@gmail.com', 
#             'https://www.amazon.ca/dp/B08C1TR9X6/ref=ods_gw_evg_gwd_btf_smp_snp_en_070121?pf_rd_r=39X0DWTDRXA2XC9WSTHH&pf_rd_p=1e63de0a-d85b-4cdd-82ab-b7771d38e5a8&pd_rd_r=621fe901-9bef-489a-99d5-bd787e634989&pd_rd_w=3b1Ji&pd_rd_wg=DfeRa&ref_=pd_gw_unk', 
#             '54.99')""")


app = Flask(__name__)

ENV = 'prod'

if ENV == 'dev':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:123@localhost/amazon1'

else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://ofsuhgiilkyipq:42b6dce0475b68da87d1763404b71192236991faaea448af9f5c20a34a590044@ec2-54-83-82-187.compute-1.amazonaws.com:5432/dfu4u8shea2uc6'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Amazon(db.Model):
    __tablename__ = 'amazon1'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String)
    url = db.Column(db.String)
    priceAlert = db.Column(db.Float)
    useragent = db.Column(db.String)

    def __init__(self, email, url, priceAlert, useragent):
        self.email = email
        self.url = url
        self.priceAlert = priceAlert
        self.useragent = useragent


scheduler = BackgroundScheduler()
scheduler.add_job(func=compare, trigger="interval", seconds=30)
scheduler.start()

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":

        link = request.form.get("url")

        if not validators.url(link):
            return "Enter a valid URL"

        user_agent = UserAgent(request.headers.get('User-Agent')).string

        headers = {"User-Agent": user_agent, "Referer": link}        

        page = requests.get(link, headers=headers)

        soup = BeautifulSoup(page.content, 'html.parser')

        title = soup.find(id="productTitle").get_text().strip()

        price = soup.find(id="priceblock_ourprice")

        if price == None:
           price = soup.find(id="priceblock_saleprice")
           if price == None:
                price = soup.find(id="priceblock_dealprice")

        price = price.get_text().strip()


        convertedPrice = (price[1:])

        convertedPrice = float(convertedPrice)
    
        return render_template("quoted.html", price=price, title=title, convertedPrice=convertedPrice, link=link)


    return render_template("index.html")


@app.route("/email", methods=["GET", "POST"])
def email():
    if request.method == "POST":

        useragent = UserAgent(request.headers.get('User-Agent')).string

        priceAlert = float(request.form.get("priceAlert"))

        email = request.form.get("email")

        url = request.form.get("link")

        if priceAlert <= 0:
            return "Enter a positive number"

        if not check_email(email):
            return "Invalid Email"
        
        data = Amazon(email, url, priceAlert, useragent)
        db.session.add(data)
        db.session.commit()


        # c.execute("INSERT INTO emails (email, url, priceAlert, useragent) VALUES(?,?,?, ?)", (email, url, priceAlert, useragent))

        # conn.commit()

        # conn.close()

        return redirect("/")

    return redirect("/")


def check_price(url, useragent):

    headers = {"User-Agent": useragent, "Referer": url}

    page = requests.get(url, headers=headers)

    soup = BeautifulSoup(page.content, 'html.parser')
    
    price = soup.find(id="priceblock_ourprice")

    if price == None:
        price = soup.find(id="priceblock_saleprice")
        if price == None:
            price = soup.find(id="priceblock_dealprice")

    price = price.get_text().strip()

    convertedPrice = (price[1:])

    convertedPrice = float(convertedPrice)

    return convertedPrice


def send_email(email, link, price):

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.ehlo()

    server.login('justin.picks88@gmail.com', 'gpsddwiadslhtsvd')

    subject = 'Amazon Price Tracker: The Price Fell Below Your Target!'
    body = f'Your tracked item fell below your target price of {price}. \r\r\nCheck the Amazon link: {link}'

    msg = f'Subject: {subject}\n\n{body}'

    server.sendmail('justin.picks88@gmail.com', f'{email}', msg)

    print('Email has been sent!')

    server.quit()

atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':

    app.run()