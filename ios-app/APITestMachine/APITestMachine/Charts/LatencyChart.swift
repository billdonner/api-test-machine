//
//  LatencyChart.swift
//  APITestMachine
//
//  Percentile bar chart for latency distribution
//

import SwiftUI
import Charts

struct LatencyChart: View {
    let metrics: Metrics

    private var latencyData: [(name: String, value: Double, color: Color)] {
        var data: [(String, Double, Color)] = []

        if let min = metrics.latencyMinMs {
            data.append(("Min", min, .green))
        }
        if let p50 = metrics.latencyP50Ms {
            data.append(("P50", p50, .blue))
        }
        if let mean = metrics.latencyMeanMs {
            data.append(("Mean", mean, .purple))
        }
        if let p90 = metrics.latencyP90Ms {
            data.append(("P90", p90, .yellow))
        }
        if let p95 = metrics.latencyP95Ms {
            data.append(("P95", p95, .orange))
        }
        if let p99 = metrics.latencyP99Ms {
            data.append(("P99", p99, .red))
        }
        if let max = metrics.latencyMaxMs {
            data.append(("Max", max, .pink))
        }

        return data
    }

    var body: some View {
        VStack(alignment: .leading) {
            if latencyData.isEmpty {
                Text("No latency data")
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Chart(latencyData, id: \.name) { item in
                    BarMark(
                        x: .value("Percentile", item.name),
                        y: .value("Latency (ms)", item.value)
                    )
                    .foregroundStyle(item.color.gradient)
                    .annotation(position: .top) {
                        Text(String(format: "%.0f", item.value))
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
                .chartYAxis {
                    AxisMarks(position: .leading) { value in
                        AxisGridLine()
                        AxisValueLabel {
                            if let intValue = value.as(Int.self) {
                                Text("\(intValue)ms")
                                    .font(.caption2)
                            }
                        }
                    }
                }
                .chartXAxis {
                    AxisMarks { value in
                        AxisValueLabel()
                    }
                }
            }
        }
    }
}

#Preview {
    LatencyChart(metrics: Metrics(
        totalRequests: 1000,
        successfulRequests: 985,
        failedRequests: 15,
        latencyMinMs: 5.2,
        latencyMaxMs: 523.4,
        latencyMeanMs: 45.6,
        latencyP50Ms: 32.1,
        latencyP90Ms: 89.4,
        latencyP95Ms: 125.7,
        latencyP99Ms: 256.3
    ))
    .frame(height: 200)
    .padding()
}
