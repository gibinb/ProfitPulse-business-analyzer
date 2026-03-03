import mysql.connector as mys

def get_connection():
    return mys.connect(
        host="localhost",
        user="root",
        password="Gibin@2004",
        database="login_db",
        port=3307
    )