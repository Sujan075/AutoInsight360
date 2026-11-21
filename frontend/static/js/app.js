/**
 * AutoInsight360 — Dynamic Customer 360 Frontend Application
 * Vanilla JavaScript implementation using fetch() for FastAPI backend communication.
 */

// Application State
const state = {
  activeCustomerId: null,
  activeCustomerData: null,
  isSearching: false,
  isAgentLoading: false,
  selectedZipFile: null,
  activeImportSessionId: null,
  isImporting: false,
};

let currentCustomer360 = null;

// DOM Elements Cache
const DOM = {
  dbStatusPill: document.getElementById("dbStatusPill"),
  dbStatusText: document.getElementById("dbStatusText"),
  aiStatusPill: document.getElementById("aiStatusPill"),
  aiStatusText: document.getElementById("aiStatusText"),

  searchInput: document.getElementById("searchInput"),
  searchBtn: document.getElementById("searchBtn"),
  clearSearchBtn: document.getElementById("clearSearchBtn"),
  quickSelectDropdown: document.getElementById("quickSelectDropdown"),

  searchResultsContainer: document.getElementById("searchResultsContainer"),
  searchResultsCount: document.getElementById("searchResultsCount"),
  searchResultsList: document.getElementById("searchResultsList"),
  closeSearchResultsBtn: document.getElementById("closeSearchResultsBtn"),

  alertBanner: document.getElementById("alertBanner"),
  alertMessage: document.getElementById("alertMessage"),
  closeAlertBtn: document.getElementById("closeAlertBtn"),

  emptyState: document.getElementById("emptyState"),
  suggestionChips: document.getElementById("suggestionChips"),
  loadingState: document.getElementById("loadingState"),
  loadingMessage: document.getElementById("loadingMessage"),
  customerProfileView: document.getElementById("customerProfileView"),

  // Hero Profile
  customerAvatar: document.getElementById("customerAvatar"),
  custFullName: document.getElementById("custFullName"),
  custSegmentBadge: document.getElementById("custSegmentBadge"),
  custStatusBadge: document.getElementById("custStatusBadge"),
  custIdTag: document.getElementById("custIdTag"),
  custEmail: document.getElementById("custEmail"),
  custPhone: document.getElementById("custPhone"),
  custLocation: document.getElementById("custLocation"),
  custJoined: document.getElementById("custJoined"),

  // KPIs
  kpiCltv: document.getElementById("kpiCltv"),
  kpiCltvBreakdown: document.getElementById("kpiCltvBreakdown"),
  kpiLoyaltyBalance: document.getElementById("kpiLoyaltyBalance"),
  kpiLoyaltySub: document.getElementById("kpiLoyaltySub"),
  kpiVehiclesCount: document.getElementById("kpiVehiclesCount"),
  kpiPrimaryVehicle: document.getElementById("kpiPrimaryVehicle"),
  kpiServiceVisits: document.getElementById("kpiServiceVisits"),
  kpiServiceCost: document.getElementById("kpiServiceCost"),
  kpiTransactionsCount: document.getElementById("kpiTransactionsCount"),
  kpiTxSub: document.getElementById("kpiTxSub"),
  kpiRating: document.getElementById("kpiRating"),
  kpiReviewsCount: document.getElementById("kpiReviewsCount"),

  // Tabs
  tabButtons: document.querySelectorAll(".tab-btn"),
  tabPanes: document.querySelectorAll(".tab-pane"),
  vehiclesTabBadge: document.getElementById("vehiclesTabBadge"),
  servicesTabBadge: document.getElementById("servicesTabBadge"),
  transactionsTabBadge: document.getElementById("transactionsTabBadge"),
  loyaltyTabBadge: document.getElementById("loyaltyTabBadge"),
  reviewsTabBadge: document.getElementById("reviewsTabBadge"),

  // Tab Content Containers
  vehiclesList: document.getElementById("vehiclesList"),
  servicesTableBody: document.getElementById("servicesTableBody"),
  transactionsTableBody: document.getElementById("transactionsTableBody"),
  loyaltyTimeline: document.getElementById("loyaltyTimeline"),
  reviewsList: document.getElementById("reviewsList"),

  // AI Agent
  agentTargetCustomerName: document.getElementById("agentTargetCustomerName"),
  agentChatHistory: document.getElementById("agentChatHistory"),
  agentLoading: document.getElementById("agentLoading"),
  agentQueryForm: document.getElementById("agentQueryForm"),
  agentQuestionInput: document.getElementById("agentQuestionInput"),
  agentSubmitBtn: document.getElementById("agentSubmitBtn"),
  charCount: document.getElementById("charCount"),
  promptChips: document.querySelectorAll(".prompt-chip"),

  // Data Ingestion / Import Modal
  openImportModalBtn: document.getElementById("openImportModalBtn"),
  closeImportModalBtn: document.getElementById("closeImportModalBtn"),
  importModal: document.getElementById("importModal"),
  metricCustomers: document.getElementById("metricCustomers"),
  metricVehicles: document.getElementById("metricVehicles"),
  metricDealers: document.getElementById("metricDealers"),
  metricTransactions: document.getElementById("metricTransactions"),
  metricServices: document.getElementById("metricServices"),
  uploadZone: document.getElementById("uploadZone"),
  zipFileInput: document.getElementById("zipFileInput"),
  uploadZoneContent: document.getElementById("uploadZoneContent"),
  selectedFileInfo: document.getElementById("selectedFileInfo"),
  selectedFileName: document.getElementById("selectedFileName"),
  selectedFileSize: document.getElementById("selectedFileSize"),
  removeFileBtn: document.getElementById("removeFileBtn"),
  previewImportBtn: document.getElementById("previewImportBtn"),
  importSpinner: document.getElementById("importSpinner"),
  previewResultsContainer: document.getElementById("previewResultsContainer"),
  previewStatusTitle: document.getElementById("previewStatusTitle"),
  badgeAcceptedCount: document.getElementById("badgeAcceptedCount"),
  badgeRejectedCount: document.getElementById("badgeRejectedCount"),
  previewTableBody: document.getElementById("previewTableBody"),
  previewIssuesBox: document.getElementById("previewIssuesBox"),
  previewIssuesList: document.getElementById("previewIssuesList"),
  commitImportBtn: document.getElementById("commitImportBtn"),
  cancelPreviewBtn: document.getElementById("cancelPreviewBtn"),
  importSuccessBox: document.getElementById("importSuccessBox"),
  importSuccessMessage: document.getElementById("importSuccessMessage"),
  importSuccessCounts: document.getElementById("importSuccessCounts"),

  // 2026 Annual Loyalty Dashboard & Redemption Modal
  loyalty2026Balance: document.getElementById("loyalty2026Balance"),
  loyalty2026VisitPts: document.getElementById("loyalty2026VisitPts"),
  loyalty2026VisitsSub: document.getElementById("loyalty2026VisitsSub"),
  loyalty2026BdayPts: document.getElementById("loyalty2026BdayPts"),
  loyalty2026BdaySub: document.getElementById("loyalty2026BdaySub"),
  loyalty2026RedeemedPts: document.getElementById("loyalty2026RedeemedPts"),
  openRedeemModalBtn: document.getElementById("openRedeemModalBtn"),
  redeemModal: document.getElementById("redeemModal"),
  closeRedeemModalBtn: document.getElementById("closeRedeemModalBtn"),
  cancelRedeemBtn: document.getElementById("cancelRedeemBtn"),
  confirmRedeemBtn: document.getElementById("confirmRedeemBtn"),
  modalAvailablePts: document.getElementById("modalAvailablePts"),
  redeemPointsInput: document.getElementById("redeemPointsInput"),
  redeemNotesInput: document.getElementById("redeemNotesInput"),
  redeemErrorMsg: document.getElementById("redeemErrorMsg"),
  redeemSuccessMsg: document.getElementById("redeemSuccessMsg"),
};

