# ui_script.py (full, modified)
JS = r"""
  const stage = document.getElementById("stage");

  const viewHome = document.getElementById("view-home");
  const viewSingle = document.getElementById("view-single");
  const viewCsv = document.getElementById("view-csv");

  const goSingle = document.getElementById("go-single");
  const goCsv = document.getElementById("go-csv");

  const backBtn = document.getElementById("backBtn");
  const csvBackBtn = document.getElementById("csvBackBtn");

  const vramText = document.getElementById("vramText");
  const vramFill = document.getElementById("vramFill");

  const singleExcelFile = document.getElementById("singleExcelFile");
  const singleExcelName = document.getElementById("singleExcelName");
  const singleRunBtn = document.getElementById("singleRunBtn");
  const singleDownloadBtn = document.getElementById("singleDownloadBtn");
  const singleStatus = document.getElementById("singleStatus");
  const singleLog = document.getElementById("singleLog");
  const singleLogScroll = document.getElementById("singleLogScroll");

  const csvPanel = document.getElementById("csv-panel");
  const csvFile = document.getElementById("csvFile");
  const csvFileName = document.getElementById("csvFileName");
  const csvCol = document.getElementById("csvCol");
  const csvRunBtn = document.getElementById("csvRunBtn");
  const csvStatus = document.getElementById("csvStatus");

  const csvProgress = document.getElementById("csvProgress");
  const csvProgressFill = document.getElementById("csvProgressFill");
  const csvProgressStage = document.getElementById("csvProgressStage");

  function _fmtGb(x){
    if(x == null || !isFinite(x)) return "--";
    return Number(x).toFixed(1);
  }

  async function refreshVram(){
    if(!vramText) return;

    try{
      const resp = await fetch("/api/vram");
      if(!resp.ok) return;

      const d = await resp.json();
      if(!d || !d.available){
        vramText.textContent = "VRAM: --GB / --GB";
        if(vramFill) vramFill.style.width = "0%";
        return;
      }

      const used = _fmtGb(d.used_gb);
      const total = _fmtGb(d.total_gb);

      vramText.textContent = `VRAM: ${used}GB / ${total}GB`;

      const pct = Math.max(0, Math.min(100, Number(d.pct || 0)));
      if(vramFill) vramFill.style.width = pct.toFixed(0) + "%";
    }catch(_){}
  }

  setInterval(refreshVram, 800);
  refreshVram();
  const csvProgressPct = document.getElementById("csvProgressPct");

  const donutBox = document.getElementById("donutBox");
  const donutPlot = document.getElementById("donutPlot");
  const legend = document.getElementById("legend");

  const confBox = document.getElementById("confBox");
  const confPosPlot = document.getElementById("confPosPlot");
  const confGibPlot = document.getElementById("confGibPlot");
  const confNegPlot = document.getElementById("confNegPlot");

  const rightSplit = document.getElementById("rightSplit");

  const topicsBox = document.getElementById("topicsBox");
  const topicsTable = document.getElementById("topicsTable");
  const topicsHint = document.getElementById("topicsHint");

  const detailsTitle = document.getElementById("detailsTitle");
  const detailsSub = document.getElementById("detailsSub");
  const detailsTable = document.getElementById("detailsTable");
  const detailsCloseBtn = document.getElementById("detailsCloseBtn");

  const topicSummBox = document.getElementById("topicSummBox");
  const summTabs = document.getElementById("summTabs");
  const summBody = document.getElementById("summBody");
  const summRunBtn = document.getElementById("summRunBtn");

  let CSV_STATE = {
    topics: [],
    topComments: {},
    topCommentsByClass: {},
    selectedTopic: null,
    selectedClass: "Positive"
  };

  let SUMM_STATE = {
    busy: false,
    runKey: null,
    cache: {}
  };

  let SINGLE_STATE = {
    busy: false,
    downloadUrl: "",
    downloadName: ""
  };


  function setSingleStatus(s){
    if(singleStatus){ singleStatus.textContent = s || ""; }
  }
  function setCsvStatus(s){ csvStatus.textContent = s || ""; }

  function showError(el, err){
    el.style.display = "block";
    el.textContent = (typeof err === "string" ? err : JSON.stringify(err, null, 2));
  }

  function setAria(){
    viewHome.setAttribute("aria-hidden", viewHome.classList.contains("active") ? "false" : "true");
    viewSingle.setAttribute("aria-hidden", viewSingle.classList.contains("active") ? "false" : "true");
    viewCsv.setAttribute("aria-hidden", viewCsv.classList.contains("active") ? "false" : "true");
  }

  function stagePulse(){
    stage.classList.remove("stage-shift");
    void stage.offsetWidth;
    stage.classList.add("stage-shift");
  }

  function transition(fromEl, toEl, after){
    stagePulse();

    fromEl.classList.add("leaving");
    toEl.classList.add("active");
    toEl.classList.remove("leaving");

    setTimeout(() => {
      fromEl.classList.remove("active");
      fromEl.classList.remove("leaving");
      setAria();
      if(after) after();
    }, 640);
  }

  function showHome(push=true){
    if(push) history.pushState({page:"home"}, "", "/");
    if(viewSingle.classList.contains("active")) transition(viewSingle, viewHome);
    else transition(viewCsv, viewHome);
  }

  function showSingle(push=true){
    if(push) history.pushState({page:"single"}, "", "/single");
    transition(
      viewHome.classList.contains("active") ? viewHome : viewCsv,
      viewSingle,
      () => { if(singleExcelFile){ singleExcelFile.focus(); } }
    );
  }

  function showCsv(push=true){
    if(push) history.pushState({page:"csv"}, "", "/csv");
    transition(viewHome.classList.contains("active") ? viewHome : viewSingle, viewCsv, () => { csvCol.focus(); });
  }

  function boot(){
    const path = location.pathname || "/";
    if(path === "/single"){
      viewSingle.classList.add("active");
      setTimeout(() => { if(singleExcelFile){ singleExcelFile.focus(); } }, 0);
    }else if(path === "/csv"){
      viewCsv.classList.add("active");
      setTimeout(() => csvCol.focus(), 0);
    }else{
      viewHome.classList.add("active");
    }
    setAria();
  }

  goSingle.addEventListener("click", () => showSingle(true));
  goCsv.addEventListener("click", () => showCsv(true));

  backBtn.addEventListener("click", () => showHome(true));
  csvBackBtn.addEventListener("click", () => showHome(true));

  window.addEventListener("popstate", () => {
    const path = location.pathname || "/";
    if(path === "/single"){
      if(!viewSingle.classList.contains("active")) showSingle(false);
    }else if(path === "/csv"){
      if(!viewCsv.classList.contains("active")) showCsv(false);
    }else{
      if(!viewHome.classList.contains("active")) showHome(false);
    }
  });

  function _appendSingleLog(msg){
    if(!singleLog){ return; }
    singleLog.textContent += (String(msg || "") + "\n");
    if(singleLogScroll){
      singleLogScroll.scrollTop = singleLogScroll.scrollHeight;
    }
  }

  function _resetSingleDownload(){
    SINGLE_STATE.downloadUrl = "";
    SINGLE_STATE.downloadName = "";
    if(!singleDownloadBtn){ return; }
    singleDownloadBtn.classList.add("is-disabled");
    singleDownloadBtn.setAttribute("aria-disabled", "true");
    singleDownloadBtn.removeAttribute("href");
    singleDownloadBtn.removeAttribute("download");
  }

  function _setSingleDownload(url, name){
    SINGLE_STATE.downloadUrl = String(url || "");
    SINGLE_STATE.downloadName = String(name || "processed_table.csv");
    if(!singleDownloadBtn){ return; }

    if(!SINGLE_STATE.downloadUrl){
      _resetSingleDownload();
      return;
    }

    singleDownloadBtn.classList.remove("is-disabled");
    singleDownloadBtn.setAttribute("aria-disabled", "false");
    singleDownloadBtn.href = SINGLE_STATE.downloadUrl;
    singleDownloadBtn.setAttribute("download", SINGLE_STATE.downloadName);
  }

  function _setSingleBusy(busy){
    SINGLE_STATE.busy = !!busy;
    if(!singleRunBtn){ return; }
    singleRunBtn.textContent = SINGLE_STATE.busy ? "Running..." : "Run";
    singleRunBtn.classList.toggle("is-disabled", SINGLE_STATE.busy);
  }

  async function runSingleExcel(){
    if(SINGLE_STATE.busy){ return; }

    const f = singleExcelFile && singleExcelFile.files && singleExcelFile.files[0];
    if(!f){
      setSingleStatus("Please choose one CSV/Excel file.");
      return;
    }

    _setSingleBusy(true);
    _resetSingleDownload();
    setSingleStatus("Running...");
    if(singleLog){ singleLog.textContent = ""; }

    const fd = new FormData();
    fd.append("file", f);

    try{
      const resp = await fetch("/api/excel_clean_gibberish_stream", {
        method: "POST",
        body: fd
      });

      if(!resp.ok){
        const data = await resp.json().catch(()=>({detail:"Pipeline request failed"}));
        setSingleStatus("Error.");
        _appendSingleLog("Error: " + (data.detail || "Pipeline request failed"));
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while(true){
        const {value, done} = await reader.read();
        if(done){ break; }

        buffer += decoder.decode(value, {stream:true});

        let cut;
        while((cut = buffer.indexOf("\n\n")) !== -1){
          const frame = buffer.slice(0, cut);
          buffer = buffer.slice(cut + 2);

          const lines = frame.split("\n");
          for(const line of lines){
            if(!line.startsWith("data:")) continue;
            const payload = line.slice(5).trim();
            if(!payload) continue;

            let obj = null;
            try{ obj = JSON.parse(payload); }catch(_){ obj = null; }
            if(!obj) continue;

            if(obj.type === "log"){
              _appendSingleLog(obj.message || "");
              continue;
            }

            if(obj.type === "error"){
              setSingleStatus("Error.");
              _appendSingleLog("Error: " + (obj.detail || "Unknown error"));
              return;
            }

            if(obj.type === "done"){
              _setSingleDownload(obj.download_url || "", obj.filename || "processed_table.csv");
              _appendSingleLog("File has been processed. Please click Download");
              setSingleStatus("File has been processed. Please click Download");
              return;
            }
          }
        }
      }

      if(!SINGLE_STATE.downloadUrl){
        setSingleStatus("No output file was returned.");
      }
    }catch(e){
      setSingleStatus("Error.");
      _appendSingleLog("Error: " + String(e));
    }finally{
      _setSingleBusy(false);
    }
  }

  if(singleExcelFile){
    singleExcelFile.addEventListener("change", () => {
      const f = singleExcelFile.files && singleExcelFile.files[0];
      if(singleExcelName){
        singleExcelName.textContent = f ? f.name : "No file selected";
      }
      _resetSingleDownload();
      setSingleStatus("");
    });
  }

  if(singleRunBtn){
    singleRunBtn.addEventListener("click", runSingleExcel);
  }

  csvFile.addEventListener("change", () => {
    const f = csvFile.files && csvFile.files[0];
    csvFileName.textContent = f ? f.name : "No file selected";
  });

  function pct(n, total){
    if(!total) return 0;
    return (100.0 * n / total);
  }

  function setDonut(posN, gibN, negN, totalN){
    const rows = [
      {k:"Positive", n:posN, p:pct(posN, totalN), cls:""},
      {k:"Gibberish", n:gibN, p:pct(gibN, totalN), cls:"s2"},
      {k:"Negative", n:negN, p:pct(negN, totalN), cls:"s3"},
    ];

    const values = [posN, gibN, negN];
    const labels = ["Positive", "Gibberish", "Negative"];

    const data = [{
      type: "pie",
      values: values,
      labels: labels,
      hole: 0.62,
      sort: false,
      direction: "clockwise",
      rotation: 90,
      textinfo: "none",
      hoverinfo: "skip",
      hovertemplate: "",
      marker: {
        colors: [
          "rgba(255,255,255,0.88)",
          "rgba(255,255,255,0.55)",
          "rgba(255,255,255,0.28)"
        ],
        line: { color: "rgba(255,255,255,0.14)", width: 1 }
      }
    }];

    const layout = {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      margin: {l: 0, r: 0, t: 0, b: 0},
      showlegend: false,
      width: 120,
      height: 120
    };

    Plotly.newPlot(donutPlot, data, layout, {displayModeBar: false, responsive: true});

    legend.innerHTML = "";

    for(const r of rows){
      const div = document.createElement("div");
      div.className = "leg-item";

      const left = document.createElement("div");
      left.className = "leg-left";

      const sw = document.createElement("div");
      sw.className = "swatch " + r.cls;

      const name = document.createElement("div");
      name.className = "leg-name";
      name.textContent = r.k;

      left.appendChild(sw);
      left.appendChild(name);

      const right = document.createElement("div");
      right.textContent = r.n + "  ·  " + r.p.toFixed(1) + "%";

      div.appendChild(left);
      div.appendChild(right);

      legend.appendChild(div);
    }
  }

function plotConfidence(el, x, y, color){
    if(!el){ return; }

    const data = [{
      type: "scatter",
      mode: "lines",
      x: x,
      y: y,
      line: { color: color, width: 3, shape: "spline", smoothing: 0.85 },
      hoverinfo: "skip",
    }];

    const tickCol = "rgba(255,255,255,0.60)";
    const gridCol = "rgba(255,255,255,0.08)";

    const layout = {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      margin: {l: 20, r: 7, t: 8, b: 12},
      showlegend: false,
      hovermode: false,

      xaxis: {
        title: {text: ""},
        range: [0, 1],
        tickvals: [0, 0.5, 1],
        ticktext: ["0", "0.5", "1"],
        gridcolor: gridCol,
        zeroline: false,
        tickfont: {color: tickCol, size: 8},
        fixedrange: true,
      },

      yaxis: {
        title: {text: ""},
        range: [0, 100],
        tickvals: [0, 50, 100],
        ticktext: ["", "50", "100"],
        gridcolor: gridCol,
        zeroline: false,
        tickfont: {color: tickCol, size: 8},
        fixedrange: true,
      }
    };

    Plotly.newPlot(el, data, layout, {
      displayModeBar: false,
      responsive: true,
      staticPlot: true
    });
  }


  function renderConfidenceDist(dist){
    if(!dist || !confBox){
      if(confBox){ confBox.style.display = "none"; }
      return;
    }

    const cPos = "rgba(255,255,255,0.88)";
    const cGib = "rgba(255,255,255,0.55)";
    const cNeg = "rgba(255,255,255,0.28)";

    const P = dist.Positive || {};
    const G = dist.Gibberish || {};
    const N = dist.Negative || {};

    plotConfidence(confPosPlot, P.x || [], P.y || [], cPos);
    plotConfidence(confGibPlot, G.x || [], G.y || [], cGib);
    plotConfidence(confNegPlot, N.x || [], N.y || [], cNeg);

    confBox.style.display = "block";
  }

  function setProgress(p, stageText){
    const pp = Math.max(0, Math.min(100, Number(p || 0)));
    csvProgressFill.style.width = pp.toFixed(0) + "%";
    csvProgressPct.textContent = pp.toFixed(0) + "%";
    csvProgressStage.textContent = stageText || "Running";
  }

  function collapseDetails(){
    CSV_STATE.selectedTopic = null;
    rightSplit.classList.remove("split");
    csvPanel.classList.remove("details-open");
  }

  function renderDetails(topicId, cls){
    const tid = String(topicId);
    const j = String(cls || CSV_STATE.selectedClass || "Positive");

    const by = CSV_STATE.topCommentsByClass[tid] || {};
    const arr = (by && by[j]) ? by[j] : (CSV_STATE.topComments[tid] || []);

    detailsTitle.textContent = "Topic " + tid + " Top 20 " + j + " Comments";
    detailsSub.textContent = "Top 20 comments";

    detailsTable.innerHTML = "";

    const thead = document.createElement("thead");
    const trh = document.createElement("tr");
    ["#", "Comment"].forEach(t => {
      const th = document.createElement("th");
      th.textContent = t;
      trh.appendChild(th);
    });
    thead.appendChild(trh);

    const tbody = document.createElement("tbody");

    arr.slice(0, 20).forEach((t, i) => {
      const tr = document.createElement("tr");

      const td0 = document.createElement("td");
      td0.textContent = String(i + 1);

      const td1 = document.createElement("td");
      td1.textContent = t;

      tr.appendChild(td0);
      tr.appendChild(td1);

      tbody.appendChild(tr);
    });

    detailsTable.appendChild(thead);
    detailsTable.appendChild(tbody);
  }

  function openDetails(topicId){
    const tid = String(topicId);

    if(CSV_STATE.selectedTopic === tid && rightSplit.classList.contains("split")){
      collapseDetails();
      return;
    }

    CSV_STATE.selectedTopic = tid;
    renderDetails(tid, CSV_STATE.selectedClass);

    csvPanel.classList.add("details-open");
    rightSplit.classList.add("split");

    _renderSummaryForSelection();
    _setRunBtnState();
  }

  function renderTopicsTable(topics){
    topicsTable.innerHTML = "";

    const thead = document.createElement("thead");
    const trh = document.createElement("tr");
    ["Topic", "Name", "Count", ""].forEach(t => {
      const th = document.createElement("th");
      th.textContent = t;
      trh.appendChild(th);
    });
    thead.appendChild(trh);

    const tbody = document.createElement("tbody");

    for(const row of topics){
      const tr = document.createElement("tr");

      const td0 = document.createElement("td");
      td0.textContent = String(row.topic_id);

      const td1 = document.createElement("td");
      td1.textContent = row.name || "";

      const td2 = document.createElement("td");
      td2.textContent = String(row.count);

      const td3 = document.createElement("td");
      const b = document.createElement("div");
      b.className = "btn";
      b.textContent = "Details";
      b.addEventListener("click", () => openDetails(row.topic_id));
      td3.appendChild(b);

      tr.appendChild(td0);
      tr.appendChild(td1);
      tr.appendChild(td2);
      tr.appendChild(td3);

      tbody.appendChild(tr);
    }

    topicsTable.appendChild(thead);
    topicsTable.appendChild(tbody);
  }

  detailsCloseBtn.addEventListener("click", () => collapseDetails());

  function _summKey(tid, cls){
    return String(tid) + "||" + String(cls || "Positive");
  }

  function _renderSummaryForSelection(){
    const tid = CSV_STATE.selectedTopic;
    const cls = CSV_STATE.selectedClass || "Positive";

    if(tid === null){
      summBody.textContent = "";
      return;
    }

    const key = _summKey(tid, cls);
    const cached = SUMM_STATE.cache[key];
    summBody.textContent = cached ? String(cached) : "";
  }

  function _setRunBtnState(){
    if(!summRunBtn){ return; }

    const cls = CSV_STATE.selectedClass || "Positive";
    const canRun = (CSV_STATE.selectedTopic !== null) && rightSplit.classList.contains("split") && !SUMM_STATE.busy && (cls !== "Gibberish");
    summRunBtn.classList.toggle("is-disabled", !canRun);
    summRunBtn.textContent = SUMM_STATE.busy ? "Running..." : "Run";
  }

  async function _streamTopicSummary(topicId, cls){
    const key = _summKey(topicId, cls);
    SUMM_STATE.runKey = key;
    SUMM_STATE.cache[key] = "";
    if(_summKey(CSV_STATE.selectedTopic, CSV_STATE.selectedClass) === key){
      summBody.textContent = "";
    }

    const resp = await fetch("/api/topic_summary_stream", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({topic_id: String(topicId), cls: String(cls)})
    });

    if(resp.status === 409){
      return;
    }

    if(!resp.ok){
      const data = await resp.json().catch(()=>({detail:"Topic summary stream failed"}));
      setCsvStatus("Error.");
      alert(JSON.stringify(data, null, 2));
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buf = "";

    while(true){
      const {value, done} = await reader.read();
      if(done){ break; }

      buf += decoder.decode(value, {stream:true});

      while(true){
        const cut = buf.indexOf("\n\n");
        if(cut < 0) break;

        const frame = buf.slice(0, cut);
        buf = buf.slice(cut + 2);

        const lines = frame.split("\n");
        for(const line of lines){
          if(!line.startsWith("data:")) continue;
          const payload = line.slice(5).trim();

          if(payload === "[DONE]"){
            return;
          }

          try{
            const obj = JSON.parse(payload);
            if(obj && typeof obj.t === "string"){
              const piece = obj.t;

              SUMM_STATE.cache[key] = (SUMM_STATE.cache[key] || "") + piece;

              if(_summKey(CSV_STATE.selectedTopic, CSV_STATE.selectedClass) === key){
                summBody.textContent += piece;
              }
            }
          }catch(e){}
        }
      }
    }
  }

  function setSummClass(cls){
    CSV_STATE.selectedClass = cls;

    const btns = summTabs.querySelectorAll(".summ-btn");
    btns.forEach(b => b.classList.toggle("is-active", b.dataset.class === cls));

    if(CSV_STATE.selectedTopic !== null && rightSplit.classList.contains("split")){
      renderDetails(CSV_STATE.selectedTopic, cls);
    }

    _renderSummaryForSelection();
    _setRunBtnState();
  }

  summTabs.addEventListener("click", (e) => {
    const el = e.target.closest(".summ-btn");
    if(!el){ return; }
    setSummClass(el.dataset.class || "Positive");
  });

  if(summRunBtn){
    summRunBtn.addEventListener("click", async () => {
      if(SUMM_STATE.busy){ return; }
      if(CSV_STATE.selectedTopic === null){ return; }
      if(!rightSplit.classList.contains("split")){ return; }

      const cls = CSV_STATE.selectedClass || "Positive";
      if(cls === "Gibberish"){ return; }

      SUMM_STATE.busy = true;
      _setRunBtnState();

      const tid = CSV_STATE.selectedTopic;

      try{
        await _streamTopicSummary(tid, cls);
      }finally{
        SUMM_STATE.busy = false;
        SUMM_STATE.runKey = null;
        _setRunBtnState();
      }
    });
  }

  async function runCsv(){
    const f = csvFile.files && csvFile.files[0];
    const col = (csvCol.value || "").trim();

    if(!f){
      setCsvStatus("Please choose a CSV file.");
      return;
    }
    if(!col){
      setCsvStatus("Please input the comment column letters.");
      return;
    }

    setCsvStatus("");
    donutBox.style.display = "none";
    topicsBox.style.display = "none";
    collapseDetails();

    CSV_STATE = {topics:[], topComments:{}, selectedTopic:null};

    csvProgress.style.display = "block";
    setProgress(0, "Starting");

    const fd = new FormData();
    fd.append("file", f);
    fd.append("col_letters", col);

    try{
      const resp = await fetch("/api/csv_analyse_stream", { method:"POST", body: fd });

      if(!resp.ok){
        const data = await resp.json().catch(()=>({detail:"CSV stream failed"}));
        setCsvStatus("Error.");
        alert(JSON.stringify(data, null, 2));
        csvProgress.style.display = "none";
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while(true){
        const {value, done} = await reader.read();
        if(done) break;

        buffer += decoder.decode(value, {stream:true});

        let idx;
        while((idx = buffer.indexOf("\n\n")) !== -1){
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);

          const lines = frame.split("\n");
          for(const line of lines){
            if(!line.startsWith("data:")) continue;
            const payload = line.slice(5).trim();

            let obj = null;
            try{ obj = JSON.parse(payload); }catch(_){ obj = null; }

            if(!obj) continue;

            if(obj.type === "error"){
              setCsvStatus("Error.");
              alert(obj.detail || "Unknown error");
              csvProgress.style.display = "none";
              return;
            }

            if(obj.type === "progress"){
              setProgress(obj.p, obj.stage || "Running");
              continue;
            }

            if(obj.type === "result"){
              setProgress(100, "Done");

              const s = obj.sentiment || {};
              setDonut(
                Number(s.Positive || 0),
                Number(s.Gibberish || 0),
                Number(s.Negative || 0),
                Number(s.Total || 0)
              );
              donutBox.style.display = "block";

              renderConfidenceDist(obj.confidence_dist || null);

              const topics = obj.topics || [];
              CSV_STATE.topics = topics;
              CSV_STATE.topComments = obj.top_comments || {};
              CSV_STATE.topCommentsByClass = obj.top_comments_by_class || {};
              CSV_STATE.selectedTopic = null;
              CSV_STATE.selectedClass = "Positive";

              setSummClass("Positive");
              renderTopicsTable(topics);
              
              topicsHint.textContent = topics.length ? "Click Details to expand the top 20 comments for a topic." : "No topics were formed.";
              topicsBox.style.display = "block";

              return;
            }
          }
        }
      }

    }catch(e){
      setCsvStatus("Error.");
      alert(String(e));
      csvProgress.style.display = "none";
      return;
    }
  }

  csvRunBtn.addEventListener("click", runCsv);

  boot();
"""
