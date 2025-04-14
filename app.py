from flask import Flask, request, redirect, render_template
import random, string
import json
import os
import uuid
import time

app = Flask(__name__)

# File-based storage for Render
DATA_DIR = "/data" if os.environ.get("RENDER") else "."
DATA_FILE = os.path.join(DATA_DIR, "shortened_links.json")
TOKEN_FILE = os.path.join(DATA_DIR, "tokens.json")

def load_links():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_links(links):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(links, f)

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return {}

def save_tokens(tokens):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f)

def generate_slug(length=5):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_token():
    return str(uuid.uuid4())

@app.route("/", methods=["GET", "POST"])
def home():
    error = None
    if request.method == "POST":
        original_url = request.form["original_url"].strip()

        if not original_url.startswith(("http://", "https://")):
            original_url = "https://" + original_url

        try:
            slug = generate_slug()
            links = load_links()
            while slug in links:
                slug = generate_slug()

            trusted_hops = [
                "https://www.google.com/search?q=tech",
                "https://www.linkedin.com",
                "https://medium.com"
            ]
            links[slug] = {
                "url": original_url,
                "hops": trusted_hops
            }
            save_links(links)

            short_link = f"{request.url_root}{slug}"
            return render_template("index.html", short_link=short_link, error=None)
        except Exception:
            error = "Something went wrong. Try again."

    return render_template("index.html", short_link=None, error=error)

@app.route("/<slug>")
def cloak_redirect(slug):
    links = load_links()
    link_data = links.get(slug)
    if not link_data:
        return render_template("error.html", message="Invalid Link")

    token = generate_token()
    tokens = load_tokens()
    tokens[token] = {
        "slug": slug,
        "current_hop": 0,
        "expires": time.time() + 15
    }
    save_tokens(tokens)

    return redirect(f"/r/{token}", code=302)

@app.route("/r/<token>")
def process_redirect(token):
    tokens = load_tokens()
    token_data = tokens.get(token)
    if not token_data or token_data["expires"] < time.time():
        return render_template("error.html", message="Link Expired")

    slug = token_data["slug"]
    current_hop = token_data["current_hop"]

    links = load_links()
    link_data = links.get(slug)
    if not link_data:
        return render_template("error.html", message="Invalid Link")

    hops = link_data["hops"]
    final_url = link_data["url"]

    if current_hop < len(hops):
        token_data["current_hop"] += 1
        tokens[token] = token_data
        save_tokens(tokens)

        next_hop = hops[current_hop]
        next_redirect = f"/r/{token}"
        return render_template("redirect.html", hop_url=next_hop, next_url=next_redirect, final_url=final_url)
    else:
        del tokens[token]
        save_tokens(tokens)
        return redirect(final_url, code=302)

if __name__ == "__main__":
    app.run(debug=True)