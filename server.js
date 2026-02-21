const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');

const app = express();
const PORT = process.env.PORT || 5002;

// Enable CORS
app.use(cors());

// Serve static files with proper headers for PWA
app.use(express.static(path.join(__dirname, 'public'), {
    setHeaders: (res, path) => {
        // Set appropriate cache headers for PWA files
        if (path.endsWith('manifest.json')) {
            res.setHeader('Content-Type', 'application/manifest+json');
            res.setHeader('Cache-Control', 'no-cache');
        }
        if (path.endsWith('browserconfig.xml')) {
            res.setHeader('Content-Type', 'application/xml');
            res.setHeader('Cache-Control', 'no-cache');
        }
        // Cache static assets for PWA
        if (path.endsWith('.png') || path.endsWith('.ico') || path.endsWith('.jpg') || path.endsWith('.jpeg')) {
            res.setHeader('Cache-Control', 'public, max-age=31536000'); // 1 year
        }
        // Set proper MIME type for images
        if (path.endsWith('.jpg') || path.endsWith('.jpeg')) {
            res.setHeader('Content-Type', 'image/jpeg');
        }
    }
}));

// Config file path
const CONFIG_FILE = path.join(__dirname, 'controller-config.json');

// Load config from file
function loadConfig() {
    try {
        if (fs.existsSync(CONFIG_FILE)) {
            const config = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
            return config;
        }
    } catch (error) {
        console.error('Error loading config:', error);
    }
    return {
        pythonScriptPath: path.join(__dirname, 'teufel-power-hifi-controller.py'),
        lastCommand: null,
        volume: 25,
        currentInput: 'BLUETOOTH',
        muted: false,
        powered: false
    };
}

// Save config to file
function saveConfig(config) {
    try {
        fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
        console.log('Config saved');
    } catch (error) {
        console.error('Error saving config:', error);
    }
}

// Load initial config
let config = loadConfig();

// Middleware
app.use(express.json());

// Execute Python script command
function executeCommand(command, repeats = 1) {
    return new Promise((resolve, reject) => {
        const pythonPath = config.pythonScriptPath;
        const repeatArg = repeats > 1 ? ` --repeats ${repeats}` : '';
        const scriptCommand = `python3 ${pythonPath} --command ${command}${repeatArg}`;
        
        console.log(`Executing: ${scriptCommand}`);
        
        exec(scriptCommand, (error, stdout, stderr) => {
            if (error) {
                console.error(`Error: ${error}`);
                reject(error);
                return;
            }
            
            if (stderr) {
                console.error(`stderr: ${stderr}`);
            }
            
            console.log(`stdout: ${stdout}`);
            
            // Update config based on command
            config.lastCommand = command;
            saveConfig(config);
            
            resolve(stdout);
        });
    });
}

// API Routes

// Health check
app.get('/api/health', (req, res) => {
    res.json({
        status: 'OK',
        timestamp: new Date().toISOString(),
        config: config
    });
});

// Get current status
app.get('/api/status', (req, res) => {
    res.json({
        powered: config.powered,
        volume: config.volume,
        currentInput: config.currentInput,
        muted: config.muted,
        lastCommand: config.lastCommand
    });
});

// Power control
app.post('/api/power', async (req, res) => {
    try {
        await executeCommand('CMD_POWER');
        config.powered = !config.powered;
        saveConfig(config);
        res.json({ success: true, powered: config.powered });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Volume control
app.post('/api/volume', async (req, res) => {
    const { action, level } = req.body;
    
    try {
        let command = '';
        let repeats = 1;
        
        if (action === 'up') {
            command = 'CMD_VOLUME_UP';
            repeats = level || 1;
            config.volume = Math.min(50, config.volume + repeats);
        } else if (action === 'down') {
            command = 'CMD_VOLUME_DOWN';
            repeats = level || 1;
            config.volume = Math.max(0, config.volume - repeats);
        } else if (action === 'set' && level !== undefined) {
            // Calculate steps from current volume
            const steps = level - config.volume;
            if (steps > 0) {
                command = 'CMD_VOLUME_UP';
                repeats = steps;
            } else if (steps < 0) {
                command = 'CMD_VOLUME_DOWN';
                repeats = Math.abs(steps);
            }
            config.volume = level;
        }
        
        if (command && repeats > 0) {
            await executeCommand(command, repeats);
        }
        
        saveConfig(config);
        res.json({ success: true, volume: config.volume });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Mute control
app.post('/api/mute', async (req, res) => {
    try {
        await executeCommand('CMD_MUTE');
        config.muted = !config.muted;
        saveConfig(config);
        res.json({ success: true, muted: config.muted });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Input selection
app.post('/api/input', async (req, res) => {
    const { input } = req.body;
    
    const inputCommands = {
        'AUX': 'CMD_AUX',
        'LINE': 'CMD_LINE',
        'OPTICAL': 'CMD_OPT',
        'USB': 'CMD_USB',
        'BLUETOOTH': 'CMD_BLUETOOTH'
    };
    
    const command = inputCommands[input];
    if (!command) {
        return res.status(400).json({ error: 'Invalid input' });
    }
    
    try {
        await executeCommand(command);
        config.currentInput = input;
        saveConfig(config);
        res.json({ success: true, currentInput: config.currentInput });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// EQ Controls
app.post('/api/eq', async (req, res) => {
    const { type, action } = req.body;
    
    const eqCommands = {
        'bass': {
            'up': 'CMD_BASS_UP',
            'down': 'CMD_BASS_DOWN'
        },
        'mid': {
            'up': 'CMD_MID_UP',
            'down': 'CMD_MID_DOWN'
        },
        'treble': {
            'up': 'CMD_TREBLE_UP',
            'down': 'CMD_TREBLE_DOWN'
        }
    };
    
    const command = eqCommands[type]?.[action];
    if (!command) {
        return res.status(400).json({ error: 'Invalid EQ command' });
    }
    
    try {
        await executeCommand(command);
        res.json({ success: true, command: command });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Balance control
app.post('/api/balance', async (req, res) => {
    const { direction } = req.body;
    
    const balanceCommands = {
        'left': 'CMD_BAL_LEFT',
        'right': 'CMD_BAL_RIGHT'
    };
    
    const command = balanceCommands[direction];
    if (!command) {
        return res.status(400).json({ error: 'Invalid balance direction' });
    }
    
    try {
        await executeCommand(command);
        res.json({ success: true, command: command });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Navigation control
app.post('/api/navigation', async (req, res) => {
    const { direction } = req.body;
    
    const navCommands = {
        'left': 'CMD_LEFT',
        'right': 'CMD_RIGHT'
    };
    
    const command = navCommands[direction];
    if (!command) {
        return res.status(400).json({ error: 'Invalid navigation direction' });
    }
    
    try {
        await executeCommand(command);
        res.json({ success: true, command: command });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Serve the main HTML file
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Teufel Power HiFi Controller Server running on port ${PORT}`);
    console.log(`Open http://localhost:${PORT} in your browser`);
    console.log(`Python script path: ${config.pythonScriptPath}`);
});