# firebase_config.py
import firebase_admin
from firebase_admin import credentials, auth

# Only initialize once
cred = credentials.Certificate(r"fawstech-robotics-firebase-adminsdk-fbsvc-e3380ead3d.json")
firebase_app = firebase_admin.initialize_app(cred)
