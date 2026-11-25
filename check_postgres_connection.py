
import psycopg
from getpass import getpass

password = getpass("Enter PostgreSQL password: ")

try:
    with psycopg.connect(
        host="localhost",
        port=5432,
        dbname="pharma_sales",
        user="postgres",
        password=password
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT current_database(), current_user;"
            )
            result = cursor.fetchone()

            print("Connection successful!")
            print("Database:", result[0])
            print("Username:", result[1])

except psycopg.Error as error:
    print("Connection failed!")
    print(error)
