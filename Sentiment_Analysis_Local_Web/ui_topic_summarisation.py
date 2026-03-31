# ui_topic_summarisation.py
VIEW_TOPIC_SUMMARISATION = r"""
              <div class="box summ-box" id="topicSummBox">
                <div class="summ-inner">
                  <div class="box-title">Topic Summarisation</div>

                  <div class="summ-top">
                    <div class="summ-tabs" id="summTabs">
                      <div class="btn summ-btn is-active" data-class="Positive">Positive</div>
                      <div class="btn summ-btn" data-class="Gibberish">Gibberish</div>
                      <div class="btn summ-btn" data-class="Negative">Negative</div>
                    </div>

                    <div class="btn summ-run-btn" id="summRunBtn">Run</div>
                  </div>

                  <div class="scroll" id="summScroll">
                    <div id="summBody"></div>
                  </div>
                </div>
              </div>
"""
