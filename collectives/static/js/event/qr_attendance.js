/**
 * QR Code Attendance Scanner
 * Used for marking event participants as present by scanning their license QR code
 */

let scanHistory = [];
let html5QrCode;
let isScanning = false;

/**
 * Initialize the QR code scanner
 */
function initQrScanner() {
  html5QrCode = new Html5Qrcode("qr-reader");
  
  const config = {
    fps: 10,
    qrbox: { width: 250, height: 250 },
    aspectRatio: 1.0
  };
  
  // Try to start with back camera
  html5QrCode.start(
    { facingMode: "environment" },
    config,
    onScanSuccess,
    onScanFailure
  ).catch((err) => {
    // If back camera fails, try with any camera
    html5QrCode.start(
      { facingMode: "user" },
      config,
      onScanSuccess,
      onScanFailure
    ).catch((err) => {
      showResult('Impossible d\'accéder à la caméra. Veuillez autoriser l\'accès.', 'error');
      console.error(err);
    });
  });
}

/**
 * Add a scan result to the history list
 * @param {string} name - User name
 * @param {string} license - License number
 * @param {boolean} success - Whether the scan was successful
 * @param {string} message - Status message
 */
function addToHistory(name, license, success, message) {
  const historyList = document.getElementById('scan-history-list');
  const timestamp = new Date().toLocaleTimeString('fr-FR');
  
  const historyItem = document.createElement('div');
  historyItem.className = `qr-history-item qr-history-item--${success ? 'success' : 'error'}`;
  
  const info = document.createElement('div');
  info.className = 'qr-history-item__info';
  info.innerHTML = `<strong>${name || license}</strong><br><small>${timestamp} - ${message}</small>`;
  
  const icon = document.createElement('div');
  icon.className = 'qr-history-item__icon';
  icon.className = 'qr-history-item__icon';
  icon.innerHTML = success ? '✓' : '✗';
  
  historyItem.appendChild(info);
  historyItem.appendChild(icon);
  
  // Insert at the beginning
  if (historyList.firstChild) {
    historyList.insertBefore(historyItem, historyList.firstChild);
  } else {
    historyList.appendChild(historyItem);
  }
  
  // Keep only last 20 entries
  while (historyList.children.length > 20) {
    historyList.removeChild(historyList.lastChild);
  }
}

/**
 * Handle successful QR code scan
 * @param {string} decodedText - The decoded QR code text
 * @param {object} decodedResult - The full scan result object
 */
async function onScanSuccess(decodedText, decodedResult) {
  if (isScanning) return; // Prevent multiple scans
  isScanning = true;
  
  showResult('Traitement...', 'info');
  
  try {
    const response = await fetch(`/collectives/${window.eventId}/qr_attendance/mark_present`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': window.csrfToken,
      },
      body: JSON.stringify({
        qr_data: decodedText
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      showResult(data.message, 'success');
      addToHistory(data.user.name, data.user.license, true, 'Marqué présent');
    } else {
      showResult(data.error, 'error');
      const license = decodedText.length >= 18 ? decodedText.substring(6, 18) : 'Inconnu';
      addToHistory(null, license, false, data.error);
      
    }
  } catch (error) {
    showResult('Erreur de communication avec le serveur.', 'error');
    addToHistory(null, 'Erreur', false, error.message);
  }
  
  // Allow next scan after 1.5 seconds
  setTimeout(() => {
    isScanning = false;
  }, 1500);
}

/**
 * Handle scan failure (usually means no QR code found)
 * @param {string} error - Error message
 */
function onScanFailure(error) {
  // Don't show errors for "No QR code found" as it's normal
  // console.warn(`QR scan error: ${error}`);
}



/**
 * Display a result message to the user
 * @param {string} message - Message to display
 * @param {string} type - Type of message (success, error, info)
 */
function showResult(message, type) {
  const container = document.getElementById('scan-result-container');
  const resultDiv = document.createElement('div');
  resultDiv.className = `qr-result qr-result--${type}`;
  resultDiv.textContent = message;
  container.innerHTML = '';
  container.appendChild(resultDiv);
  
  // Auto-hide after 5 seconds
  setTimeout(() => {
    resultDiv.style.opacity = '0';
    resultDiv.style.transition = 'opacity 0.5s';
    setTimeout(() => resultDiv.remove(), 500);
  }, 5000);
}

/**
 * Clean up scanner on page unload
 */
function cleanupScanner() {
  if (html5QrCode) {
    html5QrCode.stop().catch(err => console.error(err));
  }
}

// Start QR scanner when page loads
window.addEventListener('load', initQrScanner);

// Clean up on page unload
window.addEventListener('beforeunload', cleanupScanner);
