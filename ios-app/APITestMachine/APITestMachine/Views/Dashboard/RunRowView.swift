//
//  RunRowView.swift
//  APITestMachine
//
//  Run list item view
//

import SwiftUI

struct RunRowView: View {
    let run: RunSummary

    var body: some View {
        HStack(spacing: 12) {
            statusIcon

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(run.name)
                        .font(.headline)
                        .lineLimit(1)

                    Spacer()

                    statusBadge
                }

                HStack {
                    if run.status.isActive {
                        ProgressView(value: run.progress)
                            .frame(maxWidth: 100)

                        Text("\(Int(run.progress * 100))%")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    } else {
                        Text("\(run.requestsCompleted)/\(run.totalRequests) requests")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()

                    if let startedAt = run.startedAt {
                        Text(startedAt, style: .relative)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundStyle(.tertiary)
        }
        .padding(.vertical, 4)
    }

    @ViewBuilder
    private var statusIcon: some View {
        Group {
            switch run.status {
            case .pending:
                Image(systemName: "clock.fill")
                    .foregroundStyle(.gray)
            case .running:
                ProgressView()
                    .controlSize(.small)
            case .completed:
                if run.passed == true {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(.green)
                } else if run.passed == false {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.red)
                } else {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(.gray)
                }
            case .cancelled:
                Image(systemName: "stop.circle.fill")
                    .foregroundStyle(.orange)
            case .failed:
                Image(systemName: "exclamationmark.circle.fill")
                    .foregroundStyle(.red)
            }
        }
        .frame(width: 24)
    }

    private var statusBadge: some View {
        Text(run.status.displayName)
            .font(.caption2)
            .fontWeight(.medium)
            .padding(.horizontal, 8)
            .padding(.vertical, 2)
            .background(statusBackgroundColor.opacity(0.2))
            .foregroundStyle(statusBackgroundColor)
            .clipShape(Capsule())
    }

    private var statusBackgroundColor: Color {
        switch run.status {
        case .pending: return .gray
        case .running: return .blue
        case .completed:
            if let passed = run.passed {
                return passed ? .green : .red
            }
            return .gray
        case .cancelled: return .orange
        case .failed: return .red
        }
    }
}

#Preview {
    List {
        RunRowView(run: RunSummary(
            id: UUID(),
            name: "API Health Check",
            status: .running,
            startedAt: Date().addingTimeInterval(-60),
            completedAt: nil,
            totalRequests: 100,
            requestsCompleted: 45,
            passed: nil
        ))

        RunRowView(run: RunSummary(
            id: UUID(),
            name: "Load Test",
            status: .completed,
            startedAt: Date().addingTimeInterval(-300),
            completedAt: Date().addingTimeInterval(-240),
            totalRequests: 1000,
            requestsCompleted: 1000,
            passed: true
        ))

        RunRowView(run: RunSummary(
            id: UUID(),
            name: "Stress Test",
            status: .failed,
            startedAt: Date().addingTimeInterval(-600),
            completedAt: Date().addingTimeInterval(-590),
            totalRequests: 500,
            requestsCompleted: 125,
            passed: false
        ))
    }
}
