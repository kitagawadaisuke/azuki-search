import SwiftUI

struct MemoEditView: View {
    let item: BroadcastItem
    @EnvironmentObject var memos: MemoStore
    @Environment(\.dismiss) var dismiss

    @State private var draft: String = ""

    private var dateLabel: String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "ja_JP")
        f.dateFormat = "yyyy/M/d (E)"
        f.calendar = Calendar(identifier: .gregorian)
        f.timeZone = TimeZone(identifier: "Asia/Tokyo")
        let isoFmt = DateFormatter()
        isoFmt.dateFormat = "yyyy-MM-dd"
        isoFmt.calendar = Calendar(identifier: .gregorian)
        isoFmt.timeZone = TimeZone(identifier: "Asia/Tokyo")
        guard let d = isoFmt.date(from: item.date) else { return item.date }
        return f.string(from: d)
    }

    private var showLabel: String {
        switch item.show {
        case "okaasan": return "おかあさんといっしょ"
        case "inai":    return "いないいないばあっ!"
        default:        return item.show
        }
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(item.corner.isEmpty ? item.title : "\(item.corner)「\(item.title)」")
                        .font(.system(size: 17, weight: .bold))
                        .foregroundColor(AppColor.text)
                    Text("\(dateLabel) · \(showLabel)")
                        .font(.system(size: 12))
                        .foregroundColor(AppColor.textDim)
                }
                .padding(.horizontal, 4)

                TextEditor(text: $draft)
                    .font(.system(size: 14))
                    .padding(8)
                    .frame(minHeight: 220)
                    .background(
                        RoundedRectangle(cornerRadius: 10)
                            .fill(AppColor.surface)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(AppColor.border, lineWidth: 1)
                    )

                Text("録画した日や感想、子どもの反応などを残せるよ")
                    .font(.system(size: 11))
                    .foregroundColor(AppColor.textVeryDim)
                    .padding(.horizontal, 4)

                Spacer()
            }
            .padding(16)
            .background(AppColor.bgGradient.ignoresSafeArea())
            .navigationTitle("メモ")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("キャンセル") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("保存") {
                        memos.set(draft, for: item.id)
                        dismiss()
                    }
                    .fontWeight(.bold)
                }
            }
            .onAppear {
                draft = memos.memo(for: item.id)
            }
        }
    }
}
