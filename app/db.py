import sqlite3

def db():
    conn = sqlite3.connect("/opt/ip-allow/ip_allow.db")
    conn.row_factory = sqlite3.Row
    return conn
