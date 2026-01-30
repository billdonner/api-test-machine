//
//  StatusCodeChart.swift
//  APITestMachine
//
//  Status code distribution donut chart
//

import SwiftUI
import Charts

struct StatusCodeChart: View {
    let statusCodes: [String: Int]

    private var chartData: [(code: String, count: Int, color: Color)] {
        statusCodes.map { code, count in
            let intCode = Int(code) ?? 0
            let color: Color
            switch intCode {
            case 200..<300:
                color = .green
            case 300..<400:
                color = .blue
            case 400..<500:
                color = .orange
            case 500..<600:
                color = .red
            default:
                color = .gray
            }
            return (code, count, color)
        }
        .sorted { $0.code < $1.code }
    }

    private var totalCount: Int {
        statusCodes.values.reduce(0, +)
    }

    var body: some View {
        VStack {
            if chartData.isEmpty {
                Text("No status code data")
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Chart(chartData, id: \.code) { item in
                    SectorMark(
                        angle: .value("Count", item.count),
                        innerRadius: .ratio(0.6),
                        angularInset: 1
                    )
                    .foregroundStyle(item.color.gradient)
                    .annotation(position: .overlay) {
                        if Double(item.count) / Double(totalCount) > 0.05 {
                            Text(item.code)
                                .font(.caption2)
                                .fontWeight(.bold)
                                .foregroundStyle(.white)
                        }
                    }
                }
                .chartLegend(position: .bottom, spacing: 10) {
                    HStack(spacing: 16) {
                        ForEach(chartData, id: \.code) { item in
                            HStack(spacing: 4) {
                                Circle()
                                    .fill(item.color)
                                    .frame(width: 8, height: 8)
                                Text("\(item.code): \(item.count)")
                                    .font(.caption)
                            }
                        }
                    }
                }
            }
        }
    }
}

#Preview {
    StatusCodeChart(statusCodes: [
        "200": 850,
        "201": 100,
        "400": 30,
        "500": 20
    ])
    .frame(height: 200)
    .padding()
}
