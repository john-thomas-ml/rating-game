import sys
import logging
from flask import Flask, render_template, request, jsonify, make_response, session
from pymongo import MongoClient, errors
from bson import ObjectId, binary
from time import sleep
import uuid
import mimetypes

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize MongoDB client as None to create in each worker
mongo_client = None

def get_mongo_client(uri, retries=5, delay=2):
    global mongo_client
    if mongo_client is None:
        for attempt in range(1, retries + 1):
            try:
                client = MongoClient(uri, serverSelectionTimeoutMS=5000)
                client.admin.command('ping')
                logging.info("Connected to MongoDB successfully.")
                mongo_client = client
                return client
            except errors.ConnectionFailure as e:
                logging.warning(f"MongoDB connection failed on attempt {attempt}: {e}. Retrying in {delay} seconds...")
                sleep(delay)
        logging.error("Failed to connect to MongoDB after multiple attempts.")
        raise errors.ConnectionFailure("Could not connect to MongoDB.")
    return mongo_client

def get_db():
    client = get_mongo_client("mongodb+srv://22cs260:apple@rate.ycl6p.mongodb.net/?retryWrites=true&w=majority&appName=Rate")
    return client["rating_game_db"]

def format_image(image, is_rated=False):
    return {
        "id": str(image["_id"]),
        "name": image["name"],
        "rating": image.get("rating", 0),
        "rating_count": image.get("rating_count", 0),
        "isRated": is_rated
    }

def get_or_create_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

@app.route('/')
def index():
    try:
        db = get_db()
        images_collection = db["images"]
        image = images_collection.find_one()
        top_rated_images = list(images_collection.find().sort("rating", -1).limit(10))
        
        return render_template("index.html", image=image, top_rated_images=top_rated_images, no_images=not bool(image))
    except Exception as e:
        logging.error(f"Error fetching images for index page: {e}")
        return render_template("index.html", error="Unable to load images at the moment.", no_images=True)

@app.route('/top-rated', methods=['GET'])
def get_top_rated():
    try:
        db = get_db()
        images_collection = db["images"]
        top_images = list(images_collection.find().sort("rating", -1).limit(10))
        if not top_images:
            return jsonify([]) 
        formatted_images = [format_image(img) for img in top_images]
        return jsonify(formatted_images)
    except Exception as e:
        logging.error(f"Error fetching top-rated images: {e}")
        return jsonify({"error": "Failed to fetch top-rated images"}), 500

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        db = get_db()
        images_collection = db["images"]
        image_name = request.form.get('imageName')
        image_file = request.files.get('imageFile')

        if not image_name or not image_file:
            logging.warning("Image upload failed: Missing image name or file.")
            return jsonify({"error": "Image name and file are required"}), 400

        # Ensure the file is stored as binary data
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

@app.route('/rate', methods=['POST'])
def rate_image():
    data = request.json
    image_id = data.get('image_id')
    rating = data.get('rating')
    session_id = get_or_create_session_id()

    if image_id is None or rating is None:
        logging.warning("Rating failed: Missing image ID or rating.")
        return jsonify({"error": "Image ID and rating are required"}), 400

    try:
        db = get_db()
        images_collection = db["images"]
        user_ratings_collection = db["user_ratings"]
        
        image = images_collection.find_one({"_id": ObjectId(image_id)})
        if image:
            new_rating_count = image["rating_count"] + 1
            new_total_rating = image["rating"] * image["rating_count"] + rating
            new_average_rating = new_total_rating / new_rating_count
            
            images_collection.update_one(
                {"_id": ObjectId(image_id)},
                {"$set": {"rating": new_average_rating, "rating_count": new_rating_count}}
            )
            
            user_ratings_collection.update_one(
                {"session_id": session_id},
                {"$addToSet": {"rated_images": ObjectId(image_id)}},
                upsert=True
            )

            logging.info(f"User with session ID '{session_id}' rated image ID '{image_id}' successfully with rating {rating}.")
            return jsonify({"message": "Rating submitted successfully!"})
        
        logging.warning(f"Rating failed: Image with ID '{image_id}' not found.")
        return jsonify({"error": "Image not found"}), 404
    except Exception as e:
        logging.error(f"Error rating image: {e}")
        return jsonify({"error": "Failed to submit rating"}), 500

@app.route('/all-ratings')
def all_ratings():
    try:
        db = get_db()
        images_collection = db["images"]
        all_images = images_collection.find().sort("rating", -1)
        formatted_images = [format_image(img) for img in all_images]
        return render_template("all_ratings.html", images=formatted_images)
    except Exception as e:
        logging.error(f"Error fetching all ratings: {e}")
        return render_template("all_ratings.html", error="Unable to load ratings at the moment.")

@app.route('/image/<image_id>')
def serve_image(image_id):
    try:
        db = get_db()
        images_collection = db["images"]
        image = images_collection.find_one({"_id": ObjectId(image_id)})
        if image and 'image_data' in image:
            image_data = image["image_data"]
            mime_type, _ = mimetypes.guess_type(image["name"])
            if not mime_type:
                mime_type = 'image/jpeg'  # Default to JPEG if unknown

            response = make_response(image_data)
            response.headers.set('Content-Type', mime_type)
            return response
        logging.warning(f"Image with ID '{image_id}' not found.")
    except Exception as e:
        logging.error(f"Error in serve_image: {e}")
    return "Image not found", 404

@app.route('/unrated-images', methods=['GET'])
def get_unrated_images():
    session_id = get_or_create_session_id()
    try:
        db = get_db()
        images_collection = db["images"]
        user_ratings_collection = db["user_ratings"]
        
        rated_images_doc = user_ratings_collection.find_one({"session_id": session_id})
        rated_image_ids = rated_images_doc["rated_images"] if rated_images_doc else []

        all_images = images_collection.find()
        images_list = []

        for image in all_images:
            is_rated = image["_id"] in rated_image_ids
            images_list.append(format_image(image, is_rated))

        return jsonify(images_list)
    except Exception as e:
        logging.error(f"Error fetching unrated images: {e}")
        return jsonify({"error": "Failed to fetch unrated images"}), 500

if __name__ == '__main__':
    app.run(debug=True)