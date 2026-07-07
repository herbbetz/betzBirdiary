document.addEventListener("DOMContentLoaded", () => {
  const input = document.querySelector(".dropdown-input");
  const list = document.querySelector(".dropdown-list");
  const hiddenInput = document.getElementById("selected-station-id");
  const form = document.querySelector("form");

  // --- 1. Populate Dropdown dynamically ---
  if (typeof stationData !== "undefined" && Array.isArray(stationData)) {
    stationData.forEach(stationObj => {
      const stationName = Object.keys(stationObj)[0];
      const stationId = stationObj[stationName];

      const itemDiv = document.createElement("div");
      itemDiv.classList.add("dropdown-item");
      itemDiv.textContent = stationName;
      itemDiv.setAttribute("data-id", stationId); 

      list.appendChild(itemDiv);
    });
  }

  // --- 2. Show dropdown on focus ---
  input.addEventListener("focus", () => {
    list.style.display = "block";
    input.classList.remove("input-error"); // Clear error styling on focus
  });

  // --- 3. Filter items and Handle Manual Typing ---
  input.addEventListener("input", () => {
    const searchText = input.value.trim();
    const lowerSearchText = searchText.toLowerCase();
    
    const items = list.querySelectorAll(".dropdown-item");
    let visibleCount = 0;
    let exactMatchFound = false;

    items.forEach(item => {
      const text = item.textContent;
      const lowerText = text.toLowerCase();
      
      if (lowerText.includes(lowerSearchText)) {
        item.style.display = "block";
        visibleCount++;
      } else {
        item.style.display = "none";
      }

      // If user types a perfect match manually, auto-assign the ID
      if (lowerText === lowerSearchText) {
        hiddenInput.value = item.getAttribute("data-id");
        exactMatchFound = true;
        console.log(`[Manual Match] Station: ${text} (ID: ${hiddenInput.value})`);
      }
    });

    if (!exactMatchFound) {
      hiddenInput.value = "";
    }

    list.style.display = visibleCount > 0 ? "block" : "none";
  });

  // --- 4. Handle item selection via click ---
  list.addEventListener("click", (event) => {
    const targetItem = event.target.closest(".dropdown-item");
    if (targetItem) {
      const selectedName = targetItem.textContent;
      const selectedId = targetItem.getAttribute("data-id");

      input.value = selectedName;
      hiddenInput.value = selectedId;
      list.style.display = "none";
      input.classList.remove("input-error");

      // Restored diagnostic printout
      console.log(`[Click Selection] Station: ${selectedName} (ID: ${selectedId})`);
    }
  });

  // --- 5. UI Enforcement & Event Tracking ---
  document.addEventListener("click", (event) => {
    // Check what specific HTML element the user just clicked on
    const clickedElement = event.target;

    if (!input.contains(clickedElement) && !list.contains(clickedElement)) {
      list.style.display = "none";
      
      // Instead of deleting text, we flag it in console and visually highlight it
      if (input.value.trim() !== "" && !hiddenInput.value) {
        console.warn(
          `[Validation Warning] User clicked on <${clickedElement.tagName.toLowerCase()}> ` +
          `class="${clickedElement.className}". Input text "${input.value}" preserved, ` +
          `but station_id is missing!`
        );
        input.classList.add("input-error"); // Highlight field in red instead of clearing
      }
    }
  });

  // --- 6. Form Submission Guard ---
  form.addEventListener("submit", (event) => {
    if (!hiddenInput.value) {
      event.preventDefault(); 
      input.classList.add("input-error");
      alert("Please select a valid station from the dropdown menu before submitting.");
    } else {
      console.log(`[Form Submitting] Payload -> station_name: ${input.value}, station_id: ${hiddenInput.value}`);
      
      // FORCE HARD OVERRIDE: Manually change the window location.
      // This forces Chrome to explicitly register and lock the query string parameters in history.
      event.preventDefault(); 
      window.location.href = `${form.action}?station_name=${encodeURIComponent(input.value)}&station_id=${encodeURIComponent(hiddenInput.value)}`;
    }
  });
});