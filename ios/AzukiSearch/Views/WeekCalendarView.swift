import SwiftUI

struct WeekCalendarView: View {
    @Binding var selectedDate: Date
    let datesWithData: Set<String>   // "YYYY-MM-DD"

    private static let isoFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.calendar = Calendar(identifier: .gregorian)
        f.timeZone = TimeZone(identifier: "Asia/Tokyo")
        return f
    }()

    private var calendar: Calendar {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = TimeZone(identifier: "Asia/Tokyo")!
        c.firstWeekday = 2  // Monday = 2
        return c
    }

    private var weekStart: Date {
        // selectedDate を含む週の月曜日
        let weekday = calendar.component(.weekday, from: selectedDate)
        // weekday: 1=Sun, 2=Mon, ... 7=Sat
        // monday-start offset: weekday=1(Sun)→6, 2(Mon)→0, 3(Tue)→1, ...
        let offset = (weekday + 5) % 7
        return calendar.date(byAdding: .day, value: -offset, to: calendar.startOfDay(for: selectedDate))!
    }

    private var weekDays: [Date] {
        (0..<7).map { calendar.date(byAdding: .day, value: $0, to: weekStart)! }
    }

    private var headerLabel: String {
        let comps = calendar.dateComponents([.year, .month], from: selectedDate)
        return "\(comps.year ?? 0)年 \(comps.month ?? 0)月"
    }

    private let weekdayLabels = ["月", "火", "水", "木", "金", "土", "日"]

    var body: some View {
        VStack(spacing: 10) {
            // ヘッダ: 前週 < 月 > 次週
            HStack {
                Button(action: shiftWeek(-7)) {
                    Image(systemName: "chevron.left")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundColor(AppColor.text)
                        .frame(width: 30, height: 30)
                }
                Spacer()
                Text(headerLabel)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(AppColor.text)
                Spacer()
                Button(action: shiftWeek(7)) {
                    Image(systemName: "chevron.right")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundColor(AppColor.text)
                        .frame(width: 30, height: 30)
                }
            }
            .padding(.horizontal, 4)

            // 曜日ヘッダ
            HStack(spacing: 0) {
                ForEach(0..<7, id: \.self) { i in
                    let label = weekdayLabels[i]
                    let color: Color = (i == 5) ? AppColor.saturdayFg : (i == 6) ? AppColor.sundayFg : AppColor.textDim
                    Text(label)
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(color)
                        .frame(maxWidth: .infinity)
                }
            }

            // 日付セル
            HStack(spacing: 0) {
                ForEach(0..<7, id: \.self) { i in
                    DayCell(
                        date: weekDays[i],
                        weekIndex: i,
                        selectedDate: $selectedDate,
                        datesWithData: datesWithData,
                        calendar: calendar
                    )
                    .frame(maxWidth: .infinity)
                }
            }
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: AppRadius.medium, style: .continuous)
                .fill(AppColor.surface)
        )
        .appCardShadow()
        .padding(.horizontal, 16)
    }

    private func shiftWeek(_ days: Int) -> () -> Void {
        return {
            withAnimation(.easeOut(duration: 0.18)) {
                selectedDate = calendar.date(byAdding: .day, value: days, to: selectedDate) ?? selectedDate
            }
        }
    }
}

private struct DayCell: View {
    let date: Date
    let weekIndex: Int   // 0=月,..,5=土,6=日
    @Binding var selectedDate: Date
    let datesWithData: Set<String>
    let calendar: Calendar

    private static let isoFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.calendar = Calendar(identifier: .gregorian)
        f.timeZone = TimeZone(identifier: "Asia/Tokyo")
        return f
    }()

    private var iso: String { Self.isoFormatter.string(from: date) }
    private var day: Int { calendar.component(.day, from: date) }
    private var hasData: Bool { datesWithData.contains(iso) }
    private var isSelected: Bool {
        Self.isoFormatter.string(from: date) == Self.isoFormatter.string(from: selectedDate)
    }

    var body: some View {
        Button {
            withAnimation(.easeOut(duration: 0.15)) {
                selectedDate = date
            }
        } label: {
            ZStack {
                if isSelected {
                    Circle()
                        .stroke(AppColor.primaryBlue, lineWidth: 2)
                        .frame(width: 36, height: 36)
                }
                VStack(spacing: 2) {
                    if hasData && !isSelected {
                        Circle()
                            .fill(AppColor.warmOrange.opacity(0.7))
                            .frame(width: 4, height: 4)
                    } else {
                        Color.clear.frame(width: 4, height: 4)
                    }
                    Text("\(day)")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(textColor)
                }
            }
            .frame(height: 50)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    private var textColor: Color {
        if isSelected { return AppColor.primaryBlue }
        if !hasData { return AppColor.textVeryDim.opacity(0.7) }
        if weekIndex == 5 { return AppColor.saturdayFg }
        if weekIndex == 6 { return AppColor.sundayFg }
        return AppColor.text
    }
}

#Preview {
    @Previewable @State var date = Date()
    return WeekCalendarView(
        selectedDate: $date,
        datesWithData: Set(["2026-05-01", "2026-05-02", "2026-04-29", "2026-04-30", "2026-04-28", "2026-04-27"])
    )
    .padding(.vertical)
    .background(AppColor.bgGradient)
}