// ==========================================================================
// Formatting Helpers
// ==========================================================================

function formatCurrency(amount) {
  if (amount == null || isNaN(amount)) return "₹0.00";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(amount);
}

function formatDate(dateStr) {
  if (!dateStr) return "N/A";
  try {
    const d = new Date(dateStr);
    return isNaN(d) ? dateStr : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return dateStr;
  }
}

function formatNumber(num) {
  if (num == null || isNaN(num)) return "0";
  return new Intl.NumberFormat("en-US").format(num);
}

function getInitials(name) {
  if (!name) return "??";
  const parts = name.trim().split(" ");
  if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function showAlert(message, type = "error") {
  DOM.alertMessage.textContent = message;
  DOM.alertBanner.className = `alert-banner ${type}`;
  DOM.alertBanner.style.display = "flex";
  setTimeout(() => {
    DOM.alertBanner.style.display = "none";
  }, 6000);
}

// ==========================================================================
// Initialization & Health Checks
// ==========================================================================

async function initApp() {
  await checkSystemHealth();
  await loadInitialCustomers();
  bindEventListeners();

  // Check if a customer ID is in URL query parameters (e.g. ?customer_id=1)
  const urlParams = new URLSearchParams(window.location.search);
  const paramCustId = urlParams.get("customer_id");
  if (paramCustId && !isNaN(paramCustId)) {
    loadCustomer360(parseInt(paramCustId, 10));
  }
}

async function checkSystemHealth() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error("Health check returned status " + res.status);
    const data = await res.json();

    // Database Status (Task 4: Genuine status, no hardcoded count in primary header)
    DOM.dbStatusPill.classList.remove("warning");
    DOM.dbStatusPill.classList.add("online");
    DOM.dbStatusText.textContent = "Database: Connected";

    // Populate Detailed Metrics in Import / Admin Panel
    if (DOM.metricCustomers) DOM.metricCustomers.textContent = formatNumber(data.total_customers);
    if (DOM.metricVehicles) DOM.metricVehicles.textContent = formatNumber(data.total_vehicles);
    if (DOM.metricDealers) DOM.metricDealers.textContent = formatNumber(data.total_dealers);
    if (DOM.metricTransactions) DOM.metricTransactions.textContent = formatNumber(data.total_transactions);
    if (DOM.metricServices) DOM.metricServices.textContent = formatNumber(data.total_services);

    // AI Status
    if (data.model_available) {
      DOM.aiStatusPill.classList.remove("warning");
      DOM.aiStatusPill.classList.add("online");
      DOM.aiStatusText.textContent = `Llama 3.1: Ready`;
    } else {
      DOM.aiStatusPill.classList.add("warning");
      DOM.aiStatusText.textContent = `Llama 3.1: Offline (Fallback Mode)`;
    }
  } catch (err) {
    console.error("Health check error:", err);
    DOM.dbStatusPill.classList.add("warning");
    DOM.dbStatusText.textContent = "Database: Disconnected";
    DOM.aiStatusPill.classList.add("warning");
    DOM.aiStatusText.textContent = "AI: Offline";
  }
}

async function loadInitialCustomers() {
  try {
    const res = await fetch("/api/customers/search?limit=15");
    if (!res.ok) throw new Error("Failed to load demo customers");
    const customers = await res.json();

    // Populate Quick Select Dropdown
    DOM.quickSelectDropdown.innerHTML = `<option value="">⚡ Quick Select Customer...</option>`;
    customers.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = `#${c.id} — ${c.full_name} (${c.customer_segment || "Standard"}, ${c.city || "USA"})`;
      DOM.quickSelectDropdown.appendChild(opt);
    });

    // Populate Suggestion Chips on Empty State
    DOM.suggestionChips.innerHTML = "";
    customers.slice(0, 6).forEach((c) => {
      const chip = document.createElement("button");
      chip.className = "chip-btn";
      chip.textContent = `#${c.id} ${c.full_name}`;
      chip.addEventListener("click", () => loadCustomer360(c.id));
      DOM.suggestionChips.appendChild(chip);
    });
  } catch (err) {
    console.warn("Could not load initial customers:", err);
  }
}

// ==========================================================================
// Customer Search & Results
// ==========================================================================

async function performSearch() {
  const query = DOM.searchInput.value.trim();
  DOM.clearSearchBtn.style.display = query ? "block" : "none";

  try {
    DOM.searchBtn.disabled = true;
    DOM.searchBtn.innerHTML = `<span class="spinner-small"></span>`;

    const url = query
      ? `/api/customers/search?q=${encodeURIComponent(query)}&limit=30`
      : `/api/customers/search?limit=20`;

    const res = await fetch(url);
    if (!res.ok) throw new Error("Search request failed.");
    const results = await res.json();

    renderSearchResults(results, query);
  } catch (err) {
    console.error("Search error:", err);
    showAlert("Search failed: " + err.message);
  } finally {
    DOM.searchBtn.disabled = false;
    DOM.searchBtn.innerHTML = `<span>Search</span>`;
  }
}

