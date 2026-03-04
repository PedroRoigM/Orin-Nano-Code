const socket = io();
const portSelect = document.getElementById('port-select');
const connectBtn = document.getElementById('connect-btn');
const disconnectBtn = document.getElementById('disconnect-btn');
const terminal = document.getElementById('terminal');
const statusIndicator = document.getElementById('connection-status');

// Socket Events
socket.on('serial_data', (msg) => {
    appendTerminal(`[IN] ${msg.data}`, 'terminal-in');
});

socket.on('serial_error', (msg) => {
    appendTerminal(`[ERROR] ${msg.error}`, 'error-msg');
});

// Port Management
async function refreshPorts() {
    try {
        const response = await fetch('/ports');
        const ports = await response.json();
        portSelect.innerHTML = '<option value="">Select Port</option>';
        ports.forEach(port => {
            const opt = document.createElement('option');
            opt.value = port;
            opt.textContent = port;
            portSelect.appendChild(opt);
        });
    } catch (err) {
        appendTerminal('Failed to fetch ports', 'error-msg');
    }
}

document.getElementById('refresh-ports').onclick = refreshPorts;

connectBtn.onclick = async () => {
    const port = portSelect.value;
    if (!port) return alert('Select a port');

    const response = await fetch('/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ port, baudrate: 115200 })
    });

    const result = await response.json();
    if (result.status === 'connected') {
        setConnected(true, port);
    } else {
        alert(result.message);
    }
};

disconnectBtn.onclick = async () => {
    await fetch('/disconnect', { method: 'POST' });
    setConnected(false);
};

function setConnected(connected, port = '') {
    connectBtn.disabled = connected;
    disconnectBtn.disabled = !connected;
    portSelect.disabled = connected;
    statusIndicator.textContent = connected ? `Connected to ${port}` : 'Disconnected';
    statusIndicator.className = 'status-indicator ' + (connected ? 'success' : '');
    appendTerminal(connected ? `System connected to ${port}` : 'System disconnected', 'system-msg');
}

// Terminal Helpers
function appendTerminal(text, className) {
    const div = document.createElement('div');
    div.className = `terminal-line ${className}`;
    div.textContent = `${new Date().toLocaleTimeString()} - ${text}`;
    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;
}

document.getElementById('clear-terminal').onclick = () => {
    terminal.innerHTML = '';
};

// Command Sending
async function sendCommand(baseId, idElement, command) {
    const specificId = document.getElementById(idElement).value;
    const fullCommand = `${baseId}:${specificId}:${command}`;

    appendTerminal(`[OUT] ${fullCommand}`, 'terminal-out');

    try {
        const response = await fetch('/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: fullCommand })
        });
        const result = await response.json();
        if (result.status !== 'sent') {
            appendTerminal(`[SEND ERROR] ${result.message}`, 'error-msg');
        }
    } catch (err) {
        appendTerminal(`[FETCH ERROR] ${err.message}`, 'error-msg');
    }
}

// Specialized Commands
function sendLCDCommand() {
    const id = document.getElementById('lcd-id').value;
    const text = document.getElementById('lcd-text').value;
    sendCommand('LCD', 'lcd-id', text);
}

function sendBuzzerCommand() {
    const params = document.getElementById('buzz-params').value;
    sendCommand('BUZZ', 'buzz-id', params);
}

function sendMotorCommand(dir) {
    const speed = document.getElementById('mot-speed').value;
    sendCommand('MOT', 'mot-id', `${dir},${speed}`);
}

function sendEyesCommand() {
    const params = document.getElementById('eyes-iris').value;
    sendCommand('EYES', 'eyes-id', params);
}

function sendGazeCommand() {
    const params = document.getElementById('eyes-gaze').value;
    sendCommand('GAZE', 'eyes-id', params);
}

// UI Helpers
function showTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    event.target.classList.add('active');
    document.getElementById(`${tab}-tab`).classList.add('active');
}

// Initial Load
refreshPorts();
