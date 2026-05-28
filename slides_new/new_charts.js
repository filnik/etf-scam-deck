    if (id.startsWith('chart-anatomy-')) {
      const crashId = id.replace('chart-anatomy-', '');
      const D = JSON.parse(document.getElementById('crash-anatomy-data').textContent);
      const N = JSON.parse(document.getElementById('crash-anatomy-narratives').textContent);
      const c = D.find(x => x.id === crashId);
      const cn = N.find(x => x.id === crashId);
      if (!c) return;

      const dates = c.spy_series.dates;
      const prices = c.spy_series.prices;
      const dds = c.spy_series.drawdown_pct;

      function nearestIdx(arr, target) {
        if (!target) return -1;
        const t = new Date(target).getTime();
        let best = -1, bestDiff = Infinity;
        for (let i = 0; i < arr.length; i++) {
          const d = Math.abs(new Date(arr[i]).getTime() - t);
          if (d < bestDiff) { bestDiff = d; best = i; }
        }
        return best;
      }

      const peakIdx = nearestIdx(dates, c.peak && c.peak.date);
      const troughIdx = nearestIdx(dates, c.trough && c.trough.date);
      const fireIdx = c.v14b_fire && c.v14b_fire.date ? nearestIdx(dates, c.v14b_fire.date) : -1;
      const entryIdx = c.catalyst_entry && c.catalyst_entry.date ? nearestIdx(dates, c.catalyst_entry.date) : -1;

      const ann = {};
      if (peakIdx >= 0) {
        ann.peak = { type: 'line', scaleID: 'x', value: peakIdx,
          borderColor: 'rgba(255,165,2,0.40)', borderWidth: 1.2, borderDash: [3, 4],
          label: { display: true, content: 'ATH', position: 'start',
            backgroundColor: '#ffa502', color: '#0f0f1a', font: { size: 9, weight: 700 },
            padding: { x: 5, y: 2 }, borderRadius: 3 } };
      }
      if (troughIdx >= 0) {
        ann.trough = { type: 'line', scaleID: 'x', value: troughIdx,
          borderColor: 'rgba(255,71,87,0.45)', borderWidth: 1.2, borderDash: [3, 4],
          label: { display: true, content: 'bottom', position: 'end',
            backgroundColor: '#ff4757', color: '#fff', font: { size: 9, weight: 700 },
            padding: { x: 5, y: 2 }, borderRadius: 3 } };
      }
      if (fireIdx >= 0) {
        ann.fire = { type: 'line', scaleID: 'x', value: fireIdx,
          borderColor: '#ff4757', borderWidth: 2.4,
          label: { display: true, content: '✖ SELL', position: 'start',
            backgroundColor: '#ff4757', color: '#fff', font: { size: 11, weight: 800 },
            padding: { x: 7, y: 3 }, borderRadius: 4, yAdjust: 14 } };
      }
      if (entryIdx >= 0) {
        ann.entry = { type: 'line', scaleID: 'x', value: entryIdx,
          borderColor: '#00d26a', borderWidth: 2.4,
          label: { display: true, content: '✔ BUY', position: 'end',
            backgroundColor: '#00d26a', color: '#0f0f1a', font: { size: 11, weight: 800 },
            padding: { x: 7, y: 3 }, borderRadius: 4, yAdjust: 14 } };
      }

      const eventPoints = [];
      if (cn && cn.events) {
        cn.events.forEach(e => {
          const idx = nearestIdx(dates, e.date);
          if (idx >= 0) eventPoints.push({ x: idx, y: prices[idx], label: e.label, desc: e.description });
        });
      }

      const ddMin = Math.min(...dds);
      const ddAxisMin = Math.floor(ddMin / 10) * 10 - 5;

      new Chart(ctx, {
        type: 'line',
        data: {
          labels: dates,
          datasets: [
            {
              label: 'S&P 500',
              data: prices,
              borderColor: '#64d2ff',
              backgroundColor: 'transparent',
              borderWidth: 1.6, tension: 0.1, pointRadius: 0, pointHoverRadius: 0,
              yAxisID: 'y', order: 2,
            },
            {
              label: 'Drawdown',
              data: dds,
              borderColor: 'rgba(255,71,87,0.6)',
              backgroundColor: 'rgba(255,71,87,0.10)',
              borderWidth: 0.8, tension: 0.1, pointRadius: 0, pointHoverRadius: 0,
              fill: 'origin', yAxisID: 'y2', order: 3,
            },
            {
              type: 'scatter',
              label: 'Eventi',
              data: eventPoints,
              backgroundColor: '#ffdb4d',
              borderColor: '#0f0f1a',
              borderWidth: 1.5,
              pointRadius: 7, pointHoverRadius: 11, pointStyle: 'rectRot',
              yAxisID: 'y', order: 1,
              showLine: false,
            }
          ]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          interaction: { mode: 'nearest', intersect: false, axis: 'x' },
          plugins: {
            legend: { display: false },
            annotation: { annotations: ann },
            tooltip: {
              backgroundColor: '#1a1a36', borderColor: 'rgba(255,255,255,0.12)',
              borderWidth: 1, padding: 12, titleFont: { size: 12 }, bodyFont: { size: 12 },
              callbacks: {
                title: (items) => {
                  if (!items.length) return '';
                  const i = items[0].dataIndex;
                  return dates[i] || '';
                },
                label: (c) => {
                  if (c.dataset.label === 'S&P 500')   return 'SPY: ' + c.parsed.y.toFixed(2);
                  if (c.dataset.label === 'Drawdown')  return 'DD:  ' + c.parsed.y.toFixed(1) + '%';
                  if (c.dataset.label === 'Eventi')    return (c.raw.label || '') + ' — ' + (c.raw.desc || '');
                  return '';
                }
              }
            }
          },
          scales: {
            y:  { position: 'left',
              grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { font: { family: "'JetBrains Mono'", size: 10 }, color: '#b0b0c0' },
              title: { display: true, text: 'SPY', color: '#7a7a90', font: { size: 10 } } },
            y2: { position: 'right',
              min: ddAxisMin, max: 5,
              grid: { display: false },
              ticks: { callback: v => v + '%', font: { family: "'JetBrains Mono'", size: 9 }, color: '#ff4757' },
              title: { display: true, text: 'DD', color: '#ff4757', font: { size: 10 } } },
            x:  { grid: { display: false },
              ticks: {
                font: { family: "'JetBrains Mono'", size: 9 }, color: '#7a7a90',
                maxRotation: 0, autoSkip: true, maxTicksLimit: 8,
                callback: function(v) {
                  const d = this.getLabelForValue(v);
                  return d ? d.slice(0, 7) : '';
                }
              } }
          }
        }
      });
    }

    if (id === 'chart-lost-1966') {
      const D = JSON.parse(document.getElementById('lost-decades-data').textContent);
      const p = D.periods.find(x => x.id === 'stagflation_1966');
      const t = p.timeline;
      const ldIdx = t.lost_decade_end_idx;
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: t.dates.map(d => d.slice(0, 4)),
          datasets: [{
            label: 'S&P 500 · valore reale (100 = 1966)',
            data: t.real_index,
            borderColor: '#ff4757',
            backgroundColor: 'rgba(255,71,87,0.07)',
            borderWidth: 2.5, tension: 0.15, pointRadius: 0, pointHoverRadius: 5, fill: true,
            segment: { borderColor: c => c.p1DataIndex > ldIdx ? '#00d26a' : '#ff4757' }
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            annotation: { annotations: {
              base100: { type: 'line', yMin: 100, yMax: 100, borderColor: 'rgba(255,255,255,0.22)', borderWidth: 1, borderDash: [4, 4] },
              ldEnd: { type: 'line', scaleID: 'x', value: ldIdx, borderColor: '#ffa502', borderWidth: 2, borderDash: [6, 4],
                label: { display: true, content: '1982 · qui molli al fondo', position: 'start', backgroundColor: '#ffa502', color: '#0f0f1a', font: { size: 11, weight: 700 } } }
            } },
            tooltip: { backgroundColor: '#1a1a36', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1, padding: 12,
              callbacks: { label: c => 'Valore reale: ' + c.parsed.y.toFixed(0) + ' (100 = 1966)' } }
          },
          scales: {
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { font: { family: "'JetBrains Mono'" } },
              title: { display: true, text: 'Valore reale · inflation-adjusted', color: '#7a7a90', font: { size: 12 } } },
            x: { grid: { display: false }, ticks: { font: { family: "'JetBrains Mono'", size: 11 }, color: '#b0b0c0', maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } }
          }
        }
      });
    }

    if (id === 'chart-pac-12m') {
      const D = JSON.parse(document.getElementById('v1-charts-data').textContent).last12m;
      const order = ['SPY', 'IWMO-Top2-Hyst', 'QQQ', 'Top2-EW-Hyst', 'NoRot2', 'Mom-Top2-Hyst', 'P/E Switch'];
      const colors = {
        'SPY': '#ff4757', 'QQQ': '#ffa502', 'Top2-EW-Hyst': '#00d9ff',
        'NoRot2': '#00d26a', 'Mom-Top2-Hyst': '#c77dff', 'P/E Switch': '#0a84ff',
        'IWMO-Top2-Hyst': '#9b7fb0'
      };
      const mesi = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic'];
      const labels = D['SPY'].dates.map(d => mesi[parseInt(d.slice(5, 7), 10) - 1] + " '" + d.slice(2, 4));
      const datasets = order.map(name => ({
        label: name,
        data: D[name].value,
        borderColor: colors[name],
        backgroundColor: 'transparent',
        borderWidth: (name === 'P/E Switch' || name === 'Mom-Top2-Hyst') ? 3.5 : 2.5,
        tension: 0.3, pointRadius: 0, pointHoverRadius: 6, fill: false
      }));
      datasets.push({
        label: 'Investito (€13K)',
        data: D['SPY'].invested,
        borderColor: 'rgba(255,255,255,0.35)',
        backgroundColor: 'transparent',
        borderWidth: 1.5, borderDash: [5, 4], tension: 0,
        pointRadius: 0, pointHoverRadius: 0, fill: false
      });
      new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { position: 'top', align: 'end',
              labels: { usePointStyle: true, pointStyle: 'line', padding: 14, font: { weight: 600, size: 12 } } },
            tooltip: { mode: 'index', intersect: false, backgroundColor: '#1a1a36',
              borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1, padding: 12,
              callbacks: { label: c => c.dataset.label + ': €' + c.parsed.y.toLocaleString('it-IT') } }
          },
          scales: {
            y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { callback: v => '€' + (v / 1000).toFixed(0) + 'K', font: { family: "'JetBrains Mono'" } } },
            x: { grid: { display: false },
              ticks: { font: { family: "'JetBrains Mono'", size: 11 }, color: '#b0b0c0', maxRotation: 0, autoSkip: true, maxTicksLimit: 13 } }
          }
        }
      });
    }

    if (id === 'chart-iwmo-history') {
      const root = JSON.parse(document.getElementById('v1-charts-data').textContent);
      const H = root.iwmo_history;
      const labels = root.iwmo_history_years;
      const order = ['SPY', 'IWMO ETF', 'IWMO-Top2-Hyst', 'Mom-Top2-Hyst'];
      const colors = {
        'SPY': '#ff4757', 'IWMO ETF': '#ffa502',
        'IWMO-Top2-Hyst': '#0a84ff', 'Mom-Top2-Hyst': '#c77dff'
      };
      const datasets = order.map(name => ({
        label: name,
        data: H[name].yearly_value,
        borderColor: colors[name],
        backgroundColor: name === 'Mom-Top2-Hyst' ? 'rgba(199,125,255,0.10)' : 'transparent',
        borderWidth: (name === 'Mom-Top2-Hyst' || name === 'IWMO-Top2-Hyst') ? 3.5 : 2.5,
        tension: 0.3, pointRadius: 0, pointHoverRadius: 6,
        fill: name === 'Mom-Top2-Hyst'
      }));
      new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { position: 'top', align: 'end',
              labels: { usePointStyle: true, pointStyle: 'line', padding: 14, font: { weight: 600, size: 12 } } },
            tooltip: { mode: 'index', intersect: false, backgroundColor: '#1a1a36',
              borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1, padding: 12,
              callbacks: { label: c => c.dataset.label + ': €' + c.parsed.y.toLocaleString('it-IT') } }
          },
          scales: {
            y: { type: 'logarithmic', grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { callback: v => {
                  const f = Math.log10(v) % 1;
                  const nice = Math.abs(f) < 0.04 || Math.abs(f - 1) < 0.04 || Math.abs(f - 0.4771) < 0.05;
                  return nice ? '€' + (v >= 1e6 ? (v / 1e6) + 'M' : (v / 1e3) + 'K') : '';
                }, font: { family: "'JetBrains Mono'" } },
              title: { display: true, text: 'Valore PAC (€) · scala log', color: '#7a7a90', font: { size: 11 } } },
            x: { grid: { display: false },
              ticks: { font: { family: "'JetBrains Mono'", size: 11 }, color: '#b0b0c0', maxRotation: 0 } }
          }
        }
      });
    }

    if (id === 'chart-lost-2000') {
      const D = JSON.parse(document.getElementById('lost-decades-data').textContent);
      const p = D.periods.find(x => x.id === 'lost_2000');
      const t = p.timeline;
      const ldIdx = t.lost_decade_end_idx;
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: t.dates.map(d => d.slice(0, 4)),
          datasets: [{
            label: 'S&P 500 · valore reale (100 = 2000)',
            data: t.real_index,
            borderColor: '#ff4757',
            backgroundColor: 'rgba(255,71,87,0.07)',
            borderWidth: 2.5, tension: 0.15, pointRadius: 0, pointHoverRadius: 5, fill: true,
            segment: { borderColor: c => c.p1DataIndex > ldIdx ? '#00d26a' : '#ff4757' }
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            annotation: { annotations: {
              base100: { type: 'line', yMin: 100, yMax: 100, borderColor: 'rgba(255,255,255,0.22)', borderWidth: 1, borderDash: [4, 4] },
              ldEnd: { type: 'line', scaleID: 'x', value: ldIdx, borderColor: '#ffa502', borderWidth: 2, borderDash: [6, 4],
                label: { display: true, content: '2013 · qui molli al fondo', position: 'start', backgroundColor: '#ffa502', color: '#0f0f1a', font: { size: 11, weight: 700 } } }
            } },
            tooltip: { backgroundColor: '#1a1a36', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1, padding: 12,
              callbacks: { label: c => 'Valore reale: ' + c.parsed.y.toFixed(0) + ' (100 = 2000)' } }
          },
          scales: {
            y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { font: { family: "'JetBrains Mono'" } },
              title: { display: true, text: 'Valore reale · inflation-adjusted', color: '#7a7a90', font: { size: 12 } } },
            x: { grid: { display: false }, ticks: { font: { family: "'JetBrains Mono'", size: 11 }, color: '#b0b0c0', maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } }
          }
        }
      });
    }

    if (id === 'chart-single-name') {
      const root = JSON.parse(document.getElementById('v1-charts-data').textContent);
      const H = root.single_name;
      const labels = root.single_name_years;
      const order = ['solo AVGO', 'NoRot2', 'solo NVDA'];
      const colors = { 'solo NVDA': '#00d26a', 'solo AVGO': '#00d9ff', 'NoRot2': '#ffa502' };
      const datasets = order.map(name => ({
        label: name,
        data: H[name].yearly_value,
        borderColor: colors[name],
        backgroundColor: name === 'NoRot2' ? 'rgba(255,165,2,0.10)' : 'transparent',
        borderWidth: name === 'NoRot2' ? 3.5 : 2.5,
        tension: 0.3, pointRadius: 0, pointHoverRadius: 6,
        fill: name === 'NoRot2'
      }));
      new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { position: 'top', align: 'end',
              labels: { usePointStyle: true, pointStyle: 'line', padding: 14, font: { weight: 600, size: 12 } } },
            tooltip: { mode: 'index', intersect: false, backgroundColor: '#1a1a36',
              borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1, padding: 12,
              callbacks: { label: c => c.dataset.label + ': €' + c.parsed.y.toLocaleString('it-IT') } }
          },
          scales: {
            y: { type: 'logarithmic', grid: { color: 'rgba(255,255,255,0.05)' },
              ticks: { callback: v => {
                  const f = Math.log10(v) % 1;
                  const nice = Math.abs(f) < 0.04 || Math.abs(f - 1) < 0.04 || Math.abs(f - 0.4771) < 0.05;
                  return nice ? '€' + (v >= 1e6 ? (v / 1e6) + 'M' : (v / 1e3) + 'K') : '';
                }, font: { family: "'JetBrains Mono'" } },
              title: { display: true, text: 'Valore PAC (€) · scala log', color: '#7a7a90', font: { size: 11 } } },
            x: { grid: { display: false },
              ticks: { font: { family: "'JetBrains Mono'", size: 11 }, color: '#b0b0c0', maxRotation: 0 } }
          }
        }
      });
    }