function renderSearchResults(customers, query) {
  DOM.searchResultsList.innerHTML = "";
  DOM.searchResultsCount.textContent = `${customers.length} customer${customers.length === 1 ? "" : "s"} found${query ? ` for "${query}"` : ""}`;

  if (customers.length === 0) {
    DOM.searchResultsList.innerHTML = `
      <div style="padding: 1rem; text-align: center; color: var(--text-dim); font-size: 0.875rem;">
        No customers matching "${query}". Try searching by customer ID (e.g. 1), name, or email.
      </div>
    `;
  } else {
    customers.forEach((c) => {
      const item = document.createElement("div");
      item.className = "search-result-item";
      item.innerHTML = `
        <div class="result-item-main">
          <div class="result-avatar">${getInitials(c.full_name)}</div>
          <div class="result-info">
            <h4>
              ${c.full_name} 
              <span class="customer-id-tag">#${c.id}</span>
              <span class="badge badge-segment">${c.customer_segment || "Standard"}</span>
            </h4>
            <p>${c.email} • ${c.phone || "No phone"} • ${c.city ? `${c.city}, ${c.state}` : "USA"}</p>
          </div>
        </div>
        <div style="text-align: right;">
          <span style="font-size: 0.75rem; color: var(--text-muted); display: block;">${c.vehicles_count} vehicle(s)</span>
          <span style="font-size: 0.75rem; color: var(--accent-gold); font-family: var(--font-mono);">${formatNumber(c.loyalty_points)} pts</span>
        </div>
      `;
      item.addEventListener("click", () => {
        loadCustomer360(c.id);
        DOM.searchResultsContainer.style.display = "none";
      });
      DOM.searchResultsList.appendChild(item);
    });
  }

  DOM.searchResultsContainer.style.display = "block";
}

// ==========================================================================
// Customer 360 Loader & Renderer
// ==========================================================================

async function loadCustomer360(customerId) {
  if (!customerId || isNaN(customerId)) return;

  state.activeCustomerId = customerId;

  // Update browser URL query param without full reload
  const url = new URL(window.location);
  url.searchParams.set("customer_id", customerId);
  window.history.pushState({}, "", url);

  // Show Loading state
  DOM.emptyState.style.display = "none";
  DOM.customerProfileView.style.display = "none";
  DOM.loadingState.style.display = "flex";
  DOM.loadingMessage.textContent = `Loading Customer #${customerId} Profile & Intelligence...`;

  try {
    const res = await fetch(`/api/customers/${customerId}/360`);
    if (!res.ok) {
      if (res.status === 404) throw new Error(`Customer #${customerId} was not found.`);
      throw new Error(`Failed to load customer profile (status ${res.status}).`);
    }

    const data = await res.json();
    state.activeCustomerData = data;

    renderCustomer360(data);
  } catch (err) {
    console.error("Error loading Customer 360:", err);
    showAlert(err.message);
    DOM.loadingState.style.display = "none";
    DOM.emptyState.style.display = "flex";
  }
}

function renderCustomer360(data) {
  const c = data.customer;
  const m = data.metrics;

  // 1. Hero Profile
  DOM.customerAvatar.textContent = getInitials(c.full_name);
  DOM.custFullName.textContent = c.full_name;
  DOM.custIdTag.textContent = `#${c.id}`;
  DOM.custSegmentBadge.textContent = c.customer_segment || "Standard";
  DOM.custStatusBadge.textContent = c.is_active ? "Active" : "Inactive";
  DOM.custStatusBadge.className = `badge ${c.is_active ? "badge-success" : "badge-danger"}`;

  DOM.custEmail.textContent = c.email;
  DOM.custPhone.textContent = c.phone || "Not provided";
  DOM.custLocation.textContent = c.city ? `${c.city}, ${c.state || ""}` : "USA";
  DOM.custJoined.textContent = formatDate(c.registered_at);

  // Track current loaded customer profile
  currentCustomer360 = data;

  // Sync quick select dropdown value
  DOM.quickSelectDropdown.value = c.id;

  // 2. KPI Cards
  DOM.kpiCltv.textContent = formatCurrency(m.cltv_total);
  DOM.kpiCltvBreakdown.textContent = `Vehicles: ${formatCurrency(m.cltv_vehicle_spend)} • Services: ${formatCurrency(m.cltv_service_spend)}`;

  const displayLoyaltyBalance = m.annual_loyalty_balance != null ? m.annual_loyalty_balance : m.loyalty_points_balance;
  DOM.kpiLoyaltyBalance.textContent = `${formatNumber(displayLoyaltyBalance)} pts`;
  DOM.kpiLoyaltySub.textContent = `${formatNumber(m.annual_visit_points || 0)} visit • ${formatNumber(m.annual_birthday_points || 0)} bday pts`;

  DOM.kpiVehiclesCount.textContent = formatNumber(m.total_vehicles_count);
  const primaryV = data.vehicles.find((v) => v.is_primary) || data.vehicles[0];
  DOM.kpiPrimaryVehicle.textContent = primaryV ? `Primary: ${primaryV.year} ${primaryV.make} ${primaryV.model}` : "No vehicles";

  DOM.kpiServiceVisits.textContent = `${m.total_services_count} visit${m.total_services_count === 1 ? "" : "s"}`;
  DOM.kpiServiceCost.textContent = `${formatCurrency(m.total_service_cost)} total spend`;

  DOM.kpiTransactionsCount.textContent = formatNumber(m.total_transactions_count);
  DOM.kpiTxSub.textContent = `${m.completed_transactions_count} completed transactions`;

  DOM.kpiRating.textContent = m.average_rating != null ? `${m.average_rating} ★` : "No ratings";
  DOM.kpiReviewsCount.textContent = `${m.total_reviews_count} review${m.total_reviews_count === 1 ? "" : "s"} submitted`;

  // 3. Tab Badges
  DOM.vehiclesTabBadge.textContent = data.vehicles.length;
  DOM.servicesTabBadge.textContent = data.service_visits.length;
  DOM.transactionsTabBadge.textContent = data.transactions.length;
  DOM.loyaltyTabBadge.textContent = data.loyalty_events.length;
  DOM.reviewsTabBadge.textContent = data.reviews.length;

  // 4. Render Details in Tabs
  renderVehiclesTab(data.vehicles);
  renderServicesTab(data.service_visits);
  renderTransactionsTab(data.transactions);
  renderLoyaltyTab(data.loyalty_events);
  renderReviewsTab(data.reviews);

  // 5. Reset & Initialize AI Assistant Chat
  initializeAgentForCustomer(c);

  // Display Customer 360 Profile
  DOM.loadingState.style.display = "none";
  DOM.emptyState.style.display = "none";
  DOM.customerProfileView.style.display = "flex";
}

