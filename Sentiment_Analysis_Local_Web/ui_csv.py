# ui_csv.py (full, modified)

import ui_topic_summarisation
import ui_confidence
import ui_vram

VIEW_CSV = f"""
    <div class="view" id="view-csv" aria-hidden="true">
      <div class="csv-panel glass" id="csv-panel">
        <div class="topbar">
          <div class="btn" id="csvBackBtn">Back</div>
          {ui_vram.VRAM_BAR}
        </div>

        <div class="title">CSV Analysis</div>

        <div class="csv-grid">
          <div class="csv-left">
            <div class="box" id="uploadBox">
              <div class="box-title">Upload</div>

              <div class="file-row">
                <label class="btn" for="csvFile">Choose CSV</label>
                <input id="csvFile" type="file" accept=".csv"/>
                <div class="file-name" id="csvFileName">No file selected</div>
              </div>

              <div class="field">
                <div class="label">Which column is comment (Excel letters)</div>

                <div class="col-run-row">
                  <input class="mini-input col-input" id="csvCol" type="text" placeholder="e.g. A or AB"/>
                  <div class="pill" id="csvRunBtn">Analyze</div>
                </div>
              </div>

              <div class="progress" id="csvProgress" style="display:none;">
                <div class="progress-fill" id="csvProgressFill"></div>
                <div class="progress-meta">
                  <div class="progress-stage" id="csvProgressStage">Running</div>
                  <div class="progress-pct" id="csvProgressPct">0%</div>
                </div>
              </div>

              <div class="status" id="csvStatus"></div>
            </div>

            <div class="box" id="donutBox" style="display:none;">
              <div class="box-title">Sentiment distribution</div>
              <div class="donut-wrap">
                <div class="donut" id="donut">
                  <div id="donutPlot" style="width:120px;height:120px;"></div>
                </div>
                <div class="legend" id="legend"></div>
              </div>
            </div>

{ui_confidence.VIEW_CONFIDENCE}
          </div>

          <div class="csv-right">
            <div class="right-split" id="rightSplit">

              <div class="topics-stack" id="topicsStack">

                <div class="box" id="topicsBox" style="display:none;">
                  <div class="box-title">Topic Clusters</div>

                  <div class="scroll" id="topicsScroll">
                    <table class="table" id="topicsTable"></table>
                  </div>
                  <div class="small" id="topicsHint"></div>
                </div>

{ui_topic_summarisation.VIEW_TOPIC_SUMMARISATION}
              </div>

              <div class="box" id="topicDetailsBox">
                <div class="details-top">
                  <div class="box-title" id="detailsTitle">Topic details</div>
                  <div class="btn" id="detailsCloseBtn">Close</div>
                </div>
                <div class="small" id="detailsSub">Top 20 comments</div>
                <div class="scroll" id="detailsScroll">
                  <table class="table" id="detailsTable"></table>
                </div>
              </div>

            </div>
          </div>
        </div>

      </div>
    </div>
"""
