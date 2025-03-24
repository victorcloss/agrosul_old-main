setTimeout(function() {
    const exportButton = document.getElementById('export-button');

    if (exportButton) {
        exportButton.onclick = function() {
            if (typeof html2canvas === 'undefined') {
                console.error("html2canvas is not loaded. Check the assets folder.");
                return;
            }
            console.log("Button clicked! Checking selected tab...");

            // Get the currently selected tab value
            const selectedTab = document.querySelector('#tabs .tab--selected').getAttribute('value');

            // Map the selected tab value to the corresponding card ID
            let cardElementId;
            switch (selectedTab) {
                case 'tab-dia':
                    cardElementId = 'capture-card-dia';
                    break;
                case 'tab-historico':
                    cardElementId = 'capture-card-historico';
                    break;
                case 'tab-financeiro':
                    cardElementId = 'capture-card-financeiro';
                    break;
                case 'tab-upload':
                    cardElementId = 'capture-card-upload';
                    break;
                default:
                    console.error("No matching card for the selected tab.");
                    return;
            }

            // Select the appropriate card element
            const cardElement = document.getElementById(cardElementId);
            if (cardElement) {
                console.log(`Card element for ${selectedTab} found. Proceeding with capture.`);
                html2canvas(cardElement).then(canvas => {
                    console.log("Captured card as canvas");

                    // Convert canvas to data URL (PNG format)
                    const imgData = canvas.toDataURL('image/png');
                    
                    // Create a link element to download the image
                    const a = document.createElement('a');
                    a.href = imgData;
                    a.download = `${selectedTab}_exported_card.png`;  // Customize the file name
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                });
            } else {
                console.log("Card element not found. Check the selector.");
            }
        };
    } else {
        console.log("Export button not found in the DOM.");
    }
}, 5000);  // Delay by 5 seconds (adjust as needed)