// ==========================================================================
// Detail Tab Renderers
// ==========================================================================

function renderVehiclesTab(vehicles) {
  DOM.vehiclesList.innerHTML = "";
  if (!vehicles || vehicles.length === 0) {
    DOM.vehiclesList.innerHTML = `<div style="color: var(--text-dim); padding: 1rem;">No vehicles registered for this customer.</div>`;
    return;
  }

  vehicles.forEach((v) => {
    const card = document.createElement("div");
    card.className = "vehicle-card";
    card.innerHTML = `
      <div class="vehicle-card-header">
        <div class="vehicle-card-title">
          <h4>${v.year} ${v.make} ${v.model}</h4>
          <span>${v.trim || "Base"} • ${v.body_style || "Vehicle"}</span>
        </div>
        ${v.is_primary ? `<span class="badge badge-primary">Primary</span>` : ""}
      </div>
      <div class="vehicle-vin-badge">VIN: ${v.vin}</div>
      <div class="vehicle-specs-grid">
        <div class="spec-item"><span class="spec-label">Fuel Type</span><span class="spec-value">${v.fuel_type || "Gasoline"}</span></div>
        <div class="spec-item"><span class="spec-label">Transmission</span><span class="spec-value">${v.transmission || "Automatic"}</span></div>
        <div class="spec-item"><span class="spec-label">Engine</span><span class="spec-value">${v.engine || "Standard"}</span></div>
        <div class="spec-item"><span class="spec-label">Current Mileage</span><span class="spec-value">${v.current_mileage != null ? `${formatNumber(v.current_mileage)} mi` : "N/A"}</span></div>
        <div class="spec-item"><span class="spec-label">Purchased</span><span class="spec-value">${formatDate(v.purchase_date)}</span></div>
        <div class="spec-item"><span class="spec-label">Purchase Price</span><span class="spec-value">${formatCurrency(v.purchase_price)}</span></div>
      </div>
      <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: auto; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.5rem;">
        🔧 ${v.service_visits_count} maintenance visit${v.service_visits_count === 1 ? "" : "s"} on record
      </div>
    `;
    DOM.vehiclesList.appendChild(card);
  });
}

function renderServicesTab(services) {
  DOM.servicesTableBody.innerHTML = "";
  if (!services || services.length === 0) {
    DOM.servicesTableBody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-dim); padding: 1.5rem;">No service history records found.</td></tr>`;
    return;
  }

  services.forEach((sv) => {
    const mainTr = document.createElement("tr");
    mainTr.className = "service-row";
    mainTr.id = `sv-row-${sv.id}`;
    const statusBadge = (sv.service_status || "completed").toLowerCase() === "completed" ? "badge-success" : "badge-warning";
    const odometer = sv.odometer_reading != null ? sv.odometer_reading : sv.mileage_at_service;

    mainTr.innerHTML = `
      <td class="cell-mono">
        <strong>#${sv.id}</strong><br>
        <small style="color: var(--text-dim);">${formatDate(sv.service_date)}</small>
      </td>
      <td>
        <strong>${sv.vehicle_info || "Vehicle"}</strong><br>
        <small class="cell-mono" style="color: var(--text-dim);">${sv.vehicle_vin || ""}</small>
      </td>
      <td><span class="badge badge-info">${sv.service_type.replace(/_/g, " ")}</span></td>
      <td><span class="badge ${statusBadge}">${sv.service_status || "completed"}</span></td>
      <td class="cell-amount"><strong>${formatCurrency(sv.cost)}</strong></td>
      <td>${sv.dealer_name || "Authorized Dealer"}</td>
      <td class="cell-mono">${odometer != null ? `${formatNumber(odometer)} km/mi` : "—"}</td>
      <td>${sv.is_warranty ? `<span class="badge badge-success">Warranty</span>` : `<span style="color: var(--text-dim);">Standard</span>`}</td>
      <td>
        <button type="button" class="service-expand-btn" data-svid="${sv.id}" title="Toggle detailed service breakdown">
          <span>Details</span> <span class="arrow-icon">▾</span>
        </button>
      </td>
    `;

    // Detail Tray Row
    const detailTr = document.createElement("tr");
    detailTr.id = `sv-detail-${sv.id}`;
    detailTr.className = "service-detail-row";
    detailTr.style.display = "none";

    detailTr.innerHTML = `
      <td colspan="9">
        <div class="service-detail-tray">
          <div class="service-detail-grid">
            <!-- Card 1: Customer Complaint & Diagnosis -->
            <div class="service-detail-card">
              <h5>⚠️ Customer Complaint</h5>
              <p style="margin-bottom: 0.6rem;">${sv.customer_complaint || "Not provided"}</p>
              <h5>🔍 Diagnostic Finding</h5>
              <p>${sv.diagnosis || "Not provided"}</p>
            </div>

            <!-- Card 2: Work Performed & Technician Notes -->
            <div class="service-detail-card">
              <h5>🛠️ Work Performed</h5>
              <p style="margin-bottom: 0.6rem;">${sv.work_performed || sv.service_description || sv.description || "Not provided"}</p>
              <h5>📝 Technician Notes</h5>
              <p>${sv.technician_notes || "None noted"}</p>
            </div>

            <!-- Card 3: Financial Breakdown (INR) & Scheduling -->
            <div class="service-detail-card">
              <h5>💰 Cost Breakdown (INR)</h5>
              <div class="cost-breakdown-row">
                <span>Parts Cost:</span>
                <span>${sv.parts_cost != null ? formatCurrency(sv.parts_cost) : "Not provided"}</span>
              </div>
              <div class="cost-breakdown-row">
                <span>Labour Cost:</span>
                <span>${sv.labour_cost != null ? formatCurrency(sv.labour_cost) : "Not provided"}</span>
              </div>
              <div class="cost-breakdown-row total">
                <span>Total Service Cost:</span>
                <span>${formatCurrency(sv.cost)}</span>
              </div>
              <div style="margin-top: 0.6rem;">
                <h5 style="margin-bottom: 0.2rem;">📅 Recommended Next Service</h5>
                <p style="font-family: var(--font-mono); font-size: 0.8125rem; color: var(--accent-cyan);">${sv.next_service_date ? formatDate(sv.next_service_date) : "Not scheduled"}</p>
              </div>
            </div>
          </div>
        </div>
      </td>
    `;

    DOM.servicesTableBody.appendChild(mainTr);
    DOM.servicesTableBody.appendChild(detailTr);
  });

  // Attach accordion toggle events
  DOM.servicesTableBody.querySelectorAll(".service-expand-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const svId = btn.getAttribute("data-svid");
      const detailRow = document.getElementById(`sv-detail-${svId}`);
      const arrow = btn.querySelector(".arrow-icon");
      if (detailRow.style.display === "none") {
        detailRow.style.display = "table-row";
        arrow.textContent = "▴";
        btn.classList.add("expanded");
      } else {
        detailRow.style.display = "none";
        arrow.textContent = "▾";
        btn.classList.remove("expanded");
      }
    });
  });
}

