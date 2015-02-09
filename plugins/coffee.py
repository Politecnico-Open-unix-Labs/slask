"""!coffee <command> controls the coffee maker. Available commands:
	*please* : makes you a coffee :)
	*list* : view the credit situation (_warning_: tags everyone that has positive credit)
	*reset <nick>* : resets the credit counter for <nick> (_warning_: works only for admins)"""
import json
import re
import serial
import time
import sqlite3 as lite

class NoSuchNick(Exception):
    pass

class CoffeeDB:
    def __init__(self):
        try:
            self.con = lite.connect('coffee.db')
            self.cur = self.con.cursor()    
            self.cur.execute("CREATE TABLE IF NOT EXISTS Coffee(nickname TEXT PRIMARY KEY, coins INTEGER)")
            self.con.commit()
        except lite.Error, e:
            if self.con:
                self.con.rollback()
            print("Error %s" % e.args[0])
            raise SystemExit
    
    def getCredit(self, nickname):
        self.cur.execute("SELECT coins FROM Coffee WHERE nickname=:Nick", 
                        {"Nick": nickname})
        self.con.commit()
        rows = list(self.cur.fetchall())
        if len(rows) == 0:
            raise NoSuchNick
        else:
            return rows[0][0]

    def setCredit(self, nickname, value):
        self.cur.execute("UPDATE Coffee SET coins=:CoinValue WHERE nickname=:Nick", 
                        {"Nick": nickname, "CoinValue" : int(value)})
        self.con.commit()

    def createUser(self, nickname):
        self.cur.execute("INSERT INTO Coffee(nickname, coins) VALUES (:Nick, 0)",
                        {"Nick": nickname})
        self.con.commit()

    def deleteUser(self, nickname):
        self.cur.execute("DELETE FROM Coffee WHERE nickname=:Nick",
                        {"Nick": nickname})
        self.con.commit()

    def getCreditList(self):
        self.cur.execute("SELECT * FROM Coffee")
        self.con.commit()
        return list(self.cur.fetchall())

class CoffeeMachine:
    """
    Object representing and controlling the coffee machine
    """
    def __init__(self, serialDevice = "/dev/ttyUSB0"):
        self.serobj = serial.Serial(serialDevice)
        self.stop()

    def start(self):
        """
        Start coffee dispensing
        """
        self.serobj.setDTR(True)

    def stop(self):
        """
        Stop coffee dispensing
        """
        self.serobj.setDTR(False)

def get_coffee_balance(db):
    """Gets the current balance of coffees"""
    #fetch from the db the list of users with balance > 0
    result = "".join([r[0] + ": " + str(r[1]) + "\n" for r in db.getCreditList() if r[1]>0])
    if not result:
        return u"Nobody wants a coffee :("
    else:
        return u"{0}".format(result)

def do_coffee(nick, state, db):
    """Makes a coffee!"""
    #let's check two people aren't making coffee at the same time    
    if not "doing_coffee" in state:
        state["doing_coffee"] = True
    else:
        if state["doing_coffee"]: 
            return u"Whoops! Wait for your turn please."
        else: state["doing_coffee"] = True

    #if the user do not exists create it. else, ++ on his credit
    try:
        db.setCredit(nick, db.getCredit(nick) + 1)
    except NoSuchNick:
        db.createUser(nick)
        credit = 1
        db.setCredit(nick, credit)
    
    #make a coffee through usb
    #c = CoffeeMachine()
    #c.start()
    #time.sleep(25)
    #c.stop()

    state["doing_coffee"] = False

    #warn the user
    return u"{0} your coffee is ready :)".format(nick)

def set_user_credit(admin, nick, new_credit, db):
    if admin["is_admin"]:
        db.setCredit(nick, new_credit)
        return u"New credit for {0} is {1}".format(nick, new_credit)

def on_message(msg, server):
    text = msg["text"]
    match = re.findall(r"!coffee (.*)", text)
    if not match: return

    #dear db, we are going to talk.
    db = CoffeeDB()
    print(msg)

    user = server["client"].server.users.get(msg["user"])

    if u"please" in match[0]:
        #get the real user
        return do_coffee(user["name"], server["config"], db)
    elif u"reset" in match[0]:
        nick = match[0].split("reset ")[1] #syntax: "!coffee reset $nick"
        return set_user_credit(user, nick, 0, db)
    elif u"set" in match[0]:
        nick, amount = match[0].split("set ")[1].split() #syntax: "!coffee set $nick $amount"
        return set_user_credit(user, nick, amount, db)
    elif u"list" in match[0]:
        return get_coffee_balance(db)
    return
