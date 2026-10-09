
from flask import Flask, request, render_template_string
import os 
import base64
import json

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.storage.blob import ContentSettings
STORAGE_ACCOUNT_NAME = os.environ.get("STORAGE_ACCOUNT_NAME")
CONTAINER_NAME = "felanmalan-bilagor"

def get_blob_service_client():
    if not STORAGE_ACCOUNT_NAME:
        raise RuntimeError("STORAGE_ACCOUNT_NAME saknas")

    account_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"

    return BlobServiceClient(
        account_url=account_url,
        credential=DefaultAzureCredential()
    )

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
  
<form action="/submit" method="post" enctype="multipart/form-data">
    <label>Namn</label>
    <input name="name" required>

    <label>E-post</label>
    <input type="email" name="email" required>

    <label>Rubrik</label>
    <input name="title" required>

    <label>Beskrivning</label>
    <textarea name="message" required></textarea>

    <label>Bild (valfritt)</label>
    <input type="file" name="image" accept="image/*">

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
    title = request.form.get("title", "").strip()
    message = request.form.get("message", "").strip()
    image = request.files.get("image")

    if not name or not email or not title or not message:
        return "Alla obligatoriska fält måste fyllas i.", 400

    if image and image.filename:
        if image.mimetype not in ("image/jpeg", "image/png"):
            return "Endast JPG och PNG är tillåtna.", 400

    
    if image and image.filename:
        import uuid

        blob_name = f"{uuid.uuid4()}.jpg"
        if image.mimetype == "image/png":
            blob_name = f"{uuid.uuid4()}.png"

        try:
            blob_service = get_blob_service_client()
            blob_client = blob_service.get_blob_client(
                container=CONTAINER_NAME,
                blob=blob_name
            )

            blob_client.upload_blob(
                image.stream,
                overwrite=False,
                content_settings=ContentSettings(
                    content_type=image.mimetype
                )
            )
        except Exception:
            app.logger.exception("Bilduppladdning misslyckades")
            return "Kunde inte spara bilden.", 500

    

    # Spara felanmalan som JSON
    from datetime import datetime, timezone
    import uuid

    arende_id = str(uuid.uuid4())
    arende = {
        "id": arende_id,
        "namn": name,
        "epost": email,
        "rubrik": title,
        "beskrivning": message,
        "bild": blob_name if image and image.filename else None,
        "skapad": datetime.now(timezone.utc).isoformat(),
        "status": "Ny"
    }

    try:
        blob_service = get_blob_service_client()
        blob_client = blob_service.get_blob_client(
            container=CONTAINER_NAME,
            blob=f"arenden/{arende_id}.json"
        )
        blob_client.upload_blob(
            json.dumps(arende, ensure_ascii=False).encode("utf-8"),
            overwrite=False,
            content_settings=ContentSettings(
                content_type="application/json"
            )
        )
    except Exception:
        app.logger.exception("Kunde inte spara felanmalan")
        return "Kunde inte spara arendet.", 500        


    return f"Felanmälan registrerad! Ärendenummer: {arende_id}"

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
