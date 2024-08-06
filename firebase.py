import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate("daily-j-cd58c-9f7ba6efd040.json")
firebase_admin.initialize_app(cred)
