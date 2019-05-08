import os
from uuid import uuid4

print("Welcome to the Mortimer Environment Variables Wizard.\
 We will ask you some questions to set the correct environment variables\
  for your Mortimer installation to work correctly.")

# set general environment variables
environment_variables = {
    "SECRET_KEY": uuid4(),

    "MONGODB_HOST": str(input("MongoDB Host Address: ")),
    "MONGODB_PORT": int(input("MongoDB Port: ")),

    "MONGODB_MORTIMER_DB": str(input("Mortimer DB Name: ")),
    "MONGODB_MORTIMER_USER": str(input("Mortimer DB User: ")),
    "MONGODB_MORTIMER_PW": str(input("Mortimer DB Password: ")),
    "MONGODB_MORTIMER_AUTHDB": str(input("Mortimer DB Authentication Database: ")),

    "MONGODB_ALFRED_DB": str(input("Alfred DB Name: ")),
    "MONGODB_ALFRED_USER": str(input("Alfred DB User: ")),
    "MONGODB_ALFRED_PW": str(input("Alfred DB Password: ")),
    "MONGODB_ALFRED_AUTHDB": str(input("Alfred DB Authentication Database: ")),

    "PAROLE": str(input("Passphrase for registration: "))
}

# set mail data if wanted
mail_use = ""
while mail_use not in ["y", "n"]:
    mail_use = str(input("Do you want to enable automatic password reset emails? (y/n): "))

if mail_use == "y":
    mail_environment_variables = {
        "MAIL_SERVER": str(input("Mail Server: ")),
        "MAIL_PORT": int(input("Mail Port: ")),
        "MAIL_USERNAME": str(input("Mail User: ")),
        "MAIL_PASSWORD": str(input("Mail Password: ")),
    }

for key, value in environment_variables.items():
    os.environ[key] = value

if mail_use == "y":
    for key, value in mail_environment_variables.items():
        os.environ[key] = value
