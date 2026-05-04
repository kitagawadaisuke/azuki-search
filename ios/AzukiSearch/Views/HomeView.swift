import SwiftUI

enum ShowFilter: String, CaseIterable, Identifiable {
    case okaasan
    case inai
    var id: String { rawValue }
    var shortName: String {
        switch self {
        case .okaasan: return "おかあさんといっしょ"
        case .inai:    return "いないいないばあっ!"
        }
    }
    var key: String { rawValue }
    var color: Color {
        switch self {
        case .okaasan: return Color(red: 1.00, green: 0.65, blue: 0.40)
        case .inai:    return Color(red: 0.95, green: 0.42, blue: 0.69)
        }
    }
}

struct HomeView: View {
    enum Mode {
        case today        // ホーム: 今日固定、カレンダー非表示
        case dateSearch   // 日付検索: 週カレンダーで日付切替可
    }

    var mode: Mode = .today

    @EnvironmentObject var dataStore: DataStore
    @EnvironmentObject var favs: FavoritesStore

    @AppStorage("selectedShow") private var selectedShowRaw: String = ShowFilter.okaasan.rawValue

    @State private var query: String = ""
    @State private var selectedDate: Date = Date()
    /// 初回データロード後の日付スナップ済みフラグ
    /// (これがないとタブ復帰のたびに最新日付に戻ってしまう)
    @State private var didInitialSnap: Bool = false

    private var selectedShow: ShowFilter {
        ShowFilter(rawValue: selectedShowRaw) ?? .okaasan
    }

