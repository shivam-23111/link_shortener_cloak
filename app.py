from flask import Flask, request, redirect, render_template
import random, string
import base64
import json
import time
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def generate_slug(length=5):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def encode_url_data(url, hops):
    # Encode URL and hops into a JSON string, then base64
    data = json.dumps({"url": url, "hops": hops})
    return base64.urlsafe_b64encode(data.encode()).decode()

def decode_url_data(slug):
    # Decode base64 to JSON
    try:
        data = base64.urlsafe_b64decode(slug.encode()).decode()
        return json.loads(data)
    except Exception as e:
        logger.error(f"Failed to decode slug: {str(e)}")
        return None

@app.route("/", methods=["GET", "POST"])
def home():
    error = None
    if request.method == "POST":
        original_url = request.form["original_url"].strip()

        if not original_url.startswith(("http://", "https://")):
            original_url = "https://" + original_url

        try:
            logger.debug(f"Processing URL: {original_url}")
            slug = generate_slug()
            logger.debug(f"Generated slug: {slug}")

            trusted_hops = [
                "https://www.google.com/search?q=tech",
                "https://www.linkedin.com",
                "https://medium.com"
            ]
            # Encode URL and hops into slug
            encoded_data = encode_url_data(original_url, trusted_hops)

            short_link = f"{request.url_root}{slug}"
            logger.debug(f"Generated short link: {short_link}")
            return render_template("index.html", short_link=short_link, encoded_data=encoded_data, error=None)
        except Exception as e:
            logger.error(f"Error in POST /: {str(e)}")
            error = "Something went wrong. Try again."

    return render_template("index.html", short_link=None, encoded_data=None, error=error)

@app.route("/<slug>")
def cloak_redirect(slug):
    # In real app, we'd decode slug here, but for simplicity, expect encoded_data in session/query
    encoded_data = request.args.get("data")
    if not encoded_data:
        return render_template("error.html", message="Invalid Link")

    link_data = decode_url_data(encoded_data)
    if not link_data:
        return render_template("error.html", message="Invalid Link")

    token = generate_slug(10)  # Longer token for uniqueness
    tokens[token] = {
        "link_data": link_data,
        "current_hop": 0,
        "expires": time.time() + 15
    }

    return redirect(f"/r/{token}", code=302)

@app.route("/r/<token>")
def process_redirect(token):
    token_data = tokens.get(token)
    if not token_data or token_data["expires"] < time.time():
        return render_template("error.html", message="Link Expired")

    link_data = token_data["link_data"]
    current_hop = token_data["current_hop"]
    hops = link_data["hops"]
    final_url = link_data["url"]

    if current_hop < len(hops):
        token_data["current_hop"] += 1
        tokens[token] = token_data

        next_hop = hops[current_hop]
        next_redirect = f"/r/{token}"
        return render_template("redirect.html", hop_url=next_hop, next_url=next_redirect, final_url=final_url)
    else:
        del tokens[token]
        return redirect(final_url, code=302)

# In-memory tokens (temporary, reset on restart)
tokens = {}

if __name__ == "__main__":
    app.run(debug=True)