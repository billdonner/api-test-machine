//
//  ScheduleRowView.swift
//  APITestMachine
//
//  Schedule item view
//

import SwiftUI

struct ScheduleRowView: View {
    let schedule: ScheduleResponse

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(schedule.name)
                        .font(.headline)

                    Text(schedule.testName)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                statusBadge
            }

            HStack {
                // Trigger info
                Label(schedule.triggerDisplayDescription, systemImage: triggerIcon)
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Spacer()

                // Run count
                Text("\(schedule.runCount) runs")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if let nextRun = schedule.nextRunTime {
                HStack {
                    Image(systemName: "clock")
                        .font(.caption)
                    Text("Next: \(nextRun)")
                        .font(.caption)
                }
                .foregroundStyle(.blue)
            }

            if !schedule.tags.isEmpty {
                HStack {
                    ForEach(schedule.tags, id: \.self) { tag in
                        Text(tag)
                            .font(.caption2)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.purple.opacity(0.1))
                            .foregroundStyle(.purple)
                            .clipShape(Capsule())
                    }
                }
            }
        }
        .padding(.vertical, 4)
    }

    private var statusBadge: some View {
        Group {
            if schedule.paused {
                Text("Paused")
                    .font(.caption2)
                    .fontWeight(.medium)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 2)
                    .background(Color.orange.opacity(0.2))
                    .foregroundStyle(.orange)
                    .clipShape(Capsule())
            } else if schedule.enabled {
                Text("Active")
                    .font(.caption2)
                    .fontWeight(.medium)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 2)
                    .background(Color.green.opacity(0.2))
                    .foregroundStyle(.green)
                    .clipShape(Capsule())
            } else {
                Text("Disabled")
                    .font(.caption2)
                    .fontWeight(.medium)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 2)
                    .background(Color.gray.opacity(0.2))
                    .foregroundStyle(.gray)
                    .clipShape(Capsule())
            }
        }
    }

    private var triggerIcon: String {
        switch TriggerType(rawValue: schedule.triggerType) {
        case .interval: return "repeat"
        case .cron: return "calendar"
        case .date: return "calendar.badge.clock"
        case .none: return "questionmark"
        }
    }
}

#Preview {
    List {
        ScheduleRowView(schedule: ScheduleResponse(
            id: UUID().uuidString,
            name: "Hourly Health Check",
            description: "Run health check every hour",
            testName: "API Health",
            triggerType: "interval",
            trigger: [
                "type": AnyCodable("interval"),
                "hours": AnyCodable(1)
            ],
            maxRuns: nil,
            runCount: 42,
            enabled: true,
            paused: false,
            nextRunTime: "2024-01-15 14:00:00",
            createdAt: Date(),
            updatedAt: Date(),
            tags: ["production", "critical"]
        ))

        ScheduleRowView(schedule: ScheduleResponse(
            id: UUID().uuidString,
            name: "Daily Load Test",
            description: nil,
            testName: "Full Load Test",
            triggerType: "cron",
            trigger: [
                "type": AnyCodable("cron"),
                "minute": AnyCodable("0"),
                "hour": AnyCodable("2")
            ],
            maxRuns: 30,
            runCount: 15,
            enabled: true,
            paused: true,
            nextRunTime: nil,
            createdAt: Date(),
            updatedAt: Date(),
            tags: []
        ))
    }
}
