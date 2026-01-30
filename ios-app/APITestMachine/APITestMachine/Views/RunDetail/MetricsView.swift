//
//  MetricsView.swift
//  APITestMachine
//
//  Metrics display component
//

import SwiftUI

struct MetricsView: View {
    let metrics: Metrics

    var body: some View {
        VStack(spacing: 16) {
            // Summary row
            HStack(spacing: 20) {
                MetricItem(
                    label: "Total",
                    value: "\(metrics.totalRequests)",
                    color: .blue
                )

                MetricItem(
                    label: "Success",
                    value: "\(metrics.successfulRequests)",
                    color: .green
                )

                MetricItem(
                    label: "Failed",
                    value: "\(metrics.failedRequests)",
                    color: .red
                )
            }

            Divider()

            // Latency row
            HStack(spacing: 16) {
                if let p50 = metrics.latencyP50Ms {
                    MetricItem(
                        label: "P50",
                        value: String(format: "%.0fms", p50),
                        color: .purple
                    )
                }

                if let p95 = metrics.latencyP95Ms {
                    MetricItem(
                        label: "P95",
                        value: String(format: "%.0fms", p95),
                        color: .orange
                    )
                }

                if let p99 = metrics.latencyP99Ms {
                    MetricItem(
                        label: "P99",
                        value: String(format: "%.0fms", p99),
                        color: .red
                    )
                }
            }

            Divider()

            // Throughput row
            HStack(spacing: 20) {
                if let rps = metrics.requestsPerSecond {
                    MetricItem(
                        label: "RPS",
                        value: String(format: "%.1f", rps),
                        color: .teal
                    )
                }

                if let duration = metrics.durationSeconds {
                    MetricItem(
                        label: "Duration",
                        value: String(format: "%.1fs", duration),
                        color: .indigo
                    )
                }

                if let errorRate = metrics.errorRate {
                    MetricItem(
                        label: "Error Rate",
                        value: String(format: "%.1f%%", errorRate * 100),
                        color: errorRate > 0 ? .red : .green
                    )
                }
            }
        }
        .padding(.vertical, 8)
    }
}

struct MetricItem: View {
    let label: String
    let value: String
    let color: Color

    var body: some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.headline)
                .foregroundStyle(color)

            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }
}

#Preview {
    MetricsView(metrics: Metrics(
        totalRequests: 1000,
        successfulRequests: 985,
        failedRequests: 15,
        latencyMinMs: 5.2,
        latencyMaxMs: 523.4,
        latencyMeanMs: 45.6,
        latencyP50Ms: 32.1,
        latencyP90Ms: 89.4,
        latencyP95Ms: 125.7,
        latencyP99Ms: 256.3,
        requestsPerSecond: 156.7,
        durationSeconds: 6.38,
        errorRate: 0.015,
        errorsByType: ["timeout": 10, "connection": 5],
        statusCodeCounts: ["200": 950, "201": 35, "500": 15],
        totalBytesReceived: 1_234_567
    ))
    .padding()
}
