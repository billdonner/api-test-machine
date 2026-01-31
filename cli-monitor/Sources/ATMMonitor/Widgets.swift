//
//  Widgets.swift
//  ATMMonitor
//
//  UI widget components for the dashboard
//

import Foundation

struct Widgets {

    // MARK: - Server Status Widget

    static func serverWidget(state: DashboardState, processes: [ATMProcessInfo]) -> [String] {
        var lines: [String] = []

        lines.append(ANSIRenderer.sectionTop(title: "API TEST MACHINE"))

        // Server status line
        let statusDot = ANSIRenderer.statusDot(online: state.serverOnline)
        let statusText = ANSIRenderer.statusText(online: state.serverOnline)
        let uptime = state.serverOnline ? "  Uptime: \(ANSIRenderer.formatUptime(state.serverUptime))" : ""
        lines.append(ANSIRenderer.row("Server: \(statusDot) \(statusText)\(uptime)"))

        // Version
        if state.serverOnline {
            lines.append(ANSIRenderer.row("Version: \(ANSIRenderer.cyan(state.serverVersion))"))
        }

        lines.append(ANSIRenderer.sectionMiddle())

        // Process status
        for process in processes {
            let dot = ANSIRenderer.statusDot(online: process.isRunning)
            let status = process.isRunning ? ANSIRenderer.green("Running") : ANSIRenderer.red("Stopped")
            lines.append(ANSIRenderer.row("\(process.name): \(dot) \(status)  (port \(process.port))"))
        }

        lines.append(ANSIRenderer.sectionBottom())

        return lines
    }

    // MARK: - Active Runs Widget

    static func activeRunsWidget(state: DashboardState) -> [String] {
        var lines: [String] = []

        let activeCount = state.activeRuns.count
        let title = "ACTIVE RUNS (\(activeCount))"
        lines.append(ANSIRenderer.sectionTop(title: title))

        if state.activeRuns.isEmpty {
            lines.append(ANSIRenderer.row(ANSIRenderer.gray("No active runs")))
        } else {
            for run in state.activeRuns.prefix(5) {
                let name = ANSIRenderer.truncate(run.name, maxLength: 25)
                let status = ANSIRenderer.runStatus(run.status, passed: run.passed)
                let progress = "\(run.requestsCompleted)/\(run.totalRequests)"
                let bar = ANSIRenderer.progressBar(value: run.requestsCompleted, total: run.totalRequests, barWidth: 15)

                lines.append(ANSIRenderer.row("\(name)"))
                lines.append(ANSIRenderer.row("  \(status)  \(bar) \(progress)"))
            }

            if state.activeRuns.count > 5 {
                lines.append(ANSIRenderer.row(ANSIRenderer.gray("  ... and \(state.activeRuns.count - 5) more")))
            }
        }

        lines.append(ANSIRenderer.sectionBottom())

        return lines
    }

    // MARK: - Recent Runs Widget

    static func recentRunsWidget(state: DashboardState) -> [String] {
        var lines: [String] = []

        lines.append(ANSIRenderer.sectionTop(title: "RECENT COMPLETED"))

        if state.recentCompletedRuns.isEmpty {
            lines.append(ANSIRenderer.row(ANSIRenderer.gray("No completed runs")))
        } else {
            for run in state.recentCompletedRuns {
                let name = ANSIRenderer.truncate(run.name, maxLength: 35)
                let status = ANSIRenderer.runStatus(run.status, passed: run.passed)
                let requests = "\(run.requestsCompleted) reqs"

                lines.append(ANSIRenderer.row("\(name)  \(status)  \(requests)"))
            }
        }

        lines.append(ANSIRenderer.sectionBottom())

        return lines
    }

    // MARK: - Schedules Widget

