import sqlite3
from typing import Any, Optional, Tuple

ALLOWED_TABLE: list[str] = ["users_auth", "users_data"]
ALLOWED_COLUMN: list[str] = [
    "id",
    "name",
    "quantity",
    "price_per_unit",
    "total",
    "arrived_date",
    "discount_start_date",
    "discount_end_date",
    "discount_percentage",
    "barcode",
    "status",
]
ALLOWED_TARGET: list[str | None] = [
    "id",
    "name",
    "quantity",
    "price_per_unit",
    "total",
    "arrived_date",
    "discount_start_date",
    "discount_end_date",
    "discount_percentage",
    "barcode",
    "status",
    None,
]


def create_connection(db_path: str) -> sqlite3.Connection:
    conn: sqlite3.Connection = sqlite3.connect(db_path)
    cur: sqlite3.Cursor = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    cur.execute("PRAGMA journal_mode = WAL;")
    return conn


class UsersAuth:

    def __init__(self, db_path: str, validator: Any) -> None:
        self.db_path: str = db_path
        self.validator: Any = validator
        self.create_table()

    def create_table(self) -> None:
        with create_connection(self.db_path) as conn:
            # Level Zero 
            cur: sqlite3.Cursor = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users_auth (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE,
                    user_name TEXT UNIQUE,
                    user_password TEXT
                )
                """
            )

    def db_register(
        self,
        email: str,
        user_name: str,
        user_password: str,
    ) -> bool:
        with create_connection(self.db_path) as conn:
            # Level Zero
            cur: sqlite3.Cursor = conn.cursor()
            cur.execute(
                """
                INSERT INTO users_auth (email, user_name, user_password)
                VALUES (?, ?, ?)
                """,
                (email, user_name, user_password),
            )
            return True

    def get_email(self, id: int) -> Optional[Tuple[Any, ...]]:
        with create_connection(self.db_path) as conn:
            # Level Easy
            cur: sqlite3.Cursor = conn.cursor()
            query = """SELECT email FROM users_auth WHERE id = ?"""
            cur.execute(query, (id,))
            response = cur.fetchone()
            return response[0] if response else None
     
    def get_email_by_email(self, email: str):
        with create_connection(self.db_path) as conn:
            #level Zero
            cur: sqlite3.Cursor = conn.cursor()
            query = """SELECT email FROM users_auth WHERE email = ?"""
            cur.execute(query, (email,))
            response = cur.fetchone()
            return response[0] if response else None
    def db_ac_delete(self, id: int) -> bool | dict[str, Any]:
        # Level Zero
        with create_connection(self.db_path) as conn:
            cur: sqlite3.Cursor = conn.cursor()
            query: str = "DELETE FROM users_auth WHERE id = ?"
            cur.execute(query, (id,))
            return True

    def password_reset(self, new_password: str, id: int) -> bool:
        with create_connection(self.db_path) as conn:
            # Level Easy
            cur: sqlite3.Cursor = conn.cursor()
            query = """UPDATE users_auth SET user_password = ? WHERE id = ?"""
            cur.execute(query, (new_password, id))
            return True

    def get_password(self, email: str) -> str:
        with create_connection(self.db_path) as conn:
            # Level Easy
            cur: sqlite3.Cursor = conn.cursor()
            query = """SELECT user_password FROM users_auth WHERE email = ?"""
            cur.execute(query, (email,))
            password = cur.fetchone()[0]
            return password

    def get_user_name(self, email: str) -> str:
        with create_connection(self.db_path) as conn:
            # Level Easy
            cur: sqlite3.Cursor = conn.cursor()
            query = """SELECT user_name FROM users_auth WHERE email = ?"""
            cur.execute(query, (email,))
            user_name = cur.fetchone()[0]
            return user_name

    def get_id(self, email: str) -> int:
        with create_connection(self.db_path) as conn:
            # Level Easy
            cur: sqlite3.Cursor = conn.cursor()
            query = """SELECT id FROM users_auth WHERE email = ?"""
            cur.execute(query, (email,))
            id = cur.fetchone()[0]
            return id


class UsersData:

    def __init__(self, db_path: str, validator: Any) -> None:
        self.db_path: str = db_path
        self.validator: Any = validator
        self.create_table()

    def create_table(self) -> None:
        with create_connection(self.db_path) as conn:
            # Level Zero 
            cur: sqlite3.Cursor = conn.cursor()
            cur.execute("""
               CREATE TABLE IF NOT EXISTS users_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    quantity NUMERIC,
    price_per_unit FLOAT,
    total FLOAT,
    arrived_date DATE,
    discount_start_date DATE,
    discount_end_date DATE,
    discount_percentage FLOAT,
    barcode TEXT,
    status TEXT,
    FOREIGN KEY (user_id) REFERENCES users_auth(id) ON DELETE CASCADE,
    UNIQUE (user_id, name)
)
            """)

    def db_create(
        self,
        user_id: int,
        item_names: list[str],
        item_quantity: list[float | int],
        item_costs_per_unit: list[float],
        item_total_costs: list[float],
        items_arrived_date: list[str],
        discount_start_date: list[str | None],
        discount_end_date: list[str | None],
        discount_percentage: list[float | None],
        barcode_list: list[str],
        status_list: list[str],
    ) -> bool | dict[str, Any]:

        with create_connection(self.db_path) as conn:
            # Level Medium 
            cur: sqlite3.Cursor = conn.cursor()
            outer_list: list[list[Any]] = [
                item_names,
                item_quantity,
                item_costs_per_unit,
                item_total_costs,
                items_arrived_date,
                discount_start_date,
                discount_end_date,
                discount_percentage,
                barcode_list,
                status_list,
            ]
            check: Any = self.validator.create_helper(
                outer_list,
                ALLOWED_COLUMN
            )
            if isinstance(check, dict):
                return check
            
            items_to_insert: list[dict[str, Any]] = []
            for (
                name,
                quantity,
                cost_per_unit,
                total,
                arrived_date,
                dis_start_date,
                dis_end_date,
                dis_percentage,
                barcode,
                status,
            ) in zip(
                item_names,
                item_quantity,
                item_costs_per_unit,
                item_total_costs,
                items_arrived_date,
                discount_start_date,
                discount_end_date,
                discount_percentage,
                barcode_list,
                status_list,
            ):
                items_to_insert.append(
                    {
                        "user_id": user_id,
                        "name": name,
                        "quantity": quantity,
                        "price_per_unit": cost_per_unit,
                        "total": total,
                        "arrived_date": arrived_date,
                        "discount_start_date": dis_start_date,
                        "discount_end_date": dis_end_date,
                        "discount_percentage": dis_percentage,
                        "barcode": barcode,
                        "status": status,
                    }
                )

            query: str = """
                INSERT INTO users_data (
                    user_id, name, quantity, price_per_unit, total,
                    arrived_date, discount_start_date, discount_end_date,
                    discount_percentage, barcode, status
                ) VALUES (
                    :user_id, :name, :quantity, :price_per_unit, :total,
                    :arrived_date, :discount_start_date, :discount_end_date,
                    :discount_percentage, :barcode, :status
                )
            """
            cur.executemany(query, items_to_insert)
            return True

    def db_show(
        self,
        user_id: int
        ) -> list[Tuple[Any, ...]] | dict[str, str]:
   
        with create_connection(self.db_path) as conn:
            # Level Easy
            cur: sqlite3.Cursor = conn.cursor()
            query: str = "SELECT * FROM users_data WHERE user_id = ?"
            cur.execute(query, (user_id,))
            return cur.fetchall()

    def db_update(
        self,
        user_id: int,
        field_names: list[str],
        update_values: list[Any],
        identifier_names: list[str],
        identifier_values: list[Any],
    ) -> bool | dict[str, Any]:
        with create_connection(self.db_path) as conn:
            # Level Medium 
            cur: sqlite3.Cursor = conn.cursor()
            main_lists: list[list[str]] = [field_names, identifier_names]
            secondary_lists: list[list[Any]] = [
                update_values,
                identifier_values,
            ]
            check: Any = self.validator.update_helper(
                main_lists,
                secondary_lists,
                ALLOWED_COLUMN
            )
            if isinstance(check, dict):
                return check
                
            update_params: list[Tuple[Any, int, Any]] = [
                (value, user_id, where_value)
                for value, where_value in zip(
                    update_values,
                    identifier_values,
                )
            ]
            query_params: list[str] = [
                f"UPDATE users_data SET {name} = ? WHERE user_id = ? AND {where} = ?"
                for name, where in zip(field_names, identifier_names)
            ]
            for i in range(len(field_names)):
                cur.execute(query_params[i], update_params[i])
            return True

    def db_delete(
        self,
        user_id: int,
        id_list: list[int],
    ) -> bool | dict[str, Any]:
        with create_connection(self.db_path) as conn:
            # Level Easy 
            cur: sqlite3.Cursor = conn.cursor()
            params: list[Tuple[int, int]] = [(user_id, item) for item in id_list]
            query: str = "DELETE FROM users_data WHERE user_id = ? AND id = ?"
            cur.executemany(query, params)
            return True
            