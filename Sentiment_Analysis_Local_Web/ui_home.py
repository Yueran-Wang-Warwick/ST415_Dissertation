# ui_home.py
VIEW_HOME = r"""
    <div class="view" id="view-home" aria-hidden="true">
      <div class="hero">
        <h1 class="brand">Sentiment Analysis</h1>
        <p class="sub">Local NLP pipelines with a minimal liquid-glass UI</p>
        <div class="cards">
          <div class="card glass" id="go-single">
            <h3>Table Cleaning</h3>
            <p>Upload one CSV or Excel file and run Data Cleaning automatically.</p>
            <div class="chip"><span class="dot"></span> Ready</div>
          </div>
          <div class="card glass" id="go-csv">
            <h3>CSV Analysis</h3>
            <p>Upload a CSV, choose the comment column, then run sentiment and BERTopic.</p>
            <div class="chip"><span class="dot"></span> Ready</div>
          </div>
        </div>
      </div>
    </div>
"""