function renderTransactionsTab(transactions) {
  DOM.transactionsTableBody.innerHTML = "";
  if (!transactions || transactions.length === 0) {
    DOM.transactionsTableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-dim); padding: 1.5rem;">No transaction records found.</td></tr>`;
    return;
  }

  transactions.forEach((tx) => {
    let statusBadge = "badge-success";
    if (tx.status === "pending") statusBadge = "badge-warning";
    if (tx.status === "refunded") statusBadge = "badge-danger";

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="cell-mono"><strong>${tx.reference_number || `TXN#${tx.id}`}</strong></td>
      <td class="cell-mono">${formatDate(tx.transaction_date)}</td>
      <td><span class="badge badge-primary">${tx.transaction_type.replace("_", " ")}</span></td>
      <td class="cell-amount"><strong>${formatCurrency(tx.amount)}</strong></td>
      <td><span class="badge ${statusBadge}">${tx.status}</span></td>
      <td style="text-transform: capitalize;">${tx.payment_method || "—"}</td>
      <td>${tx.dealer_name || "Dealership"}</td>
      <td>${tx.vehicle_info || "—"}</td>
    `;
    DOM.transactionsTableBody.appendChild(tr);
  });
}

function renderLoyaltyTab(loyaltyEvents) {
  // Update 2026 Annual Dashboard
  if (currentCustomer360 && currentCustomer360.metrics) {
    const m = currentCustomer360.metrics;
    if (DOM.loyalty2026Balance) DOM.loyalty2026Balance.textContent = `${formatNumber(m.annual_loyalty_balance || 0)} pts`;
    if (DOM.loyalty2026VisitPts) DOM.loyalty2026VisitPts.textContent = `${formatNumber(m.annual_visit_points || 0)} pts`;
    if (DOM.loyalty2026VisitsSub) DOM.loyalty2026VisitsSub.textContent = `${m.qualifying_visits_2026_count || 0} qualifying visit(s)`;
    if (DOM.loyalty2026BdayPts) DOM.loyalty2026BdayPts.textContent = `${formatNumber(m.annual_birthday_points || 0)} pts`;
    if (DOM.loyalty2026BdaySub) DOM.loyalty2026BdaySub.textContent = m.has_birthday_bonus ? "Awarded (+500 pts)" : "Not awarded / Ineligible";
    if (DOM.loyalty2026RedeemedPts) DOM.loyalty2026RedeemedPts.textContent = `${formatNumber(m.annual_redeemed_points || 0)} pts`;
  }

  DOM.loyaltyTimeline.innerHTML = "";
  if (!loyaltyEvents || loyaltyEvents.length === 0) {
    DOM.loyaltyTimeline.innerHTML = `<div style="color: var(--text-dim); padding: 1rem;">No loyalty events on record.</div>`;
    return;
  }

  loyaltyEvents.forEach((le) => {
    const isPositive = le.points > 0;
    const is2026 = le.program_year === 2026 || (le.event_date && le.event_date.startsWith("2026"));
    const item = document.createElement("div");
    item.className = "loyalty-event-row";
    item.innerHTML = `
      <div class="loyalty-event-main">
        <div class="event-icon ${le.event_type}">
          ${le.event_type === "birthday_bonus" ? "🎂" : le.event_type === "visit_reward" ? "🚗" : le.event_type === "earn" ? "★" : le.event_type === "redeem" ? "↓" : "✦"}
        </div>
        <div class="loyalty-event-details">
          <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
            <h5 style="margin: 0;">${le.description || `${le.event_type.toUpperCase()} Points`}</h5>
            ${is2026 ? `<span class="badge badge-success" style="font-size: 0.65rem;">2026 Program</span>` : `<span class="badge" style="font-size: 0.65rem; background: rgba(255,255,255,0.06); color: var(--text-dim);">Historical</span>`}
          </div>
          <p style="margin-top: 0.25rem;">${formatDate(le.event_date)} • ${le.related_transaction_ref ? `Ref: ${le.related_transaction_ref}` : le.service_visit_id ? `Service Visit #${le.service_visit_id}` : "Annual Policy"}</p>
        </div>
      </div>
      <div class="loyalty-event-points">
        <div class="points-delta ${isPositive ? "positive" : "negative"}">
          ${isPositive ? `+${formatNumber(le.points)}` : `${formatNumber(le.points)}`} pts
        </div>
        <div class="balance-after">Balance: ${formatNumber(le.balance_after)} pts</div>
      </div>
    `;
    DOM.loyaltyTimeline.appendChild(item);
  });
}

function renderReviewsTab(reviews) {
  DOM.reviewsList.innerHTML = "";
  if (!reviews || reviews.length === 0) {
    DOM.reviewsList.innerHTML = `<div style="color: var(--text-dim); padding: 1rem;">No customer reviews submitted.</div>`;
    return;
  }

  reviews.forEach((r) => {
    const stars = "★".repeat(r.rating) + "☆".repeat(5 - r.rating);
    const card = document.createElement("div");
    card.className = "review-card";
    card.innerHTML = `
      <div class="review-card-header">
        <div class="star-rating">${stars} (${r.rating}/5)</div>
        <span class="badge badge-info">${r.review_type} review</span>
      </div>
      <div class="review-title">${r.title || "Customer Feedback"}</div>
      <div class="review-body">${r.body || "No feedback text provided."}</div>
      <div class="review-footer">
        <span>Reviewed on ${formatDate(r.review_date)} ${r.dealer_name ? `• ${r.dealer_name}` : ""}</span>
        ${r.is_verified ? `<span class="badge badge-success" style="font-size: 0.625rem;">Verified Customer</span>` : ""}
      </div>
    `;
    DOM.reviewsList.appendChild(card);
  });
}

// ==========================================================================
// AI Customer Insights Assistant
// ==========================================================================

function initializeAgentForCustomer(customer) {
  DOM.agentTargetCustomerName.textContent = customer.full_name;
  DOM.agentChatHistory.innerHTML = `
    <div class="agent-welcome-message">
      <p>Hello! I am your <strong>AutoInsight360 Intelligence Agent</strong>. Ask me any question about <strong>${customer.full_name}</strong>.</p>
      <p class="agent-guardrail-note">🔒 All answers are strictly grounded in verified database records with cited record IDs. No arbitrary SQL or hallucinated data.</p>
    </div>
  `;
  DOM.agentQuestionInput.value = "";
  DOM.charCount.textContent = "0";
}

async function submitAgentQuestion(questionText) {
  const question = (questionText || DOM.agentQuestionInput.value).trim();
  if (!question) return;

  if (!state.activeCustomerId) {
    showAlert("Please select a customer first.");
    return;
  }

  if (state.isAgentLoading) return;

  // Append user bubble
  appendChatBubble(question, "user");
  DOM.agentQuestionInput.value = "";
  DOM.charCount.textContent = "0";

  // Loading state
  state.isAgentLoading = true;
  DOM.agentLoading.style.display = "flex";
  DOM.agentSubmitBtn.disabled = true;

  try {
    const res = await fetch("/api/agent/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_id: state.activeCustomerId,
        question: question,
      }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Agent query returned status ${res.status}`);
    }

    const data = await res.json();
    appendAgentAnswerBubble(data);
  } catch (err) {
    console.error("AI Agent query failed:", err);
    appendChatBubble(
      `⚠️ Error executing intelligence query: ${err.message}. Please verify the Ollama local model service is active.`,
      "agent",
      []
    );
  } finally {
    state.isAgentLoading = false;
    DOM.agentLoading.style.display = "none";
    DOM.agentSubmitBtn.disabled = false;
  }
}

