//
//  Dashboard.swift
//  ATMMonitor
//
//  Main dashboard render loop
//

import Foundation
import Dispatch

class Dashboard {
    private let config: MonitorConfig
    private let fetcher: DataFetcher
    private let terminalBuffer = TerminalBuffer()
    private let keyboard = KeyboardInput()
    private var isRunning = true
    private var forceRefresh = false

    init(config: MonitorConfig) {
        self.config = config
        self.fetcher = DataFetcher(config: config)
    }

    func run() async {
        // Setup signal handling (Ctrl+C)
        setupSignalHandler()

        // Setup keyboard input
        keyboard.enable { [weak self] char in
            self?.handleKey(char)
        }

        // Set window title and hide cursor
        print(ANSIRenderer.setWindowTitle("API Test Machine Monitor"), terminator: "")
        print(ANSIRenderer.hideCursor(), terminator: "")
        fflush(stdout)

        var lastRender = Date.distantPast

        while isRunning {
            // Poll keyboard
            keyboard.poll()

            // Fetch and render at configured interval or on force refresh
            let shouldRefresh = forceRefresh || Date().timeIntervalSince(lastRender) >= config.refreshInterval

            if shouldRefresh {
                forceRefresh = false
                let state = await fetcher.fetchAll()
                let processes = getProcesses()
                render(state: state, processes: processes)
                lastRender = Date()
            }

            // Small sleep to prevent busy-waiting
            try? await Task.sleep(nanoseconds: 100_000_000)  // 100ms
        }

        // Cleanup
        cleanup()
    }

    private func setupSignalHandler() {
        let signalSource = DispatchSource.makeSignalSource(signal: SIGINT, queue: .main)
        signal(SIGINT, SIG_IGN)
        signalSource.setEventHandler { [weak self] in
            self?.isRunning = false
        }
        signalSource.resume()
    }

    private func handleKey(_ char: Character) {
        switch char.lowercased() {
        case "q":
            isRunning = false
        case "r":
            forceRefresh = true
            terminalBuffer.forceFullRedraw()
        default:
            break
        }
    }

    private func render(state: DashboardState, processes: [ATMProcessInfo]) {
        var lines: [String] = []

        // Header
        lines.append(contentsOf: Widgets.header())

        // Server status
        lines.append(contentsOf: Widgets.serverWidget(state: state, processes: processes))
        lines.append("")

        // Active runs
        lines.append(contentsOf: Widgets.activeRunsWidget(state: state))
        lines.append("")

        // Recent completed runs
        lines.append(contentsOf: Widgets.recentRunsWidget(state: state))
        lines.append("")

        // Schedules
        lines.append(contentsOf: Widgets.schedulesWidget(state: state))
        lines.append("")

        // Stats summary
        lines.append(contentsOf: Widgets.statsWidget(state: state))
        lines.append("")

        // Footer
        lines.append(contentsOf: Widgets.footer(state: state, refreshInterval: config.refreshInterval))

        // Render
        terminalBuffer.render(lines)
    }

    private func cleanup() {
        keyboard.disable()
        print(ANSIRenderer.setWindowTitle(""), terminator: "")  // Reset window title
        print(ANSIRenderer.showCursor())
        print(ANSIRenderer.clearScreen(), terminator: "")
        print("Monitor stopped.")
        fflush(stdout)

        Task {
            try? await fetcher.shutdown()
        }
    }
}
