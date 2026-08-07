document.addEventListener("DOMContentLoaded", () => {
  const input = document.querySelector(".dropdown-input");
  const list = document.querySelector(".dropdown-list");
  const hiddenInput = document.getElementById("selectvalue");
  const form = document.querySelector("form");

  // --- 1. Populate Dropdown dynamically for an Object ---
  if (typeof selectData !== "undefined" && selectData !== null) {
    Object.entries(selectData).forEach(([selectkey, selectvalue]) => {
      const itemDiv = document.createElement("div");
      itemDiv.classList.add("dropdown-item");
      itemDiv.textContent = selectkey;
      itemDiv.setAttribute("data-id", selectvalue); 

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
        console.log(`[Manual Match] Key: ${text} (Value: ${hiddenInput.value})`);
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
      // ✅ FIXED: Renamed variables to match usage
      const selectedKey = targetItem.textContent;
      const selectedValue = targetItem.getAttribute("data-id");

      input.value = selectedKey;
      hiddenInput.value = selectedValue;
      list.style.display = "none";
      input.classList.remove("input-error");

      console.log(`[Click Selection] Key: ${selectedKey} (Value: ${selectedValue})`);
    }
  });

  // --- 5. UI Enforcement & Event Tracking ---
  document.addEventListener("click", (event) => {
    const clickedElement = event.target;

    if (!input.contains(clickedElement) && !list.contains(clickedElement)) {
      list.style.display = "none";
      
      if (input.value.trim() !== "" && !hiddenInput.value) {
        console.warn(
          `[Validation Warning] User clicked on <${clickedElement.tagName.toLowerCase()}> ` +
          `class="${clickedElement.className}". Input text "${input.value}" preserved, ` +
          `but selectvalue is missing!`
        );
        input.classList.add("input-error");
      }
    }
  });

  // --- 6. Form Submission Guard ---
  form.addEventListener("submit", (event) => {
    if (!hiddenInput.value) {
      event.preventDefault(); 
      input.classList.add("input-error");
      alert("Please select a valid item from the dropdown menu before submitting.");
    }
    // No else block needed! The browser will naturally submit all form inputs.
  });
});