function appendChatBubble(text, role) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;
  bubble.textContent = text;
  DOM.agentChatHistory.appendChild(bubble);
  DOM.agentChatHistory.scrollTop = DOM.agentChatHistory.scrollHeight;
}

function appendAgentAnswerBubble(agentResponse) {
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble agent";

  // Format basic markdown bolding & newlines
  const formattedHtml = agentResponse.answer
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n\n/g, "<br><br>")
    .replace(/\n- /g, "<br>• ");

  let evidenceBadgesHtml = "";
  if (agentResponse.evidence_records && agentResponse.evidence_records.length > 0) {
    const badges = agentResponse.evidence_records
      .map((rec) => `<span class="evidence-pill">${rec}</span>`)
      .join(" ");
    evidenceBadgesHtml = `
      <div class="agent-evidence-block">
        <div class="evidence-title">Verified Database Evidence Cited:</div>
        <div class="evidence-badges">${badges}</div>
      </div>
    `;
  }

  bubble.innerHTML = `
    <div>${formattedHtml}</div>
    ${evidenceBadgesHtml}
    <div style="font-size: 0.625rem; color: var(--text-dim); margin-top: 0.5rem; text-align: right;">
      Model: ${agentResponse.model} • Grounded Output
    </div>
  `;

  DOM.agentChatHistory.appendChild(bubble);
  DOM.agentChatHistory.scrollTop = DOM.agentChatHistory.scrollHeight;
}

// ==========================================================================
// Dynamic Automotive Data Ingestion (Import Modal)
// ==========================================================================

function openImportModal() {
  DOM.importModal.style.display = "flex";
  checkSystemHealth();
}

function closeImportModal() {
  DOM.importModal.style.display = "none";
  resetImportState();
}

function resetImportState() {
  state.selectedZipFile = null;
  state.activeImportSessionId = null;
  state.isImporting = false;

  DOM.zipFileInput.value = "";
  DOM.uploadZoneContent.style.display = "block";
  DOM.selectedFileInfo.style.display = "none";
  DOM.previewImportBtn.disabled = true;
  DOM.previewResultsContainer.style.display = "none";
  DOM.importSuccessBox.style.display = "none";
  DOM.importSpinner.style.display = "none";
  DOM.commitImportBtn.disabled = true;
  DOM.previewTableBody.innerHTML = "";
  DOM.previewIssuesList.innerHTML = "";
  DOM.previewIssuesBox.style.display = "none";
}

function handleZipFileSelect(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".zip")) {
    showAlert("Please select a valid .ZIP archive containing canonical CSV files.", "error");
    return;
  }
  if (file.size > 15 * 1024 * 1024) {
    showAlert("File size exceeds 15MB limit.", "error");
    return;
  }

  state.selectedZipFile = file;
  DOM.selectedFileName.textContent = file.name;
  DOM.selectedFileSize.textContent = (file.size / 1024).toFixed(1) + " KB";

  DOM.uploadZoneContent.style.display = "none";
  DOM.selectedFileInfo.style.display = "flex";
  DOM.previewImportBtn.disabled = false;
  DOM.previewResultsContainer.style.display = "none";
  DOM.importSuccessBox.style.display = "none";
}

