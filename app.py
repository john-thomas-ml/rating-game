import sys
import logging
from flask import Flask, render_template, request, jsonify, make_response, session
from pymongo import MongoClient, errors, DESCENDING
from bson import ObjectId
from gridfs import GridFS
from time import sleep
import uuid
import mimetypes

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

PASSWORD = 'hate'  # Set your secure password here for deletion

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_mongo_client(uri, retries=5, delay=2):
    for attempt in range(1, retries + 1):
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            logging.info("Connected to MongoDB successfully.")
            return client
        except errors.ConnectionFailure as e:
            logging.warning(f"MongoDB connection failed on attempt {attempt}: {e}. Retrying in {delay} seconds...")
            sleep(delay)
    logging.error("Failed to connect to MongoDB after multiple attempts.")
    raise errors.ConnectionFailure("Could not connect to MongoDB.")

# Initialize MongoDB connection and GridFS
client = get_mongo_client("mongodb+srv://22cs260:apple@rate.ycl6p.mongodb.net/?retryWrites=true&w=majority&appName=Rate")
db = client["rating_game_db"]
images_collection = db["images"]
user_ratings_collection = db["user_ratings"]
fs = GridFS(db)

# Index frequently queried fields for better performance
images_collection.create_index([("rating", DESCENDING)])

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

# Updated to limit top-rated images to 5 only
@app.route('/')
def index():
    try:
        top_rated_images = list(images_collection.find().sort("rating", -1).limit(5))  # Limit to 5 images here
        image = top_rated_images[0] if top_rated_images else None
        return render_template("index.html", image=image, top_rated_images=top_rated_images)
    except Exception as e:
        logging.error(f"Error fetching images for index page: {e}")
        return render_template("index.html", error="Unable to load images at the moment.", image=None)

# Adjusted to consistently fetch only the top 5 rated images
@app.route('/top-rated', methods=['GET'])
def get_top_rated():
    try:
        top_images = list(images_collection.find().sort("rating", -1).limit(5))  # Limit to 5 images here as well
        formatted_images = [format_image(img) for img in top_images]
        return jsonify(formatted_images)
    except Exception as e:
        logging.error(f"Error fetching top-rated images: {e}")
        return jsonify({"error": "Failed to fetch top-rated images"}), 500

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        image_name = request.form.get('imageName')
        image_file = request.files.get('imageFile')

        if not image_name or not image_file:
            logging.warning("Image upload failed: Missing image name or file.")
            return jsonify({"error": "Image name and file are required"}), 400

        image_id = fs.put(image_file, filename=image_name)
        image_doc = {
            "name": image_name,
            "image_file_id": image_id,
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

@app.route('/delete-image', methods=['POST'])
def delete_image():
    data = request.json
    image_id = data.get('image_id')
    password = data.get('password')

    if password != PASSWORD:
        return jsonify({"error": "Incorrect password"}), 403

    try:
        image = images_collection.find_one({"_id": ObjectId(image_id)})
        if not image:
            return jsonify({"error": "Image not found"}), 404

        # Delete the image file from GridFS
        if 'image_file_id' in image:
            fs.delete(image["image_file_id"])

        # Remove the image document from the `images` collection
        images_collection.delete_one({"_id": ObjectId(image_id)})

        # Remove references from the `user_ratings_collection`
        user_ratings_collection.update_many(
            {},
            {"$pull": {"rated_images": ObjectId(image_id)}}
        )

        return jsonify({"message": "Image deleted successfully"})
    except Exception as e:
        logging.error(f"Error deleting image: {e}")
        return jsonify({"error": "Failed to delete image"}), 500

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
        if image and 'image_file_id' in image:
            image_data = fs.get(image["image_file_id"]).read()
            mime_type, _ = mimetypes.guess_type(image["name"])
            if not mime_type:
                mime_type = 'image/jpeg'
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
    rated_images_doc = user_ratings_collection.find_one({"session_id": session_id})
    rated_image_ids = rated_images_doc["rated_images"] if rated_images_doc else []

    # Pagination parameters
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    skip = (page - 1) * limit

    all_images = images_collection.find().skip(skip).limit(limit)
    images_list = [format_image(image, image["_id"] in rated_image_ids) for image in all_images]

    return jsonify(images_list)

if __name__ == '__main__':
    app.run(debug=True)
