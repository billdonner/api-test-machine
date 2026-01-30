//
//  Extensions.swift
//  APITestMachine
//
//  Date, Color, and other utility extensions
//

import SwiftUI

// MARK: - Date Extensions

extension Date {
    var relativeString: String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: self, relativeTo: Date())
    }

    var shortString: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        formatter.timeStyle = .short
        return formatter.string(from: self)
    }

    var iso8601String: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.string(from: self)
    }
}

// MARK: - Color Extensions

extension Color {
    static let statusGreen = Color.green
    static let statusRed = Color.red
    static let statusOrange = Color.orange
    static let statusBlue = Color.blue
    static let statusGray = Color.gray

    init(statusCode: Int) {
        switch statusCode {
        case 200..<300:
            self = .green
        case 300..<400:
            self = .blue
        case 400..<500:
            self = .orange
        case 500..<600:
            self = .red
        default:
            self = .gray
        }
    }
}

// MARK: - Number Formatting

extension Double {
    var formattedLatency: String {
        if self < 1 {
            return String(format: "%.2fms", self)
        } else if self < 1000 {
            return String(format: "%.0fms", self)
        } else {
            return String(format: "%.2fs", self / 1000)
        }
    }

    var formattedPercentage: String {
        String(format: "%.1f%%", self * 100)
    }

    var formattedRPS: String {
        if self < 1 {
            return String(format: "%.2f rps", self)
        } else if self < 100 {
            return String(format: "%.1f rps", self)
        } else {
            return String(format: "%.0f rps", self)
        }
    }
}

extension Int {
    var formattedBytes: String {
        ByteCountFormatter.string(fromByteCount: Int64(self), countStyle: .file)
    }

    var formattedCount: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        return formatter.string(from: NSNumber(value: self)) ?? "\(self)"
    }
}

// MARK: - String Extensions

extension String {
    var isValidURL: Bool {
        if let url = URL(string: self) {
            return url.scheme != nil && url.host != nil
        }
        return false
    }

    func truncated(to length: Int, trailing: String = "...") -> String {
        if self.count > length {
            return String(self.prefix(length)) + trailing
        }
        return self
    }
}

// MARK: - View Extensions

extension View {
    @ViewBuilder
    func `if`<Content: View>(_ condition: Bool, transform: (Self) -> Content) -> some View {
        if condition {
            transform(self)
        } else {
            self
        }
    }
}

// MARK: - Optional Extensions

extension Optional where Wrapped == String {
    var orEmpty: String {
        self ?? ""
    }

    var isNilOrEmpty: Bool {
        self?.isEmpty ?? true
    }
}
