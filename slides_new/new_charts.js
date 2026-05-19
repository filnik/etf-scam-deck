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
