import SwiftUI

struct ItemCardView: View {
    let item: BroadcastItem
    let isFav: Bool
    let onToggleFav: () -> Void
    var onTap: (() -> Void)? = nil
    /// 検索結果など、放送日を表示したい場合 true
    var showDate: Bool = false

    private var meta: GenreMeta { genreMeta(for: item.corner) }

    private var orderNumber: Int { item.order ?? 1 }
    private var numColor: Color {
        let i = (orderNumber - 1) % AppColor.numColors.count
        return AppColor.numColors[i]
    }

    private var displayTime: String {
        // 番組開始からの経過時間 (録画再生位置の目安、4分刻み擬似)
        guard let order = item.order else { return "" }
        let total = (order - 1) * 4
        let h = total / 60
        let m = total % 60
        return String(format: "%d:%02d", h, m)
    }

    private var displayTitle: String {
        // うた/コーナー/人形劇は "{corner}「{title}」" 形式
        if ["うた", "コーナー", "人形劇"].contains(item.corner) {
            return "\(item.corner)「\(item.title)」"
        }
        return item.title
    }

    /// "5/2 (土)" 形式の日付表示
    private var dateLabel: String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "ja_JP")
        f.dateFormat = "M/d (E)"
        f.calendar = Calendar(identifier: .gregorian)
        f.timeZone = TimeZone(identifier: "Asia/Tokyo")
        let isoFmt = DateFormatter()
        isoFmt.dateFormat = "yyyy-MM-dd"
        isoFmt.calendar = Calendar(identifier: .gregorian)
        isoFmt.timeZone = TimeZone(identifier: "Asia/Tokyo")
        guard let d = isoFmt.date(from: item.date) else { return item.date }
        return f.string(from: d)
    }

    /// 番組名ラベル
    private var showLabel: String {
        switch item.show {
        case "okaasan": return "おかあさんといっしょ"
        case "inai":    return "いないいないばあっ!"
        default:        return item.show
        }
    }

    private var tags: [(label: String, bg: Color, fg: Color)] {
        // タイトル文字列を normalize (substring判定用、ー/記号/空白を吸収)
        let titleNorm = Self.normalizeForCompare(item.title)

        var raw: [(String, Color, Color)] = []
        // 1) ジャンル chip (常に最初、無条件で残す)
        raw.append((item.corner, meta.chipBg, meta.chipFg))
        // 2) キャラクター名 (実データある時だけ、最大2個)
        if let chars = item.characters {
            for ch in chars.prefix(2) {
                raw.append((ch, AppColor.tagPurpleBg, AppColor.tagPurpleFg))
            }
        }
        // 注: mood / keywords は主観的形容詞が混ざるためタグ表示はしない
        //     (検索 haystack には DataStore 側で引き続き含めて検索性は維持)

        // dedupe & filter
        // - 同じラベル(normalize比較) は1つだけ
        // - タイトル(normalize)の substring or 逆 は除外
        // - ただし最初のジャンルchip(index==0)は無条件で残す
        var seen = Set<String>()
        var result: [(String, Color, Color)] = []
        for (i, t) in raw.enumerated() {
            let key = Self.normalizeForCompare(t.0)
            if key.isEmpty { continue }
            if !seen.insert(key).inserted { continue }
            if i == 0 {
                result.append(t)
                continue
            }
            if !titleNorm.isEmpty && (titleNorm.contains(key) || key.contains(titleNorm)) {
                continue
            }
            result.append(t)
        }
        return Array(result.prefix(3))
    }

    /// 部分文字列比較用normalize: 長音記号/記号/空白除去 + lowercase
    private static func normalizeForCompare(_ s: String) -> String {
        s.lowercased()
            .replacingOccurrences(of: "ー", with: "")
            .replacingOccurrences(of: "－", with: "")
            .replacingOccurrences(of: "ｰ", with: "")
            .replacingOccurrences(of: "・", with: "")
            .replacingOccurrences(of: "「", with: "")
            .replacingOccurrences(of: "」", with: "")
            .replacingOccurrences(of: "『", with: "")
            .replacingOccurrences(of: "』", with: "")
            .replacingOccurrences(of: "！", with: "")
            .replacingOccurrences(of: "？", with: "")
            .replacingOccurrences(of: "♪", with: "")
            .replacingOccurrences(of: "☆", with: "")
            .replacingOccurrences(of: "★", with: "")
            .filter { !$0.isWhitespace }
    }

    var body: some View {
        HStack(alignment: .center, spacing: 10) {
            // 左: 番号丸 + 時刻
            VStack(spacing: 4) {
                ZStack {
                    Circle()
                        .fill(numColor)
                    Text("\(orderNumber)")
                        .font(.system(size: 13, weight: .heavy))
                        .foregroundColor(.white)
                }
                .frame(width: 26, height: 26)
                Text(displayTime)
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundColor(AppColor.textDim)
            }
            .frame(width: 40)

            // アイコン square
            ZStack {
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(meta.iconBg)
                Text(meta.emoji)
                    .font(.system(size: 22))
            }
            .frame(width: 44, height: 44)

            // タイトル + タグ
            VStack(alignment: .leading, spacing: 6) {
                if showDate {
                    HStack(spacing: 6) {
                        Text(dateLabel)
                            .font(.system(size: 11, weight: .heavy))
                            .foregroundColor(AppColor.primaryBlue)
                        Text("·")
                            .font(.system(size: 11))
                            .foregroundColor(AppColor.textVeryDim)
                        Text(showLabel)
                            .font(.system(size: 10, weight: .semibold))
                            .foregroundColor(AppColor.textDim)
                    }
                }
                Text(displayTitle)
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(AppColor.text)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)

                // タグchipが長くなる場合は折返し
                FlowLayout(spacing: 4) {
                    ForEach(tags.indices, id: \.self) { i in
                        Text(tags[i].label)
                            .font(.system(size: 10, weight: .semibold))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                            .background(Capsule().fill(tags[i].bg))
                            .foregroundColor(tags[i].fg)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            // ★
            Button(action: onToggleFav) {
                Image(systemName: isFav ? "star.fill" : "star")
                    .font(.system(size: 18))
                    .foregroundColor(isFav ? AppColor.warmOrange : AppColor.textVeryDim)
                    .frame(width: 28, height: 28)
            }
            .buttonStyle(.plain)
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: AppRadius.medium, style: .continuous)
                .fill(AppColor.surface)
        )
        .appCardShadow()
        .contentShape(Rectangle())
        .onTapGesture {
            onTap?()
        }
    }
}

