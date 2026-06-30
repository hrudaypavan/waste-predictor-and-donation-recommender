document.addEventListener('DOMContentLoaded', () => {
    // -----------------------------------------------------------------
    // 1. Session and Auth Check
    // -----------------------------------------------------------------
    const username = localStorage.getItem("loggedInUser");
    const userIdStr = localStorage.getItem("userId");
    
    if (!username || !userIdStr) {
        window.location.href = "login.html";
        return;
    }
    
    const userId = parseInt(userIdStr, 10);
    const welcomeUserEl = document.getElementById("welcomeUser");
    if (welcomeUserEl) {
        welcomeUserEl.innerHTML = `<i class="fas fa-user-circle"></i> Welcome, ${username} 👋`;
    }
    
    // Set default purchase date to today
    const purchaseDateInput = document.getElementById('purchaseDate');
    if (purchaseDateInput) {
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');
        purchaseDateInput.value = `${yyyy}-${mm}-${dd}`;
    }

    // -----------------------------------------------------------------
    // 2. Global State & Theme Toggle
    // -----------------------------------------------------------------
    let inventory = [];
    let pieChartInstance = null;
    let leafMap = null;
    let mapMarkers = [];

    // Load theme selection from localStorage
    const savedTheme = localStorage.getItem("theme") || "light";
    document.body.setAttribute("data-theme", savedTheme);
    const themeBtn = document.getElementById("themeToggleBtn");
    if (themeBtn) {
        themeBtn.innerHTML = savedTheme === "dark" ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
        themeBtn.addEventListener("click", () => {
            const currentTheme = document.body.getAttribute("data-theme");
            const newTheme = currentTheme === "dark" ? "light" : "dark";
            document.body.setAttribute("data-theme", newTheme);
            localStorage.setItem("theme", newTheme);
            themeBtn.innerHTML = newTheme === "dark" ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
            showToast(`Theme switched to ${newTheme} mode!`);
        });
    }

    // Logout Handler
    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", () => {
            if (confirm("Are you sure you want to log out?")) {
                localStorage.removeItem("loggedInUser");
                localStorage.removeItem("userId");
                window.location.href = "login.html";
            }
        });
    }

    // -----------------------------------------------------------------
    // 3. UI Helpers: Toasts and Modals
    // -----------------------------------------------------------------
    window.showToast = function(message, type = 'success') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let icon = 'fa-check-circle';
        if (type === 'warning') icon = 'fa-exclamation-triangle';
        if (type === 'danger') icon = 'fa-times-circle';
        
        toast.innerHTML = `
            <i class="fas ${icon} toast-icon"></i>
            <span class="toast-message">${message}</span>
        `;
        
        container.appendChild(toast);
        setTimeout(() => toast.classList.add('show'), 50);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 400);
        }, 4000);
    };

    window.openModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex';
            setTimeout(() => modal.classList.add('active'), 50);
        }
    };

    window.closeModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300);
        }
    };

    // -----------------------------------------------------------------
    // 4. API Operations: Fetch, Create, Edit, Delete, Stats
    // -----------------------------------------------------------------
    
    // Fetch and Render Dashboard Data
    async function loadDashboardData() {
        const searchQuery = document.getElementById("searchInput")?.value.trim() || "";
        try {
            // Load inventory lists
            const url = `https://waste-predictor-and-donation-recommender.onrender.com/api/groceries?user_id=${userId}&search=${encodeURIComponent(searchQuery)}`;
            const response = await fetch(url);
            if (!response.ok) throw new Error("Failed to load inventory");
            
            inventory = await response.json();
            
            renderInventoryTable();
            renderDonatedTable();
            updateStatistics();
            updatePieChart();
            checkItemExpiryWarnings();
            
        } catch (error) {
            console.error("Fetch inventory error:", error);
            showToast("Failed to connect to the server.", "danger");
        }
    }

    // Add New Item
    const addForm = document.getElementById("addItemForm");
    if (addForm) {
        addForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            const item_name = document.getElementById("itemName").value.trim();
            const category = document.getElementById("itemCategory").value;
            const quantity = parseFloat(document.getElementById("quantity").value);
            const purchase_date = document.getElementById("purchaseDate").value;
            const expiration_date = document.getElementById("expirationDate").value;
            
            if (new Date(expiration_date) < new Date(purchase_date)) {
                showToast("Expiration date cannot be earlier than purchase date!", "warning");
                return;
            }
            
            const payload = {
                item_name,
                category,
                quantity,
                purchase_date,
                expiration_date,
                user_id: userId
            };
            
            try {
                const response = await fetch("https://waste-predictor-and-donation-recommender.onrender.com/api/groceries", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                
                if (!response.ok) throw new Error("Add item failed");
                
                const newItem = await response.json();
                showToast(`"${newItem.item_name}" added! predicted ML waste is ${newItem.predicted_waste_percent}%`, "success");
                
                addForm.reset();
                // Reset purchase date to today
                if (purchaseDateInput) {
                    const today = new Date();
                    purchaseDateInput.value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
                }
                
                loadDashboardData();
                
            } catch (err) {
                console.error(err);
                showToast("Could not save item to backend", "danger");
            }
        });
    }

    // Delete Item Configuration
    const confirmDeleteBtn = document.getElementById("confirmDeleteBtn");
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener("click", async () => {
            const itemId = document.getElementById("deleteItemId").value;
            try {
                const response = await fetch(`https://waste-predictor-and-donation-recommender.onrender.com/api/groceries/${itemId}`, {
                    method: "DELETE"
                });
                if (!response.ok) throw new Error("Delete failed");
                
                showToast("Grocery item permanently deleted", "success");
                closeModal("deleteModal");
                loadDashboardData();
            } catch (err) {
                console.error(err);
                showToast("Failed to delete item", "danger");
            }
        });
    }

    // Edit Item Submission
    const editForm = document.getElementById("editForm");
    if (editForm) {
        editForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            
            const itemId = document.getElementById("editItemId").value;
            const item_name = document.getElementById("editItemName").value.trim();
            const category = document.getElementById("editItemCategory").value;
            const quantity = parseFloat(document.getElementById("editQuantity").value);
            const purchase_date = document.getElementById("editPurchaseDate").value;
            const expiration_date = document.getElementById("editExpirationDate").value;
            
            const payload = {
                item_name,
                category,
                quantity,
                purchase_date,
                expiration_date
            };
            
            try {
                const response = await fetch(`https://waste-predictor-and-donation-recommender.onrender.com/api/groceries/${itemId}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                
                if (!response.ok) throw new Error("Update failed");
                showToast("Grocery item successfully updated!", "success");
                closeModal("editModal");
                loadDashboardData();
            } catch (err) {
                console.error(err);
                showToast("Failed to save changes", "danger");
            }
        });
    }

    // Helper: format countdown string
    function getDonationCountdown(expirationDateStr) {
        const today = new Date();
        const expiry = new Date(expirationDateStr);
        
        // Donation deadline is 24 hours before actual expiry
        const deadline = new Date(expiry.getTime() - (24 * 60 * 60 * 1000));
        
        const msRemaining = deadline - today;
        if (msRemaining < 0) {
            return { text: "Expired for Donation", statusClass: "timer-critical", isExpired: true };
        }
        
        const totalHours = Math.floor(msRemaining / (1000 * 60 * 60));
        const days = Math.floor(totalHours / 24);
        const hours = totalHours % 24;
        
        let text = "";
        let statusClass = "timer-safe";
        
        if (days > 0) {
            text = `${days}d ${hours}h remaining`;
            if (days < 2) statusClass = "timer-warning";
        } else {
            text = `${hours}h remaining`;
            statusClass = "timer-critical";
        }
        
        return { text, statusClass, isExpired: false };
    }

    // Render Active Grocery Inventory Table
    function renderInventoryTable() {
        const tbody = document.querySelector("#inventoryTable tbody");
        if (!tbody) return;
        tbody.innerHTML = "";
        
        const activeItems = inventory.filter(item => item.status === "remaining");
        
        if (activeItems.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-secondary);">No inventory items found. Add some above!</td></tr>`;
            return;
        }
        
        activeItems.forEach(item => {
            const tr = document.createElement("tr");
            const countdown = getDonationCountdown(item.expiration_date);
            
            tr.innerHTML = `
                <td><strong>${item.item_name}</strong></td>
                <td>${item.category || "General"}</td>
                <td>${item.quantity}</td>
                <td>${item.expiration_date}</td>
                <td class="waste-pct-cell">${item.predicted_waste_percent}%</td>
                <td><span class="risk-badge risk-${item.waste_risk_level.toLowerCase()}">${item.waste_risk_level}</span></td>
                <td><span class="urgency-timer ${countdown.statusClass}"><i class="far fa-clock"></i> ${countdown.text}</span></td>
                <td>
                    <div class="action-btn-group">
                        <button class="action-btn donate-btn" onclick="triggerDonate(${item.id})"><i class="fas fa-hand-holding-heart"></i> Donate</button>
                        <button class="action-btn use-recipe-btn" onclick="triggerRecipeSuggest(${item.id})"><i class="fas fa-utensils"></i> Recipe</button>
                        <button class="action-btn edit-btn" onclick="triggerEdit(${item.id})"><i class="fas fa-edit"></i></button>
                        <button class="action-btn delete-btn" onclick="triggerDelete(${item.id})"><i class="fas fa-trash-alt"></i></button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Render Donated Items Table
    function renderDonatedTable() {
        const tbody = document.getElementById("donatedItemsList");
        if (!tbody) return;
        tbody.innerHTML = "";
        
        const donatedItems = inventory.filter(item => item.status === "donated");
        
        if (donatedItems.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-secondary);">No donations completed yet.</td></tr>`;
            return;
        }
        
        donatedItems.forEach(item => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${item.item_name}</strong></td>
                <td>${item.category || "General"}</td>
                <td>${item.quantity}</td>
                <td>${item.expiration_date}</td>
                <td>
                    <div class="action-btn-group">
                        <button class="action-btn edit-btn" onclick="triggerEdit(${item.id})"><i class="fas fa-edit"></i> Edit</button>
                        <button class="action-btn delete-btn" onclick="triggerDelete(${item.id})"><i class="fas fa-trash-alt"></i> Delete</button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Action Triggers called from HTML click handlers
    window.triggerDonate = async function(itemId) {
        try {
            const response = await fetch(`https://waste-predictor-and-donation-recommender.onrender.com/api/groceries/${itemId}/status`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status: "donated" })
            });
            if (!response.ok) throw new Error("Mark donated failed");
            
            const donated = await response.json();
            showToast(`"${donated.item_name}" has been transferred to Donations! Thank you!`, "success");
            loadDashboardData();
        } catch (err) {
            console.error(err);
            showToast("Failed to donate item", "danger");
        }
    };

    window.triggerEdit = function(itemId) {
        const item = inventory.find(i => i.id === itemId);
        if (!item) return;
        
        document.getElementById("editItemId").value = item.id;
        document.getElementById("editItemName").value = item.item_name;
        document.getElementById("editItemCategory").value = item.category || "Dairy";
        document.getElementById("editQuantity").value = item.quantity;
        document.getElementById("editPurchaseDate").value = item.purchase_date;
        document.getElementById("editExpirationDate").value = item.expiration_date;
        
        openModal("editModal");
    };

    window.triggerDelete = function(itemId) {
        document.getElementById("deleteItemId").value = itemId;
        openModal("deleteModal");
    };

    window.triggerRecipeSuggest = async function(itemId) {
        // Show loading toast
        showToast("Generating recipe options...", "success");
        try {
            const response = await fetch(`https://waste-predictor-and-donation-recommender.onrender.com/api/recipes/recommend?user_id=${userId}`);
            if (!response.ok) throw new Error();
            const data = await response.json();
            
            const modalBody = document.getElementById("recipeModalBody");
            modalBody.innerHTML = "";
            
            if (data.recipes.length === 0) {
                modalBody.innerHTML = `<p style='text-align:center;'>No specific recipes found for your ingredients.</p>`;
            } else {
                data.recipes.forEach(recipe => {
                    const block = document.createElement("div");
                    block.className = "recipe-block";
                    block.innerHTML = `
                        <h4>🍳 ${recipe.recipe_title} (${recipe.matched_ingredient})</h4>
                        <p><strong>Ingredients:</strong> ${recipe.ingredients}</p>
                        <p style="margin-top: 4px;"><strong>Steps:</strong> ${recipe.steps}</p>
                        <hr style="border:none; border-top:1px solid var(--border-color); margin:12px 0;">
                    `;
                    modalBody.appendChild(block);
                });
            }
            openModal("recipeModal");
        } catch {
            showToast("Failed to load recipe suggestions", "danger");
        }
    };

    // Update statistics dashboard counts dynamically
    async function updateStatistics() {
        try {
            const response = await fetch(`https://waste-predictor-and-donation-recommender.onrender.com/api/groceries/stats?user_id=${userId}`);
            if (!response.ok) throw new Error("Stats lookup failed");
            
            const stats = await response.json();
            
            document.getElementById("totalItems").textContent = stats.total_items;
            document.getElementById("expiringItems").textContent = stats.expiring_soon;
            document.getElementById("donatedItems").textContent = stats.donated_count;
            document.getElementById("wastedCount").textContent = `${stats.waste_saved_kg} kg`;
            
            // Calculate dynamic Eco Impact score
            // Eco Impact % is (donated items / total items) * 100
            const total = stats.total_items;
            const donated = stats.donated_count;
            
            const scorePercent = total === 0 ? 0 : Math.round((donated / total) * 100);
            
            const scoreEl = document.getElementById("ecoImpactScore");
            const circleEl = document.getElementById("ecoImpactCircle");
            const msgEl = document.getElementById("ecoImpactMessage");
            
            if (scoreEl) scoreEl.textContent = `${scorePercent}%`;
            if (circleEl) {
                circleEl.style.background = `conic-gradient(var(--primary) 0% ${scorePercent}%, var(--border-color) ${scorePercent}% 100%)`;
            }
            if (msgEl) {
                if (scorePercent === 0) {
                    msgEl.textContent = "Mark expiring ingredients as 'Donated' to start saving food waste!";
                } else if (scorePercent < 40) {
                    msgEl.textContent = "Good start! You are routing approaching-expiry items to local NGOs.";
                } else if (scorePercent < 75) {
                    msgEl.textContent = "Great job! You have rescued a significant portion of your groceries from going waste.";
                } else {
                    msgEl.textContent = "Incredible! You are a master of food waste prevention. Zero-waste champion! 🏆";
                }
            }
            
        } catch (err) {
            console.error("Stats update failure:", err);
        }
    }

    // Dynamic Chart.js Analytics updating
    function updatePieChart() {
        const ctx = document.getElementById('monthlyPieChart')?.getContext('2d');
        if (!ctx) return;
        
        let remaining = 0;
        let wasted = 0;
        let donated = 0;
        
        inventory.forEach(item => {
            if (item.status === "donated") donated++;
            else if (item.status === "wasted") wasted++;
            else remaining++;
        });
        
        const chartData = [remaining, wasted, donated];
        
        if (pieChartInstance) {
            pieChartInstance.destroy();
        }
        
        // If empty inventory, show message
        if (inventory.length === 0) {
            const canvas = document.getElementById('monthlyPieChart');
            const ctxText = canvas.getContext('2d');
            ctxText.clearRect(0, 0, canvas.width, canvas.height);
            ctxText.font = "14px Outfit";
            ctxText.fillStyle = "#64748b";
            ctxText.textAlign = "center";
            ctxText.fillText("No inventory data found to chart.", canvas.width / 2, canvas.height / 2);
            return;
        }
        
        // Theme color adaptive
        const isDark = document.body.getAttribute("data-theme") === "dark";
        const gridColor = isDark ? "#475569" : "#cbd5e1";
        
        pieChartInstance = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Remaining', 'Wasted', 'Donated'],
                datasets: [{
                    data: chartData,
                    backgroundColor: ['#3b82f6', '#ef4444', '#10b981'],
                    borderWidth: 1,
                    borderColor: isDark ? '#1e293b' : '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: isDark ? '#f8fafc' : '#1e293b',
                            font: { family: 'Outfit', size: 12 }
                        }
                    }
                }
            }
        });
    }

    // Toast alert checker for items expiring within 48h
    function checkItemExpiryWarnings() {
        const today = new Date();
        const activeItems = inventory.filter(item => item.status === "remaining");
        
        activeItems.forEach(item => {
            const expiry = new Date(item.expiration_date);
            const msLeft = expiry - today;
            const daysLeft = Math.ceil(msLeft / (1000 * 60 * 60 * 24));
            
            if (daysLeft >= 0 && daysLeft <= 2) {
                // Show floating warn toasts for items entering danger zones
                showToast(`"${item.item_name}" is expiring in ${daysLeft} day(s). Donate it to prevent waste!`, "warning");
            }
        });
    }

    // -----------------------------------------------------------------
    // 5. Leaflet Map & Interactive NGO Matching
    // -----------------------------------------------------------------
    const ngos = [
        { name: "Akshaya Patra Foundation", lat: 17.4458, lon: 78.3489, phone: "+914023505555", place: "Nanakramguda, Hyderabad" },
        { name: "Goonj Hyderabad", lat: 17.4504, lon: 78.3820, phone: "+911180091222", place: "Madhapur, Hyderabad" },
        { name: "Robin Hood Army Hyderabad", lat: 17.4326, lon: 78.4071, phone: "+919873451238", place: "Jubilee Hills, Hyderabad" },
        { name: "Helping Hands Foundation", lat: 17.3850, lon: 78.4867, phone: "+919849000786", place: "Lakdikapul, Hyderabad" },
        { name: "Sparsh Hospice", lat: 17.4120, lon: 78.4480, phone: "+914023323333", place: "Banjara Hills, Hyderabad" },
        { name: "Aahwahan Foundation", lat: 17.4580, lon: 78.3630, phone: "+919611202520", place: "Gachibowli, Hyderabad" },
        { name: "Smile Foundation", lat: 17.4375, lon: 78.4483, phone: "+911140130000", place: "Somajiguda, Hyderabad" },
        { name: "Bhumi NGO", lat: 17.4065, lon: 78.4772, phone: "+919884567890", place: "Himayatnagar, Hyderabad" },
        { name: "Youth Feed India", lat: 17.4483, lon: 78.3915, phone: "+919550123456", place: "Hitech City, Hyderabad" },
        { name: "Sevalaya Hyderabad", lat: 17.4710, lon: 78.3765, phone: "+919876543210", place: "Kondapur, Hyderabad" }
    ];

    function calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Earth's radius in km
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) ** 2 +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLon / 2) ** 2;
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return (R * c).toFixed(2);
    }

    function initNgoMap() {
        const mapContainer = document.getElementById("leafletMap");
        if (!mapContainer) return;
        
        // Default: Hyderabad center coordinates
        let userLat = 17.4065;
        let userLon = 78.4772;
        
        const statusText = document.getElementById("locationStatus");
        
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    userLat = pos.coords.latitude;
                    userLon = pos.coords.longitude;
                    statusText.innerHTML = `<i class="fas fa-map-marker-alt" style="color:var(--primary);"></i> Detected location. Pinpointing 10 nearest food collection centers:`;
                    renderMapAndNGOList(userLat, userLon);
                },
                () => {
                    statusText.innerHTML = `<i class="fas fa-exclamation-triangle" style="color:var(--warning);"></i> Geolocation permission denied. Defaulting to Hyderabad center:`;
                    renderMapAndNGOList(userLat, userLon);
                }
            );
        } else {
            statusText.innerHTML = `❌ Browser doesn't support geolocation. Showing Hyderabad NGOs:`;
            renderMapAndNGOList(userLat, userLon);
        }
    }

    function renderMapAndNGOList(lat, lon) {
        // Initialize map if not yet created
        if (!leafMap) {
            leafMap = L.map('leafletMap').setView([lat, lon], 12);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(leafMap);
        } else {
            leafMap.setView([lat, lon], 12);
        }
        
        // Clear old markers
        mapMarkers.forEach(marker => leafMap.removeLayer(marker));
        mapMarkers = [];
        
        // Add User's Marker
        const userIcon = L.divIcon({
            html: '<i class="fas fa-dot-circle" style="color:#3b82f6; font-size:1.6rem; text-shadow:0 0 5px white;"></i>',
            iconSize: [24, 24],
            className: 'user-map-marker'
        });
        const userMarker = L.marker([lat, lon], { icon: userIcon }).addTo(leafMap)
            .bindPopup("<strong>You are here</strong>").openPopup();
        mapMarkers.push(userMarker);
        
        // Calculate NGO distances, sort them, render list
        const sortedNgos = ngos.map(ngo => ({
            ...ngo,
            distance: calculateDistance(lat, lon, ngo.lat, ngo.lon)
        })).sort((a, b) => a.distance - b.distance);
        
        const listContainer = document.getElementById("ngoList");
        if (listContainer) {
            listContainer.innerHTML = "";
        }
        
        sortedNgos.forEach(ngo => {
            // Add Map pins
            const ngoIcon = L.divIcon({
                html: '<i class="fas fa-hand-holding-heart" style="color:#10b981; font-size:1.8rem; text-shadow:0 1px 3px rgba(0,0,0,0.3);"></i>',
                iconSize: [24, 24],
                className: 'ngo-map-marker'
            });
            const marker = L.marker([ngo.lat, ngo.lon], { icon: ngoIcon }).addTo(leafMap)
                .bindPopup(`<strong>${ngo.name}</strong><br>📍 ${ngo.place}<br>📞 <a href="tel:${ngo.phone}">${ngo.phone}</a>`);
            mapMarkers.push(marker);
            
            // Add cards
            if (listContainer) {
                const card = document.createElement("div");
                card.className = "ngo-card";
                card.innerHTML = `
                    <div>
                        <h4>${ngo.name}</h4>
                        <p><i class="fas fa-map-pin"></i> ${ngo.place} (${ngo.distance} km away)</p>
                    </div>
                    <div class="ngo-actions">
                        <a href="tel:${ngo.phone}"><i class="fas fa-phone-alt"></i> Call for Pickup</a>
                    </div>
                `;
                listContainer.appendChild(card);
            }
        });
    }

    // -----------------------------------------------------------------
    // 6. Voice Speech input (Speech Recognition)
    // -----------------------------------------------------------------
    const micBtn = document.getElementById("micBtn");
    if (micBtn) {
        micBtn.addEventListener("click", () => {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                showToast("Web Speech API is not supported in this browser.", "danger");
                return;
            }
            
            const recognition = new SpeechRecognition();
            recognition.lang = "en-IN";
            recognition.interimResults = false;
            
            recognition.onstart = () => {
                micBtn.classList.add("mic-active");
                showToast("Listening... Speak the grocery item name.", "success");
            };
            
            recognition.onend = () => {
                micBtn.classList.remove("mic-active");
            };
            
            recognition.onresult = (event) => {
                const resultText = event.results[0][0].transcript;
                const nameInput = document.getElementById("itemName");
                if (nameInput) {
                    // Strip ending periods and capitalize
                    nameInput.value = resultText.replace(/\.$/, "");
                    showToast(`Voice input loaded: "${nameInput.value}"`);
                }
            };
            
            recognition.onerror = (e) => {
                console.error(e);
                showToast("Voice speech input failed.", "warning");
                micBtn.classList.remove("mic-active");
            };
            
            recognition.start();
        });
    }

    // -----------------------------------------------------------------
    // 7. CSV and PDF Exporters
    // -----------------------------------------------------------------
    
    // Download CSV
    const csvBtn = document.getElementById("exportCsvBtn");
    if (csvBtn) {
        csvBtn.addEventListener("click", () => {
            if (inventory.length === 0) {
                showToast("No data available to export to CSV.", "warning");
                return;
            }
            
            let csvContent = "data:text/csv;charset=utf-8,";
            csvContent += "Item Name,Category,Quantity,Purchase Date,Expiration Date,Predicted Waste (%),Waste Risk,Status\n";
            
            inventory.forEach(item => {
                const row = [
                    `"${item.item_name}"`,
                    `"${item.category || "General"}"`,
                    item.quantity,
                    item.purchase_date,
                    item.expiration_date,
                    item.predicted_waste_percent,
                    item.waste_risk_level,
                    item.status
                ].join(",");
                csvContent += row + "\n";
            });
            
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `grocery_inventory_report_${new Date().toISOString().split('T')[0]}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            showToast("CSV report downloaded successfully!");
        });
    }

    // Download PDF
    const pdfBtn = document.getElementById("exportPdfBtn");
    if (pdfBtn) {
        pdfBtn.addEventListener("click", () => {
            const element = document.getElementById("dashboardReportContainer");
            if (!element) return;
            
            showToast("Generating PDF report...", "success");
            
            const opt = {
                margin:       10,
                filename:     `grocery_waste_analytics_${new Date().toISOString().split('T')[0]}.pdf`,
                image:        { type: 'jpeg', quality: 0.98 },
                html2canvas:  { scale: 2, useCORS: true },
                jsPDF:        { unit: 'mm', format: 'a4', orientation: 'landscape' }
            };
            
            html2pdf().set(opt).from(element).save()
                .then(() => showToast("PDF report exported successfully!"))
                .catch((err) => {
                    console.error(err);
                    showToast("Failed to export PDF", "danger");
                });
        });
    }

    // -----------------------------------------------------------------
    // 8. Event Initializations
    // -----------------------------------------------------------------
    
    // Live Search input trigger
    const searchInput = document.getElementById("searchInput");
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener("input", () => {
            clearTimeout(searchTimeout);
            // Throttle database request typing latency
            searchTimeout = setTimeout(() => {
                loadDashboardData();
            }, 300);
        });
    }

    // Load initial configurations
    loadDashboardData();
    initNgoMap();
});