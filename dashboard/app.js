/* El Paso County Distress Intelligence — dashboard logic.
   Single-source build (clerk_recordings); the signal model is open-ended
   so later sessions add tax_collector / court_* signals with no redesign.
   Filter counts and the rendered table both come from applyFilters() —
   the Two-Truths invariant. */
(function () {
  "use strict";

  var DATA = (typeof window !== "undefined" && window.LEADS) || null;
  var records = [];
  var els = {};

  function $(id) { return document.getElementById(id); }
  function fmtMoney(v) {
    if (v === null || v === undefined || v === "") return "—";
    var n = Number(v);
    return isNaN(n) ? "—" : "$" + n.toLocaleString("en-US");
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function boot(payload) {
    records = (payload && payload.records) || [];
    els = {
      buildMeta: $("buildMeta"), banner: $("banner"), body: $("leadBody"),
      rowCount: $("rowCount"), empty: $("emptyMsg"),
      search: $("searchBox"), signalFilter: $("signalFilter"),
      ownerFilter: $("ownerFilter"), absentee: $("absenteeTog"),
      oos: $("oosTog"), stack: $("stackMode"), sort: $("sortMode"),
      csv: $("csvBtn"), reset: $("resetBtn")
    };

    els.buildMeta.textContent =
      (payload.county || "") + " County · generated " +
      (payload.generated_at || "") + " · " + records.length + " leads";
    if (payload.build_label && payload.build_label !== "FULL_BUILD") {
      els.banner.textContent = "PARTIAL LEAD BOARD (" + payload.build_label +
        ") — " + (payload.build_label_reason || "") +
        " Enrichment attached only to verified clerk distress events. " +
        "Not full county coverage.";
    }

    buildSignalFilter();
    buildOwnerFilter();
    ["change", "keyup"].forEach(function (ev) {
      els.search.addEventListener(ev, render);
    });
    [els.absentee, els.oos, els.stack, els.sort].forEach(function (e) {
      e.addEventListener("change", render);
    });
    els.csv.addEventListener("click", exportCsv);
    els.reset.addEventListener("click", function () {
      els.search.value = ""; els.absentee.checked = false;
      els.oos.checked = false; els.stack.value = "any"; els.sort.value = "signals";
      checks(els.signalFilter, true); checks(els.ownerFilter, true); render();
    });

    render();
    document.documentElement.setAttribute("data-ready", "1");
  }

  function checks(container, on) {
    container.querySelectorAll("input[type=checkbox]").forEach(function (c) {
      c.checked = on;
    });
  }

  function buildSignalFilter() {
    var set = {};
    records.forEach(function (r) {
      (r.signal_types || []).forEach(function (t) { set[t] = true; });
    });
    var labelByType = {};
    records.forEach(function (r) {
      (r.signals || []).forEach(function (s) { labelByType[s.signal_type] = s.signal_label; });
    });
    Object.keys(set).sort().forEach(function (t) {
      var id = "sig_" + t;
      var l = document.createElement("label");
      l.innerHTML = '<input type="checkbox" value="' + esc(t) + '" id="' +
        id + '" checked> ' + esc(labelByType[t] || t);
      l.querySelector("input").addEventListener("change", render);
      els.signalFilter.appendChild(l);
    });
  }

  function buildOwnerFilter() {
    var set = {};
    records.forEach(function (r) { set[r.owner_type || "UNKNOWN"] = true; });
    Object.keys(set).sort().forEach(function (t) {
      var l = document.createElement("label");
      l.innerHTML = '<input type="checkbox" value="' + esc(t) +
        '" checked> ' + esc(t);
      l.querySelector("input").addEventListener("change", render);
      els.ownerFilter.appendChild(l);
    });
  }

  function selectedValues(container) {
    var out = [];
    container.querySelectorAll("input[type=checkbox]:checked").forEach(function (c) {
      out.push(c.value);
    });
    return out;
  }

  function applyFilters() {
    var q = els.search.value.trim().toLowerCase();
    var sigSel = selectedValues(els.signalFilter);
    var ownerSel = selectedValues(els.ownerFilter);
    var stackMode = els.stack.value;
    var sigAll = els.signalFilter.querySelectorAll("input").length;

    return records.filter(function (r) {
      var types = r.signal_types || [];
      // signal-type filter
      if (sigSel.length < sigAll) {
        var hit = types.some(function (t) { return sigSel.indexOf(t) >= 0; });
        if (!hit) return false;
      }
      // owner-type filter
      if (ownerSel.indexOf(r.owner_type || "UNKNOWN") < 0) return false;
      // enrichment toggles
      if (els.absentee.checked && !r.absentee_owner_flag) return false;
      if (els.oos.checked && !r.out_of_state_owner_flag) return false;
      // stacking
      var n = r.signal_count || (r.signals || []).length;
      if (stackMode === "2" && n < 2) return false;
      if (stackMode === "3" && n < 3) return false;
      if (stackMode === "all" && sigSel.length < sigAll) {
        var hasAll = sigSel.every(function (t) { return types.indexOf(t) >= 0; });
        if (!hasAll) return false;
      }
      // text search
      if (q) {
        var hay = (r.owner_name + " " + r.property_full_address + " " +
          r.mailing_full_address + " " + r.legal_description).toLowerCase();
        if (hay.indexOf(q) < 0) return false;
      }
      return true;
    });
  }

  function sortRows(rows) {
    var mode = els.sort.value;
    var c = rows.slice();
    c.sort(function (a, b) {
      if (mode === "signals") return (b.signal_count || 0) - (a.signal_count || 0);
      if (mode === "value") return (Number(b.assessed_value) || 0) - (Number(a.assessed_value) || 0);
      if (mode === "date") return (b.latest_event_date || "").localeCompare(a.latest_event_date || "");
      if (mode === "owner") return (a.owner_name || "").localeCompare(b.owner_name || "");
      return 0;
    });
    return c;
  }

  function chipsHtml(r) {
    return (r.signals || []).map(function (s) {
      return '<span class="chip chip-distress" data-sig="' + esc(s.signal_type) +
        '" title="' + esc(s.doc_type_raw || s.signal_label) + " " +
        esc(s.recorded_date || "") + '">' + esc(s.signal_label) + "</span>";
    }).join("");
  }

  function badgesHtml(r) {
    var b = [];
    b.push('<span class="badge owner-type">' + esc(r.owner_type || "UNKNOWN") + "</span>");
    if (r.absentee_owner_flag) b.push('<span class="badge warn">Absentee</span>');
    if (r.out_of_state_owner_flag) b.push('<span class="badge warn">Out-of-state</span>');
    if (r.homestead === "HOMESTEAD") b.push('<span class="badge">Homestead</span>');
    if (r.homestead === "NO_HOMESTEAD") b.push('<span class="badge">No homestead</span>');
    return b.join("");
  }

  function render() {
    var rows = sortRows(applyFilters());
    els.rowCount.textContent = rows.length + " of " + records.length + " leads";
    els.body.innerHTML = "";
    els.empty.hidden = rows.length > 0;

    rows.forEach(function (r) {
      var unresolved = r.parcel_resolution_status !== "RESOLVED";
      var addr = unresolved
        ? '<span class="unresolved">Address unresolved — EPCAD no match</span>'
        : esc(r.property_full_address || "—");
      var proof = (r.source_urls || [])[0];
      var tr = document.createElement("tr");
      tr.innerHTML =
        '<td><span class="owner-name">' + esc(r.owner_name || "—") + "</span></td>" +
        "<td>" + addr + "</td>" +
        "<td>" + esc(r.mailing_full_address || "—") + "</td>" +
        '<td>' + chipsHtml(r) + "</td>" +
        "<td>" + badgesHtml(r) + "</td>" +
        '<td class="num">' + fmtMoney(r.assessed_value) + "</td>" +
        '<td class="num sigcount">' + (r.signal_count || 0) + "</td>" +
        "<td>" + (proof ? '<a class="proof-link" href="' + esc(proof) +
          '" target="_blank" rel="noopener">clerk record</a>' : "—") + "</td>";
      els.body.appendChild(tr);
    });
  }

  function exportCsv() {
    var rows = sortRows(applyFilters());
    var cols = ["owner_name", "owner_type", "property_full_address",
      "property_city", "property_state", "property_zip",
      "mailing_full_address", "mailing_city", "mailing_state",
      "assessed_value", "appraised_value", "homestead",
      "absentee_owner_flag", "out_of_state_owner_flag",
      "signal_count", "primary_signal", "latest_event_date",
      "parcel_id", "parcel_resolution_status", "legal_description"];
    var lines = [cols.join(",")];
    rows.forEach(function (r) {
      var rec = Object.assign({}, r);
      rec.signal_types_list = (r.signal_types || []).join("; ");
      var cells = cols.map(function (c) {
        var v = rec[c];
        if (v === null || v === undefined) v = "";
        v = String(v).replace(/"/g, '""');
        return '"' + v + '"';
      });
      cells.push('"' + (r.signal_types || []).join("; ") + '"');
      cells.push('"' + (r.source_urls || []).join(" ").replace(/"/g, '""') + '"');
      lines.push(cells.join(","));
    });
    lines[0] = cols.join(",") + ",signal_types,source_urls";
    var blob = new Blob([lines.join("\n")], { type: "text/csv" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "el_paso_clerk_recordings_leads.csv";
    document.body.appendChild(a); a.click(); a.remove();
  }

  function start() {
    if (DATA) { boot(DATA); return; }
    fetch("data.json").then(function (r) { return r.json(); })
      .then(boot)
      .catch(function (e) {
        document.getElementById("banner").textContent =
          "Could not load data (" + e + "). Open via data.js or a local server.";
        document.documentElement.setAttribute("data-ready", "1");
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else { start(); }
})();
