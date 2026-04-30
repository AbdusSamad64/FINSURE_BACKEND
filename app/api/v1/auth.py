from fastapi import APIRouter, HTTPException
from app.db.database import get_db_connection
from app.models.user_models import UserSignup, UserLogin, UserEdit, ChangePassword
from app.utils.hash_util import hash_password, verify_password
from app.utils.jwt_util import create_access_token, create_pending_2fa_token, get_current_user
from fastapi import Depends

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

def connect_to_db():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        yield conn
    finally:
        conn.close()

# signup

@router.post("/signup")
def signup_user(user: UserSignup, conn=Depends(connect_to_db)):

    with conn.cursor() as cursor:
    # Check if email already exists
        cursor.execute('SELECT * FROM users WHERE email = %s;', (user.email,))
        existing_user = cursor.fetchone()

        if existing_user:
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

    token = create_access_token({"user_id": new_user["userID"]})
    return {
            "message": "User registered successfully!",
            "user": new_user,
            "access_token": token
            }

# login

@router.post("/login")
def login_user(user: UserLogin, conn=Depends(connect_to_db)):
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM users WHERE email = %s;', (user.email,))
        db_user = cursor.fetchone()

    if not db_user:
        raise HTTPException(status_code=404, detail="Invalid email or password")

    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if db_user.get("totp_enabled"):
        pending_token = create_pending_2fa_token(db_user["userID"])
        return {
            "message": "Two-factor authentication required",
            "requires_2fa": True,
            "two_factor_token": pending_token,
            "token_type": "2fa_pending",
        }

    token = create_access_token({"user_id": db_user["userID"]})

    return {
        "message": "Login successful!",
        "access_token": token,
        "token_type": "bearer",
        "requires_2fa": False,
        "user": {
            "userID": db_user["userID"],
            "name": db_user["name"],
            "email": db_user["email"],
            "userType": db_user["userType"],
            "createdAt": db_user["createdAt"],
        }
    }

# update profile (name & email)

@router.patch("/edit/me")
def edit_profile(user: UserEdit, curr_user: dict = Depends(get_current_user), conn=Depends(connect_to_db)):
    with conn.cursor() as cursor:
        # update both
        if user.email != curr_user['email']:    # input email not equal to current email
            cursor.execute('SELECT * FROM users WHERE email = %s;', (user.email,))
            existing_user = cursor.fetchone()
            if existing_user:    # do not update if there is an acc on input email
                raise HTTPException(status_code=409, detail='unable to edit your email')
            else:
                cursor.execute('UPDATE users SET name=%s, email=%s WHERE "userID"=%s RETURNING name, email;', (user.name, user.email, curr_user['userID']))
                updated_user = cursor.fetchone()
                conn.commit()

                return {
                    "message": "Profile updated successfully",
                    "user": updated_user
                }

        # update name only
        elif user.name != curr_user['name']:
            cursor.execute('UPDATE users SET name=%s WHERE "userID"=%s RETURNING name, email;', (user.name, curr_user['userID']))
            updated_user = cursor.fetchone()
            conn.commit()

            return {
                    "message": "Profile updated successfully",
                    "user": updated_user
                }
        else:
            return {
                    "message": "Nothing to update"
                }


# change password
@router.patch('/change-password')
def change_password(credentials: ChangePassword, curr_user: dict = Depends(get_current_user), conn=Depends(connect_to_db)):
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM users WHERE email = %s;', (curr_user['email'],))
        logined_user = cursor.fetchone()

        # match current pw from user with existing pw in db
        if not verify_password(credentials.current_password, logined_user["password"]):
            raise HTTPException(status_code=401, detail="incorrect current password")
        
        hashed_pw = hash_password(credentials.new_password)

        cursor.execute('UPDATE users SET password=%s WHERE "userID"=%s;', (hashed_pw, curr_user['userID']))
        conn.commit()
        return {
            "message": "Password updated successfully."
        }