// シンプルな chip 折返し用 Layout
struct FlowLayout: Layout {
    var spacing: CGFloat = 4

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? .infinity
        var total = CGSize(width: 0, height: 0)
        var rowWidth: CGFloat = 0
        var rowHeight: CGFloat = 0

        for sub in subviews {
            let s = sub.sizeThatFits(.unspecified)
            if rowWidth + s.width > maxWidth {
                total.width = max(total.width, rowWidth - spacing)
                total.height += rowHeight + spacing
                rowWidth = 0
                rowHeight = 0
            }
            rowWidth += s.width + spacing
            rowHeight = max(rowHeight, s.height)
        }
        total.width = max(total.width, rowWidth - spacing)
        total.height += rowHeight
        return total
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let maxWidth = bounds.width
        var x: CGFloat = bounds.minX
        var y: CGFloat = bounds.minY
        var rowHeight: CGFloat = 0

        for sub in subviews {
            let s = sub.sizeThatFits(.unspecified)
            if x + s.width > bounds.minX + maxWidth {
                x = bounds.minX
                y += rowHeight + spacing
                rowHeight = 0
            }
            sub.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(s))
            x += s.width + spacing
            rowHeight = max(rowHeight, s.height)
        }
    }
}

#Preview {
    let sample = BroadcastItem(
        id: 1, show: "okaasan", title: "にじのむこうに", corner: "うた",
        date: "2026-05-02", airtime: "07:45", offset: nil, order: 2,
        keywords: ["にじ"], mood: "やさしい", snippet: nil, snippets: nil,
        theme: nil, characters: nil, source: "nhk+weekly", parent: nil, subcategory: nil
    )
    return VStack(spacing: 10) {
        ItemCardView(item: sample, isFav: false, onToggleFav: {})
        ItemCardView(item: BroadcastItem(
            id: 2, show: "okaasan", title: "オープニング", corner: "OP",
            date: "2026-05-02", airtime: "07:45", offset: nil, order: 1,
            keywords: nil, mood: nil, snippet: nil, snippets: nil,
            theme: nil, characters: nil, source: nil, parent: nil, subcategory: nil
        ), isFav: true, onToggleFav: {})
    }
    .padding()
    .background(AppColor.bgGradient)
}
