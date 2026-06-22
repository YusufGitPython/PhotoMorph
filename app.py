from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from PIL import Image, ImageFilter
import cv2
import os

app = Flask(__name__)
app.secret_key = "photomorph-secret-key"

UPLOAD_FOLDER = 'static/uploads'
RESULT_FOLDER = 'static/results'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# ---------------- HELPERS ---------------- #

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------- ROUTES ---------------- #

@app.route('/')
def home():
    return render_template("index.html", uploaded_image=None)


@app.route('/upload', methods=['POST'])
def upload_image():

    if "image" not in request.files:
        flash("No image was uploaded")
        return redirect(url_for("home"))

    file = request.files["image"]

    if file.filename == "":
        flash("Please select an image.")
        return redirect(url_for("home"))

    if not allowed_file(file.filename):
        flash("Only PNG, JPG, JPEG, and WEBP files are allowed.")
        return redirect(url_for("home"))

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    theme = request.form.get("theme")
    img = Image.open(save_path)

    # ---------------- FILTERS ---------------- #

    if theme == "black white":
        img = img.convert("L")

    elif theme == "sepia":
        img = img.convert("RGB")
        pixels = img.load()

        for y in range(img.height):
            for x in range(img.width):
                r, g, b = pixels[x, y]

                tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                tb = int(0.272 * r + 0.534 * g + 0.131 * b)

                pixels[x, y] = (
                    min(255, tr),
                    min(255, tg),
                    min(255, tb)
                )

    elif theme == "pixel":
        small = img.resize((img.width // 10, img.height // 10))
        img = small.resize((img.width, img.height))

    elif theme == "sketch":
        gray = img.convert("L")
        inverted = Image.eval(gray, lambda x: 255 - x)
        blurred = inverted.filter(ImageFilter.GaussianBlur(radius=10))

        def dodge(a, b):
            return min(255, int(a * 255 / (255 - b + 1)))

        result = Image.new("L", gray.size)

        for x in range(gray.width):
            for y in range(gray.height):
                result.putpixel(
                    (x, y),
                    dodge(
                        gray.getpixel((x, y)),
                        blurred.getpixel((x, y))
                    )
                )

        img = result

    elif theme == "cartoon":
        image = cv2.imread(save_path)

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 5)

        edges = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            11,
            5
        )

        color = cv2.bilateralFilter(image, 15, 300, 300)

        cartoon = cv2.bitwise_and(color, color, mask=edges)

        result_filename = "result_" + filename
        result_path = os.path.join(app.config["RESULT_FOLDER"], result_filename)

        cv2.imwrite(result_path, cartoon)

        uploaded_image = "/" + result_path.replace("\\", "/")
        return render_template("index.html", uploaded_image=uploaded_image)

    # ---------------- SAVE (PIL FILTERS) ---------------- #

    result_filename = "result_" + filename
    result_path = os.path.join(app.config["RESULT_FOLDER"], result_filename)

    img.save(result_path)

    uploaded_image = "/" + result_path.replace("\\", "/")

    return render_template("index.html", uploaded_image=uploaded_image)


# ---------------- RUN APP ---------------- #

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(RESULT_FOLDER, exist_ok=True)
    app.run(debug=True)