async function executePreviewImport() {
  if (!state.selectedZipFile) return;

  state.isImporting = true;
  DOM.previewImportBtn.disabled = true;
  DOM.importSpinner.style.display = "inline-block";

  try {
    const formData = new FormData();
    formData.append("file", state.selectedZipFile);

    const res = await fetch("/api/import/preview", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Validation failed during preview");
    }

    state.activeImportSessionId = data.session_id;

    // Render Preview
    DOM.previewResultsContainer.style.display = "flex";
    DOM.previewStatusTitle.textContent = data.message;

    DOM.badgeAcceptedCount.textContent = `${data.total_accepted_rows} Accepted`;
    if (data.total_rejected_rows > 0) {
      DOM.badgeRejectedCount.style.display = "inline-block";
      DOM.badgeRejectedCount.textContent = `${data.total_rejected_rows} Rejected`;
    } else {
      DOM.badgeRejectedCount.style.display = "none";
    }

    // Populate Entity Summary Table
    DOM.previewTableBody.innerHTML = "";
    data.summary.forEach((s) => {
      const tr = document.createElement("tr");
      const statusBadge = s.rejected_rows === 0 
        ? `<span class="badge-pill badge-success">Valid</span>`
        : `<span class="badge-pill badge-danger">${s.rejected_rows} Error(s)</span>`;
      tr.innerHTML = `
        <td><strong>${s.entity}</strong></td>
        <td><code>${s.file_name}</code></td>
        <td>${s.total_rows}</td>
        <td>${s.accepted_rows}</td>
        <td>${s.rejected_rows}</td>
        <td>${statusBadge}</td>
      `;
      DOM.previewTableBody.appendChild(tr);
    });

    // Populate Issues List
    if (data.issues && data.issues.length > 0) {
      DOM.previewIssuesBox.style.display = "block";
      DOM.previewIssuesList.innerHTML = "";
      data.issues.forEach((iss) => {
        const li = document.createElement("li");
        li.className = iss.severity === "error" ? "error-item" : "warning-item";
        const rowTag = iss.row ? ` [Row ${iss.row}]` : "";
        li.textContent = `[${iss.severity.toUpperCase()}] ${iss.file}${rowTag}: ${iss.message}`;
        DOM.previewIssuesList.appendChild(li);
      });
    } else {
      DOM.previewIssuesBox.style.display = "none";
    }

    // Enable / Disable Commit Button
    DOM.commitImportBtn.disabled = !data.can_commit;
  } catch (err) {
    showAlert(err.message, "error");
  } finally {
    state.isImporting = false;
    DOM.previewImportBtn.disabled = false;
    DOM.importSpinner.style.display = "none";
  }
}

async function executeCommitImport() {
  if (!state.activeImportSessionId) return;

  DOM.commitImportBtn.disabled = true;
  DOM.importSpinner.style.display = "inline-block";

  try {
    const res = await fetch("/api/import/commit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.activeImportSessionId }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to commit import.");
    }

    // Render Success Box
    DOM.previewResultsContainer.style.display = "none";
    DOM.importSuccessBox.style.display = "flex";
    DOM.importSuccessMessage.textContent = data.message;

    // Render Chips
    DOM.importSuccessCounts.innerHTML = "";
    for (const [entity, count] of Object.entries(data.imported_counts)) {
      if (count > 0) {
        const chip = document.createElement("span");
        chip.className = "success-chip";
        chip.textContent = `+${count} ${entity}`;
        DOM.importSuccessCounts.appendChild(chip);
      }
    }

    // Refresh health and reload initial demo list & search dropdown
    await checkSystemHealth();
    await loadInitialCustomers();
    showAlert("Dataset successfully committed to SQLite database!", "success");
  } catch (err) {
    showAlert(err.message, "error");
    DOM.commitImportBtn.disabled = false;
  } finally {
    DOM.importSpinner.style.display = "none";
  }
}

// ==========================================================================
// Event Listeners
// ==========================================================================

