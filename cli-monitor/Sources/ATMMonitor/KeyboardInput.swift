//
//  KeyboardInput.swift
//  ATMMonitor
//
//  Non-blocking keyboard input handling
//

import Foundation

class KeyboardInput {
    private var originalTermios: termios?
    private var handler: ((Character) -> Void)?
    private var isEnabled = false

    func enable(handler: @escaping (Character) -> Void) {
        guard !isEnabled else { return }

        self.handler = handler

        // Save current terminal settings
        var raw = termios()
        tcgetattr(STDIN_FILENO, &raw)
        originalTermios = raw

        // Disable echo and canonical mode
        raw.c_lflag &= ~UInt(ECHO | ICANON)

        // Set VMIN and VTIME for non-blocking read
        let vminIndex = Int(VMIN)
        let vtimeIndex = Int(VTIME)
        withUnsafeMutablePointer(to: &raw.c_cc) { ptr in
            ptr.withMemoryRebound(to: cc_t.self, capacity: Int(NCCS)) { cc in
                cc[vminIndex] = 0
                cc[vtimeIndex] = 0
            }
        }

        tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw)

        // Set non-blocking mode
        let flags = fcntl(STDIN_FILENO, F_GETFL)
        fcntl(STDIN_FILENO, F_SETFL, flags | O_NONBLOCK)

        isEnabled = true
    }

    func poll() {
        guard isEnabled else { return }

        var buffer: UInt8 = 0
        let bytesRead = read(STDIN_FILENO, &buffer, 1)

        if bytesRead == 1 {
            handler?(Character(UnicodeScalar(buffer)))
        }
    }

    func disable() {
        guard isEnabled else { return }

        // Restore original terminal settings
        if var original = originalTermios {
            tcsetattr(STDIN_FILENO, TCSAFLUSH, &original)
        }

        // Remove non-blocking flag
        let flags = fcntl(STDIN_FILENO, F_GETFL)
        fcntl(STDIN_FILENO, F_SETFL, flags & ~O_NONBLOCK)

        isEnabled = false
    }

    deinit {
        disable()
    }
}
