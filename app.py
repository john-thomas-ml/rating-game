import sys
import logging
from flask import Flask, render_template, request, jsonify, make_response
from pymongo import MongoClient, errors
from bson import ObjectId, binary
from time import sleep

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_mongo_client(uri, retries=5, delay=2):
    for attempt in range(1, retries + 1):
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')  # Test the connection
            logging.info("Connected to MongoDB successfully.")
            return client
        except errors.ConnectionFailure as e:
            logging.warning(f"MongoDB connection failed on attempt {attempt}: {e}. Retrying in {delay} seconds...")
            sleep(delay)
    logging.error("Failed to connect to MongoDB after multiple attempts.")
    raise errors.ConnectionFailure("Could not connect to MongoDB.")

client = get_mongo_client("mongodb+srv://22cs260:apple@rate.ycl6p.mongodb.net/?retryWrites=true&w=majority&appName=Rate")
db = client["rating_game_db"]
images_collection = db["images"]

def format_image(image):
    return {
        "id": str(image["_id"]),
        "name": image["name"],
        "rating": image.get("rating", 0),
        "rating_count": image.get("rating_count", 0)
    }

@app.route('/')
def index():
    try:
        image = images_collection.find_one()
        top_rated_images = list(images_collection.find().sort("rating", -1).limit(10))
        return render_template("index.html", image=image, top_rated_images=top_rated_images, no_images=not bool(image))
    except Exception as e:
        logging.error(f"Error fetching images for index page: {e}")
        return render_template("index.html", error="Unable to load images at the moment.")

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        image_name = request.form.get('imageName')
        image_file = request.files.get('imageFile')

        if not image_name or not image_file:
            logging.warning("Image upload failed: Missing image name or file.")
            return jsonify({"error": "Image name and file are required"}), 400

        image_data = binary.Binary(image_file.read())
        image_doc = {
            "name": image_name,
            "image_data": image_data,
            "rating": 0,
            "rating_count": 0
        }
        images_collection.insert_one(image_doc)
        logging.info(f"Image '{image_name}' uploaded successfully.")
        return jsonify({"message": "Image uploaded successfully!"})
    except Exception as e:
        logging.error(f"Error uploading image: {e}")
        return jsonify({"error": "Failed to upload image"}), 500

@app.route('/top-rated', methods=['GET'])
def get_top_rated():
    try:
        top_images = images_collection.find().sort("rating", -1).limit(10)
        formatted_images = [format_image(img) for img in top_images]
        return jsonify(formatted_images)
    except Exception as e:
        logging.error(f"Error fetching top-rated images: {e}")
        return jsonify({"error": "Failed to retrieve top-rated images"}), 500

@app.route('/rate', methods=['POST'])
def rate_image():
    data = request.json
    image_id = data.get('image_id')
    rating = data.get('rating')

    if image_id is None or rating is None:
        logging.warning("Rating failed: Missing image ID or rating.")
        return jsonify({"error": "Image ID and rating are required"}), 400

    try:
        image = images_collection.find_one({"_id": ObjectId(image_id)})
        if image:
            new_rating_count = image["rating_count"] + 1
            new_total_rating = image["rating"] * image["rating_count"] + rating
            new_average_rating = new_total_rating / new_rating_count
            
            images_collection.update_one(
                {"_id": ObjectId(image_id)},
                {"$set": {"rating": new_average_rating, "rating_count": new_rating_count}}
            )
            logging.info(f"Image ID '{image_id}' rated successfully with rating {rating}.")
            return jsonify({"message": "Rating submitted successfully!"})
        logging.warning(f"Rating failed: Image with ID '{image_id}' not found.")
        return jsonify({"error": "Image not found"}), 404
    except Exception as e:
        logging.error(f"Error rating image: {e}")
        return jsonify({"error": "Failed to submit rating"}), 500

@app.route('/all-ratings')
def all_ratings():
    try:
        all_images = images_collection.find().sort("rating", -1)
        formatted_images = [format_image(img) for img in all_images]
        return render_template("all_ratings.html", images=formatted_images)
    except Exception as e:
        logging.error(f"Error fetching all ratings: {e}")
        return render_template("all_ratings.html", error="Unable to load ratings at the moment.")

@app.route('/image/<image_id>')
def serve_image(image_id):
    try:
        logging.info(f"Fetching image with ID: {image_id}")
        image = images_collection.find_one({"_id": ObjectId(image_id)})
        if image and 'image_data' in image:
            image_data = image["image_data"]
            response = make_response(image_data)
            response.headers.set('Content-Type', 'image/jpeg')
            return response
        logging.warning(f"Image with ID '{image_id}' not found.")
    except Exception as e:
        logging.error(f"Error in serve_image: {e}")
    return "Image not found", 404

if __name__ == '__main__':
    app.run(debug=True)
