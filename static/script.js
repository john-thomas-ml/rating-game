// Array to hold images loaded from the backend
let images = [];
let currentIndex = 0;

// Load images on page load
document.addEventListener("DOMContentLoaded", () => {
  fetchTopRatedImages();
  loadCurrentImage();
});

// Function to load the current image
function loadCurrentImage() {
  if (images.length === 0) return;
  const currentImage = images[currentIndex];
  document.getElementById("imageTitle").textContent = currentImage.name;
  document.getElementById("mainImage").src = `/image/${currentImage.id}`;
}

// Fetch top-rated images from the backend
function fetchTopRatedImages() {
  fetch('/top-rated')
    .then(response => response.json())
    .then(data => {
      images = data;
      updateRankingList();
      loadCurrentImage();
    })
    .catch(error => console.error('Error fetching top-rated images:', error));
}

// Function to submit a rating
function rateImage(rating) {
  const currentImage = images[currentIndex];
  fetch('/rate', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json'
      },
      body: JSON.stringify({ image_id: currentImage.id, rating: rating })
  })
  .then(response => response.json())
  .then(data => {
      if (data.message) {
          document.getElementById("ratingMessage").textContent = `You rated ${rating} for ${currentImage.name}`;
          
          // Move to the next image
          currentIndex = (currentIndex + 1) % images.length; // Loop back to start if at the end
          loadCurrentImage(); // Load the new current image
          
          // Optionally refresh the top-rated images if needed
          fetchTopRatedImages();
      } else {
          console.error(data.error);
      }
  })
  .catch(error => console.error('Error submitting rating:', error));
}

// Update ranking list in the side panel
function updateRankingList() {
  const rankingList = document.getElementById("rankingList");
  rankingList.innerHTML = ""; // Clear previous list

  images.forEach(image => {
    const listItem = document.createElement("li");
    listItem.innerHTML = `<img src="/image/${image.id}" alt="${image.name}" class="thumbnail" /> ${image.name} - ${image.rating.toFixed(1)}`;
    rankingList.appendChild(listItem);
  });
}

// Form submission for uploading images
document.getElementById("uploadForm").addEventListener("submit", function (e) {
  e.preventDefault();
  const formData = new FormData(this);

  fetch('/upload', {
      method: 'POST',
      body: formData
  })
  .then(response => response.json())
  .then(data => {
      if (data.message) {
          document.getElementById("uploadMessage").textContent = "Image uploaded successfully!";
          fetchTopRatedImages(); // Refresh the top-rated images
      } else {
          document.getElementById("uploadMessage").textContent = data.error;
      }
  })
  .catch(error => console.error('Error uploading image:', error));
});
