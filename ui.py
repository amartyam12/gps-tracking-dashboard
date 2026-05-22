import os
from flask import Flask, request, jsonify, render_template_string, url_for
from dotenv import load_dotenv

# Import logic from main.py
from main import chat_with_model, read_sample_log, build_log_analysis_prompt

load_dotenv()

app = Flask(__name__)

PAGE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>GPS Log Analyzer</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='static.css') }}" />
  </head>
  <body>
    <div class="wrap">
      <header>
        <div>
          <h1>GPS Log Analyzer</h1>
          <div class="sub">View last lines of <code>sample.log</code> and extract unique movement records.</div>
        </div>
        <div class="row" style="justify-content:flex-end">
          <div>
            <label for="lastN">Last N lines</label><br/>
            <input id="lastN" type="number" min="1" step="1" value="200" />
          </div>
        </div>
      </header>

      <div class="row" style="margin-bottom: 12px">
        <button id="btnShow">Show log</button>
        <button id="btnAnalyze">Analyze log</button>
        <div id="status" class="status"></div>
      </div>

      <div class="grid">
        <div class="panel">
          <label>Log preview</label>
          <textarea id="logText" readonly></textarea>
        </div>
        <div class="panel">
          <label>Model output (ASCII table)</label>
          <div class="out"><pre id="analysisText">(output will appear here)</pre></div>
        </div>
      </div>
    </div>

    <script>
      const lastNEl = document.getElementById('lastN');
      const logTextEl = document.getElementById('logText');
      const analysisTextEl = document.getElementById('analysisText');
      const statusEl = document.getElementById('status');
      const btnShow = document.getElementById('btnShow');
      const btnAnalyze = document.getElementById('btnAnalyze');

      function setBusy(busy) {
        btnShow.disabled = busy;
        btnAnalyze.disabled = busy;
        statusEl.textContent = busy ? 'Working...' : '';
      }

      async function getJSON(url, params) {
        const u = new URL(url, window.location.origin);
        if (params) {
          for (const [k,v] of Object.entries(params)) u.searchParams.set(k, v);
        }
        const res = await fetch(u);
        const data = await res.json();
        if (!res.ok) throw new Error(data?.error || 'Request failed');
        return data;
      }

      btnShow.addEventListener('click', async () => {
        const lastN = Number(lastNEl.value || 200);
        setBusy(true);
        try {
          const data = await getJSON('/api/log', { last_n_lines: lastN });
          logTextEl.value = data.log_text;
          analysisTextEl.textContent = '(output will appear here)';
        } catch (e) {
          statusEl.textContent = e.message;
          statusEl.classList.add('err');
        } finally {
          setBusy(false);
        }
      });

      btnAnalyze.addEventListener('click', async () => {
        const lastN = Number(lastNEl.value || 200);
        setBusy(true);
        try {
          analysisTextEl.textContent = '';
          const data = await getJSON('/api/analyze', { last_n_lines: lastN });
          analysisTextEl.textContent = data.analysis;
        } catch (e) {
          statusEl.textContent = e.message;
          statusEl.classList.add('err');
        } finally {
          setBusy(false);
        }
      });

      // initial load
      btnShow.click();
    </script>
  </body>
</html>
"""


@app.get('/')
def index():
    return render_template_string(PAGE)


@app.get('/api/log')
def api_log():
    try:
        last_n_lines = request.args.get('last_n_lines', default=200, type=int)
        return jsonify({"log_text": read_sample_log(path="sample.log", last_n_lines=last_n_lines)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.get('/api/analyze')
def api_analyze():
    try:
        last_n_lines = request.args.get('last_n_lines', default=200, type=int)
        log_text = read_sample_log(path="sample.log", last_n_lines=last_n_lines)
        prompt = build_log_analysis_prompt(log_text)
        analysis = chat_with_model(prompt)
        return jsonify({"analysis": analysis})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == '__main__':
    # Running locally: http://127.0.0.1:5000/
    app.run(host='127.0.0.1', port=5000, debug=True)

