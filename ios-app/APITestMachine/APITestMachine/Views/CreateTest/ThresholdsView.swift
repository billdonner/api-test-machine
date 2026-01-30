//
//  ThresholdsView.swift
//  APITestMachine
//
//  Threshold settings for pass/fail criteria
//

import SwiftUI

struct ThresholdsView: View {
    @Bindable var viewModel: CreateTestViewModel

    var body: some View {
        Section {
            OptionalNumberField(
                title: "Max P50 Latency",
                value: $viewModel.maxLatencyP50Ms,
                unit: "ms"
            )

            OptionalNumberField(
                title: "Max P95 Latency",
                value: $viewModel.maxLatencyP95Ms,
                unit: "ms"
            )

            OptionalNumberField(
                title: "Max P99 Latency",
                value: $viewModel.maxLatencyP99Ms,
                unit: "ms"
            )

            OptionalPercentField(
                title: "Max Error Rate",
                value: $viewModel.maxErrorRate
            )

            OptionalNumberField(
                title: "Min Throughput",
                value: $viewModel.minThroughputRps,
                unit: "rps"
            )
        } header: {
            Text("Thresholds (Pass/Fail Criteria)")
        } footer: {
            Text("Leave empty to skip threshold check")
        }
    }
}

struct OptionalNumberField: View {
    let title: String
    @Binding var value: Double?
    let unit: String

    @State private var textValue: String = ""

    var body: some View {
        HStack {
            Text(title)

            Spacer()

            TextField("None", text: $textValue)
                .keyboardType(.decimalPad)
                .frame(width: 80)
                .multilineTextAlignment(.trailing)
                .onChange(of: textValue) { _, newValue in
                    if newValue.isEmpty {
                        value = nil
                    } else if let doubleValue = Double(newValue) {
                        value = doubleValue
                    }
                }

            Text(unit)
                .foregroundStyle(.secondary)
                .frame(width: 30, alignment: .leading)
        }
        .onAppear {
            if let value = value {
                textValue = String(format: "%.0f", value)
            }
        }
    }
}

struct OptionalPercentField: View {
    let title: String
    @Binding var value: Double?

    @State private var textValue: String = ""

    var body: some View {
        HStack {
            Text(title)

            Spacer()

            TextField("None", text: $textValue)
                .keyboardType(.decimalPad)
                .frame(width: 80)
                .multilineTextAlignment(.trailing)
                .onChange(of: textValue) { _, newValue in
                    if newValue.isEmpty {
                        value = nil
                    } else if let doubleValue = Double(newValue) {
                        // Convert percentage to decimal (e.g., 5% -> 0.05)
                        value = doubleValue / 100.0
                    }
                }

            Text("%")
                .foregroundStyle(.secondary)
                .frame(width: 30, alignment: .leading)
        }
        .onAppear {
            if let value = value {
                // Convert decimal to percentage for display
                textValue = String(format: "%.1f", value * 100)
            }
        }
    }
}

#Preview {
    Form {
        ThresholdsView(viewModel: CreateTestViewModel())
    }
}
