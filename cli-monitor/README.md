# API Test Machine - Terminal Monitor

Real-time terminal dashboard for monitoring API Test Machine services.

## Features

- **Server Status**: Online/offline, version, uptime
- **Process Detection**: Monitors API Server (port 8000) and Agent (port 8001)
- **Active Runs**: Progress bars and status for running tests
- **Recent Runs**: Pass/fail status for completed tests
- **Schedules**: Overview of enabled and paused schedules
- **Stats Summary**: Total runs, pass rate, active count
- **Keyboard Controls**: Refresh (R), Quit (Q)
- **Flicker-Free**: Double-buffered ANSI rendering

## Installation

### Build from Source

```bash
cd cli-monitor
swift build -c release
```

### Install Globally

```bash
# Option 1: User bin directory (recommended)
cp .build/release/ATMMonitor ~/bin/atm-monitor

# Option 2: System-wide (requires sudo)
sudo cp .build/release/ATMMonitor /usr/local/bin/atm-monitor
```

Ensure `~/bin` is in your PATH:
```bash
export PATH="$HOME/bin:$PATH"
```

## Usage

```bash
# Monitor localhost:8000 (default)
atm-monitor

# Monitor a specific server
atm-monitor -s http://api.example.com:8000

# Set refresh interval (seconds)
atm-monitor -r 5

# With API key authentication
atm-monitor -a your-api-key

# Or use environment variable
export ATM_API_KEY="your-api-key"
atm-monitor
```

### Command Line Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--server` | `-s` | `http://localhost:8000` | API server URL |
| `--api-key` | `-a` | (empty) | API key for auth |
| `--refresh` | `-r` | `3` | Refresh interval in seconds |
| `--help` | `-h` | - | Show help |
| `--version` | - | - | Show version |

### Keyboard Controls

| Key | Action |
|-----|--------|
| `R` | Force refresh |
| `Q` | Quit |

## Display Layout

```
═══ API TEST MACHINE MONITOR ═══                    [R:Refresh] [Q:Quit]

┌─ API TEST MACHINE ──────────────────────────────────────────────────┐
│ Server: ● ONLINE  Uptime: 2h 15m                                    │
│ Version: 0.1.0                                                      │
├─────────────────────────────────────────────────────────────────────┤
│ API Server: ● Running  (port 8000)                                  │
│ Agent/Scheduler: ● Running  (port 8001)                             │
└─────────────────────────────────────────────────────────────────────┘

┌─ ACTIVE RUNS (2) ───────────────────────────────────────────────────┐
│ API Load Test                                                       │
│   RUNNING  ████████████░░░░░░░░░ 450/1000                          │
│ Health Check                                                        │
│   PENDING  ░░░░░░░░░░░░░░░░░░░░░ 0/100                             │
└─────────────────────────────────────────────────────────────────────┘

┌─ RECENT COMPLETED ──────────────────────────────────────────────────┐
│ Production Test            PASSED  1000 reqs                        │
│ Staging API                FAILED  500 reqs                         │
└─────────────────────────────────────────────────────────────────────┘

┌─ SCHEDULES (Active: 3, Paused: 1) ──────────────────────────────────┐
│ ● Daily Health Check       [cron]  Runs: 45                         │
│ ● Hourly API Test          [interval]  Runs: 120                    │
│ ● Weekend Test             PAUSED                                   │
└─────────────────────────────────────────────────────────────────────┘

┌─ SUMMARY ───────────────────────────────────────────────────────────┐
│ Runs: 150  Active: 2  Passed: 140  Failed: 8                        │
│ Pass Rate: 95%                                                      │
└─────────────────────────────────────────────────────────────────────┘

─── Refresh: 3s │ Last: 14:30:45 ─────────────────────────────────────
```

## Project Structure

```
cli-monitor/
├── Package.swift              # Swift Package Manager config
└── Sources/ATMMonitor/
    ├── main.swift             # Entry point, argument parsing
    ├── MonitorConfig.swift    # Configuration struct
    ├── Dashboard.swift        # Main render loop
    ├── Widgets.swift          # UI section components
    ├── DataFetcher.swift      # HTTP client + process detection
    ├── Models.swift           # API response models
    ├── ANSIRenderer.swift     # Terminal colors and box drawing
    ├── TerminalBuffer.swift   # Double-buffered rendering
    └── KeyboardInput.swift    # Non-blocking keyboard handling
```

## Dependencies

- [swift-argument-parser](https://github.com/apple/swift-argument-parser) - CLI argument parsing
- [async-http-client](https://github.com/swift-server/async-http-client) - Async HTTP requests

## Requirements

- macOS 13.0+
- Swift 5.9+

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ATM_API_KEY` | API key (alternative to -a flag) |

## Troubleshooting

### "Server: OFFLINE" but server is running

1. Check the server URL is correct
2. Verify the server is accessible: `curl http://localhost:8000/health`
3. Check for firewall issues

### Display issues

If the display looks garbled:
1. Ensure your terminal supports ANSI escape codes
2. Try resizing the terminal window
3. Press `R` to force a full redraw

### Build errors

```bash
# Clean and rebuild
swift package clean
swift build -c release
```
