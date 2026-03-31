# ui_confidence.py
VIEW_CONFIDENCE = r"""
            <div class="box" id="confBox" style="display:none;">
              <div class="box-title">Confidence Distribution: % Density vs Conf</div>

              <div class="conf-grid">
                <div class="subbox">
                  <div class="conf-head">Positive</div>
                  <div class="conf-plot" id="confPosPlot"></div>
                </div>

                <div class="subbox">
                  <div class="conf-head">Gibberish</div>
                  <div class="conf-plot" id="confGibPlot"></div>
                </div>

                <div class="subbox">
                  <div class="conf-head">Negative</div>
                  <div class="conf-plot" id="confNegPlot"></div>
                </div>
              </div>
            </div>
"""
