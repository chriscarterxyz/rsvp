from datetime import datetime, timedelta
from collections import defaultdict

def weekday(date):
    return (date.weekday() + 1) % 7

def weekyear(date):
    if datetime(date.year, 1, 1).weekday() == 6:
        incr = 0
    else:
        incr = 1
    return int(date.strftime("%U")) + incr

def cal(start_date, end_date, selected_dates=[]):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    delta = end - start

    oldweek = weekyear(start) 
    oldmonth = start.month
    dates = [(start.strftime("%B %Y"), [[ (None,) ] * weekday(start) ])]
    for i in range(delta.days + 1):
        date = start + timedelta(days=i)
        week = weekyear(date)

        if date.month != oldmonth:
            oldmonth = date.month
            oldweek = week
            dates.append((date.strftime("%B %Y"), [[ (None,) ] * weekday(date)]))

        elif week != oldweek:
            oldweek = week
            dates[-1][-1].append([])

        date_str = date.strftime("%Y-%m-%d")
        dates[-1][-1][-1].append((
            date_str,
            f'0{date.day}' if date.day < 10 else str(date.day),
            'selected' if date_str in selected_dates else ''
        ))

    return dates

if __name__ == '__main__':
    cl = cal('2024-02-01', '2024-04-15')
    
    for month in cl:
        print(month[0], month[1])
        for week in month[2]:
            print([date[0] for date in week])
    
