import sqlite3
import logging

class Database:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        # Active support for foreign keys
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        self._create_tables()

    def delete_table(self):
        conn = self.conn
        cursor = self.cursor
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for table in tables:
            table_name = table[0]
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()

    def __close(self):
        self.delete_table()
        # Close cursor and connection
        self.cursor.close();
        logging.info("Database cursor closed.")
        self.conn.close()
        logging.info("Database connection closed.")

    def __del__(self):
        self.__close()

    def __create_user_table(self):
        conn = self.conn
        cursor = self.cursor
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user(
            userid INT PRIMARY KEY,
            username VARCHAR(15) NOT NULL UNIQUE
            );
        """)
        conn.commit()

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
        """)
        conn.commit()

    def _create_tables(self):
        self.__create_user_table()
        self.__create_link_table()


    def insert_user(self, uid, usrn):
        conn = self.conn
        cursor = self.cursor
        cursor.execute("""
            INSERT OR IGNORE INTO user (userid, username) VALUES (?, ?)
        """, (uid, usrn))
        conn.commit()

    def get_count_links(self, uid) -> int:
        cursor = self.cursor
        cursor.execute("""
            SELECT COUNT(*) as totale
            FROM link
            WHERE link.userid = ? 
            """, (uid,))
        return cursor.fetchone()[0]

    def get_tasks(self, uid) -> list:
        cursor = self.cursor
        cursor.execute("""
            SELECT taskid
            FROM link
            WHERE link.userid = ? 
            """, (uid,))
        return [tlp[0] for tlp in cursor.fetchall()]


    def get_all_tasks(self) -> list:
        cursor = self.cursor
        cursor.execute("""
            SELECT taskid
            FROM link
            """, )
        return [tlp[0] for tlp in cursor.fetchall()]

    def get_task(self, uid, url) -> str:
        cursor = self.cursor
        cursor.execute("""
            SELECT taskid
            FROM link
            WHERE link.userid = ? and link.url = ?
            """, (uid, url))
        return cursor.fetchone()[0]

    def get_user(self, uid) -> str:
        cursor = self.cursor
        cursor.execute("""
            SELECT userid
            FROM user
            WHERE user.userid = ? 
            """, (uid,))
        return cursor.fetchone()

    def get_links(self, uid) -> list:
        cursor = self.cursor
        cursor.execute("""
        SELECT url
        FROM link
        WHERE link.userid = ? 
        """, (uid,))
        return [tlp[0] for tlp in cursor.fetchall()]

    def check_link_exists(self, uid, url) -> bool:
        cursor = self.cursor
        cursor.execute("""
            SELECT 1
            FROM link
            WHERE link.url = ? AND link.userid = ?
            """, (url, uid))
        return cursor.fetchone() is not None


    def insert_link(self, uid, url, tskid):
        conn = self.conn
        cursor = self.cursor
        cursor.execute("""
            INSERT INTO link (userid, url, taskid) VALUES (?, ?, ?)
            """, (uid, url, tskid))
        conn.commit()

    def delete_user(self, uid):
        conn = self.conn
        cursor = self.cursor
        cursor.execute("""
            DELETE FROM user
            WHERE userid = ?
            """, (uid,))
        conn.commit()

    def delete_link(self, uid, url):
        conn = self.conn
        cursor = self.cursor
        cursor.execute("""
            DELETE FROM link
            WHERE userid = ? and url = ?
            """, (uid,url))
        conn.commit()


