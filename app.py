import os
import json
import sqlite3
import shortuuid

from flask import (
	Flask,
	url_for, # gets the url for a view
	render_template,
	request,
    redirect,
    abort,
)
from markupsafe import escape
from werkzeug.middleware.proxy_fix import ProxyFix

from cal import cal

DB = 'db.sqlite3'

def db():
    return sqlite3.connect(DB)

def init_db():
    con = db()
    cursor = con.cursor()

    with open('ddl.sql', 'r') as f:
        ddl = f.read()

    cursor.executescript(ddl)

    con.close()

if DB not in os.listdir(): init_db()

app = Flask(__name__)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

@app.route("/")
def index():
	return render_template("index.html")

@app.get("/new")
def new():
    
    eventuuid, invitationuuid = shortuuid.uuid(), shortuuid.uuid()

    con = db()
    cursor = con.cursor()
    cursor.execute(
        """
        INSERT INTO event (uuid, invitationuuid) 
        VALUES (?, ?);
        """, 
        [eventuuid, invitationuuid]
    )
    con.commit()
    con.close()

    return redirect(f"/event/{eventuuid}/edit")

@app.get("/event/<eventuuid>")
def event(eventuuid):
    con = db()
    cursor = con.cursor()

    # event data
    res = cursor.execute(
        """
        SELECT 
            startdate, 
            enddate, 
            name,
            invitationuuid
        FROM event
        WHERE uuid = ?;
        """, 
        [eventuuid]
    )
    row = res.fetchone()

    if not row: abort(404)

    startdate, enddate, name, invitationuuid = row

    # count of responses by date
    res = cursor.execute(
        """
        SELECT 
            rdate,
            count(*) as n 
        FROM 
            responsedate rd
            INNER JOIN response r
                on r.id = rd.responseid
        WHERE r.eventid = (SELECT id FROM event WHERE uuid = ?)
        GROUP BY rdate
        """, 
        [eventuuid]
    )
    rows = res.fetchall()
    con.close()

    return render_template(
        "event.html", 
        eventuuid=eventuuid,
        invitationuuid=invitationuuid,
        dates=cal(startdate, enddate),
        startdate=startdate, 
        enddate=enddate,
        name=name,
        counts=json.dumps({ row[0]: row[1] for row in rows }),
    )
    
    abort(404)

@app.route("/event/<eventuuid>/edit", methods=['GET', 'POST'])
def edit(eventuuid):
    if request.method == 'GET':
        con = db()
        cursor = con.cursor()
        res = cursor.execute(
            """
            SELECT 
                startdate, 
                enddate,
                name
            FROM event
            WHERE uuid = ?;
            """, 
            [eventuuid]
        )
        if res:
            startdate, enddate, name = res.fetchone()
            return render_template(
                "event-edit.html", 
                startdate=startdate, 
                enddate=enddate,
                name=name,
            )
        else:
            return render_template("event-edit.html")

        con.close()

    else:
        startdate = request.form['startdate']
        enddate = request.form['enddate']
        name = request.form['name']

        con = db()
        cursor = con.cursor()
        cursor.execute(
            """
            UPDATE event 
            SET 
                startdate = ?, 
                enddate = ?,
                name = ?
            WHERE uuid = ?;
            """, 
            [startdate, enddate, name, eventuuid]
        )
        con.commit()
        con.close()

        return redirect(f"/event/{eventuuid}")

@app.route("/event/<eventuuid>/delete", methods=['POST'])
def delete(eventuuid):
    con = db()
    cursor = con.cursor()
    
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute(
        """
        DELETE FROM event
        WHERE uuid = ?
        """,
        [eventuuid],
    )
    con.commit()
    con.close()

    return redirect("/")

@app.get("/invitation/<invitationuuid>")
def invitation(invitationuuid):
    con = db()

    cursor = con.cursor()
    res = cursor.execute(
        """
        SELECT uuid
        FROM event
        WHERE invitationuuid = ?;
        """, 
        [invitationuuid]
    )

    row = res.fetchone()
    
    if not row: abort(404)

    eventuuid = row[0]
    responseuuid = shortuuid.uuid()
    cursor.execute(
        """
        INSERT INTO response (uuid, eventid)
        VALUES (?, (SELECT id FROM event WHERE uuid = ?))
        """,
        [responseuuid, eventuuid]
    )
    con.commit()
    con.close()

    return redirect(f"/response/{responseuuid}")



@app.route("/response/<responseuuid>", methods=['GET', 'POST'])
def response(responseuuid):
    if request.method == 'GET':

        con = db()
        cursor = con.cursor()
        res = cursor.execute(
            """
            SELECT 
                startdate, 
                enddate,
                name
            FROM event
            WHERE id = (SELECT eventid FROM response WHERE uuid = ?);
            """, 
            [responseuuid]
        )
        row = res.fetchone() 

        if not row: abort(404)

        startdate, enddate, name = row
        res = cursor.execute(
            """
            SELECT guestname
            FROM response
            WHERE uuid = ?
            """,
            [responseuuid]
        )
        row = res.fetchone()

        if not row: abort(404)

        guestname = row[0]

        res = cursor.execute(
            """
            SELECT rdate
            FROM responsedate
            WHERE responseid = (SELECT id FROM response WHERE uuid = ?)
            """,
            [responseuuid]
        )
        rows = res.fetchall()
        selected_dates = [ row[0] for row in rows ]

        con.close()
        dates = cal(startdate, enddate, selected_dates)

        initial_selected = []
        for table, item in enumerate(dates):
            label, month = item
            for row, week in enumerate(month):
                for col, date in enumerate(week):
                    if date[0]:
                        if date[2] == 'selected':
                            initial_selected.append(f'{table},{row},{col}')


        return render_template(
            "response.html", 
            responseuuid=responseuuid,
            startdate=startdate, 
            enddate=enddate,
            name=name,
            dates=dates,
            initial_selected=json.dumps(initial_selected),
            guestname=guestname,
        )
        

    else:
        data = json.loads(request.get_data())
        dates = cal(data['startdate'], data['enddate'], [])

        selected_dates = []
        for selection in data['selected']:
            table, row, col = tuple(int(x) for x in selection.split(','))
            selected_dates.append(dates[table][-1][row][col])

        con = db()
        cursor = con.cursor()

        res = cursor.execute(
            """
            UPDATE response
            SET guestname = ?
            WHERE uuid = ?
            """,
            [data['guestname'], responseuuid]
        )

        res = cursor.execute(
            """
            DELETE FROM responsedate
            WHERE responseid = (SELECT id FROM response WHERE uuid = ?)
            """, 
            [responseuuid]
        )
        for date in selected_dates:
            res = cursor.execute(
                """
                INSERT INTO responsedate (responseid, rdate)
                VALUES ((SELECT id FROM response WHERE uuid = ?), ?)
                """, 
                [responseuuid, date[0]]
            )

        con.commit()
        con.close()

        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
