import sys
from flask import Flask, render_template, request, jsonify, make_response
from pymongo import MongoClient
from bson import ObjectId, binary
from io import BytesIO

app = Flask(__name__)

client = MongoClient("mongodb+srv://22cs260:apple@rate.ycl6p.mongodb.net/?retryWrites=true&w=majority&appName=Rate")
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
    image = images_collection.find_one()
    top_rated_images = list(images_collection.find().sort("rating", -1).limit(10))
    
    if image:
        return render_template("index.html", image=image, top_rated_images=top_rated_images)
    else:
        return render_template("index.html", no_images=True, top_rated_images=top_rated_images)

@app.route('/upload', methods=['POST'])
def upload_image():
    image_name = request.form.get('imageName')
    image_file = request.files.get('imageFile')

    image_data = binary.Binary(image_file.read())

    image_doc = {
        "name": image_name,
        "image_data": image_data,
        "rating": 0,
        "rating_count": 0
    }
    images_collection.insert_one(image_doc)

    return jsonify({"message": "Image uploaded successfully!"})

@app.route('/top-rated', methods=['GET'])
def get_top_rated():
    top_images = images_collection.find().sort("rating", -1).limit(10)
    formatted_images = [format_image(img) for img in top_images]
    return jsonify(formatted_images)

@app.route('/rate', methods=['POST'])
def rate_image():
    data = request.json
    image_id = data['image_id']
    rating = data['rating']
    
    image = images_collection.find_one({"_id": ObjectId(image_id)})
    if image:
        new_rating_count = image["rating_count"] + 1
        new_total_rating = image["rating"] * image["rating_count"] + rating
        new_average_rating = new_total_rating / new_rating_count
        
        images_collection.update_one(
            {"_id": ObjectId(image_id)},
            {"$set": {"rating": new_average_rating, "rating_count": new_rating_count}}
        )
        return jsonify({"message": "Rating submitted successfully!"})
    return jsonify({"error": "Image not found"}), 404

@app.route('/all-ratings')
def all_ratings():
    all_images = images_collection.find().sort("rating", -1)
    formatted_images = [format_image(img) for img in all_images]
    return render_template("all_ratings.html", images=formatted_images)

@app.route('/image/<image_id>')
def serve_image(image_id):
    try:
        print(f"Fetching image with ID: {image_id}")
        image = images_collection.find_one({"_id": ObjectId(image_id)})
        if image and 'image_data' in image:
            image_data = image["image_data"]
            response = make_response(image_data)
            response.headers.set('Content-Type', 'image/jpeg')
            return response
        print("Image not found or no data available")
    except Exception as e:
        print(f"Error in serve_image: {e}")
    return "Image not found", 404

if __name__ == '__main__':
    app.run(debug=True)
