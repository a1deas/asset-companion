/**
 * Asset Companion Renderer
 * Production-ready frontend with drag & drop, progress tracking, and preview
 */

// Configuration
const API_URL = window.API_URL || "http://localhost:8000";
const POLL_INTERVAL = 500; // Progress polling interval (ms)

// State
let currentFile = null;
let processing = false;
let progressInterval = null;

// DOM Elements
const elements = {
  // Input
  fileInput: document.getElementById("fileInput"),
  dropZone: document.getElementById("dropZone"),
  dropZoneOverlay: document.getElementById("dropZoneOverlay"),

  // Controls
  sizeModeSelect: document.getElementById("sizeMode"),
  targetInput: document.getElementById("target"),
  sizeMultipleSelect: document.getElementById("sizeMultiple"),
  sizeWidthInput: document.getElementById("sizeWidth"),
  sizeHeightInput: document.getElementById("sizeHeight"),
  squareSizeGroup: document.getElementById("squareSizeGroup"),
  multipleGroup: document.getElementById("multipleGroup"),
  customSizeGroup: document.getElementById("customSizeGroup"),
  autoSizeInfo: document.getElementById("autoSizeInfo"),
  kindSelect: document.getElementById("kind"),
  superresSelect: document.getElementById("superres"),
  processBtn: document.getElementById("processBtn"),
  resetBtn: document.getElementById("resetBtn"),

  // Progress
  progressSection: document.getElementById("progressSection"),
  progressFill: document.getElementById("progressFill"),
  progressStatus: document.getElementById("progressStatus"),
  progressPercent: document.getElementById("progressPercent"),

  // Preview
  previewIn: document.getElementById("previewIn"),
  previewOut: document.getElementById("previewOut"),
  inputPreview: document.getElementById("inputPreview"),
  outputPreview: document.getElementById("outputPreview"),
  inputInfo: document.getElementById("inputInfo"),
  outputInfo: document.getElementById("outputInfo"),
  downloadContainer: document.getElementById("downloadContainer"),
  downloadBtn: document.getElementById("downloadBtn"),

  // Metadata
  metadataSection: document.getElementById("metadataSection"),
  metadataContent: document.getElementById("metadataContent"),
  metadataLog: document.getElementById("metadataLog"),
  toggleMetadata: document.getElementById("toggleMetadata"),

  // Status
  statusText: document.getElementById("statusText"),
  apiStatus: document.getElementById("apiStatus"),

  // Toasts
  errorToast: document.getElementById("errorToast"),
  successToast: document.getElementById("successToast"),
  errorMessage: document.getElementById("errorMessage"),
  successMessage: document.getElementById("successMessage"),
  closeError: document.getElementById("closeError"),
  closeSuccess: document.getElementById("closeSuccess"),
};

/**
 * Initialize the application
 */
function init() {
  setupEventListeners();
  checkAPIStatus();
  handleSizeModeChange(); // Initialize size mode UI
  updateUI();
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
  // File input
  elements.fileInput.addEventListener("change", handleFileSelect);

  // Drag and drop
  elements.dropZone.addEventListener("click", () => elements.fileInput.click());
  elements.dropZone.addEventListener("dragover", handleDragOver);
  elements.dropZone.addEventListener("dragleave", handleDragLeave);
  elements.dropZone.addEventListener("drop", handleDrop);

  // Size mode change
  elements.sizeModeSelect.addEventListener("change", handleSizeModeChange);

  // Process button
  elements.processBtn.addEventListener("click", handleProcess);

  // Reset button
  elements.resetBtn.addEventListener("click", handleReset);

  // Download button
  elements.downloadBtn.addEventListener("click", handleDownload);

  // Metadata toggle
  elements.toggleMetadata.addEventListener("click", toggleMetadata);

  // Toast close buttons
  elements.closeError.addEventListener("click", () => hideToast("error"));
  elements.closeSuccess.addEventListener("click", () => hideToast("success"));

  // Input validation
  elements.targetInput.addEventListener("input", validateInputs);
  elements.sizeWidthInput?.addEventListener("input", validateInputs);
  elements.sizeHeightInput?.addEventListener("input", validateInputs);
}

/**
 * Handle size mode change
 */
