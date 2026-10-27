from dataclasses import dataclass
from datetime import datetime
from sqlite3 import Connection, Row
from typing import Protocol, Self

from passlib.context import CryptContext


class Table(Protocol):
    @staticmethod
    def create_table(conn: Connection): ...


@dataclass
class User:
    username: str
    email: str
    password: str | None = None
    id: int = 0

    def __post_init__(self):
        if not self.username.isalnum():
            raise ValueError(
                "You can only use digits and letters for username"
            )
        if "@" not in self.email:
            raise ValueError("Put a valid email.")

    @staticmethod
    def create_table(conn: Connection) -> None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                email TEXT,
                password_hash TEXT
            )
        """)

    def _hash_pass(self, pass_ctx: CryptContext) -> None:
        if not self.password:
            return
        self.password = pass_ctx.hash(self.password)

    def _compare_password(self, pass_ctx: CryptContext, password: str) -> bool:
        if not self.password:
            return False
        return pass_ctx.verify(password, self.password)

    def signup(self, pass_ctx: CryptContext, conn: Connection):
        self._hash_pass(pass_ctx)
        conn.execute(
            "INSERT INTO users (username, email, password_hash)"
            " VALUES (?, ?, ?)",
            (self.username, self.email, self.password),
        )
        conn.commit()

    @classmethod
    def login(
        cls,
        pass_ctx: CryptContext,
        conn: Connection,
        username: str,
        password: str,
    ) -> Self:
        field = "email" if "@" in username else "username"
        query = (
            "SELECT id, username, email, password_hash "
            f"FROM users WHERE {field} = ?"
        )
        cursor = conn.execute(query, (username,))
        row = cursor.fetchone()

        if not row:
            raise ValueError("Invalid Credentials")

        user = cls(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            password=row["password_hash"],
        )
        if not user._compare_password(pass_ctx, password):
            raise ValueError("Invalid Credentials")
        return user


@dataclass
class Comment:
    id: int
    post_slug: str
    username: str
    content: str
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def create_table(conn: Connection):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_slug TEXT,
                user_id INTEGER,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

    @classmethod
    def list_all(cls, conn: Connection, slug: str) -> list[Self]:
        cursor = conn.execute(
            """
            SELECT
                comments.id AS id,
                comments.post_slug AS post_slug,
                users.username AS username,
                comments.content AS content,
                comments.created_at AS created_at,
                comments.updated_at AS updated_at
            FROM comments
            JOIN users ON comments.user_id = users.id
            WHERE comments.post_slug = ?
            ORDER BY comments.id DESC
        """,
            (slug,),
        )
        return [cls(**row) for row in cursor.fetchall()]

    def post_comment(self, conn: Connection):
        cursor = conn.execute(
            "SELECT id FROM users WHERE username = ?", (self.username,)
        )
        user_row = cursor.fetchone()
        if not user_row:
            raise ValueError("Usuário not found.")
        user_id = user_row["id"] if isinstance(user_row, Row) else user_row[0]

        conn.execute(
            "INSERT INTO comments (post_slug, user_id, content, updated_at) "
            "VALUES (?, ?, ?, datetime('now'))",
            (self.post_slug, user_id, self.content),
        )
        conn.commit()
