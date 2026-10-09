
from flask import Flask, request, render_template_string
import os 
import base64
import json

def get_user_roles():
    encoded = request.headers.get("X-MS-CLIENT-PRINCIPAL")
    if not encoded:
        return []

    try:
        principal = json.loads(
            base64.b64decode(encoded).decode("utf-8")
        )
        return [
            claim.get("val")
            for claim in principal.get("claims", [])
            if claim.get("typ") in (
                "roles",
                "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"
            )
        ]
    except (ValueError, TypeError, UnicodeError):
        return []


app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Nordvik</title>
</head>
<body>
    <h1>Nordvik</h1>
    <h2>Felanmälan</h2>
    <form action="/submit" method="post">
        <label>Namn</label>
        <input name="name" required>
        <label>E-post</label>
        <input type="email" name="email" required>
        <label>Meddelande</label>
        <textarea name="message" required></textarea>
        <button type="submit">Skicka ärende</button>
    </form>
</body>
</html>
"""

@app.get("/")
def home():
    return render_template_string(HTML)

@app.post("/submit")
def submit():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not email or not message:
        return "Alla fält måste fyllas i.", 400

    return "Test lyckades. Ingen data har sparats."

@app.get("/my-role")
def my_role():
    roles = get_user_roles()
    if not roles:
        return "Ingen roll hittades", 403
    return "Dina roller: " + ", ".join(roles)

@app.get("/admin")
def admin_page():
    roles = get_user_roles()

    if "Administrator" not in roles and "Förvaltare" not in roles:
        return "Åtkomst nekad", 403

    return "Välkommen till Nordviks administration!"

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