function handleSizeModeChange() {
  const mode = elements.sizeModeSelect.value;

  // Hide all groups
  elements.squareSizeGroup.style.display = "none";
  elements.multipleGroup.style.display = "none";
  elements.customSizeGroup.style.display = "none";
  elements.autoSizeInfo.style.display = "none";

  // Show relevant group
  if (mode === "square") {
    elements.squareSizeGroup.style.display = "block";
  } else if (mode === "multiple") {
    elements.multipleGroup.style.display = "block";
  } else if (mode === "custom") {
    elements.customSizeGroup.style.display = "block";
  } else if (mode === "auto") {
    elements.autoSizeInfo.style.display = "block";
  }

  // Clear validation errors for fields not in use
  validateInputs();
  updateUI();
}

/**
 * Check API connection status
 */
async function checkAPIStatus() {
  try {
    const response = await fetch(`${API_URL}/docs`, { method: "HEAD" });
    if (response.ok) {
      updateAPIStatus(true);
    } else {
      updateAPIStatus(false);
    }
  } catch (error) {
    updateAPIStatus(false);
  }
}

/**
 * Update API status indicator
 */
function updateAPIStatus(connected) {
  const indicator = elements.apiStatus.querySelector(".status-indicator");
  if (connected) {
    indicator.classList.remove("disconnected");
    elements.statusText.textContent = "Ready";
  } else {
    indicator.classList.add("disconnected");
    elements.statusText.textContent = "API disconnected";
    showToast(
      "error",
      "Cannot connect to backend API. Make sure the server is running."
    );
  }
}

/**
 * Handle file selection from input
 */
function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file && file.type.startsWith("image/")) {
    loadFile(file);
  } else {
    showToast("error", "Please select a valid image file.");
  }
}

/**
 * Handle drag over event
 */
function handleDragOver(event) {
  event.preventDefault();
  event.stopPropagation();
  elements.dropZone.classList.add("drag-over");
}

/**
 * Handle drag leave event
 */
function handleDragLeave(event) {
  event.preventDefault();
  event.stopPropagation();
  elements.dropZone.classList.remove("drag-over");
}

/**
 * Handle file drop
 */
function handleDrop(event) {
  event.preventDefault();
  event.stopPropagation();
  elements.dropZone.classList.remove("drag-over");

  const files = event.dataTransfer.files;
  if (files.length > 0) {
    const file = files[0];
    if (file.type.startsWith("image/")) {
      elements.fileInput.files = files;
      loadFile(file);
    } else {
      showToast("error", "Please drop a valid image file.");
    }
  }
}

/**
 * Load and preview file
 */
