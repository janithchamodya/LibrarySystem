# database.py
import mysql.connector

class Database:
    def connect(self):
        return mysql.connector.connect(
            host="localhost",
            user="root",            # Use your MySQL username
            password="Chamod99$*",  # Use your MySQL password
            database="library_db"   # Use your actual database name
        )
