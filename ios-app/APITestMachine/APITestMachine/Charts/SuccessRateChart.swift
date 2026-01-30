//
//  SuccessRateChart.swift
//  APITestMachine
//
//  Success/failure rate donut chart
//

import SwiftUI
import Charts

struct SuccessRateChart: View {
    let successCount: Int
    let failureCount: Int

    private var total: Int {
        successCount + failureCount
    }

    private var successRate: Double {
        guard total > 0 else { return 0 }
        return Double(successCount) / Double(total) * 100
    }

    private var chartData: [(name: String, count: Int, color: Color)] {
        [
            ("Success", successCount, .green),
            ("Failed", failureCount, .red)
        ].filter { $0.count > 0 }
    }

    var body: some View {
        VStack {
            if total == 0 {
                Text("No data")
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Chart(chartData, id: \.name) { item in
                    SectorMark(
                        angle: .value("Count", item.count),
                        innerRadius: .ratio(0.6),
                        angularInset: 1
                    )
                    .foregroundStyle(item.color.gradient)
                }
                .chartBackground { chartProxy in
                    GeometryReader { geometry in
                        let frame = geometry[chartProxy.plotFrame!]
                        VStack {
                            Text(String(format: "%.1f%%", successRate))
                                .font(.title2)
                                .fontWeight(.bold)
                                .foregroundStyle(successRate >= 95 ? .green : (successRate >= 90 ? .orange : .red))
                            Text("Success")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .position(x: frame.midX, y: frame.midY)
                    }
                }
                .chartLegend(position: .bottom, spacing: 10)
            }
        }
    }
}

#Preview {
    VStack {
        SuccessRateChart(successCount: 985, failureCount: 15)
            .frame(height: 200)

        SuccessRateChart(successCount: 750, failureCount: 250)
            .frame(height: 200)
    }
    .padding()
}
