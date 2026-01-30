//
//  RunsPerDayChart.swift
//  APITestMachine
//
//  Historical line chart for runs per day
//

import SwiftUI
import Charts

struct RunsByDay: Identifiable {
    let id = UUID()
    let date: Date
    let count: Int
    let passed: Int
    let failed: Int
}

struct RunsPerDayChart: View {
    let data: [RunsByDay]

    var body: some View {
        VStack(alignment: .leading) {
            if data.isEmpty {
                Text("No historical data")
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Chart {
                    ForEach(data) { item in
                        LineMark(
                            x: .value("Date", item.date),
                            y: .value("Total", item.count)
                        )
                        .foregroundStyle(.blue)
                        .interpolationMethod(.catmullRom)

                        AreaMark(
                            x: .value("Date", item.date),
                            y: .value("Total", item.count)
                        )
                        .foregroundStyle(.blue.opacity(0.1))
                        .interpolationMethod(.catmullRom)

                        PointMark(
                            x: .value("Date", item.date),
                            y: .value("Total", item.count)
                        )
                        .foregroundStyle(.blue)
                    }
                }
                .chartXAxis {
                    AxisMarks(values: .stride(by: .day)) { value in
                        AxisGridLine()
                        AxisValueLabel(format: .dateTime.month(.abbreviated).day())
                    }
                }
                .chartYAxis {
                    AxisMarks(position: .leading) { value in
                        AxisGridLine()
                        AxisValueLabel()
                    }
                }
            }
        }
    }
}

#Preview {
    let calendar = Calendar.current
    let today = Date()

    let sampleData: [RunsByDay] = (0..<7).map { daysAgo in
        let date = calendar.date(byAdding: .day, value: -daysAgo, to: today)!
        let total = Int.random(in: 5...50)
        let passed = Int.random(in: total/2...total)
        return RunsByDay(
            date: date,
            count: total,
            passed: passed,
            failed: total - passed
        )
    }.reversed()

    return RunsPerDayChart(data: sampleData)
        .frame(height: 200)
        .padding()
}
