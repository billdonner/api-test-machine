//
//  ANSIRenderer.swift
//  ATMMonitor
//
//  ANSI terminal rendering utilities
//

import Foundation

struct ANSIRenderer {
    static let width = 72  // Dashboard width in columns

    // MARK: - Colors

    static func green(_ text: String) -> String { "\u{001B}[32m\(text)\u{001B}[0m" }
    static func red(_ text: String) -> String { "\u{001B}[31m\(text)\u{001B}[0m" }
    static func yellow(_ text: String) -> String { "\u{001B}[33m\(text)\u{001B}[0m" }
    static func cyan(_ text: String) -> String { "\u{001B}[36m\(text)\u{001B}[0m" }
    static func gray(_ text: String) -> String { "\u{001B}[90m\(text)\u{001B}[0m" }
    static func bold(_ text: String) -> String { "\u{001B}[1m\(text)\u{001B}[0m" }
    static func white(_ text: String) -> String { "\u{001B}[97m\(text)\u{001B}[0m" }

    // MARK: - Cursor/Screen Control

    static func hideCursor() -> String { "\u{001B}[?25l" }
    static func showCursor() -> String { "\u{001B}[?25h" }
    static func clearScreen() -> String { "\u{001B}[2J\u{001B}[H" }
    static func moveTo(row: Int, col: Int) -> String { "\u{001B}[\(row);\(col)H" }
    static func clearLine() -> String { "\u{001B}[2K" }
    static func setWindowTitle(_ title: String) -> String { "\u{001B}]0;\(title)\u{0007}" }

    // MARK: - Box Drawing

    static func sectionTop(title: String) -> String {
        let titlePart = "─ \(title) "
        let remaining = width - titlePart.count - 2
        return "┌\(titlePart)" + String(repeating: "─", count: max(0, remaining)) + "┐"
    }

    static func sectionMiddle() -> String {
        "├" + String(repeating: "─", count: width - 2) + "┤"
    }

    static func sectionBottom() -> String {
        "└" + String(repeating: "─", count: width - 2) + "┘"
    }

    static func row(_ content: String) -> String {
        let stripped = stripANSI(content)
        let padding = max(0, width - stripped.count - 4)
        return "│ \(content)" + String(repeating: " ", count: padding) + " │"
    }

    static func emptyRow() -> String {
        "│" + String(repeating: " ", count: width - 2) + "│"
    }

    // MARK: - Helpers

    static func stripANSI(_ text: String) -> String {
        text.replacingOccurrences(of: "\u{001B}\\[[0-9;]*m", with: "", options: .regularExpression)
    }

    static func statusDot(online: Bool) -> String {
        online ? green("●") : red("●")
    }

    static func statusText(online: Bool) -> String {
        online ? green("ONLINE") : red("OFFLINE")
    }

    static func runStatus(_ status: String, passed: Bool?) -> String {
        switch status {
        case "running":
            return yellow("RUNNING")
        case "pending":
            return gray("PENDING")
        case "completed":
            if let passed = passed {
                return passed ? green("PASSED") : red("FAILED")
            }
            return green("COMPLETED")
        case "cancelled":
            return gray("CANCELLED")
        case "failed":
            return red("FAILED")
        default:
            return gray(status.uppercased())
        }
    }

    static func progressBar(value: Int, total: Int, barWidth: Int = 20) -> String {
        guard total > 0 else { return String(repeating: "░", count: barWidth) }
        let percent = Double(value) / Double(total)
        let filled = Int(percent * Double(barWidth))
        let empty = barWidth - filled
        return green(String(repeating: "█", count: filled)) + gray(String(repeating: "░", count: empty))
    }

    static func formatUptime(_ seconds: TimeInterval) -> String {
        let hours = Int(seconds) / 3600
        let minutes = (Int(seconds) % 3600) / 60
        let secs = Int(seconds) % 60

        if hours > 0 {
            return "\(hours)h \(minutes)m"
        } else if minutes > 0 {
            return "\(minutes)m \(secs)s"
        } else {
            return "\(secs)s"
        }
    }

    static func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        return formatter.string(from: date)
    }

    static func truncate(_ text: String, maxLength: Int) -> String {
        if text.count <= maxLength {
            return text
        }
        return String(text.prefix(maxLength - 3)) + "..."
    }
}
