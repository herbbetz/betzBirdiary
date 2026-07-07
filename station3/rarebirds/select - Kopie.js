document.addEventListener("DOMContentLoaded", () => {
  const input = document.querySelector(".dropdown-input");
  const list = document.querySelector(".dropdown-list");
  const hiddenInput = document.getElementById("selected-station-id");

  // --- 1. Populate Dropdown dynamically from stations.js ---
  // stationData format looks like: [{"Station Name": "ID"}, ...]
  if (typeof stationData !== "undefined" && Array.isArray(stationData)) {
    stationData.forEach(stationObj => {
      const stationName = Object.keys(stationObj)[0];
      const stationId = stationObj[stationName];

      const itemDiv = document.createElement("div");
      itemDiv.classList.add("dropdown-item");
      itemDiv.textContent = stationName;
      // Store the station ID inside a data-attribute for later use
      itemDiv.setAttribute("data-id", stationId); 

      list.appendChild(itemDiv);
    });
  }

  const items = document.querySelectorAll(".dropdown-item");

  // --- 2. Show dropdown on focus ---
  input.addEventListener("focus", () => {
    list.style.display = "block";
  });

  // --- 3. Filter items matching user search text ---
  input.addEventListener("input", () => {
    const searchText = input.value.toLowerCase();
    let visibleCount = 0;

    items.forEach(item => {
      const text = item.textContent.toLowerCase();
      if (text.includes(searchText)) {
        item.style.display = "block";
        visibleCount++;
      } else {
        item.style.display = "none";
      }
    });

    // Hide dropdown frame entirely if no items match
    list.style.display = visibleCount > 0 ? "block" : "none";
  });

  // --- 4. Handle item selection ---
  list.addEventListener("click", (event) => {
    const targetItem = event.target.closest(".dropdown-item");
    if (targetItem) {
      const selectedName = targetItem.textContent;
      const selectedId = targetItem.getAttribute("data-id");

      input.value = selectedName;          // Put name in the search box
      hiddenInput.value = selectedId;      // Store ID securely
      list.style.display = "none";         // Close menu

      // Diagnostic printout to verify your keys match perfectly
      console.log(`Selected Station: ${selectedName} (ID: ${selectedId})`);
    }
  });

  // --- 5. Close dropdown if clicked completely outside ---
  document.addEventListener("click", (event) => {
    if (!input.contains(event.target) && !list.contains(event.target)) {
      list.style.display = "none";
    }
  });
});
// --- 6. Validate on Form Submit ---
const form = document.querySelector("form");
form.addEventListener("submit", (event) => {
  // If the hidden input has no value, the user didn't click an option
  if (!hiddenInput.value) {
    event.preventDefault(); // Stop the form from submitting
    alert("Please select a valid station from the dropdown list.");
    input.focus();
  }
});