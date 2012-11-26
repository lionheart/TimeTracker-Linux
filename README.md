![Build status](https://secure.travis-ci.org/gxela/TimeTracker.png?branch=master)

#[TimeTracker](http://aurora.io/timetracker)
----

*This Software is still beta*, please use at your own risk.

##About

Track time with your harvestapp.com account while working on projects.
>
Currently there are two different ways to handle time tracking with TimeTracker.     
Basic and Advanced. They are different in that, Basic uses no working parts and Advanced utilizes harvest api to run the timer. 

###Basic Interface
![Basic Interface](https://raw.github.com/gxela/TimeTracker/85889dabfe521f46399e5e3642bad86ccf6fdf44/data/media/screenshot-timetracker-basic.png)

* Harvest timer never runs. No moving parts. The interval you set in preferences is incremented to the desired entry on submit.
* Notes are appended to the current running entry project task
* Uses #TimerStarted, #TimerStopped, #SwitchTo markers and updated_at field

##

###Advanced Interface
![Advanced Interface](https://raw.github.com/gxela/TimeTracker/f80cec38dc54ef342a7d64e7b6ffef0615a1b362/data/media/screenshot-timetracker-advanced.png)

* Harvest meter is running. **Don't Forget To Stop The Timer**
* Start, Stop, Modify entries of projects and tasks
* Notification Message on Interval
* Clear lingering timers from previous days that may be still running(7 days back by default)

##Prerequisites

    * [pygtk](http://www.pygtk.org/) for GUI
    * [pytz](http://pypi.python.org/pypi/pytz) for timezone stuff(may remove dependency soon)
    * [dateutil](http://pypi.python.org/pypi/python-dateutil)
    * [requests](http://pypi.python.org/pypi/requests) for Harvest API Client

##Install

###Windows

###Linux

###Mac