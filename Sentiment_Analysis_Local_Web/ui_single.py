# ui_single.py
VIEW_SINGLE = r"""
    <div class="view" id="view-single" aria-hidden="true">
      <div class="panel glass single-panel" id="single-panel">
        <div class="topbar">
          <div class="btn" id="backBtn">Back</div>
          <div class="single-top-note">ST415 pipeline</div>
        </div>

        <div class="title">Table Data Cleaning</div>
        <div class="hint">Upload one CSV or Excel file and run Data Cleaning from ST415 Project notebook.</div>

        <div class="single-grid">
          <div class="single-left">
            <div class="box">
              <div class="box-title">Upload</div>

              <div class="file-row">
                <label class="btn" for="singleExcelFile">Choose File</label>
                <input id="singleExcelFile" type="file" accept=".csv,.xlsx,.xlsm"/>
                <div class="file-name" id="singleExcelName">No file selected</div>
              </div>

              <div class="small single-note">
                Required: one text/comment column.
                Optional: title and label columns.
              </div>

              <div class="single-actions">
                <div class="pill" id="singleRunBtn">Run</div>
                <a class="btn is-disabled" id="singleDownloadBtn" href="#" aria-disabled="true">Download</a>
              </div>

              <div class="status" id="singleStatus"></div>
            </div>
          </div>

          <div class="single-right">
            <div class="box single-log-box">
              <div class="box-title">Processing Log</div>
              <div class="scroll single-log-scroll" id="singleLogScroll">
                <pre id="singleLog" class="single-log"></pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
"""
