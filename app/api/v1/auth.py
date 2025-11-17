from fastapi import APIRouter, HTTPException
from app.db.database import get_db_connection
from app.models.user_models import UserSignup, UserLogin
from app.utils.hash_util import hash_password, verify_password
from app.utils.jwt_util import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# signup

@router.post("/signup")
def signup_user(user: UserSignup):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()

    # Check if email already exists
    cursor.execute('SELECT * FROM users WHERE email = %s;', (user.email,))
    existing_user = cursor.fetchone()

    if existing_user:
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=409,
            detail="Email already registered. Please log in or use a different email."
        )

    hashed_pw = hash_password(user.password)

    cursor.execute(
        """
        INSERT INTO users (name, email, password, "userType")
        VALUES (%s, %s, %s, %s)
        RETURNING "userID", name, email, "userType", "createdAt";
        """,
        (user.name, user.email, hashed_pw, user.userType)
    )

    new_user = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    token = create_access_token({"user_id": new_user["userID"]})
    return {
        "message": "User registered successfully!",
        "user": new_user,
        "access_token": token
    }

# login

@router.post("/login")
def login_user(user: UserLogin):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = %s;', (user.email,))
    db_user = cursor.fetchone()

    if not db_user:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Invalid email or password")

    if not verify_password(user.password, db_user["password"]):
        cursor.close()
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"user_id": db_user["userID"]})

    cursor.close()
    conn.close()

    return {
        "message": "Login successful!",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "userID": db_user["userID"],
            "name": db_user["name"],
            "email": db_user["email"],
            "userType": db_user["userType"],
            "createdAt": db_user["createdAt"],
        }
    }
