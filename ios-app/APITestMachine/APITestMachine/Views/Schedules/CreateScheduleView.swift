//
//  CreateScheduleView.swift
//  APITestMachine
//
//  New schedule form
//

import SwiftUI

struct CreateScheduleView: View {
    @Environment(\.dismiss) private var dismiss
    @Bindable var viewModel: SchedulesViewModel

    @State private var name = ""
    @State private var description = ""
    @State private var selectedTestName = ""
    @State private var triggerType: TriggerType = .interval
    @State private var maxRuns: Int?
    @State private var enabled = true
    @State private var tags: [String] = []
    @State private var newTag = ""

    // Interval trigger
    @State private var intervalDays = 0
    @State private var intervalHours = 1
    @State private var intervalMinutes = 0
    @State private var intervalSeconds = 0

    // Cron trigger
    @State private var cronMinute = "*"
    @State private var cronHour = "*"
    @State private var cronDay = "*"
    @State private var cronMonth = "*"
    @State private var cronDayOfWeek = "*"

    // Date trigger
    @State private var runDate = Date().addingTimeInterval(3600)

    @State private var isSubmitting = false
    @State private var error: String?

    var isValid: Bool {
        !name.isEmpty && !selectedTestName.isEmpty
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Schedule Info") {
                    TextField("Schedule Name", text: $name)
                    TextField("Description (optional)", text: $description)
                }

                Section("Test to Run") {
                    if viewModel.testConfigs.isEmpty {
                        Text("No test configurations available")
                            .foregroundStyle(.secondary)
                    } else {
                        Picker("Select Test", selection: $selectedTestName) {
                            Text("Select a test").tag("")
                            ForEach(viewModel.testConfigs) { config in
                                Text(config.name).tag(config.name)
                            }
                        }
                    }
                }

                Section("Trigger Type") {
                    Picker("Type", selection: $triggerType) {
                        ForEach(TriggerType.allCases, id: \.self) { type in
                            Text(type.displayName).tag(type)
                        }
                    }
                    .pickerStyle(.segmented)
                }

                triggerConfigSection

                Section {
                    Toggle("Enabled", isOn: $enabled)

                    HStack {
                        Text("Max Runs")
                        Spacer()
                        TextField("Unlimited", value: $maxRuns, format: .number)
                            .keyboardType(.numberPad)
                            .frame(width: 100)
                            .multilineTextAlignment(.trailing)
                    }
                } header: {
                    Text("Options")
                } footer: {
                    Text("Leave Max Runs empty for unlimited runs")
                }

                Section("Tags") {
                    ForEach(tags, id: \.self) { tag in
                        HStack {
                            Text(tag)
                            Spacer()
                            Button {
                                tags.removeAll { $0 == tag }
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundStyle(.secondary)
                            }
                            .buttonStyle(.plain)
                        }
                    }

                    HStack {
                        TextField("New tag", text: $newTag)
                        Button("Add") {
                            if !newTag.isEmpty && !tags.contains(newTag) {
                                tags.append(newTag)
                                newTag = ""
                            }
                        }
                        .disabled(newTag.isEmpty)
                    }
                }

                if let error = error {
                    Section {
                        Text(error)
                            .foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("Create Schedule")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button("Create") {
                        Task { await createSchedule() }
                    }
                    .disabled(!isValid || isSubmitting)
                }
            }
        }
    }

    @ViewBuilder
    private var triggerConfigSection: some View {
        switch triggerType {
        case .interval:
            Section("Interval") {
                Stepper("Days: \(intervalDays)", value: $intervalDays, in: 0...365)
                Stepper("Hours: \(intervalHours)", value: $intervalHours, in: 0...23)
                Stepper("Minutes: \(intervalMinutes)", value: $intervalMinutes, in: 0...59)
                Stepper("Seconds: \(intervalSeconds)", value: $intervalSeconds, in: 0...59)
            }

        case .cron:
            Section {
                TextField("Minute (0-59, *)", text: $cronMinute)
                TextField("Hour (0-23, *)", text: $cronHour)
                TextField("Day (1-31, *)", text: $cronDay)
                TextField("Month (1-12, *)", text: $cronMonth)
                TextField("Day of Week (0-6, *)", text: $cronDayOfWeek)
            } header: {
                Text("Cron Expression")
            } footer: {
                Text("Expression: \(cronMinute) \(cronHour) \(cronDay) \(cronMonth) \(cronDayOfWeek)")
            }

        case .date:
            Section("Run Date") {
                DatePicker("Date & Time", selection: $runDate, in: Date()...)
            }
        }
    }

    private func createSchedule() async {
        isSubmitting = true
        defer { isSubmitting = false }

        let trigger: AnyCodable
        switch triggerType {
        case .interval:
            var dict: [String: JSONValue] = ["type": .string("interval")]
            if intervalDays > 0 { dict["days"] = .int(intervalDays) }
            if intervalHours > 0 { dict["hours"] = .int(intervalHours) }
            if intervalMinutes > 0 { dict["minutes"] = .int(intervalMinutes) }
            if intervalSeconds > 0 { dict["seconds"] = .int(intervalSeconds) }
            trigger = AnyCodable(.object(dict))

        case .cron:
            trigger = AnyCodable(.object([
                "type": .string("cron"),
                "minute": .string(cronMinute),
                "hour": .string(cronHour),
                "day": .string(cronDay),
                "month": .string(cronMonth),
                "day_of_week": .string(cronDayOfWeek),
                "timezone": .string("UTC")
            ]))

        case .date:
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = [.withInternetDateTime]
            trigger = AnyCodable(.object([
                "type": .string("date"),
                "run_date": .string(formatter.string(from: runDate))
            ]))
        }

        do {
            try await viewModel.createSchedule(
                name: name,
                description: description.isEmpty ? nil : description,
                testName: selectedTestName,
                trigger: trigger,
                maxRuns: maxRuns,
                enabled: enabled,
                tags: tags
            )
            dismiss()
        } catch {
            self.error = error.localizedDescription
        }
    }
}

#Preview {
    CreateScheduleView(viewModel: SchedulesViewModel())
}