    private static let isoFmt: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.calendar = Calendar(identifier: .gregorian)
        f.timeZone = TimeZone(identifier: "Asia/Tokyo")
        return f
    }()

    private var selectedIso: String { Self.isoFmt.string(from: selectedDate) }

    private var dayItems: [BroadcastItem] {
        if !query.trimmingCharacters(in: .whitespaces).isEmpty {
            // 検索時は番組も絞り込む
            return dataStore.searchItems(query: query).filter { $0.show == selectedShow.key }
        }
        return dataStore.uniqueItems(forDate: selectedIso).filter { $0.show == selectedShow.key }
    }

    /// 選択中番組でデータがある日付セット (録画済み振り返り用途のため未来日付は除外)
    private var datesWithData: Set<String> {
        let today = DataStore.todayIso()
        return Set(dataStore.items
            .filter { $0.show == selectedShow.key && $0.date <= today }
            .map { $0.date })
    }

    private var dateHeading: String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "ja_JP")
        f.dateFormat = "yyyy年M月d日(E)"
        f.calendar = Calendar(identifier: .gregorian)
        f.timeZone = TimeZone(identifier: "Asia/Tokyo")
        return f.string(from: selectedDate) + "の放送内容"
    }

    private var headerTitle: String {
        switch mode {
        case .today:      return "今日の放送内容"
        case .dateSearch: return "日付で探す"
        }
    }

    private var headerSubtitle: String {
        switch mode {
        case .today:      return "子ども番組の放送内容を検索・記録・アーカイブ"
        case .dateSearch: return "カレンダーから過去の放送を見る"
        }
    }

    private var isSearching: Bool {
        !query.trimmingCharacters(in: .whitespaces).isEmpty
    }

    var body: some View {
        ZStack(alignment: .top) {
            AppColor.bgGradient.ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    HeaderView(
                        title: headerTitle,
                        subtitle: headerSubtitle,
                        query: $query,
                        showSearch: false
                    )

                    // 番組切替セグメント
                    showSwitcher
                        .padding(.horizontal, 16)
                        .padding(.top, 4)
                        .padding(.bottom, 4)

                    if !isSearching {
                        if mode == .dateSearch {
                            WeekCalendarView(
                                selectedDate: $selectedDate,
                                datesWithData: datesWithData
                            )
                            .padding(.top, 6)
                            .padding(.bottom, 4)
                        }

                        Text(dateHeading)
                            .font(.system(size: 17, weight: .bold))
                            .foregroundColor(AppColor.text)
                            .padding(.horizontal, 16)
                            .padding(.top, 14)
                            .padding(.bottom, 10)
                    } else {
                        Text("「\(query)」の検索結果 (\(dayItems.count)件)")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundColor(AppColor.text)
                            .padding(.horizontal, 16)
                            .padding(.top, 14)
                            .padding(.bottom, 10)
                    }

                    listContent
                        .padding(.horizontal, 16)

                    Text("※放送内容は変更になる場合があります。")
                        .font(.system(size: 10))
                        .foregroundColor(AppColor.textDim)
                        .frame(maxWidth: .infinity)
                        .padding(.top, 18)
                        .padding(.bottom, 24)
                }
            }
            .refreshable {
                await dataStore.load(force: true)
            }
        }
        .onAppear {
            // 初回のみ: 今日の日付がデータにあればそれ、無ければ最新
            // (タブ復帰時にユーザーが選んだ日付が上書きされないよう一度きり)
            if !didInitialSnap && !dataStore.items.isEmpty {
                snapToAvailableDate()
                didInitialSnap = true
            }
        }
        .onChange(of: dataStore.items.count) { _, newCount in
            if !didInitialSnap && newCount > 0 {
                snapToAvailableDate()
                didInitialSnap = true
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    /// 番組(おかいつ/いないばあ)切替のセグメントcontrol
    @ViewBuilder
    private var showSwitcher: some View {
        HStack(spacing: 6) {
            ForEach(ShowFilter.allCases) { f in
                let isOn = (f == selectedShow)
                Button {
                    selectedShowRaw = f.rawValue
                } label: {
                    Text(f.shortName)
                        .font(.system(size: 12, weight: .bold))
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .frame(maxWidth: .infinity)
                        .background(
                            Capsule().fill(isOn ? f.color : Color.white)
                        )
                        .overlay(
                            Capsule().stroke(isOn ? Color.clear : AppColor.border, lineWidth: 1)
                        )
                        .foregroundColor(isOn ? .white : AppColor.textDim)
                }
                .buttonStyle(.plain)
            }
        }
    }

    @ViewBuilder
    private var listContent: some View {
        if dataStore.loadState == .loading && dataStore.items.isEmpty {
            ProgressView()
                .frame(maxWidth: .infinity)
                .padding(.vertical, 40)
        } else if case .error(let msg) = dataStore.loadState, dataStore.items.isEmpty {
            VStack(spacing: 8) {
                Text("⚠️ データ取得失敗")
                    .font(.system(size: 14, weight: .bold))
                Text(msg)
                    .font(.system(size: 11))
                    .foregroundColor(AppColor.textDim)
                    .multilineTextAlignment(.center)
                Button("再試行") {
                    Task { await dataStore.load(force: true) }
                }
            }
            .padding(.vertical, 40)
            .frame(maxWidth: .infinity)
        } else if dayItems.isEmpty {
            VStack(spacing: 10) {
                Image(systemName: isSearching ? "magnifyingglass" : "calendar.badge.exclamationmark")
                    .font(.system(size: 36, weight: .light))
                    .foregroundColor(AppColor.textVeryDim)
                Text(isSearching ? "見つかりませんでした" : "この日の放送データはまだ無いよ")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(AppColor.textDim)
                if !isSearching {
                    Text("データがある日付には・の印があるよ")
                        .font(.system(size: 11))
                        .foregroundColor(AppColor.textDim)
                }
            }
            .padding(.vertical, 40)
            .frame(maxWidth: .infinity)
        } else {
            VStack(spacing: 10) {
                ForEach(dayItems) { item in
                    ItemCardView(
                        item: item,
                        isFav: favs.contains(item.id),
                        onToggleFav: { favs.toggle(item) },
                        showDate: isSearching,
                        totalItems: dayItems.count
                    )
                }
            }
        }
    }

    private func snapToAvailableDate() {
        let today = Self.isoFmt.string(from: Date())
        // 録画振り返り用途のため、今日以前のデータだけを対象に最新日を選ぶ
        let pastDates = Set(dataStore.items.map { $0.date }).filter { $0 <= today }
        if pastDates.contains(today) {
            if let d = parseIso(today) { self.selectedDate = d }
        } else if let latest = pastDates.sorted().last, let d = parseIso(latest) {
            self.selectedDate = d
        }
    }

    private func parseIso(_ s: String) -> Date? {
        Self.isoFmt.date(from: s)
    }
}

#Preview {
    let ds = DataStore()
    let fs = FavoritesStore()
    return HomeView()
        .environmentObject(ds)
        .environmentObject(fs)
        .task {
            await ds.load()
        }
}
