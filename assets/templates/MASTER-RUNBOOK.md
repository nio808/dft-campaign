# Master runbook ({{PROJECT}})

Append-only. One line per action anywhere in the project, written by `logbook.py log` (real clock, project time zone).
Format: `- <YYYY-MM-DD HH:MM> {{TZ}} | <TAG> | <folder> | <what, with numbers> | cites <ids> | <D-id>`
Tags: START INPUT GATE REVIEW LAUNCH CHECK ALERT FIX DONE FAILED KILL STOP ACCEPT HOLD MOVE SYNC RELEASE INCIDENT CORRECTION NOTE.
Corrections never edit old lines; append a CORRECTION line quoting what was wrong.

