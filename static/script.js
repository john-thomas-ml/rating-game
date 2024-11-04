let images = [];
let currentIndex = 0;

document.addEventListener("DOMContentLoaded", () => {
  fetchUnratedImages();
});

function loadCurrentImage() {
  const imageTitle = document.getElementById("imageTitle");
  const mainImage = document.getElementById("mainImage");
  const ratingMessage = document.getElementById("ratingMessage");

  if (!imageTitle || !mainImage || !ratingMessage) {
    console.error("Required elements with IDs 'imageTitle', 'mainImage', or 'ratingMessage' are missing in the HTML.");
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
}

function fetchUnratedImages() {
  fetch('/unrated-images')
    .then(response => {
      if (!response.ok) throw new Error('Network response was not ok');
      return response.json();
    })
    .then(data => {
      images = data;
      currentIndex = 0;
      loadCurrentImage();
      fetchTopRatedImages(); 
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
  .then(response => {
    if (!response.ok) throw new Error('Failed to submit rating');
    return response.json();
  })
  .then(data => {
    if (data.message) {
      document.getElementById("ratingMessage").textContent = `You rated ${rating} for ${currentImage.name}`;
      
      images.splice(currentIndex, 1);

      if (images.length === 0) {
        document.getElementById("ratingMessage").textContent = "You've rated all available images!";
      } else {
        if (currentIndex >= images.length) {
          currentIndex = 0; 
        }
        loadCurrentImage();
      }

      fetchTopRatedImages();
    } else {
      console.error(data.error);
      document.getElementById("ratingMessage").textContent = "Error: " + data.error;
    }
  })
  .catch(error => console.error('Error submitting rating:', error));
}

function fetchTopRatedImages() {
  fetch('/top-rated')
    .then(response => {
      if (!response.ok) throw new Error('Network response was not ok');
      return response.json();
    })
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

  fetch('/upload', {
    method: 'POST',
    body: formData
  })
  .then(response => {
    if (!response.ok) throw new Error('Failed to upload image');
    return response.json();
  })
  .then(data => {
    if (data.message) {
      document.getElementById("uploadMessage").textContent = "Image uploaded successfully!";
      fetchUnratedImages();
    } else {
      document.getElementById("uploadMessage").textContent = data.error;
    }
  })
  .catch(error => {
    console.error('Error uploading image:', error);
    document.getElementById("uploadMessage").textContent = "Error: Failed to upload image.";
  });
});