function loadFile(file) {
  currentFile = file;

  // Create preview URL
  const url = URL.createObjectURL(file);

  // Update input preview
  elements.previewIn.src = url;
  elements.previewIn.style.display = "block";
  elements.inputPreview.querySelector(".preview-placeholder").style.display =
    "none";

  // Update input info and suggest size for auto mode
  const reader = new FileReader();
  reader.onload = (e) => {
    const img = new Image();
    img.onload = () => {
      elements.inputInfo.textContent = `${img.width} × ${img.height}px`;

      // If auto mode, update info box with suggested size
      if (elements.sizeModeSelect && elements.sizeModeSelect.value === "auto") {
        // Simple suggestion: round to power of 2 or multiple of 8
        const longSide = Math.max(img.width, img.height);
        const aspect = img.width / img.height;

        // Try power of 2
        let power = 1;
        while (power < longSide) power <<= 1;
        const power2Long =
          power - longSide < longSide - (power >> 1) ? power : power >> 1;

        // Try multiple of 8
        const multiple8Long = Math.round(longSide / 8) * 8;

        // Choose closer
        const suggestedLong =
          Math.abs(power2Long - longSide) < Math.abs(multiple8Long - longSide)
            ? power2Long
            : multiple8Long;

        let suggestedW, suggestedH;
        if (img.width >= img.height) {
          suggestedW = suggestedLong;
          suggestedH = Math.max(8, Math.round(suggestedW / aspect));
        } else {
          suggestedH = suggestedLong;
          suggestedW = Math.max(8, Math.round(suggestedH * aspect));
        }

        // Round to multiple of 8
        suggestedW = Math.round(suggestedW / 8) * 8;
        suggestedH = Math.round(suggestedH / 8) * 8;

        const infoBox =
          elements.autoSizeInfo?.querySelector(".info-box") ||
          elements.autoSizeInfo;
        if (infoBox) {
          infoBox.innerHTML =
            `<strong>Auto mode:</strong> Will suggest ${suggestedW} × ${suggestedH}px ` +
            `(based on input ${img.width} × ${img.height}px)`;
        }
      }
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);

  // Reset output
  resetOutput();

  // Update UI
  updateUI();
  elements.statusText.textContent = `Loaded: ${file.name}`;
}

/**
 * Validate inputs
 */
function validateInputs() {
  const mode = elements.sizeModeSelect.value;
  let isValid = true;

  // Clear custom validity for all inputs first
  if (elements.targetInput) {
    elements.targetInput.setCustomValidity("");
  }
  if (elements.sizeWidthInput) {
    elements.sizeWidthInput.setCustomValidity("");
  }
  if (elements.sizeHeightInput) {
    elements.sizeHeightInput.setCustomValidity("");
  }

  // Validate only the relevant inputs for current mode
  if (mode === "square") {
    const target = parseInt(elements.targetInput.value);
    if (!target || target < 8 || target > 4096) {
      elements.targetInput.setCustomValidity(
        "Target must be between 8 and 4096"
      );
      isValid = false;
    }
  } else if (mode === "custom") {
    const width = parseInt(elements.sizeWidthInput.value);
    const height = parseInt(elements.sizeHeightInput.value);
    if (!width || width < 8 || width > 4096) {
      elements.sizeWidthInput.setCustomValidity(
        "Width must be between 8 and 4096"
      );
      isValid = false;
    }
    if (!height || height < 8 || height > 4096) {
      elements.sizeHeightInput.setCustomValidity(
        "Height must be between 8 and 4096"
      );
      isValid = false;
    }
  }
  // For auto, power_of_two, multiple modes - no validation needed

  updateUI();
  return isValid;
}

/**
 * Update UI state
 */
function updateUI() {
  const hasFile = currentFile !== null;
  if (!hasFile) {
    elements.processBtn.disabled = true;
    return;
  }

  const mode = elements.sizeModeSelect?.value || "auto";
  let isValid = true;

  // Only validate inputs that are relevant for current mode
  if (mode === "square") {
    // Check if targetInput is visible and valid
    const squareVisible =
      elements.squareSizeGroup &&
      elements.squareSizeGroup.style.display !== "none";
    if (squareVisible && elements.targetInput) {
      isValid = isValid && elements.targetInput.checkValidity();
    }
  } else if (mode === "custom") {
    // Check if custom inputs are visible and valid
    const customVisible =
      elements.customSizeGroup &&
      elements.customSizeGroup.style.display !== "none";
    if (customVisible && elements.sizeWidthInput && elements.sizeHeightInput) {
      isValid =
        isValid &&
        elements.sizeWidthInput.checkValidity() &&
        elements.sizeHeightInput.checkValidity();
    }
  }
  // auto, power_of_two, multiple modes don't need validation - just need file

  elements.processBtn.disabled = !isValid || processing;
}

/**
 * Handle process button click
 */
async function handleProcess() {
  if (!currentFile || processing) return;

  processing = true;
  updateUI();
  resetOutput();
  showProgress(0, "Uploading file...");

  try {
    // Create form data
    const formData = new FormData();
    formData.append("file", currentFile);

    // Size parameters
    const sizeMode = elements.sizeModeSelect.value;
    formData.append("size_mode", sizeMode);
    formData.append("target", elements.targetInput.value || "512");

    if (sizeMode === "multiple") {
      formData.append("size_multiple", elements.sizeMultipleSelect.value);
    } else if (sizeMode === "custom") {
      formData.append("size_width", elements.sizeWidthInput.value);
      formData.append("size_height", elements.sizeHeightInput.value);
    }

    formData.append("kind", elements.kindSelect.value);
    formData.append("superres", elements.superresSelect.value);

    // Start processing
    showProgress(10, "Processing image...");
    elements.statusText.textContent = "Processing...";

    const response = await fetch(`${API_URL}/process`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ error: "Unknown error" }));
      throw new Error(error.error || error.detail || "Processing failed");
    }

    const result = await response.json();

    if (!result.ok) {
      throw new Error(result.error || "Processing failed");
    }

    // Show progress
    showProgress(90, "Finalizing...");

    // Load output image
    if (result.meta && result.meta.dst) {
      const outputUrl = `${API_URL}/download?path=${encodeURIComponent(
        result.meta.dst
      )}`;
      await loadOutputImage(outputUrl, result.meta);
    }

    showProgress(100, "Complete!");
    elements.statusText.textContent = "Processing complete";
    showToast("success", "Image processed successfully!");

    // Update metadata
    updateMetadata(result.meta);
  } catch (error) {
    console.error("Processing error:", error);
    elements.statusText.textContent = "Error: " + error.message;
    showToast("error", error.message || "Failed to process image");
    hideProgress();
  } finally {
    processing = false;
    updateUI();
    setTimeout(() => hideProgress(), 2000);
  }
}

