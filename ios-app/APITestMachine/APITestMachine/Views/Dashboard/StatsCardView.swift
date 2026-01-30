//
//  StatsCardView.swift
//  APITestMachine
//
//  Stats overview card
//

import SwiftUI

struct StatsCardView: View {
    let title: String
    let value: String
    let icon: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: icon)
                    .foregroundStyle(color)

                Spacer()

                Text(value)
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundStyle(color)
            }

            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding()
        .background(color.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

#Preview {
    LazyVGrid(columns: [
        GridItem(.flexible()),
        GridItem(.flexible())
    ], spacing: 12) {
        StatsCardView(
            title: "Total Runs",
            value: "156",
            icon: "number",
            color: .blue
        )

        StatsCardView(
            title: "Active",
            value: "3",
            icon: "play.circle.fill",
            color: .orange
        )

        StatsCardView(
            title: "Passed",
            value: "142",
            icon: "checkmark.circle.fill",
            color: .green
        )

        StatsCardView(
            title: "Failed",
            value: "11",
            icon: "xmark.circle.fill",
            color: .red
        )
    }
    .padding()
}
