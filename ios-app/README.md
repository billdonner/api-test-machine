# API Test Machine - iOS App

Native SwiftUI application for iOS 16+ providing mobile access to API Test Machine.

## Features

- **Dashboard**: Live polling with grouped run list and stats
- **Run Details**: Metrics visualization with Swift Charts
- **Test Creation**: Full test configuration with multi-endpoint support
- **Schedule Management**: Create, pause, resume, and delete schedules
- **Settings**: Secure API key storage using iOS Keychain

## Requirements

- iOS 16.0+
- Xcode 15+
- Swift 5.9+

## Setup

1. Open the project in Xcode:
   ```bash
   cd ios-app/APITestMachine
   open APITestMachine.xcodeproj
   ```

2. Configure the API server URL in Settings (default: `http://localhost:8000`)

3. Optionally set an API key for authentication

4. Build and run on simulator or device

## Project Structure

```
APITestMachine/
├── App/
│   ├── APITestMachineApp.swift      # @main entry point
│   └── ContentView.swift             # Tab-based navigation
├── Models/
│   ├── TestSpec.swift                # Test configuration + JSONValue
│   ├── RunResult.swift               # Run summary/detail
│   ├── Metrics.swift                 # Performance metrics
│   ├── Schedule.swift                # Schedule configuration
│   └── APIError.swift                # Error types
├── Services/
│   ├── APIClient.swift               # Async HTTP client (actor)
│   └── SettingsManager.swift         # UserDefaults + Keychain
├── ViewModels/
│   ├── DashboardViewModel.swift      # @Observable dashboard state
│   ├── RunDetailViewModel.swift      # Single run details
│   ├── CreateTestViewModel.swift     # Test creation form
│   └── SchedulesViewModel.swift      # Schedule management
├── Views/
│   ├── Dashboard/                    # Main dashboard views
│   ├── RunDetail/                    # Run details and metrics
│   ├── CreateTest/                   # Test creation form
│   ├── Schedules/                    # Schedule management
│   └── Settings/                     # API configuration
├── Charts/
│   ├── LatencyChart.swift            # Percentile bar chart
│   ├── SuccessRateChart.swift        # Donut chart
│   ├── StatusCodeChart.swift         # Status breakdown
│   └── RunsPerDayChart.swift         # Historical line chart
└── Utilities/
    ├── Extensions.swift              # Date, Color helpers
    └── Constants.swift               # API paths, colors
```

## Architecture

### Concurrency Model

The app uses Swift 6 strict concurrency:
- All `@Observable` classes are `@MainActor` isolated
- `APIClient` is an `actor` for thread-safe networking
- All model types conform to `Sendable`

### Data Flow

```
API Server ←→ APIClient (actor) ←→ ViewModel (@MainActor) ←→ View
                                         ↓
                              SettingsManager (Keychain + UserDefaults)
```

### Key Patterns

- **@Observable**: Modern SwiftUI observation for ViewModels
- **Async/Await**: All network operations use structured concurrency
- **Sendable Types**: `JSONValue` enum provides type-safe JSON handling

## Configuration

### Environment Variables

The app reads these from the Settings screen:

| Setting | Default | Description |
|---------|---------|-------------|
| API Base URL | `http://localhost:8000` | Server URL |
| API Key | (empty) | Authentication key |
| Polling Interval | 3 seconds | Dashboard refresh rate |

### Keychain Storage

The API key is stored securely in the iOS Keychain, not in UserDefaults.

## Building for Release

```bash
cd ios-app/APITestMachine
xcodebuild -scheme APITestMachine -configuration Release -destination 'generic/platform=iOS'
```

## Testing

Run on iOS Simulator:
```bash
xcodebuild -scheme APITestMachine -destination 'platform=iOS Simulator,name=iPhone 16'
```

## Troubleshooting

### "Connection Refused" Error

Ensure the API server is running and accessible from the device/simulator:
- For simulator: `http://localhost:8000` works
- For physical device: Use your Mac's IP address

### API Key Issues

If authentication fails:
1. Go to Settings
2. Clear the API key
3. Re-enter and save

### Build Errors

For Swift 6 concurrency issues, ensure all model types conform to `Sendable`.
