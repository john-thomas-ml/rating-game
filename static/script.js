let images = [];
let currentIndex = 0;

document.addEventListener("DOMContentLoaded", () => {
  fetchUnratedImages();
  fetchTopRatedImages();  // Load top-rated images initially
});

function loadCurrentImage() {
  const imageTitle = document.getElementById("imageTitle");
  const mainImage = document.getElementById("mainImage");
  const ratingMessage = document.getElementById("ratingMessage");
  const ratingButtons = document.querySelectorAll(".rating-buttons button:not(.skip-button)");

  if (!imageTitle || !mainImage || !ratingMessage) {
    console.error("Required elements are missing in the HTML.");
    return;
  }

  if (images.length === 0) {
    imageTitle.textContent = "No images available";
    mainImage.style.display = "none";
    ratingMessage.textContent = "You've rated all available images!";
    return;
  }

  const currentImage = images[currentIndex];
  imageTitle.textContent = currentImage.name;
  mainImage.style.display = "block";
  mainImage.src = `/image/${currentImage.id}`;
  mainImage.setAttribute("data-image-id", currentImage.id); // Ensure ID is updated correctly

  if (currentImage.isRated) {
    ratingMessage.textContent = "You already rated this image!";
    ratingButtons.forEach(button => button.disabled = true);
  } else {
    ratingMessage.textContent = "";
    ratingButtons.forEach(button => button.disabled = false);
  }
}

function fetchUnratedImages() {
  fetch('/unrated-images')
    .then(response => response.json())
    .then(data => {
      images = data;
      currentIndex = 0;
      loadCurrentImage();
    })
    .catch(error => console.error('Error fetching unrated images:', error));
}

function rateImage(rating) {
  if (images.length === 0) {
    document.getElementById("ratingMessage").textContent = "No images available to rate.";
    return;
  }

  const currentImage = images[currentIndex];
  fetch('/rate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_id: currentImage.id, rating: rating })
  })
  .then(response => response.json())
  .then(data => {
    if (data.message) {
      document.getElementById("ratingMessage").textContent = `You rated this image a ${rating}.`;
      images[currentIndex].isRated = true;

      // Move to the next image after rating
      currentIndex = (currentIndex + 1) % images.length;
      loadCurrentImage();
      fetchTopRatedImages();  // Refresh top-rated images
    } else {
      document.getElementById("ratingMessage").textContent = data.error;
    }
  })
  .catch(error => console.error('Error submitting rating:', error));
}

function skipImage() {
  if (images.length === 0) {
    document.getElementById("ratingMessage").textContent = "No images available to skip.";
    return;
  }

  // Move to the next image after skipping
  currentIndex = (currentIndex + 1) % images.length;
  loadCurrentImage();
}

function deleteImage() {
  if (images.length === 0) {
    document.getElementById("deleteMessage").textContent = "No images available to delete.";
    return;
  }

  const password = document.getElementById("deletePassword").value;
  const mainImage = document.getElementById("mainImage");
  const imageId = mainImage.getAttribute('data-image-id'); // Ensure the current image ID is fetched directly

  // Log the image ID being sent for deletion
  console.log(`Deleting current image with ID: ${imageId}`);

  fetch('/delete-image', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_id: imageId, password: password })
  })
  .then(response => response.json())
  .then(data => {
    const deleteMessage = document.getElementById('deleteMessage');
    if (data.message) {
      deleteMessage.textContent = data.message;
      deleteMessage.style.color = 'green';

      // Remove the deleted image from the array and adjust currentIndex
      images = images.filter(image => image.id !== imageId);
      
      // Reset currentIndex if it exceeds the length of images array
      if (currentIndex >= images.length) {
        currentIndex = 0;
      }

      loadCurrentImage();
      fetchTopRatedImages();  // Refresh top-rated images after deletion
    } else {
      deleteMessage.textContent = data.error || 'Failed to delete image';
      deleteMessage.style.color = 'red';
    }
  })
  .catch(error => {
    console.error('Error deleting image:', error);
    document.getElementById("deleteMessage").textContent = "Error: Failed to delete image.";
    document.getElementById("deleteMessage").style.color = 'red';
  });
}

function fetchTopRatedImages() {
  fetch('/top-rated?limit=5')  // Fetch only top 5 images
    .then(response => response.json())
    .then(data => {
      updateRankingList(data);
    })
    .catch(error => console.error('Error fetching top-rated images:', error));
}

function updateRankingList(imagesList = []) {
  const rankingList = document.getElementById("rankingList");
  rankingList.innerHTML = "";

  if (imagesList.length === 0) {
    const listItem = document.createElement("li");
    listItem.textContent = "No top-rated images available.";
    rankingList.appendChild(listItem);
    return;
  }

  imagesList.forEach(image => {
    const listItem = document.createElement("li");
    listItem.innerHTML = `<img src="/image/${image.id}" alt="${image.name}" class="thumbnail" /> ${image.name} - ${image.rating.toFixed(1)}`;
    rankingList.appendChild(listItem);
  });
}

document.getElementById("uploadForm").addEventListener("submit", function (e) {
  e.preventDefault();
  const formData = new FormData(this);
  const uploadButton = document.querySelector("#uploadForm button[type='submit']");
  const uploadMessage = document.getElementById("uploadMessage");

  uploadButton.disabled = true;
  uploadMessage.textContent = "Uploading...";

  fetch('/upload', {
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    if (data.message) {
      uploadMessage.textContent = "Image uploaded successfully!";
      setTimeout(() => {
        uploadButton.disabled = false;
        uploadMessage.textContent = "";
      }, 60000);

      fetchUnratedImages();
      fetchTopRatedImages();  // Update top-rated images after uploading new image
    } else {
      uploadMessage.textContent = data.error;
      uploadButton.disabled = false;
    }
  })
  .catch(error => {
    console.error('Error uploading image:', error);
    uploadMessage.textContent = "Error: Failed to upload image.";
    uploadButton.disabled = false;
  });
});
