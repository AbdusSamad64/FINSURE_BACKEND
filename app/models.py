from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, CheckConstraint, func, Boolean
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    userID = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    # usertype can be either freelancer or businessman (case insensitive)
    userType = Column(String, nullable=False)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())

    accounts = relationship('Account', back_populates='user')
    transactions = relationship('Transaction', back_populates='user')

    __table_args__ = (
        CheckConstraint("LOWER(\"userType\") IN ('freelancer', 'businessman')", name="check_user_type"),
    )


class Bank(Base):
    __tablename__ = "banks"
    
    bankID = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    accounts = relationship('Account', back_populates='bank')


class Account(Base):
    __tablename__ = "accounts"

    accID = Column(Integer, primary_key=True)
    userID = Column(Integer, ForeignKey("users.userID"))
    bankID = Column(Integer, ForeignKey("banks.bankID"))
    accountTitle = Column(String, nullable=False)
    accountNo = Column(String)
    iban = Column(String)

    bank = relationship('Bank', back_populates='accounts')
    user = relationship('User', back_populates='accounts')
    transactions = relationship('Transaction', back_populates='account')


class Category(Base):
    __tablename__ = "categories"

    categID = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    transactions = relationship('Transaction', back_populates='category')


class Transaction(Base):
    __tablename__ = "transactions"
    
    # trxID: db assigned
    trxID = Column(Integer, primary_key=True, index=True)
    # trxNo: extracted from statement
    trxNo = Column(Integer)
    date = Column(DateTime(timezone=True))
    trxDetail = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    trxType = Column(String, nullable=False)
    isTaxable = Column(Boolean)
    userID = Column(Integer, ForeignKey("users.userID"), nullable=False)
    accID = Column(Integer, ForeignKey("accounts.accID"), nullable=False)
    categID = Column(Integer, ForeignKey("categories.categID"), nullable=False)

    user = relationship('User', back_populates='transactions')
    account = relationship('Account', back_populates='transactions')
    category = relationship('Category', back_populates='transactions')


    __table_args__ = (
        CheckConstraint("LOWER(\"trxType\") IN ('debit', 'credit')", name="check_trx_type"),
    )

