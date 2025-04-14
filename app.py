from flask import Flask, request, redirect, render_template
import random, string
import base64
import time
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def generate_slug(url):
    # Simple hash-based slug (not secure, but short for demo)
    # In production, use proper encoding or storage
    chars = string.ascii_letters + string.digits
    seed = sum(ord(c) for c in url)  # Deterministic seed
    random.seed(seed)
    slug = ''.join(random.choice(chars) for _ in range(5))
    random.seed()  # Reset seed
    return slug

@app.route("/", methods=["GET", "POST"])
def home():
    error = None
    if request.method == "POST":
        original_url = request.form["original_url"].strip()

        if not original_url.startswith(("http://", "https://")):
            original_url = "https://" + original_url

        try:
            logger.debug(f"Processing URL: {original_url}")
            slug = generate_slug(original_url)
            logger.debug(f"Generated slug: {slug}")

            # Encode URL in a compact way (base64 for simplicity, trimmed)
            encoded_url = base64.urlsafe_b64encode(original_url.encode()).decode().rstrip("=")

            short_link = f"{request.url_root}{slug}"
            logger.debug(f"Generated short link: {short_link}")
            return render_template("index.html", short_link=short_link, encoded_url=encoded_url, error=None)
        except Exception as e:
            logger.error(f"Error in POST /: {str(e)}")
            error = "Something went wrong. Try again."

    return render_template("index.html", short_link=None, encoded_url=None, error=error)

@app.route("/<slug>")
def cloak_redirect(slug):
    encoded_url = request.args.get("url")
    if not encoded_url:
        return render_template("error.html", message="Invalid Link")

    try:
        # Decode URL
        final_url = base64.urlsafe_b64decode(encoded_url + "==").decode()
    except Exception as e:
        logger.error(f"Failed to decode URL: {str(e)}")
        return render_template("error.html", message="Invalid Link")

    token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    tokens[token] = {
        "final_url": final_url,
        "current_hop": 0,
        "expires": time.time() + 15
    }

    return redirect(f"/r/{token}", code=302)

@app.route("/r/<token>")
def process_redirect(token):
    token_data = tokens.get(token)
    if not token_data or token_data["expires"] < time.time():
        return render_template("error.html", message="Link Expired")

    current_hop = token_data["current_hop"]
    final_url = token_data["final_url"]
    hops = [
        "https://www.google.com/search?q=tech",
        "https://www.linkedin.com",
        "https://medium.com"
    ]

    if current_hop < len(hops):
        token_data["current_hop"] += 1
        tokens[token] = token_data

        next_hop = hops[current_hop]
        next_redirect = f"/r/{token}"
        return render_template("redirect.html", hop_url=next_hop, next_url=next_redirect, final_url=final_url)
    else:
        del tokens[token]
        return redirect(final_url, code=302)

# In-memory tokens (reset on restart, no persistence needed)
tokens = {}

if __name__ == "__main__":
    app.run(debug=True)