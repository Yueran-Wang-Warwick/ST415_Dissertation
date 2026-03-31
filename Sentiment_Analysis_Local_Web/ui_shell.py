# ui_shell.py (full, modified)
HTML_PREFIX = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Sentiment Analysis</title>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  <style>
    :root{
      --bg0:#0b0f1a;
      --bg1:#0f1630;

      --glass: rgba(255,255,255,0.10);
      --glass2: rgba(255,255,255,0.06);
      --stroke: rgba(255,255,255,0.18);

      --text: rgba(255,255,255,0.92);
      --muted: rgba(255,255,255,0.62);

      --shadow: 0 20px 70px rgba(0,0,0,0.45);
      --radius: 22px;

      --csvLeftW: 420px;
      --csvLeftWOpen: 390px;

      --detailsW: 42%;
      --topicsWOpen: 58%;
      --topicSummH: clamp(220px, 34%, 330px);

    }

    *{box-sizing:border-box}
    html,body{height:100%}

    body{
      margin:0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
      color:var(--text);
      background:
        radial-gradient(1200px 800px at 20% 20%, rgba(120,140,255,0.25), transparent 60%),
        radial-gradient(1000px 700px at 80% 30%, rgba(255,140,220,0.18), transparent 55%),
        radial-gradient(900px 700px at 50% 90%, rgba(120,255,210,0.12), transparent 55%),
        linear-gradient(160deg, var(--bg0), var(--bg1));
      overflow:hidden;
    }

    .noise{
      pointer-events:none;
      position:fixed; inset:0;
      background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)' opacity='.22'/%3E%3C/svg%3E");
      mix-blend-mode: overlay;
      opacity: .15;
    }

    .wrap{
      position:relative;
      height:100%;
      display:flex;
      align-items:center;
      justify-content:center;
      padding:10px;
      perspective: 1100px;
    }

    .glass{
      border-radius: var(--radius);
      background: linear-gradient(180deg, var(--glass), var(--glass2));
      border: 1px solid var(--stroke);
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
      position:relative;
      overflow:hidden;
      transform-style: preserve-3d;
    }
    .glass:before{
      content:"";
      position:absolute; inset:-2px;
      background: radial-gradient(520px 260px at 20% 10%, rgba(255,255,255,0.16), transparent 55%);
      opacity:.7;
      pointer-events:none;
    }

    .btn{
      border: 1px solid rgba(255,255,255,0.18);
      background: rgba(0,0,0,0.18);
      color: rgba(255,255,255,0.88);
      padding: 10px 12px;
      border-radius: 999px;
      cursor:pointer;
      font-size: 12px;
      user-select:none;
      transition: transform .22s cubic-bezier(.2,.9,.2,1), filter .22s ease, background .22s ease, border-color .22s ease;
      will-change: transform;
      transform: translateZ(0);
    }
    .btn:hover{
      background: rgba(255,255,255,0.10);
      border-color: rgba(255,255,255,0.28);
      filter: brightness(1.15);
      animation: liquid-gel 520ms cubic-bezier(.2,.9,.2,1);
    }
    .btn:active{
      transform: scale(0.98);
      filter: brightness(1.18);
    }
    .btn.is-disabled{
      opacity: 0.45;
      pointer-events: none;
      cursor: not-allowed;
      filter: saturate(0.9);
    }

    .vram-bar.btn{
      min-width: 260px;
      max-width: 360px;
      flex: 0 0 auto;
      cursor: default;
      position: relative;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 10px 14px;

      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.10),
        inset 0 -1px 0 rgba(0,0,0,0.18),
        0 14px 40px rgba(0,0,0,0.25);
    }
    .vram-meter{
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 0%;
      border-radius: 999px;
      background: linear-gradient(90deg, rgba(255,255,255,0.18), rgba(255,255,255,0.06));
      transition: width .38s cubic-bezier(.2,.9,.2,1);
      pointer-events: none;
      will-change: width;
    }
    .vram-text{
      position: relative;
      z-index: 1;
      font-variant-numeric: tabular-nums;
      letter-spacing: 0.2px;
      opacity: 0.92;
      white-space: nowrap;
    }

    .vram-bar.btn.is-loading::after{
      content:"";
      position:absolute;
      inset:-2px;
      pointer-events:none;
      border-radius:999px;

      clip-path: inset(0 round 999px);

      background:
        linear-gradient(
          110deg,
          rgba(255,255,255,0.00) 0%,
          rgba(255,255,255,0.06) 35%,
          rgba(255,255,255,0.12) 50%,
          rgba(255,255,255,0.06) 65%,
          rgba(255,255,255,0.00) 100%
        );
      transform: translateX(-70%) skewX(-12deg);
      opacity: 0.55;
      mix-blend-mode: screen;
      animation: vramShimmer 4.8s cubic-bezier(.2,.9,.2,1) infinite;
    }

    @keyframes vramShimmer{
      0%   { transform: translateX(-70%) skewX(-12deg); }
      55%  { transform: translateX(70%)  skewX(-12deg); }
      100% { transform: translateX(70%)  skewX(-12deg); }
    }

    @media (prefers-reduced-motion: reduce){
      .vram-bar.btn.is-loading::after{ animation: none; opacity: 0.25; }
    }

    .pill{
      display:inline-flex;
      align-items:center;
      justify-content:center;
      min-width: 38px;
      height: 34px;
      padding: 0 12px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.18);
      background: rgba(255,255,255,0.08);
      color: rgba(255,255,255,0.86);
      font-size: 12px;
      cursor:pointer;
      user-select:none;
      transition: transform .22s cubic-bezier(.2,.9,.2,1), filter .22s ease, background .22s ease, border-color .22s ease;
      will-change: transform;
      transform: translateZ(0);
    }
    .pill:hover{
      background: rgba(255,255,255,0.14);
      border-color: rgba(255,255,255,0.30);
      filter: brightness(1.15);
      animation: liquid-gel 520ms cubic-bezier(.2,.9,.2,1);
    }
    .pill:active{ transform: scale(0.98); }
    .pill.is-disabled{
      opacity: 0.45;
      pointer-events: none;
      cursor: not-allowed;
      filter: saturate(0.9);
    }

    @keyframes liquid-gel{
      0%{transform: translateZ(0) scale(1)}
      30%{transform: translateZ(0) scale(1.02,0.985)}
      65%{transform: translateZ(0) scale(0.992,1.015)}
      100%{transform: translateZ(0) scale(1)}
    }

    .view{
      position:absolute;
      inset:0;
      display:flex;
      align-items:center;
      justify-content:center;
      pointer-events:none;
      opacity:0;
      transform: translate3d(0, 14px, 0) scale(0.985);
      filter: blur(10px) saturate(1.02);
      transition:
        opacity 460ms cubic-bezier(.2,.9,.2,1),
        transform 620ms cubic-bezier(.2,.9,.2,1),
        filter 620ms cubic-bezier(.2,.9,.2,1);
      will-change: opacity, transform, filter;
    }
    .view.active{
      pointer-events:auto;
      opacity:1;
      transform: translate3d(0, 0, 0) scale(1);
      filter: blur(0) saturate(1);
    }
    .view.leaving{
      pointer-events:none;
      opacity:0;
      transform: translate3d(0, -10px, 0) scale(0.992);
      filter: blur(14px) saturate(0.98);
    }

    .view .glass:after{
      content:"";
      position:absolute;
      inset:-40%;
      background: radial-gradient(520px 260px at 10% 20%, rgba(255,255,255,0.12), transparent 58%);
      opacity:0;
      transform: translate3d(-10px, 8px, 0) rotate(-6deg);
      pointer-events:none;
      transition: opacity 520ms ease, transform 720ms cubic-bezier(.2,.9,.2,1);
      will-change: opacity, transform;
    }
    .view.active .glass:after{
      opacity:0.55;
      transform: translate3d(0, 0, 0) rotate(-6deg);
    }
    .view.leaving .glass:after{
      opacity:0.0;
      transform: translate3d(12px, -10px, 0) rotate(-6deg);
    }

    .wrap.stage-shift{
      animation: stage-shift 640ms cubic-bezier(.2,.9,.2,1);
    }
    @keyframes stage-shift{
      0%{transform: translate3d(0,0,0)}
      45%{transform: translate3d(0,-2px,0)}
      100%{transform: translate3d(0,0,0)}
    }

    .hero{
      width:min(980px, 100%);
      display:flex;
      flex-direction:column;
      gap:18px;
      align-items:center;
      justify-content:center;
      padding: 0 6px;
    }
    .brand{
      text-align:center;
      font-weight:650;
      letter-spacing:-0.02em;
      font-size: 34px;
      margin: 0 0 8px 0;
      color: rgba(255,255,255,0.92);
    }
    .sub{
      margin:0;
      text-align:center;
      color: var(--muted);
      font-size: 14px;
    }
    .cards{
      display:grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      width:min(820px, 100%);
      margin-top: 18px;
    }
    .card{
      cursor:pointer;
      user-select:none;
      padding: 22px 22px 18px 22px;
      min-height: 140px;
      transform: translateY(0) translateZ(0);
      transition:
        transform .26s cubic-bezier(.2,.9,.2,1),
        border-color .22s ease,
        background .22s ease,
        filter .22s ease;
      will-change: transform;
    }
    .card:hover{
      transform: translateY(-4px) scale(1.01);
      border-color: rgba(255,255,255,0.30);
      background: linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0.07));
      filter: brightness(1.06);
      animation: card-breathe 900ms cubic-bezier(.2,.9,.2,1);
    }
    @keyframes card-breathe{
      0%{transform: translateY(-4px) scale(1.01)}
      40%{transform: translateY(-5px) scale(1.012)}
      100%{transform: translateY(-4px) scale(1.01)}
    }

    .card h3{
      margin:0 0 10px 0;
      font-size: 18px;
      letter-spacing:-0.01em;
    }
    .card p{
      margin:0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }
    .chip{
      display:inline-flex;
      align-items:center;
      gap:8px;
      margin-top: 14px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.18);
      background: rgba(0,0,0,0.22);
      font-size: 12px;
      color: rgba(255,255,255,0.78);
      width: fit-content;
    }
    .dot{
      width:8px;height:8px;border-radius:99px;
      background: rgba(255,255,255,0.65);
      box-shadow: 0 0 14px rgba(255,255,255,0.45);
    }

    .panel{
      width:min(920px, 100%);
      display:flex;
      flex-direction:column;
      align-items:center;
      gap: 16px;
      border-radius: 26px;
      padding: 26px 22px 24px 22px;
      transform: translateZ(0);
    }

    .topbar{
      width:100%;
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap: 12px;
      z-index: 2;
    }

    .title{
      margin: 10px 0 4px 0;
      font-size: 28px;
      letter-spacing:-0.02em;
      font-weight: 650;
      text-align:center;
      z-index:2;
    }
    .hint{
      margin: 0 0 8px 0;
      font-size: 13px;
      color: rgba(255,255,255,0.62);
      text-align:center;
      z-index:2;
    }

    .inputbar{
      width:min(720px, 100%);
      display:flex;
      align-items:center;
      gap: 10px;
      padding: 12px 14px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.18);
      background: rgba(0,0,0,0.22);
      z-index:2;
      transform: translateZ(0);
      transition: border-color .22s ease, background .22s ease, filter .22s ease;
    }
    .inputbar:focus-within{
      border-color: rgba(255,255,255,0.30);
      background: rgba(255,255,255,0.06);
      filter: brightness(1.08);
    }
    .inputbar input{
      flex:1;
      outline:none;
      border:none;
      background: transparent;
      color: rgba(255,255,255,0.92);
      font-size: 14px;
      padding: 4px 2px;
    }

    .result{
      width:min(720px, 100%);
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.16);
      background: rgba(0,0,0,0.18);
      padding: 14px 14px;
      color: rgba(255,255,255,0.92);
      font-size: 13px;
      line-height: 1.55;
      z-index:2;
      display:none;
      white-space: pre-wrap;
    }
    .status{
      width:min(720px, 100%);
      font-size: 12px;
      color: rgba(255,255,255,0.62);
      z-index:2;
      height: 18px;
    }

    .single-panel{
      width:min(1180px, 100%);
      height:min(84vh, 920px);
      min-height: 520px;
      max-height: 84vh;
      align-items:stretch;
      padding: 18px 22px 18px 22px;
      gap: 12px;
    }

    .single-top-note{
      font-size: 12px;
      color: rgba(255,255,255,0.62);
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    .single-panel .title{
      margin: -18px 0 8px 0;
    }

    .single-panel .hint{
      margin: 0 0 4px 0;
    }

    .single-grid{
      width:100%;
      display:flex;
      gap: 14px;
      flex: 1 1 auto;
      min-height: 0;
      align-items: stretch;
    }

    .single-left{
      flex: 0 0 40%;
      min-width: 320px;
      display:flex;
      flex-direction:column;
      min-height: 0;
    }

    .single-left .box{
      margin-top: 8px;
    }

    .single-note{
      margin-top: 10px;
      line-height: 1.55;
    }

    .single-actions{
      margin-top: 12px;
      display:flex;
      gap: 10px;
      align-items:center;
    }

    #singleStatus{
      margin-top: 12px;
      width:100%;
    }

    .single-right{
      flex: 1 1 auto;
      min-width: 0;
      min-height: 0;
      display:flex;
      flex-direction:column;
    }

    .single-log-box{
      flex: 1 1 auto;
      min-height: 0;
      display:flex;
      flex-direction:column;
    }

    .single-log-scroll{
      flex: 1 1 auto;
      min-height: 0;
      margin-top: 6px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.10);
      background: rgba(0,0,0,0.16);
      padding: 10px 12px;
    }

    .single-log{
      margin:0;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      line-height: 1.55;
      color: rgba(255,255,255,0.86);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }

    .csv-panel{
      width:min(1320px, 100%);
      padding: 18px 22px 18px 22px;
      border-radius: 26px;
      display:flex;
      flex-direction:column;
      gap: 12px;

      height: min(86vh, 1000px);
      min-height: 520px;
      max-height: 86vh;

      transform: translate3d(0, 0px, 0);
    }

    #view-csv .title{
      margin: -22px 0 10px 0;
    }

    .csv-grid{
      width:100%;
      display:flex;
      gap: 14px;
      align-items:stretch;

      flex: 1 1 auto;
      min-height: 0;
    }

    .csv-left{
      flex: 0 0 var(--csvLeftW);
      display:flex;
      flex-direction:column;
      gap: 10px;
      transition: flex-basis 520ms cubic-bezier(.2,.9,.2,1);
      will-change: flex-basis;
      min-width: 0;

      justify-content:flex-start;
      min-height: 0;
    }

    #confBox{
      margin-top: auto;
    }

    .csv-left > .box{
      flex: 0 0 auto;
      flex-shrink: 0;
    }

    #csv-panel.details-open .csv-left{
      flex-basis: var(--csvLeftWOpen);
    }

    .csv-right{
      flex: 1 1 auto;
      display:flex;
      flex-direction:column;
      gap: 12px;
      min-width: 0;
      align-self: stretch;

      min-height: 0;
    }

    .box{
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.16);
      background: rgba(0,0,0,0.18);
      padding: 14px 14px;
      position:relative;
      overflow:hidden;
    }

    .box-title{
      font-size: 13px;
      font-weight: 650;
      letter-spacing:-0.01em;
      margin: 0 0 10px 0;
      color: rgba(255,255,255,0.90);
    }

    .field{
      display:flex;
      flex-direction:column;
      gap: 6px;
      margin-top: 10px;
    }

    .label{
      font-size: 12px;
      color: rgba(255,255,255,0.62);
    }

    .mini-input{
      width:100%;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.16);
      background: rgba(255,255,255,0.06);
      padding: 10px 12px;
      color: rgba(255,255,255,0.92);
      outline:none;
      font-size: 13px;
      transition: border-color .22s ease, background .22s ease, filter .22s ease;
    }
    .mini-input:focus{
      border-color: rgba(255,255,255,0.30);
      background: rgba(255,255,255,0.08);
      filter: brightness(1.08);
    }

    .col-run-row{
      display:flex;
      align-items:center;
      gap: 10px;
    }
    .col-run-row .pill{
      margin-left:auto;
    }
    .col-input{
      width: 54px;
      max-width: 72px;
      text-align: center;
      letter-spacing: 0.02em;
    }

    #uploadBox{
      padding-bottom: 10px;
    }
    #uploadBox .field{
      margin-top: 6px;
    }
    #uploadBox .progress{
      margin-top: 8px;
    }
    #uploadBox #csvStatus{
      height: 7px;
    }

    .file-row{
      display:flex;
      gap: 10px;
      align-items:center;
      margin-top: 10px;
    }
    .file-row input[type="file"]{ display:none; }

    .file-name{
      flex:1;
      min-width: 0;
      font-size: 12px;
      color: rgba(255,255,255,0.62);
      overflow:hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .csv-actions{
      display:flex;
      gap: 10px;
      align-items:center;
      margin-top: 10px;
    }

    .progress{
      margin-top: 12px;
      border-radius: 16px;
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(255,255,255,0.06);
      overflow:hidden;
      position:relative;
    }
    .progress-fill{
      height: 10px;
      width: 0%;
      background: linear-gradient(90deg, rgba(255,255,255,0.30), rgba(255,255,255,0.78));
      transition: width 220ms cubic-bezier(.2,.9,.2,1);
    }
    .progress-meta{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap: 10px;
      padding: 10px 12px 10px 12px;
      border-top: 1px solid rgba(255,255,255,0.08);
      color: rgba(255,255,255,0.62);
      font-size: 12px;
    }
    .progress-stage{
      overflow:hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      flex: 1 1 auto;
      min-width: 0;
    }
    .progress-pct{
      flex: 0 0 auto;
      color: rgba(255,255,255,0.70);
    }

    .donut-wrap{
      display:flex;
      gap: 14px;
      align-items:center;
      justify-content: space-between;

      flex-wrap: nowrap;
    }

    .donut{
      width: 120px;
      height: 120px;
      border-radius: 999px;
      position:relative;
      border: 1px solid rgba(255,255,255,0.18);
      box-shadow: 0 16px 46px rgba(0,0,0,0.40);
      background: rgba(0,0,0,0.10);
      overflow:hidden;

      flex: 0 0 120px;
    }

    .legend{
      display:flex;
      flex-direction:column;
      gap: 8px;
      font-size: 12px;
      color: rgba(255,255,255,0.72);

      flex: 0 0 auto;
      margin-left: auto;
    }

    .leg-item{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap: 12px;
      padding: 8px 10px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(255,255,255,0.06);
    }

    .leg-left{
      display:flex;
      align-items:center;
      gap: 10px;
      min-width: 0;
    }

    .swatch{
      width:10px;
      height:10px;
      border-radius: 99px;
      background: rgba(255,255,255,0.8);
      box-shadow: 0 0 14px rgba(255,255,255,0.25);
      flex: 0 0 auto;
    }
    .swatch.s2{ background: rgba(255,255,255,0.55); }
    .swatch.s3{ background: rgba(255,255,255,0.28); }

    .conf-grid{
      display:flex;
      gap: 12px;
      align-items: stretch;
    }

    .subbox{
      flex: 1 1 0;
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(0,0,0,0.14);
      padding-top: 12px;
      padding-bottom: 12px;
      padding-left: 9px;
      padding-right: 12px;

      overflow:hidden;
      position:relative;
    }

    .conf-head{
      font-size: 12px;
      font-weight: 650;
      letter-spacing:-0.01em;
      color: rgba(255,255,255,0.84);
      margin-bottom: 8px;
    }

    .conf-plot{
      width: 100%;
      height: 85px;
    }

    .leg-name{
      overflow:hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .table{
      width:100%;
      border-collapse: collapse;
      font-size: 12px;
      color: rgba(255,255,255,0.86);
      overflow:hidden;
      border-radius: 16px;
    }
    .table th,
    .table td{
      padding: 10px 10px;
      border-bottom: 1px solid rgba(255,255,255,0.10);
      text-align:left;
      vertical-align: top;
    }
    .table th{
      color: rgba(255,255,255,0.70);
      font-weight: 650;
      letter-spacing: -0.01em;
      background: rgba(255,255,255,0.04);
    }
    .table tr:hover td{
      background: rgba(255,255,255,0.04);
    }

    .small{
      color: rgba(255,255,255,0.62);
      font-size: 12px;
      margin-top: 8px;
    }

    .right-split{
      display:flex;
      gap: 12px;
      position:relative;
      width:100%;
      min-width:0;
      height: 100%;
      align-items: stretch;

      flex: 1 1 auto;
      min-height: 0;
    }

    #topicsStack{
      min-width:0;
      height: 100%;
      display:flex;
      flex-direction:column;
      min-height: 0;
      transition: flex-basis 520ms cubic-bezier(.2,.9,.2,1);
      will-change: flex-basis;
      flex: 0 0 100%;
      gap: 12px;
    }
    
    #topicsBox{
      min-width:0;
      display:flex;
      flex-direction:column;
      min-height: 0;
      transition: flex-basis 520ms cubic-bezier(.2,.9,.2,1);
      will-change: flex-basis;
      flex: 0 0 100%;
    }
    #topicSummBox{
      min-width:0;
      display:flex;
      flex-direction:column;
      overflow:hidden;
      opacity:0;
      pointer-events:none;
      transform: translate3d(0, 18px, 0);
      transition:
        opacity 220ms ease,
        transform 520ms cubic-bezier(.2,.9,.2,1),
        flex-basis 520ms cubic-bezier(.2,.9,.2,1);
      will-change: opacity, transform, flex-basis;
      flex: 0 0 0%;
      padding: 0;
    }

    .summ-inner{
      height: 100%;
      display:flex;
      flex-direction:column;
      min-height: 0;
      padding: 14px 14px;
    }
    
    #summBody{
      white-space: pre-wrap;
      
    }

    .summ-top{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap: 12px;
      flex: 0 0 auto;
    }

    .summ-tabs{
      display:flex;
      gap: 10px;
      align-items:center;
      flex: 0 0 auto;
      min-width: 0;
    }

    .summ-btn{
      padding: 9px 14px;
      font-size: 12px;
    }

    .summ-run-btn{
      padding: 9px 16px;
      font-size: 12px;
      flex: 0 0 auto;
    }

    .summ-run-btn.is-disabled{
      opacity: 0.42;
      cursor: not-allowed;
      pointer-events: none;
      filter: saturate(0.92);
    }

    .summ-run-btn.is-disabled:hover{
      animation: none;
      filter: none;
      background: rgba(0,0,0,0.18);
      border-color: rgba(255,255,255,0.18);
    }

    .summ-btn.is-active{
      background: rgba(255,255,255,0.10);
      border-color: rgba(255,255,255,0.32);
      filter: brightness(1.18);
    }
    
    #topicDetailsBox{
      min-width:0;
      height: 100%;
      display:flex;
      flex-direction:column;
      overflow:hidden;
      opacity:0;
      pointer-events:none;
      transform: translate3d(18px, 0, 0);
      transition:
        opacity 220ms ease,
        transform 520ms cubic-bezier(.2,.9,.2,1),
        flex-basis 520ms cubic-bezier(.2,.9,.2,1);
      will-change: opacity, transform, flex-basis;
      flex: 0 0 0%;
      padding: 14px 14px;
    }

    #rightSplit.split #topicsStack{
      flex-basis: var(--topicsWOpen);
      flex-shrink: 1;
    }

    #rightSplit.split #topicsBox{
      flex-basis: calc(100% - var(--topicSummH) - 12px);
    }

    #rightSplit.split #topicSummBox{
      flex-basis: var(--topicSummH);
      opacity:1;
      pointer-events:auto;
      transform: translate3d(0, 0, 0);
    }

    #rightSplit.split #topicDetailsBox{
      flex-basis: var(--detailsW);
      flex-shrink: 1;
      opacity:1;
      pointer-events:auto;
      transform: translate3d(0, 0, 0);
    }

    .topics-scroll{
      width:100%;
      overflow:auto;
      flex: 1 1 auto;
      min-height: 0;
      border-radius: 16px;
      padding-right: 6px;
    }

    .details-top{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap: 10px;
      flex: 0 0 auto;
    }

    .scroll{
      margin-top: 10px;
      flex: 1 1 auto;
      min-height: 0;
      overflow:auto;
      padding-right: 6px;
      border-radius: 14px;
    }

    #summBody{
      font-size: calc(1em - 3.5px);
      padding: 6px 12px 10px 12px;
      box-sizing: border-box;
    }

    .scroll::-webkit-scrollbar,
    .topics-scroll::-webkit-scrollbar{
      width: 10px;
    }
    .scroll::-webkit-scrollbar-track,
    .topics-scroll::-webkit-scrollbar-track{
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 999px;
    }
    .scroll::-webkit-scrollbar-thumb,
    .topics-scroll::-webkit-scrollbar-thumb{
      background: rgba(255,255,255,0.18);
      border: 1px solid rgba(255,255,255,0.14);
      border-radius: 999px;
    }
    .scroll::-webkit-scrollbar-thumb:hover,
    .topics-scroll::-webkit-scrollbar-thumb:hover{
      background: rgba(255,255,255,0.26);
    }

    @media (max-width: 980px){
      .single-grid{
        flex-direction: column;
      }

      .single-left{
        flex: 1 1 auto;
        min-width: 0;
      }

      .csv-grid{ flex-direction: column; }

      .csv-left{
        flex: 1 1 auto;
        transition: none;
      }
      #csv-panel.details-open .csv-left{
        flex-basis: auto;
      }

      .right-split{
        flex-direction: column;
        height: auto;
      }

      #topicsBox{
        flex: 1 1 auto;
        height: auto;
        transition: none;
      }

      #topicDetailsBox{
        flex: 1 1 auto;
        height: auto;
        transform: translate3d(0, 10px, 0);
        transition:
          opacity 220ms ease,
          transform 520ms cubic-bezier(.2,.9,.2,1);
      }

      #rightSplit.split #topicDetailsBox{
        transform: translate3d(0, 0, 0);
      }
    }

    @media (max-width: 720px){
      .cards{grid-template-columns:1fr}
      .brand{font-size: 28px}
      .title{font-size: 24px}
    }

    @media (prefers-reduced-motion: reduce){
      .view,
      .btn,
      .pill,
      .card,
      .wrap.stage-shift{
        transition: none !important;
        animation: none !important;
      }

      .csv-left,
      #topicsBox,
      #topicDetailsBox{
        transition: none !important;
      }
    }
  </style>
</head>
<body>
  <div class="noise"></div>
  <div class="wrap" id="stage">
"""

HTML_BEFORE_SCRIPT = r"""
  </div>

<script>
"""

HTML_SUFFIX = r"""
</script>
</body>
</html>
"""
