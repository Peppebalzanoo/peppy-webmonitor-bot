import sqlite3
import logging


class Database:
    # Initialize the database connection and create necessary tables
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)  # Connect to the SQLite database
        self.cursor = self.conn.cursor()  # Create a cursor object to interact with the database
        # Active support for foreign keys
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        self._create_tables()  # Call method to create tables

    # Method to delete all tables in the database
    def delete_table(self):
        conn = self.conn
        cursor = self.cursor
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")  # Get all table names
        tables = cursor.fetchall()  # Fetch all table names
        for table in tables:
            table_name = table[0]
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")  # Drop each table if it exists
        conn.commit()  # Commit changes to the database

    # Private method to close the database connection and cursor
    def __close(self):
        self.delete_table()  # Delete all tables before closing
        # Close cursor and connection
        self.cursor.close()
        logging.info("Database cursor closed.")  # Log that the cursor has been closed
        self.conn.close()  # Close the connection to the database
        logging.info("Database connection closed.")  # Log that the connection has been closed

    # Destructor to ensure cleanup when the object is deleted
    def __del__(self):
        self.__close()  # Call the close method

    # Private method to create the user table if it doesn't exist
    def __create_user_table(self):
        conn = self.conn
        cursor = self.cursor
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user(
            userid INT PRIMARY KEY,
            username VARCHAR(15) NOT NULL UNIQUE
            );
        """)  # SQL command to create user table
        conn.commit()  # Commit changes to the database

    # Private method to create the link table if it doesn't exist
    def __create_link_table(self):
        conn = self.conn
        cursor = self.cursor
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS link(
            url TEXT PRIMARY KEY,
            userid INT,
            taskid TEXT NOT NULL,
            FOREIGN KEY (userid) REFERENCES user(userid) ON DELETE CASCADE
            );
        """)  # SQL command to create link table with foreign key reference to user table
        conn.commit()  # Commit changes to the database

    # Method to create both user and link tables by calling private methods
    def _create_tables(self):
        self.__create_user_table()  # Create user table
        self.__create_link_table()  # Create link table

    # Method to insert a new user into the user table, ignoring duplicates
    def insert_user(self, uid, usrn):
        conn = self.conn
        cursor = self.cursor
        cursor.execute("""
            INSERT OR IGNORE INTO user (userid, username) VALUES (?, ?)
        """, (uid, usrn))  # Insert user data into the user table if it doesn't already exist
        conn.commit()  # Commit changes to the database

    # Method to count how many links a user is following
    def get_count_links(self, uid) -> int:
        cursor = self.cursor
        cursor.execute("""
            SELECT COUNT(*) as totale
            FROM link
            WHERE link.userid = ? 
            """, (uid,))  # Count links associated with a specific user ID
        return cursor.fetchone()[0]  # Return the count of links

    # Method to retrieve all task IDs associated with a specific user ID
    def get_tasks(self, uid) -> list:
        cursor = self.cursor
        cursor.execute("""
            SELECT taskid
            FROM link
            WHERE link.userid = ? 
            """, (uid,))  # Select task IDs for a specific user ID
        return [tlp[0] for tlp in cursor.fetchall()]  # Return a list of task IDs

    # Method to retrieve all task IDs from the link table
    def get_all_tasks(self) -> list:
        cursor = self.cursor
        cursor.execute("""
            SELECT taskid
            FROM link
            """, )  # Select all task IDs from link table
        return [tlp[0] for tlp in cursor.fetchall()]  # Return a list of task IDs

    # Method to retrieve a specific task ID based on user ID and URL
    def get_task(self, uid, url) -> str:
        cursor = self.cursor
        cursor.execute("""
            SELECT taskid
            FROM link
            WHERE link.userid = ? and link.url = ?
            """, (uid, url))  # Select task ID for specific user ID and URL
        return cursor.fetchone()[0]  # Return the task ID

    # Method to retrieve a user's information based on their user ID
    def get_user(self, uid) -> str:
        cursor = self.cursor
        cursor.execute("""
            SELECT userid
            FROM user
            WHERE user.userid = ? 
            """, (uid,))  # Select user information based on user ID
        return cursor.fetchone()  # Return user's information

    # Method to retrieve all URLs followed by a specific user
    def get_links(self, uid) -> list:
        cursor = self.cursor
        cursor.execute("""
        SELECT url
        FROM link
        WHERE link.userid = ? 
        """, (uid,))  # Select URLs for a specific user ID
        return [tlp[0] for tlp in cursor.fetchall()]  # Return a list of URLs

    # Method to check if a specific URL already exists for a given user
    def check_link_exists(self, uid, url) -> bool:
        cursor = self.cursor
        cursor.execute("""
            SELECT 1
            FROM link
            WHERE link.url = ? AND link.userid = ?
            """, (url, uid))  # Check if URL exists for specific user ID
        return cursor.fetchone() is not None  # Return True if URL exists, else False

    # Method to insert a new link into the link table
    def insert_link(self, uid, url, tskid):
        conn = self.conn
        cursor = self.cursor
        cursor.execute("""
            INSERT INTO link (userid, url, taskid) VALUES (?, ?, ?)
            """, (uid, url, tskid))  # Insert new link data into link table
        conn.commit()  # Commit changes to the database

    # Method to delete a user from the user table based on their user ID
    def delete_user(self, uid):
        conn = self.conn
        cursor = self.cursor
        cursor.execute("""
            DELETE FROM user
            WHERE userid = ?
            """, (uid,))  # Delete specific user from user table
        conn.commit()  # Commit changes to the database

    # Method to delete a specific link for a given user
    def delete_link(self, uid, url):
        conn = self.conn
        cursor = self.cursor
        logging.info(f"Deleting link {url} for user {uid}.")
        cursor.execute("""  
             DELETE FROM link  
             WHERE userid = ? and url = ?  
             """, (uid, url))
        conn.commit()