    static func schedulesWidget(state: DashboardState) -> [String] {
        var lines: [String] = []

        let enabledCount = state.enabledSchedules.count
        let pausedCount = state.pausedSchedules.count
        let title = "SCHEDULES (Active: \(enabledCount), Paused: \(pausedCount))"
        lines.append(ANSIRenderer.sectionTop(title: title))

        if state.schedules.isEmpty {
            lines.append(ANSIRenderer.row(ANSIRenderer.gray("No schedules configured")))
        } else {
            // Show enabled schedules first
            for schedule in state.enabledSchedules.prefix(4) {
                let name = ANSIRenderer.truncate(schedule.name, maxLength: 25)
                let trigger = schedule.triggerType
                let runs = schedule.maxRuns != nil ? "\(schedule.runCount)/\(schedule.maxRuns!)" : "\(schedule.runCount)"
                let dot = ANSIRenderer.green("●")

                lines.append(ANSIRenderer.row("\(dot) \(name)  [\(trigger)]  Runs: \(runs)"))
            }

            // Show paused schedules
            for schedule in state.pausedSchedules.prefix(2) {
                let name = ANSIRenderer.truncate(schedule.name, maxLength: 25)
                let dot = ANSIRenderer.yellow("●")

                lines.append(ANSIRenderer.row("\(dot) \(name)  \(ANSIRenderer.yellow("PAUSED"))"))
            }

            let totalShown = min(4, state.enabledSchedules.count) + min(2, state.pausedSchedules.count)
            let totalSchedules = state.schedules.count
            if totalShown < totalSchedules {
                lines.append(ANSIRenderer.row(ANSIRenderer.gray("  ... and \(totalSchedules - totalShown) more")))
            }
        }

        lines.append(ANSIRenderer.sectionBottom())

        return lines
    }

    // MARK: - Stats Summary Widget

    static func statsWidget(state: DashboardState) -> [String] {
        var lines: [String] = []

        lines.append(ANSIRenderer.sectionTop(title: "SUMMARY"))

        let totalRuns = state.runs.count
        let passedRuns = state.runs.filter { $0.passed == true }.count
        let failedRuns = state.runs.filter { $0.passed == false }.count
        let activeRuns = state.activeRuns.count

        let passRate = totalRuns > 0 ? Int((Double(passedRuns) / Double(totalRuns - activeRuns)) * 100) : 0

        lines.append(ANSIRenderer.row(
            "Runs: \(ANSIRenderer.cyan("\(totalRuns)"))  " +
            "Active: \(ANSIRenderer.yellow("\(activeRuns)"))  " +
            "Passed: \(ANSIRenderer.green("\(passedRuns)"))  " +
            "Failed: \(ANSIRenderer.red("\(failedRuns)"))"
        ))

        if totalRuns > activeRuns && totalRuns > 0 {
            lines.append(ANSIRenderer.row("Pass Rate: \(passRate)%"))
        }

        lines.append(ANSIRenderer.sectionBottom())

        return lines
    }

    // MARK: - Footer

    static func footer(state: DashboardState, refreshInterval: TimeInterval) -> [String] {
        let timeStr = ANSIRenderer.formatTime(state.lastFetchTime)
        let intervalStr = Int(refreshInterval)

        var footer = "─── Refresh: \(intervalStr)s │ Last: \(timeStr) "

        if let error = state.fetchError {
            footer += "│ \(ANSIRenderer.red("Error: \(ANSIRenderer.truncate(error, maxLength: 20))")) "
        }

        let remaining = ANSIRenderer.width - ANSIRenderer.stripANSI(footer).count
        footer += String(repeating: "─", count: max(0, remaining))

        return [footer]
    }

    // MARK: - Header

    static func header() -> [String] {
        let title = ANSIRenderer.bold("═══ API TEST MACHINE MONITOR ═══")
        let controls = ANSIRenderer.gray("[R:Refresh] [Q:Quit]")

        let titleLen = ANSIRenderer.stripANSI(title).count
        let controlsLen = ANSIRenderer.stripANSI(controls).count
        let spacing = ANSIRenderer.width - titleLen - controlsLen

        return [title + String(repeating: " ", count: max(1, spacing)) + controls, ""]
    }
}