/**
 * Load output image
 */
function loadOutputImage(url, meta) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";

    img.onload = () => {
      elements.previewOut.src = url;
      elements.previewOut.style.display = "block";
      elements.outputPreview.querySelector(
        ".preview-placeholder"
      ).style.display = "none";
      elements.downloadContainer.style.display = "block";

      // Update output info
      if (meta) {
        const info = [];
        if (meta.final_w && meta.final_h) {
          info.push(`${meta.final_w} × ${meta.final_h}px`);
        }
        if (meta.kind) {
          info.push(`Type: ${meta.kind}`);
        }
        elements.outputInfo.textContent = info.join(" • ");
      }

      // Store download URL
      elements.downloadBtn.dataset.url = url;
      elements.downloadBtn.dataset.filename = currentFile
        ? `${currentFile.name.replace(/\.[^/.]+$/, "")}_processed.png`
        : "processed.png";

      resolve();
    };

    img.onerror = () => {
      reject(new Error("Failed to load output image"));
    };

    img.src = url;
  });
}

/**
 * Show progress bar
 */
function showProgress(percent, status) {
  elements.progressSection.style.display = "block";
  elements.progressFill.style.width = `${percent}%`;
  elements.progressStatus.textContent = status;
  elements.progressPercent.textContent = `${Math.round(percent)}%`;
}

/**
 * Hide progress bar
 */
function hideProgress() {
  elements.progressSection.style.display = "none";
  elements.progressFill.style.width = "0%";
}

/**
 * Update metadata display
 */
function updateMetadata(meta) {
  if (!meta) return;

  elements.metadataSection.style.display = "block";
  elements.metadataLog.textContent = JSON.stringify(meta, null, 2);
}

/**
 * Toggle metadata section
 */
function toggleMetadata() {
  const isCollapsed = elements.metadataContent.classList.contains("collapsed");
  elements.metadataContent.classList.toggle("collapsed");
  elements.toggleMetadata.textContent = isCollapsed ? "▼" : "▶";
}

/**
 * Handle download button
 */
function handleDownload() {
  const url = elements.downloadBtn.dataset.url;
  const filename = elements.downloadBtn.dataset.filename;

  if (!url) return;

  // Create temporary link and trigger download
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  showToast("success", "Download started");
}

/**
 * Handle reset button
 */
function handleReset() {
  currentFile = null;
  elements.fileInput.value = "";
  resetOutput();
  resetInput();
  updateUI();
  elements.statusText.textContent = "Ready";
  hideProgress();
  elements.metadataSection.style.display = "none";
}

/**
 * Reset input preview
 */
function resetInput() {
  if (elements.previewIn.src) {
    URL.revokeObjectURL(elements.previewIn.src);
  }
  elements.previewIn.src = "";
  elements.previewIn.style.display = "none";
  elements.inputPreview.querySelector(".preview-placeholder").style.display =
    "flex";
  elements.inputInfo.textContent = "";
}

/**
 * Reset output preview
 */
function resetOutput() {
  elements.previewOut.src = "";
  elements.previewOut.style.display = "none";
  elements.outputPreview.querySelector(".preview-placeholder").style.display =
    "flex";
  elements.downloadContainer.style.display = "none";
  elements.outputInfo.textContent = "";
  elements.downloadBtn.dataset.url = "";
  elements.downloadBtn.dataset.filename = "";
}

/**
 * Show toast notification
 */
function showToast(type, message) {
  const toast = type === "error" ? elements.errorToast : elements.successToast;
  const messageEl =
    type === "error" ? elements.errorMessage : elements.successMessage;

  messageEl.textContent = message;
  toast.style.display = "flex";

  // Auto-hide after 5 seconds
  setTimeout(() => {
    hideToast(type);
  }, 5000);
}

/**
 * Hide toast notification
 */
function hideToast(type) {
  const toast = type === "error" ? elements.errorToast : elements.successToast;
  toast.style.display = "none";
}

// Initialize on load
document.addEventListener("DOMContentLoaded", init);

// Periodic API status check
setInterval(checkAPIStatus, 30000); // Check every 30 seconds
