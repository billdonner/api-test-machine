//
//  TerminalBuffer.swift
//  ATMMonitor
//
//  Double-buffered terminal rendering to minimize flicker
//

import Foundation

class TerminalBuffer {
    private var previousLines: [String] = []
    private var isFirstRender = true

    func render(_ lines: [String]) {
        if isFirstRender {
            // Full clear and draw on first render
            print("\u{001B}[2J\u{001B}[H", terminator: "")
            for line in lines {
                print(line)
            }
            fflush(stdout)
            previousLines = lines
            isFirstRender = false
            return
        }

        // Only update changed lines
        let maxLines = max(previousLines.count, lines.count)
        for i in 0..<maxLines {
            let oldLine = i < previousLines.count ? previousLines[i] : ""
            let newLine = i < lines.count ? lines[i] : ""

            if oldLine != newLine {
                // Move to line, clear it, and print new content
                print("\u{001B}[\(i + 1);1H\u{001B}[2K\(newLine)", terminator: "")
            }
        }

        // Clear any extra lines from previous render
        if lines.count < previousLines.count {
            for i in lines.count..<previousLines.count {
                print("\u{001B}[\(i + 1);1H\u{001B}[2K", terminator: "")
            }
        }

        fflush(stdout)
        previousLines = lines
    }

    func forceFullRedraw() {
        isFirstRender = true
    }
}
