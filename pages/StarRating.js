class StarRatingComponent {
  constructor({ initialRating = null, callback = ()=>{} }) {
    this.maxRating = 10;
    this.rating = initialRating;
    this.containers = [];
    this.callback = callback;
  }

  issueNewHtmlComponent(params) {
    const starRatingHTMLContainer = new StarRatingHTMLContainer(this, params);
    this.containers.push(starRatingHTMLContainer);

    return starRatingHTMLContainer.container;
  }

  updateAllContainers() {
    this.containers.forEach(container => container.updateDisplay());
  }
}

class StarRatingHTMLContainer {
  constructor(starRatingObject, {containerType = 'div', size = 3, isActive = false, showPassiveAsNumber = true}) {
    this.starRatingObject = starRatingObject;
    this.isActive = isActive;
    this.showPassiveAsNumber = showPassiveAsNumber;
    this.symbolsList = [];
    this.container = document.createElement(containerType);
    
    this.container.classList.add(`is-size-${size.toString()}`);
    this.container.classList.add('is-gapless');
    this.container.classList.add('has-text-centered');
    this.container.classList.add('is-unselectable');
  
    this.updateDisplay();
  }

  generateStarDisplay() {
    const starRatingObject = this.starRatingObject;

    // Add the initial symbol based on the rating
    const initialSymbol = document.createElement('span');
    initialSymbol.textContent = starRatingObject.rating === null ? '◦' : '•';
    this.container.appendChild(initialSymbol);
    this.symbolsList.push(initialSymbol);
  
    // Create each star element
    for (let i = 1; i <= starRatingObject.maxRating; i++) {
      const star = document.createElement('span');
      star.textContent = i <= starRatingObject.rating ? '★' : '☆';
      star.classList.add('star');
  
      this.container.appendChild(star);
      this.symbolsList.push(star);
    }

    if (this.isActive) {
      for (let i = 0; i < this.symbolsList.length; i++) {
        this.symbolsList[i].classList.add('is-clickable');

        this.symbolsList[i].addEventListener('mouseover', () => {
          this.updateDisplay(i); 
        });

        this.symbolsList[i].addEventListener('mouseout', () => {
          this.updateDisplay(); 
        });

        this.symbolsList[i].addEventListener('click', () => {
          starRatingObject.rating = i;
          starRatingObject.callback(i);
          starRatingObject.updateAllContainers();
        });
      }
    }
  }

  updateDisplay(tmpRating = null) {
    let rating = this.starRatingObject.rating;
    const maxRating = this.starRatingObject.maxRating;

    if (tmpRating != null) rating = tmpRating;

    if (!this.isActive && this.showPassiveAsNumber) {
      if (rating == null)
        this.container.innerHTML = 'Not rated yet';
      else
        this.container.innerHTML = rating.toString() + '/' + maxRating.toString();

      // Clear the symbols list in case it was previously active for some reason
      this.symbolsList = [];
    } else {
      if (this.symbolsList.length == 0) {
        this.generateStarDisplay();
      }

      this.symbolsList[0].textContent = rating === null ? '◦' : '•';
      for (let j = 1; j <= maxRating; j++) {
        this.symbolsList[j].textContent = j <= rating ? '★' : '☆';
      }
    }
  }
}

export default StarRatingComponent;



/*
class StarRatingHTMLContainer {
  constructor(starRatingObject, { containerType = 'div', size = 3, isActive = false, showPassiveAsNumber = true } = {}) {
    this.starRatingObject = starRatingObject;
    this.isActive = isActive;
    this.showPassiveAsNumber = showPassiveAsNumber;
    this.container = document.createElement(containerType);

    // Numeric indicator element
    this.indicator = document.createElement('span');
    this.container.appendChild(this.indicator);
    // Container for stars
    this.starsWrapper = document.createElement('span');
    this.container.appendChild(this.starsWrapper);

    // Basic styling
    this.container.style.userSelect = 'none';
    this.starsWrapper.style.display = 'inline-block';

    // Create star elements (noninteractive here)
    this.generateStarDisplay(size);

    // Only one set of event handlers on the parent container:
    if (this.isActive) {
      this.starsWrapper.addEventListener('mousemove', (e) => {
        const rect = this.starsWrapper.getBoundingClientRect();
        // Compute overall rating = fraction across total width times maxRating
        let fractionOverall = (e.clientX - rect.left) / rect.width;
        fractionOverall = Math.min(Math.max(fractionOverall, 0), 1);
        const previewRating = fractionOverall * this.starRatingObject.maxRating;
        this.updateDisplay(previewRating);
      });
      this.starsWrapper.addEventListener('click', (e) => {
        const rect = this.starsWrapper.getBoundingClientRect();
        let fractionOverall = (e.clientX - rect.left) / rect.width;
        fractionOverall = Math.min(Math.max(fractionOverall, 0), 1);
        const newRating = fractionOverall * this.starRatingObject.maxRating;
        this.starRatingObject.rating = newRating;
        this.starRatingObject.callback(newRating);
        this.starRatingObject.updateAllContainers();
      });
      this.starsWrapper.addEventListener('mouseleave', () => {
        this.updateDisplay();
      });
    }
  }

  generateStarDisplay(size) {
    this.starElements = [];
    for (let i = 1; i <= this.starRatingObject.maxRating; i++) {
      const starContainer = document.createElement('span');
      starContainer.classList.add('star-container');
      starContainer.style.position = 'relative';
      starContainer.style.display = 'inline-block';
      starContainer.style.fontSize = size + 'rem';
      starContainer.style.lineHeight = '1';
      starContainer.style.margin = '0 1px';

      // Empty star layer
      const emptyStar = document.createElement('span');
      emptyStar.classList.add('star-empty');
      emptyStar.textContent = '☆';

      // Filled star overlay
      const filledStar = document.createElement('span');
      filledStar.classList.add('star-filled');
      filledStar.textContent = '★';
      filledStar.style.position = 'absolute';
      filledStar.style.top = '0';
      filledStar.style.left = '0';
      filledStar.style.overflow = 'hidden';
      filledStar.style.width = '0%';
      filledStar.style.pointerEvents = 'none';

      starContainer.appendChild(emptyStar);
      starContainer.appendChild(filledStar);
      this.starsWrapper.appendChild(starContainer);
      this.starElements.push(starContainer);
    }
  }

  updateDisplay(previewRating = null) {
    // Use previewRating if provided, else the actual rating
    let rating = previewRating == null ? this.starRatingObject.rating : previewRating;

    // For noninteractive mode, show numeric text only.
    if (!this.isActive && this.showPassiveAsNumber) {
      this.container.innerHTML =
        rating == null
          ? 'Not rated yet'
          : rating.toFixed(1) + '/' + this.starRatingObject.maxRating.toString();
      return;
    }

    // Optionally update an indicator. Here we simply use it to show a bullet if set.
    this.indicator.textContent = rating === null ? '◦' : '•';

    // Update each star fill based on its index.
    for (let j = 0; j < this.starElements.length; j++) {
      const starContainer = this.starElements[j];
      const filledStar = starContainer.querySelector('.star-filled');
      let starValue = rating - j;
      if (starValue < 0) starValue = 0;
      if (starValue > 1) starValue = 1;
      filledStar.style.width = (starValue * 100).toFixed(0) + '%';
    }
  }
}
*/