function bindEventListeners() {
  // Search Events
  DOM.searchBtn.addEventListener("click", performSearch);
  DOM.searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      performSearch();
    }
  });

  DOM.searchInput.addEventListener("input", (e) => {
    DOM.clearSearchBtn.style.display = e.target.value ? "block" : "none";
  });

  DOM.clearSearchBtn.addEventListener("click", () => {
    DOM.searchInput.value = "";
    DOM.clearSearchBtn.style.display = "none";
    DOM.searchResultsContainer.style.display = "none";
  });

  DOM.closeSearchResultsBtn.addEventListener("click", () => {
    DOM.searchResultsContainer.style.display = "none";
  });

  // Quick Select Dropdown
  DOM.quickSelectDropdown.addEventListener("change", (e) => {
    const custId = e.target.value;
    if (custId) {
      loadCustomer360(parseInt(custId, 10));
    }
  });

  // Alert Banner Close
  DOM.closeAlertBtn.addEventListener("click", () => {
    DOM.alertBanner.style.display = "none";
  });

  // Tabs Switching
  DOM.tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetTabId = btn.getAttribute("data-tab");

      DOM.tabButtons.forEach((b) => b.classList.remove("active"));
      DOM.tabPanes.forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPane = document.getElementById(targetTabId);
      if (targetPane) targetPane.classList.add("active");
    });
  });

  // AI Agent Form Submit
  DOM.agentQueryForm.addEventListener("submit", (e) => {
    e.preventDefault();
    submitAgentQuestion();
  });

  // AI Agent Input Character Counter & Enter Key
  DOM.agentQuestionInput.addEventListener("input", (e) => {
    DOM.charCount.textContent = e.target.value.length;
  });

  DOM.agentQuestionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitAgentQuestion();
    }
  });

  // AI Agent Quick Prompt Chips
  DOM.promptChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const q = chip.getAttribute("data-question");
      if (q) {
        submitAgentQuestion(q);
      }
    });
  });

  // Import Modal Events
  if (DOM.openImportModalBtn) {
    DOM.openImportModalBtn.addEventListener("click", openImportModal);
  }
  if (DOM.closeImportModalBtn) {
    DOM.closeImportModalBtn.addEventListener("click", closeImportModal);
  }
  if (DOM.cancelPreviewBtn) {
    DOM.cancelPreviewBtn.addEventListener("click", resetImportState);
  }

  // Upload Zone & Drag-Drop Events
  if (DOM.uploadZone) {
    DOM.uploadZone.addEventListener("click", (e) => {
      if (e.target !== DOM.removeFileBtn && !DOM.removeFileBtn?.contains(e.target)) {
        DOM.zipFileInput.click();
      }
    });

    DOM.uploadZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      DOM.uploadZone.classList.add("dragover");
    });

    DOM.uploadZone.addEventListener("dragleave", () => {
      DOM.uploadZone.classList.remove("dragover");
    });

    DOM.uploadZone.addEventListener("drop", (e) => {
      e.preventDefault();
      DOM.uploadZone.classList.remove("dragover");
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleZipFileSelect(e.dataTransfer.files[0]);
      }
    });
  }

  if (DOM.zipFileInput) {
    DOM.zipFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleZipFileSelect(e.target.files[0]);
      }
    });
  }

  if (DOM.removeFileBtn) {
    DOM.removeFileBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      resetImportState();
    });
  }

  if (DOM.previewImportBtn) {
    DOM.previewImportBtn.addEventListener("click", executePreviewImport);
  }

  if (DOM.commitImportBtn) {
    DOM.commitImportBtn.addEventListener("click", executeCommitImport);
  }

  // 2026 Points Redemption Modal Events
  if (DOM.openRedeemModalBtn) {
    DOM.openRedeemModalBtn.addEventListener("click", openRedeemModal);
  }
  if (DOM.closeRedeemModalBtn) {
    DOM.closeRedeemModalBtn.addEventListener("click", closeRedeemModal);
  }
  if (DOM.cancelRedeemBtn) {
    DOM.cancelRedeemBtn.addEventListener("click", closeRedeemModal);
  }
  if (DOM.confirmRedeemBtn) {
    DOM.confirmRedeemBtn.addEventListener("click", executePointsRedemption);
  }

  // Quick chips for redemption
  document.querySelectorAll(".quick-redeem-chips .chip-btn").forEach((chip) => {
    chip.addEventListener("click", () => {
      const p = chip.getAttribute("data-pts");
      const available = currentCustomer360?.metrics?.annual_loyalty_balance || 0;
      if (p === "max") {
        if (DOM.redeemPointsInput) DOM.redeemPointsInput.value = available;
      } else {
        const val = parseInt(p, 10);
        if (!isNaN(val) && DOM.redeemPointsInput) {
          DOM.redeemPointsInput.value = Math.min(val, available);
        }
      }
    });
  });
}

// ==========================================================================
// Points Redemption Logic
// ==========================================================================

function openRedeemModal() {
  if (!currentCustomer360 || !currentCustomer360.customer) {
    showAlert("Please search and select a customer before redeeming points.", "warning");
    return;
  }
  const available = currentCustomer360.metrics?.annual_loyalty_balance || 0;
  if (DOM.modalAvailablePts) {
    DOM.modalAvailablePts.textContent = `${formatNumber(available)} pts`;
  }
  if (DOM.redeemPointsInput) {
    DOM.redeemPointsInput.value = "";
    DOM.redeemPointsInput.max = available;
  }
  if (DOM.redeemNotesInput) {
    DOM.redeemNotesInput.value = "";
  }
  if (DOM.redeemErrorMsg) {
    DOM.redeemErrorMsg.style.display = "none";
    DOM.redeemErrorMsg.textContent = "";
  }
  if (DOM.redeemSuccessMsg) {
    DOM.redeemSuccessMsg.style.display = "none";
    DOM.redeemSuccessMsg.textContent = "";
  }
  if (DOM.confirmRedeemBtn) {
    DOM.confirmRedeemBtn.disabled = false;
    DOM.confirmRedeemBtn.textContent = "Confirm Redemption";
  }
  if (DOM.redeemModal) {
    DOM.redeemModal.style.display = "flex";
  }
}

function closeRedeemModal() {
  if (DOM.redeemModal) {
    DOM.redeemModal.style.display = "none";
  }
}

async function executePointsRedemption() {
  if (!currentCustomer360 || !currentCustomer360.customer) return;

  const ptsVal = parseInt(DOM.redeemPointsInput?.value, 10);
  const notesVal = DOM.redeemNotesInput?.value.trim() || "";
  const available = currentCustomer360.metrics?.annual_loyalty_balance || 0;

  if (isNaN(ptsVal) || ptsVal <= 0) {
    showRedeemError("Please enter a valid points amount greater than zero.");
    return;
  }

  if (ptsVal > available) {
    showRedeemError(`Redemption amount (${formatNumber(ptsVal)} pts) exceeds available 2026 balance (${formatNumber(available)} pts).`);
    return;
  }

  try {
    if (DOM.confirmRedeemBtn) {
      DOM.confirmRedeemBtn.disabled = true;
      DOM.confirmRedeemBtn.textContent = "Processing...";
    }

    const resp = await fetch(`/api/customers/${currentCustomer360.customer.id}/loyalty/redeem`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount: ptsVal, notes: notesVal }),
    });

    const data = await resp.json();

    if (!resp.ok) {
      throw new Error(data.detail || "Redemption request failed.");
    }

    if (DOM.redeemSuccessMsg) {
      DOM.redeemSuccessMsg.textContent = `✓ ${data.message || `Successfully redeemed ${formatNumber(ptsVal)} points.`}`;
      DOM.redeemSuccessMsg.style.display = "block";
    }
    if (DOM.redeemErrorMsg) DOM.redeemErrorMsg.style.display = "none";

    // Refresh profile in background and notify
    setTimeout(async () => {
      closeRedeemModal();
      await loadCustomer360(currentCustomer360.customer.id);
      showAlert(`Redeemed ${formatNumber(ptsVal)} loyalty points successfully.`, "success");
    }, 1200);

  } catch (err) {
    showRedeemError(err.message || "Failed to process redemption.");
  } finally {
    if (DOM.confirmRedeemBtn) {
      DOM.confirmRedeemBtn.disabled = false;
      DOM.confirmRedeemBtn.textContent = "Confirm Redemption";
    }
  }
}

function showRedeemError(msg) {
  if (DOM.redeemErrorMsg) {
    DOM.redeemErrorMsg.textContent = msg;
    DOM.redeemErrorMsg.style.display = "block";
  }
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", initApp);
