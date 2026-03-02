// DOM Elements
const statusEl = document.getElementById('status');
const recordBtn = document.getElementById('recordBtn');
const recordRipple = document.getElementById('recordRipple');
const transcriptEl = document.getElementById('transcript');
const logsListEl = document.getElementById('logs-list');

// Tab Navigation Logic
const tabBtns = document.querySelectorAll('.tab-btn');
const tabPanels = document.querySelectorAll('.tab-panel');

tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        // Deactivate all
        tabBtns.forEach(b => b.classList.remove('active', 'text-white', 'bg-brand-500', 'shadow-lg'));
        tabBtns.forEach(b => b.classList.add('text-gray-400'));
        tabPanels.forEach(p => p.classList.add('hidden'));

        // Activate current
        btn.classList.add('active', 'text-white');
        btn.classList.remove('text-gray-400');
        const targetId = btn.getAttribute('data-target') + '-panel';
        document.getElementById(targetId).classList.remove('hidden');
        
        // Refresh charts if needed
        if (targetId === 'stats-panel' && chartInstance) {
            chartInstance.resize();
        }
    });
});

// Generate Unique Client ID for WebSocket
const clientId = crypto.randomUUID();
// Setup WebSocket
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/${clientId}`;
let ws = null;

function updateStatus(text, type = 'normal') {
    const icon = type === 'success' ? 'fa-check-circle text-green-500' : 
                 type === 'error' ? 'fa-exclamation-circle text-red-500' : 
                 type === 'processing' ? 'fa-spinner fa-spin text-brand-500' : 'fa-circle text-gray-500';
    
    statusEl.innerHTML = `<i class="fas ${icon} text-[8px] mr-1.5"></i>${text}`;
    
    if (type === 'processing') {
        statusEl.classList.add('bg-brand-900/30', 'text-brand-400', 'border-brand-500/30');
    } else {
        statusEl.classList.remove('bg-brand-900/30', 'text-brand-400', 'border-brand-500/30');
    }
}

function connectWs() {
    ws = new WebSocket(wsUrl);
    ws.onopen = () => {
        console.log("WS Connected");
        updateStatus("在线", "success");
    };
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'task_completed') {
                updateStatus(data.status === 'completed' ? '处理完成' : '处理失败', data.status === 'completed' ? 'success' : 'error');
                
                if (data.transcript) {
                     transcriptEl.textContent = data.transcript;
                     transcriptEl.parentElement.classList.remove('hidden');
                }
                
                // Show notification/toast could go here
                
                fetchLogs();
                fetchStats();
            }
        } catch (e) {
            console.error("WS Parse Error", e);
        }
    };
    ws.onclose = () => {
        console.log("WS Closed, reconnecting in 3s...");
        updateStatus("离线 (重连中...)", "error");
        setTimeout(connectWs, 3000);
    };
}
connectWs();

let mediaRecorder;
let chunks = [];

async function initRecorder(){
  try{
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
    mediaRecorder.onstop = onStop;
    // updateStatus('准备就绪', 'normal');
  }catch(e){
    updateStatus('需麦克风权限', 'error');
    console.error(e);
  }
}

function onStop(){
  const blob = new Blob(chunks, { type: 'audio/webm' });
  chunks = [];
  
  // Stop Animation
  recordRipple.classList.remove('animate-ripple', 'opacity-60');
  recordRipple.classList.add('opacity-0');
  
  updateStatus('上传中...', 'processing');
  
  const fd = new FormData();
  fd.append('file', blob, 'recording.webm');
  fd.append('client_id', clientId);
  
  fetch('/api/v1/voice', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(j => {
      updateStatus('AI 分析中...', 'processing');
      transcriptEl.textContent = `...`; 
      
      // Refresh list immediately to show "processing" state
      fetchLogs(); 
    })
    .catch(err => {
      updateStatus('上传失败', 'error');
      transcriptEl.textContent = err.message;
    });
}

// Record Button Interaction
recordBtn.addEventListener('mousedown', (e) => {
  e.preventDefault(); // Prevent focus issues
  if(!mediaRecorder) return;
  chunks = [];
  try {
      mediaRecorder.start();
      transcriptEl.textContent = "正在听...";
      // Start Animation
      recordRipple.classList.remove('opacity-0');
      recordRipple.classList.add('animate-ripple', 'opacity-60');
      recordBtn.classList.add('scale-95', 'border-brand-500');
  } catch (err) {
      console.error(err);
  }
});

const stopRecording = () => {
  if(mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
      recordBtn.classList.remove('scale-95', 'border-brand-500');
  }
};

recordBtn.addEventListener('mouseup', stopRecording);
recordBtn.addEventListener('mouseleave', stopRecording);
recordBtn.addEventListener('touchstart', (e) => {
    e.preventDefault();
    if(!mediaRecorder) return;
    chunks = [];
    mediaRecorder.start();
    transcriptEl.textContent = "正在听...";
    recordRipple.classList.remove('opacity-0');
    recordRipple.classList.add('animate-ripple', 'opacity-60');
    recordBtn.classList.add('scale-95', 'border-brand-500');
});
recordBtn.addEventListener('touchend', stopRecording);


function fetchLogs() {
  fetch('/api/v1/logs')
    .then(r => r.json())
    .then(logs => {
      if (logs.length === 0) {
        logsListEl.innerHTML = '<div class="text-center text-gray-500 py-10">暂无训练记录</div>';
        return;
      }
      logsListEl.innerHTML = logs.map(log => `
        <div class="bg-gray-800 rounded-2xl p-4 shadow-sm border border-gray-700/50 hover:border-brand-500/30 transition-colors">
          <div class="flex justify-between items-start mb-2">
            <span class="text-xs font-mono text-gray-500">#${log.id}</span>
            <span class="text-xs text-gray-400">${new Date(log.created_at).toLocaleString([], {month:'numeric', day:'numeric', hour:'2-digit', minute:'2-digit'})}</span>
          </div>
          
          <div class="text-gray-300 text-sm mb-3 pl-2 border-l-2 border-gray-700">
            ${log.transcript || '<span class="italic text-gray-600">正在处理音频...</span>'}
          </div>
          
          ${(log.exercise || log.weight) ? `
          <div class="bg-gray-900/50 rounded-xl p-3 mb-2 flex flex-col gap-1">
             <div class="font-bold text-brand-400 text-sm">${log.exercise || '未识别动作'}</div>
             <div class="flex items-center gap-3 text-sm text-gray-300">
               ${log.weight ? `<span class="bg-gray-800 px-2 py-0.5 rounded text-xs">🏋️ ${log.weight}kg</span>` : ''}
               ${log.sets ? `<span class="bg-gray-800 px-2 py-0.5 rounded text-xs">🔢 ${log.sets}组</span>` : ''}
               ${log.reps ? `<span class="bg-gray-800 px-2 py-0.5 rounded text-xs">🔁 ${log.reps}次</span>` : ''}
             </div>
          </div>` : ''}

          ${log.feedback ? `
          <div class="mt-2 text-xs text-green-400 bg-green-900/10 border border-green-900/30 p-2 rounded-lg flex items-start gap-2">
            <i class="fas fa-lightbulb mt-0.5"></i>
            <span>${log.feedback}</span>
          </div>` : ''}
          
          ${log.status === 'processing' ? `
            <div class="mt-2 flex items-center gap-2 text-xs text-brand-400 animate-pulse">
                <i class="fas fa-circle-notch fa-spin"></i> AI 正在分析中...
            </div>
          ` : ''}
        </div>
      `).join('');
    })
    .catch(e => logsListEl.innerHTML = '<div class="text-center text-red-400">加载失败</div>');
}

let chartInstance = null;

function fetchStats() {
    fetch('/api/v1/stats/progress')
    .then(r => r.json())
    .then(stats => {
        const ctx = document.getElementById('progressChart').getContext('2d');
        
        const exercises = Object.keys(stats);
        if (exercises.length === 0) return;

        // 1. Get all unique sorted dates
        let allDates = new Set();
        Object.values(stats).forEach(list => list.forEach(item => allDates.add(item.date)));
        allDates = Array.from(allDates).sort();
        
        // 2. Map data to these dates
        const colors = ['#38bdf8', '#818cf8', '#34d399', '#f472b6', '#fbbf24'];
        const datasets = exercises.map((ex, i) => {
            const dataMap = {};
            stats[ex].forEach(item => dataMap[item.date] = item.weight);
            
            const data = allDates.map(date => dataMap[date] || null);
            
            return {
                label: ex,
                data: data,
                borderColor: colors[i % colors.length],
                backgroundColor: colors[i % colors.length] + '20', // Add transparency
                fill: true,
                spanGaps: true,
                tension: 0.4,
                pointBackgroundColor: '#1f2937',
                pointBorderWidth: 2,
                pointRadius: 4
            };
        });
        
        if (chartInstance) {
            chartInstance.destroy();
        }
        
        Chart.defaults.color = '#9ca3af';
        Chart.defaults.borderColor = '#374151';

         chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: allDates.map(d => new Date(d).toLocaleString(undefined, {month:'numeric', day:'numeric'})),
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#e5e7eb',
                            font: { family: "'Inter', sans-serif", size: 11 }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#1f2937',
                        titleColor: '#f3f4f6',
                        bodyColor: '#d1d5db',
                        borderColor: '#374151',
                        borderWidth: 1,
                        padding: 10,
                        cornerRadius: 8,
                        displayColors: true
                    }
                },
                scales: {
                    y: {
                        grid: { color: '#374151' },
                        ticks: { color: '#9ca3af' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#9ca3af' }
                    }
                }
            }
        });
    })
    .catch(e => console.error("Chart error:", e));
}

initRecorder();
fetchLogs();
fetchStats();

// Plan Generation Logic
const generatePlanBtn = document.getElementById('generatePlanBtn');
const planResult = document.getElementById('planResult');
const goalSelect = document.getElementById('goalSelect');

generatePlanBtn.addEventListener('click', () => {
    const goal = goalSelect.value;
    const btnContent = generatePlanBtn.innerHTML;
    
    generatePlanBtn.disabled = true;
    generatePlanBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> <span>正在生成...</span>`;
    
    planResult.classList.remove('hidden');
    planResult.innerHTML = `
        <div class="bg-gray-800 rounded-2xl p-6 text-center animate-pulse">
            <div class="text-brand-400 mb-2"><i class="fas fa-brain fa-2x"></i></div>
            <p class="text-gray-400 text-sm">AI 正在分析您的历史表现...</p>
            <p class="text-gray-500 text-xs mt-1">可能需要 10-20 秒</p>
        </div>
    `;

    const fd = new FormData();
    fd.append('goal', goal);

    fetch('/api/v1/plan/generate', {
        method: 'POST',
        body: fd
    })
    .then(r => r.json())
    .then(plan => {
        generatePlanBtn.disabled = false;
        generatePlanBtn.innerHTML = btnContent;
        
        if (plan.error) {
            planResult.innerHTML = `
                <div class="bg-red-900/20 border border-red-500/30 rounded-xl p-4 text-center">
                    <p class="text-red-400 text-sm"><i class="fas fa-exclamation-triangle mr-1"></i> 生成失败: ${plan.error}</p>
                </div>
            `;
            return;
        }

        // Render Plan
        let html = `
            <div class="bg-gray-800 rounded-3xl p-6 shadow-2xl border border-gray-700 animate-fade-in">
                <div class="flex justify-between items-start mb-6">
                    <div>
                        <h3 class="text-xl font-bold text-white">${plan.plan_name || '定制训练计划'}</h3>
                        <div class="text-xs text-brand-400 mt-1 uppercase tracking-wider font-bold">Based on ${goal}</div>
                    </div>
                    <div class="bg-brand-500/10 text-brand-400 p-2 rounded-lg">
                        <i class="fas fa-calendar-alt"></i>
                    </div>
                </div>
                
                <p class="text-gray-400 text-sm mb-6 leading-relaxed bg-gray-900/50 p-3 rounded-xl border border-gray-700/50">
                    ${plan.overview || '暂无概述'}
                </p>
                
                <div class="space-y-4">`;
        
        if (plan.schedule && Array.isArray(plan.schedule)) {
            plan.schedule.forEach(day => {
                html += `
                <div class="bg-gray-900/80 rounded-xl p-4 border-l-4 border-brand-500 overflow-hidden relative">
                    <div class="flex justify-between items-center mb-3">
                        <h4 class="font-bold text-gray-200">${day.day}</h4>
                        <span class="text-xs font-medium px-2 py-1 rounded bg-gray-800 text-gray-400 border border-gray-700">${day.focus}</span>
                    </div>
                    
                    <ul class="space-y-3">
                        ${day.exercises.map(ex => `
                            <li class="relative pl-4 border-l border-gray-700">
                                <div class="flex justify-between items-baseline">
                                    <strong class="text-sm text-gray-300">${ex.name}</strong>
                                    <span class="text-xs text-brand-500 font-mono">${ex.sets}x${ex.reps}</span>
                                </div>
                                ${ex.notes ? `<p class="text-[10px] text-gray-500 mt-0.5">${ex.notes}</p>` : ''}
                            </li>
                        `).join('')}
                    </ul>
                </div>
                `;
            });
        }
        
        html += `   </div>
                <div class="mt-6 text-center">
                    <button onclick="document.getElementById('plan-panel').classList.add('hidden'); document.querySelector('[data-target=\\'plan\\']').click();" class="text-xs text-gray-500 hover:text-white transition-colors">收起计划</button>
                </div>
            </div>`;
        
        planResult.innerHTML = html;
    })
    .catch(e => {
        generatePlanBtn.disabled = false;
        generatePlanBtn.innerHTML = btnContent;
        planResult.innerHTML = `
            <div class="bg-red-900/20 border border-red-500/30 rounded-xl p-4 text-center">
                <p class="text-red-400 text-sm">请求错误: ${e.message}</p>
            </div>
        `;
    });
});
